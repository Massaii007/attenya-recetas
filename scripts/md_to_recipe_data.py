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
    # Skip standard section headers — only capture descriptive subtitles
    _skip_h2 = ['componentes', 'procedimiento', 'emplatado', 'ingredientes',
                'puntos', 'descripci', 'appcc', 'adaptaci', 'mise en place',
                'regeneraci', 'ensamblaje', 'montaje']
    for i, line in enumerate(lines):
        if line.startswith('## ') and not line.startswith('### '):
            sub = line[3:].strip()
            if not any(sub.lower().startswith(s) for s in _skip_h2):
                data["subtitle"] = sub
                break

    # --- YAML FRONTMATTER (parse early, used by description + meta) ---
    fm = {}
    fm_match = re.match(r'^---\s*\n(.+?)\n---', text, re.DOTALL)
    if fm_match:
        for fm_line in fm_match.group(1).split('\n'):
            kv = fm_line.split(':', 1)
            if len(kv) == 2:
                fm[kv[0].strip().lower()] = kv[1].strip()

    # --- DESCRIPTION ---
    # First try: ## Descripción section
    desc_m = re.search(r'##\s*Descripci[oó]n\s*\n+(.+?)(?=\n##|\n---)', text, re.DOTALL)
    if desc_m:
        candidate = ' '.join(desc_m.group(1).strip().split())
        if candidate and candidate not in ('.', 'APPCC.', 'APPCC'):
            data["description"] = candidate
    if not data["description"]:
        # Fallback: first plain text line after # Title (allow passing through subtitle ## and ---)
        _bad_desc = {'appcc.', 'appcc', '.'}
        _skip_starts = ('#', '---', '**', '|', '>', '*')
        found_title = False
        passed_subtitle = False
        _section_h2 = ['ingredientes', 'procedimiento', 'emplatado', 'puntos', 'appcc',
                        'adaptaci', 'mise en place', 'componentes']
        for i, line in enumerate(lines):
            if line.startswith('# ') and not line.startswith('## '):
                found_title = True
                continue
            if not found_title:
                continue
            # Stop at a section ## header (not a descriptive subtitle)
            if line.startswith('## ') and not line.startswith('### '):
                h2_text = line[3:].strip().lower()
                if any(h2_text.startswith(s) for s in _section_h2):
                    break  # hit a real section, stop
                else:
                    passed_subtitle = True
                    continue  # descriptive subtitle, skip but keep searching
            if line.startswith('### '):
                break  # hit a subsection, stop
            if line.strip() and not any(line.strip().startswith(s) for s in _skip_starts):
                candidate = line.strip()
                if candidate.lower() not in _bad_desc and not candidate.startswith('APPCC.'):
                    data["description"] = candidate
                    break
    # Final fallback: use frontmatter 'nombre' as description if still empty
    if not data["description"] and fm.get('nombre'):
        data["description"] = fm['nombre']

    # --- META (from YAML frontmatter first, then fallback to **Key:** patterns) ---

    # Fill meta from frontmatter
    if fm.get('pax'):
        data["meta"]["base"] = f"{fm['pax']} PAX"
    elif fm.get('tipo'):
        data["meta"]["base"] = fm['tipo']
    if fm.get('pax'):
        data["meta"]["rendimiento"] = f"{fm['pax']} pax"
    if fm.get('tiempo_activo'):
        data["meta"]["mise_en_place"] = fm.get('tiempo_activo', '')
    if fm.get('tiempo_total'):
        data["meta"]["tiempo_total"] = fm.get('tiempo_total', '')
    if fm.get('tecnica'):
        data["meta"]["tecnica"] = fm['tecnica']
    elif fm.get('dificultad') and not data["meta"]["tecnica"]:
        data["meta"]["tecnica"] = f"Dificultad: {fm['dificultad']}"
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

    # Second fallback: unbolded "Key: Value" patterns (legacy format)
    if not data["meta"]["base"]:
        m = re.search(r'(?:^|\n)Base:\s*(.+?)(?:\s+Rendimiento:|\s+Raci|\n)', meta_text)
        if m: data["meta"]["base"] = m.group(1).strip()
    if not data["meta"]["rendimiento"]:
        m = re.search(r'Rendimiento:\s*(.+?)(?:\n|$)', meta_text)
        if m: data["meta"]["rendimiento"] = m.group(1).strip()
    if not data["meta"]["tiempo_total"]:
        m = re.search(r'Tiempo\s+[Tt]otal:\s*(.+?)(?:\*\*|\n|$)', meta_text)
        if m: data["meta"]["tiempo_total"] = m.group(1).strip()
    if not data["meta"]["mise_en_place"]:
        m = re.search(r'Mise\s+[Ee]n\s+[Pp]lace:\s*(.+?)(?:\s+Tiempo|\*\*|\n|$)', meta_text)
        if m: data["meta"]["mise_en_place"] = m.group(1).strip()
    if not data["meta"]["tecnica"]:
        m = re.search(r'T[eé]cnica:\s*(.+?)(?:\s*·|\s*\n|$)', meta_text)
        if m: data["meta"]["tecnica"] = m.group(1).strip()
    if not data["meta"]["conservacion"]:
        m = re.search(r'Conservaci[oó]n:\s*(.+?)(?:\n|$)', meta_text)
        if m: data["meta"]["conservacion"] = m.group(1).strip()

    # --- ADAPTACIÓN SENIOR (narrative paragraph) ---
    senior_m = re.search(
        r'#{2,3}\s*(?:Adaptaci[oó]n\s+Senior|ADAPTACI[OÓ]N\s+SENIOR)\s*\n+(.+?)(?=\n---|\n#{2,3}\s|\Z)',
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
            el = el.strip()
            # Numbered: "1. Step"
            m = re.match(r'^\d+\.\s+(.+)', el)
            if m:
                step = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(1))
                empl_steps.append(step.strip())
                continue
            # Bullet: "- Step"
            m = re.match(r'^-\s+(.+)', el)
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

            if any(s in header_lower for s in ['ingrediente']) and not re.search(r'fase\s*\d|preparaci|mise', header_lower):
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
            # Numbered step: "1. Do something"
            m_step = re.match(r'^\d+\.\s*(.+)', stripped)
            if m_step:
                step = m_step.group(1).strip()
                step = re.sub(r'\*\*(.+?)\*\*', r'\1', step)
                current_fase["steps"].append(step)
            # Unnumbered step: plain text line (Straker format)
            elif stripped and not stripped.startswith('|') and not stripped.startswith('-') and not stripped.startswith('*') and not stripped.startswith('>'):
                step = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
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

            # Ingredient line (table format)
            # Supports both 3-col (Ingrediente|Cantidad|Notas) and 4-col (Ingrediente|Cantidad|Unidad|Notas)
            if stripped.startswith('|') and stripped.endswith('|'):
                cols = [c.strip() for c in stripped.split('|')[1:-1]]  # skip empty first/last
                if len(cols) >= 2:
                    nombre_t = cols[0]
                    # Skip header rows and separator rows
                    if nombre_t.lower() in ('ingrediente', '---', '', 'nombre'):
                        continue
                    if re.match(r'^[-|:\s]+$', nombre_t):
                        continue

                    cantidad_t = cols[1]
                    # Detect 4-column format: col[2] looks like a unit (g, kg, ml, etc.)
                    unit_pattern = re.compile(r'^(g|kg|ml|l|cl|dl|uds?|unidades?|dientes|hojas|piezas|latas?|cucharadas?|cucharaditas?|cs|cc|c/s|c/n|puntas?|hogazas?|manojos?|manojo|ramas?|ramitas?|rebanadas?|filetes?|botes?|tiras?|rodajas?|pellizcos?|sobres?|tallos?|pizca|-)$', re.IGNORECASE)
                    if len(cols) >= 3 and unit_pattern.match(cols[2]):
                        # 4-col: merge cantidad + unidad (avoid duplication)
                        unit = cols[2]
                        # Don't append if cantidad already ends with a unit (e.g. "4 kg" + "g")
                        has_unit = re.search(r'(?:^|\s)(g|kg|ml|l|cl|dl|uds?|dientes|hojas|piezas)\s*$', cantidad_t, re.IGNORECASE)
                        if unit != '-' and not has_unit:
                            cantidad_t = f"{cantidad_t} {unit}"
                        extra = [c for c in cols[3:] if c and c != '—' and c != '-' and not re.match(r'^[-:\s]+$', c)]
                    else:
                        # 3-col or 2-col: remaining cols are notes
                        extra = [c for c in cols[2:] if c and c != '—' and c != '-' and not re.match(r'^[-:\s]+$', c)]

                    nota_t = ', '.join(extra) if extra else None
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

    # --- PLATO ENSAMBLADO FALLBACK ---
    # If no ingredientes found, try ## Componentes del Plato table
    has_ing = any(g.get("items") for g in data["ingredientes"])
    if not has_ing:
        comp_tbl_m = re.search(
            r'##\s*Componentes\s+del\s+[Pp]lato\s*\n(.+?)(?=\n##[^#]|\Z)',
            text, re.DOTALL
        )
        if comp_tbl_m:
            comp_group = {"grupo": "Componentes", "items": []}
            for tline in comp_tbl_m.group(1).strip().split('\n'):
                tline = tline.strip()
                if not tline.startswith('|') or not tline.endswith('|'):
                    continue
                tcols = [c.strip() for c in tline.split('|')[1:-1]]
                if len(tcols) >= 2:
                    nombre_c = tcols[0]
                    if nombre_c.lower() in ('componente', '---', '', 'nombre'):
                        continue
                    if re.match(r'^[-|:\s]+$', nombre_c):
                        continue
                    tipo_c = tcols[1] if len(tcols) >= 2 else ''
                    comp_group["items"].append({"nombre": nombre_c, "cantidad": tipo_c})
            if comp_group["items"]:
                data["ingredientes"].append(comp_group)

    # If no fases found, try plato-specific sections
    if not data["fases"]:
        for section_re, section_name in [
            (r'##\s*Ensamblaje\s+y\s+Emplatado\s*\n(.+?)(?=\n##[^#]|\Z)', 'Ensamblaje y Emplatado'),
            (r'##\s*Mise\s+en\s+Place\s*(?:--[^\n]*)?\s*\n(.+?)(?=\n##[^#]|\Z)', 'Mise en Place'),
            (r'##\s*Servicio\s*(?:--[^\n]*)?\s*\n(.+?)(?=\n##[^#]|\Z)', 'Servicio'),
            (r'##\s*Timing\s+de\s+Servicio\s*\n(.+?)(?=\n##[^#]|\Z)', 'Timing de Servicio'),
        ]:
            sec_m = re.search(section_re, text, re.DOTALL | re.IGNORECASE)
            if sec_m:
                steps = []
                for sline in sec_m.group(1).strip().split('\n'):
                    sline = sline.strip()
                    step_m = re.match(r'^\d+\.\s*(.+)', sline)
                    if step_m:
                        steps.append(re.sub(r'\*\*(.+?)\*\*', r'\1', step_m.group(1).strip()))
                    elif sline.startswith('- '):
                        steps.append(re.sub(r'\*\*(.+?)\*\*', r'\1', sline[2:].strip()))
                if steps:
                    data["fases"].append({"title": section_name, "steps": steps})

    # --- LEGACY FALLBACK: extract ingredients from scattered "- Name: Qty" / "• Name: Qty" ---
    has_ing_now = any(g.get("items") for g in data["ingredientes"])
    if not has_ing_now:
        legacy_group = {"grupo": "General", "items": []}
        for line in lines:
            stripped = line.strip()
            # Match "- Name: Qty" or "-Name: Qty" or "• Name: Qty" patterns (legacy two-column format)
            m_leg = re.match(r'^[-•]\s*(.+?):\s+(.+)', stripped)
            if m_leg:
                nombre_l = m_leg.group(1).strip()
                cantidad_l = m_leg.group(2).strip()
                # Skip lines that are clearly not ingredients
                if any(s in nombre_l.lower() for s in ['appcc', 'alérgeno', 'punto']):
                    continue
                legacy_group["items"].append({"nombre": nombre_l, "cantidad": cantidad_l})
        if legacy_group["items"]:
            data["ingredientes"].append(legacy_group)

    # --- LEGACY FALLBACK: extract fases from ALL-CAPS section headers ---
    if len(data["fases"]) < 2:
        existing_fases = data["fases"][:]  # preserve for fallback
        legacy_fases = []
        legacy_fase = None
        for line in lines:
            stripped = line.strip()
            # Skip markdown headings (already handled) and known sections
            if stripped.startswith('#'):
                continue
            # ALL-CAPS section header like "ASADO VERDURAS (20–25 min)" — may have trailing text from two-column
            caps_m = re.match(r'^([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ\s]{4,}\(.+?\))', stripped)
            if caps_m:
                header_text = caps_m.group(1).strip()
                # Skip known non-fase headers
                if any(s in header_text.upper() for s in ['APPCC', 'PUNTOS CR', 'ALÉRGENO']):
                    continue
                if legacy_fase and legacy_fase["steps"]:
                    legacy_fases.append(legacy_fase)
                legacy_fase = {"title": header_text, "steps": []}
                continue
            # Bold section header like **Verduras**
            bold_m = re.match(r'^\*\*(.+?)\*\*\s*$', stripped)
            if bold_m and legacy_fase is None and not stripped.startswith('**Tipo') and not stripped.startswith('**Fuente'):
                header_text = bold_m.group(1).strip()
                if any(s in header_text.lower() for s in ['mise en place', 'verduras']):
                    legacy_fase = {"title": header_text, "steps": []}
                    continue
            # Numbered step (legacy format: "1.Step text")
            if legacy_fase is not None:
                step_m = re.match(r'^(\d+)\.\s*(.+)', stripped)
                if step_m:
                    step_text = step_m.group(2).strip()
                    step_text = re.sub(r'\*\*(.+?)\*\*', r'\1', step_text)
                    legacy_fase["steps"].append(step_text)
        if legacy_fase and legacy_fase["steps"]:
            legacy_fases.append(legacy_fase)
        # Use legacy fases if they have more coverage than existing
        if len(legacy_fases) >= 2:
            data["fases"] = legacy_fases
        elif legacy_fases and not existing_fases:
            data["fases"] = legacy_fases

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
