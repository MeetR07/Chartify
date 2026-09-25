import os
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

ACTIVE_DATASET_PATH = os.path.join(os.path.dirname(__file__), "active_dataset.csv")

if os.path.exists(ACTIVE_DATASET_PATH):
    try:
        df = pd.read_csv(ACTIVE_DATASET_PATH)
    except Exception:
        df = pd.DataFrame({
            "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
            "Sales": [15000, 22000, 18000, 27000, 31000],
            "Profit": [3000, 4500, -1200, 6000, 7500],
            "Region": ["North", "South", "North", "West", "South"]
        })
else:
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "Sales": [15000, 22000, 18000, 27000, 31000],
        "Profit": [3000, 4500, -1200, 6000, 7500],
        "Region": ["North", "South", "North", "West", "South"]
    })

# ==============================================================================
# 2. MODULAR RE-EXPORTS (100% Backward Compatibility with server.py and existing code)
# ==============================================================================

from backend.charts import generate_chart, smart_preprocess_data
from backend.agent import (
    invoke_ai_with_fallbacks,
    heuristic_chart_extractor,
    chart_chain,
    ai_chain,
    execute_chart_tool,
    summarize_chart_with_llm
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
    "summarize_chart_with_llm",
    "process_query",
    "start_assistant"
]


# ==============================================================================
# 3. INTERACTIVE CLI ASSISTANT & LLM CHART SUMMARIZER
# ==============================================================================

def process_query(user_query: str):
    """Generates chart from user query, feeds it to the LLM, and prints executive summary in terminal."""
    print(f"\n[Query] '{user_query}'")
    output = chart_chain.invoke({
        "columns": list(df.columns),
        "sample_data": df.head(2).to_dict(orient="records"),
        "user_query": user_query
    })

    tokens = output.get("tokens", {})
    print(f"Tokens Used : Total = {tokens.get('total', 0)} (Input: {tokens.get('input', 0)}, Output: {tokens.get('output', 0)})")

    if output.get("tool_called"):
        print(f"Tool Chosen : generate_chart")
        print(f"Parameters  : {output.get('tool_args')}")
        print(f"Result      : {output.get('result')}")

        # Feed the generated chart directly to the LLM for analytical summary
        print("\n" + "=" * 65)
        print("🤖 FEEDING GENERATED CHART TO LLM FOR EXECUTIVE SUMMARY...")
        print("=" * 65)
        summary_result = summarize_chart_with_llm(output, user_query=user_query, df=df)
        print(f"\n[AI Visual & Data Analysis — Engine: {summary_result.get('model', 'AI')}]")
        print("-" * 65)
        print(summary_result.get("summary"))
        print("=" * 65 + "\n")
    else:
        print(f"\nAI: {output.get('ai_response')}")


def start_assistant():
    print("\n" + "=" * 65)
    print("AI Data Visualization & LLM Summarizer Assistant Ready!")
    print(f"Dataset Columns: {list(df.columns)}")
    print("Examples:")
    print("   - 'Generate a donut chart of Sales across Month'")
    print("   - 'Create a treemap of Sales by Region'")
    print("   - 'Create a waterfall chart of Monthly Profit'")
    print("   - Type 'exit' to quit")
    print("=" * 65)

    while True:
        try:
            user_query = input("\nEnter your chart request: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting assistant. Goodbye!")
            break

        if not user_query:
            continue
        if user_query.lower() in ["exit", "quit", "q"]:
            print("Exiting assistant. Goodbye!")
            break

        process_query(user_query)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_query = " ".join(sys.argv[1:])
        process_query(cli_query)
    else:
        start_assistant()
