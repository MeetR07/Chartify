import os
import io
import sys
import json
import base64
from typing import Literal, Optional, Dict, Any, List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Use non-interactive, thread-safe Agg backend for servers
import matplotlib.pyplot as plt
import seaborn as sns

try:
    import squarify
    HAS_SQUARIFY = True
except ImportError:
    squarify = None
    HAS_SQUARIFY = False

from langchain_core.tools import tool

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

# Default dataset fallback
DEFAULT_DF = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
    "Sales": [15000, 22000, 18000, 27000, 31000],
    "Profit": [3000, 4500, -1200, 6000, 7500],
    "Region": ["North", "South", "North", "West", "South"]
})



# ==============================================================================
# SASSY & CLASSY DESIGN SYSTEM (Linear, Stripe, Apple Health Inspired)
# ==============================================================================

MODERN_PALETTES: Dict[str, List[str]] = {
    "butter_green": ["#013E37", "#FFEFB3", "#08ab9c", "#f47a34", "#fc6eae", "#ffbd29", "#146665"],
    "aura_bloom":   ["#08ab9c", "#fc6eae", "#f47a34", "#146665", "#ffbd29", "#feb3a8", "#fff2b7"],
    "custom":       ["#013E37", "#FFEFB3", "#08ab9c", "#f47a34", "#fc6eae", "#ffbd29", "#146665"],
    "vibrant":   ["#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#3B82F6", "#F43F5E", "#14B8A6", "#E11D48"],
    "cyberpunk": ["#00F2FE", "#4FACFE", "#FF007F", "#7928CA", "#FF4B4B", "#00DFD8", "#FEE140", "#A855F7"],
    "emerald":   ["#10B981", "#059669", "#047857", "#34D399", "#6EE7B7", "#065F46", "#14B8A6", "#0D9488"],
    "sunset":    ["#F43F5E", "#FB923C", "#FBBF24", "#F472B6", "#C084FC", "#E11D48", "#EA580C", "#D97706"],
    "ocean":     ["#0EA5E9", "#38BDF8", "#0284C7", "#6366F1", "#7DD3FC", "#0369A1", "#2563EB", "#1D4ED8"],
    "purple":    ["#8B5CF6", "#7C3AED", "#6D28D9", "#A78BFA", "#C4B5FD", "#5B21B6", "#4C1D95", "#9333EA"],
    "luxe":      ["#38BDF8", "#818CF8", "#C084FC", "#F472B6", "#FB7185", "#34D399", "#FBBF24", "#A78BFA"],
    "monochrome":["#334155", "#475569", "#64748B", "#94A3B8", "#CBD5E1", "#1E293B", "#0F172A", "#E2E8F0"]
}

DEFAULT_PALETTE = MODERN_PALETTES["butter_green"]

LAST_CHART_DATA: Dict[str, Any] = {}

def get_last_chart_data() -> Dict[str, Any]:
    """Returns the exact plotted dataset and metadata from the most recent 2D chart generation."""
    global LAST_CHART_DATA
    return dict(LAST_CHART_DATA)


def resolve_palette_colors(palette_name: Optional[str], n_colors: int = 8) -> List[str]:
    """Resolves curated HEX color palettes with graceful fallbacks."""
    if palette_name and palette_name.lower() in MODERN_PALETTES:
        colors = MODERN_PALETTES[palette_name.lower()]
    elif palette_name:
        try:
            colors = [matplotlib.colors.to_hex(c) for c in sns.color_palette(palette_name, n_colors)]
        except Exception:
            colors = DEFAULT_PALETTE
    else:
        colors = DEFAULT_PALETTE
    
    if len(colors) < n_colors:
        repeats = (n_colors // len(colors)) + 1
        colors = (colors * repeats)[:n_colors]
    return colors[:n_colors]


def get_active_df() -> pd.DataFrame:
    """Dynamically resolves the active dataset from main.py if loaded, else fallback to DEFAULT_DF."""
    try:
        import main
        if hasattr(main, "df") and isinstance(main.df, pd.DataFrame) and not main.df.empty:
            return main.df
    except Exception:
        pass
    return DEFAULT_DF



def format_num_human(val: Any) -> str:
    """Formats numeric values into compact, human-friendly badges ($15.2K, 1.4M, 25%)."""
    if not isinstance(val, (int, float, np.number)) or pd.isna(val):
        return str(val) if not pd.isna(val) else ""
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}K"
    elif isinstance(val, float):
        if val.is_integer():
            return f"{sign}{int(abs_val)}"
        return f"{sign}{abs_val:.1f}"
    return str(int(val))

import re

# ==============================================================================
# QUERY INTENT ENGINE (Separating Query Operation from Chart Type)
# ==============================================================================

def detect_query_intent(query_str: Optional[str] = None, title: Optional[str] = None) -> tuple[str, int]:
    """
    Separates QUERY OPERATION from CHART TYPE.
    Returns:
        (operation, limit)
        where operation is one of:
        - 'ranking_desc' (highest, top, largest, maximum, greatest, biggest, rank descending)
        - 'ranking_asc'  (lowest, bottom, smallest, minimum, rank ascending)
        - 'count'        (frequency, distribution, how many, count of each value)
        - 'mean'         (average, mean, avg)
        - 'max'          (what is the maximum, max)
        - 'min'          (what is the minimum, min)
        - 'default'
    """
    text = f"{query_str or ''} {title or ''}".lower().strip()
    if not text:
        return "default", 10

    # Extract limit if specified (e.g. 'top 10', '10 highest', 'top 5', 'limit 10')
    limit = 10
    limit_match = re.search(r'\b(?:top|bottom|highest|lowest|first|last|limit)\s+(\d+)\b', text)
    if not limit_match:
        limit_match = re.search(r'\b(\d+)\s+(?:top|bottom|highest|lowest|items|rows|values|properties|records)\b', text)
    if limit_match:
        try:
            limit = max(1, min(100, int(limit_match.group(1))))
        except Exception:
            limit = 10

    # 1. Explicit COUNT / FREQUENCY queries (strictly for frequency / distribution / how many / count of each)
    count_triggers = [
        "frequency", "distribution", "how many", "count of each",
        "count each", "counts of each", "value count", "value_count",
        "number of properties", "number of houses"
    ]
    if any(trigger in text for trigger in count_triggers):
        return "count", limit
    if re.search(r'\bcounts?\b', text) and not any(w in text for w in ["highest", "lowest", "top", "rank", "average", "mean"]):
        return "count", limit

    # 2. MEAN / AVERAGE
    mean_triggers = ["average", "mean", "avg"]
    if any(re.search(rf'\b{t}\b', text) for t in mean_triggers) and not any(w in text for w in ["highest", "lowest", "top"]):
        return "mean", limit

    # 3. Explicit MAX / MIN queries (single aggregation questions)
    if re.search(r'\b(?:what\s+is\s+the\s+maximum|what\s+is\s+the\s+max|find\s+the\s+maximum|max\s+value)\b', text):
        return "max", 1
    if re.search(r'\b(?:what\s+is\s+the\s+minimum|what\s+is\s+the\s+min|find\s+the\s+minimum|min\s+value)\b', text):
        return "min", 1

    # 4. RANKING DESCENDING
    desc_triggers = [
        "highest", "top", "largest", "maximum", "greatest", "biggest",
        "rank descending", "ranked descending", "descending"
    ]
    if any(re.search(rf'\b{t}\b', text) if " " not in t else t in text for t in desc_triggers):
        return "ranking_desc", limit

    # 5. RANKING ASCENDING
    asc_triggers = [
        "lowest", "bottom", "smallest", "minimum", "least",
        "rank ascending", "ranked ascending", "ascending"
    ]
    if any(re.search(rf'\b{t}\b', text) if " " not in t else t in text for t in asc_triggers):
        return "ranking_asc", limit

    return "default", limit


# ==============================================================================
# BIG DATA SCALABILITY ENGINE (O(N) Complexity)
# ==============================================================================

def smart_preprocess_data(
    data: pd.DataFrame, 
    chart_type: str, 
    x_col: Optional[str] = None, 
    y_col: Optional[str] = None, 
    hue_col: Optional[str] = None,
    query: Optional[str] = None,
    title: Optional[str] = None
) -> pd.DataFrame:
    """
    Big Data Scalability Preprocessor:
    Guarantees clean aggregations, prevents memory leaks or label collisions,
    and ensures sub-300ms chart rendering across datasets of any size.
    Separates Query Operation (ranking, frequency, average, max, min) from Chart Type.
    """
    total_rows = len(data)

    # Detect Query Intent
    op, limit = detect_query_intent(query, title)

    # Identify the primary numeric column if any
    num_col = None
    if y_col and y_col in data.columns and pd.api.types.is_numeric_dtype(data[y_col]):
        num_col = y_col
    elif x_col and x_col in data.columns and pd.api.types.is_numeric_dtype(data[x_col]):
        num_col = x_col
    else:
        combined_text = f"{query or ''} {title or ''}".lower()
        for col in data.columns:
            if pd.api.types.is_numeric_dtype(data[col]):
                if col.lower() in combined_text or any(token in combined_text for token in col.lower().split("_") if len(token) > 2):
                    num_col = col
                    break

    # --------------------------------------------------------------------------
    # INTENT PIPELINE: DATA OPERATION SEPARATE FROM CHART TYPE
    # --------------------------------------------------------------------------

    # 1. RANKING QUERIES (highest, top, largest, lowest, bottom, smallest, etc.)
    # DO NOT use value_counts(), groupby(), or count() for ranking queries.
    if op in ["ranking_desc", "ranking_asc"] and num_col:
        ascending = (op == "ranking_asc")
        ranked_df = data.dropna(subset=[num_col]).sort_values(by=num_col, ascending=ascending).head(limit).copy()
        
        # Check if an explicit categorical column is involved
        cat_candidates = [c for c in [x_col, y_col] if c and c in data.columns and c != num_col and not pd.api.types.is_numeric_dtype(data[c])]
        if not cat_candidates:
            ranked_df["Rank"] = [f"Rank {i+1}" for i in range(len(ranked_df))]
        return ranked_df

    # 2. MEAN / AVERAGE QUERIES
    if op == "mean" and num_col:
        cat_col = x_col if (x_col and x_col in data.columns and not pd.api.types.is_numeric_dtype(data[x_col])) else None
        if cat_col:
            agg_df = data.groupby(cat_col, as_index=False, observed=True)[num_col].mean()
            return agg_df.sort_values(by=num_col, ascending=False).head(limit).reset_index(drop=True)
        else:
            mean_val = float(data[num_col].mean())
            return pd.DataFrame({"Metric": [f"Average {num_col}"], num_col: [round(mean_val, 2)]})

    # 3. MAX / MIN SINGLE VALUE AGGREGATION QUERIES
    if op == "max" and num_col:
        max_val = float(data[num_col].max())
        return pd.DataFrame({"Metric": [f"Max {num_col}"], num_col: [max_val]})
    if op == "min" and num_col:
        min_val = float(data[num_col].min())
        return pd.DataFrame({"Metric": [f"Min {num_col}"], num_col: [min_val]})

    # 4. EXPLICIT COUNT / FREQUENCY QUERIES (frequency, distribution, how many, count of each)
    if op == "count":
        col_to_count = num_col if num_col else (x_col if x_col in data.columns else data.columns[0])
        counts = data[col_to_count].value_counts().reset_index()
        counts.columns = [col_to_count, "count"]
        return counts.head(limit).reset_index(drop=True)

    # --------------------------------------------------------------------------
    # STANDARD SCALABILITY & CHART TYPE PREPROCESSING
    # --------------------------------------------------------------------------

    # Auto-swap if x_col is numeric and y_col is categorical
    if x_col and y_col and x_col in data.columns and y_col in data.columns:
        if pd.api.types.is_numeric_dtype(data[x_col]) and not pd.api.types.is_numeric_dtype(data[y_col]):
            x_col, y_col = y_col, x_col

    # Memory & time optimization: only slice the required columns
    check_cols = [c for c in [x_col, y_col, hue_col] if c and c in data.columns]
    if check_cols:
        plot_df = data[check_cols].dropna().copy()
    else:
        plot_df = data.copy()

    # Bar, Donut, Pie, Funnel, Treemap, Lollipop, Waterfall: aggregate and limit top categories
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
                        max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 15
                        if len(agg_df) > max_cats:
                            top_n = agg_df.nlargest(max_cats, y_col)
                            return top_n.sort_values(by=y_col, ascending=False).reset_index(drop=True)
                        return agg_df.sort_values(by=y_col, ascending=False).reset_index(drop=True)
                else:
                    # When y_col is missing:
                    # If x_col is numeric, DO NOT use value_counts() unless explicitly requested!
                    if pd.api.types.is_numeric_dtype(plot_df[x_col]):
                        ranked_df = plot_df.sort_values(by=x_col, ascending=False).head(10).copy()
                        ranked_df["Rank"] = [f"Rank {i+1}" for i in range(len(ranked_df))]
                        return ranked_df
                    else:
                        # Categorical frequency
                        counts = plot_df[x_col].value_counts().reset_index()
                        counts.columns = [x_col, "count"]
                        max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 15
                        return counts.head(max_cats).reset_index(drop=True)
            except Exception as e:
                try:
                    print(f"[WARN] Preprocessing aggregation fallback: {e}")
                except Exception:
                    pass

    # Line & Area: Decimate time-series / trends smoothly
    if chart_type in ["line", "trend", "area"]:
        if total_rows > 2500:
            step = max(1, total_rows // 2500)
            return plot_df.iloc[::step].copy()
        return plot_df

    # Scatter, Bubble, Hist, Box, Violin: Representative sampling
    sample_limit = 1500 if chart_type in ["scatter", "bubble"] else 3000
    if total_rows > sample_limit:
        return plot_df.sample(n=sample_limit, random_state=42)

    return plot_df


# ==============================================================================
# STUDIO MATPLOTLIB / SEABORN ENGINE (Magazine-Grade Publication Quality)
# ==============================================================================

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
    output_path: Optional[str] = None,
    query: Optional[str] = None
) -> str:
    """Generates and saves an ultra-modern, publication-quality data visualization chart.
    Args:
        chart_type: The chart visualization type.
        x_col: Category or X-axis column name.
        y_col: Numeric measure or Y-axis column name.
        hue_col: Optional category column for grouping.
        title: Short descriptive title for the chart.
        palette: Color palette name (vibrant, cyberpunk, emerald, sunset, ocean, purple, luxe, monochrome).
        style: Theme style ('whitegrid', 'darkgrid', 'white', 'dark').
    """
    chart_t = (chart_type or "bar").lower().strip()
    df = get_active_df()
    try:
        if not output_path:
            output_path = f"{chart_t}.png"

        # Step 1: Detect & auto-swap inverted x/y column assignments
        if x_col and y_col and x_col in df.columns and y_col in df.columns:
            if pd.api.types.is_numeric_dtype(df[x_col]) and not pd.api.types.is_numeric_dtype(df[y_col]):
                x_col, y_col = y_col, x_col

        # Check column availability
        for col in [x_col, y_col, hue_col]:
            if col and col not in df.columns:
                return f"Error: Column '{col}' not found. Available columns: {list(df.columns)}"

        # Step 2: Set modern typographic & style parameters
        selected_style = (style or "whitegrid").lower().strip()
        plt.close("all")

        is_dark = "dark" in selected_style
        bg_color = "#0f172a" if is_dark else "#ffffff"
        card_bg = "#1e293b" if is_dark else "#f8fafc"
        text_color = "#f8fafc" if is_dark else "#0f172a"
        muted_color = "#94a3b8" if is_dark else "#64748b"
        grid_line_color = "#334155" if is_dark else "#e2e8f0"

        # Setup font family for modern aesthetic
        plt.rcParams["font.sans-serif"] = ["Inter", "Segoe UI", "SF Pro Display", "DejaVu Sans", "Arial", "sans-serif"]
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["figure.facecolor"] = bg_color
        plt.rcParams["axes.facecolor"] = bg_color
        plt.rcParams["savefig.facecolor"] = bg_color
        plt.rcParams["text.color"] = text_color
        plt.rcParams["axes.labelcolor"] = muted_color

        # Safeguard hue_col cardinality
        safe_hue = hue_col
        show_legend = "brief"
        if hue_col and hue_col in df.columns:
            if df[hue_col].nunique() > 10:
                show_legend = False

        # Step 3: Special Case: Pairplot
        if chart_t == "pairplot":
            palette_colors = resolve_palette_colors(palette, 6)
            grid = sns.pairplot(df, hue=safe_hue, palette=palette_colors)
            grid.fig.suptitle(title, y=1.02, fontsize=14, weight="bold", color=text_color)
            buf = io.BytesIO()
            grid.savefig(buf, format="png", dpi=120, facecolor=bg_color, bbox_inches="tight")
            plt.close(grid.fig)
            buf.seek(0)
            data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            if output_path and output_path != ":memory:":
                with open(output_path, "wb") as f:
                    f.write(buf.getvalue())
            return data_url

        # Step 4: Create canvas
        if chart_t in ["radar", "spider"]:
            fig, ax = plt.subplots(figsize=(7, 6.5), subplot_kw=dict(polar=True))
        elif chart_t in ["pie", "donut", "doughnut"]:
            fig, ax = plt.subplots(figsize=(7.5, 5.5))
        else:
            fig, ax = plt.subplots(figsize=(9.2, 5.2))

        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        # Big Data Scalability Preprocessing
        plot_df = smart_preprocess_data(df, chart_t, x_col, y_col, safe_hue, query=query, title=title)

        # Detect intent for rendering orientation and metrics
        query_op, _ = detect_query_intent(query, title)

        # Effective metric column resolution
        effective_y = y_col
        if not effective_y or effective_y not in plot_df.columns:
            if "count" in plot_df.columns:
                effective_y = "count"
            else:
                num_cols_in_plot = [c for c in plot_df.columns if pd.api.types.is_numeric_dtype(plot_df[c])]
                if num_cols_in_plot:
                    effective_y = num_cols_in_plot[0]

        # Effective category column resolution
        if not x_col or x_col == effective_y or x_col not in plot_df.columns:
            if "Rank" in plot_df.columns:
                x_col = "Rank"
            elif "Metric" in plot_df.columns:
                x_col = "Metric"
            else:
                non_num = [c for c in plot_df.columns if c != effective_y]
                if non_num:
                    x_col = non_num[0]

        is_horizontal_bar = False

        # --------------------------------------------------------------------------
        # Chart 1: Bar Chart (Ultra-Modern Horizontal SaaS Ranking & Grouped)
        # --------------------------------------------------------------------------
        if chart_t == "bar":
            if safe_hue:
                # Grouped vertical bar chart
                colors = resolve_palette_colors(palette, plot_df[safe_hue].nunique() if safe_hue in plot_df.columns else 6)
                sns.barplot(data=plot_df, x=x_col, y=effective_y, hue=safe_hue, palette=colors, ax=ax)
                if hasattr(ax, "containers"):
                    for container in ax.containers:
                        try:
                            ax.bar_label(
                                container,
                                fmt=lambda v: format_num_human(v) if abs(v) > 0 else "",
                                padding=3,
                                fontsize=8.5,
                                weight="bold",
                                color=text_color
                            )
                        except Exception:
                            pass
            else:
                # Studio Horizontal Bar Chart (Linear / Stripe / Apple Health design)
                is_horizontal_bar = True
                
                # Order categories: ascending=True puts highest value at top bar (y=N-1) in ax.barh
                # for ranking_asc (lowest), ascending=False puts lowest value at top bar
                if effective_y and effective_y in plot_df.columns:
                    if query_op == "ranking_asc":
                        plot_df = plot_df.sort_values(by=effective_y, ascending=False).reset_index(drop=True)
                    else:
                        plot_df = plot_df.sort_values(by=effective_y, ascending=True).reset_index(drop=True)
                
                categories = plot_df[x_col].astype(str).tolist() if x_col and x_col in plot_df.columns else []
                values = plot_df[effective_y].tolist() if effective_y and effective_y in plot_df.columns else []
                
                n_items = len(categories)
                bar_colors = resolve_palette_colors(palette, max(n_items, 4))
                if len(bar_colors) < n_items:
                    bar_colors = (bar_colors * (n_items // len(bar_colors) + 1))[:n_items]

                y_positions = np.arange(n_items)
                bar_height = 0.62

                bars = ax.barh(
                    y_positions,
                    values,
                    height=bar_height,
                    color=bar_colors[:n_items],
                    edgecolor="none"
                )

                ax.set_yticks(y_positions)
                ax.set_yticklabels(categories, fontsize=10, weight="bold", color=text_color)

                max_val = max(values) if values and max(values) > 0 else 1
                ax.set_xlim(0, max_val * 1.18)

                # Direct crisp value labels on each bar tip
                for bar, val in zip(bars, values):
                    w = bar.get_width()
                    y_pos = bar.get_y() + bar.get_height() / 2
                    ax.text(
                        w + (max_val * 0.02),
                        y_pos,
                        f"{format_num_human(val)}",
                        va="center",
                        ha="left",
                        fontsize=9.5,
                        weight="bold",
                        color=text_color
                    )

                ax.set_xlabel(effective_y.replace("_", " ").title() if effective_y else "Value", fontsize=10, color=muted_color, labelpad=8)
                ax.set_ylabel("")

        # --------------------------------------------------------------------------
        # Chart 2: Line Chart (Trends with smooth area glow & high-contrast points)
        # --------------------------------------------------------------------------
        elif chart_t in ["line", "trend"]:
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            colors = resolve_palette_colors(palette, 6)
            if safe_hue:
                sns.lineplot(data=sorted_df, x=x_col, y=effective_y, hue=safe_hue, marker="o", linewidth=2.8, palette=colors, ax=ax)
            else:
                line_color = colors[0]
                x_vals = sorted_df[x_col]
                y_vals = sorted_df[effective_y]
                
                # Area glow fill under line
                ax.fill_between(x_vals, y_vals, alpha=0.18, color=line_color)
                ax.plot(
                    x_vals, y_vals,
                    color=line_color,
                    linewidth=2.8,
                    marker="o",
                    markersize=6.5,
                    markeredgewidth=2,
                    markeredgecolor=bg_color
                )

        # --------------------------------------------------------------------------
        # Chart 3: Scatter Plot
        # --------------------------------------------------------------------------
        elif chart_t == "scatter":
            colors = resolve_palette_colors(palette, 6)
            n_rows = len(plot_df)
            point_size = 40 if n_rows > 1000 else 75
            alpha_val = 0.75 if n_rows > 1000 else 0.88
            sns.scatterplot(
                data=plot_df, x=x_col, y=effective_y, hue=safe_hue, s=point_size,
                palette=colors, alpha=alpha_val, ax=ax,
                edgecolor=bg_color, linewidth=0.8,
                legend=show_legend
            )

        # --------------------------------------------------------------------------
        # Chart 4: Histogram
        # --------------------------------------------------------------------------
        elif chart_t in ["histogram", "hist"]:
            colors = resolve_palette_colors(palette, 4)
            if safe_hue:
                sns.histplot(data=plot_df, x=x_col, kde=True, hue=safe_hue, palette=colors, ax=ax)
            else:
                sns.histplot(
                    data=plot_df, x=x_col, kde=True, color=colors[0],
                    edgecolor=bg_color, alpha=0.65, ax=ax,
                    line_kws={"linewidth": 2.5, "color": colors[1] if len(colors) > 1 else "#06b6d4"}
                )

        # --------------------------------------------------------------------------
        # Chart 5: Box Plot
        # --------------------------------------------------------------------------
        elif chart_t == "box":
            colors = resolve_palette_colors(palette, 8)
            if safe_hue:
                sns.boxplot(data=plot_df, x=x_col, y=effective_y, hue=safe_hue, palette=colors, ax=ax, width=0.48)
            else:
                sns.boxplot(data=plot_df, x=x_col, y=effective_y, hue=x_col, palette=colors, legend=False, ax=ax, width=0.48)

        # --------------------------------------------------------------------------
        # Chart 6: Heatmap (Correlation)
        # --------------------------------------------------------------------------
        elif chart_t in ["heatmap", "correlation"]:
            corr = plot_df.corr(numeric_only=True)
            if corr.empty or corr.shape[0] < 2:
                ax.text(0.5, 0.5, "Requires at least 2 numeric columns\nfor correlation heatmap",
                        ha="center", va="center", fontsize=12, weight="bold", color=text_color, transform=ax.transAxes)
            else:
                cmap_name = palette if palette in ["coolwarm", "viridis", "mako", "rocket", "plasma"] else "coolwarm"
                sns.heatmap(
                    corr, annot=True, cmap=cmap_name, fmt=".2f",
                    linewidths=1.5, linecolor=bg_color, square=True,
                    ax=ax, cbar_kws={"shrink": 0.8},
                    annot_kws={"fontsize": 9.5, "weight": "bold"}
                )

        # --------------------------------------------------------------------------
        # Chart 7: Pie & Donut Chart (Sleek Modern Ring with Grand Total Center)
        # --------------------------------------------------------------------------
        elif chart_t in ["pie", "donut", "doughnut"]:
            if effective_y and effective_y in plot_df.columns:
                pie_data = plot_df.groupby(x_col)[effective_y].sum()
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
                ax.text(0.5, 0.5, "No positive values for donut chart", ha="center", va="center", color=text_color, transform=ax.transAxes)
            else:
                donut_colors = resolve_palette_colors(palette, len(pie_data))
                total_val = pie_data.sum()
                
                # Modern donut ring
                wedges, texts, autotexts = ax.pie(
                    pie_data.values,
                    labels=pie_data.index,
                    autopct="%1.1f%%",
                    startangle=140,
                    colors=donut_colors,
                    pctdistance=0.76,
                    wedgeprops=dict(width=0.38, edgecolor=bg_color, linewidth=2.5),
                    textprops={"color": text_color, "fontsize": 9.5, "weight": "bold"}
                )
                
                # Center KPI Grand Total Badge
                center_txt = f"TOTAL\n{format_num_human(total_val)}" if isinstance(total_val, (int, float, np.number)) else "TOTAL"
                ax.text(0, 0, center_txt, ha="center", va="center", fontsize=11, weight="bold", color=text_color)

        # --------------------------------------------------------------------------
        # Chart 8: Area Chart
        # --------------------------------------------------------------------------
        elif chart_t == "area":
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            colors = resolve_palette_colors(palette, 4)
            area_color = colors[0]
            ax.fill_between(sorted_df[x_col], sorted_df[effective_y], alpha=0.30, color=area_color)
            ax.plot(sorted_df[x_col], sorted_df[effective_y], color=area_color, linewidth=2.8, marker="o", markersize=5.5)

        # --------------------------------------------------------------------------
        # Chart 9: Violin Plot
        # --------------------------------------------------------------------------
        elif chart_t == "violin":
            colors = resolve_palette_colors(palette, 8)
            if safe_hue:
                sns.violinplot(data=plot_df, x=x_col, y=effective_y, hue=safe_hue, palette=colors, ax=ax)
            else:
                sns.violinplot(data=plot_df, x=x_col, y=effective_y, hue=x_col, palette=colors, legend=False, ax=ax)

        # --------------------------------------------------------------------------
        # Chart 10: Treemap
        # --------------------------------------------------------------------------
        elif chart_t == "treemap":
            if not HAS_SQUARIFY:
                ax.text(0.5, 0.5, "Squarify library not installed.\nRun: pip install squarify", ha="center", va="center", color=text_color, transform=ax.transAxes)
            else:
                if effective_y and effective_y in plot_df.columns:
                    tree_data = plot_df.groupby(x_col)[effective_y].sum().reset_index()
                    tree_data = tree_data[tree_data[effective_y] > 0].head(14)
                    sizes = tree_data[effective_y].values
                    labels = [f"{row[x_col]}\n{format_num_human(row[effective_y])}" for _, row in tree_data.iterrows()]
                else:
                    counts = plot_df[x_col].value_counts().head(14)
                    sizes = counts.values
                    labels = [f"{cat}\n{format_num_human(cnt)}" for cat, cnt in zip(counts.index, counts.values)]

                if len(sizes) == 0 or sum(sizes) <= 0:
                    ax.text(0.5, 0.5, "No positive values available for treemap", ha="center", va="center", color=text_color, transform=ax.transAxes)
                else:
                    tree_colors = resolve_palette_colors(palette, len(sizes))
                    squarify.plot(sizes=sizes, label=labels, color=tree_colors, alpha=0.9, text_kwargs={"fontsize": 9.5, "weight": "bold", "color": "#ffffff"}, ax=ax)
                    ax.axis("off")

        # --------------------------------------------------------------------------
        # Chart 11: Waterfall Chart
        # --------------------------------------------------------------------------
        elif chart_t == "waterfall":
            if effective_y and effective_y in plot_df.columns:
                w_df = plot_df.groupby(x_col, as_index=False)[effective_y].sum().head(12)
                categories = w_df[x_col].astype(str).tolist()
                values = w_df[effective_y].astype(float).tolist()
            else:
                counts = plot_df[x_col].value_counts().head(12)
                categories = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

            cumulative = [0]
            for val in values:
                cumulative.append(cumulative[-1] + val)

            bottoms = [min(cumulative[i], cumulative[i + 1]) for i in range(len(values))]
            heights = [abs(val) for val in values]

            pos_color, neg_color = "#10b981", "#ef4444"
            colors = [pos_color if val >= 0 else neg_color for val in values]
            bars = ax.bar(categories, heights, bottom=bottoms, color=colors, width=0.55, edgecolor="none")

            for i in range(len(values) - 1):
                ax.plot([i, i + 1], [cumulative[i + 1], cumulative[i + 1]], color=muted_color, linestyle="--", linewidth=1)

            for bar, val in zip(bars, values):
                y_text = bar.get_y() + bar.get_height() / 2
                ax.text(bar.get_x() + bar.get_width() / 2, y_text, format_num_human(val),
                        ha="center", va="center", color="#ffffff", fontsize=8.5, weight="bold")

            ax.set_ylabel(effective_y or "Value", fontsize=10, color=muted_color)

        # --------------------------------------------------------------------------
        # Chart 12: Funnel Chart
        # --------------------------------------------------------------------------
        elif chart_t == "funnel":
            is_horizontal_bar = True
            if effective_y and effective_y in plot_df.columns:
                funnel_df = plot_df.groupby(x_col, as_index=False)[effective_y].sum().sort_values(by=effective_y, ascending=False).head(10)
                stages = funnel_df[x_col].astype(str).tolist()
                values = funnel_df[effective_y].astype(float).tolist()
            else:
                counts = plot_df[x_col].value_counts().head(10)
                stages = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

            max_val = max(values) if values and max(values) > 0 else 1
            lefts = [(max_val - v) / 2 for v in values]
            f_colors = resolve_palette_colors(palette or "sunset", len(values))

            y_pos = list(range(len(stages)))
            bars = ax.barh(y_pos, values, left=lefts, color=f_colors, edgecolor="none", height=0.58, align="center")
            ax.set_yticks(y_pos)
            ax.set_yticklabels(stages, fontsize=9.5, weight="bold", color=text_color)
            ax.invert_yaxis()

            for v, bar in zip(values, bars):
                pct = (v / max_val) * 100
                ax.text(max_val / 2, bar.get_y() + bar.get_height() / 2, f"{format_num_human(v)} ({pct:.0f}%)",
                        ha="center", va="center", color="#ffffff", fontsize=9, weight="bold")
            ax.get_xaxis().set_visible(False)

        # --------------------------------------------------------------------------
        # Chart 13: Lollipop Chart
        # --------------------------------------------------------------------------
        elif chart_t == "lollipop":
            is_horizontal_bar = True
            if effective_y and effective_y in plot_df.columns:
                lolli_df = plot_df.groupby(x_col)[effective_y].sum().reset_index().sort_values(by=effective_y).tail(14)
                cats = lolli_df[x_col].astype(str).tolist()
                vals = lolli_df[effective_y].tolist()
            else:
                counts = plot_df[x_col].value_counts().sort_values().tail(14)
                cats = counts.index.astype(str).tolist()
                vals = counts.values.tolist()

            marker_c = resolve_palette_colors(palette, 1)[0]
            y_pos = list(range(len(cats)))
            ax.hlines(y=y_pos, xmin=0, xmax=vals, color=marker_c, alpha=0.55, linewidth=2.4)
            ax.scatter(vals, y_pos, color=marker_c, s=120, alpha=0.95, edgecolors=bg_color, linewidth=2, zorder=3)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(cats, fontsize=9.5, weight="bold", color=text_color)
            
            max_v = max(vals) if vals else 1
            ax.set_xlim(0, max_v * 1.15)
            for y, v in zip(y_pos, vals):
                ax.text(v + (max_v * 0.02), y, format_num_human(v), va="center", ha="left", fontsize=9, weight="bold", color=text_color)
            ax.set_xlabel(effective_y or "Count", fontsize=10, color=muted_color)

        # --------------------------------------------------------------------------
        # Chart 14: Radar / Spider Chart
        # --------------------------------------------------------------------------
        elif chart_t in ["radar", "spider"]:
            num_cols = plot_df.select_dtypes(include=["number"]).columns.tolist()
            if len(num_cols) >= 3:
                features = num_cols[:5]
                num_vars = len(features)
                angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
                angles += angles[:1]

                plot_rows = plot_df.head(3)
                cat_col = x_col if (x_col and x_col in plot_df.columns) else None
                r_colors = resolve_palette_colors(palette, len(plot_rows))

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
                    ax.plot(angles, vals, linewidth=2.2, linestyle="solid", label=lbl, color=r_colors[idx])
                    ax.fill(angles, vals, color=r_colors[idx], alpha=0.22)

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(features, fontsize=9.5, weight="bold", color=text_color)
                ax.set_yticklabels([])
                ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8.5)
            else:
                is_horizontal_bar = True
                colors = resolve_palette_colors(palette, 6)
                sns.barplot(data=plot_df.head(12), x=x_col, y=effective_y, palette=colors, ax=ax)

        # --------------------------------------------------------------------------
        # Chart 15: Bubble Chart
        # --------------------------------------------------------------------------
        elif chart_t == "bubble":
            num_cols = plot_df.select_dtypes(include=["number"]).columns.tolist()
            size_candidates = [c for c in num_cols if c not in [x_col, effective_y]]
            size_col = size_candidates[0] if size_candidates else effective_y

            sizes = plot_df[size_col].abs() if size_col else plot_df[effective_y].abs()
            s_min, s_max = sizes.min(), sizes.max()
            scaled_sizes = 60 + ((sizes - s_min) / max(1e-5, (s_max - s_min))) * 450 if s_max > s_min else [140] * len(plot_df)

            effective_hue = hue_col if (hue_col and hue_col in plot_df.columns) else None
            colors = resolve_palette_colors(palette, 6)
            if effective_hue:
                sns.scatterplot(
                    data=plot_df, x=x_col, y=effective_y, hue=effective_hue, size=scaled_sizes,
                    sizes=(60, 450), palette=colors, alpha=0.82,
                    edgecolor=bg_color, linewidth=1, ax=ax, legend="brief"
                )
            else:
                bubble_color = colors[0]
                sns.scatterplot(
                    data=plot_df, x=x_col, y=effective_y, size=scaled_sizes, color=bubble_color,
                    sizes=(60, 450), alpha=0.82,
                    edgecolor=bg_color, linewidth=1, ax=ax, legend=False
                )
            title = f"{title} (Bubble Size: {size_col})"

        # Fallback
        else:
            is_horizontal_bar = True
            colors = resolve_palette_colors(palette, 8)
            sns.barplot(data=plot_df.head(12), x=x_col, y=effective_y, palette=colors, ax=ax)

        # --------------------------------------------------------------------------
        # Studio-Grade Matplotlib Finishing Touches (Clean Despine, Dynamic Grids)
        # --------------------------------------------------------------------------
        if chart_t not in ["radar", "spider", "treemap", "pie", "donut", "doughnut"]:
            if is_horizontal_bar:
                # Horizontal Bar aesthetic: vertical grid only, no border clutter
                sns.despine(ax=ax, top=True, right=True, left=True, bottom=False)
                ax.xaxis.grid(True, linestyle="--", alpha=0.3, color=grid_line_color)
                ax.yaxis.grid(False)
                ax.tick_params(left=False, bottom=True, colors=muted_color, labelsize=9.5)
                ax.tick_params(axis='x', rotation=0)
                ax.tick_params(axis='y', rotation=0)
            else:
                # Vertical chart aesthetic: horizontal grid only
                sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
                ax.yaxis.grid(True, linestyle="--", alpha=0.3, color=grid_line_color)
                ax.xaxis.grid(False)
                
                # Check if X-axis labels are long categories -> only then rotate
                x_labels = [str(l.get_text()) for l in ax.get_xticklabels()]
                has_long_labels = any(len(lbl) > 5 for lbl in x_labels) if x_labels else False
                rot = 25 if has_long_labels else 0
                
                ax.tick_params(axis='x', rotation=rot, colors=muted_color, labelsize=9.5)
                ax.tick_params(axis='y', colors=muted_color, labelsize=9.5)
                if rot > 0:
                    for lbl in ax.get_xticklabels():
                        lbl.set_ha('right')

        # Magazine / SaaS Typography Title
        ax.set_title(title, fontsize=13.5, weight="bold", color=text_color, pad=16, loc="left")

        leg = ax.get_legend()
        if leg and chart_t not in ["radar", "spider"]:
            leg.set_loc("upper right")
            leg.get_frame().set_facecolor(card_bg)
            leg.get_frame().set_edgecolor(grid_line_color)
            for text in leg.get_texts():
                text.set_color(text_color)
                text.set_fontsize(8.5)

        try:
            fig.tight_layout(pad=1.4)
        except Exception:
            pass

        # Capture exact plotted data so 3D chart elements match 2D chart data 100%
        try:
            chart_meta: Dict[str, Any] = {
                "chart_type": chart_t,
                "x_col": x_col,
                "y_col": effective_y,
                "title": title
            }
            if chart_t in ["scatter", "bubble"]:
                sample_pts = plot_df[[x_col, effective_y]].dropna()
                if len(sample_pts) > 150:
                    sample_pts = sample_pts.sample(n=150, random_state=42)
                chart_meta["points"] = [
                    {"x": float(r[x_col]), "y": float(r[effective_y])}
                    for _, r in sample_pts.iterrows()
                ]
                chart_meta["min_x"] = float(plot_df[x_col].min())
                chart_meta["max_x"] = float(plot_df[x_col].max())
                chart_meta["min_y"] = float(plot_df[effective_y].min())
                chart_meta["max_y"] = float(plot_df[effective_y].max())
            elif chart_t in ["bar", "donut", "doughnut", "pie", "funnel", "treemap", "lollipop", "waterfall"]:
                if 'categories' in locals() and 'values' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(c), "val": float(v)} for c, v in zip(categories, values)
                    ]
                elif 'sizes' in locals() and 'labels' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(l).split('\n')[0], "val": float(s)} for l, s in zip(labels, sizes)
                    ]
                elif 'pie_data' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(k), "val": float(v)} for k, v in pie_data.items()
                    ]
                elif effective_y and effective_y in plot_df.columns and x_col and x_col in plot_df.columns:
                    grouped_p = plot_df.groupby(x_col, as_index=False)[effective_y].sum().head(16)
                    chart_meta["data_points"] = [
                        {"label": str(r[x_col]), "val": float(r[effective_y])} for _, r in grouped_p.iterrows()
                    ]
            elif chart_t in ["line", "trend", "area"]:
                if 'x_vals' in locals() and 'y_vals' in locals():
                    chart_meta["data_points"] = [
                        {"label": str(x), "val": float(y)} for x, y in zip(list(x_vals)[:40], list(y_vals)[:40])
                    ]
            elif chart_t in ["histogram", "hist"]:
                vals = plot_df[x_col].dropna().astype(float).values
                counts, bin_edges = np.histogram(vals, bins=8)
                chart_meta["bins"] = [
                    {"min": float(bin_edges[i]), "max": float(bin_edges[i+1]), "count": int(counts[i])}
                    for i in range(len(counts))
                ]
                chart_meta["min_x"] = float(vals.min())
                chart_meta["max_x"] = float(vals.max())
            
            global LAST_CHART_DATA
            LAST_CHART_DATA = chart_meta
        except Exception:
            pass

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, facecolor=bg_color, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        if output_path and output_path != ":memory:":
            with open(output_path, "wb") as f:
                f.write(buf.getvalue())

        return data_url

    except Exception as e:
        plt.close("all")
        return f"Error generating chart: {str(e)}"
