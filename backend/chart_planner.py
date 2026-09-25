import logging
import math
import re
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd

from .engine import compute_data_signature, sort_chronologically

logger = logging.getLogger("chartify.chart_planner")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

CONTRACT_VERSION = "1.1"
DEFAULT_CURRENCY = "INR"
_CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}

MAX_PIE_CATEGORIES = 7        # pie/donut slices before the tail is grouped into "Others"
MAX_BAR_CATEGORIES = 30       # bars shown before truncating to top-N
MAX_SERIES = 8                # lines / bars per group
MAX_HEATMAP_LABELS = 50
MAX_POINTS = 5000             # downsample line/area/scatter beyond this

SUPPORTED_CHARTS = {
    "bar", "column", "horizontal_bar", "grouped_bar", "stacked_bar",
    "line", "multi_line", "area", "pie", "donut", "scatter", "histogram",
    "heatmap", "treemap", "lollipop", "waterfall", "funnel", "radar",
    "violin", "box", "kpi", "bubble", "pairplot",
}

_BAR_LIKE = {"bar", "column", "horizontal_bar", "lollipop", "funnel"}
_MULTI_TYPES = {"grouped_bar", "stacked_bar", "multi_line", "area", "radar"}
_CHRONO_SORT_TYPES = {"line", "multi_line", "area"}

# If a renderer does not support a type, degrade to the nearest one it does.
_FALLBACK_CHART = {
    "grouped_bar": "bar", "stacked_bar": "bar", "multi_line": "line", "area": "line",
    "heatmap": "bar", "kpi": "bar", "funnel": "bar", "waterfall": "bar",
    "treemap": "bar", "radar": "bar", "lollipop": "bar", "violin": "box",
    "box": "bar", "donut": "pie", "pie": "bar", "column": "bar",
    "horizontal_bar": "bar", "histogram": "bar", "scatter": "bar",
    "bubble": "scatter", "pairplot": "scatter",
}

_CHART_ALIASES = {
    "doughnut": "donut", "hist": "histogram", "hbar": "horizontal_bar",
    "bar_horizontal": "horizontal_bar", "vertical_bar": "column",
    "boxplot": "box", "scatterplot": "scatter",
    "heat_map": "heatmap", "tree_map": "treemap",
    "grouped": "grouped_bar", "clustered_bar": "grouped_bar", "clustered": "grouped_bar",
    "stacked": "stacked_bar", "stacked_column": "stacked_bar",
    "multi": "multi_line", "multiple_line": "multi_line", "multi_line": "multi_line",
    "spider": "radar", "correlation": "heatmap", "card": "kpi", "metric": "kpi",
    "stat_card": "kpi",
}

_INTENT_ALIASES = {
    "trend": "time_series", "timeseries": "time_series", "over_time": "time_series",
    "top_n": "ranking", "topn": "ranking", "rank": "ranking",
    "composition": "share", "proportion": "share", "part_to_whole": "share",
    "relationship": "correlation", "cohort": "heatmap",
}

_VERTICAL_RE = re.compile(r"\b(?:vertical\s+bar(?:\s+(?:chart|graph))?|column\s+(?:chart|graph)|vertical\s+(?:chart|graph))\b")
_HORIZONTAL_RE = re.compile(r"\bhorizontal\s+(?:bar(?:\s+(?:chart|graph))?|chart|graph)\b")
# "pie chart", "heat map plot", plus Hinglish "pie me / histogram mein"
_CHART_WORD_RE = re.compile(
    r"\b(stacked\s+bar|grouped\s+bar|clustered\s+bar|pie|donut|doughnut|scatter(?:\s*plot)?|histogram|"
    r"heat\s*map|tree\s*map|waterfall|radar|funnel|violin|box\s*plot|line|area|bar)\s+(?:chart|plot|graph)\b"
    r"|\b(pie|donut|doughnut|histogram|heat\s*map|scatter)\s+(?:me|mein|men)\b"
)

_MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_WEEKDAYS = r"(?:mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"

# Labels that START like a month, weekday, quarter, week, fiscal year, dd-mm-yyyy or a year/ISO date.
# Word boundaries stop "smartphones" / "marketing" / "sunrise" from matching.
_CHRONO_RE = re.compile(
    r"^(?:"
    + _MONTHS + r"\b|"
    + _WEEKDAYS + r"\b|"
    r"q[1-4]\b|"
    r"w(?:eek)?\s*-?\s*\d{1,2}\b|"
    r"fy\s*'?\d{2,4}\b|"
    r"\d{1,2}[-/.]\d{1,2}[-/.](?:19|20)?\d{2}\b|"
    r"(?:19|20)\d{2}(?:[-/]\d{1,2}){0,2}(?:[ t].*)?$"
    r")"
)

_PERCENT_TOKENS = {"pct", "percent", "percentage", "perc"}
_COUNT_TOKENS = {"count", "size", "frequency", "qty", "quantity", "number"}
_CURRENCY_TOKENS = {
    "price", "prices", "sale", "sales", "revenue", "cost", "costs", "profit", "profits",
    "amount", "amounts", "gmv", "mrr", "arr", "income", "spend", "expense", "expenses",
    "turnover", "salary", "wage", "fee", "fees",
}
_TEMPORAL_TOKENS = {"date", "month", "year", "quarter", "week", "day", "time", "timestamp", "period", "hour"}
_NUMERIC_TIME_TOKENS = {"year", "month", "quarter", "week", "hour", "day"}
_ID_TOKENS = {"id", "rank", "index", "idx", "serial"}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _column_tokens(name: Any) -> set:
    """'profit_pct' -> {'profit','pct'}, 'TotalSales' -> {'total','sales'}."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(name))
    return {t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t}


def _is_num(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def _is_idlike(col: Any) -> bool:
    return bool(_column_tokens(col) & _ID_TOKENS)


def _is_dimension(df: pd.DataFrame, col: Any) -> bool:
    """A column that labels rows (text, dates, bools, year/month numbers) rather than measures something."""
    return (not _is_num(df[col])) or bool(_column_tokens(col) & _NUMERIC_TIME_TOKENS)


def _safe_float(raw: Any) -> float:
    try:
        if raw is None or pd.isna(raw):
            return 0.0
        f = float(raw)
    except (ValueError, TypeError):
        return 0.0
    return f if math.isfinite(f) else 0.0


def _finite_or(raw: Any, default: Optional[float]) -> Optional[float]:
    try:
        if raw is None or pd.isna(raw):
            return default
        f = float(raw)
    except (ValueError, TypeError):
        return default
    return f if math.isfinite(f) else default


def _to_jsonable(v: Any) -> Any:
    """Convert a cell to a JSON-safe value (no NaN/Inf, no numpy types, no crashes on lists)."""
    if v is None or v is pd.NaT:
        return None
    if pd.api.types.is_scalar(v) and pd.isna(v):
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        return f if math.isfinite(f) else None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def _infer_format(metric_col: Any) -> str:
    tokens = _column_tokens(metric_col)
    if tokens & _PERCENT_TOKENS:      # "profit_pct" is a percentage, not currency
        return "percentage"
    if tokens & _COUNT_TOKENS:        # "sales_count" is a count, not currency
        return "number"
    if tokens & _CURRENCY_TOKENS:
        return "currency"
    return "number"


def _year(s: Optional[str]) -> int:
    if not s:
        return 0
    y = int(s)
    return y + 2000 if y < 100 else y


def _chrono_sort_key(v: Any) -> Optional[Tuple[int, Any]]:
    """Sortable key for common time labels; None if the label is not recognised."""
    t = str(v).strip().lower()
    if not t:
        return None

    if re.match(_WEEKDAYS + r"\b", t):
        return (0, ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(t[:3]))

    m = re.match(r"^w(?:eek)?\s*-?\s*(\d{1,2})\b", t)
    if m:
        return (1, int(m.group(1)))

    m = re.match(r"^fy\s*'?(\d{2,4})\b", t)
    if m:
        return (2, _year(m.group(1)))

    m = re.match(r"^(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?", t)      # ISO: 2024-03 / 2024-03-15
    if m:
        return (3, (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)))

    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b", t)      # Indian: dd-mm-yyyy
    if m:
        return (3, (_year(m.group(3)), int(m.group(2)), int(m.group(1))))

    m = re.match(r"^(" + _MONTHS + r")\b\s*'?(\d{2,4})?", t)
    if m:
        month = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(m.group(1)[:3]) + 1
        return (5, (_year(m.group(2)), month))

    m = re.match(r"^q([1-4])\b\s*'?(\d{2,4})?", t)
    if m:
        return (6, (_year(m.group(2)), int(m.group(1))))

    try:
        return (4, float(t))
    except ValueError:
        return None


def _chronological_order(df: pd.DataFrame, group_col: Any) -> pd.DataFrame:
    """Time-order the rows. Own key first (deterministic), engine helper as fallback; never raises."""
    s = df[group_col]
    if pd.api.types.is_datetime64_any_dtype(s) or _is_num(s):
        return df.sort_values(group_col, kind="stable")

    keys = [_chrono_sort_key(v) for v in s]
    if keys and all(k is not None for k in keys):
        order = sorted(range(len(keys)), key=lambda i: keys[i])
        return df.iloc[order]

    try:
        out = sort_chronologically(df, group_col)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[CHART] chronological sort failed: {exc}")
        return df
    if isinstance(out, pd.DataFrame) and len(out) == len(df):
        return out
    return df


def _top_n_with_others(df: pd.DataFrame, group_col: Any, metric_col: Any, k: int) -> pd.DataFrame:
    ordered = df.sort_values(metric_col, ascending=False, kind="stable")
    head = ordered.head(k)
    rest = ordered.iloc[k:][metric_col].sum()
    others = pd.DataFrame([{group_col: "Others", metric_col: rest}])
    return pd.concat([head, others], ignore_index=True)


def _dist_stats(arr: np.ndarray) -> Optional[Dict[str, Any]]:
    if arr.size == 0:
        return None
    q1, med, q3 = np.percentile(arr, [25, 50, 75])
    return {
        "count": int(arr.size), "min": float(arr.min()), "q1": float(q1),
        "median": float(med), "q3": float(q3), "max": float(arr.max()), "mean": float(arr.mean()),
    }


# --------------------------------------------------------------------------- #
# Planner
# --------------------------------------------------------------------------- #

class ChartPlanner:
    """
    Decoupled Chart Planner:
    Selects chart type based on final data shape and query intent.
    Data first, chart second.

    Set `ChartPlanner.enabled_charts` to the types your renderers actually support;
    anything else is degraded to the nearest supported type (with a fallback note).
    """

    enabled_charts: set = set(SUPPORTED_CHARTS)

    # ---- shared decisions (single source of truth for planner + contract) ---- #

    @staticmethod
    def resolve_columns(result_df: pd.DataFrame, exec_meta: Dict[str, Any]) -> Tuple[Any, Any]:
        """Pick (group_col, metric_col); the metric never silently equals the group unless unavoidable."""
        exec_meta = exec_meta or {}
        cols = list(result_df.columns)
        if not cols:
            return None, None

        numeric = [c for c in cols if _is_num(result_df[c])]
        non_id_dims = [c for c in cols if _is_dimension(result_df, c) and not _is_idlike(c)]
        dims = non_id_dims if non_id_dims else [c for c in cols if _is_dimension(result_df, c)]

        group_col = exec_meta.get("primary_group_col")
        if group_col not in cols:
            group_col = dims[0] if dims else cols[0]

        metric_col = exec_meta.get("primary_metric_col")
        if metric_col not in cols:
            candidates = [c for c in numeric if c != group_col and c not in dims and not _is_idlike(c)]
            if not candidates:
                candidates = [c for c in numeric if c != group_col]
            if candidates:
                metric_col = candidates[0]
            elif numeric:
                metric_col = numeric[0]
            else:
                metric_col = cols[1] if len(cols) > 1 else cols[0]

        return group_col, metric_col

    @classmethod
    def resolve_layout(cls, result_df: pd.DataFrame, exec_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Works out the *shape* of the result:
          - single series        : group + one metric
          - long multi-series    : group + hue (2nd dimension) + one metric   -> hue_col set
          - wide multi-series    : group + several metrics                    -> metric_cols has >1
        exec_meta keys that override guessing: primary_group_col, primary_metric_col, hue_col, metric_cols.
        """
        exec_meta = exec_meta or {}
        group_col, metric_col = cls.resolve_columns(result_df, exec_meta)
        layout = {
            "group_col": group_col,
            "metric_col": metric_col,
            "hue_col": None,
            "metric_cols": [] if metric_col is None else [metric_col],
        }
        if group_col is None:
            return layout

        cols = list(result_df.columns)

        # -- second dimension (hue) --
        explicit_hue = exec_meta.get("hue_col")
        hue_col = explicit_hue if (explicit_hue in cols and explicit_hue not in (group_col, metric_col)) else None
        if hue_col is None and explicit_hue is None and not exec_meta.get("primary_group_col"):
            try:
                group_repeats = result_df[group_col].nunique(dropna=True) < len(result_df)
            except TypeError:
                group_repeats = False
            if group_repeats:  # e.g. month appears once per region -> genuinely two-dimensional
                for c in cols:
                    if c in (group_col, metric_col) or not _is_dimension(result_df, c):
                        continue
                    try:
                        n_unique = result_df[c].nunique(dropna=True)
                    except TypeError:
                        continue
                    if 2 <= n_unique <= MAX_HEATMAP_LABELS:
                        hue_col = c
                        break

        # If the engine did not pin the x-axis, put the time-like dimension on x.
        if (hue_col is not None and exec_meta.get("primary_group_col") not in cols
                and cls.detect_chronological(result_df, hue_col)
                and not cls.detect_chronological(result_df, group_col)):
            group_col, hue_col = hue_col, group_col
            layout["group_col"] = group_col

        layout["hue_col"] = hue_col

        # -- several metrics (wide) --
        if hue_col is None:
            explicit = exec_meta.get("metric_cols")
            if isinstance(explicit, (list, tuple)):
                metrics = [c for c in explicit if c in cols and c != group_col]
            elif exec_meta.get("primary_metric_col") in cols:
                metrics = [metric_col]  # the engine chose one metric; respect it
            else:
                metrics = [
                    c for c in cols
                    if c != group_col and _is_num(result_df[c])
                    and not _is_dimension(result_df, c) and not _is_idlike(c)
                ]
            if len(metrics) >= 2:
                metrics = metrics[:MAX_SERIES]
                layout["metric_cols"] = metrics
                layout["metric_col"] = metrics[0]
            elif len(metrics) == 1 and isinstance(explicit, (list, tuple)):
                layout["metric_cols"] = metrics
                layout["metric_col"] = metrics[0]

        return layout

    @staticmethod
    def detect_chronological(result_df: pd.DataFrame, group_col: Any) -> bool:
        if group_col is None or group_col not in result_df.columns or result_df.empty:
            return False
        series = result_df[group_col]
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        if _is_num(series):
            # A bare number is only "time" if the column says so (year, month, hour...), not just 2001..2010 order ids.
            return bool(_column_tokens(group_col) & _NUMERIC_TIME_TOKENS)
        sample = series.dropna().astype(str).str.strip().str.lower().head(12)
        if sample.empty:
            return False
        return bool(sample.str.match(_CHRONO_RE).mean() >= 0.8)

    @classmethod
    def resolve_chronological(cls, result_df: pd.DataFrame, exec_meta: Dict[str, Any], group_col: Any) -> bool:
        flag = (exec_meta or {}).get("is_chronological")
        if flag is not None:
            return bool(flag)
        return cls.detect_chronological(result_df, group_col)

    # ---- request parsing ---- #

    @staticmethod
    def _normalize_chart_type(raw: Any) -> str:
        if not isinstance(raw, str):
            return ""
        norm = re.sub(r"[\s\-]+", "_", raw.strip().lower())
        norm = re.sub(r"_(chart|plot|graph)$", "", norm)
        return _CHART_ALIASES.get(norm, norm)

    @staticmethod
    def _normalize_intent(raw: Any) -> str:
        norm = re.sub(r"[\s\-]+", "_", str(raw or "aggregation").strip().lower())
        return _INTENT_ALIASES.get(norm, norm)

    @classmethod
    def _chart_from_query_text(cls, text: Any) -> str:
        text = str(text or "").lower()
        if _VERTICAL_RE.search(text):
            return "column"
        if _HORIZONTAL_RE.search(text):
            return "horizontal_bar"
        m = _CHART_WORD_RE.search(text)
        if m:
            return cls._normalize_chart_type(re.sub(r"\s+", " ", m.group(1) or m.group(2)))
        return ""

    @staticmethod
    def _has_negative(result_df: pd.DataFrame, metric_col: Any) -> bool:
        if metric_col is None or metric_col not in result_df.columns:
            return False
        col = result_df[metric_col]
        return bool(_is_num(col) and (col < 0).any())

    @staticmethod
    def _usable_numeric(result_df: pd.DataFrame) -> List[Any]:
        return [c for c in result_df.columns if _is_num(result_df[c]) and not _is_idlike(c)]

    @staticmethod
    def _has_raw_distribution(result_df: pd.DataFrame, group_col: Any, metric_col: Any) -> bool:
        """Box/violin need many raw values per group, not one aggregated number per group."""
        if metric_col is None or metric_col not in result_df.columns or not _is_num(result_df[metric_col]):
            return False
        if group_col == metric_col or group_col not in result_df.columns:
            return len(result_df) >= 5
        try:
            return int(result_df.groupby(group_col, dropna=True)[metric_col].size().max()) >= 5
        except (TypeError, ValueError):
            return False

    # ---- inference ---- #

    @classmethod
    def _bar_orientation(cls, result_df: pd.DataFrame, group_col: Any) -> str:
        if group_col in result_df.columns and len(result_df) > 0:
            longest = int(result_df[group_col].astype(str).str.len().max())
            if len(result_df) > 12 or longest >= 20:
                return "horizontal_bar"
        return "bar"

    @classmethod
    def _infer_chart(cls, result_df: pd.DataFrame, intent: str, exec_meta: Dict[str, Any], layout: Dict[str, Any]) -> str:
        group_col, metric_col, hue_col = layout["group_col"], layout["metric_col"], layout["hue_col"]
        n_rows = len(result_df)
        is_multi = hue_col is not None or len(layout["metric_cols"]) > 1
        metric_numeric = metric_col in result_df.columns and _is_num(result_df[metric_col])

        if intent == "distribution" or exec_meta.get("bins") is not None:
            return "histogram"

        if intent == "correlation" and len(cls._usable_numeric(result_df)) >= 2:
            return "scatter"

        if intent == "heatmap" and hue_col is not None:
            return "heatmap"

        if n_rows == 1 and metric_numeric and not is_multi:
            return "kpi"

        is_chronological = cls.resolve_chronological(result_df, exec_meta, group_col)
        # A ranking sorted by value is not a time series, even if labels are months.
        time_like = intent == "time_series" or (is_chronological and intent != "ranking")

        if is_multi:
            if time_like:
                return "multi_line"
            if intent == "share":
                return "stacked_bar"
            return "grouped_bar"

        if time_like:
            return "line"

        if intent in ("ranking", "comparison", "aggregation"):
            return cls._bar_orientation(result_df, group_col)

        if intent == "share":
            if n_rows <= MAX_PIE_CATEGORIES and metric_numeric and not cls._has_negative(result_df, metric_col):
                return "donut"
            return "bar"

        return "bar"

    # ---- explicit request validation ---- #

    @classmethod
    def _validate_request(
        cls, rc: str, result_df: pd.DataFrame, layout: Dict[str, Any], exec_meta: Dict[str, Any], intent: str = "aggregation"
    ) -> Tuple[str, Optional[str]]:
        group_col, metric_col, hue_col = layout["group_col"], layout["metric_col"], layout["hue_col"]
        n_rows = len(result_df)
        is_multi = hue_col is not None or len(layout["metric_cols"]) > 1
        metric_numeric = metric_col in result_df.columns and _is_num(result_df[metric_col])

        def switch(target: str, why: str) -> Tuple[str, str]:
            note = f"Switched from {rc} to {target} chart because {why}."
            logger.info(f"[CHART CONFLICT] {note}")
            return target, note

        if rc in ("pie", "donut"):
            if hue_col is not None:
                return switch("stacked_bar", f"the result has two dimensions and {rc} charts show a single series")
            if cls._has_negative(result_df, metric_col):
                return switch("bar", f"{rc} charts cannot represent negative values")
            if n_rows > MAX_PIE_CATEGORIES:
                if intent != "share" or not metric_numeric:
                    return switch("bar", f"{rc} charts support up to {MAX_PIE_CATEGORIES} categories (found {n_rows})")
                note = (f"{rc.capitalize()} charts support up to {MAX_PIE_CATEGORIES} slices, so the smallest "
                        f"{n_rows - (MAX_PIE_CATEGORIES - 1)} categories were grouped into 'Others'.")
                logger.info(f"[CHART CONFLICT] {note}")
                return rc, note
            return rc, None

        if rc == "scatter":
            if len([c for c in result_df.columns if _is_num(result_df[c])]) < 2:
                return switch("bar", "scatter plots require two numeric dimensions")
            return "scatter", None

        if rc in ("box", "violin"):
            if not cls._has_raw_distribution(result_df, group_col, metric_col):
                return switch("bar", f"{rc} plots need raw (un-aggregated) values, at least 5 per group")
            return rc, None

        if rc == "heatmap":
            num_cols = [c for c in result_df.columns if _is_num(result_df[c])]
            if len(num_cols) >= 2 or hue_col is not None:
                return "heatmap", None
            return switch("bar", "a heatmap needs two dimensions or at least two numeric columns")

        if rc in ("treemap", "waterfall", "funnel", "radar", "lollipop"):
            if not metric_numeric:
                return switch("bar", f"{rc} charts need a numeric metric")
            if rc == "treemap" and cls._has_negative(result_df, metric_col):
                return switch("bar", "treemaps cannot represent negative values")
            if rc == "radar" and n_rows < 3:
                return switch("bar", "radar charts need at least 3 categories")
            return rc, None

        if rc == "kpi":
            if n_rows != 1:
                return switch("bar", f"a KPI card shows a single value (found {n_rows} rows)")
            return rc, None

        if rc in ("grouped_bar", "stacked_bar", "multi_line") and not is_multi:
            plain = "line" if rc == "multi_line" else "bar"
            return switch(plain, "the result has only one series")

        # Plain bar/line requested but the data has several series -> upgrade silently.
        if is_multi and rc in ("bar", "column"):
            return "grouped_bar", None
        if is_multi and rc == "line":
            return "multi_line", None

        return rc, None

    @classmethod
    def _gate(cls, chart: str, note: Optional[str]) -> Tuple[str, Optional[str]]:
        """Degrade to a chart type the renderers actually support."""
        if chart in cls.enabled_charts:
            return chart, note
        original, seen = chart, set()
        while chart not in cls.enabled_charts and chart not in seen:
            seen.add(chart)
            chart = _FALLBACK_CHART.get(chart, "bar")
        msg = f"{original} charts are not enabled in this deployment, so a {chart} chart was used instead."
        logger.info(f"[CHART CONFLICT] {msg}")
        return chart, (f"{note} {msg}" if note else msg)

    @classmethod
    def select_and_validate_chart(
        cls,
        result_df: pd.DataFrame,
        plan: Dict[str, Any],
        exec_meta: Dict[str, Any]
    ) -> Tuple[str, Optional[str]]:
        """
        Determines the optimal chart type and handles user explicit requests and conflict resolution.
        Returns (chosen_chart_type, fallback_note).
        """
        plan = plan or {}
        exec_meta = exec_meta or {}

        chart_request = plan.get("chart_request") or {}
        requested_raw = chart_request.get("type") if isinstance(chart_request, dict) else None
        requested_chart = cls._normalize_chart_type(requested_raw)
        intent = cls._normalize_intent(plan.get("intent"))

        layout = cls.resolve_layout(result_df, exec_meta)

        # 1. Explicit request (structured first, then tight phrase match on the query text)
        if not requested_chart:
            requested_chart = cls._chart_from_query_text(plan.get("explanation"))

        if requested_chart:
            if requested_chart not in SUPPORTED_CHARTS:
                chosen = cls._infer_chart(result_df, intent, exec_meta, layout)
                note = f"Chart type '{requested_raw or requested_chart}' is not supported, so a {chosen} chart was chosen instead."
                logger.info(f"[CHART CONFLICT] {note}")
                return cls._gate(chosen, note)
            chart, note = cls._validate_request(requested_chart, result_df, layout, exec_meta, intent)
            return cls._gate(chart, note)

        # 2. Data-first inferred selection
        return cls._gate(cls._infer_chart(result_df, intent, exec_meta, layout), None)


# --------------------------------------------------------------------------- #
# Unified data contract (v1.1, backward compatible with 1.0 fields)
# --------------------------------------------------------------------------- #

def _make_points(
    df: pd.DataFrame, x_col: Any, val_col: Any, hue_col: Any, scatter_x: Any, raw_cols: List[Any]
) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for pos, rec in enumerate(df.to_dict("records")):
        label = str(rec[x_col]) if x_col in rec else f"Item {pos + 1}"
        point: Dict[str, Any] = {
            "label": label,
            "val": _safe_float(rec.get(val_col)),
            "raw_row": {k: _to_jsonable(rec.get(k)) for k in raw_cols if k in rec},
        }
        if hue_col is not None:
            point["series"] = str(rec.get(hue_col))
        if scatter_x is not None:
            point["x"] = _safe_float(rec.get(scatter_x))
        points.append(point)
    return points


def build_unified_data_contract(
    result_df: pd.DataFrame,
    plan: Dict[str, Any],
    exec_meta: Dict[str, Any],
    chart_type: str,
    fallback_note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs the exact Unified 2D/3D Data Contract JSON object
    consumed identically by charts.py (2D) and ThreeCanvas.jsx (3D).

    1.1 adds (all optional for old renderers): hue_col, metric_cols, series[], display_notes[],
    and per-type blocks: matrix (heatmap), distributions (box/violin), histogram, waterfall.
    """
    plan = plan or {}
    exec_meta = exec_meta or {}

    if len(result_df.columns) == 0:
        raise ValueError("Cannot build a chart contract from a DataFrame with no columns.")

    chart_type = ChartPlanner._normalize_chart_type(chart_type) or "bar"
    intent = ChartPlanner._normalize_intent(plan.get("intent"))
    layout = ChartPlanner.resolve_layout(result_df, exec_meta)
    group_col, metric_col = layout["group_col"], layout["metric_col"]
    hue_col, metric_cols = layout["hue_col"], list(layout["metric_cols"])

    df = result_df
    notes: List[str] = []
    is_chronological = ChartPlanner.resolve_chronological(result_df, exec_meta, group_col)

    # ---- scatter: needs a numeric x axis ---- #
    x_col = group_col
    scatter_x = None
    if chart_type == "scatter":
        numeric_cols = [c for c in df.columns if _is_num(df[c])]
        y_candidate = metric_col if metric_col in numeric_cols else (numeric_cols[-1] if numeric_cols else None)
        x_candidates = [c for c in numeric_cols if c != y_candidate]
        if group_col in x_candidates:
            scatter_x = group_col
        elif x_candidates:
            scatter_x = x_candidates[0]
        if scatter_x is not None and y_candidate is not None:
            x_col, metric_col = scatter_x, y_candidate
            metric_cols = [metric_col]
        else:
            scatter_x = None
        hue_col = None

    use_multi = (chart_type in _MULTI_TYPES and scatter_x is None
                 and (hue_col is not None or len(metric_cols) > 1))
    use_heat = chart_type == "heatmap" and hue_col is not None and scatter_x is None
    is_long = hue_col is not None and (use_multi or use_heat)

    # ---- single-series charts given multi-series data: combine instead of drawing repeated labels ---- #
    if not use_multi and not use_heat:
        if (hue_col is not None and chart_type not in ("scatter", "box", "violin", "histogram")
                and metric_col in df.columns and _is_num(df[metric_col])):
            df = df.groupby(group_col, sort=False, dropna=False)[metric_col].sum(min_count=1).reset_index()
            notes.append(f"Series were summed because a {chart_type} chart shows a single series.")
        hue_col = None
        metric_cols = [metric_col]
        is_long = False

    metric_numeric = metric_col in df.columns and _is_num(df[metric_col])
    series: List[Dict[str, Any]] = []
    x_categories: List[str] = []
    matrix = None

    if use_multi or use_heat:
        if is_long:
            work = df.copy()
            work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce")
            if chart_type in _CHRONO_SORT_TYPES and is_chronological:
                work = _chronological_order(work, group_col)
            x_order = work[group_col].drop_duplicates().tolist()

            # series order: time-like hue in time order, otherwise biggest first
            hue_cap = MAX_HEATMAP_LABELS if use_heat else MAX_SERIES
            if ChartPlanner.detect_chronological(work, hue_col):
                hue_order = _chronological_order(
                    pd.DataFrame({hue_col: work[hue_col].dropna().drop_duplicates().tolist()}), hue_col
                )[hue_col].tolist()
            else:
                totals = work.groupby(hue_col, sort=False)[metric_col].sum()
                hue_order = totals.sort_values(ascending=False, kind="stable").index.tolist()
            if len(hue_order) > hue_cap:
                notes.append(f"Showing {hue_cap} of {len(hue_order)} series.")
                hue_order = hue_order[:hue_cap]

            if not is_chronological and len(x_order) > MAX_BAR_CATEGORIES:
                x_totals = work.groupby(group_col, sort=False)[metric_col].sum()
                keep = set(x_totals.sort_values(ascending=False, kind="stable").index[:MAX_BAR_CATEGORIES])
                notes.append(f"Showing the top {MAX_BAR_CATEGORIES} of {len(x_order)} categories.")
                x_order = [x for x in x_order if x in keep]

            work = work[work[group_col].isin(x_order) & work[hue_col].isin(hue_order)]
            if work.empty:
                pv = pd.DataFrame(index=x_order, columns=hue_order, dtype=float)
            else:
                pv = work.pivot_table(index=group_col, columns=hue_col, values=metric_col, aggfunc="sum")
                pv = pv.reindex(index=x_order, columns=hue_order)
            df = work

            gap = None if (chart_type == "multi_line" or use_heat) else 0.0
            for h in hue_order:
                series.append({"name": str(h), "axis": "y",
                               "data": [_finite_or(v, gap) for v in pv[h].tolist()]})
            x_categories = [str(x) for x in x_order]
            if use_heat:
                matrix = {
                    "x_labels": x_categories,
                    "y_labels": [str(h) for h in hue_order],
                    "values": [[_finite_or(v, None) for v in pv[h].tolist()] for h in hue_order],
                }
        else:  # wide: several metric columns
            cols_ = [c for c in metric_cols if c in df.columns][:MAX_SERIES]
            if chart_type in _CHRONO_SORT_TYPES and is_chronological:
                df = _chronological_order(df, group_col)
            elif len(df) > MAX_BAR_CATEGORIES and not is_chronological:
                notes.append(f"Showing the top {MAX_BAR_CATEGORIES} of {len(df)} categories.")
                df = df.sort_values(cols_[0], ascending=False, kind="stable").head(MAX_BAR_CATEGORIES)
            x_categories = [str(v) for v in df[group_col]]
            gap = None if chart_type == "multi_line" else 0.0
            for c in cols_:
                series.append({"name": str(c), "axis": "y", "data": [_finite_or(v, gap) for v in df[c]]})
            metric_col = cols_[0]
            # Very different magnitudes (e.g. revenue vs margin) -> second axis
            if chart_type == "multi_line" and len(series) == 2:
                peaks = [max((abs(v) for v in s["data"] if v is not None), default=0.0) for s in series]
                if min(peaks) > 0 and max(peaks) / min(peaks) > 20:
                    series[1]["axis"] = "y2"
    else:
        # ---- ordering, truncation and grouping for single-series charts ---- #
        if scatter_x is None:
            if chart_type in _CHRONO_SORT_TYPES and is_chronological:
                df = _chronological_order(df, group_col)
            elif chart_type in _BAR_LIKE and metric_numeric:
                total = len(df)
                ranked = intent == "ranking" or chart_type == "funnel"
                too_many = total > MAX_BAR_CATEGORIES and not (is_chronological and intent != "ranking")
                if ranked or too_many:
                    asc = ranked and not too_many and str(exec_meta.get("sort_order", "")).lower() == "asc"
                    df = df.sort_values(metric_col, ascending=asc, kind="stable")
                if too_many:
                    notes.append(f"Showing the top {MAX_BAR_CATEGORIES} of {total} categories.")
                    df = df.head(MAX_BAR_CATEGORIES)

            if (chart_type in ("pie", "donut") and len(df) > MAX_PIE_CATEGORIES and metric_numeric
                    and not (df[metric_col] < 0).any()):
                total = len(df)
                df = _top_n_with_others(df, group_col, metric_col, MAX_PIE_CATEGORIES - 1)
                notes.append(f"Smallest {total - (MAX_PIE_CATEGORIES - 1)} categories grouped into 'Others'.")

        if chart_type in ("line", "area", "scatter") and len(df) > MAX_POINTS:
            idx = np.unique(np.linspace(0, len(df) - 1, MAX_POINTS).astype(int))
            notes.append(f"Downsampled from {len(df)} to {len(idx)} points.")
            df = df.iloc[idx]

        x_categories = [] if scatter_x is not None else [str(v) for v in df[x_col].tolist()]
        series.append({"name": str(metric_col), "axis": "y", "data": [_safe_float(v) for v in df[metric_col].tolist()]})

    # ---- which source columns reach the browser ---- #
    raw_opt = exec_meta.get("raw_row_columns")
    if raw_opt == "all":
        raw_cols = list(df.columns)
    elif isinstance(raw_opt, (list, tuple)):
        raw_cols = [c for c in raw_opt if c in df.columns]
    else:  # default: only what the chart itself uses (avoids leaking emails, ids, etc.)
        wanted = [x_col, hue_col if is_long else None, scatter_x, *metric_cols]
        raw_cols = []
        for c in wanted:
            if c is not None and c in df.columns and c not in raw_cols:
                raw_cols.append(c)

    data_points = _make_points(df, x_col, metric_col, hue_col if is_long else None, scatter_x, raw_cols)
    total_sum = sum(p["val"] for p in data_points)

    # ---- per-type extras ---- #
    extras: Dict[str, Any] = {}
    if matrix is not None:
        extras["matrix"] = matrix

    if chart_type in ("box", "violin") and metric_col in df.columns:
        if group_col == metric_col or group_col not in df.columns:
            groups = [("All", df[[metric_col]])]
        else:
            groups = list(df.groupby(group_col, sort=False))
        if len(groups) > MAX_BAR_CATEGORIES:
            notes.append(f"Showing {MAX_BAR_CATEGORIES} of {len(groups)} groups.")
            groups = groups[:MAX_BAR_CATEGORIES]
        distributions = []
        for g, sub in groups:
            vals = pd.to_numeric(sub[metric_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            arr = vals.to_numpy(dtype=float)
            if arr.size > MAX_POINTS:
                arr = arr[np.unique(np.linspace(0, arr.size - 1, MAX_POINTS).astype(int))]
            distributions.append({"group": str(g), "values": arr.tolist(), "stats": _dist_stats(arr)})
        extras["distributions"] = distributions
        x_categories = [d["group"] for d in distributions]

    if (chart_type == "histogram" and exec_meta.get("bins") is None
            and group_col == metric_col and metric_numeric):
        vals = pd.to_numeric(df[metric_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy(float)
        if vals.size >= 2:
            n_bins = int(min(30, max(5, round(math.sqrt(vals.size)))))
            counts, edges = np.histogram(vals, bins=n_bins)
            extras["histogram"] = {"bin_edges": [float(e) for e in edges], "counts": [int(c) for c in counts]}

    if chart_type == "waterfall":
        running, steps = 0.0, []
        for p in data_points:
            start = running
            running += p["val"]
            steps.append({"label": p["label"], "delta": p["val"], "start": start, "end": running})
        extras["waterfall"] = {"steps": steps, "total": running}

    # ---- axis metadata ---- #
    x_tokens = _column_tokens(x_col)
    if scatter_x is not None:
        x_type = "numeric"
    else:
        is_temporal = (
            (x_col in df.columns and pd.api.types.is_datetime64_any_dtype(df[x_col]))
            or bool(x_tokens & _TEMPORAL_TOKENS)
            or is_chronological
        )
        x_type = "temporal" if is_temporal else "categorical"

    fmt = _infer_format(metric_col)
    if len(series) > 1 and not is_long:
        y_label = " / ".join(s["name"] for s in series)
    elif str(metric_col).lower() in ["count", "size", "frequency", "unique_count"]:
        y_label = "Total Count"
    else:
        y_label = str(metric_col)

    axis_metadata: Dict[str, Any] = {
        "x_type": x_type,
        "y_type": "numeric",
        "x_label": str(x_col),
        "y_label": y_label,
        "x_categories": x_categories,
        "format": fmt,
    }
    if fmt == "currency":
        code = str(exec_meta.get("currency") or DEFAULT_CURRENCY).upper()
        axis_metadata["currency"] = code
        axis_metadata["currency_symbol"] = _CURRENCY_SYMBOLS.get(code, code)
        axis_metadata["locale"] = "en-IN" if code == "INR" else "en-US"

    # ---- signature ---- #
    signature_meta: Dict[str, Any] = {
        "chart_type": chart_type, "group_col": x_col, "metric_col": metric_col,
        "hue_col": hue_col if is_long else None, "metric_cols": [str(c) for c in metric_cols],
    }
    if len(series) > 1:
        signature_meta["series"] = series
    signature = compute_data_signature(
        data_points=data_points,
        query=plan.get("explanation", ""),
        metadata=signature_meta
    )

    contract = {
        "contract_version": CONTRACT_VERSION,
        "data_signature": signature,
        "query": plan.get("explanation", ""),
        "intent": plan.get("intent", "aggregation"),
        "chart_type": chart_type,
        "fallback_note": fallback_note,
        "display_notes": notes,
        "x_col": x_col,
        "y_col": metric_col,
        "hue_col": hue_col if is_long else None,
        "metric_cols": [c for c in metric_cols],
        "axis_metadata": axis_metadata,
        "series": series,
        "chart_metadata": {
            "bins": exec_meta.get("bins"),
            "total_sum": round(total_sum, 2),
            "is_chronological": is_chronological,
            "source_row_count": len(result_df),
        },
        "data_points": data_points
    }
    contract.update(extras)

    return contract
