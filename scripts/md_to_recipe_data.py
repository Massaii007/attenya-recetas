#!/usr/bin/env python3
"""
Parse a Culinary Advisor Benchmark .md file into a recipe_data dict
compatible with generate_componente_pdf() v3.
Captures ALL sections: adaptación senior, componentes, emplatado, puntos críticos.
"""
import re

def parse_benchmark_md(filepath):
    """Parse benchmark .md into recipe_data dict."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')

    data = {
        "title": "",
        "subtitle": "",
        "description": "",
        "meta": {
            "base": "",
            "rendimiento": "",
            "mise_en_place": "",
            "tiempo_total": "",
            "tecnica": "",
            "conservacion": ""
        },
        "fases": [],
        "ingredientes": [],
        "appcc": None,
        "cita": None,
        "adaptacion_senior": None,
        "componentes_plato": None,
        "emplatado": None,
        "puntos_criticos": None,
    }

    # --- TITLE (# line) ---
    for line in lines:
        if line.startswith('# ') and not line.startswith('## '):
            data["title"] = line[2:].strip()
            break

    # --- SUBTITLE (## line right after title) ---
    for i, line in enumerate(lines):
        if line.startswith('## ') and not line.startswith('### '):
            sub = line[3:].strip()
            skip_headers = ['componentes', 'procedimiento', 'emplatado', 'ingredientes', 'puntos', 'descripci']
            if not any(sub.lower().startswith(s) for s in skip_headers):
                data["subtitle"] = sub
                break

    # --- DESCRIPTION ---
    # First try: ## Descripción section
    desc_m = re.search(r'##\s*Descripci[oó]n\s*\n+(.+?)(?=\n##|\n---)', text, re.DOTALL)
    if desc_m:
        data["description"] = ' '.join(desc_m.group(1).strip().split())
    else:
        # Fallback: first non-header line after title
        found_title = False
        for i, line in enumerate(lines):
            if line.startswith('# ') and not line.startswith('## '):
                found_title = True
                continue
            if found_title and line.startswith('## ') and data["subtitle"]:
                continue
            if found_title and line.strip() and not line.startswith('#') and not line.startswith('---') and not line.startswith('**'):
                data["description"] = line.strip()
                break

    # --- META (from YAML frontmatter first, then fallback to **Key:** patterns) ---
    # Parse YAML frontmatter
    fm = {}
    fm_match = re.match(r'^---\s*\n(.+?)\n---', text, re.DOTALL)
    if fm_match:
        for fm_line in fm_match.group(1).split('\n'):
            kv = fm_line.split(':', 1)
            if len(kv) == 2:
                fm[kv[0].strip().lower()] = kv[1].strip()

    # Fill meta from frontmatter
    if fm.get('tipo'):
        data["meta"]["base"] = fm.get('tipo', '')
    if fm.get('pax'):
        data["meta"]["rendimiento"] = f"{fm.get('pax', '')} pax"
    if fm.get('tiempo_activo'):
        data["meta"]["mise_en_place"] = fm.get('tiempo_activo', '')
    if fm.get('tiempo_total'):
        data["meta"]["tiempo_total"] = fm.get('tiempo_total', '')
    if fm.get('tecnica'):
        data["meta"]["tecnica"] = fm.get('tecnica', '')
    if fm.get('dificultad'):
        data["meta"]["tecnica"] = fm.get('tecnica', fm.get('dificultad', ''))
    if fm.get('conservacion'):
        data["meta"]["conservacion"] = fm.get('conservacion', '')

    # Fallback: **Key:** patterns in body text
    meta_text = text
    if not data["meta"]["base"]:
        m = re.search(r'\*\*Base:\*\*\s*(.+?)(?:\s*·|\s*\*\*)', meta_text)
        if m: data["meta"]["base"] = m.group(1).strip()

    if not data["meta"]["rendimiento"]:
        m = re.search(r'\*\*Raci[oó]n:\*\*\s*(.+?)(?:\n|$)', meta_text)
        if m:
            data["meta"]["rendimiento"] = m.group(1).strip()
        else:
            m = re.search(r'\*\*Rendimiento:\*\*\s*(.+?)(?:\n|$)', meta_text)
            if m: data["meta"]["rendimiento"] = m.group(1).strip()

    if not data["meta"]["mise_en_place"]:
        m = re.search(r'\*\*Mise en place:\*\*\s*(.+?)(?:\s*·|\s*\*\*)', meta_text)
        if m: data["meta"]["mise_en_place"] = m.group(1).strip()

    if not data["meta"]["tiempo_total"]:
        m = re.search(r'\*\*Tiempo total:\*\*\s*(.+?)(?:\n|$)', meta_text)
        if m: data["meta"]["tiempo_total"] = m.group(1).strip()

    if not data["meta"]["tecnica"]:
        m = re.search(r'\*\*T[eé]cnica:\*\*\s*(.+?)(?:\s*·|\s*\*\*)', meta_text)
        if m: data["meta"]["tecnica"] = m.group(1).strip()

    if not data["meta"]["conservacion"]:
        m = re.search(r'\*\*Conservaci[oó]n:\*\*\s*(.+?)(?:\n|$)', meta_text)
        if m: data["meta"]["conservacion"] = m.group(1).strip()

    # --- ADAPTACIÓN SENIOR (narrative paragraph) ---
    senior_m = re.search(
        r'#{2,3}\s*ADAPTACI[OÓ]N\s+SENIOR\s*\n+(.+?)(?=\n---|\n#{2,3}\s)',
        text, re.DOTALL | re.IGNORECASE
    )
    if senior_m:
        senior_text = senior_m.group(1).strip()
        senior_text = re.sub(r'\*\*(.+?)\*\*', r'\1', senior_text)
        # Collapse multiple lines into one paragraph
        senior_text = ' '.join(senior_text.split())
        data["adaptacion_senior"] = senior_text

    # --- COMPONENTES DEL PLATO ---
    comp_m = re.search(
        r'##?\s*Componentes\s+del\s+plato\s*\n+(.+?)(?=\n---|\n##[^#]|\n###\s+(?!-))',
        text, re.DOTALL | re.IGNORECASE
    )
    if comp_m:
        comp_text = comp_m.group(1).strip()
        comp_lines = []
        for cl in comp_text.split('\n'):
            cl = cl.strip()
            if cl.startswith('- '):
                cl = re.sub(r'\*\*(.+?)\*\*', r'\1', cl)
                comp_lines.append(cl[2:].strip())
        if comp_lines:
            data["componentes_plato"] = comp_lines

    # --- EMPLATADO ---
    empl_m = re.search(
        r'###?\s*(?:Emplatado|EMPLATADO)\s*\n+(.+?)(?=\n---|\n###?\s+(?![\d])|\n##[^#])',
        text, re.DOTALL
    )
    if empl_m:
        empl_text = empl_m.group(1).strip()
        empl_steps = []
        for el in empl_text.split('\n'):
            m = re.match(r'^\d+\.\s+(.+)', el.strip())
            if m:
                step = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(1))
                empl_steps.append(step.strip())
        if empl_steps:
            data["emplatado"] = empl_steps

    # --- PUNTOS CRÍTICOS ---
    puntos_m = re.search(
        r'#{2,3}\s*(?:⚠️?\s*)?(?:PUNTOS?\s+CR[IÍ]TICOS?|Puntos?\s+cr[ií]ticos?)\s*\n+(.+?)(?=\n---|\n#{2,3}\s|\n\*")',
        text, re.DOTALL | re.IGNORECASE
    )
    if puntos_m:
        puntos_text = puntos_m.group(1).strip()
        puntos_text = re.sub(r'\*\*(.+?)\*\*', r'\1', puntos_text)
        puntos_text = ' '.join(puntos_text.split())
        data["puntos_criticos"] = puntos_text

    # --- FASES (procedure sections) ---
    skip_sections = ['adaptaci', 'ingrediente', 'puntos cr', 'appcc', 'alérgeno', 'alergeno',
                     'emplatado', 'componentes']

    current_fase = None
    in_ingredients = False
    in_appcc = False
    in_skip = False

    for line in lines:
        stripped = line.strip()

        # Track ## headers to know when entering/leaving Ingredientes
        if stripped.startswith('## ') and not stripped.startswith('### '):
            h2 = stripped[3:].strip().lower()
            if 'ingrediente' in h2:
                in_ingredients = True
                in_appcc = False
                in_skip = False
                if current_fase:
                    data["fases"].append(current_fase)
                    current_fase = None
            elif 'procedimiento' in h2:
                in_ingredients = False
                in_appcc = False
                in_skip = False
            elif any(s in h2 for s in ['emplatado', 'puntos', 'appcc', 'adaptaci']):
                in_skip = True
                in_ingredients = False
                if current_fase:
                    data["fases"].append(current_fase)
                    current_fase = None
            continue

        if stripped.startswith('### '):
            header = stripped[4:].strip()
            header_lower = header.lower()
            header_clean = re.sub(r'[⚠️\s]+', '', header).lower()

            if any(s in header_lower for s in ['ingrediente']):
                in_ingredients = True
                in_appcc = False
                in_skip = False
                if current_fase:
                    data["fases"].append(current_fase)
                    current_fase = None
                continue
            elif in_ingredients:
                # Skip ### headers within Ingredientes section (they are ingredient groups)
                continue
            elif any(s in header_clean for s in ['appcc', 'alérgeno', 'alergeno']):
                in_appcc = True
                in_ingredients = False
                in_skip = False
                if current_fase:
                    data["fases"].append(current_fase)
                    current_fase = None
                continue
            elif any(s in header_lower for s in ['puntos cr', 'punto cr', 'emplatado', 'componentes']):
                in_skip = True
                in_ingredients = False
                in_appcc = False
                if current_fase:
                    data["fases"].append(current_fase)
                    current_fase = None
                continue
            elif any(s in header_lower for s in ['adaptaci']):
                # Skip adaptación as a fase (captured separately)
                in_skip = True
                if current_fase:
                    data["fases"].append(current_fase)
                    current_fase = None
                continue
            else:
                in_appcc = False
                in_skip = False
                if current_fase:
                    data["fases"].append(current_fase)
                current_fase = {"title": header, "steps": []}
                continue

        if stripped.startswith('#### '):
            continue

        if current_fase and not in_ingredients and not in_appcc and not in_skip:
            m_step = re.match(r'^\d+\.\s+(.+)', stripped)
            if m_step:
                step = m_step.group(1).strip()
                step = re.sub(r'\*\*(.+?)\*\*', r'\1', step)
                current_fase["steps"].append(step)

    if current_fase and current_fase["steps"]:
        data["fases"].append(current_fase)

    # --- INGREDIENTES (capture ALL ingredient blocks) ---
    in_ing = False
    current_group = None
    ingredient_section_count = 0

    for line in lines:
        stripped = line.strip()

        # Match ingredient section headers
        if re.match(r'^#{2,3}\s+(?:Ingredientes|COMPONENTE:)', stripped, re.IGNORECASE):
            in_ing = True
            ingredient_section_count += 1
            # If it's a COMPONENTE section, create a group header from it
            comp_m = re.match(r'^#{2,3}\s+COMPONENTE:\s+(.+)', stripped)
            if comp_m:
                if current_group:
                    data["ingredientes"].append(current_group)
                current_group = None
            continue

        if in_ing:
            # New group header
            if stripped.startswith('#### ') or (stripped.startswith('### ') and 'ingrediente' in stripped.lower()):
                header = re.sub(r'^#{3,4}\s+', '', stripped).strip()
                # Check if it's another ingredients block (e.g. "Ingredientes romesco")
                if 'ingrediente' in header.lower():
                    continue
                if any(s in header.lower() for s in ['punto', 'appcc', 'alérgeno']):
                    if current_group:
                        data["ingredientes"].append(current_group)
                        current_group = None
                    in_ing = False
                    continue
                if current_group:
                    data["ingredientes"].append(current_group)
                current_group = {"grupo": header, "items": []}
                continue

            # Sub-section within ingredients
            if stripped.startswith('### ') and in_ing:
                header = stripped[4:].strip()
                if any(s in header.lower() for s in ['mise en place', 'elaboraci', 'punto', 'appcc']):
                    if current_group:
                        data["ingredientes"].append(current_group)
                        current_group = None
                    in_ing = False
                    continue
                # Treat ### headers inside ingredients as group headers
                if not any(s in header.lower() for s in ['ingrediente']):
                    if current_group:
                        data["ingredientes"].append(current_group)
                    current_group = {"grupo": header, "items": []}
                    continue

            # Ingredient line (list format: - Name: Quantity)
            m_ing = re.match(r'^-\s+(.+?):\s+(.+)', stripped)
            if m_ing and current_group is not None:
                nombre = m_ing.group(1).strip()
                rest = m_ing.group(2).strip()
                nota = None
                nota_m = re.search(r'\*\((.+?)\)\*', rest)
                if nota_m:
                    nota = nota_m.group(1)
                    rest = rest[:nota_m.start()].strip()
                item = {"nombre": nombre, "cantidad": rest}
                if nota:
                    item["nota"] = nota
                current_group["items"].append(item)
                continue
            # Also handle ingredient line without a current group
            if m_ing and current_group is None:
                current_group = {"grupo": "General", "items": []}
                nombre = m_ing.group(1).strip()
                rest = m_ing.group(2).strip()
                nota = None
                nota_m = re.search(r'\*\((.+?)\)\*', rest)
                if nota_m:
                    nota = nota_m.group(1)
                    rest = rest[:nota_m.start()].strip()
                item = {"nombre": nombre, "cantidad": rest}
                if nota:
                    item["nota"] = nota
                current_group["items"].append(item)
                continue

            # Ingredient line (table format: | Name | Quantity | ... optional cols ... |)
            if stripped.startswith('|') and stripped.endswith('|'):
                cols = [c.strip() for c in stripped.split('|')[1:-1]]  # skip empty first/last
                if len(cols) >= 2:
                    nombre_t = cols[0]
                    cantidad_t = cols[1]
                    # Collect notes from remaining columns (skip empty/separator)
                    extra = [c for c in cols[2:] if c and c != '—' and not re.match(r'^[-:\s]+$', c)]
                    nota_t = ', '.join(extra) if extra else None
                    # Skip header rows and separator rows
                    if nombre_t.lower() in ('ingrediente', '---', '', 'nombre'):
                        continue
                    if re.match(r'^[-|:\s]+$', nombre_t):
                        continue
                    if current_group is None:
                        current_group = {"grupo": "General", "items": []}
                    item = {"nombre": nombre_t, "cantidad": cantidad_t}
                    if nota_t:
                        item["nota"] = nota_t
                    current_group["items"].append(item)
                    continue

            # Section break
            if stripped.startswith('---') or (stripped.startswith('## ') and 'ingrediente' not in stripped.lower() and 'componente' not in stripped.lower()):
                if current_group:
                    data["ingredientes"].append(current_group)
                    current_group = None
                in_ing = False
                continue

    if current_group and current_group["items"]:
        data["ingredientes"].append(current_group)

    # --- APPCC ---
    appcc_m = re.search(r'#{2,3}\s*(?:⚠️?\s*)?APPCC\s*\n+(.+?)(?:\n\n|\n---|\n#{2,3}\s|\n\*")', text, re.DOTALL)
    if appcc_m:
        appcc_text = appcc_m.group(1).strip()
        appcc_text = re.sub(r'\*\*(.+?)\*\*', r'\1', appcc_text)
        data["appcc"] = appcc_text

    # --- CITA ---
    cita_m = re.search(r'\*"(.+?)"\*\s*$', text, re.DOTALL)
    if cita_m:
        data["cita"] = cita_m.group(1).strip()

    return data


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python md_to_recipe_data.py <file.md>")
        sys.exit(1)
    d = parse_benchmark_md(sys.argv[1])
    print(json.dumps(d, ensure_ascii=False, indent=2))
