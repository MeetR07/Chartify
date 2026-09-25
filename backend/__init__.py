"""
backend — Chartify core library package.

This package contains all server-side logic modules:

  charts        — Matplotlib/Seaborn rendering engine (2D & 3D chart types)
  agent         — LLM agent, tool-calling chains, and summarization
  profiler      — Dataset schema detection and statistical profiling
  planner       — NL→query planning (rule-based + LLM-assisted)
  engine        — Deterministic data aggregation and result validation
  chart_planner — Chart type selection, data contract builder (v1.1)

Public API re-exports
---------------------
Import the most commonly used symbols directly from `backend`:

    from backend.charts import generate_chart
    from backend.chart_planner import ChartPlanner, build_unified_data_contract
    from backend.profiler import profile_dataset, get_dataset_schema
    from backend.engine import DeterministicDataEngine, ResultValidator
    from backend.planner import LLMQueryPlanner, RuleBasedFallbackPlanner
    from backend.agent import chart_chain, summarize_chart_with_llm

No circular imports exist in this package — the dependency graph is a clean DAG:
  agent  →  charts
  planner  →  profiler
  chart_planner  →  engine
  charts / engine / profiler  →  (no internal deps)
"""

# -- Rendering --
from .charts import generate_chart, smart_preprocess_data, detect_query_intent

# -- Agent / LLM --
from .agent import (
    invoke_ai_with_fallbacks,
    heuristic_chart_extractor,
    chart_chain,
    ai_chain,
    execute_chart_tool,
    summarize_chart_with_llm,
)

# -- Data pipeline --
from .profiler import profile_dataset, get_dataset_schema, clear_profile_cache
from .planner import (
    LLMQueryPlanner,
    PlanValidator,
    RuleBasedFallbackPlanner,
    check_column_ambiguity,
    check_missing_column,
)
from .engine import (
    DeterministicDataEngine,
    ResultValidator,
    compute_data_signature,
    sort_chronologically,
)
from .chart_planner import ChartPlanner, build_unified_data_contract, SUPPORTED_CHARTS

__all__ = [
    # charts
    "generate_chart",
    "smart_preprocess_data",
    "detect_query_intent",
    # agent
    "invoke_ai_with_fallbacks",
    "heuristic_chart_extractor",
    "chart_chain",
    "ai_chain",
    "execute_chart_tool",
    "summarize_chart_with_llm",
    # profiler
    "profile_dataset",
    "get_dataset_schema",
    "clear_profile_cache",
    # planner
    "LLMQueryPlanner",
    "PlanValidator",
    "RuleBasedFallbackPlanner",
    "check_column_ambiguity",
    "check_missing_column",
    # engine
    "DeterministicDataEngine",
    "ResultValidator",
    "compute_data_signature",
    "sort_chronologically",
    # chart_planner
    "ChartPlanner",
    "build_unified_data_contract",
    "SUPPORTED_CHARTS",
]
