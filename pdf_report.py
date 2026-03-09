import io, base64, os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                  TableStyle, Image, PageBreak, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Custom Colors ────────────────────────────────────────────────────────────
TEAL = colors.HexColor('#00f5c4')
PURPLE = colors.HexColor('#7b61ff')
DARK = colors.HexColor('#060b18')
SURFACE = colors.HexColor('#0d1628')
LIGHT_BG = colors.HexColor('#f0f9ff')
ACCENT = colors.HexColor('#ff6b6b')
TEXT_DARK = colors.HexColor('#1e293b')
MUTED = colors.HexColor('#64748b')

def make_styles():
    styles = getSampleStyleSheet()
    custom = {
        'cover_title': ParagraphStyle('cover_title', fontSize=32, textColor=TEAL,
                                       fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=8),
        'cover_sub': ParagraphStyle('cover_sub', fontSize=14, textColor=PURPLE,
                                     fontName='Helvetica', alignment=TA_CENTER, spaceAfter=4),
        'cover_meta': ParagraphStyle('cover_meta', fontSize=10, textColor=MUTED,
                                      fontName='Helvetica', alignment=TA_CENTER),
        'section_h': ParagraphStyle('section_h', fontSize=16, textColor=TEAL,
                                     fontName='Helvetica-Bold', spaceBefore=16, spaceAfter=8,
                                     borderPad=4),
        'chart_title': ParagraphStyle('chart_title', fontSize=12, textColor=PURPLE,
                                       fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=4),
        'insight': ParagraphStyle('insight', fontSize=10, textColor=TEXT_DARK,
                                   fontName='Helvetica', leading=15, spaceAfter=8,
                                   leftIndent=10, borderPad=6,
                                   backColor=LIGHT_BG, borderColor=TEAL, borderWidth=1),
        'body': ParagraphStyle('body', fontSize=10, textColor=TEXT_DARK,
                                fontName='Helvetica', leading=14, spaceAfter=6),
        'stat_label': ParagraphStyle('stat_label', fontSize=8, textColor=MUTED,
                                      fontName='Helvetica-Bold'),
        'stat_val': ParagraphStyle('stat_val', fontSize=10, textColor=TEXT_DARK,
                                    fontName='Helvetica-Bold'),
    }
    return custom

def b64_to_img(b64_str, width=16*cm, max_height=12*cm):
    data = base64.b64decode(b64_str)
    buf = io.BytesIO(data)
    img = Image(buf, width=width)
    # Constrain height
    if img.imageHeight * (width / img.imageWidth) > max_height:
        img = Image(io.BytesIO(data), height=max_height)
    return img

def generate_pdf_report(dataset_name, rows, cols, num_cols, cat_cols,
                         clean_report, stats_dict, charts, username='User'):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             topMargin=2*cm, bottomMargin=2*cm,
                             leftMargin=2*cm, rightMargin=2*cm)
    s = make_styles()
    story = []
    now = datetime.now().strftime('%B %d, %Y  %H:%M')

    # ── Cover Page ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph('OMNI DATA AI', s['cover_title']))
    story.append(Paragraph('Intelligent Data Analysis Report', s['cover_sub']))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width='100%', thickness=1, color=TEAL))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f'Dataset: {dataset_name}', s['cover_meta']))
    story.append(Paragraph(f'Generated: {now}', s['cover_meta']))
    story.append(Paragraph(f'Prepared for: {username}', s['cover_meta']))
    story.append(Spacer(1, 1*cm))

    # Summary box
    summary_data = [
        ['Total Rows', 'Total Columns', 'Numeric Features', 'Categorical Features'],
        [str(rows), str(cols), str(len(num_cols)), str(len(cat_cols))],
    ]
    summary_table = Table(summary_data, colWidths=[4*cm]*4)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SURFACE),
        ('TEXTCOLOR', (0,0), (-1,0), TEAL),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,1), LIGHT_BG),
        ('TEXTCOLOR', (0,1), (-1,1), TEXT_DARK),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 18),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [SURFACE, LIGHT_BG]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROUNDEDCORNERS', [4]),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(summary_table)
    story.append(PageBreak())

    # ── Data Cleaning Report ─────────────────────────────────────────────────
    story.append(Paragraph('Data Cleaning Report', s['section_h']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=PURPLE))
    story.append(Spacer(1, 0.3*cm))
    for item in (clean_report or []):
        story.append(Paragraph(f'• {item}', s['body']))
    story.append(Spacer(1, 0.5*cm))

    # ── Statistics Table ─────────────────────────────────────────────────────
    story.append(Paragraph('Descriptive Statistics', s['section_h']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=PURPLE))
    story.append(Spacer(1, 0.3*cm))

    if stats_dict and num_cols:
        metrics = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']
        available = [m for m in metrics if any(m in stats_dict.get(c, {}) for c in num_cols[:6])]
        cols_to_show = num_cols[:6]
        header = ['Metric'] + [c[:12] for c in cols_to_show]
        stat_rows = [header]
        for m in available:
            row = [m]
            for c in cols_to_show:
                val = stats_dict.get(c, {}).get(m, '—')
                row.append(f'{val:.3f}' if isinstance(val, float) else str(val) if val else '—')
            stat_rows.append(row)

        col_w = [3*cm] + [max(2.5*cm, (17*cm-3*cm)/len(cols_to_show))]*len(cols_to_show)
        stat_table = Table(stat_rows, colWidths=col_w)
        stat_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), SURFACE),
            ('TEXTCOLOR', (0,0), (-1,0), TEAL),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,1), (0,-1), LIGHT_BG),
            ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,1), (0,-1), PURPLE),
            ('ROWBACKGROUNDS', (1,1), (-1,-1), [colors.white, LIGHT_BG]),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(stat_table)

    story.append(PageBreak())

    # ── Charts ────────────────────────────────────────────────────────────────
    if charts:
        story.append(Paragraph('Visualizations & AI Insights', s['section_h']))
        story.append(HRFlowable(width='100%', thickness=0.5, color=PURPLE))
        story.append(Spacer(1, 0.4*cm))
        for i, chart in enumerate(charts):
            label = chart.get('chart_type', 'Chart').replace('_', ' ').title()
            story.append(Paragraph(f'{i+1}. {label}', s['chart_title']))
            try:
                img = b64_to_img(chart['image'], width=17*cm, max_height=11*cm)
                story.append(img)
            except:
                story.append(Paragraph('[Chart could not be rendered]', s['body']))
            if chart.get('insight'):
                clean_insight = chart['insight'].replace('**', '')
                story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph(f'AI Insight: {clean_insight}', s['insight']))
            story.append(Spacer(1, 0.5*cm))
            if (i+1) % 2 == 0 and i < len(charts)-1:
                story.append(PageBreak())

    # ── Footer note ──────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph('Report generated by Omni Data AI', s['cover_meta']))
    story.append(Paragraph('Intelligent Multi-Format Data Visualization Platform', s['cover_meta']))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width='60%', thickness=0.5, color=TEAL))

    doc.build(story)
    buf.seek(0)
    return buf
