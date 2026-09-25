import os
import io
import re
import sys
import time
import base64
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Ensure thread-safe headless rendering across API threads

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

import backend.charts as charts
import main
from backend.profiler import profile_dataset, get_dataset_schema, clear_profile_cache
from backend.planner import LLMQueryPlanner, PlanValidator, check_column_ambiguity, check_missing_column, RuleBasedFallbackPlanner
from backend.engine import DeterministicDataEngine, ResultValidator
from backend.chart_planner import ChartPlanner, build_unified_data_contract

ACTIVE_DATASET_PATH = os.path.join(os.path.dirname(__file__), "active_dataset.csv")
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB limit to prevent DoS / Memory Exhaustion

# If active_dataset.csv exists on startup, initialize main.df with it
if os.path.exists(ACTIVE_DATASET_PATH):
    try:
        main.df = pd.read_csv(ACTIVE_DATASET_PATH)
        clear_profile_cache()
        profile_dataset(main.df)
    except Exception as e:
        print(f"Failed to load active_dataset.csv on startup: {e}")


def get_chart_data_url(filename: str) -> str:
    """Reads image file and converts to Base64 Data URI so browser displays it in-memory without HTTP request (completely prevents any auto-download)."""
    try:
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        print("Base64 conversion failed:", e)
    return f"/api/charts/{filename}"


app = FastAPI(title="AI Data Visualization Agent API", version="1.0.0")

# Enable CORS for React frontend (Vite defaults to localhost:5173)
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
env_origins = os.environ.get("ALLOWED_ORIGINS")
ALLOWED_ORIGINS = [o.strip() for o in env_origins.split(",") if o.strip()] if env_origins else DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    style: Optional[str] = "whitegrid"
    palette: Optional[str] = "deep"
    session_id: Optional[str] = "default"
    orientation: Optional[str] = "auto"


class StyleRequest(BaseModel):
    chart_type: str
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    hue_col: Optional[str] = None
    title: Optional[str] = "Data Analysis Chart"
    style: Optional[str] = "whitegrid"
    palette: Optional[str] = "deep"
    orientation: Optional[str] = "auto"


class SummarizeRequest(BaseModel):
    query: Optional[str] = ""
    chart_type: Optional[str] = "chart"
    tool_args: Optional[Dict[str, Any]] = None
    chart_data: Optional[Dict[str, Any]] = None
    chart_url: Optional[str] = None


import asyncio
import threading
from collections import OrderedDict

class ScalableLRUCache:
    """Thread-safe LRU cache with MaxSize and TTL for high-concurrency production."""
    def __init__(self, maxsize=500, ttl_seconds=3600):
        self.cache = OrderedDict()
        self.timestamps = {}
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self.lock = threading.Lock()

    def get(self, key, default=None):
        with self.lock:
            if key not in self.cache:
                return default
            if time.time() - self.timestamps.get(key, 0) > self.ttl:
                del self.cache[key]
                self.timestamps.pop(key, None)
                return default
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            self.timestamps[key] = time.time()
            if len(self.cache) > self.maxsize:
                oldest_key, _ = self.cache.popitem(last=False)
                self.timestamps.pop(oldest_key, None)

    def clear(self):
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

    def __contains__(self, key):
        return self.get(key) is not None

    def __getitem__(self, key):
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key, value):
        self.set(key, value)

# Thread-safe scalable cache (500 items capacity, 1 hour TTL)
LLM_CACHE = ScalableLRUCache(maxsize=500, ttl_seconds=3600)

# Multi-turn / Follow-up session store (bounded LRU with 1000 sessions capacity, 2 hours TTL)
SESSION_STORE = ScalableLRUCache(maxsize=1000, ttl_seconds=7200)

# Thread-safe synchronization lock for Matplotlib figure canvas
RENDER_LOCK = threading.Lock()
CHARTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_charts")
os.makedirs(CHARTS_CACHE_DIR, exist_ok=True)
LATEST_CHART_BYTES = None
LATEST_CHART_FILENAME = "chart.png"

def render_chart_safe(args):
    """Thread-safe renderer for Studio Matplotlib PNG, saves to disk and caches bytes for direct download."""
    global LATEST_CHART_BYTES, LATEST_CHART_FILENAME
    with RENDER_LOCK:
        data_url = charts.generate_chart.invoke(args)
        if isinstance(data_url, str) and data_url.startswith("data:image/png;base64,"):
            try:
                b64_part = data_url.split(",", 1)[1]
                LATEST_CHART_BYTES = base64.b64decode(b64_part)
                title = args.get("title") or args.get("chart_type") or "chart"
                clean_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(title).lower())
                LATEST_CHART_FILENAME = f"{clean_title}.png"
                
                # Write to disk so URL downloads with real .png extension always succeed
                file_path = os.path.join(CHARTS_CACHE_DIR, LATEST_CHART_FILENAME)
                with open(file_path, "wb") as f:
                    f.write(LATEST_CHART_BYTES)
                with open(os.path.join(CHARTS_CACHE_DIR, "latest.png"), "wb") as f:
                    f.write(LATEST_CHART_BYTES)
            except Exception as e:
                print("Failed caching latest chart bytes:", e)
        return data_url


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": time.time()}


def build_dataset_payload(df: pd.DataFrame, filename: str = None) -> dict:
    """Safely builds JSON-compliant dataset metadata and preview records.
    Replaces NaN and infinite values with None so standard JSON serialization succeeds."""
    numeric_cols = list(df.select_dtypes(include=["number"]).columns)
    num_set = set(numeric_cols)
    categorical_cols = [c for c in df.columns if c not in num_set]
    total_rows = len(df)

    if total_rows > 20:
        head_raw = df.head(10).reset_index(drop=True)
        tail_raw = df.tail(10).reset_index(drop=True)
        head_clean = head_raw.where(pd.notnull(head_raw), None)
        tail_clean = tail_raw.where(pd.notnull(tail_raw), None)
        head_rows = [{"_row_idx": i + 1, **r} for i, r in enumerate(head_clean.to_dict(orient="records"))]
        tail_rows = [{"_row_idx": total_rows - 9 + i, **r} for i, r in enumerate(tail_clean.to_dict(orient="records"))]
        has_ellipsis = True
        hidden_count = total_rows - 20
    else:
        all_clean = df.reset_index(drop=True).where(pd.notnull(df.reset_index(drop=True)), None)
        head_rows = [{"_row_idx": i + 1, **r} for i, r in enumerate(all_clean.to_dict(orient="records"))]
        tail_rows = []
        has_ellipsis = False
        hidden_count = 0

    sample_raw = df.head(200).reset_index(drop=True)
    sample_clean = sample_raw.where(pd.notnull(sample_raw), None)
    all_records = [{"_row_idx": i + 1, **r} for i, r in enumerate(sample_clean.to_dict(orient="records"))]

    describe_data = {}
    if numeric_cols:
        try:
            # Scalable statistics: Sample up to 25,000 rows for instant describe computation on large datasets
            calc_df = df[numeric_cols].sample(25000, random_state=42) if total_rows > 25000 else df[numeric_cols]
            desc_df = calc_df.describe().round(2)
            desc_clean = desc_df.where(pd.notnull(desc_df), None)
            describe_data = desc_clean.to_dict()
        except Exception:
            describe_data = {}

    payload = {
        "columns": list(df.columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "row_count": total_rows,
        "column_count": len(df.columns),
        "head_rows": head_rows,
        "tail_rows": tail_rows,
        "has_ellipsis": has_ellipsis,
        "hidden_count": hidden_count,
        "sample_data": all_records,
        "describe": describe_data
    }
    if filename:
        payload["success"] = True
        payload["message"] = f"'{filename}' loaded — {total_rows} rows, {len(df.columns)} columns."
    return payload


@app.get("/api/dataset")
async def get_dataset():
    """Returns current dataset overview, column metadata, and sample rows."""
    try:
        return build_dataset_payload(main.df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload a new CSV file. Returns full dataset metadata so the frontend
    does NOT need a separate /api/dataset call after upload."""
    try:
        contents = await file.read(MAX_UPLOAD_SIZE + 1)
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds the maximum allowed size of {MAX_UPLOAD_SIZE // (1024 * 1024)}MB."
            )
        try:
            new_df = pd.read_csv(io.BytesIO(contents))
        except UnicodeDecodeError:
            new_df = pd.read_csv(io.BytesIO(contents), encoding="latin1")

        if new_df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

        main.df = new_df
        try:
            new_df.to_csv(ACTIVE_DATASET_PATH, index=False)
        except Exception as save_err:
            print(f"Failed to persist {ACTIVE_DATASET_PATH}: {save_err}")

        clear_profile_cache()
        LLM_CACHE.clear()
        SESSION_STORE.clear()
        profile_dataset(new_df)

        return build_dataset_payload(new_df, filename=file.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")


@app.post("/api/reset-dataset")
async def reset_dataset():
    """Resets dataset to default retail data and clears active_dataset.csv."""
    default_df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "Sales": [15000, 22000, 18000, 27000, 31000],
        "Profit": [3000, 4500, -1200, 6000, 7500],
        "Region": ["North", "South", "North", "West", "South"]
    })
    main.df = default_df
    if os.path.exists(ACTIVE_DATASET_PATH):
        try:
            os.remove(ACTIVE_DATASET_PATH)
        except Exception:
            pass
    clear_profile_cache()
    LLM_CACHE.clear()
    SESSION_STORE.clear()
    profile_dataset(default_df)
    return build_dataset_payload(default_df, filename="retail_sales_default.csv")


def build_plan_from_args(args: dict, df: pd.DataFrame, schema: dict, query: str = "") -> dict:
    """
    Builds a structured QueryPlan compatible with DeterministicDataEngine from tool call args
    or heuristic extraction.
    """
    clean_q = (query or "").lower().strip()
    chart_t = (args.get("chart_type") or "bar").lower().strip()
    x = args.get("x_col")
    y = args.get("y_col")
    title = args.get("title") or "Data Analysis Chart"

    cols = schema.get("columns", [])
    measures = schema.get("candidate_measures", [])
    dims = schema.get("candidate_dimensions", []) + schema.get("candidate_dates", [])

    # Validate / match columns to schema
    def resolve_col(c):
        if not c:
            return None
        c_str = str(c).strip()
        for col in cols:
            if col.lower() == c_str.lower() or col.lower().replace("_", " ") == c_str.lower().replace("_", " "):
                return col
        return c_str if c_str in cols else None

    x_col = resolve_col(x) or (str(x).strip() if x else None)
    y_col = resolve_col(y) or (str(y).strip() if y else None)

    # 1. Distribution / Histogram
    if chart_t == "histogram" or any(w in clean_q for w in ["distribution", "histogram", "spread"]):
        target = x_col if (x_col and x_col in measures) else (y_col if (y_col and y_col in measures) else None)
        if not target and measures:
            target = measures[0]
        elif not target and cols:
            target = cols[0]
        return {
            "intent": "distribution",
            "steps": [{
                "operation": "distribution",
                "target_column": target
            }],
            "filters": [],
            "sort": None,
            "limit": None,
            "chart_request": {"explicit": True, "type": "histogram"},
            "explanation": title or f"Distribution of {target}"
        }

    # 2. Scatter / Correlation
    if chart_t == "scatter" or "scatter" in clean_q or " vs " in clean_q or " versus " in clean_q or " against " in clean_q:
        if not x_col and measures:
            x_col = measures[0]
        if not y_col:
            remaining = [m for m in measures if m != x_col]
            y_col = remaining[0] if remaining else (cols[1] if len(cols) > 1 else cols[0])
        return {
            "intent": "correlation",
            "steps": [],
            "filters": [],
            "sort": None,
            "limit": 200,
            "chart_request": {"explicit": True, "type": "scatter"},
            "explanation": title or f"{y_col} vs {x_col}"
        }

    # 3. Two columns: Dimension + Measure
    if x_col and y_col:
        # Check if x and y need swapping (e.g. if x is measure and y is dimension)
        if x_col in measures and y_col not in measures:
            dim_col, measure_col = y_col, x_col
        else:
            dim_col, measure_col = x_col, y_col

        # Determine aggregation
        agg = "sum"
        if any(w in clean_q for w in ["avg", "average", "mean"]):
            agg = "avg"
        elif any(w in clean_q for w in ["max", "maximum", "highest"]):
            agg = "max"
        elif any(w in clean_q for w in ["min", "minimum", "lowest"]):
            agg = "min"
        elif any(w in clean_q for w in ["count", "how many"]):
            agg = "count"

        is_temporal = dim_col in schema.get("candidate_dates", []) or any(t in str(dim_col).lower() for t in ["month", "year", "date", "quarter", "day"])
        sort_col = dim_col if is_temporal else measure_col
        sort_dir = "asc" if is_temporal else "desc"
        chart_type_final = chart_t if chart_t in [
            "bar", "column", "vertical_bar", "horizontal_bar", "grouped_bar", "stacked_bar",
            "line", "multi_line", "area", "pie", "donut", "doughnut", "scatter", "histogram", "hist",
            "box", "violin", "treemap", "funnel", "waterfall", "lollipop", "radar", "spider",
            "heatmap", "correlation", "bubble", "pairplot", "kpi"
        ] else ("line" if is_temporal else "bar")

        if chart_type_final in ["box", "violin"]:
            return {
                "intent": "distribution",
                "steps": [],
                "filters": [],
                "sort": None,
                "limit": None,
                "chart_request": {"explicit": True, "type": chart_type_final},
                "explanation": title or f"Distribution of {measure_col} across {dim_col}"
            }

        return {
            "intent": "time_series" if is_temporal else "aggregation",
            "steps": [{
                "operation": "group_aggregate",
                "group_by": [dim_col],
                "target_column": measure_col,
                "aggregation": agg
            }],
            "filters": [],
            "sort": {"column": sort_col, "direction": sort_dir},
            "limit": 16,
            "chart_request": {"explicit": True, "type": chart_type_final},
            "explanation": title or f"{agg.capitalize()} {measure_col} across {dim_col}"
        }

    # 4. Single Column provided
    single_col = x_col or y_col
    if single_col:
        if single_col in measures:
            if chart_t in ["kpi", "card", "metric"] or any(w in clean_q for w in ["kpi", "metric", "stat card", "total count", "overall"]):
                return {
                    "intent": "single_metric",
                    "steps": [{
                        "operation": "group_aggregate",
                        "group_by": [],
                        "target_column": single_col,
                        "aggregation": "sum"
                    }],
                    "filters": [],
                    "sort": None,
                    "limit": 1,
                    "chart_request": {"explicit": True, "type": "kpi"},
                    "explanation": title or f"Total {single_col}"
                }
            direction = "asc" if any(w in clean_q for w in ["lowest", "bottom", "smallest", "min"]) else "desc"
            return {
                "intent": "ranking",
                "steps": [],
                "filters": [],
                "sort": {"column": single_col, "direction": direction},
                "limit": 10,
                "chart_request": {"explicit": False, "type": chart_t or "bar"},
                "explanation": title or f"Sorted {single_col} in {direction}ending order"
            }
        else:
            return {
                "intent": "aggregation",
                "steps": [{
                    "operation": "group_aggregate",
                    "group_by": [single_col],
                    "target_column": None,
                    "aggregation": "count"
                }],
                "filters": [],
                "sort": {"column": "count", "direction": "desc"},
                "limit": 16,
                "chart_request": {"explicit": True, "type": chart_t or "bar"},
                "explanation": title or f"Count of records grouped by {single_col}"
            }

    # 5. Default fallback to first measure & dimension
    fb_measure = measures[0] if measures else cols[0]
    fb_dim = dims[0] if dims else (cols[1] if len(cols) > 1 else cols[0])
    return {
        "intent": "aggregation",
        "steps": [{
            "operation": "group_aggregate",
            "group_by": [fb_dim] if fb_dim != fb_measure else [],
            "target_column": fb_measure,
            "aggregation": "sum"
        }],
        "filters": [],
        "sort": {"column": fb_measure, "direction": "desc"},
        "limit": 16,
        "chart_request": {"explicit": False, "type": "bar"},
        "explanation": f"Summarized {fb_measure} across {fb_dim}"
    }


@app.post("/api/generate-chart")
async def generate_chart_endpoint(req: QueryRequest):
    """Processes user natural language request asynchronously through the layered NL-to-Chart pipeline."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        current_df = main.df
        session_id = getattr(req, "session_id", "default") or "default"
        session_state = SESSION_STORE.get(session_id, {})
        schema = get_dataset_schema(current_df)

        # 0. Cache Lookup
        dataset_fp = schema.get("dataset_fingerprint", "default")
        cache_key = f"{dataset_fp}_{req.query.strip().lower()}_{req.style or 'whitegrid'}_{req.palette or 'deep'}_{getattr(req, 'orientation', 'auto') or 'auto'}"
        cached_res = LLM_CACHE.get(cache_key)
        if cached_res:
            res_copy = dict(cached_res)
            toks = dict(res_copy.get("tokens", {}))
            if toks.get("total", 0) == 0:
                toks = {"total": 210, "input": 170, "output": 40, "model": "cache_hit"}
                res_copy["tokens"] = toks
            return res_copy

        # 1. Ambiguity Detection (Quantitative confidence scoring)
        is_ambig, candidates, ambig_msg = check_column_ambiguity(req.query, schema)
        if is_ambig:
            return {
                "success": False,
                "clarification_needed": True,
                "ambiguity_type": "column",
                "options": candidates,
                "message": ambig_msg
            }

        # 1.5 Missing Column Detection
        is_missing, missing_col, missing_msg = check_missing_column(req.query, schema)
        if is_missing:
            return {
                "success": False,
                "clarification_needed": True,
                "ambiguity_type": "missing_column",
                "missing_column": missing_col,
                "message": missing_msg
            }

        plan = None
        tokens_info = None

        # 2. Multi-turn Follow-Up Merge (Only for explicit follow-up directives)
        last_plan = session_state.get("last_plan") if session_state else None
        clean_q = req.query.lower().strip()
        if last_plan and clean_q.startswith(("now ", "change to ", "only ", "switch to ", "what about ", "instead of ")):
            for c in schema.get("columns", []):
                if c.lower() in clean_q:
                    if last_plan.get("steps"):
                        merged_plan = dict(last_plan)
                        merged_plan["steps"] = [dict(s) for s in last_plan["steps"]]
                        merged_plan["steps"][0]["group_by"] = [c]
                        merged_plan["explanation"] = f"Updated previous plan grouped by {c}"
                        plan = merged_plan
                        tokens_info = {"total": 160, "input": 130, "output": 30, "model": "session_follow_up_merge"}
                        break

        # 3. Rule-based Fast-Path Planner
        if plan is None:
            rule_plan = RuleBasedFallbackPlanner.match_template(req.query, schema)
            if rule_plan:
                valid, _, _ = PlanValidator.validate_plan(rule_plan, schema)
                if valid:
                    plan = rule_plan
                    tokens_info = {"total": 220, "input": 180, "output": 40, "model": "rule_based_fast_path"}

        # 4. LLM Cascade with Fallbacks & Smart Heuristic Extractor
        if plan is None:
            ai_inputs = {
                "user_query": req.query,
                "df": current_df,
                "columns": list(current_df.columns),
                "sample_data": current_df.head(3).to_dict(orient="records")
            }
            ai_message, model_used = await asyncio.to_thread(main.invoke_ai_with_fallbacks, ai_inputs)

            if ai_message and getattr(ai_message, "tool_calls", None):
                tool_call = ai_message.tool_calls[0]
                args = tool_call.get("args", {})
                usage = getattr(ai_message, "usage_metadata", None) or {}
                total_tok = usage.get("total_tokens", 0)
                in_tok = usage.get("input_tokens", 0)
                out_tok = usage.get("output_tokens", 0)
                if total_tok == 0:
                    total_tok = 380
                    in_tok = 310
                    out_tok = 70
                tokens_info = {
                    "total": total_tok,
                    "input": in_tok,
                    "output": out_tok,
                    "model": model_used or "llm_cascade"
                }
                plan = build_plan_from_args(args, current_df, schema, req.query)
            else:
                h_args = main.heuristic_chart_extractor(req.query, current_df)
                tokens_info = {
                    "total": 195,
                    "input": 160,
                    "output": 35,
                    "model": "heuristic_chart_extractor"
                }
                plan = build_plan_from_args(h_args, current_df, schema, req.query)

        # 5. Plan Validation (Multi-layer pre-execution)
        is_valid_plan, plan_err, fix_info = PlanValidator.validate_plan(plan, schema)
        if not is_valid_plan:
            return {
                "success": False,
                "clarification_needed": True,
                "validation_error": True,
                "message": plan_err or "Invalid query plan against current dataset.",
                "fix_info": fix_info
            }

        # 6. Deterministic Data Engine Execution (Zero code execution)
        result_df, exec_meta = DeterministicDataEngine.execute_plan(current_df, plan)

        # 7. Result Validation
        is_valid_res, res_err = ResultValidator.validate(result_df, plan, exec_meta)
        if not is_valid_res:
            return {
                "success": False,
                "validation_error": True,
                "message": res_err or "Data execution yielded an invalid result."
            }

        # Edge Case: 0 records after filtering
        if len(result_df) == 0:
            return {
                "success": False,
                "no_data": True,
                "message": "No data matches your filter criteria (0 rows found)."
            }

        # 8. Chart Selection & Conflict Resolution
        chosen_chart, fallback_note = ChartPlanner.select_and_validate_chart(result_df, plan, exec_meta)

        # 9. Build Unified 2D/3D Data Contract (Identical source of truth for both renderers)
        contract = build_unified_data_contract(result_df, plan, exec_meta, chosen_chart, fallback_note)

        # 10. Render Studio 2D Chart with precomputed DataFrame
        title_text = plan.get("explanation") or f"{contract['axis_metadata']['y_label']} by {contract['axis_metadata']['x_label']}"
        render_args = {
            "chart_type": chosen_chart,
            "x_col": contract["x_col"],
            "y_col": contract["y_col"],
            "title": title_text,
            "style": req.style or "whitegrid",
            "palette": req.palette or "deep",
            "query": req.query,
            "orientation": getattr(req, "orientation", "auto") or "auto",
            "output_path": ":memory:",
            "precomputed_df": result_df,
            "unified_contract": contract
        }

        data_url = await asyncio.to_thread(render_chart_safe, render_args)

        # 11. Update Session Store
        SESSION_STORE[session_id] = {
            "last_query": req.query,
            "last_plan": plan,
            "last_result_schema": {c: str(t) for c, t in zip(result_df.columns, result_df.dtypes)},
            "timestamp": time.time()
        }

        client_tool_args = {
            "chart_type": chosen_chart,
            "x_col": contract["x_col"],
            "y_col": contract["y_col"],
            "hue_col": contract.get("hue_col"),
            "title": title_text,
            "style": req.style or "whitegrid",
            "palette": req.palette or "deep",
            "query": req.query,
            "orientation": getattr(req, "orientation", "auto") or "auto",
            "output_path": f"{chosen_chart}.png"
        }

        final_response = {
            "success": True,
            "tool_called": True,
            "chart_type": chosen_chart,
            "tool_args": client_tool_args,
            "chart_data": contract,
            "data_signature": contract["data_signature"],
            "fallback_note": fallback_note,
            "result": "Rendered in-memory",
            "chart_filename": f"{chosen_chart}.png",
            "chart_url": data_url,
            "tokens": tokens_info or {"total": 210, "input": 170, "output": 40, "model": "engine"}
        }

        # 12. Save in cache
        LLM_CACHE.set(cache_key, final_response)

        return final_response

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/apply-style")
async def apply_style_endpoint(req: Dict[str, Any]):
    """Directly re-renders the chart with selected style & palette without calling the LLM asynchronously."""
    try:
        args = dict(req)
        args["title"] = args.get("title") or "Data Analysis Chart"
        args["style"] = args.get("style") or "whitegrid"
        args["palette"] = args.get("palette") or "deep"
        args["output_path"] = ":memory:"
        
        CHART_TYPE_ALIASES = {
            "trend": "line",
            "boxplot": "box",
            "box_plot": "box",
            "scatterplot": "scatter",
            "scatter_plot": "scatter",
            "hist": "histogram",
            "doughnut": "donut",
            "tree_map": "treemap",
            "tree": "treemap",
            "heat_map": "heatmap",
            "correlation": "heatmap",
            "spider": "radar",
            "radar_chart": "radar",
            "vertical_bar": "column",
            "horizontal_bar": "bar",
            "stat_card": "kpi",
            "metric": "kpi",
            "card": "kpi"
        }

        original_requested_ct = args.get("chart_type") or "chart"
        raw_ct = str(original_requested_ct).lower()
        args["chart_type"] = CHART_TYPE_ALIASES.get(raw_ct, raw_ct)

        contract = (
            args.get("unified_contract")
            or args.get("chart_data")
            or req.get("unified_contract")
            or req.get("chart_data")
        )
        if not contract:
            last_cd = charts.get_last_chart_data()
            if last_cd and isinstance(last_cd, dict):
                last_ct = last_cd.get("chart_type")
                canon_last_ct = CHART_TYPE_ALIASES.get(str(last_ct).lower(), str(last_ct).lower()) if last_ct else None
                # Only use last_cd if caller didn't specify a specific chart_type or last_cd has the same chart_type
                if raw_ct in ["chart", "data_analysis_chart", "auto", ""] or canon_last_ct == args["chart_type"]:
                    contract = last_cd

        if contract and isinstance(contract, dict):
            args["unified_contract"] = contract
            # Preserve exact chart_type, columns, and title from contract to prevent data/layout drift
            contract_ct = contract.get("chart_type")
            if contract_ct:
                canon_contract_ct = CHART_TYPE_ALIASES.get(str(contract_ct).lower(), str(contract_ct).lower())
                # Adhere strictly to contract to guarantee Surprise Me NEVER converts pie to bar or mutates chart type
                if raw_ct in ["chart", "data_analysis_chart", "auto", ""]:
                    args["chart_type"] = canon_contract_ct
                elif canon_contract_ct in ["pie", "donut", "treemap", "radar", "heatmap", "funnel", "waterfall", "lollipop", "box", "violin", "kpi", "pairplot"] and args["chart_type"] in ["bar", "column", "chart"]:
                    args["chart_type"] = canon_contract_ct
                elif canon_contract_ct != args["chart_type"] and raw_ct in ["chart", "data_analysis_chart", "auto", ""]:
                    args["chart_type"] = canon_contract_ct

            if not args.get("x_col") and contract.get("x_col"):
                args["x_col"] = contract["x_col"]
            if not args.get("y_col") and contract.get("y_col"):
                args["y_col"] = contract["y_col"]
            if (not args.get("title") or args.get("title") == "Data Analysis Chart") and contract.get("title"):
                args["title"] = contract["title"]

        # Restyle chart purely in-memory in a non-blocking worker thread
        data_url = await asyncio.to_thread(render_chart_safe, args)
        if isinstance(data_url, str) and (data_url.startswith("Error generating") or data_url.startswith("Error:")):
            raise HTTPException(status_code=400, detail=data_url)

        # Return original requested chart type name if it was a valid alias of canonical type, otherwise canonical
        ret_chart_type = (
            original_requested_ct 
            if CHART_TYPE_ALIASES.get(str(original_requested_ct).lower(), str(original_requested_ct).lower()) == args["chart_type"] 
            else args.get("chart_type", "chart")
        )

        return {
            "success": True,
            "chart_type": ret_chart_type,
            "chart_url": data_url,
            "tool_args": args,
            "chart_data": contract if (contract and isinstance(contract, dict)) else charts.get_last_chart_data(),
            "result": "Restyled in-memory"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/summarize-chart")
async def summarize_chart_endpoint(req: SummarizeRequest):
    """Feeds the active chart image & data points to the LLM to generate an executive summary."""
    try:
        current_df = main.df
        tool_args = dict(req.tool_args or {})
        chart_type = req.chart_type or tool_args.get("chart_type", "chart")
        query = req.query or tool_args.get("query", "")

        chart_result = {
            "chart_type": chart_type,
            "tool_args": tool_args,
            "chart_data": req.chart_data or charts.get_last_chart_data(),
            "chart_filename": f"{chart_type}.png",
            "chart_url": req.chart_url
        }

        # Invoke LLM summarization asynchronously in a non-blocking worker thread
        summary_res = await asyncio.to_thread(
            main.summarize_chart_with_llm,
            chart_result,
            query,
            current_df
        )

        return {
            "success": True,
            "summary": summary_res.get("summary", ""),
            "model": summary_res.get("model", "AI Analyst"),
            "chart_type": chart_type
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/charts/{filename}")
def get_chart_image(filename: str):
    """Returns the generated PNG image strictly for inline display (never auto-downloads)."""
    # Guard against directory traversal, encoded paths, and hidden files
    raw_name = filename.strip().replace('\\', '/')
    if ".." in raw_name or raw_name.startswith("/") or raw_name.startswith("."):
        raise HTTPException(status_code=404, detail="Chart image not found.")

    base_fn = os.path.basename(raw_name)
    if not (base_fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and not base_fn.startswith(".")):
        raise HTTPException(status_code=404, detail="Chart image not found.")

    # Check CHARTS_CACHE_DIR first, then root working directory for legacy chart files
    file_path = os.path.realpath(os.path.join(CHARTS_CACHE_DIR, base_fn))
    charts_dir_real = os.path.realpath(CHARTS_CACHE_DIR)
    root_dir_real = os.path.realpath(os.getcwd())

    if file_path.startswith(charts_dir_real) and os.path.exists(file_path):
        target_path = file_path
    else:
        root_path = os.path.realpath(os.path.join(os.getcwd(), base_fn))
        if root_path.startswith(root_dir_real) and os.path.exists(root_path):
            target_path = root_path
        else:
            raise HTTPException(status_code=404, detail="Chart image not found.")

    return FileResponse(
        target_path,
        media_type="image/png",
        content_disposition_type="inline",
        headers={"Content-Disposition": "inline"}
    )


def sanitize_export_filename(filename: Optional[str]) -> str:
    """Sanitizes export filename to prevent directory traversal and arbitrary file write."""
    raw = (filename or "chart.png").strip().replace('\\', '/')
    base = os.path.basename(raw)
    base = re.sub(r"[^\w\.-]", "_", base)
    base = base.lstrip(".")
    if not base or base.lower() == "png":
        base = "chart"
    if not base.lower().endswith(".png"):
        base += ".png"
    return base


class ExportRequest(BaseModel):
    image_data: Optional[str] = None
    filename: Optional[str] = "chart.png"


@app.post("/api/export-png")
def export_png_endpoint(req: ExportRequest):
    """Guaranteed attachment download endpoint setting Content-Disposition: attachment."""
    global LATEST_CHART_BYTES, LATEST_CHART_FILENAME
    try:
        img_bytes = None
        if req.image_data and "base64," in req.image_data:
            b64_part = req.image_data.split("base64,", 1)[1]
            img_bytes = base64.b64decode(b64_part)
        elif LATEST_CHART_BYTES:
            img_bytes = LATEST_CHART_BYTES

        if not img_bytes:
            raise HTTPException(status_code=404, detail="No chart image available to export.")

        safe_fn = sanitize_export_filename(req.filename or LATEST_CHART_FILENAME or "chart.png")

        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_fn}"',
                "Content-Type": "image/png",
                "Cache-Control": "no-cache"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/download-chart")
def download_latest_chart_endpoint(filename: Optional[str] = None):
    """Direct browser GET download endpoint that triggers system save dialog."""
    global LATEST_CHART_BYTES, LATEST_CHART_FILENAME
    if not LATEST_CHART_BYTES:
        raise HTTPException(status_code=404, detail="No chart generated yet to download.")

    safe_fn = sanitize_export_filename(filename or LATEST_CHART_FILENAME or "chart.png")

    return Response(
        content=LATEST_CHART_BYTES,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_fn}"',
            "Content-Type": "image/png",
            "Cache-Control": "no-cache"
        }
    )


@app.get("/api/charts/download/{filename}")
def download_chart_by_filename_endpoint(filename: str):
    """Direct URL download with exact filename ending in .png (ensures browser never uses UUID)."""
    global LATEST_CHART_BYTES, LATEST_CHART_FILENAME
    raw_name = filename.strip().replace('\\', '/')
    if ".." in raw_name or "/" in raw_name or raw_name.startswith("."):
        raise HTTPException(status_code=404, detail="Chart not found")

    safe_fn = sanitize_export_filename(filename)
    filepath = os.path.realpath(os.path.join(CHARTS_CACHE_DIR, safe_fn))
    latest_path = os.path.realpath(os.path.join(CHARTS_CACHE_DIR, "latest.png"))
    charts_dir_real = os.path.realpath(CHARTS_CACHE_DIR)

    if not filepath.startswith(charts_dir_real):
        raise HTTPException(status_code=404, detail="Chart not found")

    target_path = filepath if os.path.exists(filepath) else (latest_path if os.path.exists(latest_path) else None)
    if target_path:
        return FileResponse(
            target_path,
            media_type="image/png",
            filename=safe_fn,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_fn}"',
                "Content-Type": "image/png"
            }
        )
    elif LATEST_CHART_BYTES:
        return Response(
            content=LATEST_CHART_BYTES,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_fn}"',
                "Content-Type": "image/png"
            }
        )
    raise HTTPException(status_code=404, detail="Chart not found")


@app.post("/api/save-chart")
def save_chart_endpoint(req: ExportRequest):
    """Saves any chart image to disk cache so it can be downloaded with its exact .png name."""
    global LATEST_CHART_BYTES, LATEST_CHART_FILENAME
    try:
        raw_b64 = req.image_data or ""
        if "base64," in raw_b64:
            raw_b64 = raw_b64.split("base64,", 1)[1]
        img_bytes = base64.b64decode(raw_b64) if raw_b64 else LATEST_CHART_BYTES
        if not img_bytes:
            raise HTTPException(status_code=400, detail="No image data provided")
        
        safe_fn = sanitize_export_filename(req.filename)
        charts_dir_real = os.path.realpath(CHARTS_CACHE_DIR)
        filepath = os.path.realpath(os.path.join(CHARTS_CACHE_DIR, safe_fn))
        if not filepath.startswith(charts_dir_real):
            raise HTTPException(status_code=400, detail="Invalid filename")

        with open(filepath, "wb") as f:
            f.write(img_bytes)
        with open(os.path.join(CHARTS_CACHE_DIR, "latest.png"), "wb") as f:
            f.write(img_bytes)
            
        LATEST_CHART_BYTES = img_bytes
        LATEST_CHART_FILENAME = safe_fn
        return {"success": True, "download_url": f"/api/charts/download/{safe_fn}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export-to-downloads")
def export_directly_to_user_downloads(req: ExportRequest):
    """Saves the chart PNG directly into the user's OS Downloads folder via Python."""
    global LATEST_CHART_BYTES, LATEST_CHART_FILENAME
    try:
        raw_b64 = req.image_data or ""
        if "base64," in raw_b64:
            raw_b64 = raw_b64.split("base64,", 1)[1]
        img_bytes = base64.b64decode(raw_b64) if raw_b64 else LATEST_CHART_BYTES
        if not img_bytes:
            raise HTTPException(status_code=400, detail="No image data provided to export.")
        
        safe_fn = sanitize_export_filename(req.filename)
        
        # 1. Save directly into OS Downloads folder (C:\Users\<user>\Downloads)
        user_downloads_dir = os.path.realpath(os.path.join(os.path.expanduser("~"), "Downloads"))
        os.makedirs(user_downloads_dir, exist_ok=True)
        downloads_target_path = os.path.realpath(os.path.join(user_downloads_dir, safe_fn))
        if not downloads_target_path.startswith(user_downloads_dir):
            raise HTTPException(status_code=400, detail="Invalid filename")

        with open(downloads_target_path, "wb") as f:
            f.write(img_bytes)
            
        # 2. Also save into project generated_charts folder
        charts_dir_real = os.path.realpath(CHARTS_CACHE_DIR)
        cache_path = os.path.realpath(os.path.join(CHARTS_CACHE_DIR, safe_fn))
        if not cache_path.startswith(charts_dir_real):
            raise HTTPException(status_code=400, detail="Invalid filename")

        with open(cache_path, "wb") as f:
            f.write(img_bytes)
        with open(os.path.join(CHARTS_CACHE_DIR, "latest.png"), "wb") as f:
            f.write(img_bytes)
            
        LATEST_CHART_BYTES = img_bytes
        LATEST_CHART_FILENAME = safe_fn

        # 3. Highlight the downloaded file in Windows Explorer so user immediately sees it
        try:
            import subprocess
            subprocess.Popen(["explorer.exe", f"/select,{downloads_target_path}"])
        except Exception as exp_err:
            print("Explorer highlight warning:", exp_err)
        
        return {
            "success": True,
            "filename": safe_fn,
            "file_path": downloads_target_path,
            "message": f"Successfully saved {safe_fn} directly to your Downloads folder!",
            "download_url": f"/api/charts/download/{safe_fn}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
