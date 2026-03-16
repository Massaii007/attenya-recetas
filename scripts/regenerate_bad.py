#!/usr/bin/env python3
"""Regenerate only the 160 bad PDFs (those NOT in _good/)."""

import os, sys, subprocess, glob

sys.path.insert(0, os.path.dirname(__file__))
from md_to_recipe_data import parse_benchmark_md
from generate_componente import generate_componente_pdf

REPO = "/Users/massaii/Global Nomads Dropbox/Mike Meeger/2026/ATTENYA/attenya-recetas"
VAULT_RECETAS = "/Users/massaii/Global Nomads Dropbox/Mike Meeger/2026/techila/AI/SECOND_BRAIN/VAULT - TRABAJO/TRABAJO/COCKPIT/ATTENYA/Restaurante/Culinario/Recetas"
GOOD_DIR = os.path.join(REPO, "_good")
REPAIRED_DIR = os.path.join(REPO, "_repaired")
DATA_DIR = os.path.join(REPO, "data")
IMG_DIR = os.path.join(REPO, "img")

os.makedirs(REPAIRED_DIR, exist_ok=True)

# IDs to regenerate: all JSONs minus those already in _good/
good_ids = set(f[:-4] for f in os.listdir(GOOD_DIR) if f.endswith('.pdf'))
all_ids = sorted(f[:-5] for f in os.listdir(DATA_DIR) if f.endswith('.json'))
to_regen = [rid for rid in all_ids if rid not in good_ids]

print(f"Total IDs: {len(all_ids)}, Buenos: {len(good_ids)}, A regenerar: {len(to_regen)}")

# Build vault .md index
vault_index = {}
for root, dirs, files in os.walk(VAULT_RECETAS):
    for f in files:
        if f.endswith('.md'):
            name = f[:-3]
            vault_index[name] = os.path.join(root, f)

# Find image for a recipe
def find_image(rid):
    # Try img/ directory first
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        p = os.path.join(IMG_DIR, rid + ext)
        if os.path.isfile(p):
            return p
    # Try {id}_AI.jpg
    p = os.path.join(IMG_DIR, rid + '_AI.jpg')
    if os.path.isfile(p):
        return p
    # Try vault folder
    if rid in vault_index:
        folder = os.path.dirname(vault_index[rid])
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            candidates = glob.glob(os.path.join(folder, f'*{ext}'))
            if candidates:
                return candidates[0]
    return None

# Regenerate
ok = 0
fail = 0
manual = []

for rid in to_regen:
    if rid not in vault_index:
        manual.append((rid, "No .md in vault"))
        fail += 1
        continue

    md_path = vault_index[rid]
    try:
        data = parse_benchmark_md(md_path)
    except Exception as e:
        manual.append((rid, f"Parse error: {e}"))
        fail += 1
        continue

    # Skip if no fases AND no ingredientes (likely a prompt/storytelling file, not a recipe)
    if not data['fases'] and not data['ingredientes']:
        manual.append((rid, "No fases + no ingredientes (non-recipe .md?)"))
        fail += 1
        continue

    img_path = find_image(rid)
    out_path = os.path.join(REPAIRED_DIR, rid + '.pdf')

    try:
        generate_componente_pdf(data, out_path, img_path)
        ok += 1
    except Exception as e:
        manual.append((rid, f"PDF generation error: {e}"))
        fail += 1

print(f"\nRegenerados: {ok}")
print(f"Fallidos: {fail}")
if manual:
    print(f"\nManuales ({len(manual)}):")
    for rid, reason in manual:
        print(f"  {rid}: {reason}")
