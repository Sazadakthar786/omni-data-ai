/* ── Omni Data AI v2 — Frontend ── */

const State = {
  dataLoaded: false, theme: 'dark', currentImage: null, currentType: null,
  dashboard: [], dataset: null, dragIdx: null,
};

// ─── Toast ──────────────────────────────────────────────────────────────────
const toast = (msg, type='info', ms=3200) => {
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = `toast show ${type}`;
  setTimeout(() => el.classList.remove('show'), ms);
};

// ─── Panel Switch ────────────────────────────────────────────────────────────
function switchPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const panel = document.getElementById(`panel-${name}`);
  if (panel) panel.classList.add('active');
  const nav = document.querySelector(`[data-panel="${name}"]`);
  if (nav) nav.classList.add('active');
  const labels = { upload:'Data Ingestion', visualize:'Visualization Engine', nlp:'Ask AI', compare:'Compare Data', dashboard:'My Dashboard', stats:'Descriptive Statistics', docint:'Document Intelligence' };
  document.getElementById('breadcrumb').textContent = labels[name] || name;
  if (name === 'stats' && State.dataLoaded) loadStats();
  if (name === 'compare' && State.dataLoaded) loadSlot1Info();
}
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => { e.preventDefault(); switchPanel(item.dataset.panel); });
});

// ─── Sidebar Toggle ──────────────────────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const mainWrapper = document.getElementById('mainWrapper');
document.getElementById('sidebarToggle').addEventListener('click', () => {
  sidebar.classList.toggle('collapsed');
  mainWrapper.classList.toggle('expanded');
});

// ─── Theme Toggle ────────────────────────────────────────────────────────────
document.getElementById('themeToggle').addEventListener('click', () => {
  State.theme = State.theme === 'dark' ? 'light' : 'dark';
  document.body.setAttribute('data-theme', State.theme);
  toast(`${State.theme === 'dark' ? 'Dark' : 'Light'} theme active`, 'info', 1500);
});

// ─── Auth ────────────────────────────────────────────────────────────────────
async function doLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/';
}

// ─── Upload ────────────────────────────────────────
let isProcessing = false;
let isFileDialogOpen = false;

const zone      = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
// ── DOCUMENT INTELLIGENCE upload state (complete separation)
let isDocProcessing  = false;
let isDocDialogOpen  = false;
const docZone      = document.getElementById('docUploadZone');
const docFileInput = document.getElementById('docFileInput');

// When user clicks the zone, open file picker ONCE only
zone.addEventListener('click', (e) => {
  // If the click came FROM the fileInput itself, ignore it
  // This prevents the bubbling loop
  if (e.target === fileInput) return;
  
  // If already processing an upload, ignore
  if (isProcessing) return;
  
  // If file dialog is already open, ignore
  if (isFileDialogOpen) return;
  
  isFileDialogOpen = true;
  fileInput.click();
  
  // Reset the flag after a short delay
  // (handles case where user cancels the dialog)
  setTimeout(() => { isFileDialogOpen = false; }, 1000);
});

// Prevent clicks on the fileInput from bubbling to the zone
fileInput.addEventListener('click', (e) => {
  e.stopPropagation();
});
docFileInput?.addEventListener('click', (e) => {
  e.stopPropagation();
});

// Drag over
zone.addEventListener('dragover', (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (!isProcessing) zone.classList.add('over');
});

// Drag leave
zone.addEventListener('dragleave', (e) => {
  e.stopPropagation();
  zone.classList.remove('over');
});

// Drop
zone.addEventListener('drop', (e) => {
  e.preventDefault();
  e.stopPropagation();
  zone.classList.remove('over');
  if (isProcessing) return;
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

// File selected from picker — this is the KEY fix
fileInput.addEventListener('change', (e) => {
  // Reset dialog flag immediately
  isFileDialogOpen = false;
  
  const file = e.target.files[0];
  
  // If no file selected (user cancelled), just return
  if (!file) return;
  
  // If already processing, ignore
  if (isProcessing) return;
  
  // Start upload immediately with the selected file
  uploadFile(file);
  
  // Reset input value AFTER current call stack clears
  // Using 300ms delay prevents Safari re-trigger bug
  setTimeout(() => {
    fileInput.value = '';
    isFileDialogOpen = false;
  }, 300);
});

// ─── Doc Zone: click to open once only
docZone?.addEventListener('click', (e) => {
  if (e.target === docFileInput) return;
  if (isDocProcessing || isDocDialogOpen) return;
  isDocDialogOpen = true;
  docFileInput.click();
  setTimeout(() => { isDocDialogOpen = false; }, 1000);
});
// Doc Zone drag over/leave/drop
docZone?.addEventListener('dragover', (e) => {
  e.preventDefault(); e.stopPropagation();
  if (!isDocProcessing) docZone.classList.add('over');
});
docZone?.addEventListener('dragleave', (e) => {
  e.stopPropagation(); docZone.classList.remove('over');
});
docZone?.addEventListener('drop', (e) => {
  e.preventDefault(); e.stopPropagation(); docZone.classList.remove('over');
  if (isDocProcessing) return;
  const file = e.dataTransfer.files[0];
  if (file) analyzeDocument(file);
});
// Doc input change handler with Safari delayed reset
docFileInput?.addEventListener('change', (e) => {
  isDocDialogOpen = false;
  const file = e.target.files[0];
  if (!file || isDocProcessing) return;
  analyzeDocument(file);
  setTimeout(() => { docFileInput.value = ''; }, 300);
});

async function uploadFile(file) {
  // Hard guard — never run twice simultaneously
  if (isProcessing) return;
  isProcessing = true;

  // Validate file extension
  const allowed = ['csv','xlsx','xls','json','pdf','py','r'];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    toast('Unsupported file type: .' + ext, 'error', 4000);
    isProcessing = false;
    return;
  }

  const logEl    = document.getElementById('processLog');
  const logLines = document.getElementById('logLines');
  const fill     = document.getElementById('logFill');
  const pct      = document.getElementById('logPercent');

  logEl.style.display = 'block';
  logLines.innerHTML  = '';
  fill.style.width    = '0%';
  pct.textContent     = '0%';

  const steps = [
    'Reading file format…',
    'Parsing data structure…',
    'Detecting column types…',
    'Imputing missing values…',
    'Running statistical analysis…',
    'Generating AI recommendations…',
    'Finalizing dataset…',
  ];

  const addLine = (msg, progress) => {
    document.querySelectorAll('.log-line').forEach(l => {
      l.classList.remove('current');
      l.classList.add('done');
    });
    const div = document.createElement('div');
    div.className = 'log-line current';
    div.textContent = msg;
    logLines.appendChild(div);
    logLines.scrollTop = logLines.scrollHeight;
    fill.style.width = progress + '%';
    pct.textContent  = progress + '%';
  };

  let si = 0;
  const interval = setInterval(() => {
    if (si >= steps.length - 1) return;
    addLine(steps[si], Math.round((si + 1) / steps.length * 85));
    si++;
  }, 400);

  try {
    const fd = new FormData();
    fd.append('file', file);

    const res  = await fetch('/api/upload', {
      method: 'POST',
      body: fd
    });
    const text = await res.text();
    clearInterval(interval);

    let data;
    try {
      data = JSON.parse(text);
    } catch (parseErr) {
      console.error('Server returned non-JSON:', text.slice(0,500));
      toast('Server error — check terminal', 'error', 6000);
      logEl.style.display = 'none';
      return;
    }

    if (!res.ok || data.error) {
      const errMsg = data.error || ('HTTP ' + res.status);
      toast('Upload error: ' + errMsg, 'error', 6000);
      addLine('✗ ' + errMsg, 0);
      if (data.trace) console.error(data.trace);
      return;
    }

    addLine('✓ Dataset ready!', 100);
    handleUploadResult(data);

  } catch (e) {
    clearInterval(interval);
    console.error('Upload exception:', e);
    toast('Upload failed: ' + e.message, 'error', 5000);
  } finally {
    // ALWAYS reset processing flag whether success or error
    isProcessing = false;
  }
}

/* removed regularUpload: guarded single-path upload handles all cases */

function handleUploadResult(data) {
  State.dataLoaded = true;
  State.dataset = data;

  // Status pill
  document.querySelector('.pill-dot').className = 'pill-dot active';
  document.getElementById('pillText').textContent = `${data.filename} · ${data.rows.toLocaleString()} rows`;
  document.getElementById('downloadBtn').disabled = false;
  document.getElementById('pdfBtn').disabled = false;

  // Info cards
  document.getElementById('iRows').textContent = data.rows.toLocaleString();
  document.getElementById('iCols').textContent = data.cols;
  document.getElementById('iNum').textContent = data.num_cols.length;
  document.getElementById('iCat').textContent = data.cat_cols.length;
  document.getElementById('infoGrid').style.display = 'grid';

  // AI Recommendations
  if (data.recommendations && data.recommendations.length) {
    const cards = document.getElementById('recCards');
    cards.innerHTML = '';
    data.recommendations.forEach(rec => {
      const card = document.createElement('div');
      card.className = 'rec-card';
      card.innerHTML = `<div class="rec-badge">AI PICK</div><div class="rec-card-type">${rec.type.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</div><div class="rec-card-reason">${rec.reason}</div>`;
      card.onclick = () => { switchPanel('visualize'); setTimeout(() => generateChart(rec.type), 200); };
      cards.appendChild(card);
    });
    document.getElementById('recBox').style.display = 'block';
  }

  // Clean report
  if (data.clean_report) {
    const ul = document.getElementById('cleanList'); ul.innerHTML = '';
    data.clean_report.forEach(item => { const li = document.createElement('li'); li.textContent = item; ul.appendChild(li); });
    document.getElementById('cleanBox').style.display = 'block';
  }

  if (data.smart_insight) {
    const box = document.getElementById('smartInsightBox');
    const badge = document.getElementById('datasetTypeBadge');
    box.style.display = 'block';
    badge.textContent = (data.dataset_type || '').replace(/_/g,' ').toUpperCase();
    const map = {reference_table:'ref',numeric_rich:'num',categorical_rich:'cat',time_series:'ts'};
    badge.className = 'dataset-type-badge ' + (map[data.dataset_type] || '');
    document.getElementById('smartInsightTxt').textContent = data.smart_insight;
  }

  // Preview table
  buildTable(data.preview, data.columns);
  document.getElementById('tableWrap').style.display = 'block';
  document.getElementById('emptyViz').style.display = 'none';

  // Column chips for insights
  buildColChips(data.num_cols, data.cat_cols);

  if (Array.isArray(data.smart_charts) && data.smart_charts.length) {
    const first = data.smart_charts[0];
    switchPanel('visualize');
    setTimeout(() => generateChart(first), 200);
  }

  if (data.dataset_type === 'reference_table' || data.dataset_type === 'categorical_rich') {
    fetch('/api/smart-analyze', { method: 'POST' })
      .then(r => r.json())
      .then(sd => {
        if (!sd.success) return;
        const box = document.getElementById('autoVizBox');
        const grid = document.getElementById('autoVizGrid');
        if (box && grid) {
          box.style.display = 'block';
          grid.innerHTML = '';
          sd.charts.forEach(ch => {
            const card = document.createElement('div');
            card.className = 'diagram-card';
            const hdr = document.createElement('div'); hdr.className = 'hdr'; hdr.textContent = ch.title || ch.type;
            const img = document.createElement('img'); img.src = 'data:image/png;base64,' + ch.image;
            const txt = document.createElement('div'); txt.className = 'txt'; txt.textContent = 'AI-selected chart for your dataset type.';
            card.appendChild(hdr); card.appendChild(img); card.appendChild(txt);
            grid.appendChild(card);
          });
        }
      }).catch(()=>{});
  }

  toast(`✓ ${data.filename} loaded — ${data.rows.toLocaleString()} rows, ${data.cols} columns`, 'success');
}

function buildTable(rows, cols) {
  const table = document.getElementById('previewTable');
  table.innerHTML = '';
  const thead = document.createElement('thead');
  const tr = document.createElement('tr');
  cols.forEach(c => {
    const th = document.createElement('th');
    th.textContent = c;
    th.onclick = () => showColModal(c);
    tr.appendChild(th);
  });
  thead.appendChild(tr); table.appendChild(thead);
  const tbody = document.createElement('tbody');
  rows.forEach(row => {
    const tr = document.createElement('tr');
    cols.forEach(c => { const td = document.createElement('td'); const v = row[c]; td.textContent = v === null || v === undefined ? '—' : v; tr.appendChild(td); });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
}

// ─── Column-level Insights ────────────────────────────────────────────────────
function buildColChips(numCols, catCols) {
  const chips = document.getElementById('colChips');
  if (!chips) return;
  chips.innerHTML = '';
  [...numCols, ...catCols].forEach(col => {
    const btn = document.createElement('button');
    btn.className = 'col-chip'; btn.textContent = col;
    btn.onclick = () => showColModal(col);
    chips.appendChild(btn);
  });
  const ci = document.getElementById('colInsights');
  if (ci) ci.style.display = 'block';
}

async function showColModal(col) {
  document.getElementById('modalTitle').textContent = `COLUMN: ${col.toUpperCase()}`;
  document.getElementById('modalOverlay').classList.add('open');
  const body = document.getElementById('modalBody');
  body.innerHTML = '<div style="color:var(--muted);font-family:var(--font-mono);font-size:11px;padding:10px">Analyzing…</div>';
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (data.error) { body.innerHTML = `<p style="color:var(--accent)">${data.error}</p>`; return; }
    const stats = data.stats[col];
    if (!stats) { body.innerHTML = '<p style="color:var(--muted)">No stats available for this column</p>'; return; }
    const metrics = Object.entries(stats).filter(([k,v]) => v !== null && v !== undefined);
    body.innerHTML = metrics.map(([k,v]) => `<div class="modal-stat"><span class="modal-stat-k">${k}</span><span class="modal-stat-v">${typeof v === 'number' ? v.toFixed(4) : v}</span></div>`).join('');
    // AI insight
    const mean = stats['mean']; const std = stats['std']; const skew = stats['skew'];
    let insight = '';
    if (mean !== undefined) insight += `Mean value is <strong>${typeof mean === 'number' ? mean.toFixed(3) : mean}</strong>. `;
    if (std !== undefined && mean !== undefined && mean !== 0) {
      const cv = (std / Math.abs(mean) * 100).toFixed(1);
      insight += `Coefficient of variation: ${cv}% (${cv > 30 ? 'high variability' : 'moderate variability'}). `;
    }
    const countNull = Object.values(data.stats).filter(s => s[col] === null).length;
    if (insight) body.innerHTML += `<div class="modal-insight">${insight}</div>`;
  } catch {}
}

function closeModal() { document.getElementById('modalOverlay').classList.remove('open'); }

// ─── Chart Generation ─────────────────────────────────────────────────────────
document.querySelectorAll('.chart-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (!State.dataLoaded) { toast('Upload data first', 'error'); return; }
    document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('sel'));
    btn.classList.add('sel');
    generateChart(btn.dataset.type);
  });
});

async function generateChart(type) {
  const out = document.getElementById('chartOut');
  const spin = document.getElementById('chartSpin');
  const img = document.getElementById('chartImg');
  const ib = document.getElementById('insightBlock');
  out.style.display = 'block';
  spin.style.display = 'flex'; img.style.display = 'none'; ib.style.display = 'none';
  const labels = {correlation_matrix:'CORRELATION MATRIX',heatmap:'DATA HEATMAP',cluster_plot:'K-MEANS CLUSTER PLOT',pca_plot:'PCA ANALYSIS',dendrogram:'DENDROGRAM',scatter_plot:'SCATTER ANALYSIS',distribution_plot:'DISTRIBUTION ANALYSIS',bar_chart:'BAR CHART',box_plot:'BOX PLOT',violin_plot:'VIOLIN PLOT',anomaly_detection:'ANOMALY DETECTION',time_series:'TIME SERIES ANALYSIS',bubble_chart:'BUBBLE CHART',confusion_matrix:'CONFUSION MATRIX',feature_importance:'FEATURE IMPORTANCE',category_distribution:'CATEGORY DISTRIBUTION',category_pie:'CATEGORY PIE',value_counts_grid:'VALUE COUNTS GRID',text_summary_image:'SUMMARY IMAGE',range_parser_chart:'REFERENCE RANGE'};
  document.getElementById('chartTitle').textContent = labels[type] || type.toUpperCase().replace(/_/g,' ');
  try {
    const res = await fetch('/api/generate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ chart_type: type, theme: State.theme, save: false }) });
    const data = await res.json();
    spin.style.display = 'none';
    if (data.success === false && data.user_friendly_error) {
      const panel = document.getElementById('errorSuggestPanel');
      const msg = document.getElementById('errorSuggestMsg');
      const tip = document.getElementById('errorSuggestTip');
      const btns = document.getElementById('errorSuggestBtns');
      panel.style.display = 'block';
      msg.textContent = data.user_friendly_error;
      tip.textContent = data.suggestion || '';
      btns.innerHTML = '';
      (data.available_charts || []).slice(0,6).forEach(ct => {
        const b = document.createElement('button');
        b.className = 'available-chart-btn';
        b.textContent = (labels[ct] || ct.replace(/_/g,' ').toUpperCase());
        b.onclick = () => generateChart(ct);
        btns.appendChild(b);
      });
      return;
    }
    if (data.error) { toast('Error: ' + data.error, 'error', 5000); out.style.display = 'none'; return; }
    document.getElementById('errorSuggestPanel').style.display = 'none';
    img.src = 'data:image/png;base64,' + data.image; img.style.display = 'block';
    State.currentImage = data.image; State.currentType = type;
    if (data.insight) {
      document.getElementById('insightTxt').innerHTML = data.insight.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      ib.style.display = 'block';
    }
    document.getElementById('downloadBtn').disabled = false;
  } catch (e) { spin.style.display = 'none'; toast('Error: ' + e.message, 'error'); }
}

document.getElementById('downloadBtn').addEventListener('click', () => {
  if (!State.currentImage) return;
  const a = document.createElement('a');
  a.href = 'data:image/png;base64,' + State.currentImage;
  a.download = `omni-${State.currentType}-${Date.now()}.png`;
  a.click(); toast('Chart downloaded', 'success');
});
document.getElementById('dlChartBtn')?.addEventListener('click', () => {
  if (!State.currentImage) return;
  const a = document.createElement('a');
  a.href = 'data:image/png;base64,' + State.currentImage;
  a.download = `omni-${State.currentType}-${Date.now()}.png`;
  a.click();
});

// ─── Dashboard ───────────────────────────────────────────────────────────────
document.getElementById('addDashBtn')?.addEventListener('click', () => {
  if (!State.currentImage) { toast('Generate a chart first', 'error'); return; }
  addToDash(State.currentType, State.currentImage);
});

function addToDash(type, imgData) {
  const id = Date.now();
  State.dashboard.push({ id, type, imgData });
  renderDash();
  toast('Added to dashboard', 'success');
}

function renderDash() {
  const grid = document.getElementById('dashGrid');
  const empty = document.getElementById('dashEmpty');
  const tag = document.getElementById('dashTag');
  const actions = document.getElementById('dashActions');
  tag.textContent = State.dashboard.length + ' CHARTS';
  if (!State.dashboard.length) {
    grid.innerHTML = ''; grid.appendChild(empty); empty.style.display = 'flex';
    actions.style.display = 'none'; return;
  }
  empty.style.display = 'none';
  actions.style.display = 'flex';
  // Re-render
  grid.innerHTML = '';
  State.dashboard.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = 'dash-item'; div.draggable = true;
    div.dataset.idx = idx;
    div.innerHTML = `<div class="dash-hdr"><span>${item.type.replace(/_/g,' ').toUpperCase()}</span><button class="dash-rm" onclick="removeFromDash(${item.id})">✕</button></div><img src="data:image/png;base64,${item.imgData}" alt="${item.type}">`;
    div.addEventListener('dragstart', e => { State.dragIdx = idx; div.classList.add('dragging'); });
    div.addEventListener('dragend', () => { State.dragIdx = null; div.classList.remove('dragging'); });
    div.addEventListener('dragover', e => e.preventDefault());
    div.addEventListener('drop', e => {
      e.preventDefault();
      if (State.dragIdx === null || State.dragIdx === idx) return;
      const moved = State.dashboard.splice(State.dragIdx, 1)[0];
      State.dashboard.splice(idx, 0, moved);
      renderDash();
    });
    grid.appendChild(div);
  });
  grid.appendChild(empty);
}

function removeFromDash(id) {
  State.dashboard = State.dashboard.filter(i => i.id !== id);
  renderDash(); toast('Removed from dashboard', 'info');
}

function clearDashboard() {
  State.dashboard = []; renderDash(); toast('Dashboard cleared', 'info');
}

function allowDrop(e) { e.preventDefault(); }
function dropChart(e) { e.preventDefault(); }

// ─── PDF Report ───────────────────────────────────────────────────────────────
async function downloadPDF() {
  if (!State.dataLoaded) { toast('Upload data first', 'error'); return; }
  toast('Generating PDF report…', 'info', 4000);
  try {
    const charts = State.dashboard.map(item => ({ chart_type: item.type, image: item.imgData, insight: '' }));
    // Also add current chart if any
    if (State.currentImage && !charts.find(c => c.chart_type === State.currentType)) {
      charts.unshift({ chart_type: State.currentType, image: State.currentImage, insight: '' });
    }
    const res = await fetch('/api/report/pdf', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ charts })
    });
    if (!res.ok) { const e = await res.json(); toast('PDF error: ' + e.error, 'error'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `omni-report-${Date.now()}.pdf`; a.click();
    URL.revokeObjectURL(url);
    toast('✓ PDF Report downloaded!', 'success');
  } catch (e) { toast('PDF generation failed: ' + e.message, 'error'); }
}

// ─── NLP ─────────────────────────────────────────────────────────────────────
function setCmd(cmd) { document.getElementById('nlpInput').value = cmd; document.getElementById('nlpInput').focus(); }

async function submitNLP() {
  const cmd = document.getElementById('nlpInput').value.trim();
  if (!cmd) return;
  if (!State.dataLoaded) { toast('Upload data first', 'error'); return; }
  const out = document.getElementById('nlpOut');
  const msg = document.getElementById('nlpMsg');
  const nlpImg = document.getElementById('nlpImg');
  const nlpIB = document.getElementById('nlpInsightBlock');
  const nlpType = document.getElementById('nlpType');
  out.style.display = 'block'; nlpImg.style.display = 'none'; nlpIB.style.display = 'none';
  msg.textContent = 'Processing your request…'; nlpType.textContent = '';

  // Parse locally
  const map = {correlation:'correlation_matrix',corr:'correlation_matrix',heatmap:'heatmap','heat map':'heatmap',cluster:'cluster_plot',kmeans:'cluster_plot',pca:'pca_plot',principal:'pca_plot',dendrogram:'dendrogram',hierarchical:'dendrogram',scatter:'scatter_plot',distribution:'distribution_plot',histogram:'distribution_plot',bar:'bar_chart',box:'box_plot',violin:'violin_plot',anomaly:'anomaly_detection',outlier:'anomaly_detection','time series':'time_series',trend:'time_series',bubble:'bubble_chart',confusion:'confusion_matrix',classification:'confusion_matrix',feature:'feature_importance',importance:'feature_importance'};
  const lower = cmd.toLowerCase();
  let chartType = null;
  for (const [kw, ct] of Object.entries(map)) { if (lower.includes(kw)) { chartType = ct; break; } }
  if (!chartType) {
    msg.textContent = "I couldn't identify a chart type. Try: 'show correlation matrix', 'detect anomalies', 'create cluster plot', 'show time series'."; return;
  }
  try {
    const res = await fetch('/api/generate', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ chart_type: chartType, theme: State.theme, save: false })
    });
    const data = await res.json();
    if (data.error) { msg.textContent = 'Error: ' + data.error; return; }
    nlpType.textContent = chartType.replace(/_/g,' ').toUpperCase();
    msg.textContent = 'Here is your ' + chartType.replace(/_/g,' ') + ':';
    nlpImg.src = 'data:image/png;base64,' + data.image; nlpImg.style.display = 'block';
    State.currentImage = data.image; State.currentType = chartType;
    if (data.insight) {
      document.getElementById('nlpInsightTxt').innerHTML = data.insight.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
      nlpIB.style.display = 'block';
    }
  } catch (e) { msg.textContent = 'Error: ' + e.message; }
}

document.getElementById('nlpGo').addEventListener('click', submitNLP);
document.getElementById('nlpInput').addEventListener('keydown', e => { if (e.key === 'Enter') submitNLP(); });

// ─── Statistics ───────────────────────────────────────────────────────────────
async function loadStats() {
  const wrap = document.getElementById('statsWrap');
  wrap.innerHTML = '<div style="color:var(--muted);font-family:var(--font-mono);font-size:12px;padding:16px">Loading…</div>';
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (data.error) { wrap.innerHTML = `<div class="empty-state"><p>${data.error}</p></div>`; return; }
    const stats = data.stats; const cols = Object.keys(stats);
    const grid = document.createElement('div'); grid.className = 'stats-grid';
    cols.forEach(col => {
      const card = document.createElement('div'); card.className = 'stat-card';
      card.onclick = () => showColModal(col);
      card.innerHTML = `<div class="stat-col">${col} <span style="font-size:8px;color:var(--muted);font-family:var(--font-mono)">(click for analysis)</span></div>`;
      Object.entries(stats[col] || {}).forEach(([k,v]) => {
        if (v === null) return;
        const row = document.createElement('div'); row.className = 'stat-row';
        row.innerHTML = `<span class="stat-k">${k}</span><span class="stat-v">${typeof v === 'number' ? v.toFixed(3) : v}</span>`;
        card.appendChild(row);
      });
      grid.appendChild(card);
    });
    wrap.innerHTML = ''; wrap.appendChild(grid);
  } catch (e) { wrap.innerHTML = `<div class="empty-state"><p style="color:var(--accent)">Error loading stats</p></div>`; }
}

// ─── Compare ──────────────────────────────────────────────────────────────────
function loadSlot1Info() {
  if (!State.dataset) return;
  const s = State.dataset;
  document.getElementById('slot1Status').textContent = 'Loaded';
  document.getElementById('slot1Content').innerHTML = `<div style="font-size:13px;color:var(--text)">${s.filename}</div><div style="font-size:12px;color:var(--muted)">${s.rows} rows · ${s.cols} columns</div>`;
}

document.getElementById('compareFile')?.addEventListener('change', async e => {
  const file = e.target.files[0]; if (!file) return;
  const fd = new FormData(); fd.append('file', file);
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) { toast(data.error, 'error'); return; }
    document.getElementById('slot2Status').textContent = 'Loaded';
    document.getElementById('slot2Content').innerHTML = `<div style="font-size:13px;color:var(--text)">${data.filename}</div><div style="font-size:12px;color:var(--muted)">${data.rows} rows · ${data.cols} columns</div>`;
    const results = document.getElementById('compareResults');
    results.style.display = 'block';
    results.innerHTML = `<div class="clean-box" style="display:block"><div class="clean-hdr">DATASET COMPARISON SUMMARY</div>
    <ul><li>Dataset A: ${State.dataset?.filename || 'Primary'} — ${State.dataset?.rows || 0} rows, ${State.dataset?.cols || 0} cols</li>
    <li>Dataset B: ${data.filename} — ${data.rows} rows, ${data.cols} cols</li>
    <li>Row difference: ${Math.abs((State.dataset?.rows || 0) - data.rows)}</li>
    <li>Shared numeric columns: ${(State.dataset?.num_cols || []).filter(c => data.num_cols.includes(c)).length}</li>
    </ul></div>`;
    toast('Comparison loaded', 'success');
  } catch (e) { toast('Error: ' + e.message, 'error'); }
  finally { setTimeout(() => { e.target.value = ''; }, 300); }
});

// ─── Document Intelligence ───────────────────────────────────────────────────
async function analyzeDocument(file) {
  if (isDocProcessing) return;
  isDocProcessing = true;
  const allowed = ['pdf','docx','txt'];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    toast('Unsupported document type: .' + ext, 'error', 4000);
    isDocProcessing = false;
    return;
  }
  const log = document.getElementById('docProcessLog');
  const lines = document.getElementById('docProcessLines');
  const fill = document.getElementById('docProcessFill');
  const pct = document.getElementById('docProcessPercent');
  log.style.display = 'block'; lines.innerHTML = ''; fill.style.width = '0%'; pct.textContent = '0%';
  const steps = ['Extracting text from document...','Analyzing entities and relationships...','Detecting action sequences...','Classifying document type...','Deciding diagram requirements...','Generating diagrams...','Assembling illustrated PDF...'];
  let si = 0;
  const interval = setInterval(() => {
    if (si >= steps.length - 1) return;
    document.querySelectorAll('#docProcessLog .log-line').forEach(l => { l.classList.remove('current'); l.classList.add('done'); });
    const div = document.createElement('div'); div.className = 'log-line current'; div.textContent = steps[si];
    lines.appendChild(div); lines.scrollTop = lines.scrollHeight;
    const p = Math.round((si+1) / steps.length * 85);
    fill.style.width = p + '%'; pct.textContent = p + '%';
    si++;
  }, 300);
  try {
    const fd = new FormData(); fd.append('file', file);
    const res = await fetch('/api/doc-analyze', { method: 'POST', body: fd });
    let data = null; try { data = await res.json(); } catch {}
    clearInterval(interval); fill.style.width = '100%'; pct.textContent = '100%';
    if (!res.ok || !data?.success) { toast('Error: ' + ((data && data.error) || res.statusText || 'Document analysis failed'), 'error'); return; }
    const results = document.getElementById('docResultsSection'); results.style.display = 'block';
    const badge = document.getElementById('docTypeBadge'); badge.textContent = data.doc_type;
    const chips = document.getElementById('entityChips'); chips.innerHTML = '';
    (data.entities || []).forEach(e => { const b = document.createElement('span'); b.className = 'entity-chip'; b.textContent = e.name; chips.appendChild(b); });
    const grid = document.getElementById('diagramGrid'); grid.innerHTML = '';
    (data.diagrams || []).forEach(d => {
      const card = document.createElement('div'); card.className = 'diagram-card';
      const hdr = document.createElement('div'); hdr.className = 'hdr'; hdr.textContent = d.title;
      const img = document.createElement('img'); img.src = 'data:image/png;base64,' + d.image;
      const txt = document.createElement('div'); txt.className = 'txt'; txt.textContent = 'Generated automatically from document analysis.';
      card.appendChild(hdr); card.appendChild(img); card.appendChild(txt);
      grid.appendChild(card);
    });
    const btn = document.getElementById('downloadDocPdfBtn'); btn.style.display = 'block';
    btn.onclick = async () => {
      const res2 = await fetch('/api/doc-report', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ title: file.name, text: '', diagrams: data.diagrams }) });
      const blob = await res2.blob(); const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `illustrated-${Date.now()}.pdf`; a.click(); URL.revokeObjectURL(url);
      toast('✓ Illustrated PDF downloaded!', 'success');
    };
  } catch (e) { clearInterval(interval); toast('Error: ' + e.message, 'error'); }
  finally { isDocProcessing = false; }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.getElementById('emptyViz').style.display = 'flex';
document.getElementById('chartOut').style.display = 'none';
renderDash();
