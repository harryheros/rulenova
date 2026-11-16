#!/usr/bin/env python3
"""Checks for icons/ (standard library only).

    python3 sources/scripts/test_icons.py

- icons/solid and icons/transparent contain exactly the same file names
- names are lowercase kebab-case .png
- every file is a valid PNG, 108x108, 8-bit RGBA
- the preview images exist and every icon appears in icons/README.md
- every local path referenced in icons/README.md exists (case-sensitive)
"""
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "icons"
SIZE = 108
STYLES = ("solid", "transparent")
errors = []


def png_header(path: Path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None, "not a PNG file"
    length, ctype = struct.unpack(">I4s", data[8:16])
    if ctype != b"IHDR" or length != 13:
        return None, "missing IHDR"
    ihdr = data[16:29]
    if zlib.crc32(data[12:29]) & 0xFFFFFFFF != struct.unpack(">I", data[29:33])[0]:
        return None, "corrupt IHDR"
    if b"IEND" not in data[-12:]:
        return None, "truncated (no IEND)"
    w, h, depth, color = struct.unpack(">IIBB", ihdr[:10])
    return (w, h, depth, color), None


names = {}
for style in STYLES:
    folder = ICONS / style
    if not folder.is_dir():
        errors.append(f"icons/{style}/ is missing")
        names[style] = set()
        continue
    names[style] = {p.name for p in folder.iterdir() if not p.name.startswith(".")}
    for name in sorted(names[style]):
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*\.png", name):
            errors.append(f"icons/{style}/{name}: name must be lowercase kebab-case .png")
            continue
        info, err = png_header(folder / name)
        if err:
            errors.append(f"icons/{style}/{name}: {err}")
        elif info != (SIZE, SIZE, 8, 6):
            errors.append(f"icons/{style}/{name}: expected {SIZE}x{SIZE} 8-bit RGBA, got {info[0]}x{info[1]} depth {info[2]} colour type {info[3]}")

a, b = names.get("solid", set()), names.get("transparent", set())
for n in sorted(a - b):
    errors.append(f"{n} exists in solid/ but not in transparent/")
for n in sorted(b - a):
    errors.append(f"{n} exists in transparent/ but not in solid/")

readme = ICONS / "README.md"
if not readme.exists():
    errors.append("icons/README.md is missing")
else:
    text = readme.read_text(encoding="utf-8")
    for style in STYLES:
        if not (ICONS / f"preview-{style}.png").exists():
            errors.append(f"icons/preview-{style}.png is missing (run build_icon_preview.py)")
    for n in sorted(a | b):
        stem = n[:-4]
        if f"`{stem}`" not in text:
            errors.append(f"{stem} is not listed in icons/README.md")
    for ref in set(re.findall(r'(?:src="|\]\()([^")#]+\.(?:png|md))', text)):
        if ref.startswith("http"):
            continue
        target = (ICONS / ref).resolve()
        if not target.exists():
            errors.append(f"icons/README.md links to {ref}, which does not exist")
    # jsDelivr examples must point at real files
    for style, name in set(re.findall(r"/icons/(solid|transparent)/([a-z0-9-]+\.png)", text)):
        if name not in names.get(style, set()):
            errors.append(f"icons/README.md uses {style}/{name}, which does not exist")

if errors:
    print("\n".join("FAIL " + e for e in errors))
    print(f"\n{len(errors)} icon check(s) FAILED")
    sys.exit(1)
print(f"icons: {len(a)} icons x {len(STYLES)} styles OK ({SIZE}x{SIZE} RGBA PNG, names match, README complete)")
