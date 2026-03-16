#!/usr/bin/env python3
"""Regenerate ALL remaining PDFs not in _good/ — including platos, naming fixes, and parciales."""

import os, sys, glob, shutil, unicodedata

sys.path.insert(0, os.path.dirname(__file__))
from md_to_recipe_data import parse_benchmark_md
from generate_componente import generate_componente_pdf

REPO = "/Users/massaii/Global Nomads Dropbox/Mike Meeger/2026/ATTENYA/attenya-recetas"
VAULT = "/Users/massaii/Global Nomads Dropbox/Mike Meeger/2026/techila/AI/SECOND_BRAIN/VAULT - TRABAJO/TRABAJO/COCKPIT/ATTENYA/Restaurante/Culinario/Recetas"
GOOD_DIR = os.path.join(REPO, "_good")
REPAIRED_DIR = os.path.join(REPO, "_repaired")
DATA_DIR = os.path.join(REPO, "data")
IMG_DIR = os.path.join(REPO, "img")

os.makedirs(REPAIRED_DIR, exist_ok=True)

# IDs to regenerate
good_ids = set(f[:-4] for f in os.listdir(GOOD_DIR) if f.endswith('.pdf'))
all_ids = sorted(f[:-5] for f in os.listdir(DATA_DIR) if f.endswith('.json'))
to_regen = [rid for rid in all_ids if rid not in good_ids]

print(f"Total IDs: {len(all_ids)}, Buenos: {len(good_ids)}, A regenerar: {len(to_regen)}")

# Build vault .md index (including tilde variants)
vault_index = {}
for root, dirs, files in os.walk(VAULT):
    for f in files:
        if f.endswith('.md') and not f.endswith('_prompt.md') and not f.endswith('_storytelling.md'):
            name = f[:-3]
            vault_index[name] = os.path.join(root, f)
            # Also add normalized (no accents) version
            name_norm = unicodedata.normalize('NFD', name)
            name_norm = ''.join(c for c in name_norm if unicodedata.category(c) != 'Mn')
            if name_norm != name:
                vault_index[name_norm] = os.path.join(root, f)

# Special naming mappings
NAMING_MAP = {
    'Patatas_Fritas_Triple_Coccion': 'Patatas_Fritas_Triple_Cocción',
    'Risotto_Azafran_Plato': 'Risotto_Azafran',  # Use Platos/ version
}

def find_md(rid):
    # Direct match
    if rid in vault_index:
        return vault_index[rid]
    # Naming map
    mapped = NAMING_MAP.get(rid)
    if mapped and mapped in vault_index:
        return vault_index[mapped]
    # Try without _Plato suffix
    if rid.endswith('_Plato'):
        base = rid[:-6]
        if base in vault_index:
            return vault_index[base]
    return None

def find_image(rid):
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        p = os.path.join(IMG_DIR, rid + ext)
        if os.path.isfile(p):
            return p
        p = os.path.join(IMG_DIR, rid + '_AI' + ext)
        if os.path.isfile(p):
            return p
    # Try vault folder
    md_path = find_md(rid)
    if md_path:
        folder = os.path.dirname(md_path)
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            candidates = glob.glob(os.path.join(folder, f'*{ext}'))
            if candidates:
                return candidates[0]
    return None

ok = 0
fail = 0
manual = []

for rid in to_regen:
    md_path = find_md(rid)
    if not md_path:
        manual.append((rid, "No .md found"))
        fail += 1
        continue

    try:
        data = parse_benchmark_md(md_path)
    except Exception as e:
        manual.append((rid, f"Parse error: {e}"))
        fail += 1
        continue

    # Allow platos with componentes but no fases/ingredientes to still generate
    has_content = bool(data['fases']) or bool(data['ingredientes']) or bool(data.get('componentes_plato'))
    if not has_content:
        manual.append((rid, "No content (no fases, no ingredientes, no componentes)"))
        fail += 1
        continue

    img_path = find_image(rid)
    out_path = os.path.join(REPAIRED_DIR, rid + '.pdf')

    try:
        generate_componente_pdf(data, out_path, img_path)
        ok += 1
    except Exception as e:
        manual.append((rid, f"PDF error: {e}"))
        fail += 1

print(f"\nRegenerados: {ok}")
print(f"Fallidos: {fail}")
if manual:
    print(f"\nManuales ({len(manual)}):")
    for rid, reason in manual:
        print(f"  {rid}: {reason}")
