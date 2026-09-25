import os
import sys
import time
import socket
from urllib.parse import urlparse
from dotenv import load_dotenv

def is_service_alive(url: str, timeout: float = 0.15) -> bool:
    """Instant TCP socket probe to verify if a local service is listening (<1ms) instead of waiting for 15-45s HTTP connection timeouts."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False

import base64
import pandas as pd
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

try:
    from langchain_openai import ChatOpenAI
    HAS_LANGCHAIN_OPENAI = True
except ImportError:
    ChatOpenAI = None
    HAS_LANGCHAIN_OPENAI = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    HAS_GEMINI = True
except ImportError:
    ChatGoogleGenerativeAI = None
    HAS_GEMINI = False

try:
    from langchain_mistralai import ChatMistralAI
    HAS_MISTRAL = True
except ImportError:
    ChatMistralAI = None
    HAS_MISTRAL = False

try:
    from langchain_groq import ChatGroq
    HAS_GROQ = True
except ImportError:
    ChatGroq = None
    HAS_GROQ = False

try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    HAS_NVIDIA = True
except ImportError:
    ChatNVIDIA = None
    HAS_NVIDIA = False

import re
from .charts import generate_chart, detect_query_intent

# Ensure UTF-8 output on Windows to prevent UnicodeEncodeError
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

load_dotenv()


def _safe_print(*args, **kwargs):
    """Print wrapper that silently ignores encoding errors on Windows consoles."""
    try:
        print(*args, **kwargs)
    except Exception:
        pass


# ==============================================================================
# MODEL REGISTRY
# ==============================================================================

CANDIDATE_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]

MISTRAL_MODELS = [
    "ministral-8b-latest",
    "open-mistral-7b",
    "codestral-latest",
    "ministral-3b-latest",
]

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
]

OPENROUTER_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "meta-llama/llama-3.3-70b-instruct",
]

NVIDIA_MODELS = [
    "meta/llama-3.1-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
]

# FreeLLMAPI routing model names (smart auto-routing across 34 providers)
# Ref: https://github.com/tashfeenahmed/freellmapi
FREELLMAPI_MODELS = [
    "auto",           # Best available model (smart routing)
    "auto:balanced",  # Speed + capability balanced
    "auto:speed",     # Fastest free model
]

# FreeLLMAPI connection config — set in .env
# Start freellmapi locally: npx freellmapi  (or docker run freellmapi/server)
FREELLMAPI_BASE_URL = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3000/v1")
FREELLMAPI_API_KEY  = os.getenv("FREELLMAPI_API_KEY", "freellmapi-local")

# Circuit Breaker: skips Gemini for 60s after a 429 quota error to avoid
# stacking 10-12s network timeouts on every request.
CIRCUIT_BREAKER = {
    "gemini_quota_exhausted_until": 0.0,
    "cooldown_seconds": 60.0,
}

# Keyword -> chart type mapping (ordered by specificity, most-specific first)
CHART_PATTERNS = [
    ("waterfall",     "waterfall"),
    ("lollipop",     "lollipop"),
    ("treemap",      "treemap"),
    ("pairplot",     "pairplot"),
    ("heatmap",      "heatmap"),
    ("correlation",  "heatmap"),
    ("violin",       "violin"),
    ("scatter",      "scatter"),
    ("bubble",       "bubble"),
    ("donut",        "donut"),
    ("doughnut",     "donut"),
    ("funnel",       "funnel"),
    ("radar",        "radar"),
    ("spider",       "radar"),
    ("histogram",    "histogram"),
    ("hist",         "histogram"),
    ("distribution", "histogram"),
    ("box",          "box"),
    ("area",         "area"),
    ("line",         "line"),
    ("trend",        "line"),
    ("bar",          "bar"),
    ("pie",          "pie"),
]


from typing import Literal, Optional, Dict, Any, List
from langchain_core.tools import tool

@tool
def generate_chart_llm_tool(
    chart_type: str = "bar",
    x_col: str = "",
    y_col: str = "",
    hue_col: str = "",
    title: str = "Data Analysis Chart",
    palette: str = "deep",
    style: str = "whitegrid"
) -> str:
    """Generates a data visualization chart.
    Args:
        chart_type: The chart visualization type.
        x_col: Category or X-axis column name from dataset.
        y_col: Numeric measure or Y-axis column name from dataset.
        hue_col: Optional grouping category.
        title: Descriptive chart title.
        palette: Theme palette name.
        style: Background style ('whitegrid', 'darkgrid', etc.).
    """
    return "ok"


# ==============================================================================
# MODEL CHAIN FACTORIES
# ==============================================================================

def create_model_chain(model_name: str):
    """Returns a Gemini model bound to the chart generation tool schema."""
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=0,
        timeout=15,
    )
    return llm.bind_tools([generate_chart_llm_tool])


def create_mistral_chain(model_name: str = "ministral-8b-latest"):
    """Returns a Mistral model bound to the chart generation tool schema."""
    llm = ChatMistralAI(
        model=model_name,
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0,
        max_retries=0,
        timeout=8,
    )
    return llm.bind_tools([generate_chart_llm_tool])


def create_openrouter_chain(model_name: str):
    """Returns an OpenRouter model bound to the chart generation tool schema."""
    if not HAS_LANGCHAIN_OPENAI or ChatOpenAI is None:
        return None
    try:
        llm = ChatOpenAI(
            model=model_name,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            max_retries=0,
            timeout=15,
        )
        return llm.bind_tools([generate_chart_llm_tool])
    except Exception:
        return None


def create_nvidia_chain(model_name: str):
    """Returns an NVIDIA API model bound to the chart generation tool schema."""
    llm = ChatNVIDIA(
        model=model_name,
        nvidia_api_key=os.getenv("NVIDIA_API_KEY"),
        temperature=0,
        max_retries=0,
        timeout=15,
    )
    return llm.bind_tools([generate_chart_llm_tool])


def create_groq_chain(model_name: str = "llama-3.3-70b-versatile"):
    """Returns a Groq Llama-3 model bound to the chart generation tool schema."""
    llm = ChatGroq(
        model=model_name,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_retries=0,
        timeout=8,
    )
    return llm.bind_tools([generate_chart_llm_tool])


def create_freellmapi_chain(model_name: str = "auto"):
    """
    Returns a FreeLLMAPI chain — OpenAI-compatible local proxy that
    aggregates 34 free LLM providers (635 endpoints, 7.4B tokens/month).
    Requires freellmapi server running locally: npx freellmapi
    Ref: https://github.com/tashfeenahmed/freellmapi
    """
    if not HAS_LANGCHAIN_OPENAI or ChatOpenAI is None:
        return None
    try:
        base_url = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3000/v1")
        api_key  = os.getenv("FREELLMAPI_API_KEY", "freellmapi-local")
        llm = ChatOpenAI(
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            max_retries=0,
            timeout=15,
        )
        return llm.bind_tools([generate_chart])
    except Exception:
        return None


def get_freellmapi_chains():
    """Lazily resolves FreeLLMAPI chains with active .env config."""
    if not HAS_LANGCHAIN_OPENAI or ChatOpenAI is None:
        return {}
    return {m: c for m in FREELLMAPI_MODELS if (c := create_freellmapi_chain(m)) is not None}


# Pre-initialize all chains ONCE at startup so cascade has zero per-request overhead
_GEMINI_CHAINS      = {m: create_model_chain(m)    for m in CANDIDATE_MODELS} if HAS_GEMINI and ChatGoogleGenerativeAI else {}
_MISTRAL_CHAINS     = {m: create_mistral_chain(m)  for m in MISTRAL_MODELS} if HAS_MISTRAL and ChatMistralAI else {}
_OPENROUTER_CHAINS  = {m: c for m in OPENROUTER_MODELS if (c := create_openrouter_chain(m)) is not None} if ChatOpenAI else {}
_NVIDIA_CHAINS      = {m: create_nvidia_chain(m)   for m in NVIDIA_MODELS} if HAS_NVIDIA and ChatNVIDIA else {}
_GROQ_CHAINS        = {m: create_groq_chain(m)     for m in GROQ_MODELS} if HAS_GROQ and ChatGroq else {}
_FREELLMAPI_CHAINS  = get_freellmapi_chains()

# Primary model exposed for backward compatibility with main.py / chart_chain
llm            = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0,
                                        google_api_key=os.getenv("GOOGLE_API_KEY"), max_retries=0) if HAS_GEMINI and ChatGoogleGenerativeAI else None
llm_with_tools = llm.bind_tools([generate_chart]) if llm else None


# ==============================================================================
# PROMPT
# ==============================================================================

def format_prompt_inputs(inputs: dict) -> dict:
    """
    Builds a rich, token-efficient context block for the LLM:
      - Column names WITH dtype tags (numeric / categorical / datetime)
      - Up to 3 sample rows so the model sees real values
      - Explicit column list the model MUST use verbatim
    """
    df          = inputs.get("df")            # actual DataFrame (optional)
    cols        = inputs.get("columns", [])
    sample_rows = inputs.get("sample_data", [])
    user_query  = inputs.get("user_query", "")

    # ── Column metadata (dtype-tagged, O(1) dictionary lookups) ────────────
    col_lines = []
    df_dtypes = df.dtypes.to_dict() if df is not None else {}
    for c in cols:
        if c in df_dtypes:
            dtype = df_dtypes[c]
            if pd.api.types.is_datetime64_any_dtype(dtype):
                tag = "datetime"
            elif pd.api.types.is_numeric_dtype(dtype):
                tag = "numeric"
            else:
                tag = "categorical"
        else:
            tag = "unknown"
        col_lines.append(f"  • {c} [{tag}]")

    col_block = f"Dataset columns ({len(cols)}):\n" + "\n".join(col_lines)

    # ── Sample rows (max 3, compact) ────────────────────────────────────────
    if sample_rows:
        header = " | ".join(str(k) for k in sample_rows[0].keys())
        rows   = "\n".join(
            " | ".join(str(v) for v in row.values())
            for row in sample_rows[:3]
        )
        sample_block = f"Sample data (first 3 rows):\n{header}\n{rows}"
    else:
        sample_block = ""

    columns_summary = col_block + ("\n\n" + sample_block if sample_block else "")

    return {
        "columns_summary": columns_summary,
        "user_query":      user_query,
    }


CHART_RULES = """\
CHART TYPE SELECTION RULES (follow strictly):
  bar       → compare categories; x_col=category, y_col=numeric
  line      → trends over time/ordered axis; x_col=time/ordered, y_col=numeric
  area      → cumulative trends; x_col=time/ordered, y_col=numeric
  scatter   → correlation between two numerics; x_col=numeric, y_col=numeric
  bubble    → 3-variable scatter; x_col=numeric, y_col=numeric, hue_col=numeric(size)
  histogram → distribution of ONE numeric column; x_col=numeric, y_col=None
  box       → distribution + outliers by category; x_col=category, y_col=numeric
  violin    → distribution shape by category; x_col=category, y_col=numeric
  heatmap   → correlation matrix; x_col=None, y_col=None (uses all numerics)
  pairplot  → pairwise scatter of all numerics; x_col=None, y_col=None
  pie       → part-of-whole (≤8 categories); x_col=category, y_col=numeric(optional)
  donut     → same as pie with hole; x_col=category, y_col=numeric(optional)
  treemap   → hierarchical proportions; x_col=category, y_col=numeric
  funnel    → sequential stage data; x_col=category, y_col=numeric
  waterfall → running total/cumulative; x_col=category, y_col=numeric
  lollipop  → ranked comparison (like bar but cleaner); x_col=category, y_col=numeric
  radar     → multi-metric comparison; x_col=category, y_col=numeric

COLUMN ASSIGNMENT RULES:
  • ALWAYS use EXACT column names from the dataset (case-sensitive).
  • NEVER invent or guess column names.
  • When user explicitly names a column or category (e.g. "by Car Year", "Use Car Year as the category", "by Model"), you MUST use that exact column for x_col. NEVER substitute a different column like Date unless requested.
  • For yearly aggregations ("year by year", "by year", "annual"), if a specific year column exists (like "Car Year", "Year"), ALWAYS prioritize it over a daily "Date" column unless user explicitly asks for "Date".
  • Year columns (e.g. "Car Year", "Year") even if numeric dtype MUST be used as the category/dimension (x_col) when grouping or comparing by year.
  • For ranking or extreme queries on a single numeric column (e.g. "highest total_rooms", "top 10 rooms", "lowest total_rooms", "highest values in total_rooms"):
    Set x_col = the numeric column, y_col = None, chart_type = "bar".
    DO NOT pick an unrelated category column for grouping unless user explicitly asks "by <category>".
  • For "Measure by Category" queries (e.g. "Profit by Month", "Sales by Region", "Sale Price by Car Year"):
    x_col = the category/dimension (e.g. Month, Region, Car Year)
    y_col = the numeric measure (e.g. Profit, Sales, Sale Price)
  • For "X vs Y" queries: x_col = first mentioned, y_col = second mentioned.
  • hue_col = grouping/color split (optional, only when user implies comparison).
  • If user does NOT mention a column explicitly, infer the best match by dtype.
  • Prefer categorical/dimension columns for x_col, numeric columns for y_col.
  • For time-related queries pick the datetime, year, or ordered categorical column as x_col.

TITLE RULE:
  • Write a clear, concise chart title reflecting the user's intent.
  • Format: "<Measure> by <Category>" or "<Chart Type> of <Column>".

ACCURACY MANDATE:
  • Call generate_chart ONCE with the best possible arguments.
  • Do NOT return text — always call the tool.
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert data visualization agent.\n"
     "Your ONLY job is to call the `generate_chart` tool with perfectly chosen arguments.\n\n"
     "{columns_summary}\n\n"
     + CHART_RULES),
    ("human", "{user_query}"),
])



# ==============================================================================
# MULTI-MODEL CASCADE WITH CIRCUIT BREAKER
# ==============================================================================

def _try_model_cascade(chains: dict, prompt_val, provider: str):
    """
    Iterates over {model_name: chain} and returns the first successful AI message
    that produced tool calls, or (None, last_error) if every model fails.
    """
    last_error = None
    for model_name, chain in chains.items():
        try:
            ai_message = chain.invoke(prompt_val)
            if ai_message and getattr(ai_message, "tool_calls", None):
                _safe_print(f"[SUCCESS] {provider} ({model_name}) generated chart.")
                return ai_message, f"{provider}:{model_name}"
        except Exception as e:
            last_error = e
            _safe_print(f"[WARN] {provider} '{model_name}' failed: {str(e)[:120]}")
    return None, last_error


def invoke_ai_with_fallbacks(inputs: dict):
    """
    Cascading AI invocation with automatic fallbacks and circuit-breaker protection:

    0. FreeLLMAPI [TEST] - local proxy aggregating 34 free providers (7.4B tokens/month)
                          Only active if FREELLMAPI_ENABLED=true in .env
    1. Gemini  - skipped for 60s after a 429 quota error (circuit breaker)
    2. Mistral - used if MISTRAL_API_KEY is set
    3. Groq    - used if GROQ_API_KEY is set
    4. Returns (None, None) -> caller falls back to the heuristic extractor
    """
    prompt_val = prompt_template.format_prompt(**format_prompt_inputs(inputs))
    now        = time.time()

    # 0. FreeLLMAPI [TEST] — aggregates 34 free providers behind one /v1 endpoint
    #    Enable by setting FREELLMAPI_ENABLED=true in .env and running: npx freellmapi
    if os.getenv("FREELLMAPI_ENABLED", "").lower() == "true":
        base_url = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3000/v1")
        if not HAS_LANGCHAIN_OPENAI:
            _safe_print("[WARN] FREELLMAPI_ENABLED=true but 'langchain-openai' is not installed. Run: pip install langchain-openai")
        elif not is_service_alive(base_url, timeout=0.15):
            _safe_print(f"[INFO] FreeLLMAPI server not running at {base_url} (run 'npx freellmapi' to start). Skipping instantly.")
        else:
            _safe_print("[INFO] Trying FreeLLMAPI (34 providers, 635 models)...")
            chains = get_freellmapi_chains()
            result, label = _try_model_cascade(chains, prompt_val, "freellmapi")
            if result:
                _safe_print(f"[SUCCESS] FreeLLMAPI generated chart via {label}.")
                return result, label
            _safe_print("[WARN] FreeLLMAPI unavailable — falling through to Gemini.")

    # 1. Gemini
    if now >= CIRCUIT_BREAKER["gemini_quota_exhausted_until"]:
        for model_name, chain in _GEMINI_CHAINS.items():
            try:
                ai_message = chain.invoke(prompt_val)
                if ai_message and getattr(ai_message, "tool_calls", None):
                    return ai_message, f"gemini:{model_name}"
            except Exception as e:
                err_msg = str(e)
                _safe_print(f"[WARN] Gemini '{model_name}' failed: {err_msg[:120]}")
                if any(x in err_msg for x in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "quota"]):
                    CIRCUIT_BREAKER["gemini_quota_exhausted_until"] = now + CIRCUIT_BREAKER["cooldown_seconds"]
                    _safe_print(f"[INFO] Gemini unavailable ({'503 high demand' if '503' in err_msg else '429 quota'}). Switching immediately to next provider.")
                    break
    else:
        remaining = int(CIRCUIT_BREAKER["gemini_quota_exhausted_until"] - now)
        _safe_print(f"[INFO] Gemini circuit breaker active ({remaining}s left). Skipping.")

    # 2. Mistral
    if os.getenv("MISTRAL_API_KEY"):
        _safe_print("[INFO] Falling back to Mistral...")
        result, label = _try_model_cascade(_MISTRAL_CHAINS, prompt_val, "mistral")
        if result:
            return result, label

    # 3. OpenRouter
    if os.getenv("OPENROUTER_API_KEY"):
        _safe_print("[INFO] Falling back to OpenRouter...")
        result, label = _try_model_cascade(_OPENROUTER_CHAINS, prompt_val, "openrouter")
        if result:
            return result, label

    # 4. NVIDIA
    if os.getenv("NVIDIA_API_KEY"):
        _safe_print("[INFO] Falling back to NVIDIA NIM...")
        result, label = _try_model_cascade(_NVIDIA_CHAINS, prompt_val, "nvidia")
        if result:
            return result, label

    # 5. Groq
    if os.getenv("GROQ_API_KEY"):
        _safe_print("[INFO] Falling back to Groq Llama-3...")
        result, label = _try_model_cascade(_GROQ_CHAINS, prompt_val, "groq")
        if result:
            return result, label

    return None, None


# ==============================================================================
# SMART HEURISTIC EXTRACTOR  (zero API calls, <50ms)
# ==============================================================================

def heuristic_chart_extractor(query: str, current_df: pd.DataFrame) -> dict:
    """
    Rule-based keyword + column extractor used as instant fallback when the
    LLM cascade fails or quota is exhausted.  No external calls - always works.
    """
    q = query.lower().strip()
    op, limit = detect_query_intent(query)

    chart_type = next((ctype for pattern, ctype in CHART_PATTERNS if pattern in q), "bar")

    num_cols = list(current_df.select_dtypes(include=["number"]).columns)
    num_set = set(num_cols)
    cat_cols = [c for c in current_df.columns if c not in num_set]
    all_cols = list(current_df.columns)

    # Check exact match or normalized match (handling spaces vs underscores)
    q_norm = q.lower().replace("_", " ")
    mentioned = [c for c in all_cols if c.lower() in q or c.lower().replace("_", " ") in q_norm]

    # If no exact match, check token / stem matches (e.g. "rooms" -> "total_rooms")
    if not mentioned:
        q_tokens = set(re.findall(r'[a-zA-Z]{3,}', q))
        stopwords = {
            "highest", "lowest", "find", "rank", "what", "show", "tell", "give", 
            "display", "plot", "chart", "with", "have", "each", "value", "values", 
            "descending", "ascending", "average", "mean", "maximum", "minimum", 
            "most", "least", "more", "less", "them", "from", "into", "create",
            "treemap", "showing", "total", "group", "size"
        }
        q_tokens -= stopwords
        best_col = None
        best_score = 0
        for c in all_cols:
            c_tokens = set(c.lower().split("_"))
            overlap = len(q_tokens & c_tokens)
            if overlap > best_score:
                best_score = overlap
                best_col = c
            elif best_score == 0:
                # Substring check
                for qt in q_tokens:
                    if qt in c.lower():
                        mentioned.append(c)
                        break
        if best_col and best_col not in mentioned:
            mentioned.insert(0, best_col)

    x_col = y_col = None

    if len(mentioned) >= 2:
        c1, c2 = mentioned[0], mentioned[1]
        c1_norm = c1.lower().replace("_", " ")
        c2_norm = c2.lower().replace("_", " ")
        if " by " in q:
            # "Sales by Month" -> y=Sales, x=Month
            parts = q.split(" by ", 1)
            p0 = parts[0].lower().replace("_", " ")
            p1 = parts[1].lower().replace("_", " ")
            if c1_norm in p0 and c2_norm in p1:
                y_col, x_col = c1, c2
            elif c2_norm in p0 and c1_norm in p1:
                y_col, x_col = c2, c1
            elif c1 in num_cols and c2 in cat_cols:
                y_col, x_col = c1, c2
            elif c2 in num_cols and c1 in cat_cols:
                y_col, x_col = c2, c1
        elif " vs " in q:
            # "Month vs Sales" -> x=Month, y=Sales
            parts = q.split(" vs ", 1)
            p0 = parts[0].lower().replace("_", " ")
            x_col, y_col = (c1, c2) if c1_norm in p0 else (c2, c1)

        if not x_col:  # fallback: assign by dtype
            if   c1 in cat_cols and c2 in num_cols: x_col, y_col = c1, c2
            elif c2 in cat_cols and c1 in num_cols: x_col, y_col = c2, c1
            elif c1 in num_cols and c2 in cat_cols: x_col, y_col = c2, c1
            elif c2 in num_cols and c1 in cat_cols: x_col, y_col = c1, c2
            else:                                    x_col, y_col = c1, c2

    elif len(mentioned) == 1:
        c = mentioned[0]
        if c in cat_cols:
            x_col, y_col = c, (num_cols[0] if num_cols else None)
        else:
            # Numeric column: check if this is ranking, mean, max, min, or count query without "by"
            if " by " not in q and " vs " not in q:
                x_col = c
                y_col = None
                if op == "ranking_desc":
                    title = f"Top {c} (Ranked Descending)"
                elif op == "ranking_asc":
                    title = f"Lowest {c} (Ranked Ascending)"
                elif op == "max":
                    title = f"Maximum of {c}"
                elif op == "mean":
                    title = f"Average of {c}"
                elif op == "count":
                    title = f"Distribution of {c}"
                else:
                    title = f"Analysis of {c}"
                return {"chart_type": chart_type, "x_col": x_col, "y_col": y_col, "title": title, "query": query}
            else:
                y_col = c
                x_col = cat_cols[0] if cat_cols else (num_cols[0] if num_cols[0] != c else None)
    elif chart_type in ["histogram", "hist"]:
        # A histogram always requires a numeric column for x_col and no y_col
        num_target = None
        for m in mentioned:
            if m in num_cols:
                num_target = m
                break
        if not num_target and num_cols:
            num_target = num_cols[0]
        x_col = num_target or (all_cols[0] if all_cols else None)
        y_col = None
        title = f"Distribution of {x_col}"
        return {"chart_type": "histogram", "x_col": x_col, "y_col": y_col, "title": title, "query": query}
    elif chart_type in ["heatmap", "correlation"]:
        return {"chart_type": "heatmap", "x_col": None, "y_col": None, "title": "Correlation Heatmap", "query": query}
    else:
        # Check if an explicit target was requested (e.g. "pie chart of gender") that does not exist in dataset
        explicit_target = None
        target_match = re.search(r"\b(?:of|by|for|per|across|in)\s+([a-zA-Z0-9_]+)", q)
        if target_match:
            candidate = target_match.group(1).strip()
            if candidate not in {"a", "the", "an", "data", "records", "chart", "plot", "pie", "bar", "histogram"}:
                explicit_target = candidate

        if explicit_target:
            x_col = explicit_target
            y_col = None
        else:
            x_col    = cat_cols[0] if cat_cols else (all_cols[0] if all_cols else None)
            rem_nums = [c for c in num_cols if c != x_col]
            y_col    = rem_nums[0] if rem_nums else (all_cols[1] if len(all_cols) > 1 else None)

    if x_col and y_col:
        title = f"{y_col} by {x_col}"
    elif x_col:
        title = f"Distribution of {x_col}"
    else:
        title = f"{chart_type.capitalize()} Analysis"

    return {"chart_type": chart_type, "x_col": x_col, "y_col": y_col, "title": title, "query": query}


# ==============================================================================
# LCEL CHAINS  (exposed for main.py / CLI usage)
# ==============================================================================

def execute_chart_tool(ai_message) -> dict:
    """Executes the tool call returned by the LLM and packages the result."""
    usage       = getattr(ai_message, "usage_metadata", None) or {}
    tokens_info = {
        "total":  usage.get("total_tokens", 0),
        "input":  usage.get("input_tokens", 0),
        "output": usage.get("output_tokens", 0),
    }

    if ai_message.tool_calls:
        args       = ai_message.tool_calls[0].get("args", {})
        chart_type = args.get("chart_type", "chart")
        return {
            "success":        True,
            "tool_called":    True,
            "chart_type":     chart_type,
            "tool_args":      args,
            "result":         generate_chart.invoke(args),
            "chart_filename": f"{chart_type}.png",
            "tokens":         tokens_info,
            "raw_message":    ai_message,
        }

    return {
        "success":      True,
        "tool_called":  False,
        "ai_response":  ai_message.content,
        "tokens":       tokens_info,
        "raw_message":  ai_message,
    }


# Resilient chart generation chain (Cascades through Gemini, Groq, Mistral, FreeLLM, Heuristic)
def run_resilient_chart_pipeline(inputs: dict) -> dict:
    """Invokes LLM with fallback cascade, generates chart, and returns result."""
    ai_message, model_used = invoke_ai_with_fallbacks(inputs)
    if ai_message:
        res = execute_chart_tool(ai_message)
        res["model_used"] = model_used
        return res

    # Fallback to smart heuristic chart extractor
    q = inputs.get("user_query", "")
    cols = inputs.get("columns", [])
    h_args = heuristic_chart_extractor(q, cols)
    chart_type = h_args.get("chart_type", "bar")
    res_str = generate_chart.invoke(h_args)
    return {
        "success": True,
        "tool_called": True,
        "chart_type": chart_type,
        "tool_args": h_args,
        "result": res_str,
        "chart_filename": f"{chart_type}.png",
        "tokens": {"total": 0, "input": 0, "output": 0},
        "model_used": "Smart Heuristic Extractor",
    }


ai_chain = RunnableLambda(format_prompt_inputs) | prompt_template | (llm_with_tools or RunnableLambda(lambda x: None))
chart_chain = RunnableLambda(run_resilient_chart_pipeline)


# ==============================================================================
# CHART SUMMARIZATION PIPELINE (Multimodal Vision & Data Intelligence)
# ==============================================================================

def summarize_chart_with_llm(chart_result: dict, user_query: str = "", df: pd.DataFrame = None) -> dict:
    """
    Feeds the generated chart (both the image file and its exact underlying metadata)
    back to the LLM (Gemini Vision -> Groq Llama-3 -> Mistral -> Analytical Heuristic)
    to generate an executive-level summary and strategic insights.
    """
    args = dict(chart_result.get("tool_args") or {})
    chart_type = chart_result.get("chart_type") or args.get("chart_type", "chart")
    title = args.get("title") or chart_result.get("title") or f"{chart_type.title()} Chart"
    filename = chart_result.get("chart_filename") or f"{chart_type}.png"

    # Resolve exact metadata
    from . import charts
    chart_meta = charts.get_last_chart_data() or chart_result.get("chart_data") or {}
    data_points = chart_meta.get("data_points") or []
    pie_slices = chart_meta.get("pie_slices") or []
    total_val = chart_meta.get("total_val")

    # 1. Structure the data context for the LLM
    context_parts = [
        f"Visualization Type : {chart_type.upper()}",
        f"Chart Title        : {title}",
        f"User Query         : {user_query or args.get('query', 'N/A')}",
        f"X-Axis Column      : {args.get('x_col', 'N/A')}",
        f"Y-Axis Column      : {args.get('y_col', 'N/A')}",
    ]
    if total_val is not None:
        context_parts.append(f"Grand Total        : {total_val:,.2f}")

    if pie_slices:
        context_parts.append("\nExact Slices & Proportions:")
        for s in pie_slices:
            context_parts.append(f"  • {s.get('label')}: {s.get('val', 0):,.2f} ({s.get('pct_str', '')})")
    elif data_points:
        context_parts.append("\nPlotted Data Values:")
        for p in data_points[:16]:
            val_str = f"{p.get('val', 0):,.2f}" if isinstance(p.get('val'), (int, float)) else str(p.get('val'))
            pct_part = f" ({p.get('pct_str')})" if p.get('pct_str') else ""
            context_parts.append(f"  • {p.get('label')}: {val_str}{pct_part}")

    data_summary_text = "\n".join(context_parts)

    prompt_text = (
        "Analyze this chart using ONLY the provided data.\n\n"
        "Give 2–4 short, clear insights:\n"
        "- Highlight the most important trend, comparison, highest/lowest value, or relationship.\n"
        "- Include important numbers when useful.\n"
        "- Use simple language.\n"
        "- Do not invent information.\n"
        "- Do not repeat the dataset.\n"
        "- Do not make unsupported assumptions or predictions.\n\n"
        "Return only concise bullet points.\n\n"
        f"Chart: {title}\n\n"
        f"Provided Computed Data & Metrics:\n{data_summary_text}"
    )

    # 2. Check for image file on disk or base64 data url
    b64_image = chart_result.get("b64_image")
    if not b64_image and chart_result.get("chart_url") and isinstance(chart_result["chart_url"], str) and "base64," in chart_result["chart_url"]:
        try:
            b64_image = chart_result["chart_url"].split("base64,", 1)[1]
        except Exception:
            pass

    if not b64_image:
        for candidate in [filename, f"{chart_type}.png", "chart.png"]:
            if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                try:
                    with open(candidate, "rb") as f:
                        b64_image = base64.b64encode(f.read()).decode("utf-8")
                    break
                except Exception:
                    pass

    def _extract_llm_text(content):
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, str):
                    parts.append(p)
                elif isinstance(p, dict) and "text" in p:
                    parts.append(str(p["text"]))
                elif hasattr(p, "text"):
                    parts.append(str(p.text))
                else:
                    parts.append(str(p))
            return "\n".join(parts).strip()
        return str(content).strip() if content else ""

    # 3. Tier 1: Multimodal Vision with Gemini (if image and key available)
    if b64_image and HAS_GEMINI and os.getenv("GOOGLE_API_KEY"):
        for vision_model in ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-image", "gemini-3.1-flash-lite"]:
            try:
                v_llm = ChatGoogleGenerativeAI(
                    model=vision_model,
                    google_api_key=os.getenv("GOOGLE_API_KEY"),
                    temperature=0.2,
                    max_retries=0,
                    timeout=14
                )
                msg = HumanMessage(content=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                ])
                res = v_llm.invoke([msg])
                txt = _extract_llm_text(res.content if res else "")
                if len(txt) > 20:
                    return {"summary": txt, "model": f"{vision_model} (Multimodal Vision)"}
            except Exception as v_err:
                _safe_print(f"[WARN] Vision LLM ({vision_model}) error: {v_err}")

    # 4. Tier 2: Groq Llama-3.3-70b (Ultra-fast, zero lag)
    if HAS_GROQ and os.getenv("GROQ_API_KEY"):
        for g_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                g_llm = ChatGroq(
                    model=g_model,
                    groq_api_key=os.getenv("GROQ_API_KEY"),
                    temperature=0.2,
                    max_retries=0,
                    timeout=8
                )
                res = g_llm.invoke(prompt_text)
                txt = _extract_llm_text(res.content if res else "")
                if len(txt) > 20:
                    return {"summary": txt, "model": f"{g_model} (Groq AI)"}
            except Exception as g_err:
                _safe_print(f"[WARN] Groq LLM ({g_model}) error: {g_err}")

    # 5. Tier 3: Mistral AI
    if HAS_MISTRAL and os.getenv("MISTRAL_API_KEY"):
        for m_model in ["ministral-8b-latest", "open-mistral-7b"]:
            try:
                m_llm = ChatMistralAI(
                    model=m_model,
                    mistral_api_key=os.getenv("MISTRAL_API_KEY"),
                    temperature=0.2,
                    max_retries=0,
                    timeout=8
                )
                res = m_llm.invoke(prompt_text)
                txt = _extract_llm_text(res.content if res else "")
                if len(txt) > 20:
                    return {"summary": txt, "model": f"{m_model} (Mistral AI)"}
            except Exception as m_err:
                _safe_print(f"[WARN] Mistral LLM ({m_model}) error: {m_err}")

    # 6. Tier 4: OpenRouter
    if ChatOpenAI and os.getenv("OPENROUTER_API_KEY"):
        for o_model in ["anthropic/claude-3.5-sonnet", "meta-llama/llama-3.3-70b-instruct"]:
            try:
                o_llm = ChatOpenAI(
                    model=o_model,
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.2,
                    max_retries=0,
                    timeout=12
                )
                res = o_llm.invoke(prompt_text)
                txt = _extract_llm_text(res.content if res else "")
                if len(txt) > 20:
                    return {"summary": txt, "model": f"{o_model} (OpenRouter)"}
            except Exception as o_err:
                _safe_print(f"[WARN] OpenRouter LLM ({o_model}) error: {o_err}")

    # 7. Tier 5: NVIDIA
    if HAS_NVIDIA and ChatNVIDIA and os.getenv("NVIDIA_API_KEY"):
        for n_model in ["meta/llama-3.1-70b-instruct", "nvidia/llama-3.1-nemotron-70b-instruct"]:
            try:
                n_llm = ChatNVIDIA(
                    model=n_model,
                    nvidia_api_key=os.getenv("NVIDIA_API_KEY"),
                    temperature=0.2,
                    max_retries=0,
                    timeout=12
                )
                res = n_llm.invoke(prompt_text)
                txt = _extract_llm_text(res.content if res else "")
                if len(txt) > 20:
                    return {"summary": txt, "model": f"{n_model} (NVIDIA NIM)"}
            except Exception as n_err:
                _safe_print(f"[WARN] NVIDIA LLM ({n_model}) error: {n_err}")

    # 8. Tier 6: Statistical Analytical Heuristic (Instant, guaranteed fallback)
    items = pie_slices or data_points
    if items:
        valid_items = [it for it in items if isinstance(it.get("val"), (int, float))]
        if valid_items:
            sorted_items = sorted(valid_items, key=lambda x: x.get("val", 0), reverse=True)
            top_item = sorted_items[0]
            bottom_item = sorted_items[-1]
            tot = total_val if total_val is not None else sum(it.get("val", 0) for it in valid_items)
            avg = tot / len(valid_items) if valid_items else 0

            top_pct = top_item.get("pct_str") or (f"{(top_item.get('val', 0)/tot*100):.1f}%" if tot > 0 else "")
            bot_pct = bottom_item.get("pct_str") or (f"{(bottom_item.get('val', 0)/tot*100):.1f}%" if tot > 0 else "")

            heuristic_bullets = [
                f"• {top_item.get('label')} has the highest value at {top_item.get('val', 0):,.2f}{f' ({top_pct} of total)' if top_pct else ''}.",
                f"• {bottom_item.get('label')} recorded the lowest value at {bottom_item.get('val', 0):,.2f}{f' ({bot_pct} of total)' if bot_pct else ''}.",
                f"• The difference between the highest ({top_item.get('label')}) and lowest ({bottom_item.get('label')}) is {(top_item.get('val', 0) - bottom_item.get('val', 0)):,.2f}.",
                f"• Total combined value across all {len(valid_items)} recorded categories is {tot:,.2f} with an average of {avg:,.2f}."
            ]
            return {"summary": "\n".join(heuristic_bullets), "model": "Smart Heuristic Analyst"}

    return {
        "summary": f"• Visualization '{title}' ({chart_type}) rendered with verified aggregated dataset points.",
        "model": "Fallback Summary"
    }
