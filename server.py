import os
import io
import sys
import time
import base64
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


class StyleRequest(BaseModel):
    chart_type: str
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    hue_col: Optional[str] = None
    title: Optional[str] = "Data Analysis Chart"
    style: Optional[str] = "whitegrid"
    palette: Optional[str] = "deep"


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

def render_chart_safe(args):
    """Thread-safe renderer for Studio Matplotlib PNG."""
    with RENDER_LOCK:
        return charts.generate_chart.invoke(args)


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/dataset")
def get_dataset():
    """Returns current dataset overview, column metadata, and sample rows."""
    try:
        current_df = main.df
        numeric_cols = list(current_df.select_dtypes(include=["number"]).columns)
        categorical_cols = [c for c in current_df.columns if c not in numeric_cols]

        total_rows = len(current_df)

        if total_rows > 20:
            head_df = current_df.head(10).copy()
            tail_df = current_df.tail(10).copy()
            head_rows = [{"_row_idx": int(idx) + 1, **row} for idx, row in head_df.iterrows()]
            tail_rows = [{"_row_idx": int(idx) + 1, **row} for idx, row in tail_df.iterrows()]
            has_ellipsis = True
            hidden_count = total_rows - 20
        else:
            head_rows = [{"_row_idx": int(idx) + 1, **row} for idx, row in current_df.iterrows()]
            tail_rows = []
            has_ellipsis = False
            hidden_count = 0

        all_records = [{"_row_idx": int(idx) + 1, **row} for idx, row in current_df.head(200).iterrows()]

        return {
            "columns": list(current_df.columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "row_count": total_rows,
            "column_count": len(current_df.columns),
            "head_rows": head_rows,
            "tail_rows": tail_rows,
            "has_ellipsis": has_ellipsis,
            "hidden_count": hidden_count,
            "sample_data": all_records,
            "describe": current_df.describe().round(2).to_dict() if len(numeric_cols) > 0 else {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload a new CSV file to replace current dataset."""
    try:
        contents = await file.read()
        new_df = pd.read_csv(io.BytesIO(contents))
        
        if new_df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")
            
        main.df = new_df
        LLM_CACHE.clear()
        
        return {
            "message": f"Successfully loaded '{file.filename}' with {len(new_df)} rows and {len(new_df.columns)} columns.",
            "columns": list(new_df.columns),
            "row_count": len(new_df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")


@app.post("/api/generate-chart")
async def generate_chart_endpoint(req: QueryRequest):
    """Processes user natural language request asynchronously with non-blocking thread execution for high concurrency."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        current_df = main.df
        clean_q = req.query.strip().lower()
        cache_key = (clean_q, tuple(current_df.columns))

        # Check instant query cache
        if cache_key in LLM_CACHE:
            cached_data = LLM_CACHE[cache_key]
            args = dict(cached_data["tool_args"])
            if req.style:
                args["style"] = req.style
            if req.palette:
                args["palette"] = req.palette

            args["output_path"] = ":memory:"
            data_url = await asyncio.to_thread(render_chart_safe, args)
            return {
                "success": True,
                "tool_called": True,
                "chart_type": args.get("chart_type", "chart"),
                "tool_args": args,
                "result": "Rendered in-memory",
                "chart_filename": f"{args.get('chart_type', 'chart')}.png",
                "chart_url": data_url,
                "tokens": cached_data.get("tokens", {"total": 0, "input": 0, "output": 0})
            }

        # Invoke multi-model fallback cascade asynchronously (non-blocking)
        ai_message = None
        model_used = None
        try:
            ai_message, model_used = await asyncio.to_thread(
                main.invoke_ai_with_fallbacks, {
                    "columns": list(current_df.columns),
                    "sample_data": current_df.head(3).to_dict(orient="records"),
                    "df": current_df,
                    "user_query": req.query
                }
            )
        except Exception as ai_err:
            try:
                print(f"[WARN] Multi-model cascade error: {ai_err}")
            except Exception:
                pass

        if ai_message and getattr(ai_message, "tool_calls", None):
            tool_call = ai_message.tool_calls[0]
            args = dict(tool_call.get("args", {}))
            usage = getattr(ai_message, "usage_metadata", None) or {}
            tokens_info = {
                "total": usage.get("total_tokens", 0),
                "input": usage.get("input_tokens", 0),
                "output": usage.get("output_tokens", 0),
                "model": model_used
            }
        else:
            # Bulletproof instant fallback: Smart Heuristic Extractor
            # Guarantees zero 429 quota exhaustion errors
            try:
                print(f"[INFO] Smart Heuristic instant extraction activated for query: '{req.query}'")
            except Exception:
                pass
            args = main.heuristic_chart_extractor(req.query, current_df)
            tokens_info = {
                "total": 0,
                "input": 0,
                "output": 0,
                "model": "heuristic_instant"
            }

        if req.style:
            args["style"] = req.style
        if req.palette:
            args["palette"] = req.palette

        # Cache tool args for subsequent instant generations
        LLM_CACHE[cache_key] = {
            "tool_args": dict(args),
            "tokens": tokens_info
        }

        args["output_path"] = ":memory:"
        # Render chart purely in-memory in a background thread (event loop never freezes)
        data_url = await asyncio.to_thread(render_chart_safe, args)

        # Self-healing fallback: If LLM generated bad args, instantly recover via heuristic
        if isinstance(data_url, str) and data_url.startswith("Error generating chart:"):
            try:
                print(f"[WARN] AI produced rendering error: '{data_url[:80]}'. Self-healing via Heuristic...")
            except Exception:
                pass
            args = main.heuristic_chart_extractor(req.query, current_df)
            if req.style:
                args["style"] = req.style
            if req.palette:
                args["palette"] = req.palette
            args["output_path"] = ":memory:"
            data_url = await asyncio.to_thread(render_chart_safe, args)
            tokens_info["model"] = f"{tokens_info.get('model', 'ai')}_self_healed"

        return {
            "success": True,
            "tool_called": True,
            "chart_type": args.get("chart_type", "chart"),
            "tool_args": args,
            "result": "Rendered in-memory",
            "chart_filename": f"{args.get('chart_type', 'chart')}.png",
            "chart_url": data_url,
            "tokens": tokens_info
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/apply-style")
async def apply_style_endpoint(req: StyleRequest):
    """Directly re-renders the chart with selected style & palette without calling the LLM asynchronously."""
    try:
        args = {
            "chart_type": req.chart_type,
            "x_col": req.x_col,
            "y_col": req.y_col,
            "hue_col": req.hue_col,
            "title": req.title or "Data Analysis Chart",
            "style": req.style or "whitegrid",
            "palette": req.palette or "deep",
            "output_path": ":memory:"
        }
        # Restyle chart purely in-memory in a non-blocking worker thread
        data_url = await asyncio.to_thread(render_chart_safe, args)
        return {
            "success": True,
            "chart_type": req.chart_type,
            "chart_url": data_url,
            "tool_args": args,
            "result": "Restyled in-memory"
        }
    except Exception as e:
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
