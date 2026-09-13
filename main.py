import sys
import pandas as pd
from dotenv import load_dotenv

# Ensure UTF-8 encoding on Windows console to prevent UnicodeEncodeError ('charmap' codec)
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
# 1. CORE DATASET
# ==============================================================================

df = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
    "Sales": [15000, 22000, 18000, 27000, 31000],
    "Profit": [3000, 4500, -1200, 6000, 7500],
    "Region": ["North", "South", "North", "West", "South"]
})

# ==============================================================================
# 2. MODULAR RE-EXPORTS (100% Backward Compatibility with server.py and existing code)
# ==============================================================================

from charts import generate_chart, smart_preprocess_data
from agent import (
    invoke_ai_with_fallbacks,
    heuristic_chart_extractor,
    chart_chain,
    ai_chain,
    execute_chart_tool
)

# Export list
__all__ = [
    "df",
    "generate_chart",
    "smart_preprocess_data",
    "invoke_ai_with_fallbacks",
    "heuristic_chart_extractor",
    "chart_chain",
    "ai_chain",
    "execute_chart_tool",
    "start_assistant"
]


# ==============================================================================
# 3. INTERACTIVE CLI ASSISTANT
# ==============================================================================

def start_assistant():
    print("\n" + "=" * 60)
    print("AI Data Visualization Assistant Ready (LCEL Runnable Chain)!")
    print(f"Dataset Columns: {list(df.columns)}")
    print("Examples:")
    print("   - 'Generate a treemap of Sales by Region'")
    print("   - 'Create a waterfall chart of Monthly Profit'")
    print("   - Type 'exit' to quit")
    print("=" * 60)

    while True:
        user_query = input("\nEnter your chart request: ").strip()

        if not user_query:
            continue
        if user_query.lower() in ["exit", "quit", "q"]:
            print("Exiting assistant. Goodbye!")
            break

        output = chart_chain.invoke({
            "columns": list(df.columns),
            "sample_data": df.head(2).to_dict(orient="records"),
            "user_query": user_query
        })

        tokens = output.get("tokens", {})
        print(f"\nTokens Used: Total = {tokens.get('total', 0)} (Input: {tokens.get('input', 0)}, Output: {tokens.get('output', 0)})")

        if output.get("tool_called"):
            print(f"Tool Chosen : generate_chart")
            print(f"Parameters  : {output.get('tool_args')}")
            print(f"Result      : {output.get('result')}")
        else:
            print(f"\nAI: {output.get('ai_response')}")


if __name__ == "__main__":
    start_assistant()
