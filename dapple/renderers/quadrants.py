"""Quadrants renderer - Quadrant block characters (2x2 pixels per character).

Uses Unicode quadrant block characters (▀▄▌▐▖▗▘▝▚▞▙▛▜▟█) with foreground
and background colors to represent 2x2 pixel regions. This gives both
shape information and color/tone gradients.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# ITU-R BT.601 luminance coefficients
from dapple.color import LUM_R as _LUM_R, LUM_G as _LUM_G, LUM_B as _LUM_B
from dapple.renderers._ansi import RESET, color_code as _color_code, gray_code as _gray_code

_UNIFORM_THRESHOLD = 0.001  # Threshold for treating a block as uniform color

# Quadrant block characters indexed by 4-bit pattern.
# Bit positions: TL=8, TR=4, BL=2, BR=1
QUADRANT_CHARS = [
    " ",  # 0b0000 - empty
    "▗",  # 0b0001 - BR
    "▖",  # 0b0010 - BL
    "▄",  # 0b0011 - lower half
    "▝",  # 0b0100 - TR
    "▐",  # 0b0101 - right half
    "▞",  # 0b0110 - diagonal
    "▟",  # 0b0111 - TR+BL+BR
    "▘",  # 0b1000 - TL
    "▚",  # 0b1001 - diagonal
    "▌",  # 0b1010 - left half
    "▙",  # 0b1011 - TL+BL+BR
    "▀",  # 0b1100 - upper half
    "▜",  # 0b1101 - TL+TR+BR
    "▛",  # 0b1110 - TL+TR+BL
    "█",  # 0b1111 - full
]

# Bit weights for pattern calculation: TL, TR, BL, BR
_BITS = np.array([8, 4, 2, 1], dtype=np.uint8)


@dataclass(frozen=True)
class QuadrantsRenderer:
    """Render bitmap as quadrant blocks (2x2 pixels per character).

    Each character represents a 2x2 pixel region using one of 16 quadrant
    block characters, with foreground and background colors to maximize
    visual fidelity.

    Attributes:
        true_color: Use 24-bit RGB instead of 256-color mode (default True).
        grayscale: Force grayscale output even for RGB input (default False).

    Example:
        >>> from dapple import Canvas, quadrants
        >>> canvas = Canvas(np.random.rand(24, 40))
        >>> canvas.out(quadrants)                       # to stdout
        >>> canvas.out(quadrants(true_color=False))     # 256-color mode
    """

    true_color: bool = True
    grayscale: bool = False

    @property
    def cell_width(self) -> int:
        """Pixels per character horizontally."""
        return 2

    @property
    def cell_height(self) -> int:
        """Pixels per character vertically."""
        return 2

    def __call__(
        self,
        true_color: bool | None = None,
        grayscale: bool | None = None,
    ) -> QuadrantsRenderer:
        """Create a new renderer with modified options.

        Args:
            true_color: Use 24-bit color (None to keep current)
            grayscale: Force grayscale (None to keep current)

        Returns:
            New QuadrantsRenderer with updated settings.
        """
        return QuadrantsRenderer(
            true_color=true_color if true_color is not None else self.true_color,
            grayscale=grayscale if grayscale is not None else self.grayscale,
        )

    def render(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating] | None = None,
        *,
        dest: TextIO,
    ) -> None:
        """Render bitmap to stream as ANSI-colored quadrant blocks.

        Args:
            bitmap: 2D array (H, W) for grayscale, values 0.0-1.0.
            colors: Optional 3D array (H, W, 3) with RGB values 0.0-1.0.
                    If provided and grayscale=False, renders in color.
            dest: Stream to write output to.

        Raises:
            ValueError: If bitmap is not 2D or colors shape doesn't match.
        """
        if bitmap.ndim != 2:
            raise ValueError(f"bitmap must be 2D, got shape {bitmap.shape}")

        if colors is not None:
            if colors.ndim != 3 or colors.shape[2] != 3:
                raise ValueError(f"colors must be (H, W, 3), got shape {colors.shape}")
            if colors.shape[:2] != bitmap.shape:
                raise ValueError(
                    f"colors shape {colors.shape[:2]} must match bitmap shape {bitmap.shape}"
                )

        h, w = bitmap.shape
        rows, cols = h // 2, w // 2

        if rows == 0 or cols == 0:
            return

        # Use grayscale rendering if no colors or grayscale forced
        if colors is None or self.grayscale:
            self._render_gray(bitmap, rows, cols, dest)
        else:
            self._render_rgb(bitmap, colors, rows, cols, dest)

    def _render_gray(
        self,
        bitmap: NDArray[np.floating],
        rows: int,
        cols: int,
        dest: TextIO,
    ) -> None:
        """Render grayscale bitmap using vectorized numpy operations."""
        # Reshape to blocks: (rows, 2, cols, 2) -> (rows, cols, 4)
        block_data = (
            bitmap[: rows * 2, : cols * 2]
            .reshape(rows, 2, cols, 2)
            .transpose(0, 2, 1, 3)
            .reshape(rows, cols, 4)
        )

        # Min/max per block for fg/bg
        fg = np.amax(block_data, axis=2)
        bg = np.amin(block_data, axis=2)

        # Threshold at midpoint, compute pattern
        thresh = ((fg + bg) / 2)[:, :, np.newaxis]
        patterns = np.sum((block_data > thresh).astype(np.uint8) * _BITS, axis=2)

        # Uniform blocks -> full block
        uniform = (fg - bg) < _UNIFORM_THRESHOLD
        patterns[uniform] = 0b1111

        # Write output
        first_row = True
        for y in range(rows):
            if not first_row:
                dest.write("\n")
            first_row = False

            parts = []
            for x in range(cols):
                parts.append(
                    f"{_gray_code(fg[y, x], True, self.true_color)}"
                    f"{_gray_code(bg[y, x], False, self.true_color)}"
                    f"{QUADRANT_CHARS[patterns[y, x]]}"
                )
            dest.write("".join(parts) + RESET)

    def _render_rgb(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating],
        rows: int,
        cols: int,
        dest: TextIO,
    ) -> None:
        """Render RGB bitmap using vectorized numpy operations."""
        # Reshape blocks: (rows, cols, 4, 3)
        block_data = (
            colors[: rows * 2, : cols * 2]
            .reshape(rows, 2, cols, 2, 3)
            .transpose(0, 2, 1, 3, 4)
            .reshape(rows, cols, 4, 3)
        )

        # Luminance per pixel (ITU-R BT.601)
        lum = (
            _LUM_R * block_data[:, :, :, 0]
            + _LUM_G * block_data[:, :, :, 1]
            + _LUM_B * block_data[:, :, :, 2]
        )

        # Min/max luminance for thresholding
        fg_lum = np.amax(lum, axis=2)
        bg_lum = np.amin(lum, axis=2)
        fg_idx = lum.argmax(axis=2)
        bg_idx = lum.argmin(axis=2)

        # Pattern from lum > threshold
        thresh = ((fg_lum + bg_lum) / 2)[:, :, np.newaxis]
        patterns = np.sum((lum > thresh).astype(np.uint8) * _BITS, axis=2)

        # Uniform blocks -> full block
        uniform = (fg_lum - bg_lum) < _UNIFORM_THRESHOLD
        patterns[uniform] = 0b1111

        # Extract fg/bg colors
        y_idx, x_idx = np.ogrid[:rows, :cols]
        fg_colors = block_data[y_idx, x_idx, fg_idx]
        bg_colors = block_data[y_idx, x_idx, bg_idx]

        # Uniform blocks use mean color
        if np.any(uniform):
            mean_colors = np.mean(block_data[uniform], axis=1)
            fg_colors[uniform] = mean_colors
            bg_colors[uniform] = mean_colors

        # Write output
        first_row = True
        for y in range(rows):
            if not first_row:
                dest.write("\n")
            first_row = False

            parts = []
            for x in range(cols):
                fg = fg_colors[y, x]
                bg = bg_colors[y, x]
                parts.append(
                    f"{_color_code(fg[0], fg[1], fg[2], True, self.true_color)}"
                    f"{_color_code(bg[0], bg[1], bg[2], False, self.true_color)}"
                    f"{QUADRANT_CHARS[patterns[y, x]]}"
                )
            dest.write("".join(parts) + RESET)


# Convenience instance for default usage
quadrants = QuadrantsRenderer()
