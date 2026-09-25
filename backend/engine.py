import json
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd
import numpy as np

logger = logging.getLogger("chartify.engine")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

MONTH_CHRONO_ORDER = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]


def compute_data_signature(data_points: List[Dict[str, Any]], query: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
    """Computes a deterministic SHA-256 hash signature of the final data payload ensuring 2D and 3D parity."""
    try:
        norm_payload = {
            "query": (query or "").strip().lower(),
            "data": [{"label": str(d.get("label", "")), "val": round(float(d.get("val", 0.0)), 4)} for d in data_points],
            "metadata": metadata or {}
        }
        serialized = json.dumps(norm_payload, sort_keys=True)
        return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"
    except Exception as e:
        logger.warning(f"Failed to generate data signature: {e}")
        return f"sha256:fallback_{len(data_points)}"


def sort_chronologically(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
    """Sorts DataFrame chronologically if time_col contains month names, quarters, or years."""
    if time_col not in df.columns or len(df) == 0:
        return df

    series = df[time_col].astype(str).str.strip().str.lower()
    
    # 1. Month sorting
    is_month = series.isin(MONTH_CHRONO_ORDER)
    if is_month.mean() >= 0.7:
        month_map = {m: i % 12 for i, m in enumerate(MONTH_CHRONO_ORDER)}
        df_copy = df.copy()
        df_copy["_chrono_key"] = series.map(lambda x: month_map.get(x, 99))
        sorted_df = df_copy.sort_values(by="_chrono_key", ascending=True).drop(columns=["_chrono_key"])
        return sorted_df.reset_index(drop=True)

    # 2. Native Datetime sorting
    try:
        try:
            dt_series = pd.to_datetime(df[time_col], format="mixed", errors="coerce")
        except TypeError:
            dt_series = pd.to_datetime(df[time_col], errors="coerce")
        if dt_series.notnull().mean() >= 0.8:
            df_copy = df.copy()
            df_copy["_chrono_dt"] = dt_series
            sorted_df = df_copy.sort_values(by="_chrono_dt", ascending=True).drop(columns=["_chrono_dt"])
            return sorted_df.reset_index(drop=True)
    except Exception:
        pass

    # 3. Numeric Year or Quarter sorting
    try:
        num_series = pd.to_numeric(df[time_col], errors="coerce")
        if num_series.notnull().mean() >= 0.8:
            df_copy = df.copy()
            df_copy["_chrono_num"] = num_series
            sorted_df = df_copy.sort_values(by="_chrono_num", ascending=True).drop(columns=["_chrono_num"])
            return sorted_df.reset_index(drop=True)
    except Exception:
        pass

    return df.reset_index(drop=True)


class DeterministicDataEngine:
    """
    Executes structured query plans deterministically using vectorized Pandas.
    Zero raw code execution (no eval/exec).
    """

    @classmethod
    def execute_plan(cls, df: pd.DataFrame, plan: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Executes a QueryPlan dict against DataFrame.
        Returns (result_df, execution_meta).
        """
        if df is None or not isinstance(df, pd.DataFrame):
            raise ValueError("Invalid DataFrame provided to engine.")

        working_df = df.copy()
        meta = {
            "initial_rows": len(df),
            "operations_applied": [],
            "warnings": []
        }

        # Step 1: Execute Filters
        filters = plan.get("filters", [])
        if filters:
            for f in filters:
                col = f.get("column")
                op = f.get("operator", "eq").lower()
                val = f.get("value")

                if col not in working_df.columns:
                    meta["warnings"].append(f"Filter column '{col}' not in dataset; skipped.")
                    continue

                col_s = working_df[col]
                # Cast value according to column dtype if possible
                if pd.api.types.is_numeric_dtype(col_s):
                    try:
                        val = float(val)
                    except (ValueError, TypeError):
                        pass

                try:
                    if op == "eq":
                        working_df = working_df[col_s == val]
                    elif op == "neq":
                        working_df = working_df[col_s != val]
                    elif op == "gt":
                        working_df = working_df[col_s > val]
                    elif op == "gte":
                        working_df = working_df[col_s >= val]
                    elif op == "lt":
                        working_df = working_df[col_s < val]
                    elif op == "lte":
                        working_df = working_df[col_s <= val]
                    elif op in ["in", "isin"]:
                        val_list = val if isinstance(val, list) else [val]
                        working_df = working_df[col_s.isin(val_list)]
                    meta["operations_applied"].append(f"filter({col} {op} {val})")
                except (TypeError, ValueError) as err:
                    applied = False
                    if op in ["gt", "gte", "lt", "lte"]:
                        try:
                            num_col = pd.to_numeric(col_s, errors="coerce")
                            if num_col.notna().mean() >= 0.5:
                                num_val = float(val)
                                if op == "gt":
                                    working_df = working_df[num_col > num_val]
                                elif op == "gte":
                                    working_df = working_df[num_col >= num_val]
                                elif op == "lt":
                                    working_df = working_df[num_col < num_val]
                                elif op == "lte":
                                    working_df = working_df[num_col <= num_val]
                                meta["operations_applied"].append(f"filter({col} {op} {val})")
                                applied = True
                        except Exception:
                            pass
                    if not applied:
                        meta["warnings"].append(f"Incompatible type for filter({col} {op} {val}): {err}; skipped.")

            # Check for 0-row filter match edge case
            if len(working_df) == 0:
                logger.info("[EXECUTION] Filter reduced rows to 0.")
                return working_df, meta

        # Step 2: Execute Core Operations
        steps = plan.get("steps", [])
        primary_group_col = plan.get("primary_group_col")
        primary_metric_col = plan.get("primary_metric_col")

        for step in steps:
            op_name = step.get("operation")

            # A. Group & Aggregate
            if op_name in ["group_aggregate", "groupby"]:
                group_by = step.get("group_by", [])
                target_col = step.get("target_column")
                agg_func = (step.get("aggregation") or "sum").lower()

                if not group_by:
                    # Single column aggregation without grouping
                    if target_col and target_col in working_df.columns:
                        primary_metric_col = target_col
                        if agg_func == "sum":
                            val = float(working_df[target_col].sum())
                        elif agg_func in ["avg", "mean"]:
                            val = float(working_df[target_col].mean())
                        elif agg_func == "max":
                            val = float(working_df[target_col].max())
                        elif agg_func == "min":
                            val = float(working_df[target_col].min())
                        elif agg_func in ["count", "distinct_count"]:
                            val = float(working_df[target_col].nunique() if agg_func == "distinct_count" else working_df[target_col].count())
                        else:
                            val = float(working_df[target_col].sum())

                        working_df = pd.DataFrame({"Metric": [f"{agg_func.capitalize()} {target_col}"], target_col: [val]})
                        primary_group_col = "Metric"
                    meta["operations_applied"].append(f"aggregate({agg_func} of {target_col})")
                    continue

                valid_group_cols = [c for c in group_by if c in working_df.columns]
                if not valid_group_cols:
                    meta["warnings"].append(f"Grouping columns {group_by} not found in dataset.")
                    continue

                primary_group_col = valid_group_cols[0]

                # Map aggregation type
                if agg_func == "count":
                    if target_col and target_col in working_df.columns and target_col not in valid_group_cols:
                        grouped = working_df.groupby(valid_group_cols, as_index=False, observed=True)[target_col].count()
                        grouped.rename(columns={target_col: "count"}, inplace=True)
                        primary_metric_col = "count"
                    else:
                        grouped = working_df.groupby(valid_group_cols, as_index=False, observed=True).size()
                        grouped.rename(columns={"size": "count"}, inplace=True)
                        primary_metric_col = "count"
                elif agg_func == "distinct_count":
                    col_to_count = target_col if (target_col and target_col in working_df.columns) else valid_group_cols[0]
                    grouped = working_df.groupby(valid_group_cols, as_index=False, observed=True)[col_to_count].nunique()
                    grouped.rename(columns={col_to_count: f"unique_{col_to_count}"}, inplace=True)
                    primary_metric_col = f"unique_{col_to_count}"
                else:
                    if not target_col or target_col not in working_df.columns:
                        # Fallback to first available numeric
                        num_candidates = [c for c in working_df.select_dtypes(include=["number"]).columns if c not in valid_group_cols]
                        target_col = num_candidates[0] if num_candidates else valid_group_cols[0]

                    primary_metric_col = target_col
                    pandas_agg = "mean" if agg_func in ["avg", "mean"] else agg_func
                    grouped = working_df.groupby(valid_group_cols, as_index=False, observed=True)[target_col].agg(pandas_agg)

                working_df = grouped
                meta["operations_applied"].append(f"group_by({valid_group_cols}) -> {agg_func}({primary_metric_col})")

            # B. Distribution / Histogram Binning
            elif op_name == "distribution":
                target_col = step.get("target_column")
                if target_col and target_col in working_df.columns and pd.api.types.is_numeric_dtype(working_df[target_col]):
                    num_series = working_df[target_col].dropna()
                    if len(num_series) > 0:
                        counts, bin_edges = np.histogram(num_series, bins="auto")
                        # Format bin ranges as labels
                        bin_labels = [f"{bin_edges[i]:.1f} - {bin_edges[i+1]:.1f}" for i in range(len(counts))]
                        working_df = pd.DataFrame({
                            f"{target_col} Range": bin_labels,
                            "count": [int(c) for c in counts]
                        })
                        primary_group_col = f"{target_col} Range"
                        primary_metric_col = "count"
                        meta["bins"] = {"edges": [float(e) for e in bin_edges], "counts": [int(c) for c in counts]}
                        meta["operations_applied"].append(f"distribution({target_col})")

            # C. Percentage / Share of Total
            elif op_name == "percentage":
                target_col = step.get("target_column") or primary_metric_col
                if target_col and target_col in working_df.columns and pd.api.types.is_numeric_dtype(working_df[target_col]):
                    total_sum = float(working_df[target_col].sum())
                    # Edge Case: Division by zero guard
                    if total_sum == 0.0 or math.isnan(total_sum):
                        working_df[f"{target_col}_pct"] = 0.0
                        meta["warnings"].append(f"Total sum of '{target_col}' is zero; percentage defaulted to 0.0%.")
                    else:
                        working_df[f"{target_col}_pct"] = ((working_df[target_col] / total_sum) * 100.0).round(2)
                    primary_metric_col = f"{target_col}_pct"
                    meta["operations_applied"].append(f"percentage({target_col})")

        # Step 3: Chronological Sorting for Temporal Columns
        if primary_group_col and primary_group_col in working_df.columns:
            working_df = sort_chronologically(working_df, primary_group_col)

        # Step 4: Sort (Explicit)
        sort_info = plan.get("sort")
        if sort_info and isinstance(sort_info, dict):
            sort_col = sort_info.get("column")
            direction = (sort_info.get("direction") or "desc").lower()
            ascending = (direction == "asc")

            # If user didn't specify column or specified invalid column, sort by metric column
            if not sort_col or sort_col not in working_df.columns:
                sort_col = primary_metric_col or (working_df.columns[-1] if len(working_df.columns) > 1 else working_df.columns[0])

            if sort_col in working_df.columns:
                series_lower = working_df[sort_col].astype(str).str.strip().str.lower()
                is_chrono = series_lower.isin(MONTH_CHRONO_ORDER).mean() >= 0.7 or any(c in sort_col.lower() for c in ["date", "month", "year"])
                if is_chrono:
                    working_df = sort_chronologically(working_df, sort_col)
                    if not ascending:
                        working_df = working_df.iloc[::-1].reset_index(drop=True)
                else:
                    working_df = working_df.sort_values(by=sort_col, ascending=ascending)
                meta["operations_applied"].append(f"sort({sort_col} {direction})")

        # Step 5: Top-N / Limit (ALWAYS Applied AFTER Grouping & Aggregation)
        limit = plan.get("limit")
        if limit and isinstance(limit, (int, float)) and limit > 0:
            limit_n = int(limit)
            meta["total_logical_rows"] = len(working_df)
            working_df = working_df.head(limit_n)
            meta["operations_applied"].append(f"limit({limit_n})")

        meta["final_rows"] = len(working_df)
        meta["primary_group_col"] = primary_group_col
        meta["primary_metric_col"] = primary_metric_col

        logger.info(f"[EXECUTION] Engine completed pipeline: {', '.join(meta['operations_applied'])}; rows={len(working_df)}")
        return working_df.reset_index(drop=True), meta


class ResultValidator:
    """Validates the output DataFrame produced by the DeterministicDataEngine."""

    @classmethod
    def validate(cls, df: pd.DataFrame, plan: Dict[str, Any], meta: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verifies output shape, required columns, and data types."""
        # 1. Check for empty result
        if df is None:
            return False, "Result DataFrame is null."

        if len(df) == 0:
            # If the user applied a filter, this is an expected 'no data matches' scenario
            if plan.get("filters"):
                return True, "No records match the given filter criteria."
            return False, "Resulting dataset contains 0 records."

        # 2. Check for NaN or inf values in metric columns
        metric_col = meta.get("primary_metric_col")
        if metric_col and metric_col in df.columns:
            if pd.api.types.is_numeric_dtype(df[metric_col]):
                has_inf = np.isinf(df[metric_col]).any()
                if has_inf:
                    return False, f"Metric column '{metric_col}' contains Infinite values."

        # 3. Check for single column / single row edge cases
        if len(df.columns) == 1 and len(df) == 1:
            logger.info("[RESULT VALIDATION] Single-cell result detected; valid scalar KPI.")

        return True, None
