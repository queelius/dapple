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

__version__ = "0.9.0"

# Core class
from dapple.canvas import Canvas
from dapple.adapters.numpy import from_array

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

# Lazily-loaded attributes that depend on optional packages. Keeping these
# out of the eager import block lets `import dapple` work in numpy-only
# environments — core depends only on numpy per CLAUDE.md.
_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "from_pil": ("dapple.adapters.pil", "from_pil"),
    "PILAdapter": ("dapple.adapters.pil", "PILAdapter"),
    "from_matplotlib": ("dapple.adapters.matplotlib", "from_matplotlib"),
    "MatplotlibAdapter": ("dapple.adapters.matplotlib", "MatplotlibAdapter"),
    "from_cairo": ("dapple.adapters.cairo", "from_cairo"),
    "CairoAdapter": ("dapple.adapters.cairo", "CairoAdapter"),
    "from_ansi": ("dapple.adapters.ansi", "from_ansi"),
    "ANSIAdapter": ("dapple.adapters.ansi", "ANSIAdapter"),
}


def __getattr__(name: str):
    """Lazy-load optional adapters on first access."""
    entry = _LAZY_ATTRS.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = entry
    import importlib

    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value  # cache for subsequent lookups
    return value


__all__ = [
    # Version
    "__version__",
    # Core
    "Canvas",
    "from_array",
    "from_pil",
    "PILAdapter",
    "from_matplotlib",
    "MatplotlibAdapter",
    "from_cairo",
    "CairoAdapter",
    "from_ansi",
    "ANSIAdapter",
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
