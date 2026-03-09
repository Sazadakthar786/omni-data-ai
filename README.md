cat > README.md << 'EOF'
# Omni Data AI 🤖

> Intelligent Multi-Format Data Visualization Platform

Upload any data file and instantly get AI-powered charts, machine learning visualizations, anomaly detection, and professional PDF reports — no coding required.

---

## What it does

- Upload CSV, Excel, JSON, PDF, Python, R files
- Automatically generates 15 types of charts and ML visualizations
- Detects anomalies, clusters, and patterns in your data
- Ask in plain English — "show me anomalies" → chart appears
- Document Intelligence — upload any English document → auto-generates flowcharts, ER diagrams, UML diagrams
- Personal dashboard with drag-to-reorder charts
- One-click PDF report export with all charts and AI insights
- Works 100% offline — no API keys or internet needed

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python + Flask | Web server and API routes |
| Pandas + NumPy | Data processing and cleaning |
| Matplotlib + Seaborn | Chart and visualization generation |
| Scikit-learn | ML — clustering, PCA, anomaly detection, feature importance |
| SQLite | Database for users, sessions, and datasets |
| ReportLab | PDF report generation |
| NLTK + NetworkX | Document intelligence and diagram generation |

---

## How to Run

### 1. Clone the repository
```bash
git clone https://github.com/Sazadakthar786/omni-data-ai.git
cd omni-data-ai
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python3 app.py
```

### 5. Open in browser
```
http://127.0.0.1:5000
```

---

## Features

### 15 Chart Types
- Correlation Matrix, Heatmap, Cluster Plot, PCA Analysis
- Scatter Plot, Distribution, Bar Chart, Box Plot, Violin Plot
- Anomaly Detection, Time Series, Bubble Chart
- Confusion Matrix, Feature Importance, Dendrogram

### Smart Data Engine
- Automatically detects dataset type
- Never crashes on unusual data
- Shows friendly suggestions instead of raw errors
- Works with medical data, reference tables, catalogs

### Document Intelligence
- Upload PDF, DOCX, or TXT documents
- AI reads and understands the text
- Auto-generates technical diagrams
- Downloads as illustrated PDF

### Security
- Secure login and registration
- Passwords hashed with SHA-256 + salt
- Session tokens for authentication
- Each user has private data and dashboard

---

## Project Structure
```
omni-data-ai/
├── app.py                 # Flask server and all API routes
├── charts.py              # All 15 chart generator functions
├── database.py            # SQLite database operations
├── pdf_report.py          # PDF report builder
├── smart_engine.py        # Smart dataset type handler
├── doc_intelligence.py    # Document NLP engine
├── diagram_generators.py  # Technical diagram generators
├── requirements.txt       # All Python dependencies
├── templates/
│   ├── index.html         # Main application page
│   └── auth.html          # Login and register page
└── static/
    ├── css/style.css      # All styling and themes
    └── js/app.js          # All frontend logic
```