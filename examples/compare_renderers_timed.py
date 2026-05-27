#!/usr/bin/env python3
"""Compare renderers side-by-side in the terminal with per-render timing.

Usage:
    python examples/compare_renderers_timed.py [image_path]
    python examples/compare_renderers_timed.py examples/landscape.jpg
"""

from __future__ import annotations

import sys
import time
from io import StringIO
from pathlib import Path

from PIL import Image

from dapple import braille, fingerprint, from_pil, sextants
from dapple.layout import terminal_columns, terminal_fit


def render_timed(canvas, renderer, width):
    """Render and return (output_string, elapsed_ms)."""
    c, r = terminal_fit(canvas, renderer, width=width)
    buf = StringIO()
    t0 = time.monotonic()
    r.render(c.bitmap, c.colors, dest=buf)
    elapsed = (time.monotonic() - t0) * 1000
    return buf.getvalue(), elapsed


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else "examples/landscape.jpg"
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        sys.exit(1)

    img = Image.open(image_path)
    canvas = from_pil(img)
    cols = terminal_columns()
    w = min(cols, 80)

    renderers = [
        ("sextants (native)", sextants),
        ("braille (truecolor)", braille(color_mode="truecolor")),
        ("fingerprint (basic)", fingerprint(glyph_set="basic")),
        ("fingerprint (blocks)", fingerprint(glyph_set="blocks")),
        ("fingerprint (extended)", fingerprint(glyph_set="extended")),
        ("fingerprint (sextants)", fingerprint(glyph_set="sextants")),
        ("fingerprint (full)", fingerprint(glyph_set="full")),
    ]

    print(f"Image: {image_path} ({img.size[0]}x{img.size[1]})")
    print(f"Output width: {w} chars\n")

    # Pre-warm each renderer (especially fingerprint glyph caches) so the
    # timed pass below measures per-render cost only, not cache-build cost.
    for _label, renderer in renderers:
        render_timed(canvas, renderer, w)

    for label, renderer in renderers:
        output, ms = render_timed(canvas, renderer, w)
        print(f"--- {label} ({ms:.0f}ms) ---")
        sys.stdout.write(output)
        print()


if __name__ == "__main__":
    main()
