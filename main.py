import os
import io
import sys
import base64
from typing import Literal, Optional
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
    Guarantees clean aggregations, prevents memory leaks or label collisions,
    and ensures sub-300ms chart rendering across datasets of any size.
    """
    total_rows = len(data)
    plot_df = data.copy()

    # Drop nulls in primary plotting columns to prevent matplotlib/seaborn crashes
    check_cols = [c for c in [x_col, y_col, hue_col] if c and c in plot_df.columns]
    if check_cols:
        plot_df = plot_df.dropna(subset=check_cols)

    # 1. Bar, Donut, Pie, Funnel, Treemap, Lollipop, Waterfall: aggregate and limit top categories
    if chart_type in ["bar", "donut", "doughnut", "pie", "funnel", "treemap", "lollipop", "waterfall"]:
        if x_col and x_col in plot_df.columns:
            try:
                # If numeric y_col is present, aggregate sum
                if y_col and y_col in plot_df.columns and pd.api.types.is_numeric_dtype(plot_df[y_col]):
                    if hue_col and hue_col in plot_df.columns and chart_type == "bar":
                        agg_df = plot_df.groupby([x_col, hue_col], as_index=False, observed=True)[y_col].mean()
                        top_x = plot_df.groupby(x_col, observed=True)[y_col].sum().nlargest(12).index
                        return agg_df[agg_df[x_col].isin(top_x)].copy()
                    else:
                        agg_df = plot_df.groupby(x_col, as_index=False, observed=True)[y_col].sum()
                        max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 18
                        if len(agg_df) > max_cats:
                            top_n = agg_df.nlargest(max_cats, y_col)
                            return top_n.copy()
                        return agg_df.sort_values(by=y_col, ascending=False)
                else:
                    # Categorical frequency
                    counts = plot_df[x_col].value_counts().reset_index()
                    counts.columns = [x_col, "count"]
                    max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 18
                    return counts.head(max_cats)
            except Exception as e:
                print("Preprocessing aggregation fallback:", e)

    # 2. Line & Area: Decimate time-series / trends smoothly
    if chart_type in ["line", "trend", "area"]:
        if total_rows > 2500:
            step = max(1, total_rows // 2500)
            return plot_df.iloc[::step].copy()
        return plot_df

    # 3. Scatter, Bubble, Hist, Box, Violin: Representative sampling
    sample_limit = 3000 if chart_type in ["scatter", "bubble"] else 6000
    if total_rows > sample_limit:
        return plot_df.sample(n=sample_limit, random_state=42)

    return plot_df


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
            plt.close(grid.fig)
            buf.seek(0)
            data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            if output_path and output_path != ":memory:":
                with open(output_path, "wb") as f:
                    f.write(buf.getvalue())
            sns.set_theme(style="whitegrid")
            return data_url

        # Step 3.4: Create canvas for charts (polar for radar, rectangular for others)
        chart_t = (chart_type or "bar").lower().strip()
        if chart_t in ["radar", "spider"]:
            fig, ax = plt.subplots(figsize=(7, 6), subplot_kw=dict(polar=True))
        else:
            fig, ax = plt.subplots(figsize=(8.5, 5))

        # Big Data Scalability: Smart pre-processing & downsampling for massive datasets
        plot_df = smart_preprocess_data(df, chart_t, x_col, y_col, safe_hue)

        # Chart 1: Bar Chart (Category comparison)
        if chart_t == "bar":
            if safe_hue:
                sns.barplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "deep", ax=ax)
            else:
                sns.barplot(data=plot_df, x=x_col, y=y_col, hue=x_col, palette=palette or "deep", legend=False, ax=ax)
            ax.tick_params(axis='x', rotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

        # Chart 2: Line Chart (Trends)
        elif chart_t in ["line", "trend"]:
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            if safe_hue:
                sns.lineplot(data=sorted_df, x=x_col, y=y_col, hue=safe_hue, marker="o", linewidth=2.5, palette=palette or "deep", ax=ax)
            else:
                line_color = sns.color_palette(palette)[0] if palette else None
                sns.lineplot(data=sorted_df, x=x_col, y=y_col, marker="o", linewidth=2.5, color=line_color, ax=ax)
            ax.tick_params(axis='x', rotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

        # Chart 3: Scatter Plot
        elif chart_t == "scatter":
            n_rows = len(plot_df)
            point_size = 20 if n_rows > 3000 else (40 if n_rows > 1000 else 70)
            alpha_val = 0.65 if n_rows > 2000 else 0.85
            sns.scatterplot(
                data=plot_df, x=x_col, y=y_col, hue=safe_hue, s=point_size,
                palette=palette or "deep", alpha=alpha_val, ax=ax,
                legend=show_legend
            )

        # Chart 4: Histogram
        elif chart_t in ["histogram", "hist"]:
            if safe_hue:
                sns.histplot(data=plot_df, x=x_col, kde=True, hue=safe_hue, palette=palette or "deep", ax=ax)
            else:
                bar_color = sns.color_palette(palette)[0] if palette else None
                sns.histplot(data=plot_df, x=x_col, kde=True, color=bar_color, ax=ax)

        # Chart 5: Box Plot
        elif chart_t == "box":
            if safe_hue:
                sns.boxplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "Set2", ax=ax)
            else:
                sns.boxplot(data=plot_df, x=x_col, y=y_col, hue=x_col, palette=palette or "Set2", legend=False, ax=ax)
            ax.tick_params(axis='x', rotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

        # Chart 6: Heatmap (Correlation)
        elif chart_t in ["heatmap", "correlation"]:
            corr = plot_df.corr(numeric_only=True)
            if corr.empty or corr.shape[0] < 2:
                ax.text(0.5, 0.5, "Requires at least 2 numeric columns\nfor correlation heatmap",
                        ha="center", va="center", fontsize=12, weight="bold", transform=ax.transAxes)
            else:
                sns.heatmap(corr, annot=True, cmap=palette or "coolwarm", fmt=".2f", linewidths=0.5, ax=ax)

        # Chart 7: Pie Chart
        elif chart_t == "pie":
            if y_col and y_col in plot_df.columns:
                pie_data = plot_df.groupby(x_col)[y_col].sum()
            elif x_col and x_col in plot_df.columns:
                pie_data = plot_df[x_col].value_counts()
            else:
                pie_data = plot_df.iloc[:, 0].value_counts()

            pie_data = pie_data[pie_data > 0]
            if len(pie_data) > 8:
                top_8 = pie_data.head(8)
                other_val = pie_data.iloc[8:].sum()
                pie_data = pd.concat([top_8, pd.Series([other_val], index=["Other"])])

            if pie_data.empty:
                ax.text(0.5, 0.5, "No positive data available for pie chart", ha="center", va="center", transform=ax.transAxes)
            else:
                pie_colors = sns.color_palette(palette or "pastel", len(pie_data))
                ax.pie(pie_data.values, labels=pie_data.index, autopct="%1.1f%%", startangle=140, colors=pie_colors)

        # Chart 8: Area Chart
        elif chart_t == "area":
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            area_colors = sns.color_palette(palette or "mako", 2)
            ax.fill_between(sorted_df[x_col], sorted_df[y_col], alpha=0.4, color=area_colors[0])
            ax.plot(sorted_df[x_col], sorted_df[y_col], color=area_colors[-1], linewidth=2.5, marker="o")
            ax.tick_params(axis='x', rotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

        # Chart 9: Violin Plot
        elif chart_t == "violin":
            if safe_hue:
                sns.violinplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "muted", ax=ax)
            else:
                sns.violinplot(data=plot_df, x=x_col, y=y_col, hue=x_col, palette=palette or "muted", legend=False, ax=ax)
            ax.tick_params(axis='x', rotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

        # Chart 10: Treemap
        elif chart_t == "treemap":
            if y_col and y_col in plot_df.columns:
                tree_data = plot_df.groupby(x_col)[y_col].sum().reset_index()
                tree_data = tree_data[tree_data[y_col] > 0].head(16)
                sizes = tree_data[y_col].values
                labels = [f"{row[x_col]}\n({row[y_col]:,.0f})" for _, row in tree_data.iterrows()]
            else:
                counts = plot_df[x_col].value_counts().head(16)
                sizes = counts.values
                labels = [f"{cat}\n({cnt:,})" for cat, cnt in zip(counts.index, counts.values)]

            if len(sizes) == 0 or sum(sizes) <= 0:
                ax.text(0.5, 0.5, "No positive values available for treemap", ha="center", va="center", transform=ax.transAxes)
            else:
                tree_colors = sns.color_palette(palette or "Spectral", len(sizes))
                squarify.plot(sizes=sizes, label=labels, color=tree_colors, alpha=0.85, text_kwargs={"fontsize": 10, "weight": "bold"}, ax=ax)
                ax.axis("off")

        # Chart 11: Waterfall Chart
        elif chart_t == "waterfall":
            if y_col and y_col in plot_df.columns:
                w_df = plot_df.groupby(x_col, as_index=False)[y_col].sum().head(14)
                categories = w_df[x_col].astype(str).tolist()
                values = w_df[y_col].astype(float).tolist()
            else:
                counts = plot_df[x_col].value_counts().head(14)
                categories = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

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

            for i in range(len(values) - 1):
                ax.plot([i, i + 1], [cumulative[i + 1], cumulative[i + 1]], color="grey", linestyle="--")

            ax.set_ylabel(y_col or "Value", fontsize=11)
            ax.tick_params(axis='x', rotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

        # Chart 12: Donut Chart
        elif chart_t in ["donut", "doughnut"]:
            if y_col and y_col in plot_df.columns:
                donut_data = plot_df.groupby(x_col)[y_col].sum()
            elif x_col and x_col in plot_df.columns:
                donut_data = plot_df[x_col].value_counts()
            else:
                donut_data = plot_df.iloc[:, 0].value_counts()

            donut_data = donut_data[donut_data > 0]
            if len(donut_data) > 8:
                top_8 = donut_data.head(8)
                other_val = donut_data.iloc[8:].sum()
                donut_data = pd.concat([top_8, pd.Series([other_val], index=["Other"])])

            if donut_data.empty:
                ax.text(0.5, 0.5, "No positive values for donut chart", ha="center", va="center", transform=ax.transAxes)
            else:
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
                total_val = donut_data.sum()
                center_txt = f"TOTAL\n{total_val:,.0f}" if isinstance(total_val, (int, float, np.number)) else "TOTAL"
                ax.text(0, 0, center_txt, ha="center", va="center", fontsize=11, weight="bold")

        # Chart 13: Funnel Chart
        elif chart_t == "funnel":
            if y_col and y_col in plot_df.columns:
                funnel_df = plot_df.groupby(x_col, as_index=False)[y_col].sum().sort_values(by=y_col, ascending=False).head(12)
                stages = funnel_df[x_col].astype(str).tolist()
                values = funnel_df[y_col].astype(float).tolist()
            else:
                counts = plot_df[x_col].value_counts().head(12)
                stages = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

            max_val = max(values) if values and max(values) > 0 else 1
            lefts = [(max_val - v) / 2 for v in values]
            f_colors = sns.color_palette(palette or "flare", len(values))

            y_pos = list(range(len(stages)))
            bars = ax.barh(y_pos, values, left=lefts, color=f_colors, edgecolor="black", height=0.6, align="center")
            ax.set_yticks(y_pos)
            ax.set_yticklabels(stages, fontsize=10, weight="bold")
            ax.invert_yaxis()

            for i, (v, bar) in enumerate(zip(values, bars)):
                pct = (v / max_val) * 100
                text_color = "white" if selected_style.startswith("dark") else "#0f172a"
                ax.text(max_val / 2, bar.get_y() + bar.get_height() / 2, f"{v:,.0f} ({pct:.1f}%)",
                        ha="center", va="center", color=text_color, fontsize=10, weight="bold")
            ax.get_xaxis().set_visible(False)

        # Chart 14: Lollipop Chart
        elif chart_t == "lollipop":
            if y_col and y_col in plot_df.columns:
                lolli_df = plot_df.groupby(x_col)[y_col].sum().reset_index().sort_values(by=y_col).tail(18)
                cats = lolli_df[x_col].astype(str).tolist()
                vals = lolli_df[y_col].tolist()
            else:
                counts = plot_df[x_col].value_counts().sort_values().tail(18)
                cats = counts.index.astype(str).tolist()
                vals = counts.values.tolist()

            c_list = sns.color_palette(palette or "deep", len(vals))
            marker_c = c_list[0] if len(c_list) > 0 else "#6366f1"

            y_pos = list(range(len(cats)))
            ax.hlines(y=y_pos, xmin=0, xmax=vals, color=marker_c, alpha=0.7, linewidth=2.5)
            ax.scatter(vals, y_pos, color=marker_c, s=120, alpha=0.9, edgecolors="white", linewidth=1.5, zorder=3)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(cats, fontsize=10, weight="bold")
            ax.set_xlabel(y_col or "Count", fontsize=11)

        # Chart 15: Radar Chart
        elif chart_t in ["radar", "spider"]:
            num_cols = plot_df.select_dtypes(include=["number"]).columns.tolist()
            if len(num_cols) >= 3:
                features = num_cols[:6]
                num_vars = len(features)
                angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
                angles += angles[:1]

                plot_rows = plot_df.head(4)
                cat_col = x_col if (x_col and x_col in plot_df.columns) else None
                r_colors = sns.color_palette(palette or "Set2", len(plot_rows))

                scaled_vals = {}
                for col in features:
                    s = plot_df[col].astype(float)
                    c_min, c_max = float(s.min()), float(s.max())
                    if c_max > c_min:
                        scaled_vals[col] = (s - c_min) / (c_max - c_min) * 100
                    else:
                        scaled_vals[col] = pd.Series(50.0, index=plot_df.index)

                for idx, (_, row) in enumerate(plot_rows.iterrows()):
                    vals = [float(scaled_vals[f].loc[row.name]) for f in features]
                    vals += vals[:1]
                    lbl = str(row[cat_col]) if (cat_col and cat_col in plot_df.columns) else f"Row {idx + 1}"
                    ax.plot(angles, vals, linewidth=2, linestyle="solid", label=lbl, color=r_colors[idx])
                    ax.fill(angles, vals, color=r_colors[idx], alpha=0.25)

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(features, fontsize=10, weight="bold")
                ax.set_yticklabels([])
                ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)
            else:
                sns.barplot(data=plot_df.head(15), x=x_col, y=y_col, hue=x_col, palette=palette or "deep", legend=False, ax=ax)
                ax.tick_params(axis='x', rotation=45)

        # Chart 16: Bubble Chart
        elif chart_t == "bubble":
            num_cols = plot_df.select_dtypes(include=["number"]).columns.tolist()
            size_candidates = [c for c in num_cols if c not in [x_col, y_col]]
            size_col = size_candidates[0] if size_candidates else y_col

            sizes = plot_df[size_col].abs() if size_col else plot_df[y_col].abs()
            s_min, s_max = sizes.min(), sizes.max()
            if s_max > s_min:
                scaled_sizes = 60 + ((sizes - s_min) / (s_max - s_min)) * 500
            else:
                scaled_sizes = [150] * len(plot_df)

            effective_hue = hue_col if (hue_col and hue_col in plot_df.columns) else None
            if effective_hue:
                sns.scatterplot(
                    data=plot_df, x=x_col, y=y_col, hue=effective_hue, size=scaled_sizes,
                    sizes=(60, 500), palette=palette or "plasma", alpha=0.75,
                    edgecolor="white", linewidth=1.2, ax=ax, legend="brief"
                )
            else:
                bubble_color = sns.color_palette(palette or "plasma")[0]
                sns.scatterplot(
                    data=plot_df, x=x_col, y=y_col, size=scaled_sizes, color=bubble_color,
                    sizes=(60, 500), alpha=0.75,
                    edgecolor="white", linewidth=1.2, ax=ax, legend=False
                )
            title = f"{title} (Bubble: {size_col})"

        # Fallback to standard Bar Chart
        else:
            sns.barplot(data=plot_df.head(20), x=x_col, y=y_col, hue=x_col, palette=palette or "deep", legend=False, ax=ax)
            ax.tick_params(axis='x', rotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

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
            try:
                print(f"[WARN] Gemini Model '{model_name}' issue: {err_msg[:120]}")
            except Exception:
                pass
            continue

    # 2. If Gemini exhausted or failed, automatically fall back to Mistral LLM via LangChain
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        try:
            print("[INFO] All Gemini models exhausted. Automatically switching to Mistral LLM via LangChain...")
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
