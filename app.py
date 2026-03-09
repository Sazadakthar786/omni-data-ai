import os, json, traceback, io, base64
from functools import wraps
from flask import (Flask, render_template, request, jsonify,
                   send_file, make_response, redirect, url_for)
import pandas as pd
import numpy as np

from database import (init_db, create_user, login_user, get_user_from_token,
                      logout_user, save_chart, get_user_charts, delete_chart,
                      save_dataset, get_user_dataset)
from charts import (load_data, clean_dataframe, analyze_data, get_top3_recommendations,
                    gen_correlation_matrix, gen_heatmap, gen_cluster_plot, gen_pca_plot,
                    gen_dendrogram, gen_scatter_plot, gen_distribution, gen_bar_chart,
                    gen_box_plot, gen_violin_plot, gen_confusion_matrix,
                    gen_feature_importance, gen_anomaly_detection, gen_time_series,
                    gen_bubble_chart, parse_nl_command)
from pdf_report import generate_pdf_report
from smart_engine import (detect_dataset_type, get_smart_charts,
                          generate_smart_insights, generate_fallback_charts)
from doc_intelligence import extract_text, analyze_text, decide_diagrams
from diagram_generators import (gen_flowchart, gen_er_diagram, gen_block_diagram,
                                gen_uml_usecase, gen_uml_sequence, gen_network_diagram, gen_mind_map)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# ── Init DB ───────────────────────────────────────────────────────────────────
init_db()

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 50 MB'}), 413

# ── Auth Decorator ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token')
        user = get_user_from_token(token)
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required', 'redirect': '/'}), 401
            return redirect('/')
        return f(*args, **kwargs, user=user)
    return decorated

def convert_np(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o) if not np.isnan(o) else None
    if isinstance(o, np.ndarray): return o.tolist()
    return str(o)

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    token = request.cookies.get('auth_token')
    user = get_user_from_token(token)
    if user:
        return redirect('/app')
    return render_template('auth.html')

@app.route('/app')
@login_required
def main_app(user):
    return render_template('index.html', user=user)

# ── Auth API ──────────────────────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.json
    username = d.get('username', '').strip()
    email = d.get('email', '').strip()
    password = d.get('password', '')
    if not username or not email or not password:
        return jsonify({'error': 'All fields required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    ok, msg = create_user(username, email, password)
    if not ok:
        return jsonify({'error': msg}), 400
    token, _ = login_user(username, password)
    resp = make_response(jsonify({'success': True, 'username': username}))
    resp.set_cookie('auth_token', token, httponly=True, max_age=7*24*3600)
    return resp

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.json
    identifier = d.get('identifier', '').strip()
    password = d.get('password', '')
    if not identifier or not password:
        return jsonify({'error': 'All fields required'}), 400
    token, msg = login_user(identifier, password)
    if not token:
        return jsonify({'error': msg}), 401
    user = get_user_from_token(token)
    resp = make_response(jsonify({'success': True, 'username': user['username']}))
    resp.set_cookie('auth_token', token, httponly=True, max_age=7*24*3600)
    return resp

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    token = request.cookies.get('auth_token')
    if token:
        logout_user(token)
    resp = make_response(jsonify({'success': True}))
    resp.delete_cookie('auth_token')
    return resp

@app.route('/api/auth/me', methods=['GET'])
@login_required
def me(user):
    return jsonify({'username': user['username'], 'email': user['email']})

# ── Data Upload ───────────────────────────────────────────────────────────────
@app.route('/api/upload', methods=['POST'])
@login_required
def upload(user):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    filename = file.filename
    if not filename or filename.strip() == '':
        return jsonify({'error': 'Empty filename'}), 400
    try:
        file_bytes = file.read()
        if len(file_bytes) == 0:
            return jsonify({'error': 'Uploaded file is empty'}), 400
        df = load_data(io.BytesIO(file_bytes), filename)
        if df is None or len(df) == 0:
            return jsonify({'error': 'No data found in file'}), 400
        df, clean_report = clean_dataframe(df)
        analysis = analyze_data(df)
        preview = df.head(8).to_dict(orient='records')
        preview = [{k: convert_np(v) for k, v in row.items()} for row in preview]
        save_dataset(user['id'], filename, analysis['n_rows'], analysis['n_cols'],
                     df.to_json(orient='records'))
        recs = get_top3_recommendations(df, analysis)
        dataset_type = detect_dataset_type(df)
        smart_charts = get_smart_charts(df, dataset_type)
        smart_insight = generate_smart_insights(df, dataset_type, filename)
        return jsonify({
            'success': True,
            'filename': filename,
            'rows': analysis['n_rows'],
            'cols': analysis['n_cols'],
            'num_cols': analysis['num_cols'],
            'cat_cols': analysis['cat_cols'],
            'date_cols': analysis['date_cols'],
            'suggestions': analysis['suggestions'],
            'recommendations': [{'type': r[0], 'reason': r[1]} for r in recs],
            'clean_report': clean_report,
            'preview': preview,
            'columns': list(df.columns),
            'dataset_type': dataset_type,
            'smart_charts': smart_charts,
            'smart_insight': smart_insight,
            'has_numeric': bool(len(analysis['num_cols']) > 0),
            'has_categorical': bool(len(analysis['cat_cols']) > 0),
        })
    except Exception as e:
        print(f"[UPLOAD ERROR] {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# ── Generate Chart ────────────────────────────────────────────────────────────
@app.route('/api/generate', methods=['POST'])
@login_required
def generate(user):
    data = request.json
    chart_type = data.get('chart_type')
    theme = data.get('theme', 'dark')
    save_to_db = data.get('save', False)
    try:
        ds = get_user_dataset(user['id'])
        if not ds:
            return jsonify({'error': 'No dataset loaded. Please upload data first.'}), 400
        df = pd.read_json(io.StringIO(ds['data_json']))
        analysis = analyze_data(df)
        num = analysis['num_cols']
        cat = analysis['cat_cols']
        date = analysis['date_cols']
        img, insight = None, ''
        if chart_type == 'correlation_matrix':
            if len(num) < 2:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'This chart requires at least two numeric columns.', 'suggestion': 'Add numeric columns or choose charts suited for categorical data.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_correlation_matrix(df, num, theme)
        elif chart_type == 'heatmap':
            if len(num) < 2:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Heatmap needs multiple numeric columns.', 'suggestion': 'Upload data with numeric features or use distribution and category charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_heatmap(df, num, theme)
        elif chart_type == 'cluster_plot':
            if len(num) < 2:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Clustering needs at least two numeric features.', 'suggestion': 'Provide numeric features or use category-based charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_cluster_plot(df, num, theme)
        elif chart_type == 'pca_plot':
            if len(num) < 3:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'PCA needs three or more numeric columns.', 'suggestion': 'Add numeric features or choose distribution/summary charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_pca_plot(df, num, theme)
        elif chart_type == 'dendrogram':
            if len(num) < 2:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Dendrogram needs multiple numeric columns.', 'suggestion': 'Add numeric data or use categorical distribution charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_dendrogram(df, num, theme)
        elif chart_type == 'scatter_plot':
            if len(num) < 2:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Scatter plot needs two numeric columns.', 'suggestion': 'Upload numeric data or use category/value counts charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_scatter_plot(df, num, theme)
        elif chart_type == 'distribution_plot':
            if not num:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Distribution analysis needs numeric columns.', 'suggestion': 'Provide numeric data or use text summary and category charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_distribution(df, num, theme)
        elif chart_type == 'bar_chart':
            if not cat or not num:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Bar chart needs categorical and numeric columns.', 'suggestion': 'Include one category and one numeric field or use value counts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_bar_chart(df, cat, num, theme)
        elif chart_type == 'box_plot':
            if not cat or not num:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Box plot needs categorical and numeric columns.', 'suggestion': 'Add categorical grouping or choose distribution charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_box_plot(df, cat, num, theme)
        elif chart_type == 'violin_plot':
            if not cat or not num:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Violin plot needs categorical and numeric columns.', 'suggestion': 'Include categorical grouping or try value counts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_violin_plot(df, cat, num, theme)
        elif chart_type == 'confusion_matrix':
            img, insight = gen_confusion_matrix(df, cat, num, theme)
            if img is None:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Confusion matrix needs a categorical target and two or more numeric features.', 'suggestion': 'Provide target labels and numeric features or use category distribution charts.', 'available_charts': get_smart_charts(df, dt)})
        elif chart_type == 'feature_importance':
            img, insight = gen_feature_importance(df, cat, num, theme)
            if img is None:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Feature importance needs labeled target and numeric features.', 'suggestion': 'Add target labels and numeric features or use summary charts.', 'available_charts': get_smart_charts(df, dt)})
        elif chart_type == 'anomaly_detection':
            if len(num) < 2:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Anomaly detection needs at least two numeric columns.', 'suggestion': 'Add numeric columns or use value counts and text summary.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_anomaly_detection(df, num, theme)
        elif chart_type == 'time_series':
            if not date:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Time series needs a date/time column.', 'suggestion': 'Include a date column or use categorical distribution charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_time_series(df, num, date, theme)
            if img is None:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Date parsing failed.', 'suggestion': 'Ensure date format is consistent or choose non-time charts.', 'available_charts': get_smart_charts(df, dt)})
        elif chart_type == 'bubble_chart':
            if len(num) < 3:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Bubble chart needs at least three numeric columns.', 'suggestion': 'Add numeric features or pick distribution/value counts charts.', 'available_charts': get_smart_charts(df, dt)})
            img, insight = gen_bubble_chart(df, num, theme)
            if img is None:
                dt = detect_dataset_type(df)
                return jsonify({'success': False, 'user_friendly_error': 'Not enough numeric columns for bubble chart.', 'suggestion': 'Provide three numeric columns or choose other charts.', 'available_charts': get_smart_charts(df, dt)})
        elif chart_type in ('category_distribution','category_pie','value_counts_grid','text_summary_image','range_parser_chart'):
            if chart_type == 'category_distribution':
                from smart_engine import gen_category_distribution
                img = gen_category_distribution(df)
                insight = ''
            elif chart_type == 'category_pie':
                from smart_engine import gen_category_pie
                img = gen_category_pie(df)
                insight = ''
            elif chart_type == 'value_counts_grid':
                from smart_engine import gen_value_counts_grid
                img = gen_value_counts_grid(df)
                insight = ''
            elif chart_type == 'text_summary_image':
                from smart_engine import gen_text_summary_image
                img = gen_text_summary_image(df, ds['filename'])
                insight = ''
            elif chart_type == 'range_parser_chart':
                from smart_engine import gen_range_parser_chart
                img = gen_range_parser_chart(df)
                insight = ''
        else:
            return jsonify({'error': f'Unknown chart type: {chart_type}'}), 400

        if save_to_db and img:
            save_chart(user['id'], chart_type, img, insight, ds['filename'])

        return jsonify({'success': True, 'image': img, 'insight': insight, 'chart_type': chart_type})
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# ── Smart Analyze ────────────────────────────────────────────────────────────
@app.route('/api/smart-analyze', methods=['POST'])
@login_required
def smart_analyze(user):
    ds = get_user_dataset(user['id'])
    if not ds:
        return jsonify({'error': 'No dataset loaded'}), 400
    df = pd.read_json(io.StringIO(ds['data_json']))
    dt = detect_dataset_type(df)
    charts = generate_fallback_charts(df, dt)
    insight = generate_smart_insights(df, dt, ds['filename'])
    return jsonify({'success': True, 'dataset_type': dt, 'charts': charts, 'insight': insight})

# ── NLP Query ─────────────────────────────────────────────────────────────────
@app.route('/api/nlp', methods=['POST'])
@login_required
def nlp_query(user):
    command = request.json.get('command', '').strip()
    if not command:
        return jsonify({'error': 'Empty command'}), 400
    chart_type = parse_nl_command(command)
    if not chart_type:
        return jsonify({
            'success': False,
            'message': "I couldn't identify a chart type. Try: 'show correlation matrix', 'create cluster plot', 'display anomaly detection', 'generate heatmap'."
        })
    # Forward to generate
    req_data = {'chart_type': chart_type, 'theme': request.json.get('theme', 'dark'), 'save': False}
    # Inline call
    ds = get_user_dataset(user['id'])
    if not ds:
        return jsonify({'error': 'No dataset loaded'}), 400
    import flask
    with app.test_request_context(json=req_data, method='POST'):
        # Direct function call instead
        pass
    # Just call generate directly
    original_json = request.json
    request._cached_json = (req_data, req_data)
    result = generate(user)
    return result

# ── Saved Charts ──────────────────────────────────────────────────────────────
@app.route('/api/charts/saved', methods=['GET'])
@login_required
def get_saved_charts(user):
    charts = get_user_charts(user['id'])
    return jsonify({'charts': charts})

@app.route('/api/charts/delete/<int:chart_id>', methods=['DELETE'])
@login_required
def delete_saved_chart(user, chart_id):
    delete_chart(chart_id, user['id'])
    return jsonify({'success': True})

# ── Statistics ────────────────────────────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats(user):
    ds = get_user_dataset(user['id'])
    if not ds:
        return jsonify({'error': 'No data loaded'}), 400
    df = pd.read_json(io.StringIO(ds['data_json']))
    stats = df.describe(include='all').round(3)
    return jsonify({'stats': stats.to_dict(), 'filename': ds['filename']})

# ── PDF Report ────────────────────────────────────────────────────────────────
@app.route('/api/report/pdf', methods=['POST'])
@login_required
def download_pdf(user):
    try:
        charts_data = request.json.get('charts', [])
        ds = get_user_dataset(user['id'])
        if not ds:
            return jsonify({'error': 'No dataset loaded'}), 400
        df = pd.read_json(io.StringIO(ds['data_json']))
        analysis = analyze_data(df)
        # Also include auto-generated charts if user sent none
        if not charts_data:
            recs = get_top3_recommendations(df, analysis)
            for rec_type, _ in recs[:3]:
                try:
                    req_data = {'chart_type': rec_type, 'theme': 'light', 'save': False}
                    request._cached_json = (req_data, req_data)
                    result = generate.__wrapped__(user)
                    rd = result.get_json()
                    if rd.get('success'):
                        charts_data.append({'chart_type': rec_type, 'image': rd['image'], 'insight': rd.get('insight','')})
                except:
                    pass

        stats = df.describe().round(3).to_dict()
        buf = generate_pdf_report(
            dataset_name=ds['filename'],
            rows=ds['rows'], cols=ds['cols'],
            num_cols=analysis['num_cols'], cat_cols=analysis['cat_cols'],
            clean_report=[], stats_dict=stats,
            charts=charts_data, username=user['username']
        )
        return send_file(buf, mimetype='application/pdf',
                         as_attachment=True,
                         download_name=f'omni-report-{ds["filename"].rsplit(".",1)[0]}.pdf')
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# ── SSE — Real-time Processing Log ───────────────────────────────────────────
@app.route('/api/process-stream', methods=['POST'])
@login_required
def process_stream(user):
    import time
    from flask import Response, stream_with_context
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file'}), 400

    filename = file.filename
    file_bytes = file.read()

    def generate_stream():
        import io
        steps = [
            ('Reading file format…', 15),
            ('Parsing data structure…', 25),
            ('Detecting column types…', 40),
            ('Imputing missing values…', 55),
            ('Normalizing column names…', 65),
            ('Running statistical analysis…', 75),
            ('Detecting anomaly patterns…', 83),
            ('Generating AI recommendations…', 92),
            ('Finalizing dataset…', 100),
        ]
        for msg, prog in steps:
            yield f"data: {json.dumps({'step': msg, 'progress': prog})}\n\n"
            time.sleep(0.35)

        try:
            df = load_data(io.BytesIO(file_bytes), filename)
            df, clean_report = clean_dataframe(df)
            analysis = analyze_data(df)
            preview = df.head(8).to_dict(orient='records')
            preview = [{k: convert_np(v) for k, v in row.items()} for row in preview]
            save_dataset(user['id'], filename, analysis['n_rows'], analysis['n_cols'],
                         df.to_json(orient='records'))
            recs = get_top3_recommendations(df, analysis)
            dataset_type = detect_dataset_type(df)
            smart_charts = get_smart_charts(df, dataset_type)
            smart_insight = generate_smart_insights(df, dataset_type, filename)
            result = {
                'done': True,
                'filename': filename,
                'rows': analysis['n_rows'],
                'cols': analysis['n_cols'],
                'num_cols': analysis['num_cols'],
                'cat_cols': analysis['cat_cols'],
                'date_cols': analysis['date_cols'],
                'suggestions': analysis['suggestions'],
                'recommendations': [{'type': r[0], 'reason': r[1]} for r in recs],
                'clean_report': clean_report,
                'preview': preview,
                'columns': list(df.columns),
                'dataset_type': dataset_type,
                'smart_charts': smart_charts,
                'smart_insight': smart_insight,
                'has_numeric': bool(len(analysis['num_cols']) > 0),
                'has_categorical': bool(len(analysis['cat_cols']) > 0),
            }
            yield f"data: {json.dumps(result)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate_stream()),
                    mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

# ── Document Intelligence ───────────────────────────────────────────────────
@app.route('/api/doc-analyze', methods=['POST'])
@login_required
def doc_analyze(user):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    filename = file.filename
    fb = file.read()
    try:
        text = extract_text(fb, filename)
        analysis = analyze_text(text)
        diagrams = decide_diagrams(analysis)
        out = []
        if 'Flowchart' in diagrams:
            img = gen_flowchart(analysis.get('actions', []), "Process Flow")
            out.append({'type': 'flowchart', 'title': 'Process Flow', 'image': img})
        if 'ER Diagram' in diagrams:
            img = gen_er_diagram(analysis.get('entities', []), analysis.get('relationships', []))
            out.append({'type': 'er_diagram', 'title': 'Entity-Relationship', 'image': img})
        if 'Block Diagram' in diagrams:
            comps = [e['name'] for e in analysis.get('entities', [])]
            conns = [(r[0], r[2], r[1]) for r in analysis.get('relationships', [])]
            img = gen_block_diagram(comps, conns)
            out.append({'type': 'block_diagram', 'title': 'System Architecture', 'image': img})
        if 'Use Case Diagram' in diagrams:
            actors = [e['name'] for e in analysis.get('entities', []) if e.get('type') == 'actor']
            use_cases = [a for a in analysis.get('actions', [])]
            img = gen_uml_usecase(actors, use_cases)
            out.append({'type': 'uml_usecase', 'title': 'Use Cases', 'image': img})
        if 'Sequence Diagram' in diagrams:
            objects = [e['name'] for e in analysis.get('entities', [])]
            interactions = analysis.get('relationships', [])
            img = gen_uml_sequence(objects, interactions)
            out.append({'type': 'uml_sequence', 'title': 'Sequence', 'image': img})
        if 'Network Diagram' in diagrams:
            nodes = [e['name'] for e in analysis.get('entities', [])]
            edges = [(r[0], r[2]) for r in analysis.get('relationships', [])]
            img = gen_network_diagram(nodes, edges)
            out.append({'type': 'network_diagram', 'title': 'Network', 'image': img})
        if 'Mind Map' in diagrams:
            branches = {}
            for e in analysis.get('entities', []):
                t = e.get('type', 'topic')
                branches.setdefault(t, []).append(e['name'])
            img = gen_mind_map('Document', branches)
            out.append({'type': 'mind_map', 'title': 'Mind Map', 'image': img})
        doc_type = analysis.get('doc_type', 'General Technical')
        insight = "Document analyzed; entities and relationships identified; diagrams generated."
        return jsonify({'success': True, 'doc_type': doc_type, 'entities': analysis.get('entities', []), 'relationships': analysis.get('relationships', []), 'diagrams_generated': len(out), 'diagrams': out, 'insight': insight})
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/api/doc-report', methods=['POST'])
@login_required
def doc_report(user):
    d = request.json or {}
    diagrams = d.get('diagrams', [])
    title = d.get('title', 'Illustrated Document')
    text = d.get('text', '')
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    c.setFillColorRGB(0, 0.96, 0.77)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, h - 72, title)
    c.setFillColorRGB(0.9, 0.96, 0.99)
    c.setFont("Helvetica", 10)
    c.drawString(72, h - 90, "AI Illustrated Report")
    c.showPage()
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, h - 72, "Executive Summary")
    c.setFont("Helvetica", 10)
    y = h - 96
    for line in text.split("\n"):
        c.drawString(72, y, line[:1000])
        y -= 14
        if y < 72:
            c.showPage()
            y = h - 72
    for dgm in diagrams:
        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, h - 72, dgm.get('title', dgm.get('type','Diagram')))
        img_b64 = dgm.get('image')
        if img_b64:
            img_bytes = base64.b64decode(img_b64)
            img = ImageReader(io.BytesIO(img_bytes))
            c.drawImage(img, 72, 120, width=w - 144, height=h - 240, preserveAspectRatio=True, mask='auto')
    c.showPage()
    c.setFont("Helvetica", 10)
    c.drawString(72, h - 72, "Index")
    y = h - 96
    for i, dgm in enumerate(diagrams, 1):
        c.drawString(72, y, f"{i}. {dgm.get('title', dgm.get('type','Diagram'))}")
        y -= 14
        if y < 72:
            c.showPage()
            y = h - 72
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='illustrated_document.pdf')

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
