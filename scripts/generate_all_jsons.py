#!/usr/bin/env python3
"""
generate_all_jsons.py
Reads ALL recipe .md files from vault Recetas/ and generates JSONs for the HTML catalog.
For platos ensamblados: merges content from the principal component into the plato JSON,
so the web shows the full recipe (ingredients, procedure) not just the assembly shell.

Usage: python3 generate_all_jsons.py
"""
import os, json, re, sys

VAULT = os.path.expanduser(
    "~/Global Nomads Dropbox/Mike Meeger/2026/techila/AI/SECOND_BRAIN/VAULT - TRABAJO/TRABAJO"
)
RECETAS = os.path.join(VAULT, "COCKPIT/ATTENYA/Restaurante/Culinario/Recetas")
OUTPUT = os.path.expanduser(
    "~/Global Nomads Dropbox/Mike Meeger/2026/ATTENYA/attenya-recetas/data"
)
os.makedirs(OUTPUT, exist_ok=True)

# ── Parsing helpers ──────────────────────────────────────────

def parse_fm(text):
    fm = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            for line in text[3:end].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
    return fm

def after_frontmatter(text):
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            return text[end+3:].strip()
    return text

def extract(text, headings):
    """Extract content under a ## heading (or ### as fallback)."""
    for h in headings:
        pat = rf"^##\s+{re.escape(h)}.*?\n(.*?)(?=\n##\s|\Z)"
        m = re.search(pat, text, re.DOTALL | re.MULTILINE)
        if m:
            return m.group(1).strip()
    for h in headings:
        pat = rf"^###\s+{re.escape(h)}.*?\n(.*?)(?=\n###\s|\n##\s|\Z)"
        m = re.search(pat, text, re.DOTALL | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None

def extract_quote(text):
    m = re.search(r'\*"([^"]+)"\*\s*$', text)
    if m: return m.group(1)
    m = re.search(r'\u00AB(.+?)\u00BB\s*$', text)
    if m: return m.group(1)
    m = re.search(r'\u201C(.+?)\u201D\s*$', text)
    if m: return m.group(1)
    m = re.search(r'\*([^*]{20,})\*\s*$', text)
    if m: return m.group(1)
    return None

def is_recipe_md(filepath, filename):
    if filename.startswith('_'):
        return False
    if '_storytelling' in filename or '_prompt' in filename:
        return False
    if filename in ('Soul.md', '_index.md'):
        return False
    return True

def find_storytelling(recipe_dir, recipe_id):
    for suffix in ("_storytelling.md", "_Storytelling.md"):
        c = os.path.join(recipe_dir, recipe_id + suffix)
        if os.path.exists(c):
            with open(c, "r", encoding="utf-8") as f:
                return f.read().strip()
    return None

def parse_componentes_yaml(raw):
    """Parse componentes list from frontmatter YAML."""
    comps = []
    if not raw.startswith("---"):
        return comps
    fm_block = raw[3:raw.find("---", 3)]
    in_comps = False
    for line in fm_block.split("\n"):
        stripped = line.strip()
        if stripped.startswith("componentes:"):
            if "[]" in stripped:
                return comps
            in_comps = True
            continue
        if in_comps:
            if stripped.startswith("- "):
                part = stripped[2:].strip()
                if ":" in part:
                    role, cid = part.split(":", 1)
                    cid = cid.strip()
                    if cid and not cid.startswith("pendiente"):
                        comps.append({"role": role.strip(), "id": cid})
            elif not stripped.startswith("-") and stripped and not stripped.startswith("#"):
                in_comps = False
    return comps

# ── Component finder ─────────────────────────────────────────

_comp_cache = {}

def find_component_md(comp_id):
    """Find a component .md file anywhere under Recetas/ by its ID. Cached."""
    if comp_id in _comp_cache:
        return _comp_cache[comp_id]
    target = comp_id + ".md"
    for root, dirs, files in os.walk(RECETAS):
        if target in files:
            path = os.path.join(root, target)
            _comp_cache[comp_id] = path
            return path
    _comp_cache[comp_id] = None
    return None

HEADING_MAP = {
    "ingredients": ["Ingredientes", "Ingredients"],
    "procedure": [
        "Procedimiento", "Procedure",
        "MISE EN PLACE", "Mise en Place",
        "Elaboracion", "Elaboración"
    ],
    "plating": ["Emplatado", "Plating", "Uso en Plato", "USO EN PLATO"],
    "timing": ["Timing de Servicio", "Timing", "Timing de servicio"],
    "critical_points": [
        "Puntos Criticos", "Puntos Críticos",
        "PUNTOS CRITICOS", "PUNTOS CRÍTICOS",
        "Critical Points"
    ],
    "appcc": ["APPCC"],
    "senior_adaptation": [
        "Adaptacion Senior", "Adaptación Senior",
        "ADAPTACION SENIOR", "ADAPTACIÓN SENIOR"
    ],
}

HEADING_MAP_PLATO = {
    "ingredients": [
        "Ingredientes", "Ingredients"
    ],
    "procedure": [
        "Procedimiento", "Procedure",
        "MISE EN PLACE", "Mise en Place",
        "Elaboracion", "Elaboración",
        "Ensamblaje y Emplatado", "Ensamblaje", "Montaje"
    ],
    "plating": ["Emplatado", "Plating", "Uso en Plato", "USO EN PLATO"],
    "timing": ["Timing de Servicio", "Timing", "Timing de servicio"],
    "critical_points": HEADING_MAP["critical_points"],
    "appcc": HEADING_MAP["appcc"],
    "senior_adaptation": HEADING_MAP["senior_adaptation"],
}

def extract_fields(body, heading_map):
    return {k: extract(body, v) for k, v in heading_map.items()}

def extract_component(comp_id):
    """Read and extract all fields from a component .md."""
    path = find_component_md(comp_id)
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    fm = parse_fm(raw)
    body = after_frontmatter(raw)
    recipe_dir = os.path.dirname(path)

    fields = extract_fields(body, HEADING_MAP)
    fields["nombre"] = fm.get("nombre", fm.get("nombre_original", ""))
    fields["fuente"] = fm.get("fuente", "")
    fields["pax"] = fm.get("pax", fm.get("base", "25"))
    fields["time_total"] = fm.get("tiempo_total", fm.get("time_total", ""))
    fields["technique"] = fm.get("tecnica", fm.get("technique", ""))
    fields["protein"] = fm.get("proteina", fm.get("protein", ""))
    fields["difficulty"] = fm.get("dificultad", fm.get("difficulty", ""))
    fields["quote"] = extract_quote(raw)
    fields["storytelling"] = find_storytelling(recipe_dir, comp_id)
    return fields

# ── Main recipe processor ────────────────────────────────────

def process_recipe(md_path, recipe_dir, recipe_id):
    with open(md_path, "r", encoding="utf-8") as f:
        raw = f.read()
    fm = parse_fm(raw)
    body = after_frontmatter(raw)

    comps = parse_componentes_yaml(raw)
    fields = extract_fields(body, HEADING_MAP_PLATO)

    data = {
        "nombre": fm.get("nombre", fm.get("nombre_original", "")),
        "fuente": fm.get("fuente", ""),
        "pax": fm.get("pax", fm.get("base", "25")),
        "time_total": fm.get("tiempo_total", fm.get("time_total", "")),
        "technique": fm.get("tecnica", fm.get("technique", "")),
        "protein": fm.get("proteina", fm.get("protein", "")),
        "allergens": fm.get("alergenos", fm.get("allergens", "")),
        "difficulty": fm.get("dificultad", fm.get("difficulty", "")),
        **fields,
        "quote": extract_quote(raw),
        "storytelling": find_storytelling(recipe_dir, recipe_id),
    }

    if comps:
        data["componentes"] = comps

    # ── MERGE: For platos ensamblados, always pull content from principal component ──
    is_ensamblado = fm.get("subtipo", "").lower().startswith("plato ensamblado")
    principal_ids = [c["id"] for c in comps if c["role"] == "principal"] if comps else []
    needs_merge = is_ensamblado and principal_ids

    if needs_merge:
        principal_id = principal_ids[0]
        comp = extract_component(principal_id)

        if comp:
            # Save plato's own assembly procedure before overwriting
            plato_assembly = data.get("procedure")
            
            # 1. Ingredients: always from component (the real recipe)
            if comp.get("ingredients"):
                data["ingredients"] = comp["ingredients"]

            # 2. Procedure: component procedure + plato assembly
            parts = []
            if comp.get("procedure"):
                parts.append(comp["procedure"])
            if plato_assembly:
                parts.append("---\n\n### Ensamblaje y Emplatado\n\n" + plato_assembly)
            if parts:
                data["procedure"] = "\n\n".join(parts)

            # 3. Plating: prefer plato (assembly-specific), fallback component
            if not data.get("plating") and comp.get("plating"):
                data["plating"] = comp["plating"]

            # 4. Fill metadata gaps
            for field in ("technique", "protein", "time_total", "difficulty", "fuente"):
                if not data.get(field) and comp.get(field):
                    data[field] = comp[field]

            # 5. Fill content gaps
            for field in ("critical_points", "appcc", "senior_adaptation", "quote"):
                if not data.get(field) and comp.get(field):
                    data[field] = comp[field]

            data["_merged_from"] = principal_id
        else:
            print(f"  ⚠ {recipe_id}: component '{principal_id}' not found")

    return data

# ── Main ─────────────────────────────────────────────────────

def main():
    print(f"Scanning: {RECETAS}")
    print(f"Output:   {OUTPUT}")
    print()

    count = 0
    updated = 0
    skipped = 0
    merged = 0
    errors = []

    for root, dirs, files in os.walk(RECETAS):
        for f in files:
            if not f.endswith(".md"):
                continue
            if not is_recipe_md(os.path.join(root, f), f):
                continue

            recipe_id = f.replace(".md", "")
            md_path = os.path.join(root, f)
            json_path = os.path.join(OUTPUT, recipe_id + ".json")

            try:
                data = process_recipe(md_path, root, recipe_id)

                was_merged = "_merged_from" in data
                merged_from = data.pop("_merged_from", None)
                if was_merged:
                    merged += 1

                has_content = any([
                    data.get("ingredients"),
                    data.get("procedure"),
                    data.get("storytelling"),
                    data.get("componentes"),
                    data.get("timing"),
                    data.get("critical_points"),
                ])

                if has_content:
                    new_json = json.dumps(data, ensure_ascii=False, indent=2)

                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as jf:
                            existing = jf.read()
                        if existing.strip() == new_json.strip():
                            skipped += 1
                            continue
                        updated += 1

                    with open(json_path, "w", encoding="utf-8") as jf:
                        jf.write(new_json)

                    tag = f" [MERGED ← {merged_from}]" if was_merged else ""
                    print(f"  ✓ {recipe_id}{tag}")
                    count += 1
                else:
                    skipped += 1

            except Exception as e:
                print(f"  ✗ FAIL {recipe_id}: {e}")
                errors.append(recipe_id)

    print(f"\n{'='*60}")
    print(f"Generated/updated: {count} JSONs ({merged} merged from components)")
    print(f"Skipped (no change or no content): {skipped}")
    if errors:
        print(f"Errors ({len(errors)}): {', '.join(errors)}")
    print(f"Output: {OUTPUT}")

if __name__ == "__main__":
    main()
