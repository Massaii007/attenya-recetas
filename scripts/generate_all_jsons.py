#!/usr/bin/env python3
"""
generate_all_jsons.py
Reads ALL recipe .md files from vault Recetas/ and generates JSONs for the HTML catalog.
Works for any recipe (Straker, Adrià, originals, new ones).

Usage: python3 generate_all_jsons.py
"""
import os, json, re

VAULT = os.path.expanduser(
    "~/Global Nomads Dropbox/Mike Meeger/2026/techila/AI/SECOND_BRAIN/VAULT - TRABAJO/TRABAJO"
)
RECETAS = os.path.join(VAULT, "COCKPIT/ATTENYA/Restaurante/Culinario/Recetas")
OUTPUT = os.path.expanduser("~/Desktop/attenya-recetas/data")
os.makedirs(OUTPUT, exist_ok=True)

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
    for h in headings:
        pat = rf"^##\s+{re.escape(h)}.*?\n(.*?)(?=\n##\s|\Z)"
        m = re.search(pat, text, re.DOTALL | re.MULTILINE)
        if m:
            return m.group(1).strip()
    # Also try ### headings for some older formats
    for h in headings:
        pat = rf"^###\s+{re.escape(h)}.*?\n(.*?)(?=\n###\s|\n##\s|\Z)"
        m = re.search(pat, text, re.DOTALL | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None

def extract_quote(text):
    m = re.search(r'\*"([^"]+)"\*\s*$', text)
    if m: return m.group(1)
    m = re.search(r'\u00AB(.+?)\u00BB\s*$', text)  # «...»
    if m: return m.group(1)
    m = re.search(r'\u201C(.+?)\u201D\s*$', text)  # "..."
    if m: return m.group(1)
    m = re.search(r'\*([^*]{20,})\*\s*$', text)
    if m: return m.group(1)
    return None

def is_recipe_md(filepath, filename):
    """Check if a .md file is a recipe (not storytelling, prompt, or index)."""
    if filename.startswith('_'):
        return False
    if '_storytelling' in filename or '_prompt' in filename:
        return False
    if filename == 'Soul.md' or filename == '_index.md':
        return False
    return True

def find_storytelling(recipe_dir, recipe_id):
    """Find storytelling file for a recipe."""
    candidates = [
        os.path.join(recipe_dir, recipe_id + "_storytelling.md"),
        os.path.join(recipe_dir, recipe_id + "_Storytelling.md"),
    ]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r", encoding="utf-8") as f:
                return f.read().strip()
    return None

def process_recipe(md_path, recipe_dir, recipe_id):
    with open(md_path, "r", encoding="utf-8") as f:
        raw = f.read()
    fm = parse_fm(raw)
    body = after_frontmatter(raw)
    
    data = {
        "nombre": fm.get("nombre", fm.get("nombre_original", "")),
        "fuente": fm.get("fuente", ""),
        "pax": fm.get("pax", fm.get("base", "25")),
        "time_total": fm.get("tiempo_total", fm.get("time_total", "")),
        "technique": fm.get("tecnica", fm.get("technique", "")),
        "protein": fm.get("proteina", fm.get("protein", "")),
        "allergens": fm.get("alergenos", fm.get("allergens", "")),
        "difficulty": fm.get("dificultad", fm.get("difficulty", "")),
        "ingredients": extract(body, ["Ingredientes", "Ingredients"]),
        "procedure": extract(body, [
            "Procedimiento", "Procedure",
            "MISE EN PLACE", "Mise en Place",
            "Elaboracion", u"Elaboraci\u00f3n"
        ]),
        "plating": extract(body, ["Emplatado", "Plating", "Uso en Plato", "USO EN PLATO"]),
        "critical_points": extract(body, [
            "Puntos Criticos", u"Puntos Cr\u00edticos",
            "PUNTOS CRITICOS", u"PUNTOS CR\u00cdTICOS",
            "Critical Points"
        ]),
        "appcc": extract(body, ["APPCC"]),
        "senior_adaptation": extract(body, [
            "Adaptacion Senior", u"Adaptaci\u00f3n Senior",
            "ADAPTACION SENIOR", u"ADAPTACI\u00d3N SENIOR"
        ]),
        "quote": extract_quote(raw),
        "storytelling": find_storytelling(recipe_dir, recipe_id),
    }
    
    # If no procedure found with ## headings, try to get everything after ingredients
    if not data["procedure"] and data["ingredients"]:
        # Grab the full body after frontmatter as procedure fallback
        pass
    
    return data

def main():
    print(f"Scanning: {RECETAS}")
    count = 0
    updated = 0
    skipped = 0
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
                
                # Only write if we have meaningful content
                has_content = any([
                    data["ingredients"],
                    data["procedure"],
                    data["storytelling"]
                ])
                
                if has_content:
                    # Check if JSON already exists and is identical
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as jf:
                            existing = jf.read()
                        new_json = json.dumps(data, ensure_ascii=False, indent=2)
                        if existing.strip() == new_json.strip():
                            skipped += 1
                            continue
                        updated += 1
                    
                    with open(json_path, "w", encoding="utf-8") as jf:
                        json.dump(data, jf, ensure_ascii=False, indent=2)
                    print(f"  ok {recipe_id}")
                    count += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"  FAIL {recipe_id}: {e}")
                errors.append(recipe_id)
    
    print(f"\n{'='*50}")
    print(f"Generated/updated: {count} JSONs")
    print(f"Skipped (no change or no content): {skipped}")
    if errors:
        print(f"Errors ({len(errors)}): {', '.join(errors)}")
    print(f"Output: {OUTPUT}")

if __name__ == "__main__":
    main()
