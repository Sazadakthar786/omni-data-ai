import io
import re

def extract_text(file_bytes: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            parts = []
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    return io.BytesIO(file_bytes).read().decode("utf-8", errors="ignore")

def analyze_text(text: str):
    entities_kw = ["user","admin","system","database","server","api","client","application","service","module","component","interface","gateway","cache","queue","manager","controller","handler","processor","validator","authenticator"]
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_ ]{1,40}", text.lower())
    entities = []
    for kw in entities_kw:
        if kw in tokens or re.search(rf"\b{kw}\b", text.lower()):
            entities.append({"name": kw, "type": "component" if kw not in ["user","admin"] else "actor"})
    rel_patterns = [
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) connects to (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "connects to"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) sends to (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "sends to"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) stores in (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "stores in"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) validates (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "validates"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) processes (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "processes"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) calls (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "calls"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) depends on (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "depends on"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) manages (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "manages"),
        (r"(\b[A-Za-z][A-Za-z0-9_ ]{1,40}) communicates with (\b[A-Za-z][A-Za-z0-9_ ]{1,40})", "communicates with"),
    ]
    relationships = []
    for pat, label in rel_patterns:
        for m in re.findall(pat, text, flags=re.IGNORECASE):
            a = m[0].strip()
            b = m[1].strip()
            relationships.append((a, label, b))
    steps = []
    for m in re.findall(r"(?:Step\s*\d+[:\.\-]?\s*)?([A-Za-z][A-Za-z0-9_ ]{2,40})", text, flags=re.IGNORECASE):
        s = m.strip()
        if s.lower() in ["first","then","finally","next"]:
            continue
        if len(steps) < 12:
            steps.append(s)
    if not steps:
        seq = re.findall(r"(First|Then|Finally|Next)\s+([A-Za-z][A-Za-z0-9_ ]{2,40})", text, flags=re.IGNORECASE)
        steps = [w[0] + " " + w[1] for w in seq][:12]
    doc_type = "General Technical"
    srs_kw = ["requirement","shall","system","user","functional"]
    spec_kw = ["architecture","component","module","api"]
    bp_kw = ["workflow","process","stakeholder"]
    db_kw = ["table","column","primary key","foreign key"]
    t = text.lower()
    if sum(1 for k in srs_kw if k in t) >= 3:
        doc_type = "SRS"
    elif sum(1 for k in spec_kw if k in t) >= 2:
        doc_type = "Technical Spec"
    elif sum(1 for k in bp_kw if k in t) >= 2:
        doc_type = "Business Process"
    elif sum(1 for k in db_kw if k in t) >= 2:
        doc_type = "Database Design"
    return {"entities": entities, "relationships": relationships, "actions": steps, "doc_type": doc_type}

def decide_diagrams(analysis_result):
    entities = analysis_result.get("entities", [])
    relationships = analysis_result.get("relationships", [])
    actions = analysis_result.get("actions", [])
    components = [e for e in entities if e.get("type") == "component"]
    diagrams = []
    if len(entities) >= 2 and len(relationships) >= 1:
        diagrams.append("ER Diagram")
    if actions:
        diagrams.append("Flowchart")
    if len(components) >= 3:
        diagrams.append("Block Diagram")
    actors = [e for e in entities if e.get("type") == "actor"]
    if actors and actions:
        diagrams.append("Use Case Diagram")
    if relationships and actors:
        diagrams.append("Sequence Diagram")
    if len(entities) >= 5 and len(relationships) >= 4:
        diagrams.append("Network Diagram")
    if len(entities) >= 4:
        diagrams.append("Mind Map")
    return diagrams
