"""Renderer protocol and exports for dapple renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TextIO, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


@runtime_checkable
class Renderer(Protocol):
    """Protocol for terminal character renderers.

    Renderers convert a bitmap (2D float array, values 0.0-1.0) and write
    directly to a stream. Each renderer has a characteristic cell size
    that defines how many pixels map to each output character.

    Examples:
        - Braille: 2x4 pixels per character (8 dots)
        - Quadrants: 2x2 pixels per character (4 quadrants)
        - Sextants: 2x3 pixels per character (6 cells)
        - ASCII: 1x2 pixels per character (aspect ratio correction)
        - Sixel/Kitty: 1x1 (true pixel output)
        - Fingerprint: configurable cell size (glyph matching)
    """

    @property
    def cell_width(self) -> int:
        """Pixels per character horizontally."""
        ...

    @property
    def cell_height(self) -> int:
        """Pixels per character vertically."""
        ...

    def render(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating] | None = None,
        *,
        dest: TextIO,
    ) -> None:
        """Render bitmap to stream.

        Args:
            bitmap: 2D array of shape (H, W) with values in [0.0, 1.0].
                    Higher values = brighter/more ink.
            colors: Optional 3D array of shape (H, W, 3) with RGB values in [0.0, 1.0].
                    If None, grayscale rendering is used.
            dest: Stream to write output to.
        """
        ...


# Import renderers for convenient access
from dapple.renderers.braille import BrailleRenderer, braille
from dapple.renderers.quadrants import QuadrantsRenderer, quadrants
from dapple.renderers.sextants import SextantsRenderer, sextants
from dapple.renderers.ascii import AsciiRenderer, ascii
from dapple.renderers.sixel import SixelRenderer, sixel
from dapple.renderers.kitty import KittyRenderer, kitty
from dapple.renderers.fingerprint import (
    FingerprintRenderer,
    clear_glyph_caches,
    fingerprint,
    warm_glyph_cache,
)

__all__ = [
    "Renderer",
    "BrailleRenderer",
    "braille",
    "QuadrantsRenderer",
    "quadrants",
    "SextantsRenderer",
    "sextants",
    "AsciiRenderer",
    "ascii",
    "SixelRenderer",
    "sixel",
    "KittyRenderer",
    "kitty",
    "FingerprintRenderer",
    "fingerprint",
    "clear_glyph_caches",
    "warm_glyph_cache",
]
