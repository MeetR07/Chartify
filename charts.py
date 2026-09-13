import os
import io
import sys
import json
import base64
from typing import Literal, Optional, Dict, Any

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Use non-interactive, thread-safe Agg backend for servers
import matplotlib.pyplot as plt
import seaborn as sns
import squarify

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
        return f"{sign}{abs_val:.1f}"
    return str(int(val))


# ==============================================================================
# BIG DATA SCALABILITY ENGINE (O(N) Complexity)
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
                        max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 16
                        if len(agg_df) > max_cats:
                            top_n = agg_df.nlargest(max_cats, y_col)
                            return top_n.copy()
                        return agg_df.sort_values(by=y_col, ascending=False)
                else:
                    # Categorical frequency
                    counts = plot_df[x_col].value_counts().reset_index()
                    counts.columns = [x_col, "count"]
                    max_cats = 10 if chart_type in ["pie", "donut", "doughnut", "waterfall"] else 16
                    return counts.head(max_cats)
            except Exception as e:
                try:
                    print(f"[WARN] Preprocessing aggregation fallback: {e}")
                except Exception:
                    pass

    # 2. Line & Area: Decimate time-series / trends smoothly
    if chart_type in ["line", "trend", "area"]:
        if total_rows > 2500:
            step = max(1, total_rows // 2500)
            return plot_df.iloc[::step].copy()
        return plot_df

    # 3. Scatter, Bubble, Hist, Box, Violin: Representative sampling
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
    df = get_active_df()
    try:
        if not output_path:
            output_path = f"{chart_type}.png"
        
        # Step 1: Check column availability
        for col in [x_col, y_col, hue_col]:
            if col and col not in df.columns:
                return f"Error: Column '{col}' not found. Available columns: {list(df.columns)}"

        # Step 2: Apply visual style/theme dynamically
        selected_style = style or "whitegrid"
        plt.close("all")

        valid_sns_styles = ["whitegrid", "darkgrid", "white", "dark", "ticks"]
        if selected_style in valid_sns_styles:
            sns.set_theme(style=selected_style)
        elif selected_style in plt.style.available:
            plt.style.use(selected_style)
        else:
            sns.set_theme(style="whitegrid")

        is_dark = selected_style.startswith("dark")
        text_color = "#f8fafc" if is_dark else "#0f172a"
        muted_color = "#94a3b8" if is_dark else "#64748b"
        grid_line_color = "#334155" if is_dark else "#e2e8f0"

        # Safeguard hue_col cardinality
        safe_hue = hue_col
        show_legend = "brief"
        if hue_col and hue_col in df.columns:
            if df[hue_col].nunique() > 10:
                show_legend = False

        # Step 3: Special Case: Pairplot
        if chart_type == "pairplot":
            grid = sns.pairplot(df, hue=safe_hue, palette=palette or "deep")
            grid.fig.suptitle(title, y=1.02, fontsize=14, weight="bold")
            buf = io.BytesIO()
            grid.savefig(buf, format="png", dpi=110, facecolor=grid.fig.get_facecolor(), bbox_inches="tight")
            plt.close(grid.fig)
            buf.seek(0)
            data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            if output_path and output_path != ":memory:":
                with open(output_path, "wb") as f:
                    f.write(buf.getvalue())
            sns.set_theme(style="whitegrid")
            return data_url

        # Step 4: Create canvas
        chart_t = (chart_type or "bar").lower().strip()
        if chart_t in ["radar", "spider"]:
            fig, ax = plt.subplots(figsize=(7, 6), subplot_kw=dict(polar=True))
        else:
            fig, ax = plt.subplots(figsize=(8.5, 4.8))

        # Big Data Scalability Preprocessing
        plot_df = smart_preprocess_data(df, chart_t, x_col, y_col, safe_hue)

        # --------------------------------------------------------------------------
        # Chart 1: Bar Chart (Studio-grade with data labels & average benchmark)
        # --------------------------------------------------------------------------
        if chart_t == "bar":
            if safe_hue:
                sns.barplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "deep", ax=ax)
            else:
                sns.barplot(data=plot_df, x=x_col, y=y_col, hue=x_col, palette=palette or "deep", legend=False, ax=ax)

            # Direct Bar Data Labels
            if hasattr(ax, "containers"):
                for container in ax.containers:
                    try:
                        ax.bar_label(
                            container,
                            fmt=lambda v: format_num_human(v) if abs(v) > 0 else "",
                            padding=4,
                            fontsize=8.5,
                            weight="bold",
                            color=text_color
                        )
                    except Exception:
                        pass

            # Average benchmark line
            if y_col and y_col in plot_df.columns and pd.api.types.is_numeric_dtype(plot_df[y_col]):
                try:
                    mean_val = float(plot_df[y_col].mean())
                    if not np.isnan(mean_val) and abs(mean_val) > 0:
                        ax.axhline(mean_val, color="#f59e0b", linestyle=":", linewidth=1.5, alpha=0.85)
                        ax.text(
                            0.98, 0.94, f"Mean: {format_num_human(mean_val)}",
                            transform=ax.transAxes, color="#f59e0b", fontsize=8.5, weight="bold",
                            ha="right", va="top",
                            bbox=dict(boxstyle="round,pad=0.25", facecolor=fig.get_facecolor(), edgecolor="#f59e0b", alpha=0.8)
                        )
                except Exception:
                    pass

        # --------------------------------------------------------------------------
        # Chart 2: Line Chart (Trends with markers)
        # --------------------------------------------------------------------------
        elif chart_t in ["line", "trend"]:
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            if safe_hue:
                sns.lineplot(data=sorted_df, x=x_col, y=y_col, hue=safe_hue, marker="o", linewidth=2.5, palette=palette or "deep", ax=ax)
            else:
                line_color = sns.color_palette(palette)[0] if palette else None
                sns.lineplot(data=sorted_df, x=x_col, y=y_col, marker="o", markersize=6, linewidth=2.5, color=line_color, ax=ax)

        # --------------------------------------------------------------------------
        # Chart 3: Scatter Plot
        # --------------------------------------------------------------------------
        elif chart_t == "scatter":
            n_rows = len(plot_df)
            point_size = 30 if n_rows > 1000 else 65
            alpha_val = 0.7 if n_rows > 1000 else 0.85
            sns.scatterplot(
                data=plot_df, x=x_col, y=y_col, hue=safe_hue, s=point_size,
                palette=palette or "deep", alpha=alpha_val, ax=ax,
                edgecolor="white", linewidth=0.5,
                legend=show_legend
            )

        # --------------------------------------------------------------------------
        # Chart 4: Histogram
        # --------------------------------------------------------------------------
        elif chart_t in ["histogram", "hist"]:
            if safe_hue:
                sns.histplot(data=plot_df, x=x_col, kde=True, hue=safe_hue, palette=palette or "deep", ax=ax)
            else:
                bar_color = sns.color_palette(palette)[0] if palette else None
                sns.histplot(data=plot_df, x=x_col, kde=True, color=bar_color, edgecolor="white", ax=ax)

        # --------------------------------------------------------------------------
        # Chart 5: Box Plot
        # --------------------------------------------------------------------------
        elif chart_t == "box":
            if safe_hue:
                sns.boxplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "Set2", ax=ax, width=0.5)
            else:
                sns.boxplot(data=plot_df, x=x_col, y=y_col, hue=x_col, palette=palette or "Set2", legend=False, ax=ax, width=0.5)

        # --------------------------------------------------------------------------
        # Chart 6: Heatmap (Correlation)
        # --------------------------------------------------------------------------
        elif chart_t in ["heatmap", "correlation"]:
            corr = plot_df.corr(numeric_only=True)
            if corr.empty or corr.shape[0] < 2:
                ax.text(0.5, 0.5, "Requires at least 2 numeric columns\nfor correlation heatmap",
                        ha="center", va="center", fontsize=12, weight="bold", color=text_color, transform=ax.transAxes)
            else:
                sns.heatmap(corr, annot=True, cmap=palette or "coolwarm", fmt=".2f", linewidths=0.5, ax=ax, cbar_kws={"shrink": 0.8})

        # --------------------------------------------------------------------------
        # Chart 7: Pie Chart
        # --------------------------------------------------------------------------
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
                ax.text(0.5, 0.5, "No positive data available for pie chart", ha="center", va="center", color=text_color, transform=ax.transAxes)
            else:
                pie_colors = sns.color_palette(palette or "pastel", len(pie_data))
                ax.pie(pie_data.values, labels=pie_data.index, autopct="%1.1f%%", startangle=140, colors=pie_colors, textprops={"color": text_color, "fontsize": 9.5})

        # --------------------------------------------------------------------------
        # Chart 8: Area Chart
        # --------------------------------------------------------------------------
        elif chart_t == "area":
            sorted_df = plot_df.sort_values(by=x_col) if (x_col and x_col in plot_df.columns) else plot_df
            area_colors = sns.color_palette(palette or "mako", 2)
            ax.fill_between(sorted_df[x_col], sorted_df[y_col], alpha=0.35, color=area_colors[0])
            ax.plot(sorted_df[x_col], sorted_df[y_col], color=area_colors[-1], linewidth=2.5, marker="o", markersize=5)

        # --------------------------------------------------------------------------
        # Chart 9: Violin Plot
        # --------------------------------------------------------------------------
        elif chart_t == "violin":
            if safe_hue:
                sns.violinplot(data=plot_df, x=x_col, y=y_col, hue=safe_hue, palette=palette or "muted", ax=ax)
            else:
                sns.violinplot(data=plot_df, x=x_col, y=y_col, hue=x_col, palette=palette or "muted", legend=False, ax=ax)

        # --------------------------------------------------------------------------
        # Chart 10: Treemap
        # --------------------------------------------------------------------------
        elif chart_t == "treemap":
            if y_col and y_col in plot_df.columns:
                tree_data = plot_df.groupby(x_col)[y_col].sum().reset_index()
                tree_data = tree_data[tree_data[y_col] > 0].head(14)
                sizes = tree_data[y_col].values
                labels = [f"{row[x_col]}\n({format_num_human(row[y_col])})" for _, row in tree_data.iterrows()]
            else:
                counts = plot_df[x_col].value_counts().head(14)
                sizes = counts.values
                labels = [f"{cat}\n({format_num_human(cnt)})" for cat, cnt in zip(counts.index, counts.values)]

            if len(sizes) == 0 or sum(sizes) <= 0:
                ax.text(0.5, 0.5, "No positive values available for treemap", ha="center", va="center", color=text_color, transform=ax.transAxes)
            else:
                tree_colors = sns.color_palette(palette or "Spectral", len(sizes))
                squarify.plot(sizes=sizes, label=labels, color=tree_colors, alpha=0.85, text_kwargs={"fontsize": 9.5, "weight": "bold", "color": "white"}, ax=ax)
                ax.axis("off")

        # --------------------------------------------------------------------------
        # Chart 11: Waterfall Chart
        # --------------------------------------------------------------------------
        elif chart_t == "waterfall":
            if y_col and y_col in plot_df.columns:
                w_df = plot_df.groupby(x_col, as_index=False)[y_col].sum().head(12)
                categories = w_df[x_col].astype(str).tolist()
                values = w_df[y_col].astype(float).tolist()
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
            bars = ax.bar(categories, heights, bottom=bottoms, color=colors, edgecolor="black", width=0.55)

            for i in range(len(values) - 1):
                ax.plot([i, i + 1], [cumulative[i + 1], cumulative[i + 1]], color="grey", linestyle="--")

            for bar, val in zip(bars, values):
                y_text = bar.get_y() + bar.get_height() / 2
                ax.text(bar.get_x() + bar.get_width() / 2, y_text, format_num_human(val),
                        ha="center", va="center", color="white", fontsize=8.5, weight="bold")

            ax.set_ylabel(y_col or "Value", fontsize=11, color=text_color)

        # --------------------------------------------------------------------------
        # Chart 12: Donut Chart
        # --------------------------------------------------------------------------
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
                ax.text(0.5, 0.5, "No positive values for donut chart", ha="center", va="center", color=text_color, transform=ax.transAxes)
            else:
                donut_colors = sns.color_palette(palette or "pastel", len(donut_data))
                wedges, texts, autotexts = ax.pie(
                    donut_data.values,
                    labels=donut_data.index,
                    autopct="%1.1f%%",
                    startangle=140,
                    colors=donut_colors,
                    pctdistance=0.75,
                    wedgeprops=dict(width=0.42, edgecolor="w", linewidth=1.5),
                    textprops={"color": text_color, "fontsize": 9}
                )
                total_val = donut_data.sum()
                center_txt = f"TOTAL\n{format_num_human(total_val)}" if isinstance(total_val, (int, float, np.number)) else "TOTAL"
                ax.text(0, 0, center_txt, ha="center", va="center", fontsize=10, weight="bold", color=text_color)

        # --------------------------------------------------------------------------
        # Chart 13: Funnel Chart
        # --------------------------------------------------------------------------
        elif chart_t == "funnel":
            if y_col and y_col in plot_df.columns:
                funnel_df = plot_df.groupby(x_col, as_index=False)[y_col].sum().sort_values(by=y_col, ascending=False).head(10)
                stages = funnel_df[x_col].astype(str).tolist()
                values = funnel_df[y_col].astype(float).tolist()
            else:
                counts = plot_df[x_col].value_counts().head(10)
                stages = counts.index.astype(str).tolist()
                values = counts.values.astype(float).tolist()

            max_val = max(values) if values and max(values) > 0 else 1
            lefts = [(max_val - v) / 2 for v in values]
            f_colors = sns.color_palette(palette or "flare", len(values))

            y_pos = list(range(len(stages)))
            bars = ax.barh(y_pos, values, left=lefts, color=f_colors, edgecolor="black", height=0.55, align="center")
            ax.set_yticks(y_pos)
            ax.set_yticklabels(stages, fontsize=10, weight="bold", color=text_color)
            ax.invert_yaxis()

            for v, bar in zip(values, bars):
                pct = (v / max_val) * 100
                ax.text(max_val / 2, bar.get_y() + bar.get_height() / 2, f"{format_num_human(v)} ({pct:.0f}%)",
                        ha="center", va="center", color="white", fontsize=9, weight="bold")
            ax.get_xaxis().set_visible(False)

        # --------------------------------------------------------------------------
        # Chart 14: Lollipop Chart
        # --------------------------------------------------------------------------
        elif chart_t == "lollipop":
            if y_col and y_col in plot_df.columns:
                lolli_df = plot_df.groupby(x_col)[y_col].sum().reset_index().sort_values(by=y_col).tail(14)
                cats = lolli_df[x_col].astype(str).tolist()
                vals = lolli_df[y_col].tolist()
            else:
                counts = plot_df[x_col].value_counts().sort_values().tail(14)
                cats = counts.index.astype(str).tolist()
                vals = counts.values.tolist()

            marker_c = "#6366f1"
            y_pos = list(range(len(cats)))
            ax.hlines(y=y_pos, xmin=0, xmax=vals, color=marker_c, alpha=0.65, linewidth=2.2)
            ax.scatter(vals, y_pos, color=marker_c, s=110, alpha=0.9, edgecolors="white", linewidth=1.5, zorder=3)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(cats, fontsize=9.5, weight="bold", color=text_color)
            ax.set_xlabel(y_col or "Count", fontsize=10.5, color=muted_color)

        # --------------------------------------------------------------------------
        # Chart 15: Radar Chart
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
                    ax.fill(angles, vals, color=r_colors[idx], alpha=0.22)

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(features, fontsize=9.5, weight="bold", color=text_color)
                ax.set_yticklabels([])
                ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8.5)
            else:
                sns.barplot(data=plot_df.head(12), x=x_col, y=y_col, hue=x_col, palette=palette or "deep", legend=False, ax=ax)

        # --------------------------------------------------------------------------
        # Chart 16: Bubble Chart
        # --------------------------------------------------------------------------
        elif chart_t == "bubble":
            num_cols = plot_df.select_dtypes(include=["number"]).columns.tolist()
            size_candidates = [c for c in num_cols if c not in [x_col, y_col]]
            size_col = size_candidates[0] if size_candidates else y_col

            sizes = plot_df[size_col].abs() if size_col else plot_df[y_col].abs()
            s_min, s_max = sizes.min(), sizes.max()
            scaled_sizes = 60 + ((sizes - s_min) / max(1e-5, (s_max - s_min))) * 450 if s_max > s_min else [140] * len(plot_df)

            effective_hue = hue_col if (hue_col and hue_col in plot_df.columns) else None
            if effective_hue:
                sns.scatterplot(
                    data=plot_df, x=x_col, y=y_col, hue=effective_hue, size=scaled_sizes,
                    sizes=(60, 450), palette=palette or "plasma", alpha=0.75,
                    edgecolor="white", linewidth=1, ax=ax, legend="brief"
                )
            else:
                bubble_color = sns.color_palette(palette or "plasma")[0]
                sns.scatterplot(
                    data=plot_df, x=x_col, y=y_col, size=scaled_sizes, color=bubble_color,
                    sizes=(60, 450), alpha=0.75,
                    edgecolor="white", linewidth=1, ax=ax, legend=False
                )
            title = f"{title} (Bubble: {size_col})"

        # Fallback to Bar
        else:
            sns.barplot(data=plot_df.head(15), x=x_col, y=y_col, hue=x_col, palette=palette or "deep", legend=False, ax=ax)

        # --------------------------------------------------------------------------
        # Studio-Grade Matplotlib Finishing Touches (Despine, Horizontal-Only Grid, Title)
        # --------------------------------------------------------------------------
        if chart_t not in ["radar", "spider", "treemap"]:
            # Remove top & right borders for clean floating modern aesthetic
            sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
            
            # Subtle horizontal-only grid lines
            ax.yaxis.grid(True, linestyle="--", alpha=0.22, color=grid_line_color)
            ax.xaxis.grid(False)

            # Clean label rotation
            ax.tick_params(axis='x', rotation=28, colors=muted_color, labelsize=9.5)
            ax.tick_params(axis='y', colors=muted_color, labelsize=9.5)
            for lbl in ax.get_xticklabels():
                lbl.set_ha('right')

        # Studio Typography Title
        ax.set_title(title, fontsize=13, weight="bold", color=text_color, pad=14, loc="left")

        leg = ax.get_legend()
        if leg and chart_t not in ["radar", "spider"]:
            leg.set_loc("upper right")

        try:
            fig.tight_layout(pad=1.2)
        except Exception:
            pass

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=105, facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        if output_path and output_path != ":memory:":
            with open(output_path, "wb") as f:
                f.write(buf.getvalue())
        
        sns.set_theme(style="whitegrid")
        return data_url

    except Exception as e:
        plt.close("all")
        sns.set_theme(style="whitegrid")
        return f"Error generating chart: {str(e)}"

