import io
import base64
import math
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BG = "#060b18"
TEXT = "#e8f4fd"
PRI = "#00f5c4"
SEC = "#7b61ff"

def _to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

def detect_dataset_type(df: pd.DataFrame) -> str:
    if df is None or df.shape[1] == 0:
        return "single_column"
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if len(df.columns) == 1:
        return "single_column"
    if date_cols:
        return "time_series"
    if len(num_cols) >= 3 and len(cat_cols) <= len(num_cols):
        return "numeric_rich"
    if len(cat_cols) >= max(3, len(df.columns) // 2) and len(num_cols) <= len(cat_cols):
        ref_patterns = ["range", "normal", "unit", "code", "catalog", "sku", "reference"]
        lower_cols = " ".join(df.columns.astype(str)).lower()
        if any(p in lower_cols for p in ref_patterns):
            return "reference_table"
        return "categorical_rich"
    return "mixed"

def get_smart_charts(df: pd.DataFrame, dataset_type: str):
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    available = []
    if dataset_type in ("reference_table", "categorical_rich"):
        return ["category_distribution", "category_pie", "value_counts_grid", "text_summary_image", "range_parser_chart"]
    if len(num_cols) >= 2:
        available.append("correlation_matrix")
        available.append("heatmap")
        available.append("cluster_plot")
        available.append("dendrogram")
        available.append("scatter_plot")
        available.append("distribution_plot")
    if len(num_cols) >= 3:
        available.append("pca_plot")
        available.append("bubble_chart")
    if date_cols:
        available.append("time_series")
    if cat_cols and num_cols:
        available.append("bar_chart")
        available.append("box_plot")
        available.append("violin_plot")
    if cat_cols and len(num_cols) >= 2:
        available.append("confusion_matrix")
        available.append("feature_importance")
    return available or ["text_summary_image"]

def generate_smart_insights(df: pd.DataFrame, dataset_type: str, filename: str) -> str:
    rows = df.shape[0]
    cols = df.shape[1]
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    uniq_counts = {c: int(df[c].nunique(dropna=True)) for c in df.columns}
    obs = []
    if dataset_type == "numeric_rich":
        obs.append("multiple numeric features suitable for statistical and ML analysis")
    if dataset_type == "categorical_rich":
        obs.append("primarily categorical values; comparison and distribution charts are suitable")
    if dataset_type == "mixed":
        obs.append("both numeric and categorical features; hybrid charts are possible")
    if dataset_type == "reference_table":
        obs.append("lookup or reference style data; value distributions and ranges are key")
    if dataset_type == "time_series":
        obs.append("temporal data detected; trend and seasonality analysis is applicable")
    if dataset_type == "single_column":
        obs.append("single column dataset; summary and value counts are applicable")
    need = []
    if not num_cols:
        need.append("numeric columns to enable correlation, clustering, PCA and distribution analysis")
    if not cat_cols:
        need.append("categorical columns to enable bar, box, violin and ML classification charts")
    if dataset_type != "time_series" and not date_cols:
        need.append("date/time columns to enable time series analysis")
    parts = []
    parts.append(f"Dataset {filename} has {rows} rows and {cols} columns ({len(num_cols)} numeric, {len(cat_cols)} categorical).")
    parts.append(f"Detected type: {dataset_type.replace('_',' ')}; observations: {', '.join(obs)}.")
    parts.append(f"Unique values per column: " + ", ".join([f"{k}: {v}" for k, v in uniq_counts.items()]))
    if need:
        parts.append("To unlock more chart types, add " + "; ".join(need) + ".")
    return " ".join(parts)

def _style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT)
    for spine in ax.spines.values():
        spine.set_color("#1a2d4a")

def gen_category_distribution(df: pd.DataFrame):
    cat_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]
    if not cat_cols:
        s = pd.Series(["All Rows"], name="All")
        counts = {"All": len(df)}
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor(BG)
        ax.barh(list(counts.keys()), list(counts.values()), color=PRI)
        _style_ax(ax)
        ax.set_title("Category Distribution", color=TEXT)
        return _to_base64(fig)
    col = cat_cols[0]
    vc = df[col].astype(str).value_counts().head(15)
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor(BG)
    ax.barh(vc.index.tolist()[::-1], vc.values.tolist()[::-1], color=PRI)
    _style_ax(ax)
    ax.set_title(f"Category Distribution • {col}", color=TEXT)
    return _to_base64(fig)

def gen_category_pie(df: pd.DataFrame):
    cat_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]
    labels = []
    sizes = []
    if cat_cols:
        col = cat_cols[0]
        vc = df[col].astype(str).value_counts().head(8)
        labels = vc.index.tolist()
        sizes = vc.values.tolist()
    if not labels:
        labels = ["All"]
        sizes = [len(df)]
    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor(BG)
    wedges, texts = ax.pie(sizes, labels=labels, colors=[PRI, SEC], textprops={"color": TEXT})
    ax.set_title("Category Proportions", color=TEXT)
    return _to_base64(fig)

def gen_value_counts_grid(df: pd.DataFrame):
    cat_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]
    cols = cat_cols[:6] if cat_cols else []
    if not cols:
        cols = [df.columns[0]]
    n = len(cols)
    rows = math.ceil(n / 3)
    fig, axes = plt.subplots(rows, 3, figsize=(12, rows * 3))
    fig.patch.set_facecolor(BG)
    axes = np.array(axes).reshape(-1)
    for i, c in enumerate(cols):
        ax = axes[i]
        vc = df[c].astype(str).value_counts().head(10)
        ax.bar(vc.index.tolist(), vc.values.tolist(), color=PRI)
        ax.set_title(c, color=TEXT, fontsize=10)
        ax.tick_params(axis="x", rotation=45)
        _style_ax(ax)
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    return _to_base64(fig)

def gen_text_summary_image(df: pd.DataFrame, filename: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    text = []
    text.append(f"Dataset: {filename}")
    text.append(f"Rows: {df.shape[0]} • Columns: {df.shape[1]}")
    dtypes = ", ".join([f"{c}:{str(df[c].dtype)}" for c in df.columns])
    text.append(f"Dtypes: {dtypes}")
    uv = ", ".join([f"{c}:{int(df[c].nunique(dropna=True))}" for c in df.columns])
    text.append(f"Unique values: {uv}")
    top3 = []
    for c in df.columns:
        vc = df[c].astype(str).value_counts().head(3)
        top3.append(f"{c} → " + "; ".join([f"{idx}({val})" for idx, val in vc.items()]))
    y = 0.9
    ax.text(0.05, y, "SUMMARY", color=PRI, fontsize=14, fontweight="bold", transform=ax.transAxes)
    y -= 0.08
    for line in text:
        ax.text(0.05, y, line, color=TEXT, fontsize=11, transform=ax.transAxes)
        y -= 0.06
    ax.text(0.05, y, "Top values per column:", color=SEC, fontsize=12, transform=ax.transAxes)
    y -= 0.06
    for line in top3:
        ax.text(0.05, y, line, color=TEXT, fontsize=10, transform=ax.transAxes)
        y -= 0.045
    return _to_base64(fig)

def gen_range_parser_chart(df: pd.DataFrame):
    cols = df.columns.tolist()
    ranges = []
    for c in cols:
        series = df[c].astype(str)
        for val in series.head(200):
            m = re.findall(r'([<>]?\s*\-?\d+\.?\d*)\s*-\s*([<>]?\s*\-?\d+\.?\d*)', val)
            if m:
                try:
                    a = m[0][0].replace("<", "").replace(">", "").strip()
                    b = m[0][1].replace("<", "").replace(">", "").strip()
                    lo = float(a)
                    hi = float(b)
                    ranges.append((c, lo, hi))
                except:
                    pass
            else:
                m2 = re.findall(r'[<>]\s*\-?\d+\.?\d*', val)
                if m2:
                    try:
                        x = float(re.findall(r'\-?\d+\.?\d*', m2[0])[0])
                        if "<" in m2[0]:
                            ranges.append((c, -np.inf, x))
                        else:
                            ranges.append((c, x, np.inf))
                    except:
                        pass
    if not ranges:
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor(BG)
        ax.text(0.05, 0.5, "No range patterns detected", color=TEXT)
        ax.axis("off")
        return _to_base64(fig)
    uniq = {}
    for c, lo, hi in ranges:
        uniq.setdefault(c, []).append((lo, hi))
    items = list(uniq.items())[:12]
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG)
    y = np.arange(len(items))
    lo_vals = [np.nanmin([r[0] for r in rs]) if all(np.isfinite([r[0] for r in rs])) else 0 for _, rs in items]
    hi_vals = [np.nanmax([r[1] for r in rs]) if all(np.isfinite([r[1] for r in rs])) else 0 for _, rs in items]
    for i, (name, rs) in enumerate(items):
        finite = [(a, b) for a, b in rs if np.isfinite(a) and np.isfinite(b)]
        if finite:
            ax.plot([lo_vals[i], hi_vals[i]], [y[i], y[i]], color=PRI, linewidth=6)
        else:
            ax.scatter([0], [y[i]], color=SEC)
    ax.set_yticks(y)
    ax.set_yticklabels([n for n, _ in items], color=TEXT)
    ax.set_title("Reference Ranges", color=TEXT)
    _style_ax(ax)
    return _to_base64(fig)

def generate_fallback_charts(df: pd.DataFrame, dataset_type: str):
    out = []
    out.append({"type": "category_distribution", "title": "Category Distribution", "image": gen_category_distribution(df)})
    out.append({"type": "category_pie", "title": "Category Proportions", "image": gen_category_pie(df)})
    out.append({"type": "value_counts_grid", "title": "Value Counts Grid", "image": gen_value_counts_grid(df)})
    out.append({"type": "text_summary_image", "title": "Dataset Summary", "image": gen_text_summary_image(df, "dataset")})
    out.append({"type": "range_parser_chart", "title": "Reference Range Chart", "image": gen_range_parser_chart(df)})
    return out
