"""Shared renderer resolution and terminal size helpers."""

from __future__ import annotations

import shutil

from dapple.renderers import Renderer


def get_renderer(
    name: str,
    *,
    grayscale: bool = False,
    no_color: bool = False,
) -> Renderer:
    """Get a renderer by name, configured for chart output.

    Delegates to :func:`dapple.extras.common.get_renderer` for colour
    handling (including ``NO_COLOR`` env var support), then layers
    chart-specific defaults on top.

    Args:
        name: Renderer name (braille, quadrants, sextants, ascii, sixel, kitty).
        grayscale: Force grayscale output.
        no_color: Disable colour output entirely.

    Returns:
        Configured Renderer instance.

    Raises:
        ValueError: If the renderer name is unknown.
    """
    from dapple.extras.common import get_renderer as _common_get_renderer

    rend = _common_get_renderer(name, grayscale=grayscale, no_color=no_color)

    # Chart-specific overrides: braille needs a lower threshold for
    # thin chart lines to stay visible.
    if name == "braille" and hasattr(rend, "threshold"):
        rend = rend(threshold=0.2)

    return rend


def get_terminal_size() -> tuple[int, int]:
    """Return (columns, lines) of the terminal."""
    return shutil.get_terminal_size(fallback=(80, 24))


def pixel_dimensions(
    renderer: Renderer,
    char_width: int,
    char_height: int,
) -> tuple[int, int]:
    """Convert character dimensions to pixel dimensions for a renderer.

    Args:
        renderer: The dapple renderer.
        char_width: Width in terminal characters.
        char_height: Height in terminal characters.

    Returns:
        (pixel_width, pixel_height) tuple.
    """
    return (char_width * renderer.cell_width, char_height * renderer.cell_height)
