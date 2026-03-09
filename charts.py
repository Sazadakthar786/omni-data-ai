import io, base64, re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import confusion_matrix
from sklearn.impute import SimpleImputer
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ── Palette ──────────────────────────────────────────────────────────────────
P = {
    'primary': '#00f5c4', 'secondary': '#7b61ff', 'accent': '#ff6b6b',
    'bg': '#060b18', 'surface': '#0d1628', 'text': '#e8f4fd', 'muted': '#5a7a99'
}
COLORS = ['#00f5c4','#7b61ff','#ff6b6b','#ffd166','#06d6a0','#118ab2','#e07a5f','#3d405b']

def set_style(light=False):
    if light:
        plt.rcParams.update({
            'figure.facecolor': '#f8fafc', 'axes.facecolor': '#ffffff',
            'axes.edgecolor': '#e2e8f0', 'axes.labelcolor': '#1e293b',
            'text.color': '#1e293b', 'xtick.color': '#64748b', 'ytick.color': '#64748b',
            'grid.color': '#e2e8f0', 'grid.alpha': 0.6, 'font.family': 'monospace',
            'axes.spines.top': False, 'axes.spines.right': False,
        })
        return '#f8fafc'
    else:
        plt.rcParams.update({
            'figure.facecolor': P['bg'], 'axes.facecolor': P['surface'],
            'axes.edgecolor': '#1e3a5f', 'axes.labelcolor': P['text'],
            'text.color': P['text'], 'xtick.color': '#8ab4cc', 'ytick.color': '#8ab4cc',
            'grid.color': '#1e3a5f', 'grid.alpha': 0.4, 'font.family': 'monospace',
            'axes.spines.top': False, 'axes.spines.right': False,
        })
        return P['bg']

def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded

# ── Data Loading ──────────────────────────────────────────────────────────────
def load_data(file, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext == 'csv':
        return pd.read_csv(file)
    elif ext in ('xls', 'xlsx'):
        return pd.read_excel(file)
    elif ext == 'json':
        content = __import__('json').load(file)
        if isinstance(content, list): return pd.DataFrame(content)
        return pd.DataFrame(content) if any(isinstance(v, list) for v in content.values()) else pd.DataFrame([content])
    elif ext == 'pdf':
        import pdfplumber
        rows = []
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    if table: rows.extend(table)
        if rows:
            df = pd.DataFrame(rows[1:], columns=rows[0])
            for c in df.columns:
                try: df[c] = pd.to_numeric(df[c])
                except: pass
            return df
        raise ValueError("No table data found in PDF")
    elif ext in ('py', 'r'):
        content = file.read().decode('utf-8')
        rows = []
        for line in content.split('\n'):
            nums = re.findall(r'-?\d+\.?\d*', line)
            if len(nums) >= 2: rows.append([float(n) for n in nums])
        if rows:
            mc = max(len(r) for r in rows)
            for r in rows:
                while len(r) < mc: r.append(np.nan)
            return pd.DataFrame(rows, columns=[f'col_{i}' for i in range(mc)])
        raise ValueError("No numeric data found in code file")
    raise ValueError(f"Unsupported format: {ext}")

def clean_dataframe(df):
    report = []
    orig = len(df)
    df = df.dropna(how='all').dropna(axis=1, how='all')
    df.columns = [str(c).strip().replace(' ', '_').lower() for c in df.columns]
    for col in df.columns:
        try: df[col] = pd.to_numeric(df[col])
        except: pass
    num = df.select_dtypes(include=np.number).columns
    cat = df.select_dtypes(exclude=np.number).columns
    missing_before = df.isnull().sum().sum()
    if len(num): df[num] = df[num].fillna(df[num].median())
    if len(cat): df[cat] = df[cat].fillna(df[cat].mode().iloc[0] if len(df[cat].mode()) else 'Unknown')
    report.append(f"Rows: {orig} → {len(df)}")
    report.append(f"Missing values imputed: {missing_before - df.isnull().sum().sum()}")
    report.append(f"Numeric features: {list(num)}")
    report.append(f"Categorical features: {list(cat)}")
    return df, report

def analyze_data(df):
    num = df.select_dtypes(include=np.number).columns.tolist()
    cat = df.select_dtypes(exclude=np.number).columns.tolist()
    date_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['date','time','year','month','day','timestamp'])]
    suggestions = []
    if len(num) >= 2: suggestions += ['correlation_matrix', 'scatter_plot']
    if len(num) >= 3: suggestions += ['pca_plot', 'cluster_plot', 'heatmap']
    if cat and num: suggestions += ['bar_chart', 'box_plot', 'violin_plot']
    if len(num) >= 2: suggestions += ['dendrogram', 'distribution_plot', 'anomaly_detection']
    if date_cols: suggestions.append('time_series')
    if cat and len(num) >= 2: suggestions += ['confusion_matrix', 'feature_importance']
    return {
        'num_cols': num, 'cat_cols': cat, 'date_cols': date_cols,
        'n_rows': len(df), 'n_cols': len(df.columns),
        'suggestions': list(dict.fromkeys(suggestions)),
        'stats': df.describe().round(3).to_dict()
    }

def get_top3_recommendations(df, analysis):
    """Auto-recommend top 3 best charts for this specific dataset."""
    num = analysis['num_cols']
    cat = analysis['cat_cols']
    date = analysis['date_cols']
    recs = []
    if date: recs.append(('time_series', 'Date column detected — time series analysis recommended'))
    if len(num) >= 3: recs.append(('correlation_matrix', f'Strong correlation candidates found across {len(num)} numeric features'))
    if len(num) >= 3: recs.append(('cluster_plot', f'Dataset has {analysis["n_rows"]} samples ideal for clustering'))
    if cat and num: recs.append(('feature_importance', f'Categorical target "{cat[0]}" with {len(num)} numeric features'))
    if len(num) >= 2: recs.append(('distribution_plot', 'Distribution analysis recommended for all numeric features'))
    if len(num) >= 2: recs.append(('anomaly_detection', 'Anomaly detection available for outlier discovery'))
    return recs[:3]

# ── Chart Generators ──────────────────────────────────────────────────────────
def gen_correlation_matrix(df, num_cols, theme='dark'):
    bg = set_style(theme == 'light')
    data = df[num_cols].select_dtypes(include=np.number)
    corr = data.corr()
    fig, ax = plt.subplots(figsize=(max(7, len(num_cols)), max(6, len(num_cols)-1)))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    sns.heatmap(corr, mask=mask, cmap=cmap, vmax=1, vmin=-1, center=0,
                annot=True, fmt='.2f', linewidths=0.5, ax=ax,
                annot_kws={'size': 8, 'color': 'white' if theme == 'dark' else 'black'})
    ax.set_title('Correlation Matrix', fontsize=14, color=P['primary'], pad=15, fontweight='bold')
    fig.tight_layout()
    pairs = [(num_cols[i], num_cols[j], abs(corr.iloc[i,j])) for i in range(len(num_cols)) for j in range(i+1, len(num_cols))]
    pairs.sort(key=lambda x: x[2], reverse=True)
    top = pairs[0] if pairs else None
    insight = f"Strongest correlation: **{top[0]}** & **{top[1]}** (r={top[2]:.3f}). " if top else ""
    insight += f"Analyzed {len(num_cols)} numeric features across {len(df)} samples."
    return fig_to_b64(fig), insight

def gen_heatmap(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    data = df[num_cols].head(50)
    scaler = StandardScaler()
    scaled = pd.DataFrame(scaler.fit_transform(data), columns=num_cols)
    fig, ax = plt.subplots(figsize=(max(8, len(num_cols)), min(14, max(6, len(data)//3))))
    sns.heatmap(scaled.T, cmap='YlOrRd', ax=ax, linewidths=0.1, cbar_kws={'label': 'Standardized Value'})
    ax.set_title('Data Heatmap (Standardized)', fontsize=14, color=P['primary'], pad=15, fontweight='bold')
    fig.tight_layout()
    insight = f"Heatmap shows standardized values for {len(num_cols)} features. Bright = high values, dark = low values. Rows represent features, columns represent samples."
    return fig_to_b64(fig), insight

def gen_cluster_plot(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    data = df[num_cols].dropna()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(data)
    if scaled.shape[1] > 2:
        pca = PCA(n_components=2)
        reduced = pca.fit_transform(scaled)
        xlabel, ylabel = 'PC1', 'PC2'
    else:
        reduced = scaled; xlabel, ylabel = num_cols[0], num_cols[1]
    k = min(5, max(2, len(data) // 20))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(scaled)
    fig, ax = plt.subplots(figsize=(9, 6))
    for i in range(k):
        mask = labels == i
        ax.scatter(reduced[mask, 0], reduced[mask, 1], c=COLORS[i], label=f'Cluster {i+1}', alpha=0.75, s=40, edgecolors='none')
    centers = km.cluster_centers_
    c2d = PCA(n_components=2).fit_transform(centers) if scaled.shape[1] > 2 else centers
    ax.scatter(c2d[:, 0], c2d[:, 1], c='white', s=200, marker='X', zorder=5, label='Centroids')
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.set_title(f'K-Means Clustering (k={k})', fontsize=14, color=P['primary'], pad=15, fontweight='bold')
    ax.legend(facecolor=P['surface'], edgecolor='#1e3a5f')
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    sizes = [int((labels == i).sum()) for i in range(k)]
    insight = f"**{k} clusters** identified. Cluster sizes: {', '.join([f'Cluster {i+1}: {s} samples' for i,s in enumerate(sizes)])}. Points projected to 2D via PCA."
    return fig_to_b64(fig), insight

def gen_pca_plot(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    data = df[num_cols].dropna()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(data)
    pca = PCA(); pca.fit(scaled)
    explained = pca.explained_variance_ratio_ * 100
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    n = min(10, len(explained))
    ax1.bar(range(1, n+1), explained[:n], color=[P['primary'] if i==0 else P['secondary'] for i in range(n)], alpha=0.85)
    ax1.plot(range(1, n+1), np.cumsum(explained[:n]), 'o-', color=P['accent'], label='Cumulative')
    ax1.set_xlabel('Component'); ax1.set_ylabel('Variance Explained (%)')
    ax1.set_title('PCA Scree Plot', fontsize=13, color=P['primary'], fontweight='bold')
    ax1.legend(facecolor=P['surface'])
    proj = pca.transform(scaled)
    sc = ax2.scatter(proj[:, 0], proj[:, 1], c=proj[:, 2] if proj.shape[1] > 2 else proj[:, 0],
                     cmap='plasma', alpha=0.7, s=30, edgecolors='none')
    plt.colorbar(sc, ax=ax2)
    ax2.set_xlabel(f'PC1 ({explained[0]:.1f}%)'); ax2.set_ylabel(f'PC2 ({explained[1]:.1f}%)')
    ax2.set_title('PCA 2D Projection', fontsize=13, color=P['primary'], fontweight='bold')
    ax2.grid(True, alpha=0.2); fig.tight_layout()
    cum = np.cumsum(explained); n90 = int(np.searchsorted(cum, 90)) + 1
    insight = f"PC1+PC2 explain **{explained[:2].sum():.1f}%** of variance. **{n90} components** needed to capture 90% of information. Original {len(num_cols)} features reduced."
    return fig_to_b64(fig), insight

def gen_dendrogram(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    data = df[num_cols].dropna().head(50)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(data)
    Z = linkage(scaled, method='ward')
    fig, ax = plt.subplots(figsize=(12, 6))
    dendrogram(Z, ax=ax, color_threshold=0.7*max(Z[:,2]), above_threshold_color='#8ab4cc', leaf_rotation=90, leaf_font_size=7)
    ax.set_title('Hierarchical Clustering Dendrogram', fontsize=14, color=P['primary'], pad=15, fontweight='bold')
    ax.set_ylabel('Distance'); fig.tight_layout()
    insight = f"Ward linkage dendrogram on {min(50, len(df))} samples. **Longer branches = more dissimilar clusters**. Merge height indicates cluster distance. Cut horizontally to choose number of clusters."
    return fig_to_b64(fig), insight

def gen_scatter_plot(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    cols = num_cols[:min(4, len(num_cols))]
    n = len(cols) - 1
    fig, axes = plt.subplots(1, max(1,n), figsize=(5*max(1,n), 5))
    if n <= 1: axes = [axes]
    for i, ax in enumerate(axes[:n]):
        x, y = df[cols[0]].dropna(), df[cols[i+1]].dropna()
        mn = min(len(x), len(y))
        x, y = x.iloc[:mn], y.iloc[:mn]
        ax.scatter(x, y, c=P['primary'], alpha=0.5, s=20, edgecolors='none')
        if len(x) > 1:
            m, b = np.polyfit(x, y, 1)
            xl = np.linspace(x.min(), x.max(), 100)
            ax.plot(xl, m*xl+b, color=P['accent'], linewidth=2, alpha=0.8)
            r, pval = stats.pearsonr(x, y)
            ax.set_title(f'r={r:.3f} (p={pval:.3f})', fontsize=10, color=P['muted'])
        ax.set_xlabel(cols[0]); ax.set_ylabel(cols[i+1]); ax.grid(True, alpha=0.2)
    fig.suptitle('Scatter Analysis with Trend Lines', fontsize=14, color=P['primary'], fontweight='bold')
    fig.tight_layout()
    insight = f"Scatter plots with Pearson correlation coefficients. **r close to ±1** = strong linear relationship. Trend lines show direction of association."
    return fig_to_b64(fig), insight

def gen_distribution(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    cols = num_cols[:min(6, len(num_cols))]
    n = len(cols); ncols = min(3, n); nrows = (n+ncols-1)//ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5*ncols, 4*nrows))
    axes = np.array(axes).flatten() if n > 1 else [axes]
    for i, col in enumerate(cols):
        ax = axes[i]; d = df[col].dropna()
        ax.hist(d, bins=30, color=COLORS[i%len(COLORS)], alpha=0.75, edgecolor='none')
        ax.axvline(d.mean(), color='white', linestyle='--', linewidth=1.5, label=f'Mean: {d.mean():.2f}')
        ax.axvline(d.median(), color=P['accent'], linestyle=':', linewidth=1.5, label=f'Median: {d.median():.2f}')
        ax.set_title(f'{col} (skew={d.skew():.2f})', color=P['primary'], fontsize=10, fontweight='bold')
        ax.legend(facecolor=P['surface'], fontsize=7); ax.grid(True, alpha=0.2)
    for j in range(i+1, len(axes)): axes[j].set_visible(False)
    fig.suptitle('Distribution Analysis', fontsize=14, color=P['primary'], fontweight='bold', y=1.01)
    fig.tight_layout()
    skewed = [c for c in cols if abs(df[c].skew()) > 1]
    insight = f"Histograms with mean (dashed) and median (dotted) markers. **{len(skewed)} features are skewed**: {', '.join(skewed) if skewed else 'none'}. Consider log transformation for skewed features."
    return fig_to_b64(fig), insight

def gen_bar_chart(df, cat_cols, num_cols, theme='dark'):
    set_style(theme == 'light')
    cat, num = cat_cols[0], num_cols[0]
    grouped = df.groupby(cat)[num].mean().sort_values(ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.plasma(np.linspace(0.2, 0.9, len(grouped)))
    bars = ax.bar(range(len(grouped)), grouped.values, color=colors, edgecolor='none', alpha=0.9)
    ax.set_xticks(range(len(grouped))); ax.set_xticklabels(grouped.index, rotation=35, ha='right', fontsize=9)
    ax.set_ylabel(f'Mean {num}')
    ax.set_title(f'Mean {num} by {cat}', fontsize=14, color=P['primary'], fontweight='bold', pad=15)
    for bar, val in zip(bars, grouped.values):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01*grouped.max(), f'{val:.2f}', ha='center', va='bottom', fontsize=8, color='#8ab4cc')
    ax.grid(True, alpha=0.2, axis='y'); fig.tight_layout()
    top = grouped.index[0]; bottom = grouped.index[-1]
    insight = f"**{top}** has the highest mean {num} ({grouped.iloc[0]:.2f}). **{bottom}** has the lowest ({grouped.iloc[-1]:.2f}). Difference: {grouped.iloc[0]-grouped.iloc[-1]:.2f}."
    return fig_to_b64(fig), insight

def gen_box_plot(df, cat_cols, num_cols, theme='dark'):
    set_style(theme == 'light')
    cat, num = cat_cols[0], num_cols[0]
    groups = df[cat].value_counts().head(8).index
    data = [df[df[cat]==g][num].dropna().values for g in groups]
    fig, ax = plt.subplots(figsize=(10, 5))
    bp = ax.boxplot(data, patch_artist=True, notch=True, medianprops=dict(color=P['primary'], linewidth=2))
    for patch, color in zip(bp['boxes'], plt.cm.cool(np.linspace(0.2, 0.9, len(groups)))):
        patch.set_facecolor(color); patch.set_alpha(0.7)
    ax.set_xticklabels(groups, rotation=30, ha='right')
    ax.set_ylabel(num); ax.set_title(f'{num} Distribution by {cat}', fontsize=14, color=P['primary'], fontweight='bold', pad=15)
    ax.grid(True, alpha=0.2); fig.tight_layout()
    insight = f"Box plots show median, IQR, and outliers for **{num}** across {len(groups)} categories of **{cat}**. Notches indicate 95% confidence interval around the median."
    return fig_to_b64(fig), insight

def gen_violin_plot(df, cat_cols, num_cols, theme='dark'):
    set_style(theme == 'light')
    cat, num = cat_cols[0], num_cols[0]
    top_cats = df[cat].value_counts().head(6).index
    sub = df[df[cat].isin(top_cats)]
    fig, ax = plt.subplots(figsize=(10, 5))
    palette = {c: COLORS[i%len(COLORS)] for i, c in enumerate(top_cats)}
    sns.violinplot(data=sub, x=cat, y=num, palette=palette, ax=ax, inner='box', cut=0)
    ax.set_title(f'{num} Violin Plot by {cat}', fontsize=14, color=P['primary'], fontweight='bold', pad=15)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right')
    ax.grid(True, alpha=0.2); fig.tight_layout()
    insight = f"Violin plots reveal the **full distribution shape** of {num} across categories. Wider sections = more data points at that value. More informative than box plots for multimodal distributions."
    return fig_to_b64(fig), insight

def gen_confusion_matrix(df, cat_cols, num_cols, theme='dark'):
    set_style(theme == 'light')
    if not cat_cols or not num_cols: return None, None
    target = cat_cols[0]; features = num_cols[:min(5, len(num_cols))]
    X = df[features].dropna(); y = df.loc[X.index, target]
    le = LabelEncoder(); y_enc = le.fit_transform(y.astype(str))
    if len(set(y_enc)) < 2: return None, None
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y_enc, test_size=0.3, random_state=42)
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train); y_pred = clf.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    acc = (y_pred == y_test).mean()
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax, xticklabels=le.classes_, yticklabels=le.classes_)
    ax.set_title(f'Confusion Matrix — Accuracy: {acc:.1%}', fontsize=13, color=P['primary'], fontweight='bold')
    ax.set_xlabel('Predicted'); ax.set_ylabel('Actual'); fig.tight_layout()
    insight = f"Random Forest classifier trained on {len(features)} features to predict **{target}**. Overall accuracy: **{acc:.1%}**. Diagonal cells = correct predictions."
    return fig_to_b64(fig), insight

def gen_feature_importance(df, cat_cols, num_cols, theme='dark'):
    set_style(theme == 'light')
    if not cat_cols or len(num_cols) < 2: return None, None
    target = cat_cols[0]; features = num_cols[:min(8, len(num_cols))]
    X = df[features].dropna(); y = df.loc[X.index, target]
    le = LabelEncoder(); y_enc = le.fit_transform(y.astype(str))
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y_enc)
    imp = pd.Series(clf.feature_importances_, index=features).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(imp.index, imp.values, color=plt.cm.plasma(np.linspace(0.3, 0.9, len(imp))), edgecolor='none')
    ax.set_title(f'Feature Importance → {target}', fontsize=13, color=P['primary'], fontweight='bold')
    ax.set_xlabel('Importance Score'); ax.grid(True, alpha=0.2, axis='x'); fig.tight_layout()
    top_feat = imp.index[-1]; bottom_feat = imp.index[0]
    insight = f"**{top_feat}** is the most predictive feature for **{target}** (score: {imp.iloc[-1]:.3f}). **{bottom_feat}** contributes least ({imp.iloc[0]:.3f}). Remove low-importance features to simplify the model."
    return fig_to_b64(fig), insight

def gen_anomaly_detection(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    data = df[num_cols[:min(5, len(num_cols))]].dropna()
    scaler = StandardScaler(); scaled = scaler.fit_transform(data)
    iso = IsolationForest(contamination=0.1, random_state=42)
    labels = iso.fit_predict(scaled)
    n_anom = (labels == -1).sum()
    if scaled.shape[1] >= 2:
        pca = PCA(n_components=2); proj = pca.fit_transform(scaled)
        fig, ax = plt.subplots(figsize=(9, 6))
        normal = proj[labels == 1]; anom = proj[labels == -1]
        ax.scatter(normal[:, 0], normal[:, 1], c=P['primary'], s=30, alpha=0.6, label=f'Normal ({(labels==1).sum()})', edgecolors='none')
        ax.scatter(anom[:, 0], anom[:, 1], c=P['accent'], s=60, alpha=0.9, label=f'Anomaly ({n_anom})', marker='X', zorder=5)
        ax.set_xlabel('PC1'); ax.set_ylabel('PC2')
    else:
        fig, ax = plt.subplots(figsize=(9, 4))
        col = num_cols[0]; d = df[col].dropna()
        ax.scatter(range(len(d)), d, c=[P['accent'] if l==-1 else P['primary'] for l in labels], s=20, alpha=0.7)
        ax.set_xlabel('Index'); ax.set_ylabel(col)
    ax.set_title(f'Anomaly Detection (Isolation Forest)', fontsize=14, color=P['primary'], fontweight='bold', pad=15)
    ax.legend(facecolor=P['surface']); ax.grid(True, alpha=0.2); fig.tight_layout()
    pct = n_anom / len(data) * 100
    insight = f"**{n_anom} anomalies detected** ({pct:.1f}% of data) using Isolation Forest. Red ✕ marks = outlier data points that deviate significantly from the normal pattern. Investigate these rows in your original dataset."
    return fig_to_b64(fig), insight

def gen_time_series(df, num_cols, date_cols, theme='dark'):
    set_style(theme == 'light')
    date_col = date_cols[0]
    try:
        df[date_col] = pd.to_datetime(df[date_col])
        df_ts = df.sort_values(date_col)
    except:
        return None, None
    targets = num_cols[:min(3, len(num_cols))]
    fig, axes = plt.subplots(len(targets), 1, figsize=(12, 4*len(targets)), sharex=True)
    if len(targets) == 1: axes = [axes]
    for i, (col, ax) in enumerate(zip(targets, axes)):
        y = df_ts[col].dropna()
        x = df_ts.loc[y.index, date_col]
        ax.plot(x, y, color=COLORS[i], linewidth=1.5, alpha=0.85)
        # Rolling mean
        if len(y) > 7:
            roll = y.rolling(window=min(7, len(y)//5), center=True).mean()
            ax.plot(x, roll, color='white', linewidth=2, linestyle='--', alpha=0.6, label='7-period MA')
        ax.fill_between(x, y, alpha=0.1, color=COLORS[i])
        ax.set_ylabel(col); ax.grid(True, alpha=0.2); ax.legend(facecolor=P['surface'], fontsize=8)
        ax.set_title(col, color=P['primary'], fontsize=11, fontweight='bold')
    axes[-1].set_xlabel(date_col)
    fig.suptitle('Time Series Analysis', fontsize=14, color=P['primary'], fontweight='bold', y=1.01)
    fig.tight_layout()
    insight = f"Time series for **{len(targets)} numeric features** over **{date_col}**. Dashed white line = 7-period moving average to smooth short-term fluctuations. Trends and seasonality are visible."
    return fig_to_b64(fig), insight

def gen_bubble_chart(df, num_cols, theme='dark'):
    set_style(theme == 'light')
    if len(num_cols) < 3: return None, None
    x_col, y_col, size_col = num_cols[0], num_cols[1], num_cols[2]
    color_col = num_cols[3] if len(num_cols) > 3 else num_cols[2]
    d = df[[x_col, y_col, size_col, color_col]].dropna()
    sizes = ((d[size_col] - d[size_col].min()) / (d[size_col].max() - d[size_col].min() + 1e-9)) * 500 + 20
    fig, ax = plt.subplots(figsize=(9, 6))
    sc = ax.scatter(d[x_col], d[y_col], s=sizes, c=d[color_col], cmap='plasma', alpha=0.65, edgecolors='none')
    plt.colorbar(sc, ax=ax, label=color_col)
    ax.set_xlabel(x_col); ax.set_ylabel(y_col)
    ax.set_title(f'Bubble Chart — size={size_col}', fontsize=14, color=P['primary'], fontweight='bold', pad=15)
    ax.grid(True, alpha=0.2); fig.tight_layout()
    insight = f"Bubble chart with **{x_col}** vs **{y_col}**. Bubble size represents **{size_col}** and color represents **{color_col}**. Four variables visualized simultaneously."
    return fig_to_b64(fig), insight

# ── NLP Parser ────────────────────────────────────────────────────────────────
CHART_KEYWORDS = {
    'correlation': 'correlation_matrix', 'corr': 'correlation_matrix',
    'heatmap': 'heatmap', 'heat map': 'heatmap',
    'cluster': 'cluster_plot', 'kmeans': 'cluster_plot', 'k-means': 'cluster_plot',
    'pca': 'pca_plot', 'principal component': 'pca_plot', 'dimension': 'pca_plot',
    'dendrogram': 'dendrogram', 'hierarchical': 'dendrogram',
    'scatter': 'scatter_plot',
    'distribution': 'distribution_plot', 'histogram': 'distribution_plot', 'hist': 'distribution_plot',
    'bar': 'bar_chart',
    'box': 'box_plot', 'boxplot': 'box_plot', 'quartile': 'box_plot',
    'violin': 'violin_plot',
    'confusion': 'confusion_matrix', 'classification': 'confusion_matrix',
    'feature': 'feature_importance', 'importance': 'feature_importance',
    'anomaly': 'anomaly_detection', 'outlier': 'anomaly_detection',
    'time series': 'time_series', 'trend': 'time_series', 'timeline': 'time_series',
    'bubble': 'bubble_chart',
}

def parse_nl_command(command):
    lower = command.lower()
    for kw, ct in CHART_KEYWORDS.items():
        if kw in lower:
            return ct
    return None
