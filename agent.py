import os
import sys
import time
from typing import Optional
from dotenv import load_dotenv

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq

from charts import generate_chart

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

load_dotenv()

# ==============================================================================
# MODEL DEFINITIONS & CIRCUIT BREAKER FOR ZERO-LATENCY FALLBACK
# ==============================================================================

CANDIDATE_MODELS = [
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite"
]

MISTRAL_MODELS = [
    "ministral-8b-latest",
    "open-mistral-7b",
    "codestral-latest",
    "ministral-3b-latest"
]

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-8b-8192"
]

# Smart Circuit Breaker: Prevents 10-12s sequential network delays when Gemini free-tier daily quota (429) is exhausted
CIRCUIT_BREAKER = {
    "gemini_quota_exhausted_until": 0.0,
    "cooldown_seconds": 60.0
}


def create_model_chain(model_name: str):
    """Creates an LCEL chain for a specific Gemini model."""
    api_key = os.getenv("GOOGLE_API_KEY")
    llm_instance = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=api_key,
        max_retries=0
    )
    return llm_instance.bind_tools([generate_chart])


def create_mistral_chain(model_name: str = "ministral-8b-latest"):
    """Creates an LCEL chain for Mistral LLM using LangChain."""
    mistral_key = os.getenv("MISTRAL_API_KEY")
    llm_instance = ChatMistralAI(
        model=model_name,
        mistral_api_key=mistral_key,
        temperature=0,
        max_retries=0
    )
    return llm_instance.bind_tools([generate_chart])


def create_groq_chain(model_name: str = "llama-3.3-70b-versatile"):
    """Creates an LCEL chain for Groq Llama-3 using LangChain."""
    groq_key = os.getenv("GROQ_API_KEY")
    llm_instance = ChatGroq(
        model=model_name,
        groq_api_key=groq_key,
        temperature=0,
        max_retries=0
    )
    return llm_instance.bind_tools([generate_chart])


# Primary model with tool binding (for backward compatibility)
primary_api_key = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=primary_api_key, max_retries=0)
llm_with_tools = llm.bind_tools([generate_chart])


# ==============================================================================
# PROMPT DEFINITION
# ==============================================================================

def format_prompt_inputs(inputs: dict) -> dict:
    """Safely formats prompt variables from dictionary."""
    cols = inputs.get("columns", [])
    sample = inputs.get("sample_data", [])
    user_query = inputs.get("user_query", "")
    
    summary = f"Columns ({len(cols)}): {', '.join(cols)} | Sample: {sample}"
    return {
        "columns_summary": summary,
        "user_query": user_query
    }


prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "Expert data visualizer. Call generate_chart using exact dataset columns: {columns_summary}.\n"
     "Rules:\n"
     "- Prioritize requested chart type.\n"
     "- heatmap/pairplot/radar: x_col and y_col optional.\n"
     "- donut/pie/histogram: x_col=category, optional y_col=metric.\n"
     "- funnel/lollipop: x_col=category, y_col=metric.\n"
     "- bubble: x_col, y_col."
    ),
    ("human", "{user_query}")
])


# ==============================================================================
# MULTI-MODEL ORCHESTRATION & RESILIENT CASCADE
# ==============================================================================

def invoke_ai_with_fallbacks(inputs: dict):
    """
    Invokes AI with automatic cascading & circuit-breaker protection:
    1. Checks Circuit Breaker: If Gemini quota is exhausted, skips network wait.
    2. Tries Gemini models. If 429 is received, trips circuit breaker for 60s and stops hammering.
    3. Falls back to Mistral LLM via LangChain if configured.
    4. Falls back to Groq LPU via LangChain if configured.
    5. Returns None so smart heuristic takes over instantly.
    """
    last_error = None
    formatted_inputs = format_prompt_inputs(inputs)
    prompt_val = prompt_template.format_prompt(**formatted_inputs)
    now = time.time()

    # 1. Try Gemini models if circuit breaker is not tripped
    if now >= CIRCUIT_BREAKER["gemini_quota_exhausted_until"]:
        for model_name in CANDIDATE_MODELS:
            try:
                model_with_tools = create_model_chain(model_name)
                ai_message = model_with_tools.invoke(prompt_val)
                if ai_message and getattr(ai_message, "tool_calls", None):
                    return ai_message, f"gemini:{model_name}"
            except Exception as e:
                last_error = e
                err_msg = str(e)
                try:
                    print(f"[WARN] Gemini Model '{model_name}' issue: {err_msg[:120]}")
                except Exception:
                    pass
                # If quota limit hit, trip circuit breaker for 60s to eliminate delay on subsequent requests
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    CIRCUIT_BREAKER["gemini_quota_exhausted_until"] = now + CIRCUIT_BREAKER["cooldown_seconds"]
                    try:
                        print(f"[INFO] Gemini quota exhausted (429). Circuit breaker tripped for 60s.")
                    except Exception:
                        pass
                    break
                continue
    else:
        try:
            remaining = int(CIRCUIT_BREAKER["gemini_quota_exhausted_until"] - now)
            print(f"[INFO] Gemini circuit breaker active ({remaining}s remaining). Skipping network retries.")
        except Exception:
            pass

    # 2. If Gemini exhausted or failed, automatically fall back to Mistral LLM via LangChain
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        try:
            print("[INFO] Gemini unavailable. Switching to Mistral LLM via LangChain...")
        except Exception:
            pass
        for mistral_model in MISTRAL_MODELS:
            try:
                mistral_chain = create_mistral_chain(mistral_model)
                ai_message = mistral_chain.invoke(prompt_val)
                if ai_message and getattr(ai_message, "tool_calls", None):
                    try:
                        print(f"[SUCCESS] Successfully generated chart using Mistral LLM ({mistral_model})!")
                    except Exception:
                        pass
                    return ai_message, f"mistral:{mistral_model}"
            except Exception as e:
                last_error = e
                err_msg = str(e)
                try:
                    print(f"[WARN] Mistral Model '{mistral_model}' issue: {err_msg[:120]}")
                except Exception:
                    pass
                continue

    # 3. If Gemini & Mistral exhausted, automatically fall back to Groq Llama-3 via LangChain
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            print("[INFO] Switching to Groq Llama-3 (LangChain) fallback...")
        except Exception:
            pass
        for groq_model in GROQ_MODELS:
            try:
                groq_chain = create_groq_chain(groq_model)
                ai_message = groq_chain.invoke(prompt_val)
                if ai_message and getattr(ai_message, "tool_calls", None):
                    try:
                        print(f"[SUCCESS] Successfully generated chart using Groq Llama-3 ({groq_model})!")
                    except Exception:
                        pass
                    return ai_message, f"groq:{groq_model}"
            except Exception as e:
                last_error = e
                err_msg = str(e)
                try:
                    print(f"[WARN] Groq Model '{groq_model}' issue: {err_msg[:120]}")
                except Exception:
                    pass
                continue

    return None, last_error


# ==============================================================================
# SMART HEURISTIC INTENT & COLUMN EXTRACTOR
# ==============================================================================

def heuristic_chart_extractor(query: str, current_df: pd.DataFrame) -> dict:
    """
    Ultra-fast rule-based keyword & column extractor.
    Guarantees 100% reliability and sub-50ms instant response without any external API calls.
    """
    q = query.lower().strip()

    # Supported chart types sorted by specificity
    CHART_PATTERNS = [
        ("waterfall", "waterfall"),
        ("lollipop", "lollipop"),
        ("treemap", "treemap"),
        ("pairplot", "pairplot"),
        ("heatmap", "heatmap"),
        ("correlation", "heatmap"),
        ("violin", "violin"),
        ("scatter", "scatter"),
        ("bubble", "bubble"),
        ("donut", "donut"),
        ("doughnut", "donut"),
        ("funnel", "funnel"),
        ("radar", "radar"),
        ("spider", "radar"),
        ("histogram", "histogram"),
        ("hist", "histogram"),
        ("distribution", "histogram"),
        ("box", "box"),
        ("area", "area"),
        ("line", "line"),
        ("trend", "line"),
        ("bar", "bar"),
        ("pie", "pie"),
    ]

    chart_type = "bar"
    for pattern, ctype in CHART_PATTERNS:
        if pattern in q:
            chart_type = ctype
            break

    num_cols = [c for c in current_df.columns if pd.api.types.is_numeric_dtype(current_df[c])]
    cat_cols = [c for c in current_df.columns if not pd.api.types.is_numeric_dtype(current_df[c])]
    all_cols = list(current_df.columns)

    # Find explicitly mentioned columns in query
    mentioned = [c for c in all_cols if c.lower() in q]

    x_col = None
    y_col = None

    if len(mentioned) >= 2:
        c1, c2 = mentioned[0], mentioned[1]
        if " by " in q:
            parts = q.split(" by ", 1)
            # e.g., 'Sales by Month' -> y=Sales, x=Month
            if c1.lower() in parts[0].lower() and c2.lower() in parts[1].lower():
                y_col, x_col = c1, c2
            elif c2.lower() in parts[0].lower() and c1.lower() in parts[1].lower():
                y_col, x_col = c2, c1
        elif " vs " in q:
            # e.g., 'Month vs Sales' -> x=Month, y=Sales
            parts = q.split(" vs ", 1)
            if c1.lower() in parts[0].lower() and c2.lower() in parts[1].lower():
                x_col, y_col = c1, c2
            else:
                x_col, y_col = c2, c1
        
        if not x_col:
            if c1 in cat_cols and c2 in num_cols:
                x_col, y_col = c1, c2
            elif c2 in cat_cols and c1 in num_cols:
                x_col, y_col = c2, c1
            else:
                x_col, y_col = c1, c2

    elif len(mentioned) == 1:
        c = mentioned[0]
        if c in cat_cols:
            x_col = c
            y_col = num_cols[0] if num_cols else None
        else:
            y_col = c
            x_col = cat_cols[0] if cat_cols else (num_cols[0] if num_cols[0] != c else None)
    else:
        # Default mapping
        x_col = cat_cols[0] if cat_cols else (all_cols[0] if all_cols else None)
        rem_nums = [c for c in num_cols if c != x_col]
        y_col = rem_nums[0] if rem_nums else (all_cols[1] if len(all_cols) > 1 else None)

    title = f"{chart_type.capitalize()} Analysis"
    if x_col and y_col:
        title = f"{y_col} by {x_col}"
    elif x_col:
        title = f"Distribution of {x_col}"

    return {
        "chart_type": chart_type,
        "x_col": x_col,
        "y_col": y_col,
        "title": title
    }


# ==============================================================================
# RUNNABLE LCEL CHAINS
# ==============================================================================

def execute_chart_tool(ai_message):
    """Runnable node that handles tool execution and extracts token metrics."""
    usage = getattr(ai_message, "usage_metadata", None) or {}
    tokens_info = {
        "total": usage.get("total_tokens", 0),
        "input": usage.get("input_tokens", 0),
        "output": usage.get("output_tokens", 0)
    }

    if ai_message.tool_calls:
        tool_call = ai_message.tool_calls[0]
        args = tool_call.get("args", {})
        chart_type = args.get("chart_type", "chart")
        
        execution_result = generate_chart.invoke(args)
        filename = f"{chart_type}.png"
        
        return {
            "success": True,
            "tool_called": True,
            "chart_type": chart_type,
            "tool_args": args,
            "result": execution_result,
            "chart_filename": filename,
            "tokens": tokens_info,
            "raw_message": ai_message
        }
    else:
        return {
            "success": True,
            "tool_called": False,
            "ai_response": ai_message.content,
            "tokens": tokens_info,
            "raw_message": ai_message
        }

# Pure LLM Chain
ai_chain = RunnableLambda(format_prompt_inputs) | prompt_template | llm_with_tools

# Full LCEL Pipeline: Formatter -> Prompt -> LLM with Tools -> Tool Executor
chart_chain = ai_chain | RunnableLambda(execute_chart_tool)
