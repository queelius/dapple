#!/usr/bin/env python3
"""Side-by-side renderer comparison."""

import sys

from PIL import Image

from dapple import braille, fingerprint, sextants
from dapple.adapters.pil import from_pil
from dapple.layout import terminal_fit

img_path = sys.argv[1] if len(sys.argv) > 1 else "examples/lena.png"
width = int(sys.argv[2]) if len(sys.argv) > 2 else 60

img = Image.open(img_path)
canvas = from_pil(img)

renderers = [
    ("sextants (native)", sextants),
    ("braille (truecolor)", braille(color_mode="truecolor")),
    ("fingerprint (basic)", fingerprint),
    ("fingerprint (blocks)", fingerprint(glyph_set="blocks")),
    ("fingerprint (sextants)", fingerprint(glyph_set="sextants")),
    ("fingerprint (braille)", fingerprint(glyph_set="braille")),
    ("fingerprint (extended)", fingerprint(glyph_set="extended")),
    ("fingerprint (full)", fingerprint(glyph_set="full")),
]

for name, rend in renderers:
    c, r = terminal_fit(canvas, rend, width=width)
    print(f"\033[1m=== {name} ===\033[0m")
    c.out(r, dest=sys.stdout)
    print("\n")
