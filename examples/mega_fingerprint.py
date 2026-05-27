#!/usr/bin/env python3
"""Render with a massive glyph set to see what fingerprint selects.

Usage:
    python examples/mega_fingerprint.py [image] [width]
    python examples/mega_fingerprint.py examples/landscape.jpg 80
"""

from __future__ import annotations

import re
import sys
import time
from io import StringIO

from PIL import Image

from dapple import fingerprint, sextants
from dapple.adapters.pil import from_pil
from dapple.layout import terminal_fit
from dapple.renderers.fingerprint import clear_glyph_caches, warm_glyph_cache

img_path = sys.argv[1] if len(sys.argv) > 1 else "examples/landscape.jpg"
width = int(sys.argv[2]) if len(sys.argv) > 2 else 80

# Build mega glyph set: ~9K characters from diverse Unicode blocks
chars = set()
for i in range(0x20, 0x0250):    chars.add(chr(i))   # Latin
for i in range(0x0370, 0x0530):   chars.add(chr(i))   # Greek + Cyrillic
for i in range(0x2100, 0x2C00):   chars.add(chr(i))   # Symbols, box, geometric, math, misc
for i in range(0x2800, 0x2900):   chars.add(chr(i))   # Braille
for i in range(0x1FB00, 0x1FB3C): chars.add(chr(i))   # Sextants
for i in range(0x4E00, 0x9FFF, 4): chars.add(chr(i))  # CJK (sampled)
mega = "".join(sorted(chars))

print(f"Image: {img_path}")
print(f"Glyph set: {len(mega)} characters")
print("Building glyph cache (one-time cost)...", flush=True)

clear_glyph_caches()
t0 = time.monotonic()
renderable = warm_glyph_cache(mega, 8, 16)
cache_ms = (time.monotonic() - t0) * 1000
skipped = len(mega) - renderable
if skipped:
    print(
        f"Cache built in {cache_ms:.0f}ms "
        f"({renderable}/{len(mega)} glyphs renderable, "
        f"{skipped} skipped due to missing font coverage)"
    )
else:
    print(f"Cache built in {cache_ms:.0f}ms ({renderable} glyphs)")

img = Image.open(img_path)
canvas = from_pil(img)

# Render with mega set
r_mega = fingerprint(glyph_set=mega)
c, r = terminal_fit(canvas, r_mega, width=width)

buf = StringIO()
t0 = time.monotonic()
r.render(c.bitmap, c.colors, dest=buf)
render_ms = (time.monotonic() - t0) * 1000
output = buf.getvalue()

# Analyze which glyphs were selected
clean = re.sub(r"\033\[[^m]*m", "", output).replace("\n", "")
unique = sorted(set(clean), key=ord)

# Categorize
def categorize(ch):
    cp = ord(ch)
    if 0x4E00 <= cp <= 0x9FFF: return "CJK"
    if 0x0370 <= cp <= 0x03FF: return "Greek"
    if 0x0400 <= cp <= 0x04FF: return "Cyrillic"
    if 0x2800 <= cp <= 0x28FF: return "Braille"
    if 0x1FB00 <= cp <= 0x1FB3F: return "Sextant"
    if 0x2500 <= cp <= 0x257F: return "Box Drawing"
    if 0x2580 <= cp <= 0x259F: return "Block"
    if 0x25A0 <= cp <= 0x25FF: return "Geometric"
    if 0x2200 <= cp <= 0x22FF: return "Math"
    if 0x2300 <= cp <= 0x23FF: return "Technical"
    if 0x20 <= cp <= 0x7E: return "ASCII"
    if 0x80 <= cp <= 0x024F: return "Latin Ext"
    return "Other"

categories = {}
for ch in unique:
    cat = categorize(ch)
    categories.setdefault(cat, []).append(ch)

print(f"\nRender: {render_ms:.0f}ms")
print(f"Unique glyphs used: {len(unique)} / {len(mega)}\n")

print("Glyphs by category:")
for cat in sorted(categories, key=lambda c: -len(categories[c])):
    chars_list = categories[cat]
    sample = "".join(chars_list[:20])
    suffix = "..." if len(chars_list) > 20 else ""
    print(f"  {cat:15s}: {len(chars_list):4d}  {sample}{suffix}")

# Also render native sextants for comparison
c2, r2 = terminal_fit(canvas, sextants, width=width)
buf2 = StringIO()
t0 = time.monotonic()
r2.render(c2.bitmap, c2.colors, dest=buf2)
sext_ms = (time.monotonic() - t0) * 1000

print(f"\n\033[1m=== sextants (native) ({sext_ms:.0f}ms) ===\033[0m")
sys.stdout.write(buf2.getvalue())
print("\n")

print(f"\033[1m=== fingerprint (mega {len(mega)} glyphs, {render_ms:.0f}ms) ===\033[0m")
sys.stdout.write(output)
print()
