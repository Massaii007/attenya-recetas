#!/usr/bin/env python3
"""
Generador de PDF para recetas tipo COMPONENTE — v4.
Método prueba-y-ajuste: mide la altura real del contenido y recalcula
la escala para que llene ~92 % de la página A4.

Zona FIJA (no escala): Header (título, subtítulo, meta) + foto + línea.
Zona VARIABLE (escala): todo lo de debajo de la línea.
"""

import sys
import os
import io
import subprocess
from xml.sax.saxutils import escape as xml_escape

def _ensure_deps():
    for pkg, test in [("reportlab", "reportlab"), ("Pillow", "PIL")]:
        try:
            __import__(test)
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg,
                 "--break-system-packages", "-q"])

_ensure_deps()

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image, KeepTogether,
)
from reportlab.platypus.doctemplate import LayoutError
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Line


# ─── helpers ─────────────────────────────────────────
def safe(text):
    if not text:
        return ""
    t = xml_escape(str(text))
    t = t.replace('\u2022', '\u2013')
    t = t.replace('\u2026', '...')
    return t


# ─── colores ─────────────────────────────────────────
DARK   = HexColor('#2C2C2C')
MED    = HexColor('#555555')
VLIGHT = HexColor('#F5F5F5')
SENIOR_BG = HexColor('#EBF5FB')
SENIOR_FG = HexColor('#1A5276')
PUNTOS_BG = HexColor('#FDEDEC')
PUNTOS_FG = HexColor('#922B21')
APPCC_BG  = HexColor('#FEF9E7')
APPCC_FG  = HexColor('#7D6608')
EMPL_BG   = HexColor('#F0F3F4')
EMPL_FG   = HexColor('#2C3E50')


# ─── estilos con factor de escala ────────────────────
def _styles(scale=1.0, header_only=False):
    """
    Genera diccionario de estilos.
    header_only=True  → tamaños fijos para la zona de header.
    header_only=False → tamaños escalados para el cuerpo.
    """
    base = getSampleStyleSheet()
    s = {}

    # Header: siempre a tamaño fijo
    s['title'] = ParagraphStyle(
        'RTitle', parent=base['Heading1'],
        fontSize=28, fontName='Helvetica-Bold',
        textColor=DARK, leading=32, spaceAfter=1,
    )
    s['subtitle'] = ParagraphStyle(
        'RSub', parent=base['Normal'],
        fontSize=11, fontName='Helvetica',
        textColor=MED, leading=14, spaceAfter=3,
    )
    s['meta'] = ParagraphStyle(
        'RMeta', parent=base['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=MED, leading=12,
    )

    if header_only:
        return s

    # Body: escalado
    def sz(pt):
        return max(5.5, pt * scale)

    def ld(pt):
        return max(7, pt * scale)

    def sp(pt):
        return max(1, pt * scale)

    s['section'] = ParagraphStyle(
        'RSec', parent=base['Heading2'],
        fontSize=sz(9), fontName='Helvetica-Bold',
        textColor=DARK, spaceBefore=sp(8), spaceAfter=sp(2), leading=ld(11.5),
    )
    s['step'] = ParagraphStyle(
        'RStep', parent=base['Normal'],
        fontSize=sz(7.5), fontName='Helvetica',
        textColor=DARK, leading=ld(10),
    )
    s['ing_title'] = ParagraphStyle(
        'RIngT', parent=base['Normal'],
        fontSize=sz(7.5), fontName='Helvetica-Bold',
        textColor=DARK, spaceBefore=sp(6), spaceAfter=sp(1),
    )
    s['ing_item'] = ParagraphStyle(
        'RIngI', parent=base['Normal'],
        fontSize=sz(7), fontName='Helvetica',
        textColor=MED, leading=ld(9.5), leftIndent=4,
    )
    s['senior'] = ParagraphStyle(
        'RSenior', parent=base['Normal'],
        fontSize=sz(7), fontName='Helvetica',
        textColor=SENIOR_FG, leading=ld(9.5),
        backColor=SENIOR_BG, borderPadding=sp(5),
    )
    s['emplatado'] = ParagraphStyle(
        'REmpl', parent=base['Normal'],
        fontSize=sz(7), fontName='Helvetica',
        textColor=EMPL_FG, leading=ld(9.5),
        backColor=EMPL_BG, borderPadding=sp(5),
    )
    s['puntos'] = ParagraphStyle(
        'RPuntos', parent=base['Normal'],
        fontSize=sz(7), fontName='Helvetica',
        textColor=PUNTOS_FG, leading=ld(9.5),
        backColor=PUNTOS_BG, borderPadding=sp(5),
    )
    s['appcc'] = ParagraphStyle(
        'RAPPCC', parent=base['Normal'],
        fontSize=sz(7), fontName='Helvetica',
        textColor=APPCC_FG, leading=ld(9.5),
        backColor=APPCC_BG, borderPadding=sp(5),
    )
    s['cita'] = ParagraphStyle(
        'RCita', parent=base['Normal'],
        fontSize=sz(7.5), fontName='Helvetica-Oblique',
        textColor=MED, leading=ld(10),
        spaceBefore=sp(6), alignment=TA_JUSTIFY,
    )
    s['componentes'] = ParagraphStyle(
        'RComp', parent=base['Normal'],
        fontSize=sz(7), fontName='Helvetica',
        textColor=MED, leading=ld(9.5),
    )
    return s


# ─── imagen con aspect ratio preservado ──────────────
def _load_image(path, max_w, max_h):
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            ow, oh = im.size
        sc = min(max_w / ow, max_h / oh)
        return Image(path, width=ow * sc, height=oh * sc)
    except Exception:
        return Image(path, width=max_w, height=max_h)


# ─── separador fino ─────────────────────────────────
def _separator(cw, color='#CCCCCC'):
    d = Drawing(cw, 3)
    ln = Line(0, 1.5, cw, 1.5)
    ln.strokeColor = HexColor(color)
    ln.strokeWidth = 0.4
    d.add(ln)
    return d


# ─── construir header fijo ───────────────────────────
def _build_header(recipe, s, cw, image_path):
    """Retorna (header_flowables, img_col_w).  Estos NO cambian con la escala."""
    IMG_MAX = 5.5 * cm
    has_img = bool(image_path and os.path.exists(image_path))

    # Calcular columnas
    if has_img:
        img = _load_image(image_path, IMG_MAX, IMG_MAX)
        img_col = IMG_MAX + 0.4 * cm
        txt_col = cw - img_col
    else:
        img = None
        img_col = 0
        txt_col = cw

    # Columna izquierda: título + subtítulo + metadata (todo junto a la foto)
    htxt = []
    htxt.append(Paragraph(safe(recipe["title"]), s['title']))
    htxt.append(Paragraph(
        f'{safe(recipe.get("subtitle",""))}. {safe(recipe.get("description",""))}',
        s['subtitle'],
    ))

    # Metadata como mini-tabla de 2 columnas dentro de la columna de texto
    m = recipe.get("meta", {})
    meta_left = (
        f'<b>Base:</b> {safe(m.get("base",""))}<br/>'
        f'<b>Rendimiento:</b> {safe(m.get("rendimiento",""))}<br/>'
        f'<b>Mise en place:</b> {safe(m.get("mise_en_place",""))}'
    )
    meta_right = (
        f'<b>Tiempo total:</b> {safe(m.get("tiempo_total",""))}<br/>'
        f'<b>T&#233;cnica:</b> {safe(m.get("tecnica",""))}<br/>'
        f'<b>Conservaci&#243;n:</b> {safe(m.get("conservacion",""))}'
    )

    meta_inner_w = txt_col - 4  # small margin
    meta_tbl = Table(
        [[Paragraph(meta_left, s['meta']),
          Paragraph(meta_right, s['meta'])]],
        colWidths=[meta_inner_w * 0.50, meta_inner_w * 0.50],
    )
    meta_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 2),
        ('BACKGROUND',   (0, 0), (-1, -1), VLIGHT),
    ]))
    htxt.append(Spacer(1, 3))
    htxt.append(meta_tbl)

    if has_img:
        header_tbl = Table([[htxt, img]], colWidths=[txt_col, img_col])
    else:
        header_tbl = Table([[htxt]], colWidths=[cw])

    header_tbl.setStyle(TableStyle([
        ('VALIGN',  (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',   (-1, 0), (-1, 0), 'RIGHT'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))

    parts = [header_tbl, Spacer(1, 4), _separator(cw), Spacer(1, 3)]
    return parts, img_col


# ─── construir cuerpo con escala ─────────────────────
def _build_body(recipe, scale, cw, img_col):
    """Construye la lista de flowables del cuerpo con la escala dada."""
    s = _styles(scale)
    body_parts = []

    has_senior = bool(recipe.get("adaptacion_senior"))
    has_emplatado = bool(recipe.get("emplatado"))
    has_puntos = bool(recipe.get("puntos_criticos"))
    has_componentes = bool(recipe.get("componentes_plato"))

    sp = max(1, 3 * scale)   # spacer base

    # ── COMPONENTES DEL PLATO
    if has_componentes:
        comp_text = ' &#183; '.join(safe(c) for c in recipe["componentes_plato"])
        body_parts.append(Paragraph(
            f'<b>Componentes:</b> {comp_text}',
            s['componentes'],
        ))
        body_parts.append(Spacer(1, sp))

    # ── columna izquierda: fases
    left = []
    for fase in recipe.get("fases", []):
        if not fase.get("steps"):
            continue
        left.append(Paragraph(f'<b>{safe(fase["title"])}</b>', s['section']))
        for i, step in enumerate(fase["steps"], 1):
            left.append(Paragraph(f'{i}. {safe(step)}', s['step']))

    # ── columna derecha: ingredientes
    right = []
    for grupo in recipe.get("ingredientes", []):
        right.append(Paragraph(safe(grupo["grupo"]), s['ing_title']))
        for item in grupo["items"]:
            nota = (f' <i>({safe(item["nota"])})</i>'
                    if item.get("nota") else '')
            right.append(Paragraph(
                f'- {safe(item["nombre"])}: {safe(item["cantidad"])}{nota}',
                s['ing_item'],
            ))

    # ── anchos de columna
    if img_col > 0:
        right_w = img_col
        left_w = cw - right_w
    else:
        left_w = cw * 0.58
        right_w = cw * 0.42

    body_tbl = Table([[left, right]], colWidths=[left_w, right_w])
    body_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 6),
        ('LEFTPADDING',  (1, 0), (1, 0), 6),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('LINEAFTER',    (0, 0), (0, 0), 0.4, VLIGHT),
    ]))
    body_parts.append(body_tbl)
    body_parts.append(Spacer(1, sp + 1))

    # ── EMPLATADO
    if has_emplatado:
        empl_text = ' '.join(
            f'{i+1}. {safe(st)}' for i, st in enumerate(recipe["emplatado"]))
        body_parts.append(Paragraph(
            f'<b>Emplatado:</b> {empl_text}', s['emplatado'],
        ))
        body_parts.append(Spacer(1, sp))

    # ── PUNTOS CRÍTICOS
    if has_puntos:
        body_parts.append(Paragraph(
            f'<b>PUNTOS CR&#205;TICOS:</b> {safe(recipe["puntos_criticos"])}',
            s['puntos'],
        ))
        body_parts.append(Spacer(1, sp))

    # ── APPCC
    if recipe.get("appcc"):
        body_parts.append(Paragraph(
            f'<b>APPCC:</b> {safe(recipe["appcc"])}', s['appcc'],
        ))
        body_parts.append(Spacer(1, sp))

    # ── ADAPTACIÓN SENIOR (entre APPCC y cita)
    if has_senior:
        body_parts.append(Paragraph(
            f'<b>ADAPTACI&#211;N SENIOR:</b> {safe(recipe["adaptacion_senior"])}',
            s['senior'],
        ))
        body_parts.append(Spacer(1, sp))

    # ── cita final
    if recipe.get("cita"):
        body_parts.append(Paragraph(
            f'&#171;{safe(recipe["cita"])}&#187;', s['cita'],
        ))

    return body_parts


# ─── medir altura de flowables ───────────────────────
def _measure_height(flowables, page_w, margin):
    """Construye un PDF en memoria y mide cuántas páginas y la altura usada."""
    buf = io.BytesIO()
    available_w = page_w - 2 * margin

    heights = []

    class _HeightTracker(SimpleDocTemplate):
        def afterPage(self):
            heights.append(self.frame._y)

    doc = _HeightTracker(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )
    try:
        doc.build(list(flowables))
    except LayoutError:
        return None, 999   # no cabe

    n_pages = len(heights)
    if n_pages == 0:
        return 0, 0

    page_h = A4[1]
    usable_h = page_h - 2 * margin

    # La última página: heights[-1] es el frame._y restante
    used_on_last = usable_h - heights[-1]
    total_used = (n_pages - 1) * usable_h + used_on_last

    return total_used, n_pages


# ─── generador principal ─────────────────────────────
def generate_componente_pdf(recipe, output_path, image_path=None):
    """Genera el PDF benchmark con ajuste automático de escala."""

    PAGE_W, PAGE_H = A4
    MARGIN = 1.2 * cm
    cw = PAGE_W - 2 * MARGIN
    usable_h = PAGE_H - 2 * MARGIN

    # ── 1. Header fijo
    s_hdr = _styles(header_only=True)
    header_parts, img_col = _build_header(recipe, s_hdr, cw, image_path)

    # Medir header
    header_h, _ = _measure_height(header_parts, PAGE_W, MARGIN)

    # Espacio disponible para el cuerpo
    body_budget = usable_h - header_h

    # ── 2. Primera prueba a escala 1.0
    body_10 = _build_body(recipe, 1.0, cw, img_col)
    body_h_10, n_pages = _measure_height(header_parts + body_10, PAGE_W, MARGIN)

    # Altura del cuerpo a escala 1.0
    body_content_h = body_h_10 - header_h
    if body_content_h <= 0:
        body_content_h = 1

    # ── 3. Calcular escala óptima
    TARGET_FILL = 0.92   # queremos llenar el 92 % de la página
    target_body_h = body_budget * TARGET_FILL

    # La relación entre escala y altura es ~lineal para text
    raw_scale = target_body_h / body_content_h

    # Limitar rango
    SCALE_MIN = 0.75
    SCALE_MAX = 1.35
    scale = max(SCALE_MIN, min(SCALE_MAX, raw_scale))

    # ── 4. Verificar que cabe en 1 página — si no, reducir
    for attempt in range(5):
        body_final = _build_body(recipe, scale, cw, img_col)
        full_story = list(header_parts) + body_final
        total_h, n_pages = _measure_height(full_story, PAGE_W, MARGIN)

        if n_pages <= 1:
            break
        # Reduce un 8 % por intento
        scale *= 0.92

    scale = max(SCALE_MIN, scale)

    # ── 5. Build final
    body_final = _build_body(recipe, scale, cw, img_col)
    full_story = list(header_parts) + body_final

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    doc.build(full_story)
    return output_path


# ─── CLI ─────────────────────────────────────────────
if __name__ == "__main__":
    import json
    if len(sys.argv) < 3:
        print("Uso: python generate_componente.py <recipe.json> <output.pdf> [image_path]")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    img = sys.argv[3] if len(sys.argv) > 3 else None
    print(f"PDF generado: {generate_componente_pdf(data, sys.argv[2], img)}")
