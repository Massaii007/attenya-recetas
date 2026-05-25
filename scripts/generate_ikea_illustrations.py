#!/usr/bin/env python3
"""
generate_ikea_illustrations.py
Itera data_ikea/*.json · para cada step genera line-art con Imagen 4.0.
Guarda en img_ikea/<recipe_id>_step{n:02d}.jpeg.
Idempotente: skip si la imagen ya existe.

Uso:
  python3 scripts/generate_ikea_illustrations.py <recipe_id>
  python3 scripts/generate_ikea_illustrations.py --all
  python3 scripts/generate_ikea_illustrations.py --list
  python3 scripts/generate_ikea_illustrations.py --step <recipe_id> <step_n>   # solo un paso (regen)

Coste: $0.03/imagen · quota Imagen 4.0 70/día.
"""
import json, os, sys, time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REPO     = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data_ikea"
IMG_DIR  = REPO / "img_ikea"
IMG_DIR.mkdir(exist_ok=True)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL   = "imagen-4.0-generate-001"


def build_prompt(step: dict, element_label: str) -> str:
    """Construye prompt line-art coloring book desde title + element."""
    title = step["title"]
    return (
        "minimalist black ink line drawing on white background, "
        "coloring book style, simple thick clean outlines, "
        f"a kitchen still life scene illustrating: {title}. "
        f"Context element: {element_label.lower()}. "
        "Food preparation scene, kitchen utensils and ingredients visible, "
        "no shading, no color fills, only black outlines on white. "
        "Square 1:1 aspect ratio.\n\n"
        "ABSOLUTELY NO TEXT, no words, no letters, no labels, no numbers, "
        "no captions, no callouts, no arrows, no annotations. "
        "No human figures, no faces, no people, no hands, no clothing."
    )


def generate_one(client, prompt: str, out_path: Path) -> bool:
    from google.genai import types
    result = client.models.generate_images(
        model=MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio="1:1",
        ),
    )
    if result.generated_images:
        result.generated_images[0].image.save(str(out_path))
        return True
    return False


def process_recipe(recipe_id: str, only_step: int | None = None) -> tuple[int, int]:
    """Devuelve (ok, fail)."""
    src = DATA_DIR / f"{recipe_id}.json"
    if not src.exists():
        print(f"  ✗ JSON no encontrado: {recipe_id}")
        return (0, 0)

    data = json.loads(src.read_text(encoding="utf-8"))
    e_lookup = {e["key"]: e for e in data["elements"]}

    from google import genai
    client = genai.Client(api_key=API_KEY)

    ok = fail = 0
    for s in data["steps"]:
        if only_step is not None and s["n"] != only_step:
            continue
        out = IMG_DIR / f"{recipe_id}_step{s['n']:02d}.jpeg"
        if out.exists() and only_step is None:
            print(f"  → existe, skip: {out.name}")
            ok += 1
            continue

        elt = e_lookup[s["element"]]
        prompt = build_prompt(s, elt["label"])
        print(f"  ⟳ {recipe_id} · step {s['n']:02d} · {s['title']}")
        try:
            success = generate_one(client, prompt, out)
            if success:
                print(f"     ✓ {out.name} ({out.stat().st_size//1024} KB)")
                ok += 1
            else:
                print(f"     ✗ no image returned")
                fail += 1
        except Exception as e:
            print(f"     ✗ error: {e}")
            fail += 1
            # Si la quota se agota, parar
            if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                print("\n⚠ Quota agotada · parando batch.")
                return (ok, fail)

        # Throttle ligero
        time.sleep(1.0)

    return (ok, fail)


def main():
    if not API_KEY:
        print("ERROR: GEMINI_API_KEY no definido. Revisar ~/.env")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    arg = sys.argv[1]

    if arg == "--list":
        for f in sorted(DATA_DIR.glob("*.json")):
            print(f"  • {f.stem}")
        return

    if arg == "--all":
        total_ok = total_fail = 0
        for f in sorted(DATA_DIR.glob("*.json")):
            print(f"\n=== {f.stem} ===")
            ok, fail = process_recipe(f.stem)
            total_ok  += ok
            total_fail += fail
        print(f"\n========================")
        print(f"Done · generated: {total_ok} · failed: {total_fail}")
        print(f"Estimated cost: ~${total_ok * 0.03:.2f}")
        return

    if arg == "--step":
        recipe_id = sys.argv[2]
        step_n    = int(sys.argv[3])
        process_recipe(recipe_id, only_step=step_n)
        return

    # default: single recipe
    process_recipe(arg)


if __name__ == "__main__":
    main()
