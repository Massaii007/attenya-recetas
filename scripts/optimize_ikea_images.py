#!/usr/bin/env python3
"""
optimize_ikea_images.py
Resize + recompress img_ikea/*.jpeg para tablet cocina (carga rápida).

Default: 600×600, JPEG quality 70, optimize=True.
In-place (sobreescribe los originales).
"""
import sys
from pathlib import Path
from PIL import Image

REPO    = Path(__file__).resolve().parent.parent
IMG_DIR = REPO / "img_ikea"
SIZE    = 600
QUALITY = 70


def optimize_one(path: Path) -> tuple[int, int]:
    """Devuelve (bytes_antes, bytes_despues)."""
    before = path.stat().st_size
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((SIZE, SIZE), Image.LANCZOS)
    img.save(path, "JPEG", quality=QUALITY, optimize=True)
    after = path.stat().st_size
    return (before, after)


def main():
    files = sorted(IMG_DIR.glob("*.jpeg"))
    if not files:
        print("No images found.")
        sys.exit(0)
    total_b = total_a = 0
    for f in files:
        b, a = optimize_one(f)
        total_b += b
        total_a += a
        print(f"  ✓ {f.name}: {b//1024} KB → {a//1024} KB ({100*(b-a)//b}% off)")
    print(f"\n=== Total: {total_b//1024} KB → {total_a//1024} KB ({100*(total_b-total_a)//total_b}% reducción) ===")


if __name__ == "__main__":
    main()
