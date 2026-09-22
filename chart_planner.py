import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from engine import compute_data_signature, sort_chronologically

logger = logging.getLogger("chartify.chart_planner")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class ChartPlanner:
    """
    Decoupled Chart Planner:
    Selects chart type based on final data shape and query intent.
    Data first, chart second.
    """

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
        requested_chart = (plan.get("chart_request", {}).get("type") or "").lower().strip()
        intent = (plan.get("intent") or "aggregation").lower()
        fallback_note = None

        group_col = exec_meta.get("primary_group_col")
        metric_col = exec_meta.get("primary_metric_col")
        n_rows = len(result_df)

        is_distribution = intent == "distribution" or "bins" in exec_meta
        is_chronological = False
        if group_col and group_col in result_df.columns:
            sorted_chrono = sort_chronologically(result_df.head(12), group_col)
            # If values were ordered chronologically
            is_chronological = any(m in str(result_df[group_col].iloc[0]).lower() for m in ["jan", "feb", "mar", "q1", "2020", "2021", "2022", "2023", "2024", "2025"])

        # 1. Evaluate Explicit User Request against Data Shape
        if requested_chart:
            # Pie / Donut Conflict Resolution: Needs <= 7 categories and positive values
            if requested_chart in ["pie", "donut", "doughnut"]:
                if n_rows > 7:
                    fallback_note = f"Switched from pie to bar chart because pie charts support up to 7 categories (found {n_rows})."
                    logger.info(f"[CHART CONFLICT] {fallback_note}")
                    return "bar", fallback_note

                if metric_col and metric_col in result_df.columns:
                    if (result_df[metric_col] < 0).any():
                        fallback_note = "Switched from pie to bar chart because pie charts cannot represent negative values."
                        logger.info(f"[CHART CONFLICT] {fallback_note}")
                        return "bar", fallback_note

                return requested_chart, None

            # Scatter Conflict Resolution: Needs 2 numeric columns
            if requested_chart == "scatter":
                num_cols = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
                if len(num_cols) < 2:
                    fallback_note = "Switched from scatter to bar chart because scatter plots require two numeric dimensions."
                    logger.info(f"[CHART CONFLICT] {fallback_note}")
                    return "bar", fallback_note
                return "scatter", None

            # Histogram Conflict Resolution
            if requested_chart in ["histogram", "hist"]:
                return "histogram", None

            # Other explicit allowed charts (line, bar, treemap, lollipop, waterfall, radar, area, violin, box)
            return requested_chart, None

        # 2. Data-First Inferred Selection
        if is_distribution:
            return "histogram", None

        if is_chronological or intent == "time_series":
            return "line", None

        if intent in ["ranking", "comparison", "aggregation"]:
            return "bar", None

        if intent == "share":
            if n_rows <= 7 and metric_col and (result_df[metric_col] >= 0).all():
                return "donut", None
            return "bar", None

        return "bar", None


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
    """
    group_col = exec_meta.get("primary_group_col")
    metric_col = exec_meta.get("primary_metric_col")

    # Fallback column detection if not explicitly set
    if not group_col:
        non_nums = [c for c in result_df.columns if not pd.api.types.is_numeric_dtype(result_df[c])]
        group_col = non_nums[0] if non_nums else result_df.columns[0]

    if not metric_col:
        nums = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
        metric_col = nums[0] if nums else (result_df.columns[1] if len(result_df.columns) > 1 else result_df.columns[0])

    x_categories = [str(v) for v in result_df[group_col].tolist()] if group_col in result_df.columns else []

    # Detect formatting
    col_format = "number"
    if any(q in str(metric_col).lower() for q in ["price", "sales", "revenue", "cost", "profit", "amount"]):
        col_format = "currency"
    elif "pct" in str(metric_col).lower() or "percentage" in str(metric_col).lower():
        col_format = "percentage"

    # Total sum for pie/part-to-whole
    total_sum = 0.0
    if metric_col in result_df.columns and pd.api.types.is_numeric_dtype(result_df[metric_col]):
        total_sum = float(result_df[metric_col].sum())

    # Build data points array
    data_points = []
    for idx, row in result_df.iterrows():
        raw_val = row[metric_col] if metric_col in result_df.columns else 0.0
        try:
            float_val = float(raw_val) if not pd.isna(raw_val) else 0.0
        except (ValueError, TypeError):
            float_val = 0.0

        label_str = str(row[group_col]) if group_col in result_df.columns else f"Item {idx + 1}"
        raw_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}

        data_points.append({
            "label": label_str,
            "val": float_val,
            "raw_row": raw_dict
        })

    # Generate data signature hash
    signature = compute_data_signature(
        data_points=data_points,
        query=plan.get("explanation", ""),
        metadata={"chart_type": chart_type, "group_col": group_col, "metric_col": metric_col}
    )

    contract = {
        "contract_version": "1.0",
        "data_signature": signature,
        "query": plan.get("explanation", ""),
        "intent": plan.get("intent", "aggregation"),
        "chart_type": chart_type,
        "fallback_note": fallback_note,
        "x_col": group_col,
        "y_col": metric_col,
        "hue_col": None,
        "axis_metadata": {
            "x_type": "categorical" if not any(c in str(group_col).lower() for c in ["date", "month", "year"]) else "temporal",
            "y_type": "numeric",
            "x_label": str(group_col),
            "y_label": str(metric_col),
            "x_categories": x_categories,
            "format": col_format
        },
        "chart_metadata": {
            "bins": exec_meta.get("bins"),
            "total_sum": round(total_sum, 2),
            "is_chronological": exec_meta.get("is_chronological", False)
        },
        "data_points": data_points
    }

    return contract
