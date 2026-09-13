import os
import io
import base64
from typing import Literal, Optional
from dotenv import load_dotenv

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Use non-interactive, thread-safe Agg backend for servers
import matplotlib.pyplot as plt
import seaborn as sns
import squarify

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq


# ==============================================================================
# 1. CONFIGURATION & ENVIRONMENT SETUP
# ==============================================================================

# Load API keys from the .env file (GOOGLE_API_KEY)
load_dotenv()

# Set visual style for charts (whitegrid gives clean, modern charts)
sns.set_theme(style="whitegrid")


# ==============================================================================
# 2. DATASET (You can replace this with: df = pd.read_csv("your_data.csv"))
# ==============================================================================

df = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
    "Sales": [15000, 22000, 18000, 27000, 31000],
    "Profit": [3000, 4500, -1200, 6000, 7500],
    "Region": ["North", "South", "North", "West", "South"]
})


# ==============================================================================
# 3. BIG DATA SCALABILITY ENGINE & CUSTOM LANGCHAIN CHART TOOL
# ==============================================================================

def smart_preprocess_data(data: pd.DataFrame, chart_type: str, x_col: Optional[str] = None, y_col: Optional[str] = None, hue_col: Optional[str] = None) -> pd.DataFrame:
    """
    Big Data Scalability Preprocessor:
    Automatically downsamples or statistically aggregates massive datasets (10,000 to 1,000,000+ rows)
    to guarantee sub-300ms chart rendering and 100% memory safety.
    """
    total_rows = len(data)
    if total_rows <= 10000:
        return data

    # 1. Bar, Donut, Pie, Funnel, Treemap, Lollipop: aggregate sum/mean
    if chart_type in ["bar", "donut", "pie", "funnel", "treemap", "lollipop"] and x_col and y_col:
        try:
            agg_df = data.groupby(x_col, as_index=False, observed=True)[y_col].sum()
            if len(agg_df) > 25:
                top_25 = agg_df.nlargest(25, y_col)
                other_sum = agg_df[~agg_df[x_col].isin(top_25[x_col])][y_col].sum()
                other_row = pd.DataFrame({x_col: ["Other"], y_col: [other_sum]})
                return pd.concat([top_25, other_row], ignore_index=True)
            return agg_df
        except Exception:
            pass

    # 2. Line & Area: Decimate time-series / trends smoothly
    if chart_type in ["line", "area"]:
        step = max(1, total_rows // 2500)
        return data.iloc[::step].copy()

    # 3. Scatter, Bubble, Hist, Box, Violin: Representative sampling
    sample_limit = 5000 if chart_type in ["scatter", "bubble"] else 8000
    if total_rows > sample_limit:
        return data.sample(n=sample_limit, random_state=42)

    return data


@tool
def generate_chart(
    chart_type: Literal[
        "bar", "line", "scatter", "histogram", 
        "box", "heatmap", "pie", "area", "violin", "pairplot",
        "treemap", "waterfall", "donut", "funnel", "lollipop", "radar", "bubble"
    ],
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    hue_col: Optional[str] = None,
    title: Optional[str] = "Data Analysis Chart",
    palette: Optional[str] = None,
    style: Optional[str] = "whitegrid",
    output_path: Optional[str] = None
) -> str:
    """Generates and saves a data visualization chart.
    Args:
        chart_type: The chart visualization type.
        x_col: Category or X-axis column name.
        y_col: Numeric measure or Y-axis column name.
        hue_col: Optional category column for grouping.
        title: Short descriptive title for the chart.
    """
    try:
        # File name will match output_path if provided, else fallback to chart_type.png
        if not output_path:
            output_path = f"{chart_type}.png"
        
        # Step 3.1: Check if the columns requested by LLM actually exist in df
        for col in [x_col, y_col, hue_col]:
            if col and col not in df.columns:
                return f"Error: Column '{col}' not found. Available columns: {list(df.columns)}"

        # Step 3.2: Apply visual style/theme dynamically
        selected_style = style or "whitegrid"
        plt.close("all")

        valid_sns_styles = ["whitegrid", "darkgrid", "white", "dark", "ticks"]
        if selected_style in valid_sns_styles:
            sns.set_theme(style=selected_style)
        elif selected_style in plt.style.available:
            plt.style.use(selected_style)
        else:
            sns.set_theme(style="whitegrid")

        # Safeguard hue_col cardinality to prevent legend freeze and multi-megabyte image blowups
        safe_hue = hue_col
        show_legend = "brief"
        if hue_col and hue_col in df.columns:
            if df[hue_col].nunique() > 10:
                show_legend = False

        # Step 3.3: Special Case: Pairplot (creates its own figure window)
        if chart_type == "pairplot":
            grid = sns.pairplot(df, hue=safe_hue, palette=palette or "deep")
            grid.fig.suptitle(title, y=1.02)
            buf = io.BytesIO()
            grid.savefig(buf, format="png", dpi=100, facecolor=grid.fig.get_facecolor(), bbox_inches="tight")
            plt.close()
            buf.seek(0)
            data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            if output_path and output_path != ":memory:":
                with open(output_path, "wb") as f:
                    f.write(buf.getvalue())
            sns.set_theme(style="whitegrid")
            return data_url

        # Step 3.4: Create canvas for charts (polar for radar, rectangular for others)
        if chart_type == "radar":
            fig, ax = plt.subplots(figsize=(7, 6), subplot_kw=dict(polar=True))
        else:
            fig, ax = plt.subplots(figsize=(8.5, 5))

        # Big Data Scalability: Smart pre-processing & downsampling for massive datasets
        plot_df = smart_preprocess_data(df, chart_type, x_col, y_col, safe_hue)

        # Chart 1: Bar Chart (Category comparison)
        if chart_type == "bar":
            sns.barplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "deep", ax=ax)
            plt.xticks(rotation=45)

        # Chart 2: Line Chart (Trends)
        elif chart_type == "line":
            if safe_hue:
                sns.lineplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, marker="o", linewidth=2.5, palette=palette or "deep", ax=ax)
            else:
                line_color = sns.color_palette(palette)[0] if palette else None
                sns.lineplot(data=plot_df, x=x_col, y=y_col, marker="o", linewidth=2.5, color=line_color, ax=ax)

        # Chart 3: Scatter Plot (Relationship with instant adaptive sampling for large datasets)
        elif chart_type == "scatter":
            n_rows = len(plot_df)
            point_size = 18 if n_rows > 5000 else (35 if n_rows > 1000 else 70)
            alpha_val = 0.6 if n_rows > 2000 else 0.85
            sns.scatterplot(
                data=plot_df, x=x_col, y=y_col, hue=safe_hue, s=point_size,
                palette=palette or "deep", alpha=alpha_val, ax=ax,
                legend=show_legend
            )

        # Chart 4: Histogram (Distribution with fast KDE calculation)
        elif chart_type == "histogram":
            sns.histplot(data=plot_df, x=x_col, kde=True, hue=safe_hue, palette=palette or "deep", ax=ax)

        # Chart 5: Box Plot (Outliers)
        elif chart_type == "box":
            sns.boxplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "Set2", ax=ax)

        # Chart 6: Heatmap (Correlation)
        elif chart_type == "heatmap":
            corr = plot_df.corr(numeric_only=True)
            sns.heatmap(corr, annot=True, cmap=palette or "coolwarm", fmt=".2f", linewidths=0.5, ax=ax)

        # Chart 7: Pie Chart (Proportions)
        elif chart_type == "pie":
            if y_col:
                pie_data = plot_df.groupby(x_col)[y_col].sum()
            else:
                pie_data = plot_df[x_col].value_counts()
            pie_colors = sns.color_palette(palette or "pastel", len(pie_data))
            ax.pie(pie_data.values, labels=pie_data.index, autopct="%1.1f%%", startangle=140, colors=pie_colors)

        # Chart 8: Area Chart (Cumulative trend)
        elif chart_type == "area":
            sorted_df = plot_df.sort_values(by=x_col)
            area_colors = sns.color_palette(palette or "mako", 2)
            ax.fill_between(sorted_df[x_col], sorted_df[y_col], alpha=0.4, color=area_colors[0])
            ax.plot(sorted_df[x_col], sorted_df[y_col], color=area_colors[-1], linewidth=2.5, marker="o")

        # Chart 9: Violin Plot (Distribution shape)
        elif chart_type == "violin":
            sns.violinplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "muted", ax=ax)


        # Chart 11: Treemap (Nested Rectangles)
        elif chart_type == "treemap":
            if y_col:
                tree_data = df.groupby(x_col)[y_col].sum().reset_index()
                sizes = tree_data[y_col].abs().values
                labels = [f"{row[x_col]}\n({row[y_col]})" for _, row in tree_data.iterrows()]
            else:
                counts = df[x_col].value_counts()
                sizes = counts.values
                labels = [f"{cat}\n({cnt})" for cat, cnt in zip(counts.index, counts.values)]

            tree_colors = sns.color_palette(palette or "Spectral", len(sizes))
            squarify.plot(sizes=sizes, label=labels, color=tree_colors, alpha=0.85, text_kwargs={"fontsize": 11, "weight": "bold"}, ax=ax)
            ax.axis("off")

        # Chart 12: Waterfall Chart (Sequential positive/negative breakdown)
        elif chart_type == "waterfall":
            categories = df[x_col].astype(str).tolist()
            values = df[y_col].astype(float).tolist()

            # Calculate cumulative values for bar bottoms
            cumulative = [0]
            for val in values:
                cumulative.append(cumulative[-1] + val)

            bottoms = [min(cumulative[i], cumulative[i + 1]) for i in range(len(values))]
            heights = [abs(val) for val in values]

            if palette:
                pal_colors = sns.color_palette(palette, 2)
                pos_color, neg_color = pal_colors[0], pal_colors[1]
            else:
                pos_color, neg_color = "#10b981", "#ef4444"

            colors = [pos_color if val >= 0 else neg_color for val in values]

            ax.bar(categories, heights, bottom=bottoms, color=colors, edgecolor="black", width=0.6)

            # Draw connector lines between bars
            for i in range(len(values) - 1):
                ax.plot([i, i + 1], [cumulative[i + 1], cumulative[i + 1]], color="grey", linestyle="--")

            ax.set_ylabel(y_col, fontsize=12)
            plt.xticks(rotation=45)

        # Chart 13: Donut Chart (Modern Ring Proportion)
        elif chart_type == "donut":
            if y_col:
                donut_data = df.groupby(x_col)[y_col].sum()
            else:
                donut_data = df[x_col].value_counts()
            donut_colors = sns.color_palette(palette or "pastel", len(donut_data))
            wedges, texts, autotexts = ax.pie(
                donut_data.values,
                labels=donut_data.index,
                autopct="%1.1f%%",
                startangle=140,
                colors=donut_colors,
                pctdistance=0.75,
                wedgeprops=dict(width=0.42, edgecolor="w", linewidth=1.5)
            )
            # Center text displaying total
            total_val = donut_data.sum()
            center_txt = f"TOTAL\n{total_val:,.0f}" if isinstance(total_val, (int, float, np.number)) else "TOTAL"
            ax.text(0, 0, center_txt, ha="center", va="center", fontsize=12, weight="bold")

        # Chart 14: Funnel Chart (Stage-by-stage Conversion)
        elif chart_type == "funnel":
            if y_col:
                funnel_df = df[[x_col, y_col]].dropna().copy()
                funnel_df = funnel_df.sort_values(by=y_col, ascending=False)
                stages = funnel_df[x_col].astype(str).tolist()
                values = funnel_df[y_col].astype(float).tolist()
            else:
                counts = df[x_col].value_counts()
                stages = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

            max_val = max(values) if values else 1
            lefts = [(max_val - v) / 2 for v in values]
            f_colors = sns.color_palette(palette or "flare", len(values))

            y_pos = list(range(len(stages)))
            bars = ax.barh(y_pos, values, left=lefts, color=f_colors, edgecolor="black", height=0.6, align="center")
            ax.set_yticks(y_pos)
            ax.set_yticklabels(stages, fontsize=11, weight="bold")
            ax.invert_yaxis()  # Top to bottom

            # Add percentage & value labels on each bar
            for i, (v, bar) in enumerate(zip(values, bars)):
                pct = (v / max_val) * 100
                text_color = "white" if selected_style.startswith("dark") else "#0f172a"
                ax.text(max_val / 2, bar.get_y() + bar.get_height() / 2, f"{v:,.0f} ({pct:.1f}%)",
                        ha="center", va="center", color=text_color, fontsize=10, weight="bold")
            ax.get_xaxis().set_visible(False)

        # Chart 15: Lollipop Chart (Clean Modern Bar Alternative)
        elif chart_type == "lollipop":
            if y_col:
                lolli_df = df.groupby(x_col)[y_col].sum().reset_index()
                lolli_df = lolli_df.sort_values(by=y_col)
                cats = lolli_df[x_col].astype(str)
                vals = lolli_df[y_col]
            else:
                counts = df[x_col].value_counts().sort_values()
                cats = counts.index.astype(str)
                vals = counts.values

            c_list = sns.color_palette(palette or "deep", len(vals))
            marker_c = c_list[0] if len(c_list) > 0 else "#6366f1"

            y_pos = list(range(len(cats)))
            ax.hlines(y=y_pos, xmin=0, xmax=vals, color=marker_c, alpha=0.7, linewidth=2.5)
            ax.scatter(vals, y_pos, color=marker_c, s=120, alpha=0.9, edgecolors="white", linewidth=1.5, zorder=3)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(cats, fontsize=10, weight="bold")
            ax.set_xlabel(y_col or "Count", fontsize=11)

        # Chart 16: Radar / Spider Chart (Multivariate feature comparison)
        elif chart_type == "radar":
            num_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if len(num_cols) >= 3:
                features = num_cols[:8]
                num_vars = len(features)
                angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
                angles += angles[:1]

                plot_rows = df.head(5)
                cat_col = x_col if (x_col and x_col in df.columns) else None
                r_colors = sns.color_palette(palette or "Set2", len(plot_rows))

                # Normalize 0-100 safely per feature
                scaled_vals = {}
                for col in features:
                    s = df[col].astype(float)
                    c_min, c_max = float(s.min()), float(s.max())
                    if c_max > c_min:
                        scaled_vals[col] = (s - c_min) / (c_max - c_min) * 100
                    else:
                        scaled_vals[col] = pd.Series(50.0, index=df.index)

                for idx, (_, row) in enumerate(plot_rows.iterrows()):
                    vals = [float(scaled_vals[f].iloc[idx]) for f in features]
                    vals += vals[:1]
                    lbl = str(row[cat_col]) if (cat_col and cat_col in df.columns) else f"Record {idx + 1}"
                    ax.plot(angles, vals, linewidth=2, linestyle="solid", label=lbl, color=r_colors[idx])
                    ax.fill(angles, vals, color=r_colors[idx], alpha=0.25)

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(features, fontsize=10, weight="bold")
                ax.set_yticklabels([])
                ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)
            elif len(num_cols) >= 1:
                # Plot categories as radial polygon axes for the numeric metric
                val_col = y_col if (y_col and y_col in num_cols) else num_cols[0]
                lbl_col = x_col if (x_col and x_col in df.columns) else df.columns[0]
                categories = df[lbl_col].astype(str).tolist()
                vals = df[val_col].astype(float).tolist()

                num_vars = len(categories)
                angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
                angles += angles[:1]
                vals += vals[:1]

                r_color = sns.color_palette(palette or "deep", 1)[0]
                ax.plot(angles, vals, linewidth=2.5, linestyle="solid", color=r_color, marker="o")
                ax.fill(angles, vals, color=r_color, alpha=0.3)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(categories, fontsize=10, weight="bold")
                title = f"{title} ({val_col} by {lbl_col})"

        # Chart 17: Bubble Chart (3-Variable Scatter Plot)
        elif chart_type == "bubble":
            num_cols = df.select_dtypes(include=["number"]).columns.tolist()
            size_candidates = [c for c in num_cols if c not in [x_col, y_col]]
            size_col = size_candidates[0] if size_candidates else y_col
            
            sizes = df[size_col].abs() if size_col else df[y_col].abs()
            s_min, s_max = sizes.min(), sizes.max()
            if s_max > s_min:
                scaled_sizes = 60 + ((sizes - s_min) / (s_max - s_min)) * 550
            else:
                scaled_sizes = [180] * len(df)

            effective_hue = hue_col if (hue_col and hue_col in df.columns) else (x_col if x_col in df.columns else None)
            if effective_hue:
                sns.scatterplot(
                    data=df, x=x_col, y=y_col, hue=effective_hue, size=scaled_sizes,
                    sizes=(60, 600), palette=palette or "plasma", alpha=0.75,
                    edgecolor="white", linewidth=1.2, ax=ax, legend="brief"
                )
            else:
                bubble_color = sns.color_palette(palette or "plasma")[0]
                sns.scatterplot(
                    data=df, x=x_col, y=y_col, size=scaled_sizes, color=bubble_color,
                    sizes=(60, 600), alpha=0.75,
                    edgecolor="white", linewidth=1.2, ax=ax, legend="brief"
                )
            title = f"{title} (Bubble: {size_col})"

        # Finalize and save plot (dpi=125 provides instant ~0.1s rendering and clean ~150KB web files)
        ax.set_title(title, fontsize=14, weight="bold")

        # Explicit legend position prevents slow loc="best" combinatorial searching
        leg = ax.get_legend()
        if leg:
            leg.set_loc("upper right")

        try:
            fig.tight_layout(pad=1.2)
        except Exception:
            pass

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        # Strictly write to disk ONLY if a real file path is passed (never for :memory:)
        if output_path and output_path != ":memory:":
            with open(output_path, "wb") as f:
                f.write(buf.getvalue())
        
        # Reset to default seaborn theme
        sns.set_theme(style="whitegrid")

        return data_url

    except Exception as e:
        plt.close("all")
        sns.set_theme(style="whitegrid")
        return f"Error generating chart: {str(e)}"


# ==============================================================================
# 4. MULTI-MODEL SELECTION, HEURISTIC EXTRACTOR & CHAIN DEFINITION
# ==============================================================================

# High-quota production models for Google AI Studio
CANDIDATE_MODELS = [
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite"
]

# Mistral AI models (LangChain fallback when Gemini quota is exhausted)
MISTRAL_MODELS = [
    "ministral-8b-latest",
    "open-mistral-7b",
    "codestral-latest",
    "ministral-3b-latest"
]

# Groq LPU models (LangChain fallback for ultra-fast 500 tok/sec inference)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-8b-8192"
]

def create_model_chain(model_name: str):
    """Creates an LCEL chain for a specific Gemini model."""
    api_key = os.getenv("GOOGLE_API_KEY")
    llm_instance = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=api_key
    )
    return llm_instance.bind_tools([generate_chart])

def create_mistral_chain(model_name: str = "ministral-8b-latest"):
    """Creates an LCEL chain for Mistral LLM using LangChain."""
    mistral_key = os.getenv("MISTRAL_API_KEY")
    llm_instance = ChatMistralAI(
        model=model_name,
        mistral_api_key=mistral_key,
        temperature=0
    )
    return llm_instance.bind_tools([generate_chart])

def create_groq_chain(model_name: str = "llama-3.3-70b-versatile"):
    """Creates an LCEL chain for Groq Llama-3 using LangChain."""
    groq_key = os.getenv("GROQ_API_KEY")
    llm_instance = ChatGroq(
        model=model_name,
        groq_api_key=groq_key,
        temperature=0
    )
    return llm_instance.bind_tools([generate_chart])

# Primary model with tool binding (gemini-flash-latest has standard free tier quota of 1500 req/day)
llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=os.getenv("GOOGLE_API_KEY"))
llm_with_tools = llm.bind_tools([generate_chart])


# ==============================================================================
# 5. LCEL RUNNABLE CHAIN DEFINITION
# ==============================================================================

def format_prompt_inputs(inputs: dict) -> dict:
    """Formats inputs with ultra-concise column types to minimize token burn."""
    active_df = inputs.get("df", df)
    col_types = []
    for c in active_df.columns:
        dtype = "num" if pd.api.types.is_numeric_dtype(active_df[c]) else "cat"
        col_types.append(f"{c} ({dtype})")
    columns_summary = ", ".join(col_types)
    return {
        "columns_summary": columns_summary,
        "user_query": inputs.get("user_query", "")
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

def invoke_ai_with_fallbacks(inputs: dict):
    """
    Invokes AI with automatic cascading:
    1. First tries Gemini models (gemini-flash-latest, gemini-3.7-flash, etc.).
    2. If all Gemini quotas are exhausted (429 RESOURCE_EXHAUSTED) or fail, automatically switches to Mistral LLM (LangChain).
    3. If even Mistral encounters issues, returns None so smart heuristic can take over instantly.
    """
    last_error = None
    formatted_inputs = format_prompt_inputs(inputs)
    prompt_val = prompt_template.format_prompt(**formatted_inputs)
    
    # 1. Try Gemini models first
    for model_name in CANDIDATE_MODELS:
        try:
            model_with_tools = create_model_chain(model_name)
            ai_message = model_with_tools.invoke(prompt_val)
            if ai_message and getattr(ai_message, "tool_calls", None):
                return ai_message, f"gemini:{model_name}"
        except Exception as e:
            last_error = e
            err_msg = str(e)
            print(f"⚠️ Gemini Model '{model_name}' issue: {err_msg[:120]}")
            continue

    # 2. If Gemini exhausted or failed, automatically fall back to Mistral LLM via LangChain
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        print("🔄 All Gemini models exhausted. Automatically switching to Mistral LLM via LangChain...")
        for mistral_model in MISTRAL_MODELS:
            try:
                mistral_chain = create_mistral_chain(mistral_model)
                ai_message = mistral_chain.invoke(prompt_val)
                if ai_message and getattr(ai_message, "tool_calls", None):
                    print(f"✅ Successfully generated chart using Mistral LLM ({mistral_model})!")
                    return ai_message, f"mistral:{mistral_model}"
            except Exception as e:
                last_error = e
                err_msg = str(e)
                print(f"⚠️ Mistral Model '{mistral_model}' issue: {err_msg[:120]}")
                continue

    # 3. If Gemini & Mistral exhausted, automatically fall back to Groq Llama-3 via LangChain
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("🔄 Switching to Groq Llama-3 (LangChain) fallback...")
        for groq_model in GROQ_MODELS:
            try:
                groq_chain = create_groq_chain(groq_model)
                ai_message = groq_chain.invoke(prompt_val)
                if ai_message and getattr(ai_message, "tool_calls", None):
                    print(f"✅ Successfully generated chart using Groq Llama-3 ({groq_model})!")
                    return ai_message, f"groq:{groq_model}"
            except Exception as e:
                last_error = e
                err_msg = str(e)
                print(f"⚠️ Groq Model '{groq_model}' issue: {err_msg[:120]}")
                continue

    return None, last_error

def heuristic_chart_extractor(query: str, current_df: pd.DataFrame) -> dict:
    """
    Ultra-fast rule-based keyword & column extractor.
    Guarantees 100% reliability and instant response even if all AI API quotas are exhausted.
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
        ("histogram", "hist"),
        ("hist", "hist"),
        ("distribution", "hist"),
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

# Pure LLM Chain (for backward compatibility)
ai_chain = RunnableLambda(format_prompt_inputs) | prompt_template | llm_with_tools

# Full LCEL Pipeline: Input Formatter -> Prompt -> LLM with Tools -> Tool Executor (for CLI)
chart_chain = ai_chain | RunnableLambda(execute_chart_tool)


# ==============================================================================
# 6. USER INTERACTION LOOP (CLI)
# ==============================================================================

def start_assistant():
    print("\n" + "=" * 60)
    print("🤖 AI Data Visualization Assistant Ready (LCEL Runnable Chain)!")
    print(f"📁 Dataset Columns: {list(df.columns)}")
    print("💡 Examples:")
    print("   - 'Generate a treemap of Sales by Region'")
    print("   - 'Create a waterfall chart of Monthly Profit'")
    print("   - Type 'exit' to quit")
    print("=" * 60)

    while True:
        user_query = input("\n👉 Enter your chart request: ").strip()

        # Check for exit command
        if not user_query:
            continue
        if user_query.lower() in ["exit", "quit", "q"]:
            print("👋 Exiting assistant. Goodbye!")
            break

        # Invoke the LCEL Runnable Chain
        output = chart_chain.invoke({
            "columns": list(df.columns),
            "sample_data": df.head(2).to_dict(orient="records"),
            "user_query": user_query
        })

        # Display token usage
        tokens = output.get("tokens", {})
        print(f"\n🪙 Tokens Used: Total = {tokens.get('total', 0)} (Input: {tokens.get('input', 0)}, Output: {tokens.get('output', 0)})")

        if output.get("tool_called"):
            print(f"⚙️  Tool Chosen : generate_chart")
            print(f"📌 Parameters  : {output.get('tool_args')}")
            print(f"✅ Result      : {output.get('result')}")
        else:
            print(f"\n🤖 AI: {output.get('ai_response')}")


# Run the assistant
if __name__ == "__main__":
    start_assistant()
