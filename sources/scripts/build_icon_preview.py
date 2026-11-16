#!/usr/bin/env python3
"""Regenerate the icon preview images shown in icons/README.md.

    pip install pillow
    python3 sources/scripts/build_icon_preview.py

Reads icons/solid/*.png and icons/transparent/*.png (same file names, sorted)
and writes icons/preview-solid.png and icons/preview-transparent.png: a grid
of all icons on a transparent background, so the previews look right in both
light and dark mode. Run it after adding or changing icons.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "icons"
CELL, GAP, COLS = 96, 16, 8


def build(style: str) -> Path:
    files = sorted((ICONS / style).glob("*.png"))
    rows = (len(files) + COLS - 1) // COLS
    sheet = Image.new("RGBA", (COLS * CELL + (COLS - 1) * GAP, rows * CELL + (rows - 1) * GAP), (0, 0, 0, 0))
    for i, f in enumerate(files):
        icon = Image.open(f).convert("RGBA").resize((CELL, CELL), Image.LANCZOS)
        sheet.alpha_composite(icon, ((i % COLS) * (CELL + GAP), (i // COLS) * (CELL + GAP)))
    out = ICONS / f"preview-{style}.png"
    sheet.save(out, optimize=True)
    return out


if __name__ == "__main__":
    for style in ("solid", "transparent"):
        p = build(style)
        print(f"{p.relative_to(ROOT)}  {p.stat().st_size // 1024} KB")
