"""dapple - Unified terminal graphics library.

Render bitmaps to terminal character art using various formats:
braille, quadrants, sextants, ASCII, sixel, kitty, and fingerprint.

Example:
    >>> import numpy as np
    >>> from dapple import Canvas, braille, quadrants, sextants
    >>>
    >>> # Create canvas from bitmap
    >>> bitmap = np.random.rand(40, 80).astype(np.float32)
    >>> canvas = Canvas(bitmap)
    >>>
    >>> # Output to different destinations
    >>> canvas.out(braille)                    # to stdout
    >>> canvas.out(quadrants, "art.txt")       # to file
    >>> canvas.out(sextants, my_stringio)      # to StringIO
    >>> canvas.out(braille(threshold=0.3))     # custom options
    >>>
    >>> # Default renderer for __str__
    >>> canvas = Canvas(bitmap, renderer=braille)
    >>> print(canvas)  # Uses braille
"""

from __future__ import annotations

__version__ = "0.7.1"

# Core class
from dapple.canvas import Canvas
from dapple.adapters.numpy import from_array
from dapple.adapters.pil import from_pil

# Renderers (instances for direct use)
from dapple.renderers import (
    Renderer,
    BrailleRenderer,
    braille,
    QuadrantsRenderer,
    quadrants,
    SextantsRenderer,
    sextants,
    AsciiRenderer,
    ascii,
    SixelRenderer,
    sixel,
    KittyRenderer,
    kitty,
    FingerprintRenderer,
    fingerprint,
)

# Preprocessing functions
from dapple.preprocess import (
    auto_contrast,
    floyd_steinberg,
    invert,
    gamma_correct,
    sharpen,
    threshold,
    resize,
    crop,
    flip,
    rotate,
)

# Layout
from dapple.layout import (
    Frame,
    Grid,
    terminal_columns,
    terminal_fit,
)

# Auto-detection
from dapple.auto import (
    Protocol,
    TerminalInfo,
    auto_renderer,
    detect_terminal,
    render_image,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "Canvas",
    "from_array",
    "from_pil",
    # Renderer protocol
    "Renderer",
    # Renderer classes
    "BrailleRenderer",
    "QuadrantsRenderer",
    "SextantsRenderer",
    "AsciiRenderer",
    "SixelRenderer",
    "KittyRenderer",
    "FingerprintRenderer",
    # Renderer instances
    "braille",
    "quadrants",
    "sextants",
    "ascii",
    "sixel",
    "kitty",
    "fingerprint",
    # Preprocessing
    "auto_contrast",
    "floyd_steinberg",
    "invert",
    "gamma_correct",
    "sharpen",
    "threshold",
    "resize",
    "crop",
    "flip",
    "rotate",
    # Layout
    "Frame",
    "Grid",
    "terminal_columns",
    "terminal_fit",
    # Auto-detection
    "Protocol",
    "TerminalInfo",
    "auto_renderer",
    "detect_terminal",
    "render_image",
]
