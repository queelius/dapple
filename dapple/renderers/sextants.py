"""Sextants renderer - Unicode sextant characters (2x3 pixels per character).

Uses Unicode sextant characters (U+1FB00–U+1FB3B) plus block elements to
represent 2x3 pixel regions. Each character encodes a 2-wide by 3-tall
pattern, providing 6 pixels per character position.
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

_UNIFORM_THRESHOLD = 0.001


def _build_sextant_table() -> list[str]:
    """Build the 64-entry sextant character lookup table.

    Sextant patterns encode a 2×3 grid (6 cells) as a 6-bit pattern:
        Cell layout:        Bit weights:
        0 1                 32 16
        2 3                  8  4
        4 5                  2  1

    Pattern = (cell0 * 32) + (cell1 * 16) + (cell2 * 8) + (cell3 * 4) + (cell4 * 2) + cell5

    Unicode sextants (U+1FB00–U+1FB3B) cover patterns 1–63, excluding:
    - Pattern 0 (empty) -> space
    - Pattern 21 (left half: cells 0,2,4) -> ▌ (U+258C)
    - Pattern 42 (right half: cells 1,3,5) -> ▐ (U+2590)
    - Pattern 63 (full) -> █ (U+2588)

    Returns:
        64-character list indexed by pattern value.
    """
    # Unicode sextant encoding:
    # - Cells are numbered 1-6 (1-indexed), pattern = sum of 2^(cell-1)
    # - Cell 1=top-left, 2=top-right, 3=mid-left, 4=mid-right, 5=bot-left, 6=bot-right
    # - Left half = cells 1,3,5 = 2^0 + 2^2 + 2^4 = 1+4+16 = 21
    # - Right half = cells 2,4,6 = 2^1 + 2^3 + 2^5 = 2+8+32 = 42
    #
    # Internal encoding uses 0-indexed cells with weights [32,16,8,4,2,1]:
    # - Cell 0=top-left(bit5), 1=top-right(bit4), 2=mid-left(bit3),
    #   3=mid-right(bit2), 4=bot-left(bit1), 5=bot-right(bit0)
    # - Left half in internal encoding = cells 0,2,4 = 32+8+2 = 42
    # - Right half in internal encoding = cells 1,3,5 = 16+4+1 = 21
    #
    # Special patterns that use existing block characters instead of sextants:
    # - Pattern 0 (empty) -> space
    # - Pattern 21 (left half) -> "▌" (U+258C)
    # - Pattern 42 (right half) -> "▐" (U+2590)
    # - Pattern 63 (full) -> "█" (U+2588)

    table = []
    for my_pattern in range(64):
        # Convert my bit layout to Unicode bit layout
        # My bits: [bit5=cell0, bit4=cell1, bit3=cell2, bit2=cell3, bit1=cell4, bit0=cell5]
        # Unicode: cell_i contributes 2^(i) where i is 0-indexed now
        # So unicode_pattern = cell0*1 + cell1*2 + cell2*4 + cell3*8 + cell4*16 + cell5*32

        cell0 = (my_pattern >> 5) & 1
        cell1 = (my_pattern >> 4) & 1
        cell2 = (my_pattern >> 3) & 1
        cell3 = (my_pattern >> 2) & 1
        cell4 = (my_pattern >> 1) & 1
        cell5 = my_pattern & 1

        unicode_pattern = cell0 * 1 + cell1 * 2 + cell2 * 4 + cell3 * 8 + cell4 * 16 + cell5 * 32

        if unicode_pattern == 0:
            table.append(" ")
        elif unicode_pattern == 63:
            table.append("█")
        elif unicode_pattern == 21:  # Left half in Unicode encoding
            table.append("▌")
        elif unicode_pattern == 42:  # Right half in Unicode encoding
            table.append("▐")
        else:
            # Count how many special patterns (21, 42) are below unicode_pattern
            offset = sum(1 for x in (21, 42) if x < unicode_pattern)
            table.append(chr(0x1FB00 + unicode_pattern - 1 - offset))

    return table


SEXTANT_CHARS = _build_sextant_table()

# Bit weights for pattern calculation: cells 0-5 in row-major order
# Cell layout: row0: [0,1], row1: [2,3], row2: [4,5]
_BITS = np.array([32, 16, 8, 4, 2, 1], dtype=np.uint8)


@dataclass(frozen=True)
class SextantsRenderer:
    """Render bitmap as sextant blocks (2x3 pixels per character).

    Each character represents a 2x3 pixel region using one of 64 sextant
    block characters, with foreground and background colors to maximize
    visual fidelity. Sextants provide higher vertical resolution than
    quadrants (2x2) while remaining widely supported in modern terminals.

    Attributes:
        true_color: Use 24-bit RGB instead of 256-color mode (default True).
        grayscale: Force grayscale output even for RGB input (default False).

    Example:
        >>> from dapple import Canvas, sextants
        >>> canvas = Canvas(np.random.rand(24, 40))
        >>> canvas.out(sextants)                       # to stdout
        >>> canvas.out(sextants(true_color=False))     # 256-color mode
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
        return 3

    def __call__(
        self,
        true_color: bool | None = None,
        grayscale: bool | None = None,
    ) -> SextantsRenderer:
        """Create a new renderer with modified options.

        Args:
            true_color: Use 24-bit color (None to keep current)
            grayscale: Force grayscale (None to keep current)

        Returns:
            New SextantsRenderer with updated settings.
        """
        return SextantsRenderer(
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
        """Render bitmap to stream as ANSI-colored sextant blocks.

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
        rows, cols = h // 3, w // 2

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
        # Reshape to sextant blocks: (rows, 3, cols, 2) -> (rows, cols, 6)
        block_data = (
            bitmap[: rows * 3, : cols * 2]
            .reshape(rows, 3, cols, 2)
            .transpose(0, 2, 1, 3)
            .reshape(rows, cols, 6)
        )

        # Min/max per block for fg/bg
        fg = np.amax(block_data, axis=2)
        bg = np.amin(block_data, axis=2)

        # Threshold at midpoint, compute pattern
        thresh = ((fg + bg) / 2)[:, :, np.newaxis]
        patterns = np.sum((block_data > thresh).astype(np.uint8) * _BITS, axis=2)

        # Uniform blocks -> full block
        uniform = (fg - bg) < _UNIFORM_THRESHOLD
        patterns[uniform] = 0b111111

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
                    f"{SEXTANT_CHARS[patterns[y, x]]}"
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
        # Reshape blocks: (rows, cols, 6, 3)
        block_data = (
            colors[: rows * 3, : cols * 2]
            .reshape(rows, 3, cols, 2, 3)
            .transpose(0, 2, 1, 3, 4)
            .reshape(rows, cols, 6, 3)
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
        patterns[uniform] = 0b111111

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
                    f"{SEXTANT_CHARS[patterns[y, x]]}"
                )
            dest.write("".join(parts) + RESET)


# Convenience instance for default usage
sextants = SextantsRenderer()
