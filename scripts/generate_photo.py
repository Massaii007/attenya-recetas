#!/usr/bin/env python3
"""
generate_photo.py
Reads a recipe's _prompt.md from vault, calls Imagen 3 API, saves photo to recipe folder.
Fully autonomous — no browser, no permissions needed.

Usage:
  python3 generate_photo.py Bacalao_Tomate_Pimientos_Straker
  python3 generate_photo.py --all          # generates for ALL recipes missing photos
  python3 generate_photo.py --list         # lists recipes with prompts but no photo

Setup:
  1. pip install google-genai python-dotenv
  2. Create .env file with: GEMINI_API_KEY=your_api_key_here
  3. Get API key from https://aistudio.google.com/apikey

Cost: $0.03 per image
"""
import os, sys, glob
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

VAULT = Path(os.path.expanduser(
    "~/Global Nomads Dropbox/Mike Meeger/2026/techila/AI/SECOND_BRAIN/VAULT - TRABAJO/TRABAJO"
))
RECETAS = VAULT / "COCKPIT/ATTENYA/Restaurante/Culinario/Recetas"

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "imagen-4.0-generate-001"

def find_recipe_dir(recipe_id):
    """Find the recipe folder by id anywhere under Recetas/."""
    for root, dirs, files in os.walk(RECETAS):
        if os.path.basename(root) == recipe_id:
            return Path(root)
    return None

def read_prompt(recipe_dir, recipe_id):
    """Read the _prompt.md file and extract the prompt text."""
    prompt_file = recipe_dir / f"{recipe_id}_prompt.md"
    if not prompt_file.exists():
        return None
    
    text = prompt_file.read_text(encoding="utf-8")
    
    # Extract the prompt section (after ## Prompt or the main content)
    lines = text.split("\n")
    prompt_lines = []
    in_prompt = False
    in_notes = False
    
    for line in lines:
        if line.strip().startswith("## Prompt"):
            in_prompt = True
            continue
        if line.strip().startswith("## Notas") or line.strip().startswith("## Notes"):
            in_notes = True
            in_prompt = False
            continue
        if in_prompt and not in_notes:
            prompt_lines.append(line)
    
    # If no ## Prompt section found, use everything after the title
    if not prompt_lines:
        skip_header = True
        for line in lines:
            if skip_header and (line.startswith("#") or line.startswith("---") or not line.strip()):
                if line.startswith("## Estilo") or line.startswith("## Style"):
                    skip_header = False
                continue
            skip_header = False
            if line.strip().startswith("## Notas") or line.strip().startswith("## Notes"):
                break
            prompt_lines.append(line)
    
    prompt = "\n".join(prompt_lines).strip()
    
    # Ensure it starts with "Square format 1000x1000px" if not already
    if prompt and not prompt.startswith("Square format"):
        prompt = "Square format 1000x1000px. " + prompt
    
    return prompt if prompt else None

def has_photo(recipe_dir, recipe_id):
    """Check if recipe already has any photo (AI or otherwise)."""
    for ext in [".jpg", ".jpeg", ".png"]:
        # Check _AI naming first
        if (recipe_dir / f"{recipe_id}_AI{ext}").exists():
            return True
        # Also check plain naming (e.g. Tiramisu_Straker.jpg)
        if (recipe_dir / f"{recipe_id}{ext}").exists():
            return True
    return False

def generate_image(prompt, output_path):
    """Call Imagen API and save the image."""
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=API_KEY)
    
    result = client.models.generate_images(
        model=MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio="1:1",
        )
    )
    
    if result.generated_images:
        result.generated_images[0].image.save(str(output_path))
        return True
    return False

def list_missing():
    """List recipes that have prompt but no photo."""
    missing = []
    for root, dirs, files in os.walk(RECETAS):
        recipe_id = os.path.basename(root)
        recipe_dir = Path(root)
        prompt_file = recipe_dir / f"{recipe_id}_prompt.md"
        if prompt_file.exists() and not has_photo(recipe_dir, recipe_id):
            missing.append(recipe_id)
    return missing

def process_recipe(recipe_id, force=False):
    """Process a single recipe: read prompt, generate photo, save."""
    recipe_dir = find_recipe_dir(recipe_id)
    if not recipe_dir:
        print(f"  ✗ Recipe folder not found: {recipe_id}")
        return False
    
    if not force and has_photo(recipe_dir, recipe_id):
        print(f"  → Photo already exists: {recipe_id}")
        return True
    
    prompt = read_prompt(recipe_dir, recipe_id)
    if not prompt:
        print(f"  ✗ No prompt found: {recipe_id}")
        return False
    
    output_path = recipe_dir / f"{recipe_id}_AI.jpg"
    print(f"  ⟳ Generating: {recipe_id}...")
    
    try:
        success = generate_image(prompt, output_path)
        if success:
            print(f"  ✓ Saved: {output_path.name}")
            return True
        else:
            print(f"  ✗ No image returned: {recipe_id}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {recipe_id} — {e}")
        return False

def main():
    if not API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        print("Create a .env file with: GEMINI_API_KEY=your_key")
        print("Get key from: https://aistudio.google.com/apikey")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 generate_photo.py Recipe_Id          # single recipe")
        print("  python3 generate_photo.py --all              # all missing photos")
        print("  python3 generate_photo.py --list             # list recipes needing photos")
        print("  python3 generate_photo.py --force Recipe_Id  # regenerate even if exists")
        sys.exit(0)
    
    arg = sys.argv[1]
    
    if arg == "--list":
        missing = list_missing()
        print(f"Recipes with prompt but no photo: {len(missing)}")
        for r in sorted(missing):
            print(f"  • {r}")
        return
    
    if arg == "--all":
        missing = list_missing()
        print(f"Generating photos for {len(missing)} recipes...")
        ok = 0
        fail = 0
        for r in sorted(missing):
            if process_recipe(r):
                ok += 1
            else:
                fail += 1
        print(f"\nDone. Generated: {ok}, Failed: {fail}")
        print(f"Cost: ~${ok * 0.03:.2f}")
        return
    
    force = False
    recipe_id = arg
    if arg == "--force" and len(sys.argv) > 2:
        force = True
        recipe_id = sys.argv[2]
    
    process_recipe(recipe_id, force=force)

if __name__ == "__main__":
    main()
