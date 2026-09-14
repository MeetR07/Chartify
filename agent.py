import os
import sys
import time
from dotenv import load_dotenv

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq

from charts import generate_chart

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
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
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
    ("waterfall",    "waterfall"),
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


# ==============================================================================
# MODEL CHAIN FACTORIES
# ==============================================================================

def create_model_chain(model_name: str):
    """Returns a Gemini model bound to the generate_chart tool."""
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=0,
    )
    return llm.bind_tools([generate_chart])


def create_mistral_chain(model_name: str = "ministral-8b-latest"):
    """Returns a Mistral model bound to the generate_chart tool."""
    llm = ChatMistralAI(
        model=model_name,
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0,
        max_retries=0,
    )
    return llm.bind_tools([generate_chart])


def create_groq_chain(model_name: str = "llama-3.3-70b-versatile"):
    """Returns a Groq Llama-3 model bound to the generate_chart tool."""
    llm = ChatGroq(
        model=model_name,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_retries=0,
    )
    return llm.bind_tools([generate_chart])


def create_freellmapi_chain(model_name: str = "auto"):
    """
    [TEST] Returns a FreeLLMAPI chain — OpenAI-compatible local proxy that
    aggregates 34 free LLM providers (635 endpoints, 7.4B tokens/month).
    Requires freellmapi server running locally: npx freellmapi
    Ref: https://github.com/tashfeenahmed/freellmapi
    """
    llm = ChatOpenAI(
        model=model_name,
        base_url=FREELLMAPI_BASE_URL,
        api_key=FREELLMAPI_API_KEY,
        temperature=0,
        max_retries=0,
        timeout=15,
    )
    return llm.bind_tools([generate_chart])


# Pre-initialize all chains ONCE at startup so cascade has zero per-request overhead
_GEMINI_CHAINS      = {m: create_model_chain(m)    for m in CANDIDATE_MODELS}
_MISTRAL_CHAINS     = {m: create_mistral_chain(m)  for m in MISTRAL_MODELS}
_GROQ_CHAINS        = {m: create_groq_chain(m)     for m in GROQ_MODELS}
_FREELLMAPI_CHAINS  = {m: create_freellmapi_chain(m) for m in FREELLMAPI_MODELS}

# Primary model exposed for backward compatibility with main.py / chart_chain
llm            = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0,
                                        google_api_key=os.getenv("GOOGLE_API_KEY"), max_retries=0)
llm_with_tools = llm.bind_tools([generate_chart])


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

    # ── Column metadata (dtype-tagged) ──────────────────────────────────────
    col_lines = []
    for c in cols:
        if df is not None and c in df.columns:
            dtype = df[c].dtype
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
  • For "X by Y" queries: x_col = the grouping/category, y_col = the measure.
  • For "X vs Y" queries: x_col = first mentioned, y_col = second mentioned.
  • hue_col = grouping/color split (optional, only when user implies comparison).
  • If user does NOT mention a column explicitly, infer the best match by dtype.
  • Prefer categorical columns for x_col, numeric columns for y_col.
  • For time-related queries pick the datetime or ordered categorical column as x_col.

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
        _safe_print("[INFO] Trying FreeLLMAPI (34 providers, 635 models)...")
        result, label = _try_model_cascade(_FREELLMAPI_CHAINS, prompt_val, "freellmapi")
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
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    CIRCUIT_BREAKER["gemini_quota_exhausted_until"] = now + CIRCUIT_BREAKER["cooldown_seconds"]
                    _safe_print("[INFO] Gemini quota hit (429). Circuit breaker tripped for 60s.")
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

    # 3. Groq
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

    chart_type = next((ctype for pattern, ctype in CHART_PATTERNS if pattern in q), "bar")

    num_cols = [c for c in current_df.columns if pd.api.types.is_numeric_dtype(current_df[c])]
    cat_cols = [c for c in current_df.columns if not pd.api.types.is_numeric_dtype(current_df[c])]
    all_cols = list(current_df.columns)

    mentioned = [c for c in all_cols if c.lower() in q]
    x_col = y_col = None

    if len(mentioned) >= 2:
        c1, c2 = mentioned[0], mentioned[1]
        if " by " in q:
            # "Sales by Month" -> y=Sales, x=Month
            parts = q.split(" by ", 1)
            if c1.lower() in parts[0] and c2.lower() in parts[1]:
                y_col, x_col = c1, c2
            elif c2.lower() in parts[0] and c1.lower() in parts[1]:
                y_col, x_col = c2, c1
        elif " vs " in q:
            # "Month vs Sales" -> x=Month, y=Sales
            parts = q.split(" vs ", 1)
            x_col, y_col = (c1, c2) if c1.lower() in parts[0] else (c2, c1)

        if not x_col:  # fallback: assign by dtype
            if   c1 in cat_cols and c2 in num_cols: x_col, y_col = c1, c2
            elif c2 in cat_cols and c1 in num_cols: x_col, y_col = c2, c1
            else:                                    x_col, y_col = c1, c2

    elif len(mentioned) == 1:
        c = mentioned[0]
        if c in cat_cols:
            x_col, y_col = c, (num_cols[0] if num_cols else None)
        else:
            y_col = c
            x_col = cat_cols[0] if cat_cols else (num_cols[0] if num_cols[0] != c else None)
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

    return {"chart_type": chart_type, "x_col": x_col, "y_col": y_col, "title": title}


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


# Pure LLM chain
ai_chain = RunnableLambda(format_prompt_inputs) | prompt_template | llm_with_tools

# Full pipeline: formatter -> prompt -> LLM -> tool executor
chart_chain = ai_chain | RunnableLambda(execute_chart_tool)
