#!/usr/bin/env python3
"""
generate_html_ikea.py
Lee data_ikea/<recipe_id>.json y produce recetas/<recipe_id>.html
en formato IKEA (landscape · side panel · slides discretos · 3 pasos por slide).

Estructura sidebar: 00 INTRO + 1 entry por paso individual (apunta al slide del grupo).
Estructura slides:  Slide 0 (intro) + N slides con 3 pasos cada uno (último incluye Notas finales).

Uso:
  python3 generate_html_ikea.py <recipe_id>
  python3 generate_html_ikea.py --all      # genera todos los disponibles
  python3 generate_html_ikea.py --list     # lista los disponibles
"""
import json
import sys
from pathlib import Path
from html import escape

REPO     = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data_ikea"
HTML_DIR = REPO / "recetas"
IMG_DIR  = "../img_ikea"   # ruta relativa desde recetas/
CSS_REL  = "_styles_ikea.css"

STEPS_PER_SLIDE = 3


def step_to_slide(n: int) -> int:
    """Paso (1..N) → slide-idx (1..ceil(N/3))."""
    return ((n - 1) // STEPS_PER_SLIDE) + 1


def render_step_inner(s: dict, elt: dict) -> str:
    """HTML del cuerpo de un paso (sin wrapper de slide)."""
    ill_path = f'{IMG_DIR}/{s["illustration"]}'
    fields = []
    fields.append(f'''
          <div class="field">
            <span class="field-label accion" style="background:{elt["color"]}">ACCIÓN</span>
            <span class="field-value">{escape(s["action"])}</span>
          </div>''')
    if s.get("ingredients"):
        fields.append(f'''
              <div class="field">
                <span class="field-label ingredientes">INGREDIENTES</span>
                <span class="field-value">{escape(s["ingredients"])}</span>
              </div>''')
    if s.get("temp_time"):
        fields.append(f'''
              <div class="field">
                <span class="field-label temp">TEMP·TIEMPO</span>
                <span class="field-value">{escape(s["temp_time"])}</span>
              </div>''')
    if s.get("note"):
        fields.append(f'''
              <div class="field">
                <span class="field-label nota">NOTA</span>
                <span class="field-value">{escape(s["note"])}</span>
              </div>''')

    return f'''
            <article class="step">
              <div class="illustration">
                <img src="{ill_path}" alt="Paso {s["n"]}: {escape(s["title"])}">
              </div>
              <div class="info">
                <div class="head">
                  <span class="num">{s["n"]:02d}</span>
                  <span class="badge {elt["key"]}" style="background:{elt["color"]}">{escape(elt["label"])}</span>
                </div>
                <h3 class="title">{escape(s["title"])}</h3>
                {"".join(fields)}
              </div>
            </article>'''


def render(data: dict) -> str:
    e_lookup = {e["key"]: e for e in data["elements"]}
    steps = data["steps"]
    notes = data.get("notes_final", {})

    # Agrupar pasos en grupos de N
    grouped = [steps[i:i+STEPS_PER_SLIDE] for i in range(0, len(steps), STEPS_PER_SLIDE)]
    max_slide = len(grouped)

    # Sidebar: intro + 1 entry por paso individual
    sidebar_items = ['''
          <a class="sidebar-step active" data-slide-target="0" href="#slide-0">
            <span class="num">00</span>
            <span class="info">
              <span class="badge intro">INTRO</span>
              <span class="title-mini">Resumen · ingredientes · pasos</span>
            </span>
          </a>''']
    for s in steps:
        elt = e_lookup[s["element"]]
        slide_idx = step_to_slide(s["n"])
        sidebar_items.append(f'''
          <a class="sidebar-step" data-slide-target="{slide_idx}" href="#slide-{slide_idx}">
            <span class="num">{s["n"]:02d}</span>
            <span class="info">
              <span class="badge" style="background:{elt['color']}">{escape(elt["label"])}</span>
              <span class="title-mini">{escape(s["title"])}</span>
            </span>
          </a>''')

    # Element rail
    rail = "\n".join(
        f'<div class="element-tag {e["key"]}" style="background:{e["color"]}">{escape(e["label"])}</div>'
        for e in data["elements"]
    )

    # Ingredients grid
    ing_html_blocks = []
    for e in data["elements"]:
        block = data["ingredients_by_element"][e["key"]]
        items = "".join(f"<li>{escape(it)}</li>" for it in block["items"])
        note = f'<div class="note">{escape(block["note"])}</div>' if block.get("note") else ""
        equip = ""
        if block.get("equipment"):
            equip_items = "".join(f"<li>{escape(it)}</li>" for it in block["equipment"])
            equip = (
                f'<div class="equipment-label">{escape(block.get("equipment_label","Equipo necesario:"))}</div>'
                f'<ul>{equip_items}</ul>'
            )
        ing_html_blocks.append(f'''
          <div class="ing-col {e["key"]}">
            <h3>{escape(e["label"])}</h3>
            <ul>{items}</ul>
            {note}
            {equip}
          </div>''')

    # Summary grid (cada cell → slide del grupo que contiene el paso)
    # Si hay 9 pasos (post-fusión 9+10), la última cell ocupa 2 cols (span-2) para llenar 5x2
    summary_cells = []
    total = len(steps)
    for i, s in enumerate(steps):
        elt = e_lookup[s["element"]]
        slide_idx = step_to_slide(s["n"])
        is_last = (i == total - 1)
        span_class = " span-2" if (is_last and total % 5 == 4) else ""
        summary_cells.append(f'''
          <a class="summary-cell{span_class}" data-slide-target="{slide_idx}" href="#slide-{slide_idx}">
            <div class="cell-head">
              <span class="cell-num">{s["n"]:02d}</span>
              <span class="cell-badge" style="background:{elt["color"]}">{escape(elt["label"])}</span>
            </div>
            <div class="cell-illustration">
              <img src="{IMG_DIR}/{s["illustration"]}" alt="">
            </div>
            <div class="cell-title">{escape(s["title"])}</div>
          </a>''')

    # Notas finales · al final del último slide del grupo
    notes_html = ""
    if notes:
        notes_html = f'''
            <section class="final-notes">
              <h2 class="notes-section-title">Notas finales · APPCC · Adaptación Senior</h2>
              <div class="notes-final">
                <div class="note-card appcc"><h4>APPCC</h4>{escape(notes.get("appcc",""))}</div>
                <div class="note-card senior"><h4>SENIOR</h4>{escape(notes.get("senior",""))}</div>
                <div class="note-card critical"><h4>CRÍTICO</h4>{escape(notes.get("critical",""))}</div>
              </div>
            </section>'''

    # Slides de grupos (3 pasos cada uno)
    group_slide_blocks = []
    for idx, group in enumerate(grouped, 1):
        steps_inner = "".join(render_step_inner(s, e_lookup[s["element"]]) for s in group)
        is_last = (idx == max_slide)
        suffix = notes_html if (is_last and notes) else ""
        group_slide_blocks.append(f'''
          <section class="slide group-slide" id="slide-{idx}" data-slide="{idx}">
            {steps_inner}
            {suffix}
          </section>''')

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1024, initial-scale=1.0">
<title>{escape(data["title"])} · IKEA</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500&family=Jost:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{CSS_REL}">
</head>
<body>
<div class="layout">

  <aside class="sidebar">
    <a class="back-cocina" href="../index.html#detail-{data['recipe_id']}">← COCINA</a>
    <h2>Resumen · {len(steps)} pasos</h2>
    {"".join(sidebar_items)}
  </aside>

  <main class="content">
    <section class="slide active" id="slide-0" data-slide="0">

      <section class="hero">
        <div class="hero-row">
          <div class="hero-left">
            <h1>{escape(data["title"])}</h1>
            <div class="subtitle">{escape(data["subtitle"])}</div>
          </div>
          <div class="hero-pax">25 PAX</div>
        </div>
        <div class="elements-rail">
          {rail}
        </div>
        <div class="element-explainer">Tres elementos. Cada color = un elemento. Sigue los pasos en orden.</div>
      </section>

      <section class="ingredients-block">
        <h2>Ingredientes</h2>
        <div class="calc-base">{escape(data["calc_base"])}</div>
        <div class="ingredients-grid">
          {"".join(ing_html_blocks)}
        </div>
        <div class="banda tiempo"><span class="tag">TIEMPO</span><div class="body">{escape(data["time"])}</div></div>
        <div class="banda senior"><span class="tag">SENIOR</span><div class="body">{escape(data["senior"])}</div></div>
      </section>

      <section class="summary-block">
        <h2>Resumen visual — los {len(steps)} pasos en orden</h2>
        <div class="summary-grid">
          {"".join(summary_cells)}
        </div>
      </section>

    </section>
    <!-- /slide-0 intro -->

    {"".join(group_slide_blocks)}
  </main>
</div>

<script>
  // Slide navigation · click discreto, no scroll spy
  const slides = document.querySelectorAll('.slide');
  const sidebarSteps = document.querySelectorAll('.sidebar-step');
  const triggers = document.querySelectorAll('[data-slide-target]');
  const content = document.querySelector('.content');
  const MAX = {max_slide};

  function show(n) {{
    const k = String(n);
    slides.forEach(s => s.classList.toggle('active', s.dataset.slide === k));
    sidebarSteps.forEach(a => a.classList.toggle('active', a.dataset.slideTarget === k));
    if (content) content.scrollTop = 0;
    const active = document.querySelector('.sidebar-step.active');
    if (active) active.scrollIntoView({{block: 'nearest'}});
  }}

  triggers.forEach(el => el.addEventListener('click', e => {{
    e.preventDefault();
    show(Number(el.dataset.slideTarget));
  }}));

  document.addEventListener('keydown', e => {{
    const active = document.querySelector('.slide.active');
    if (!active) return;
    const current = Number(active.dataset.slide);
    if (e.key === 'ArrowRight' && current < MAX) show(current + 1);
    if (e.key === 'ArrowLeft'  && current > 0)   show(current - 1);
  }});
</script>
</body>
</html>
"""
    return html


def process(recipe_id: str) -> bool:
    src = DATA_DIR / f"{recipe_id}.json"
    if not src.exists():
        print(f"  ✗ data_ikea JSON not found: {recipe_id}")
        return False
    data = json.loads(src.read_text(encoding="utf-8"))
    out = HTML_DIR / f"{recipe_id}.html"
    out.write_text(render(data), encoding="utf-8")
    print(f"  ✓ {out}  ({out.stat().st_size // 1024} KB)")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    arg = sys.argv[1]
    if arg == "--list":
        for f in sorted(DATA_DIR.glob("*.json")):
            print(f"  • {f.stem}")
        return
    if arg == "--all":
        ok = 0
        for f in sorted(DATA_DIR.glob("*.json")):
            if process(f.stem):
                ok += 1
        print(f"\nGenerated: {ok}")
        return
    process(arg)


if __name__ == "__main__":
    main()
