import os
import io
import sys
import json
import base64
from typing import Literal, Optional, Dict, Any, List
from itertools import cycle, islice

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Use non-interactive, thread-safe Agg backend for servers
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.ticker import FuncFormatter
import seaborn as sns

try:
    import squarify
    HAS_SQUARIFY = True
except ImportError:
    squarify = None
    HAS_SQUARIFY = False

from langchain_core.tools import tool

# Ensure UTF-8 output encoding on Windows console to prevent UnicodeEncodeError ('charmap' codec)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Default dataset fallback
DEFAULT_DF = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
    "Sales": [15000, 22000, 18000, 27000, 31000],
    "Profit": [3000, 4500, -1200, 6000, 7500],
    "Region": ["North", "South", "North", "West", "South"]
})



# ==============================================================================
# SASSY & CLASSY DESIGN SYSTEM (Linear, Stripe, Apple Health Inspired)
# ==============================================================================

MODERN_PALETTES: Dict[str, List[str]] = {
    "butter_green": ["#013E37", "#FFEFB3", "#08ab9c", "#f47a34", "#fc6eae", "#ffbd29", "#146665"],
    "aura_bloom":   ["#08ab9c", "#fc6eae", "#f47a34", "#146665", "#ffbd29", "#feb3a8", "#fff2b7"],
    "custom":       ["#013E37", "#FFEFB3", "#08ab9c", "#f47a34", "#fc6eae", "#ffbd29", "#146665"],
    "vibrant":   ["#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#3B82F6", "#F43F5E", "#14B8A6", "#E11D48"],
    "cyberpunk": ["#00F2FE", "#4FACFE", "#FF007F", "#7928CA", "#FF4B4B", "#00DFD8", "#FEE140", "#A855F7"],
    "emerald":   ["#10B981", "#059669", "#047857", "#34D399", "#6EE7B7", "#065F46", "#14B8A6", "#0D9488"],
    "sunset":    ["#F43F5E", "#FB923C", "#FBBF24", "#F472B6", "#C084FC", "#E11D48", "#EA580C", "#D97706"],
    "ocean":     ["#0EA5E9", "#38BDF8", "#0284C7", "#6366F1", "#7DD3FC", "#0369A1", "#2563EB", "#1D4ED8"],
    "purple":    ["#8B5CF6", "#7C3AED", "#6D28D9", "#A78BFA", "#C4B5FD", "#5B21B6", "#4C1D95", "#9333EA"],
    "luxe":      ["#38BDF8", "#818CF8", "#C084FC", "#F472B6", "#FB7185", "#34D399", "#FBBF24", "#A78BFA"],
    "monochrome":["#334155", "#475569", "#64748B", "#94A3B8", "#CBD5E1", "#1E293B", "#0F172A", "#E2E8F0"]
}

DEFAULT_PALETTE = MODERN_PALETTES["butter_green"]

LAST_CHART_DATA: Dict[str, Any] = {}

def get_last_chart_data() -> Dict[str, Any]:
    """Returns the exact plotted dataset and metadata from the most recent 2D chart generation."""
    global LAST_CHART_DATA
    return dict(LAST_CHART_DATA)


def resolve_palette_colors(palette_name: Optional[str], n_colors: int = 8) -> List[str]:
    """Resolves curated HEX color palettes with graceful fallbacks."""
    if palette_name and palette_name.lower() in MODERN_PALETTES:
        colors = MODERN_PALETTES[palette_name.lower()]
    elif palette_name:
        try:
            colors = [matplotlib.colors.to_hex(c) for c in sns.color_palette(palette_name, n_colors)]
        except Exception:
            colors = DEFAULT_PALETTE
    else:
        colors = DEFAULT_PALETTE
    
    if len(colors) < n_colors:
        repeats = (n_colors // len(colors)) + 1
        colors = (colors * repeats)[:n_colors]
    return colors[:n_colors]


def _rank_shade_colors(hero_color: str, values: List[float], is_dark: bool = False) -> List[str]:
    """Generates magnitude-based shades of the hero hue for industry dashboard bar charts."""
    if not values:
        return []
    val_arr = np.array(values, dtype=float)
    max_v = float(np.max(val_arr)) if float(np.max(val_arr)) > 0 else 1.0
    min_v = float(max(np.min(val_arr), 0.0))
    span = (max_v - min_v) if max_v > min_v else 1.0

    try:
        base_rgb = np.array(mcolors.to_rgb(hero_color))
    except Exception:
        base_rgb = np.array([0.2, 0.6, 0.86])

    tint_rgb = np.array([0.22, 0.28, 0.36]) if is_dark else np.array([0.88, 0.91, 0.95])

    shades = []
    for v in val_arr:
        ratio = float(np.clip((v - min_v) / span, 0.0, 1.0))
        intensity = 0.45 + 0.55 * (ratio ** 0.8)
        blended = (1.0 - intensity) * tint_rgb + intensity * base_rgb
        shades.append(mcolors.to_hex(blended))
    return shades


def _draw_gradient_rounded_bar(ax, y_pos: float, bar_height: float, val: float, x_max: float, color: str, is_dark: bool = False):
    """Draws a modern SaaS-styled rounded horizontal bar with a subtle background track."""
    rounding = bar_height / 2.0
    track_color = "#1e293b" if is_dark else "#f1f5f9"

    # Background track pill
    track = mpatches.FancyBboxPatch(
        (0, y_pos - bar_height / 2.0),
        x_max,
        bar_height,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=0,
        facecolor=track_color,
        edgecolor="none",
        zorder=1
    )
    ax.add_patch(track)

    # Filled foreground bar pill
    if val > 0:
        bar_w = max(val, 0.001)
        actual_rounding = min(rounding, bar_w / 2.0)
        bar_patch = mpatches.FancyBboxPatch(
            (0, y_pos - bar_height / 2.0),
            bar_w,
            bar_height,
            boxstyle=f"round,pad=0,rounding_size={actual_rounding}",
            linewidth=0,
            facecolor=color,
            edgecolor="none",
            zorder=3
        )
        ax.add_patch(bar_patch)


def get_active_df() -> pd.DataFrame:
    """Dynamically resolves the active dataset from main.py if loaded, else fallback to DEFAULT_DF."""
    try:
        import main
        if hasattr(main, "df") and isinstance(main.df, pd.DataFrame) and not main.df.empty:
            return main.df
    except Exception:
        pass
    return DEFAULT_DF



def format_num_human(val: Any) -> str:
    """Formats numeric values into compact, human-friendly badges ($15.2K, 1.4M, 25%)."""
    if not isinstance(val, (int, float, np.number)) or pd.isna(val):
        return str(val) if not pd.isna(val) else ""
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}K"
    elif isinstance(val, float):
        if val.is_integer():
            return f"{sign}{int(abs_val)}"
        return f"{sign}{abs_val:.1f}"
    return str(int(val))

import re


def is_temporal_column(col_name: Optional[str], series: Optional[pd.Series] = None) -> bool:
    """Checks if a column represents time, year, date, month, or a chronological dimension."""
    if not col_name:
        return False
    name_lower = str(col_name).lower().strip()
    temporal_terms = ["year", "yr", "date", "month", "quarter", "period", "day", "time", "week"]
    if any(t == name_lower or f"_{t}" in name_lower or f"{t}_" in name_lower or f" {t}" in name_lower or f"{t} " in name_lower or name_lower.endswith(t) or name_lower.startswith(t) for t in temporal_terms):
        return True
    if series is not None:
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        if pd.api.types.is_numeric_dtype(series):
            try:
                valid_vals = series.dropna()
                if len(valid_vals) > 0 and valid_vals.between(1800, 2150).all():
                    return True
            except Exception:
                pass
    return False


def resolve_grouping_column(
    data: pd.DataFrame,
    preferred_col: Optional[str],
    num_col: Optional[str],
    query: Optional[str] = None,
    title: Optional[str] = None
) -> Optional[str]:
    """
    Intelligently resolves the grouping/category dimension column:
    1. Respects user/extractor preferred_col even if numeric (e.g. 'Car Year').
    2. Matches columns mentioned in query/title.
    3. Prefers categorical or temporal columns.
    """
    # 1. Preferred column explicitly provided and valid
    if preferred_col and preferred_col in data.columns and preferred_col != num_col:
        return preferred_col

    combined_text = f"{query or ''} {title or ''}".lower()

    # 2. Match exact column mentions in user query / title
    for col in data.columns:
        if col != num_col and (col.lower() in combined_text or col.lower().replace("_", " ") in combined_text):
            return col

    # 3. Categorical or temporal columns
    candidates = [
        c for c in data.columns
        if c != num_col and (not pd.api.types.is_numeric_dtype(data[c]) or is_temporal_column(c, data[c]))
    ]
    if candidates:
        return candidates[0]

    # 4. Any column other than num_col
    remaining = [c for c in data.columns if c != num_col]
    return remaining[0] if remaining else None


# ==============================================================================
# QUERY INTENT ENGINE (Separating Query Operation from Chart Type)
# ==============================================================================

def detect_query_intent(query_str: Optional[str] = None, title: Optional[str] = None) -> tuple[str, int]:
    """
    Separates QUERY OPERATION from CHART TYPE.
    Returns:
        (operation, limit)
        where operation is one of:
        - 'ranking_desc' (highest, top, largest, maximum, greatest, biggest, rank descending)
        - 'ranking_asc'  (lowest, bottom, smallest, minimum, rank ascending)
        - 'count'        (frequency, distribution, how many, count of each value)
        - 'mean'         (average, mean, avg)
        - 'max'          (what is the maximum, max)
        - 'min'          (what is the minimum, min)
        - 'default'
    """
    text = f"{query_str or ''} {title or ''}".lower().strip()
    if not text:
        return "default", 10

    # Extract limit if specified (e.g. 'top 10', '10 highest', 'top 5', 'limit 10')
    limit = 10
    limit_match = re.search(r'\b(?:top|bottom|highest|lowest|first|last|limit)\s+(\d+)\b', text)
    if not limit_match:
        limit_match = re.search(r'\b(\d+)\s+(?:top|bottom|highest|lowest|items|rows|values|properties|records)\b', text)
    if limit_match:
        try:
            limit = max(1, min(100, int(limit_match.group(1))))
        except Exception:
            limit = 10

    # Check for negations of count / frequency (e.g. "do not use count", "don't count", "no count", "without count", "not frequency")
    negated_count = bool(re.search(r'\b(?:do\s+not|dont|don\'t|no|never|without|not)\s+(?:use\s+)?(?:count|frequency|counts|frequencies)\b', text))

    # 1. SUM / TOTAL QUERIES (sum of, total of, sum, total, size/value)
    if re.search(r'\b(?:total\s+of|sum\s+of|sum\b|totals?\b|overall\s+sum)\b', text) and not any(w in text for w in ["average", "mean", "avg"]):
        return "sum", limit

    # 2. Explicit COUNT / FREQUENCY queries (strictly for frequency / count of each)
    if not negated_count:
        count_triggers = [
            "how many", "count of each",
            "count each", "counts of each", "value count", "value_count",
            "number of properties", "number of houses"
        ]
        if any(trigger in text for trigger in count_triggers):
            return "count", limit
        if "frequency" in text and not any(w in text for w in ["price", "sales", "revenue", "profit", "amount", "cost", "total", "sum", "rate", "earned"]):
            return "count", limit
        if "distribution" in text and not any(w in text for w in ["price", "sales", "revenue", "profit", "amount", "cost", "total", "sum", "rate", "earned", "val", "value"]):
            return "count", limit
        if re.search(r'\bcounts?\b', text) and not any(w in text for w in ["highest", "lowest", "top", "rank", "average", "mean", "sum", "total"]):
            return "count", limit

    # 3. MEAN / AVERAGE
    mean_triggers = ["average", "mean", "avg"]
    if any(re.search(rf'\b{t}\b', text) for t in mean_triggers) and not any(w in text for w in ["highest", "lowest", "top"]):
        return "mean", limit

    # 4. Explicit MAX / MIN queries (single aggregation questions)
    if re.search(r'\b(?:what\s+is\s+the\s+maximum|what\s+is\s+the\s+max|find\s+the\s+maximum|max\s+value)\b', text):
        return "max", 1
    if re.search(r'\b(?:what\s+is\s+the\s+minimum|what\s+is\s+the\s+min|find\s+the\s+minimum|min\s+value)\b', text):
        return "min", 1

    # 5. RANKING DESCENDING
    desc_triggers = [
        "highest", "top", "largest", "maximum", "greatest", "biggest",
        "rank descending", "ranked descending", "descending"
    ]
    if any(re.search(rf'\b{t}\b', text) if " " not in t else t in text for t in desc_triggers):
        return "ranking_desc", limit

    # 6. RANKING ASCENDING
    asc_triggers = [
        "lowest", "bottom", "smallest", "minimum", "least",
        "rank ascending", "ranked ascending", "ascending"
    ]
    if any(re.search(rf'\b{t}\b', text) if " " not in t else t in text for t in asc_triggers):
        return "ranking_asc", limit

    return "default", limit


# ==============================================================================
# BIG DATA SCALABILITY ENGINE (O(N) Complexity)
# ==============================================================================

def smart_preprocess_data(
    data: pd.DataFrame, 
    chart_type: str, 
    x_col: Optional[str] = None, 
    y_col: Optional[str] = None, 
    hue_col: Optional[str] = None,
    query: Optional[str] = None,
    title: Optional[str] = None
) -> pd.DataFrame:
    """
    Big Data Scalability Preprocessor:
    Guarantees clean aggregations, prevents memory leaks or label collisions,
    and ensures sub-300ms chart rendering across datasets of any size.
    Separates Query Operation (ranking, frequency, average, max, min) from Chart Type.
    """
    total_rows = len(data)

    # Detect Query Intent
    op, limit = detect_query_intent(query, title)

    # Identify the primary numeric column if any
    num_col = None
    if y_col and y_col in data.columns and pd.api.types.is_numeric_dtype(data[y_col]):
        num_col = y_col
    elif x_col and x_col in data.columns and pd.api.types.is_numeric_dtype(data[x_col]):
        num_col = x_col
    else:
        combined_text = f"{query or ''} {title or ''}".lower()
        for col in data.columns:
            if pd.api.types.is_numeric_dtype(data[col]):
                if col.lower() in combined_text or any(token in combined_text for token in col.lower().split("_") if len(token) > 2):
                    num_col = col
                    break

    # --------------------------------------------------------------------------
    # INTENT PIPELINE: DATA OPERATION SEPARATE FROM CHART TYPE
    # --------------------------------------------------------------------------

    # 1. RANKING QUERIES (highest, top, largest, lowest, bottom, smallest, etc.)
    # DO NOT use value_counts(), groupby(), or count() for ranking queries.
    if op in ["ranking_desc", "ranking_asc"] and num_col:
        ascending = (op == "ranking_asc")
        ranked_df = data.dropna(subset=[num_col]).sort_values(by=num_col, ascending=ascending).head(limit).copy()
        
        # Check if an explicit categorical/dimension column is involved
        cat_candidates = [c for c in [x_col, y_col] if c and c in data.columns and c != num_col]
        if not cat_candidates:
            ranked_df["Rank"] = [f"Rank {i+1}" for i in range(len(ranked_df))]
        return ranked_df

    # 2. SUM / TOTAL QUERIES
    if op == "sum" and num_col:
        cat_col = resolve_grouping_column(data, x_col, num_col, query=query, title=title)
        if cat_col:
            if chart_type == "treemap":
                return data[[cat_col, num_col]].dropna().copy()
            agg_df = data.groupby(cat_col, as_index=False, observed=True)[num_col].sum()
            if is_temporal_column(cat_col, data[cat_col]):
                return agg_df.sort_values(by=cat_col, ascending=True).head(max(limit, 30)).reset_index(drop=True)
            return agg_df.sort_values(by=num_col, ascending=False).head(limit).reset_index(drop=True)
        else:
            total_val = float(data[num_col].sum())
            return pd.DataFrame({"Metric": [f"Total {num_col}"], num_col: [total_val]})

    # 3. MEAN / AVERAGE QUERIES
    if op == "mean" and num_col:
        cat_col = resolve_grouping_column(data, x_col, num_col, query=query, title=title)
        if cat_col:
            agg_df = data.groupby(cat_col, as_index=False, observed=True)[num_col].mean()
            if is_temporal_column(cat_col, data[cat_col]):
                return agg_df.sort_values(by=cat_col, ascending=True).head(max(limit, 30)).reset_index(drop=True)
            return agg_df.sort_values(by=num_col, ascending=False).head(limit).reset_index(drop=True)
        else:
            mean_val = float(data[num_col].mean())
            return pd.DataFrame({"Metric": [f"Average {num_col}"], num_col: [round(mean_val, 2)]})

    # 4. MAX / MIN SINGLE VALUE AGGREGATION QUERIES
    if op == "max" and num_col:
        max_val = float(data[num_col].max())
        return pd.DataFrame({"Metric": [f"Max {num_col}"], num_col: [max_val]})
    if op == "min" and num_col:
        min_val = float(data[num_col].min())
        return pd.DataFrame({"Metric": [f"Min {num_col}"], num_col: [min_val]})

    # 5. EXPLICIT COUNT / FREQUENCY QUERIES (frequency, distribution, how many, count of each)
    if op == "count":
        # Guard: If y_col is numeric and distinct from x_col, this is a measure distribution (sum), not row count!
        if y_col and y_col in data.columns and pd.api.types.is_numeric_dtype(data[y_col]) and y_col != x_col:
            cat_col = resolve_grouping_column(data, x_col, y_col, query=query, title=title)
            if cat_col:
                if chart_type in ["treemap", "pie", "donut", "doughnut"]:
                    return data[[cat_col, y_col]].dropna().copy()
                agg_df = data.groupby(cat_col, as_index=False, observed=True)[y_col].sum()
                if is_temporal_column(cat_col, data[cat_col]):
                    return agg_df.sort_values(by=cat_col, ascending=True).head(max(limit, 30)).reset_index(drop=True)
                return agg_df.sort_values(by=y_col, ascending=False).head(limit).reset_index(drop=True)
        # Don't force count on treemap/pie/donut if a numeric measure is already present
        if not (chart_type in ["treemap", "pie", "donut", "doughnut"] and y_col and y_col in data.columns and pd.api.types.is_numeric_dtype(data[y_col])):
            col_to_count = resolve_grouping_column(data, x_col, num_col=None, query=query, title=title) or (num_col if num_col else data.columns[0])
            counts = data[col_to_count].value_counts().reset_index()
            counts.columns = [col_to_count, "count"]
            if is_temporal_column(col_to_count, data[col_to_count]):
                counts = counts.sort_values(by=col_to_count, ascending=True)
                return counts.head(max(limit, 30)).reset_index(drop=True)
            return counts.head(limit).reset_index(drop=True)

    # --------------------------------------------------------------------------
    # STANDARD SCALABILITY & CHART TYPE PREPROCESSING
    # --------------------------------------------------------------------------

    # Auto-swap if x_col is numeric and y_col is categorical, UNLESS x_col is temporal/chronological
    if x_col and y_col and x_col in data.columns and y_col in data.columns:
        if pd.api.types.is_numeric_dtype(data[x_col]) and not pd.api.types.is_numeric_dtype(data[y_col]):
            if not is_temporal_column(x_col, data[x_col]):
                x_col, y_col = y_col, x_col

    # For correlation heatmaps and radar charts, retain numeric columns
    if chart_type in ["heatmap", "correlation", "radar", "spider"]:
        num_cols = list(data.select_dtypes(include=["number"]).columns)
        if chart_type in ["radar", "spider"] and x_col and x_col in data.columns and x_col not in num_cols:
            cols = [x_col] + num_cols
            return data[cols].dropna().copy()
        return data[num_cols].dropna().copy() if len(num_cols) >= 2 else data.copy()

    if chart_type == "bubble":
        num_cols = list(data.select_dtypes(include=["number"]).columns)
        check_cols = list(dict.fromkeys([c for c in [x_col, y_col, hue_col] if c and c in data.columns] + num_cols[:4]))
        plot_df = data[check_cols].dropna().copy()
    else:
        # Memory & time optimization: only slice the required columns
        check_cols = [c for c in [x_col, y_col, hue_col] if c and c in data.columns]
        if check_cols:
            plot_df = data[check_cols].dropna().copy()
        else:
            plot_df = data.copy()

    # Bar, Donut, Pie, Funnel, Treemap, Lollipop, Waterfall: aggregate and limit top categories
    if chart_type in ["bar", "donut", "doughnut", "pie", "funnel", "treemap", "lollipop", "waterfall"]:
        if x_col and x_col in plot_df.columns:
            try:
                # If numeric y_col is present, aggregate sum
                if y_col and y_col in plot_df.columns and pd.api.types.is_numeric_dtype(plot_df[y_col]):
                    if chart_type in ["treemap", "pie", "donut", "doughnut"]:
                        # Treemap and pie/donut render blocks handle slice aggregation and top items themselves
                        return plot_df[[x_col, y_col]].dropna().copy()
                    elif hue_col and hue_col in plot_df.columns and chart_type == "bar":
                        agg_df = plot_df.groupby([x_col, hue_col], as_index=False, observed=True)[y_col].mean()
                        top_x = plot_df.groupby(x_col, observed=True)[y_col].sum().nlargest(12).index
                        return agg_df[agg_df[x_col].isin(top_x)].copy()
                    else:
                        agg_df = plot_df.groupby(x_col, as_index=False, observed=True)[y_col].sum()
                        if is_temporal_column(x_col, plot_df[x_col]):
                            return agg_df.sort_values(by=x_col, ascending=True).head(30).reset_index(drop=True)
                        max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 15
                        if len(agg_df) > max_cats:
                            top_n = agg_df.nlargest(max_cats, y_col)
                            return top_n.sort_values(by=y_col, ascending=False).reset_index(drop=True)
                        return agg_df.sort_values(by=y_col, ascending=False).reset_index(drop=True)
                else:
                    # When y_col is missing:
                    # If x_col is numeric, DO NOT use value_counts() unless explicitly requested!
                    if pd.api.types.is_numeric_dtype(plot_df[x_col]):
                        ranked_df = plot_df.sort_values(by=x_col, ascending=False).head(10).copy()
                        ranked_df["Rank"] = [f"Rank {i+1}" for i in range(len(ranked_df))]
                        return ranked_df
                    else:
                        # Categorical frequency
                        counts = plot_df[x_col].value_counts().reset_index()
                        counts.columns = [x_col, "count"]
                        max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 15
                        return counts.head(max_cats).reset_index(drop=True)
            except Exception as e:
                try:
                    print(f"[WARN] Preprocessing aggregation fallback: {e}")
                except Exception:
                    pass

    # Line & Area: Decimate time-series / trends smoothly
    if chart_type in ["line", "trend", "area"]:
        if total_rows > 2500:
            step = max(1, total_rows // 2500)
            return plot_df.iloc[::step].copy()
        return plot_df

    # Scatter, Bubble, Hist, Box, Violin: Representative sampling
    sample_limit = 1500 if chart_type in ["scatter", "bubble"] else 3000
    if total_rows > sample_limit:
        return plot_df.sample(n=sample_limit, random_state=42)

    return plot_df


# ==============================================================================
# STUDIO MATPLOTLIB / SEABORN ENGINE (Magazine-Grade Publication Quality)
# ==============================================================================

@tool
def generate_chart(
    chart_type: Literal[
        "bar", "column", "vertical_bar", "horizontal_bar", "line", "scatter", "histogram", 
        "box", "heatmap", "pie", "area", "violin", "pairplot",
        "treemap", "waterfall", "donut", "funnel", "lollipop", "radar", "bubble"
    ],
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    hue_col: Optional[str] = None,
    title: Optional[str] = "Data Analysis Chart",
    palette: Optional[str] = None,
    style: Optional[str] = "whitegrid",
    output_path: Optional[str] = None,
    query: Optional[str] = None,
    precomputed_df: Optional[Any] = None,
    unified_contract: Optional[Any] = None,
    orientation: Optional[Literal["vertical", "horizontal", "auto"]] = "auto"
) -> str:
    """Generates and saves an ultra-modern, publication-quality data visualization chart.
    Args:
        chart_type: The chart visualization type ('bar', 'column', 'vertical_bar', 'horizontal_bar', 'line', etc.).
        x_col: Category or X-axis column name.
        y_col: Numeric measure or Y-axis column name.
        hue_col: Optional category column for grouping.
        title: Short descriptive title for the chart.
        palette: Color palette name (vibrant, cyberpunk, emerald, sunset, ocean, purple, luxe, monochrome).
        style: Theme style ('whitegrid', 'darkgrid', 'white', 'dark').
        orientation: Optional explicit bar orientation ('vertical', 'horizontal', 'auto').
    """
    global LAST_CHART_DATA
    chart_t = (chart_type or "bar").lower().strip()
    df = get_active_df()
    try:
        if not output_path:
            output_path = f"{chart_t}.png"

        # Step 1: Detect & auto-swap inverted x/y column assignments (exempting temporal/year columns)
        if x_col and y_col and x_col in df.columns and y_col in df.columns:
            if pd.api.types.is_numeric_dtype(df[x_col]) and not pd.api.types.is_numeric_dtype(df[y_col]):
                if not is_temporal_column(x_col, df[x_col]):
                    x_col, y_col = y_col, x_col

        # Check column availability
        for col in [x_col, y_col, hue_col]:
            if col and col not in df.columns:
                return f"Error: Column '{col}' not found. Available columns: {list(df.columns)}"

        # Step 2: Set modern typographic & style parameters
        selected_style = (style or "whitegrid").lower().strip()
        plt.close("all")

        if "dark" in selected_style:
            is_dark = True
            bg_color = "#080d1a" if "background" in selected_style else "#0f172a"
            card_bg = "#1e293b"
            text_color = "#ffffff"
            muted_color = "#ffffff"
            grid_line_color = "#2a374a" if "background" in selected_style else "#334155"
        elif "fivethirtyeight" in selected_style or "538" in selected_style:
            is_dark = False
            bg_color = "#f0f2f5"
            card_bg = "#e2e8f0"
            text_color = "#1e293b"
            muted_color = "#64748b"
            grid_line_color = "#cbd5e1"
        elif "ggplot" in selected_style:
            is_dark = False
            bg_color = "#e5e5e5"
            card_bg = "#d4d4d4"
            text_color = "#262626"
            muted_color = "#525252"
            grid_line_color = "#ffffff"
        else:
            is_dark = False
            bg_color = "#ffffff"
            card_bg = "#f8fafc"
            text_color = "#0f172a"
            muted_color = "#64748b"
            grid_line_color = "#e2e8f0"

        # Setup font family and rcParams for modern aesthetic
        plt.rcParams["font.sans-serif"] = ["Inter", "Segoe UI", "SF Pro Display", "DejaVu Sans", "Arial", "sans-serif"]
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["figure.facecolor"] = bg_color
        plt.rcParams["axes.facecolor"] = bg_color
        plt.rcParams["savefig.facecolor"] = bg_color
        plt.rcParams["text.color"] = text_color
        plt.rcParams["axes.labelcolor"] = text_color
        plt.rcParams["xtick.color"] = text_color
        plt.rcParams["ytick.color"] = text_color
        plt.rcParams["axes.edgecolor"] = grid_line_color if is_dark else muted_color
        plt.rcParams["grid.color"] = grid_line_color

        # Safeguard hue_col cardinality
        safe_hue = hue_col
        show_legend = "brief"
        if hue_col and hue_col in df.columns:
            if df[hue_col].nunique() > 10:
                show_legend = False

        # Step 3: Special Case: Pairplot
        if chart_t == "pairplot":
            palette_colors = resolve_palette_colors(palette, 6)
            grid = sns.pairplot(df, hue=safe_hue, palette=palette_colors)
            grid.fig.suptitle(title, y=1.02, fontsize=14, weight="bold", color=text_color)
            buf = io.BytesIO()
            grid.savefig(buf, format="png", dpi=120, facecolor=bg_color, bbox_inches="tight")
            plt.close(grid.fig)
            buf.seek(0)
            data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            num_cols_p = df.select_dtypes(include=["number"]).columns.tolist()[:4]
            LAST_CHART_DATA = {
                "chart_type": "pairplot",
                "features": num_cols_p,
                "title": title
            }
            if output_path and output_path != ":memory:":
                with open(output_path, "wb") as f:
                    f.write(buf.getvalue())
            return data_url

        # Step 4: Create canvas
        if chart_t in ["radar", "spider"]:
            fig, ax = plt.subplots(figsize=(7, 6.5), subplot_kw=dict(polar=True))
        elif chart_t in ["pie", "donut", "doughnut"]:
            fig, ax = plt.subplots(figsize=(7.5, 5.5))
        else:
            fig, ax = plt.subplots(figsize=(9.2, 5.2))

        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        # Big Data Scalability Preprocessing
        if precomputed_df is not None and isinstance(precomputed_df, pd.DataFrame) and not precomputed_df.empty:
            plot_df = precomputed_df.copy()
        else:
            plot_df = smart_preprocess_data(df, chart_t, x_col, y_col, safe_hue, query=query, title=title)

        # Detect intent for rendering orientation and metrics
        query_op, _ = detect_query_intent(query, title)

        # Effective metric column resolution
        if chart_t in ["histogram", "hist"]:
            num_cols_in_plot = [c for c in plot_df.columns if pd.api.types.is_numeric_dtype(plot_df[c])]
            if not x_col or x_col not in plot_df.columns or not pd.api.types.is_numeric_dtype(plot_df[x_col]):
                if y_col and y_col in plot_df.columns and pd.api.types.is_numeric_dtype(plot_df[y_col]):
                    x_col = y_col
                elif num_cols_in_plot:
                    x_col = num_cols_in_plot[0]
            effective_y = "count"
        else:
            effective_y = y_col
            if not effective_y or effective_y not in plot_df.columns:
                num_cols_in_plot = [c for c in plot_df.columns if c != x_col and c != "count" and pd.api.types.is_numeric_dtype(plot_df[c])]
                if num_cols_in_plot:
                    effective_y = num_cols_in_plot[0]
                elif "count" in plot_df.columns:
                    effective_y = "count"
                else:
                    all_num = [c for c in plot_df.columns if pd.api.types.is_numeric_dtype(plot_df[c])]
                    if all_num:
                        effective_y = all_num[0]

            # Effective category column resolution
            if not x_col or x_col == effective_y or x_col not in plot_df.columns:
                if "Rank" in plot_df.columns:
                    x_col = "Rank"
                elif "Metric" in plot_df.columns:
                    x_col = "Metric"
                else:
                    candidates = [c for c in plot_df.columns if c != effective_y]
                    if candidates:
                        x_col = candidates[0]

        is_horizontal_bar = False

        # --------------------------------------------------------------------------
        # Chart 1: Bar Chart (Ultra-Modern Vertical for Timeline, Horizontal for Ranking)
        # --------------------------------------------------------------------------
        if chart_t in ["bar", "column", "vertical_bar", "horizontal_bar"]:
            if safe_hue:
                # Grouped vertical bar chart
                colors = resolve_palette_colors(palette, plot_df[safe_hue].nunique() if safe_hue in plot_df.columns else 6)
                sns.barplot(data=plot_df, x=x_col, y=effective_y, hue=safe_hue, palette=colors, ax=ax)
                if hasattr(ax, "containers"):
                    for container in ax.containers:
                        try:
                            ax.bar_label(
                                container,
                                fmt=lambda v: format_num_human(v) if abs(v) > 0 else "",
                                padding=3,
                                fontsize=8.5,
                                weight="bold",
                                color=text_color
                            )
                        except Exception:
                            pass
            else:
                is_temporal = is_temporal_column(x_col, plot_df[x_col] if (x_col and x_col in plot_df.columns) else None) or any(
                    w in f"{query or ''} {title or ''}".lower() for w in ["year by year", "by year", "over time", "yearly", "monthly", "timeline", "chronological", "trend", "annual"]
                )

                # Check explicit orientation triggers from chart type, orientation param, or user query text
                query_text = f"{query or ''} {title or ''}".lower()
                user_wants_vertical = (
                    chart_t in ["column", "vertical_bar"] or
                    str(orientation).lower() in ["vertical", "vert", "v"] or
                    any(w in query_text for w in ["vertical bar", "vertical", "column chart", "column", "standing", "upright", "verticale"])
                )
                user_wants_horizontal = (
                    chart_t in ["horizontal_bar"] or
                    str(orientation).lower() in ["horizontal", "horiz", "h"] or
                    any(w in query_text for w in ["horizontal bar", "horizontal", "sideways"])
                )

                if user_wants_vertical:
                    is_vertical = True
                elif user_wants_horizontal:
                    is_vertical = False
                elif is_temporal:
                    is_vertical = True
                else:
                    # Default heuristic when unspecified: vertical if <= 10 categories and labels <= 20 chars
                    categories_sample = plot_df[x_col].astype(str).tolist() if x_col and x_col in plot_df.columns else []
                    max_label_len = max((len(c) for c in categories_sample), default=0)
                    is_vertical = len(categories_sample) <= 10 and max_label_len <= 20

                if is_vertical:
                    # ----------------------------------------------------------
                    # Studio Vertical Column Bar Chart
                    # (Categories on X-axis, metric vertically on Y-axis)
                    # ----------------------------------------------------------
                    is_horizontal_bar = False

                    if is_temporal and x_col and x_col in plot_df.columns:
                        plot_df = plot_df.sort_values(by=x_col, ascending=True).reset_index(drop=True)

                    categories = plot_df[x_col].astype(str).tolist() if x_col and x_col in plot_df.columns else []
                    values = plot_df[effective_y].tolist() if effective_y and effective_y in plot_df.columns else []

                    n_items = len(categories)
                    bar_colors = resolve_palette_colors(palette, max(n_items, 4))
                    if len(bar_colors) < n_items:
                        bar_colors = (bar_colors * (n_items // len(bar_colors) + 1))[:n_items]

                    x_positions = np.arange(n_items)
                    bar_width = 0.52 if n_items <= 6 else (0.62 if n_items <= 12 else 0.72)

                    bars = ax.bar(
                        x_positions,
                        values,
                        width=bar_width,
                        color=bar_colors[:n_items],
                        edgecolor="none",
                        zorder=3
                    )

                    ax.set_xticks(x_positions)
                    rot = 25 if (any(len(str(c)) > 5 for c in categories) or n_items > 8) else 0
                    ax.set_xticklabels(categories, fontsize=10, weight="bold", color=text_color, rotation=rot, ha="right" if rot else "center")

                    max_val = max(values) if values and max(values) > 0 else 1
                    min_val = min(values) if values and min(values) < 0 else 0
                    ax.set_ylim(min(0, min_val * 1.15), max_val * 1.16)

                    # Direct crisp value labels on top of each vertical bar
                    for bar, val in zip(bars, values):
                        h = bar.get_height()
                        x_pos = bar.get_x() + bar.get_width() / 2
                        label_y = h + (max_val * 0.02) if h >= 0 else h - (abs(max_val) * 0.04)
                        va_align = "bottom" if h >= 0 else "top"
                        ax.text(
                            x_pos,
                            label_y,
                            f"{format_num_human(val)}",
                            va=va_align,
                            ha="center",
                            fontsize=9.5,
                            weight="bold",
                            color=text_color,
                            zorder=4
                        )

                    ax.set_xlabel(x_col.replace("_", " ").title() if x_col else "Category", fontsize=10.5, weight="bold", color=text_color, labelpad=8)
                    ax.set_ylabel(effective_y.replace("_", " ").title() if effective_y else "Value", fontsize=10, color=muted_color, labelpad=8)
                else:
                    # ----------------------------------------------------------
                    # Studio Horizontal Bar Chart (Linear / Stripe / Apple Health design)
                    # ----------------------------------------------------------
                    is_horizontal_bar = True

                    # Order categories: ascending=True puts highest value at top bar (y=N-1) in ax.barh
                    # for ranking_asc (lowest), ascending=False puts lowest value at top bar
                    if effective_y and effective_y in plot_df.columns:
                        if query_op == "ranking_asc":
                            plot_df = plot_df.sort_values(by=effective_y, ascending=False).reset_index(drop=True)
                        else:
                            plot_df = plot_df.sort_values(by=effective_y, ascending=True).reset_index(drop=True)

                    categories = plot_df[x_col].astype(str).tolist() if x_col and x_col in plot_df.columns else []
                    values = plot_df[effective_y].tolist() if effective_y and effective_y in plot_df.columns else []

                    n_items = len(categories)
                    bar_colors = resolve_palette_colors(palette, max(n_items, 4))
                    if len(bar_colors) < n_items:
                        bar_colors = (bar_colors * (n_items // len(bar_colors) + 1))[:n_items]

                    y_positions = np.arange(n_items)
                    bar_height = 0.62

                    bars = ax.barh(
                        y_positions,
                        values,
                        height=bar_height,
                        color=bar_colors[:n_items],
                        edgecolor="none"
                    )

                    ax.set_yticks(y_positions)
                    ax.set_yticklabels(categories, fontsize=10, weight="bold", color=text_color)

                    max_val = max(values) if values and max(values) > 0 else 1
                    ax.set_xlim(0, max_val * 1.18)

                    # Direct crisp value labels on each bar tip
                    for bar, val in zip(bars, values):
                        w = bar.get_width()
                        y_pos = bar.get_y() + bar.get_height() / 2
                        ax.text(
                            w + (max_val * 0.02),
                            y_pos,
                            f"{format_num_human(val)}",
                            va="center",
                            ha="left",
                            fontsize=9.5,
                            weight="bold",
                            color=text_color
                        )

                    ax.set_xlabel(effective_y.replace("_", " ").title() if effective_y else "Value", fontsize=10, color=muted_color, labelpad=8)
                    ax.set_ylabel("")

        # --------------------------------------------------------------------------
        # Chart 2: Line Chart (Trends with smooth area glow & high-contrast points)
        # --------------------------------------------------------------------------
        elif chart_t in ["line", "trend"]:
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            colors = resolve_palette_colors(palette, 6)
            if safe_hue:
                sns.lineplot(data=sorted_df, x=x_col, y=effective_y, hue=safe_hue, marker="o", linewidth=2.8, palette=colors, ax=ax)
            else:
                line_color = colors[0]
                x_vals = sorted_df[x_col]
                y_vals = sorted_df[effective_y]
                
                # Area glow fill under line
                ax.fill_between(x_vals, y_vals, alpha=0.18, color=line_color)
                ax.plot(
                    x_vals, y_vals,
                    color=line_color,
                    linewidth=2.8,
                    marker="o",
                    markersize=6.5,
                    markeredgewidth=2,
                    markeredgecolor=bg_color
                )

        # --------------------------------------------------------------------------
        # Chart 3: Scatter Plot
        # --------------------------------------------------------------------------
        elif chart_t == "scatter":
            colors = resolve_palette_colors(palette, 8)
            n_rows = len(plot_df)
            point_size = 45 if n_rows > 1000 else 85
            alpha_val = 0.75 if n_rows > 1000 else 0.88

            if safe_hue and safe_hue in plot_df.columns:
                sns.scatterplot(
                    data=plot_df, x=x_col, y=effective_y, hue=safe_hue, s=point_size,
                    palette=colors, alpha=alpha_val, ax=ax,
                    edgecolor=bg_color, linewidth=0.8,
                    legend=show_legend
                )
            else:
                # Dynamically generate continuous palette colormap so Surprise Me & palette selection work 100%
                try:
                    cmap = plt.get_cmap(palette)
                except Exception:
                    cmap = mcolors.LinearSegmentedColormap.from_list(palette or "custom", colors, N=256)

                y_vals_num = pd.to_numeric(plot_df[effective_y], errors="coerce").fillna(0)
                sc = ax.scatter(
                    plot_df[x_col], plot_df[effective_y],
                    c=y_vals_num, cmap=cmap, s=point_size,
                    alpha=alpha_val, edgecolors=bg_color, linewidth=0.8,
                    zorder=3
                )
                cbar = fig.colorbar(sc, ax=ax, pad=0.02, fraction=0.035, aspect=24)
                cbar.outline.set_visible(False)
                cbar.ax.tick_params(labelsize=8.5, colors=muted_color, length=0)
                cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: format_num_human(v)))

        # --------------------------------------------------------------------------
        # Chart 4: Histogram
        # --------------------------------------------------------------------------
        elif chart_t in ["histogram", "hist"]:
            colors = resolve_palette_colors(palette, 4)
            if safe_hue:
                sns.histplot(data=plot_df, x=x_col, kde=True, hue=safe_hue, palette=colors, ax=ax)
            else:
                sns.histplot(
                    data=plot_df, x=x_col, kde=True, color=colors[0],
                    edgecolor=bg_color, alpha=0.65, ax=ax,
                    line_kws={"linewidth": 2.5, "color": colors[1] if len(colors) > 1 else "#06b6d4"}
                )

            # Label bars with exact counts matching 3D badges
            if hasattr(ax, "containers"):
                for container in ax.containers:
                    try:
                        ax.bar_label(
                            container,
                            fmt=lambda v: str(int(v)) if v > 0 else "",
                            padding=3,
                            fontsize=9,
                            weight="bold",
                            color=text_color
                        )
                    except Exception:
                        pass

        # --------------------------------------------------------------------------
        # Chart 5: Box Plot
        # --------------------------------------------------------------------------
        elif chart_t == "box":
            colors = resolve_palette_colors(palette, 8)
            if safe_hue:
                sns.boxplot(data=plot_df, x=x_col, y=effective_y, hue=safe_hue, palette=colors, ax=ax, width=0.48)
            else:
                sns.boxplot(data=plot_df, x=x_col, y=effective_y, hue=x_col, palette=colors, legend=False, ax=ax, width=0.48)

        # --------------------------------------------------------------------------
        # Chart 6: Heatmap (Correlation)
        # --------------------------------------------------------------------------
        elif chart_t in ["heatmap", "correlation"]:
            num_df = plot_df.select_dtypes(include=["number"])
            if num_df.shape[1] < 2:
                num_df = df.select_dtypes(include=["number"])
            corr = num_df.corr()
            if corr.empty or corr.shape[0] < 2:
                ax.text(0.5, 0.5, "Requires at least 2 numeric columns\nfor correlation heatmap",
                        ha="center", va="center", fontsize=12, weight="bold", color=text_color, transform=ax.transAxes)
            else:
                cmap_name = palette if palette in ["coolwarm", "viridis", "mako", "rocket", "plasma", "icefire", "crest"] else "coolwarm"
                sns.heatmap(
                    corr, annot=True, cmap=cmap_name, fmt=".2f",
                    linewidths=2.0, linecolor=bg_color, square=True,
                    ax=ax, cbar_kws={"shrink": 0.8},
                    vmin=-1.0, vmax=1.0,
                    annot_kws={"fontsize": 11, "weight": "bold"}
                )
                ax.tick_params(colors=text_color, labelsize=10)

        # --------------------------------------------------------------------------
        # Chart 7: Pie & Donut Chart (Sleek Modern Ring with Grand Total Center)
        # --------------------------------------------------------------------------
        elif chart_t in ["pie", "donut", "doughnut"]:
            # Ensure effective_y is a numeric measure if one exists in plot_df
            if not effective_y or effective_y == x_col or effective_y not in plot_df.columns or not pd.api.types.is_numeric_dtype(plot_df[effective_y]):
                num_candidates = [c for c in plot_df.columns if c != x_col and pd.api.types.is_numeric_dtype(plot_df[c])]
                if num_candidates:
                    effective_y = num_candidates[0]
                else:
                    effective_y = None

            if effective_y and effective_y in plot_df.columns:
                pie_data = plot_df.groupby(x_col)[effective_y].sum()
            elif x_col and x_col in plot_df.columns:
                pie_data = plot_df[x_col].value_counts()
            else:
                pie_data = plot_df.iloc[:, 0].value_counts()

            pie_data = pie_data[pie_data > 0]

            # If temporal/chronological (e.g. Car Year), sort chronologically!
            is_temp = is_temporal_column(x_col, plot_df[x_col] if (x_col and x_col in plot_df.columns) else None)
            if is_temp:
                pie_data = pie_data.sort_index(ascending=True)
                max_slices = 14  # show up to 14 years without hiding in 'Other'
            else:
                pie_data = pie_data.sort_values(ascending=False)
                max_slices = 8

            if len(pie_data) > max_slices:
                top_slices = pie_data.head(max_slices)
                other_val = pie_data.iloc[max_slices:].sum()
                pie_data = pd.concat([top_slices, pd.Series([other_val], index=["Other"])])

            if pie_data.empty:
                ax.text(0.5, 0.5, f"No positive values for {chart_t} chart", ha="center", va="center", color=text_color, transform=ax.transAxes)
            else:
                slice_colors = resolve_palette_colors(palette, len(pie_data))
                total_val = pie_data.sum()
                is_donut = chart_t in ["donut", "doughnut"]

                if is_donut:
                    # Modern Donut Ring with Center Hole & Grand Total Badge
                    wedges, texts, autotexts = ax.pie(
                        pie_data.values,
                        labels=pie_data.index,
                        autopct="%1.1f%%",
                        startangle=140,
                        colors=slice_colors,
                        pctdistance=0.76,
                        wedgeprops=dict(width=0.40, edgecolor=bg_color, linewidth=2.2),
                        textprops={"color": text_color, "fontsize": 9.5, "weight": "bold"}
                    )
                    center_txt = f"TOTAL\n{format_num_human(total_val)}" if isinstance(total_val, (int, float, np.number)) else "TOTAL"
                    ax.text(0, 0, center_txt, ha="center", va="center", fontsize=11, weight="bold", color=text_color)
                else:
                    # Classic Solid Modern Pie Chart (Full circle, no center hole)
                    wedges, texts, autotexts = ax.pie(
                        pie_data.values,
                        labels=pie_data.index,
                        autopct="%1.1f%%",
                        startangle=140,
                        colors=slice_colors,
                        pctdistance=0.68,
                        wedgeprops=dict(edgecolor=bg_color, linewidth=2.0),
                        textprops={"color": text_color, "fontsize": 9.5, "weight": "bold"}
                    )

                for at in autotexts:
                    at.set_color(text_color)
                    at.set_weight("bold")

                pie_slices = []
                for val, w, t, at, c in zip(pie_data.values, wedges, texts, autotexts, slice_colors):
                    pie_slices.append({
                        "label": str(t.get_text()),
                        "val": float(val),
                        "pct_str": str(at.get_text()).strip(),
                        "theta1": float(w.theta1),
                        "theta2": float(w.theta2),
                        "color": str(c)
                    })

        # --------------------------------------------------------------------------
        # Chart 8: Area Chart
        # --------------------------------------------------------------------------
        elif chart_t == "area":
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            colors = resolve_palette_colors(palette, 4)
            area_color = colors[0]
            ax.fill_between(sorted_df[x_col], sorted_df[effective_y], alpha=0.30, color=area_color)
            ax.plot(sorted_df[x_col], sorted_df[effective_y], color=area_color, linewidth=2.8, marker="o", markersize=5.5)

        # --------------------------------------------------------------------------
        # Chart 9: Violin Plot
        # --------------------------------------------------------------------------
        elif chart_t == "violin":
            colors = resolve_palette_colors(palette, 8)
            if safe_hue:
                sns.violinplot(data=plot_df, x=x_col, y=effective_y, hue=safe_hue, palette=colors, ax=ax)
            else:
                sns.violinplot(data=plot_df, x=x_col, y=effective_y, hue=x_col, palette=colors, legend=False, ax=ax)

        # --------------------------------------------------------------------------
        # Chart 10: Treemap
        # --------------------------------------------------------------------------
        elif chart_t == "treemap":
            MAX_ITEMS = 14

            if not HAS_SQUARIFY:
                ax.text(0.5, 0.5, "Squarify library not installed.\nRun: pip install squarify",
                        ha="center", va="center", color=text_color, transform=ax.transAxes)

            elif x_col not in plot_df.columns:
                ax.text(0.5, 0.5, f"Column '{x_col}' not found",
                        ha="center", va="center", color=text_color, transform=ax.transAxes)

            else:
                df_t = plot_df.dropna(subset=[x_col]).copy()
                df_t[x_col] = df_t[x_col].astype(str).str.strip()

                metric_name = "Count"
                if effective_y and effective_y in df_t.columns and effective_y != x_col:
                    df_t[effective_y] = (
                        pd.to_numeric(df_t[effective_y], errors="coerce")
                        .replace([np.inf, -np.inf], np.nan)
                    )
                    df_t = df_t.dropna(subset=[effective_y])
                    tree_data = df_t.groupby(x_col)[effective_y].sum().reset_index()
                    tree_data.columns = [x_col, "value"]
                    metric_name = f"Sum of {effective_y}"
                else:
                    tree_data = df_t[x_col].value_counts().reset_index()
                    tree_data.columns = [x_col, "value"]

                n_removed = int((tree_data["value"] <= 0).sum())
                tree_data = (tree_data[tree_data["value"] > 0]
                             .sort_values("value", ascending=False))

                if tree_data.empty:
                    ax.text(0.5, 0.5, "No positive values available for treemap",
                            ha="center", va="center", color=text_color, transform=ax.transAxes)
                else:
                    total = tree_data["value"].sum()
                    top = tree_data.head(MAX_ITEMS)
                    rest = tree_data.iloc[MAX_ITEMS:]

                    names = top[x_col].tolist()
                    sizes = top["value"].to_numpy()

                    if len(rest) > 0:
                        names.append(f"Others ({len(rest)})")
                        sizes = np.append(sizes, rest["value"].sum())

                    labels = [
                        f"{(n[:18] + '…') if len(n) > 18 else n}\n"
                        f"{format_num_human(v)} ({v / total:.1%})"
                        for n, v in zip(names, sizes)
                    ]

                    tree_colors = resolve_palette_colors(palette, len(sizes))

                    squarify.plot(
                        sizes=sizes,
                        label=labels,
                        color=tree_colors,
                        alpha=0.9,
                        bar_kwargs={"edgecolor": "#ffffff", "linewidth": 1.5},
                        text_kwargs={"fontsize": 9, "weight": "bold", "color": "#ffffff"},
                        ax=ax,
                    )
                    ax.axis("off")

                    note = f"{metric_name} by {x_col}"
                    if n_removed:
                        note += f" | {n_removed} non-positive group(s) excluded"
                    ax.text(0.5, -0.02, note, ha="center", va="top",
                            fontsize=8, color=text_color, transform=ax.transAxes)

        # --------------------------------------------------------------------------
        # Chart 11: Waterfall Chart
        # --------------------------------------------------------------------------
        elif chart_t == "waterfall":
            if effective_y and effective_y in plot_df.columns:
                w_df = plot_df.groupby(x_col, as_index=False)[effective_y].sum().head(12)
                categories = w_df[x_col].astype(str).tolist()
                values = w_df[effective_y].astype(float).tolist()
            else:
                counts = plot_df[x_col].value_counts().head(12)
                categories = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

            cumulative = [0]
            for val in values:
                cumulative.append(cumulative[-1] + val)

            bottoms = [min(cumulative[i], cumulative[i + 1]) for i in range(len(values))]
            heights = [abs(val) for val in values]

            pos_color, neg_color = "#10b981", "#ef4444"
            colors = [pos_color if val >= 0 else neg_color for val in values]
            bars = ax.bar(categories, heights, bottom=bottoms, color=colors, width=0.55, edgecolor="none")

            for i in range(len(values) - 1):
                ax.plot([i, i + 1], [cumulative[i + 1], cumulative[i + 1]], color=muted_color, linestyle="--", linewidth=1)

            for bar, val in zip(bars, values):
                y_text = bar.get_y() + bar.get_height() / 2
                ax.text(bar.get_x() + bar.get_width() / 2, y_text, format_num_human(val),
                        ha="center", va="center", color="#ffffff", fontsize=8.5, weight="bold")

            ax.set_ylabel(effective_y or "Value", fontsize=10, color=muted_color)

        # --------------------------------------------------------------------------
        # Chart 12: Funnel Chart
        # --------------------------------------------------------------------------
        elif chart_t == "funnel":
            is_horizontal_bar = True
            if effective_y and effective_y in plot_df.columns:
                funnel_df = plot_df.groupby(x_col, as_index=False)[effective_y].sum().sort_values(by=effective_y, ascending=False).head(10)
                stages = funnel_df[x_col].astype(str).tolist()
                values = funnel_df[effective_y].astype(float).tolist()
            else:
                counts = plot_df[x_col].value_counts().head(10)
                stages = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

            max_val = max(values) if values and max(values) > 0 else 1
            lefts = [(max_val - v) / 2 for v in values]
            f_colors = resolve_palette_colors(palette or "sunset", len(values))

            y_pos = list(range(len(stages)))
            bars = ax.barh(y_pos, values, left=lefts, color=f_colors, edgecolor="none", height=0.58, align="center")
            ax.set_yticks(y_pos)
            ax.set_yticklabels(stages, fontsize=9.5, weight="bold", color=text_color)
            ax.invert_yaxis()

            for v, bar in zip(values, bars):
                pct = (v / max_val) * 100
                ax.text(max_val / 2, bar.get_y() + bar.get_height() / 2, f"{format_num_human(v)} ({pct:.0f}%)",
                        ha="center", va="center", color="#ffffff", fontsize=9, weight="bold")
            ax.get_xaxis().set_visible(False)

        # --------------------------------------------------------------------------
        # Chart 13: Lollipop Chart
        # --------------------------------------------------------------------------
        elif chart_t == "lollipop":
            is_horizontal_bar = True
            if effective_y and effective_y in plot_df.columns:
                lolli_df = plot_df.groupby(x_col)[effective_y].sum().reset_index().sort_values(by=effective_y).tail(14)
                cats = lolli_df[x_col].astype(str).tolist()
                vals = lolli_df[effective_y].tolist()
            else:
                counts = plot_df[x_col].value_counts().sort_values().tail(14)
                cats = counts.index.astype(str).tolist()
                vals = counts.values.tolist()

            marker_c = resolve_palette_colors(palette, 1)[0]
            y_pos = list(range(len(cats)))
            ax.hlines(y=y_pos, xmin=0, xmax=vals, color=marker_c, alpha=0.55, linewidth=2.4)
            ax.scatter(vals, y_pos, color=marker_c, s=120, alpha=0.95, edgecolors=bg_color, linewidth=2, zorder=3)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(cats, fontsize=9.5, weight="bold", color=text_color)
            
            max_v = max(vals) if vals else 1
            ax.set_xlim(0, max_v * 1.15)
            for y, v in zip(y_pos, vals):
                ax.text(v + (max_v * 0.02), y, format_num_human(v), va="center", ha="left", fontsize=9, weight="bold", color=text_color)
            ax.set_xlabel(effective_y or "Count", fontsize=10, color=muted_color)

        # --------------------------------------------------------------------------
        # Chart 14: Radar / Spider Chart
        # --------------------------------------------------------------------------
        elif chart_t in ["radar", "spider"]:
            num_cols = plot_df.select_dtypes(include=["number"]).columns.tolist()
            if len(num_cols) >= 3:
                features = num_cols[:5]
                num_vars = len(features)
                angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
                angles += angles[:1]

                plot_rows = plot_df.head(3)
                cat_col = x_col if (x_col and x_col in plot_df.columns) else None
                r_colors = resolve_palette_colors(palette, len(plot_rows))

                scaled_vals = {}
                for col in features:
                    s = plot_df[col].astype(float)
                    c_min, c_max = float(s.min()), float(s.max())
                    if c_max > c_min:
                        scaled_vals[col] = (s - c_min) / (c_max - c_min) * 100
                    else:
                        scaled_vals[col] = pd.Series(50.0, index=plot_df.index)

                for idx, (_, row) in enumerate(plot_rows.iterrows()):
                    vals = [float(scaled_vals[f].loc[row.name]) for f in features]
                    vals += vals[:1]
                    lbl = str(row[cat_col]) if (cat_col and cat_col in plot_df.columns) else f"Row {idx + 1}"
                    ax.plot(angles, vals, linewidth=2.2, linestyle="solid", label=lbl, color=r_colors[idx])
                    ax.fill(angles, vals, color=r_colors[idx], alpha=0.22)

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(features, fontsize=9.5, weight="bold", color=text_color)
                ax.set_yticklabels([])
                ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8.5)
            else:
                colors = resolve_palette_colors(palette, 6)
                sns.barplot(data=plot_df.head(12), x=x_col, y=effective_y, palette=colors, ax=ax)
                # Polar bar styling: ensure circular rings, radial ticks, and theta labels are white
                ax.tick_params(axis='x', colors=text_color, labelsize=9.5)
                ax.tick_params(axis='y', colors=text_color, labelsize=8.5)
                for lbl in ax.get_xticklabels():
                    lbl.set_color(text_color)
                    lbl.set_fontweight("bold")
                for lbl in ax.get_yticklabels():
                    lbl.set_color(text_color)
                if ax.xaxis.label:
                    ax.xaxis.label.set_color(text_color)
                if ax.yaxis.label:
                    ax.yaxis.label.set_color(text_color)
                ax.grid(True, color=grid_line_color, linestyle="--", alpha=0.45)

        # --------------------------------------------------------------------------
        # Chart 15: Bubble Chart
        # --------------------------------------------------------------------------
        elif chart_t == "bubble":
            num_cols = plot_df.select_dtypes(include=["number"]).columns.tolist()
            size_candidates = [c for c in num_cols if c not in [x_col, effective_y]]
            size_col = size_candidates[0] if size_candidates else effective_y

            sizes = plot_df[size_col].abs() if size_col else plot_df[effective_y].abs()
            s_min, s_max = sizes.min(), sizes.max()
            scaled_sizes = 60 + ((sizes - s_min) / max(1e-5, (s_max - s_min))) * 450 if s_max > s_min else [140] * len(plot_df)

            effective_hue = hue_col if (hue_col and hue_col in plot_df.columns) else None
            colors = resolve_palette_colors(palette, 6)
            if effective_hue:
                sns.scatterplot(
                    data=plot_df, x=x_col, y=effective_y, hue=effective_hue, size=scaled_sizes,
                    sizes=(60, 450), palette=colors, alpha=0.82,
                    edgecolor=bg_color, linewidth=1, ax=ax, legend="brief"
                )
            else:
                bubble_color = colors[0]
                sns.scatterplot(
                    data=plot_df, x=x_col, y=effective_y, size=scaled_sizes, color=bubble_color,
                    sizes=(60, 450), alpha=0.82,
                    edgecolor=bg_color, linewidth=1, ax=ax, legend=False
                )
            title = f"{title} (Bubble Size: {size_col})"

        # Fallback
        else:
            is_horizontal_bar = True
            colors = resolve_palette_colors(palette, 8)
            sns.barplot(data=plot_df.head(12), x=x_col, y=effective_y, palette=colors, ax=ax)

        # --------------------------------------------------------------------------
        # Studio-Grade Matplotlib Finishing Touches (Clean Despine, Dynamic Grids)
        # --------------------------------------------------------------------------
        if chart_t not in ["radar", "spider", "treemap", "pie", "donut", "doughnut"]:
            if is_horizontal_bar:
                # Horizontal Bar aesthetic: vertical grid only, no border clutter
                sns.despine(ax=ax, top=True, right=True, left=True, bottom=False)
                ax.xaxis.grid(True, linestyle="--", alpha=0.3, color=grid_line_color)
                ax.yaxis.grid(False)
                ax.tick_params(left=False, bottom=True, colors=text_color, labelsize=9.5)
                ax.tick_params(axis='x', rotation=0)
                ax.tick_params(axis='y', rotation=0)
            elif chart_t in ["scatter", "bubble"]:
                # Scatter / coordinate plane: both horizontal and vertical grids
                sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
                show_grid = "ticks" not in selected_style
                ax.xaxis.grid(show_grid, linestyle="--", alpha=0.35, color=grid_line_color)
                ax.yaxis.grid(show_grid, linestyle="--", alpha=0.35, color=grid_line_color)
                ax.tick_params(colors=text_color, labelsize=9.5)
            else:
                # Vertical chart aesthetic: horizontal grid only
                sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
                show_grid = "ticks" not in selected_style
                ax.yaxis.grid(show_grid, linestyle="--", alpha=0.3, color=grid_line_color)
                ax.xaxis.grid(False)

                # Check if X-axis labels are long categories -> only then rotate
                x_labels = [str(l.get_text()) for l in ax.get_xticklabels()]
                has_long_labels = any(len(lbl) > 5 for lbl in x_labels) if x_labels else False
                rot = 25 if has_long_labels else 0

                ax.tick_params(axis='x', rotation=rot, colors=text_color, labelsize=9.5)
                ax.tick_params(axis='y', colors=text_color, labelsize=9.5)
                if rot > 0:
                    for lbl in ax.get_xticklabels():
                        lbl.set_ha('right')

        # Universal Text, Label & Tick Color Enforcement for All Chart Types
        all_axes = [ax] if not hasattr(fig, "axes") else fig.axes
        for axis_obj in all_axes:
            axis_obj.tick_params(colors=text_color, which='both')
            for lbl in axis_obj.get_xticklabels():
                lbl.set_color(text_color)
            for lbl in axis_obj.get_yticklabels():
                lbl.set_color(text_color)
            if axis_obj.xaxis.label:
                axis_obj.xaxis.label.set_color(text_color)
            if axis_obj.yaxis.label:
                axis_obj.yaxis.label.set_color(text_color)

        # Magazine / SaaS Typography Title
        ax.set_title(title, fontsize=13.5, weight="bold", color=text_color, pad=16, loc="left")

        leg = ax.get_legend()
        if leg and chart_t not in ["radar", "spider"]:
            leg.set_loc("upper right")
            leg.get_frame().set_facecolor(card_bg)
            leg.get_frame().set_edgecolor(grid_line_color)
            for text in leg.get_texts():
                text.set_color(text_color)
                text.set_fontsize(8.5)

        try:
            fig.tight_layout(pad=1.4)
        except Exception:
            pass

        # Capture exact plotted data so 3D chart elements match 2D chart data 100%
        try:
            chart_meta: Dict[str, Any] = {
                "chart_type": chart_t,
                "x_col": x_col,
                "y_col": effective_y,
                "title": title
            }
            if chart_t == "scatter":
                sample_pts = plot_df[[x_col, effective_y]].dropna()
                if len(sample_pts) > 150:
                    sample_pts = sample_pts.sample(n=150, random_state=42)
                x_vals_arr = sample_pts[x_col].to_numpy(dtype=float)
                y_vals_arr = sample_pts[effective_y].to_numpy(dtype=float)
                chart_meta["points"] = [
                    {"x": float(x), "y": float(y)}
                    for x, y in zip(x_vals_arr, y_vals_arr)
                ]
                chart_meta["min_x"] = float(plot_df[x_col].min())
                chart_meta["max_x"] = float(plot_df[x_col].max())
                chart_meta["min_y"] = float(plot_df[effective_y].min())
                chart_meta["max_y"] = float(plot_df[effective_y].max())
                chart_meta["data_points"] = [
                    {"label": f"({p['x']:.2f}, {p['y']:.2f})", "val": p["y"]}
                    for p in chart_meta["points"][:24]
                ]
            elif chart_t == "bubble":
                b_size_col = size_col if ('size_col' in locals() and size_col) else effective_y
                needed_cols = [x_col, effective_y]
                if b_size_col and b_size_col in plot_df.columns and b_size_col not in needed_cols:
                    needed_cols.append(b_size_col)
                sample_pts = plot_df[needed_cols].dropna()
                if len(sample_pts) > 150:
                    sample_pts = sample_pts.sample(n=150, random_state=42)
                x_vals_arr = sample_pts[x_col].to_numpy(dtype=float)
                y_vals_arr = sample_pts[effective_y].to_numpy(dtype=float)
                s_vals_arr = sample_pts[b_size_col].abs().to_numpy(dtype=float) if (b_size_col and b_size_col in sample_pts.columns) else y_vals_arr
                chart_meta["points"] = [
                    {"x": float(x), "y": float(y), "size": float(s)}
                    for x, y, s in zip(x_vals_arr, y_vals_arr, s_vals_arr)
                ]
                chart_meta["size_col"] = b_size_col
                chart_meta["min_x"] = float(plot_df[x_col].min())
                chart_meta["max_x"] = float(plot_df[x_col].max())
                chart_meta["min_y"] = float(plot_df[effective_y].min())
                chart_meta["max_y"] = float(plot_df[effective_y].max())
                chart_meta["min_size"] = float(s_vals_arr.min()) if len(s_vals_arr) > 0 else 1.0
                chart_meta["max_size"] = float(s_vals_arr.max()) if len(s_vals_arr) > 0 else 10.0
                chart_meta["data_points"] = [
                    {"label": f"({p['x']:.2f}, {p['y']:.2f})", "val": p["y"]}
                    for p in chart_meta["points"][:24]
                ]
            elif chart_t in ["bar", "column", "vertical_bar", "horizontal_bar"]:
                if 'categories' in locals() and 'values' in locals():
                    if is_horizontal_bar:
                        # 2D horizontal bar has categories ordered ascending for ax.barh (so highest is at top y=N-1).
                        # Reverse so that 3D bar chart (left-to-right) matches 2D top-to-bottom reading order.
                        chart_meta["data_points"] = [
                            {"label": str(c), "val": float(v)} for c, v in zip(categories[::-1], values[::-1])
                        ]
                    else:
                        # 2D vertical bar already has categories in chronological left-to-right order.
                        chart_meta["data_points"] = [
                            {"label": str(c), "val": float(v)} for c, v in zip(categories, values)
                        ]
                elif effective_y and effective_y in plot_df.columns and x_col and x_col in plot_df.columns:
                    grouped_p = plot_df.groupby(x_col, as_index=False)[effective_y].sum().head(16)
                    chart_meta["data_points"] = [
                        {"label": str(r[x_col]), "val": float(r[effective_y])} for _, r in grouped_p.iterrows()
                    ]
            elif chart_t in ["donut", "doughnut", "pie"]:
                if 'pie_slices' in locals() and pie_slices:
                    chart_meta["pie_slices"] = pie_slices
                    chart_meta["total_val"] = float(total_val) if 'total_val' in locals() else sum(s["val"] for s in pie_slices)
                    chart_meta["data_points"] = [
                        {"label": s["label"], "val": s["val"], "pct_str": s["pct_str"]} for s in pie_slices
                    ]
                elif 'pie_data' in locals() and not pie_data.empty:
                    chart_meta["data_points"] = [
                        {"label": str(k), "val": float(v)} for k, v in pie_data.items()
                    ]
                elif effective_y and effective_y in plot_df.columns and x_col and x_col in plot_df.columns:
                    grouped_p = plot_df.groupby(x_col, as_index=False)[effective_y].sum().head(8)
                    chart_meta["data_points"] = [
                        {"label": str(r[x_col]), "val": float(r[effective_y])} for _, r in grouped_p.iterrows()
                    ]
            elif chart_t == "treemap":
                if 'sizes' in locals() and 'labels' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(l).split('\n')[0], "val": float(s)} for l, s in zip(labels, sizes)
                    ]
                    if 'rects' in locals() and rects:
                        chart_meta["treemap_rects"] = [
                            {
                                "label": str(l).split('\n')[0],
                                "val": float(s),
                                "x": float(r['x']),
                                "y": float(r['y']),
                                "dx": float(r['dx']),
                                "dy": float(r['dy']),
                                "color": tree_colors[idx % len(tree_colors)] if 'tree_colors' in locals() else None
                            }
                            for idx, (r, s, l) in enumerate(zip(rects, sizes, labels))
                        ]
            elif chart_t == "waterfall":
                if 'categories' in locals() and 'values' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(c), "val": float(v)} for c, v in zip(categories, values)
                    ]
            elif chart_t == "funnel":
                if 'stages' in locals() and 'values' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(s), "val": float(v)} for s, v in zip(stages, values)
                    ]
                elif 'categories' in locals() and 'values' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(c), "val": float(v)} for c, v in zip(categories, values)
                    ]
            elif chart_t == "lollipop":
                if 'cats' in locals() and 'vals' in locals():
                    # Reverse so top-to-bottom in 2D matches left-to-right in 3D
                    chart_meta["data_points"] = [
                        {"label": str(c), "val": float(v)} for c, v in zip(cats[::-1], vals[::-1])
                    ]
                elif 'categories' in locals() and 'values' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(c), "val": float(v)} for c, v in zip(categories[::-1], values[::-1])
                    ]
            elif chart_t in ["line", "trend", "area"]:
                if 'sorted_df' in locals() and x_col and effective_y and x_col in sorted_df.columns and effective_y in sorted_df.columns:
                    s_sub = sorted_df[[x_col, effective_y]].dropna().head(40)
                    chart_meta["data_points"] = [
                        {"label": str(r[x_col]), "val": float(r[effective_y])}
                        for _, r in s_sub.iterrows()
                    ]
                elif 'x_vals' in locals() and 'y_vals' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(x), "val": float(y)} for x, y in zip(list(x_vals)[:40], list(y_vals)[:40])
                    ]
            elif chart_t in ["histogram", "hist"]:
                # Extract exact histogram bars rendered by Seaborn on ax so 3D matches 2D 100%
                hist_bins = []
                for p in ax.patches:
                    w = float(p.get_width())
                    if w > 0:
                        hist_bins.append({
                            "min": float(p.get_x()),
                            "max": float(p.get_x() + w),
                            "count": float(p.get_height())
                        })

                # Sort bins by min value
                hist_bins.sort(key=lambda b: b["min"])

                kde_curve = []
                if ax.lines:
                    try:
                        kx, ky = ax.lines[0].get_data()
                        if len(kx) > 0:
                            step = max(1, len(kx) // 30)
                            kde_curve = [
                                {"x": float(x), "y": float(y)}
                                for x, y in zip(kx[::step], ky[::step])
                            ]
                    except Exception:
                        pass

                chart_meta["bins"] = hist_bins
                chart_meta["kde"] = kde_curve
                if hist_bins:
                    chart_meta["min_x"] = float(min(b["min"] for b in hist_bins))
                    chart_meta["max_x"] = float(max(b["max"] for b in hist_bins))
                    chart_meta["max_count"] = float(max(b["count"] for b in hist_bins))
                    chart_meta["data_points"] = [
                        {"label": f"{format_num_human(b['min'])} - {format_num_human(b['max'])}", "val": b["count"]}
                        for b in hist_bins
                    ]
            elif chart_t in ["heatmap", "correlation"]:
                if 'corr' in locals() and not corr.empty and corr.shape[0] >= 2:
                    cols = list(corr.columns)
                    rows = list(corr.index)
                    matrix = []
                    for r_idx, r_name in enumerate(rows):
                        for c_idx, c_name in enumerate(cols):
                            val = float(corr.iloc[r_idx, c_idx])
                            val_rounded = round(val, 2) if not np.isnan(val) else 0.0
                            matrix.append({
                                "row": str(r_name),
                                "col": str(c_name),
                                "row_idx": r_idx,
                                "col_idx": c_idx,
                                "val": val_rounded
                            })
                    chart_meta["columns"] = cols
                    chart_meta["rows"] = rows
                    chart_meta["matrix"] = matrix
                    chart_meta["min_val"] = float(corr.min().min()) if not np.isnan(corr.min().min()) else -1.0
                    chart_meta["max_val"] = float(corr.max().max()) if not np.isnan(corr.max().max()) else 1.0
                    chart_meta["data_points"] = [
                        {"label": f"{m['row']} × {m['col']}", "val": m["val"]}
                        for m in matrix
                    ]
            elif chart_t == "box":
                boxes = []
                if x_col and effective_y and x_col in plot_df.columns and effective_y in plot_df.columns:
                    unique_cats = plot_df[x_col].dropna().unique()[:8]
                    for cat in unique_cats:
                        c_vals = plot_df[plot_df[x_col] == cat][effective_y].dropna().to_numpy(dtype=float)
                        if len(c_vals) > 0:
                            q1, med, q3 = np.percentile(c_vals, [25, 50, 75])
                            iqr = q3 - q1
                            min_val = float(np.min(c_vals))
                            max_val = float(np.max(c_vals))
                            lf = float(max(min_val, q1 - 1.5 * iqr))
                            uf = float(min(max_val, q3 + 1.5 * iqr))
                            outliers = [float(v) for v in c_vals if v < lf or v > uf][:10]
                            boxes.append({
                                "category": str(cat),
                                "min": min_val,
                                "q1": float(q1),
                                "median": float(med),
                                "q3": float(q3),
                                "max": max_val,
                                "lower_fence": lf,
                                "upper_fence": uf,
                                "outliers": outliers,
                                "count": len(c_vals)
                            })
                elif effective_y and effective_y in plot_df.columns:
                    c_vals = plot_df[effective_y].dropna().to_numpy(dtype=float)
                    if len(c_vals) > 0:
                        q1, med, q3 = np.percentile(c_vals, [25, 50, 75])
                        iqr = q3 - q1
                        min_val = float(np.min(c_vals))
                        max_val = float(np.max(c_vals))
                        lf = float(max(min_val, q1 - 1.5 * iqr))
                        uf = float(min(max_val, q3 + 1.5 * iqr))
                        outliers = [float(v) for v in c_vals if v < lf or v > uf][:10]
                        boxes.append({
                            "category": "Overall",
                            "min": min_val,
                            "q1": float(q1),
                            "median": float(med),
                            "q3": float(q3),
                            "max": max_val,
                            "lower_fence": lf,
                            "upper_fence": uf,
                            "outliers": outliers,
                            "count": len(c_vals)
                        })
                chart_meta["boxes"] = boxes
                chart_meta["data_points"] = [{"label": b["category"], "val": b["median"]} for b in boxes]
            elif chart_t == "violin":
                violins = []
                if x_col and effective_y and x_col in plot_df.columns and effective_y in plot_df.columns:
                    unique_cats = plot_df[x_col].dropna().unique()[:6]
                    for cat in unique_cats:
                        c_vals = plot_df[plot_df[x_col] == cat][effective_y].dropna().to_numpy(dtype=float)
                        if len(c_vals) > 0:
                            q1, med, q3 = np.percentile(c_vals, [25, 50, 75])
                            violins.append({
                                "category": str(cat),
                                "min": float(np.min(c_vals)),
                                "q1": float(q1),
                                "median": float(med),
                                "q3": float(q3),
                                "max": float(np.max(c_vals)),
                                "mean": float(np.mean(c_vals)),
                                "std": float(np.std(c_vals)) if len(c_vals) > 1 else 1.0,
                                "raw_sample": [float(v) for v in c_vals[:50]],
                                "count": len(c_vals)
                            })
                elif effective_y and effective_y in plot_df.columns:
                    c_vals = plot_df[effective_y].dropna().to_numpy(dtype=float)
                    if len(c_vals) > 0:
                        q1, med, q3 = np.percentile(c_vals, [25, 50, 75])
                        violins.append({
                            "category": "Overall",
                            "min": float(np.min(c_vals)),
                            "q1": float(q1),
                            "median": float(med),
                            "q3": float(q3),
                            "max": float(np.max(c_vals)),
                            "mean": float(np.mean(c_vals)),
                            "std": float(np.std(c_vals)) if len(c_vals) > 1 else 1.0,
                            "raw_sample": [float(v) for v in c_vals[:50]],
                            "count": len(c_vals)
                        })
                chart_meta["violins"] = violins
                chart_meta["data_points"] = [{"label": v["category"], "val": v["median"]} for v in violins]
            elif chart_t in ["radar", "spider"]:
                if 'features' in locals() and 'plot_rows' in locals():
                    cat_col = x_col if (x_col and x_col in plot_df.columns) else None
                    radar_series = []
                    for idx, (_, row) in enumerate(plot_rows.iterrows()):
                        lbl = str(row[cat_col]) if (cat_col and cat_col in plot_df.columns) else f"Row {idx + 1}"
                        s_vals = [float(scaled_vals[f].loc[row.name]) if f in scaled_vals else 50.0 for f in features]
                        raw_vals = [float(row[f]) if pd.api.types.is_numeric_dtype(type(row[f])) or str(row[f]).replace('.','',1).isdigit() else 0.0 for f in features]
                        radar_series.append({
                            "label": lbl,
                            "raw_values": raw_vals,
                            "norm_values": [v / 100.0 for v in s_vals]
                        })
                    chart_meta["radar"] = {
                        "features": features,
                        "series": radar_series
                    }
                    chart_meta["data_points"] = [
                        {"label": f"{f} ({radar_series[0]['label']})", "val": radar_series[0]['raw_values'][i]}
                        for i, f in enumerate(features)
                    ] if radar_series else []

            # Universal fallback for data_points if still missing
            if "data_points" not in chart_meta or not chart_meta["data_points"]:
                if effective_y and effective_y in plot_df.columns and x_col and x_col in plot_df.columns:
                    grouped_p = plot_df.groupby(x_col, as_index=False)[effective_y].sum().head(16)
                    chart_meta["data_points"] = [
                        {"label": str(r[x_col]), "val": float(r[effective_y])} for _, r in grouped_p.iterrows()
                    ]

            if unified_contract and isinstance(unified_contract, dict) and unified_contract.get("data_points"):
                LAST_CHART_DATA = unified_contract
            else:
                LAST_CHART_DATA = chart_meta
        except Exception:
            pass

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, facecolor=bg_color, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        if output_path and output_path != ":memory:":
            with open(output_path, "wb") as f:
                f.write(buf.getvalue())

        return data_url

    except Exception as e:
        plt.close("all")
        return f"Error generating chart: {str(e)}"
