#!/usr/bin/env python3
"""Auditoría de PDFs de recetas — solo clasifica, no regenera nada."""

import os, re, shutil, glob
import fitz  # PyMuPDF

REPO = "/Users/massaii/Global Nomads Dropbox/Mike Meeger/2026/ATTENYA/attenya-recetas"
VAULT_RECETAS = "/Users/massaii/Global Nomads Dropbox/Mike Meeger/2026/techila/AI/SECOND_BRAIN/VAULT - TRABAJO/TRABAJO/COCKPIT/ATTENYA/Restaurante/Culinario/Recetas"
GOOD_DIR = os.path.join(REPO, "_good")
DATA_DIR = os.path.join(REPO, "data")
DATA_PDF_DIR = os.path.join(REPO, "data", "pdf")
PDFS_DIR = os.path.join(REPO, "pdfs")

os.makedirs(GOOD_DIR, exist_ok=True)

# Build recipe ID list from JSON filenames in data/
ids = sorted([f.replace(".json", "") for f in os.listdir(DATA_DIR)
              if f.endswith(".json") and not f.startswith(".")])

# Build vault index: recursively find all PDFs in vault
vault_index = {}
if os.path.isdir(VAULT_RECETAS):
    for root, dirs, files in os.walk(VAULT_RECETAS):
        for f in files:
            if f.endswith(".pdf"):
                name = f.replace(".pdf", "")
                vault_index[name] = os.path.join(root, f)


def find_pdf(rid):
    """Return dict of source -> path for each location where PDF exists."""
    found = {}
    # Vault (recursive)
    if rid in vault_index:
        found["vault"] = vault_index[rid]
    # data/pdf/
    p = os.path.join(DATA_PDF_DIR, rid + ".pdf")
    if os.path.isfile(p):
        found["data_pdf"] = p
    # pdfs/
    p = os.path.join(PDFS_DIR, rid + ".pdf")
    if os.path.isfile(p):
        found["pdfs"] = p
    return found


def classify_pdf(path):
    """Classify a PDF. Returns (estado, problema)."""
    size = os.path.getsize(path)
    if size < 5120:
        return "ROTO", f"<5KB ({size}B)"

    try:
        doc = fitz.open(path)
    except Exception as e:
        return "ROTO", f"No se puede abrir: {e}"

    if doc.page_count == 0:
        doc.close()
        return "ROTO", "0 páginas"

    text = doc[0].get_text()
    doc.close()

    if not text or len(text.strip()) < 50:
        return "ROTO", "Sin texto extraíble"

    problems = []

    # Check size >10KB
    if size <= 10240:
        problems.append(f"≤10KB ({size}B)")

    # Check ingredientes con cantidades (números + unidades)
    qty_pattern = re.compile(r'\d+\s*(g|kg|ml|l|L|uds|ud|unidades|unidad|cs|cc|pizca)', re.IGNORECASE)
    qty_matches = qty_pattern.findall(text)
    if len(qty_matches) < 2:
        problems.append("Sin ingredientes con cantidades")

    # Check al menos 2 "Fase" con pasos numerados
    fase_pattern = re.compile(r'Fase\s+\d', re.IGNORECASE)
    fases = fase_pattern.findall(text)
    if len(fases) < 2:
        problems.append(f"Fases insuficientes ({len(fases)})")

    # Check no empieza con "APPCC." o "." suelto en la descripción
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # Look for description-like line (skip title, category lines)
    for line in lines[1:6]:
        if line.startswith("APPCC."):
            problems.append("Descripción empieza con APPCC.")
            break
        if line == "." or (len(line) <= 2 and line.startswith(".")):
            problems.append("Descripción empieza con punto suelto")
            break

    # Check metadatos: "Tiempo total" present and not empty
    tiempo_pattern = re.compile(r'Tiempo\s+total\s*[:\-]?\s*(\S+)', re.IGNORECASE)
    tiempo_match = tiempo_pattern.search(text)
    if not tiempo_match:
        problems.append("Sin Tiempo total")

    if not problems:
        return "BUENO", ""
    elif size >= 5120 and len(text.strip()) >= 50:
        return "PARCIAL", "; ".join(problems)
    else:
        return "ROTO", "; ".join(problems)


# Run audit
results = []
counts = {"BUENO": 0, "PARCIAL": 0, "ROTO": 0, "SIN_PDF": 0}

for rid in ids:
    sources = find_pdf(rid)

    if not sources:
        results.append({
            "id": rid,
            "vault": "-", "data_pdf": "-", "pdfs": "-",
            "mejor": "-", "estado": "SIN_PDF", "problema": "No encontrado en ninguna ubicación"
        })
        counts["SIN_PDF"] += 1
        continue

    classifications = {}
    for src, path in sources.items():
        estado, problema = classify_pdf(path)
        classifications[src] = (estado, problema, path)

    # Determine best source (priority: BUENO > PARCIAL > ROTO; then vault > data_pdf > pdfs)
    priority_estado = {"BUENO": 0, "PARCIAL": 1, "ROTO": 2}
    priority_src = {"vault": 0, "data_pdf": 1, "pdfs": 2}
    best_src = min(classifications.keys(),
                   key=lambda s: (priority_estado[classifications[s][0]], priority_src[s]))
    best_estado, best_problema, best_path = classifications[best_src]

    # Source labels for table
    src_labels = {"vault": "vault", "data_pdf": "data/pdf", "pdfs": "pdfs"}

    row = {
        "id": rid,
        "vault": classifications.get("vault", ("-",))[0] if "vault" in classifications else "-",
        "data_pdf": classifications.get("data_pdf", ("-",))[0] if "data_pdf" in classifications else "-",
        "pdfs": classifications.get("pdfs", ("-",))[0] if "pdfs" in classifications else "-",
        "mejor": src_labels.get(best_src, best_src),
        "estado": best_estado,
        "problema": best_problema
    }
    results.append(row)
    counts[best_estado] += 1

    # Copy best to _good/ if BUENO
    if best_estado == "BUENO":
        shutil.copy2(best_path, os.path.join(GOOD_DIR, rid + ".pdf"))

# Generate report
report_lines = []
report_lines.append("# Auditoría de PDFs de Recetas")
report_lines.append(f"\n**Fecha:** 2026-03-16")
report_lines.append(f"**Total recetas:** {len(ids)}")
report_lines.append(f"**BUENO:** {counts['BUENO']} | **PARCIAL:** {counts['PARCIAL']} | **ROTO:** {counts['ROTO']} | **SIN_PDF:** {counts['SIN_PDF']}")
report_lines.append("")
report_lines.append("| # | ID | Vault | data/pdf | pdfs | Mejor | Estado | Problema |")
report_lines.append("|---|---|---|---|---|---|---|---|")

for i, r in enumerate(results, 1):
    report_lines.append(
        f"| {i} | {r['id']} | {r['vault']} | {r['data_pdf']} | {r['pdfs']} | {r['mejor']} | {r['estado']} | {r['problema']} |"
    )

# Summary sections
report_lines.append("")
report_lines.append("## Resumen por estado")
report_lines.append("")
for estado in ["BUENO", "PARCIAL", "ROTO", "SIN_PDF"]:
    items = [r for r in results if r["estado"] == estado]
    report_lines.append(f"### {estado} ({len(items)})")
    if items:
        for r in items:
            prob = f" — {r['problema']}" if r['problema'] else ""
            report_lines.append(f"- {r['id']}{prob}")
    report_lines.append("")

report_path = os.path.join(REPO, "_auditoria_pdfs.md")
with open(report_path, "w") as f:
    f.write("\n".join(report_lines))

# Print summary
print(f"✓ Auditoría completada")
print(f"  Total: {len(ids)} recetas")
print(f"  BUENO:   {counts['BUENO']}")
print(f"  PARCIAL: {counts['PARCIAL']}")
print(f"  ROTO:    {counts['ROTO']}")
print(f"  SIN_PDF: {counts['SIN_PDF']}")
print(f"  Copiados a _good/: {counts['BUENO']}")
print(f"  Reporte: _auditoria_pdfs.md")
