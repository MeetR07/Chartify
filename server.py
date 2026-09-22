import os
import io
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

import charts
import main
from profiler import profile_dataset, get_dataset_schema, clear_profile_cache
from planner import LLMQueryPlanner, PlanValidator, check_column_ambiguity
from engine import DeterministicDataEngine, ResultValidator
from chart_planner import ChartPlanner, build_unified_data_contract

# Multi-turn / Follow-up session store
SESSION_STORE: Dict[str, Dict[str, Any]] = {}

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    style: Optional[str] = "whitegrid"
    palette: Optional[str] = "deep"
    session_id: Optional[str] = "default"


class StyleRequest(BaseModel):
    chart_type: str
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    hue_col: Optional[str] = None
    title: Optional[str] = "Data Analysis Chart"
    style: Optional[str] = "whitegrid"
    palette: Optional[str] = "deep"


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

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            if time.time() - self.timestamps.get(key, 0) > self.ttl:
                del self.cache[key]
                self.timestamps.pop(key, None)
                return None
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

# Thread-safe synchronization lock for Matplotlib figure canvas
RENDER_LOCK = threading.Lock()
CHARTS_CACHE_DIR = os.path.join(os.getcwd(), "generated_charts")
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
        contents = await file.read()
        try:
            new_df = pd.read_csv(io.BytesIO(contents))
        except UnicodeDecodeError:
            new_df = pd.read_csv(io.BytesIO(contents), encoding="latin1")

        if new_df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

        main.df = new_df
        clear_profile_cache()
        LLM_CACHE.clear()
        SESSION_STORE.clear()
        profile_dataset(new_df)

        return build_dataset_payload(new_df, filename=file.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")


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

        # 2. Structured Query Planning with Rule Fast-Path & Cascade Fallbacks
        plan, plan_meta = LLMQueryPlanner.generate_plan(
            query=req.query,
            df=current_df,
            session_state=session_state
        )

        if plan.get("clarification_needed"):
            return plan

        # 3. Plan Validation (Multi-layer pre-execution)
        is_valid_plan, plan_err, fix_info = PlanValidator.validate_plan(plan, schema)
        if not is_valid_plan:
            return {
                "success": False,
                "validation_error": True,
                "message": plan_err or "Invalid query plan.",
                "fix_info": fix_info
            }

        # 4. Deterministic Data Engine Execution (Zero code execution)
        result_df, exec_meta = DeterministicDataEngine.execute_plan(current_df, plan)

        # 5. Result Validation
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

        # 6. Chart Selection & Conflict Resolution
        chosen_chart, fallback_note = ChartPlanner.select_and_validate_chart(result_df, plan, exec_meta)

        # 7. Build Unified 2D/3D Data Contract (Identical source of truth for both renderers)
        contract = build_unified_data_contract(result_df, plan, exec_meta, chosen_chart, fallback_note)

        # 8. Render Studio 2D Chart with precomputed DataFrame
        title_text = plan.get("explanation") or f"{contract['axis_metadata']['y_label']} by {contract['axis_metadata']['x_label']}"
        render_args = {
            "chart_type": chosen_chart,
            "x_col": contract["x_col"],
            "y_col": contract["y_col"],
            "title": title_text,
            "style": req.style or "whitegrid",
            "palette": req.palette or "deep",
            "query": req.query,
            "output_path": ":memory:",
            "precomputed_df": result_df,
            "unified_contract": contract
        }

        data_url = await asyncio.to_thread(render_chart_safe, render_args)

        # 9. Update Session Store
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
            "output_path": f"{chosen_chart}.png"
        }

        return {
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
            "tokens": {"total": 0, "input": 0, "output": 0, "model": plan_meta.get("model") if plan_meta else "engine"}
        }

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
        
        # Restyle chart purely in-memory in a non-blocking worker thread
        data_url = await asyncio.to_thread(render_chart_safe, args)
        if isinstance(data_url, str) and data_url.startswith("Error generating"):
            raise HTTPException(status_code=400, detail=data_url)

        return {
            "success": True,
            "chart_type": args.get("chart_type", "chart"),
            "chart_url": data_url,
            "tool_args": args,
            "chart_data": charts.get_last_chart_data(),
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
    file_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chart image not found.")
    return FileResponse(
        file_path,
        media_type="image/png",
        content_disposition_type="inline",
        headers={"Content-Disposition": "inline"}
    )


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

        safe_fn = (req.filename or LATEST_CHART_FILENAME or "chart.png").replace('"', '').strip()
        if not safe_fn.endswith(".png"):
            safe_fn += ".png"

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

    safe_fn = (filename or LATEST_CHART_FILENAME or "chart.png").replace('"', '').strip()
    if not safe_fn.endswith(".png"):
        safe_fn += ".png"

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
    safe_fn = filename.strip().replace('"', '')
    if not safe_fn.endswith(".png"):
        safe_fn += ".png"
    filepath = os.path.join(CHARTS_CACHE_DIR, safe_fn)
    latest_path = os.path.join(CHARTS_CACHE_DIR, "latest.png")
    
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
        
        safe_fn = (req.filename or "chart.png").strip().replace('"', '')
        if not safe_fn.endswith(".png"):
            safe_fn += ".png"
            
        filepath = os.path.join(CHARTS_CACHE_DIR, safe_fn)
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
        
        safe_fn = (req.filename or "chart.png").strip().replace('"', '')
        if not safe_fn.endswith(".png"):
            safe_fn += ".png"
            
        # 1. Save directly into OS Downloads folder (C:\Users\<user>\Downloads)
        user_downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(user_downloads_dir, exist_ok=True)
        downloads_target_path = os.path.join(user_downloads_dir, safe_fn)
        with open(downloads_target_path, "wb") as f:
            f.write(img_bytes)
            
        # 2. Also save into project generated_charts folder
        cache_path = os.path.join(CHARTS_CACHE_DIR, safe_fn)
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
