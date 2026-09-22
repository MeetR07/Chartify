import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    fuzz = None
    HAS_RAPIDFUZZ = False

from profiler import get_dataset_schema

logger = logging.getLogger("chartify.planner")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Configurable constants
AMBIGUITY_DELTA_THRESHOLD = 0.10
AMBIGUITY_MIN_CONFIDENCE = 0.65
MAX_PLANNER_RETRIES = 3


def token_similarity(str1: str, str2: str) -> float:
    """Computes normalized similarity between 0.0 and 1.0 using rapidfuzz or token set overlap."""
    s1 = re.sub(r"[^\w\s]", "", str(str1).lower()).strip()
    s2 = re.sub(r"[^\w\s]", "", str(str2).lower()).strip()

    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    if HAS_RAPIDFUZZ and fuzz:
        return float(fuzz.token_sort_ratio(s1, s2) / 100.0)

    # Fallback token set overlap
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def check_column_ambiguity(query: str, schema: Dict[str, Any]) -> Tuple[bool, List[str], Optional[str]]:
    """
    Evaluates whether the user's query matches multiple columns with high, close confidence.
    Returns (is_ambiguous, candidate_columns, clarification_message).
    """
    clean_q = query.lower().strip()
    columns = schema.get("columns", [])
    if len(columns) <= 1:
        return False, [], None

    # Check if query references a generic or ambiguous term like "sales", "price", "count"
    # Find all columns that match any token in query
    q_tokens = [t for t in re.split(r"[^\w]+", clean_q) if len(t) >= 3 and t not in ["show", "chart", "plot", "view", "give", "each", "across", "data", "with", "from"]]

    for token in q_tokens:
        scores = []
        stem_token = token[:-1] if token.endswith("s") and len(token) > 3 else token
        for col in columns:
            col_lower = col.lower()
            col_words = [w.strip() for w in re.split(r"[^\w]+", col_lower) if w.strip()]
            col_stems = [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in col_words]

            sim = token_similarity(token, col)
            # Bonus if token or stem is an exact match to a column word or column stem
            if token == col_lower or token in col_words or stem_token in col_stems:
                sim = max(sim, 0.95)
            elif stem_token in col_lower or any(stem_token in w for w in col_words):
                sim = max(sim, 0.88)

            if sim >= AMBIGUITY_MIN_CONFIDENCE:
                scores.append((col, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        if len(scores) >= 2:
            top_col, top_score = scores[0]
            second_col, second_score = scores[1]
            if (top_score - second_score) <= AMBIGUITY_DELTA_THRESHOLD:
                # Ensure they are distinct columns
                if top_col != second_col:
                    msg = f"Your query mentions '{token}', which could refer to either '{top_col}' or '{second_col}'. Which column would you like to visualize?"
                    logger.info(f"[AMBIGUITY DETECTED] Token '{token}' matched '{top_col}' ({top_score:.2f}) and '{second_col}' ({second_score:.2f})")
                    return True, [top_col, second_col], msg

    return False, [], None


class PlanValidator:
    """Multi-layer pre-execution validation for structured QueryPlans."""

    @classmethod
    def validate_plan(cls, plan: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validates:
        1. All referenced columns exist in schema
        2. Aggregation is compatible with data type
        3. Grouping columns are categorical/dimension/date
        4. Post-aggregation ordering of Top-N
        """
        valid_cols = set(schema.get("columns", []))
        col_profiles = {cp["column"]: cp for cp in schema.get("column_profiles", [])}

        # Check steps
        steps = plan.get("steps", [])
        for step in steps:
            target_col = step.get("target_column")
            group_by = step.get("group_by", [])
            agg = (step.get("aggregation") or "sum").lower()
            op = step.get("operation")

            # Validate target_column existence
            if target_col and target_col not in valid_cols:
                # Suggest closest column
                closest = max(valid_cols, key=lambda c: token_similarity(target_col, c))
                return False, f"Column '{target_col}' does not exist in dataset.", {"suggested_fix": closest}

            # Validate group_by columns
            for g_col in group_by:
                if g_col not in valid_cols:
                    closest = max(valid_cols, key=lambda c: token_similarity(g_col, c))
                    return False, f"Grouping column '{g_col}' does not exist in dataset.", {"suggested_fix": closest}

            # Validate aggregation compatibility
            if op in ["group_aggregate", "groupby"] and agg in ["sum", "avg", "mean", "min", "max"]:
                if target_col and target_col in col_profiles:
                    c_type = col_profiles[target_col].get("logical_type")
                    if c_type not in ["numeric"]:
                        return False, f"Cannot compute {agg.upper()} on non-numeric column '{target_col}' (type: {c_type}).", None

        # Check filters
        filters = plan.get("filters", [])
        for f in filters:
            f_col = f.get("column")
            if f_col and f_col not in valid_cols:
                closest = max(valid_cols, key=lambda c: token_similarity(f_col, c))
                return False, f"Filter column '{f_col}' does not exist in dataset.", {"suggested_fix": closest}

        # Check sort
        sort_info = plan.get("sort")
        if sort_info and isinstance(sort_info, dict):
            s_col = sort_info.get("column")
            if s_col and s_col not in valid_cols and s_col != "count":
                # If target was aggregated, sort may be on aggregated metric
                pass

        return True, None, None


class RuleBasedFallbackPlanner:
    """
    Deterministic fast-path planner:
    Matches high-frequency, standard analytical query templates via regex.
    Guarantees zero-failure, instant query plan generation for standard patterns.
    """

    @classmethod
    def match_template(cls, query: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        clean_q = query.lower().strip()
        columns = schema.get("columns", [])
        measures = schema.get("candidate_measures", [])
        dimensions = schema.get("candidate_dimensions", []) + schema.get("candidate_dates", [])

        # Helper to find exact or fuzzy column mention in text
        def find_col(text: str, candidates: List[str]) -> Optional[str]:
            for c in candidates:
                c_low = c.lower()
                if c_low in text or c_low.replace("_", " ") in text:
                    return c
            # Fuzzy match
            best_c = None
            best_sim = 0.0
            for c in candidates:
                for token in text.split():
                    sim = token_similarity(token, c)
                    if sim > best_sim and sim >= 0.80:
                        best_sim = sim
                        best_c = c
            return best_c

        # Check for explicit chart orientation/type request in query
        explicit_chart = None
        if any(w in clean_q for w in ["vertical bar", "vertical", "column chart", "column", "standing bar", "upright"]):
            explicit_chart = {"explicit": True, "type": "column"}
        elif any(w in clean_q for w in ["horizontal bar", "horizontal"]):
            explicit_chart = {"explicit": True, "type": "horizontal_bar"}
        elif "pie" in clean_q:
            explicit_chart = {"explicit": True, "type": "pie"}
        elif "donut" in clean_q:
            explicit_chart = {"explicit": True, "type": "donut"}
        elif "scatter" in clean_q:
            explicit_chart = {"explicit": True, "type": "scatter"}
        elif "line" in clean_q:
            explicit_chart = {"explicit": True, "type": "line"}

        # Template 1: Top-N Ranking ("top 10 cities by revenue", "top 5 models by price")
        top_n_match = re.search(r"\btop\s+(\d+)\s+([a-zA-Z0-9_\s]+?)\s+(?:by|with highest|for)\s+([a-zA-Z0-9_\s]+)", clean_q)
        if top_n_match:
            limit = int(top_n_match.group(1))
            dim_text = top_n_match.group(2).strip()
            measure_text = top_n_match.group(3).strip()

            dim_col = find_col(dim_text, dimensions) or find_col(dim_text, columns)
            measure_col = find_col(measure_text, measures) or find_col(measure_text, columns)

            if dim_col and measure_col and dim_col != measure_col:
                return {
                    "intent": "ranking",
                    "steps": [{
                        "operation": "group_aggregate",
                        "group_by": [dim_col],
                        "target_column": measure_col,
                        "aggregation": "sum"
                    }],
                    "filters": [],
                    "sort": {"column": measure_col, "direction": "desc"},
                    "limit": limit,
                    "chart_request": explicit_chart or {"explicit": False, "type": "bar"},
                    "explanation": f"Ranked top {limit} {dim_col} by total {measure_col}"
                }

        # Template 2: Single-Measure Extreme/Ranking ("highest total_rooms", "top rooms", "lowest price")
        if not (" by " in clean_q or " per " in clean_q or " for each " in clean_q):
            extreme_match = re.search(r"\b(highest|top|maximum|largest|max|lowest|bottom|smallest|min)\s+([a-zA-Z0-9_\s]+)", clean_q)
            if extreme_match:
                direction = "desc" if extreme_match.group(1) in ["highest", "top", "maximum", "largest", "max"] else "asc"
                measure_text = extreme_match.group(2).strip()
                measure_col = find_col(measure_text, measures) or find_col(measure_text, columns)

                if measure_col:
                    return {
                        "intent": "ranking",
                        "steps": [],
                        "filters": [],
                        "sort": {"column": measure_col, "direction": direction},
                        "limit": 10,
                        "chart_request": {"explicit": False, "type": "bar"},
                        "explanation": f"Sorted {measure_col} in {direction}ending order without grouping"
                    }

        # Template 3: Distribution / Histogram ("distribution of profit", "spread of prices", "histogram of rooms")
        dist_match = re.search(r"\b(distribution|histogram|spread|frequency)\s+of\s+([a-zA-Z0-9_\s]+)", clean_q)
        if dist_match and not (" by " in clean_q or " per " in clean_q):
            measure_text = dist_match.group(2).strip()
            measure_col = find_col(measure_text, measures) or find_col(measure_text, columns)
            if measure_col:
                return {
                    "intent": "distribution",
                    "steps": [{
                        "operation": "distribution",
                        "target_column": measure_col
                    }],
                    "filters": [],
                    "sort": None,
                    "limit": None,
                    "chart_request": {"explicit": True, "type": "histogram"},
                    "explanation": f"Computed numeric distribution for {measure_col}"
                }

        # Template 4: Measure by Dimension ("total sales by month", "profit per region", "average salary across department")
        by_match = re.search(r"(?:total|sum|average|avg|mean|max|min|count)?\s*([a-zA-Z0-9_\s]+?)\s+(?:by|per|across|for each)\s+([a-zA-Z0-9_\s]+)", clean_q)
        if by_match:
            measure_text = by_match.group(1).strip()
            dim_text = by_match.group(2).strip()

            agg = "sum"
            if any(w in clean_q for w in ["average", "avg", "mean"]):
                agg = "avg"
            elif any(w in clean_q for w in ["max", "maximum", "highest"]):
                agg = "max"
            elif any(w in clean_q for w in ["min", "minimum", "lowest"]):
                agg = "min"
            elif any(w in clean_q for w in ["count", "how many"]):
                agg = "count"

            dim_col = find_col(dim_text, dimensions) or find_col(dim_text, columns)
            measure_col = find_col(measure_text, measures) or find_col(measure_text, columns)

            if dim_col:
                # If no measure found but query has "count" or "how many"
                if not measure_col and agg == "count":
                    return {
                        "intent": "aggregation",
                        "steps": [{
                            "operation": "group_aggregate",
                            "group_by": [dim_col],
                            "target_column": None,
                            "aggregation": "count"
                        }],
                        "filters": [],
                        "sort": {"column": "count", "direction": "desc"},
                        "limit": 16,
                        "chart_request": explicit_chart or {"explicit": False, "type": "bar"},
                        "explanation": f"Count of records grouped by {dim_col}"
                    }

                if measure_col and dim_col != measure_col:
                    is_temporal = dim_col in schema.get("candidate_dates", []) or any(t in dim_col.lower() for t in ["month", "year", "date", "quarter", "day"])
                    sort_spec = {"column": dim_col, "direction": "asc"} if is_temporal else {"column": measure_col, "direction": "desc"}
                    chart_t = "line" if is_temporal else "bar"
                    intent_str = "time_series" if is_temporal else "aggregation"
                    return {
                        "intent": intent_str,
                        "steps": [{
                            "operation": "group_aggregate",
                            "group_by": [dim_col],
                            "target_column": measure_col,
                            "aggregation": agg
                        }],
                        "filters": [],
                        "sort": sort_spec,
                        "limit": 16,
                        "chart_request": explicit_chart or {"explicit": False, "type": chart_t},
                        "explanation": f"{agg.capitalize()} of {measure_col} grouped by {dim_col}"
                    }

        # Template 5: Count of Category ("how many customers by city", "count of orders")
        count_match = re.search(r"\b(how many|count of|number of)\s+([a-zA-Z0-9_\s]+)", clean_q)
        if count_match and (" by " in clean_q or " per " in clean_q):
            parts = re.split(r"\s+(?:by|per)\s+", count_match.group(2).strip(), maxsplit=1)
            target_text = parts[0]
            dim_text = parts[1] if len(parts) > 1 else ""

            dim_col = find_col(dim_text, dimensions) or find_col(dim_text, columns)
            target_col = find_col(target_text, columns)

            if dim_col:
                return {
                    "intent": "aggregation",
                    "steps": [{
                        "operation": "group_aggregate",
                        "group_by": [dim_col],
                        "target_column": target_col,
                        "aggregation": "count"
                    }],
                    "filters": [],
                    "sort": {"column": "count", "direction": "desc"},
                    "limit": 16,
                    "chart_request": explicit_chart or {"explicit": False, "type": "bar"},
                    "explanation": f"Count of {target_col or 'items'} grouped by {dim_col}"
                }

        return None


class LLMQueryPlanner:
    """
    LLM Query Planner with Retry Loop and Rule-Based Fallback.
    """

    @classmethod
    def generate_plan(
        cls,
        query: str,
        df: pd.DataFrame,
        session_state: Optional[Dict[str, Any]] = None,
        llm_invoker=None
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Executes query planning:
        1. Check for Ambiguity
        2. Handle multi-turn follow-up modifications
        3. Try Rule-based Fallback fast-path
        4. Invoke LLM with retry loop and validation feedback
        """
        schema = get_dataset_schema(df)

        # 1. Ambiguity Detection
        is_ambig, candidates, ambig_msg = check_column_ambiguity(query, schema)
        if is_ambig:
            return {
                "clarification_needed": True,
                "ambiguity_type": "column",
                "options": candidates,
                "message": ambig_msg
            }, None

        # 2. Multi-turn Follow-Up Merge
        last_plan = session_state.get("last_plan") if session_state else None
        clean_q = query.lower().strip()
        is_follow_up = False
        if last_plan and (len(clean_q.split()) <= 4 or clean_q.startswith(("now ", "change to ", "only ", "by ", "in "))):
            is_follow_up = True
            logger.info(f"[MULTI-TURN] Follow-up query detected: '{query}'. Merging with previous plan.")

        # 3. Rule-based Fast-Path Planner
        rule_plan = RuleBasedFallbackPlanner.match_template(query, schema)
        if rule_plan:
            valid, err, _ = PlanValidator.validate_plan(rule_plan, schema)
            if valid:
                logger.info(f"[PLANNER] Fast-path rule matched for query: '{query}'")
                return rule_plan, {"model": "rule_based_fast_path"}

        # If follow-up, attempt delta merge on last plan
        if is_follow_up and last_plan:
            merged_plan = dict(last_plan)
            # Check if user specified a new dimension ("now by month", "by region")
            for c in schema.get("columns", []):
                if c.lower() in clean_q:
                    if merged_plan.get("steps"):
                        merged_plan["steps"][0]["group_by"] = [c]
                        merged_plan["explanation"] = f"Updated previous plan grouped by {c}"
                        return merged_plan, {"model": "session_follow_up_merge"}

        # 4. LLM Planner with Retry Loop
        if llm_invoker:
            prompt_context = {
                "schema": {
                    "columns": schema["columns"],
                    "candidate_dimensions": schema["candidate_dimensions"],
                    "candidate_measures": schema["candidate_measures"],
                    "candidate_dates": schema["candidate_dates"]
                },
                "query": query
            }

            error_feedback = None
            for attempt in range(MAX_PLANNER_RETRIES):
                try:
                    llm_plan = llm_invoker(query, prompt_context, error_feedback)
                    if llm_plan and isinstance(llm_plan, dict):
                        valid, err_msg, fix_meta = PlanValidator.validate_plan(llm_plan, schema)
                        if valid:
                            return llm_plan, {"model": "llm_planner", "attempts": attempt + 1}
                        else:
                            error_feedback = f"Plan validation failed on attempt {attempt+1}: {err_msg}. Available columns are: {schema['columns']}."
                            logger.warning(f"[PLANNER RETRY] {error_feedback}")
                except Exception as e:
                    error_feedback = f"LLM error: {str(e)}"

        # Default graceful fallback if all else fails
        fallback_metric = schema["candidate_measures"][0] if schema["candidate_measures"] else schema["columns"][0]
        fallback_dim = schema["candidate_dimensions"][0] if schema["candidate_dimensions"] else (schema["columns"][1] if len(schema["columns"]) > 1 else schema["columns"][0])

        default_plan = {
            "intent": "aggregation",
            "steps": [{
                "operation": "group_aggregate",
                "group_by": [fallback_dim] if fallback_dim != fallback_metric else [],
                "target_column": fallback_metric,
                "aggregation": "sum"
            }],
            "filters": [],
            "sort": {"column": fallback_metric, "direction": "desc"},
            "limit": 16,
            "chart_request": {"explicit": False, "type": "bar"},
            "explanation": f"Summarized {fallback_metric} across {fallback_dim}"
        }
        return default_plan, {"model": "default_schema_fallback"}
