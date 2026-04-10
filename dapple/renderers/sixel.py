"""Sixel renderer - DEC Sixel graphics protocol.

Sixel is a bitmap graphics format developed by DEC. Each character encodes
a 6-pixel vertical band, hence "sixel" (six elements). Supported by xterm
(with -ti vt340), mlterm, WezTerm, foot, and some other terminals.

Format: ESC P q <color definitions> <sixel data> ESC \\

The sixel data consists of:
- Color selection: #<n> where n is color index
- Color definition: #<n>;2;<r>;<g>;<b> (RGB percentages 0-100)
- Pixel data: characters '?' (0x3F) to '~' (0x7E) encode 6-bit patterns
- Carriage return: $ moves to start of current row
- Line feed: - moves to next 6-pixel row
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


# DCS (Device Control String) escape sequences
DCS_START = "\033Pq"  # ESC P q (start sixel sequence)
DCS_END = "\033\\"  # ESC \ (string terminator)

# Sixel encoding: each char encodes 6 vertical pixels
# Character = '?' (0x3F) + 6-bit pattern
# Bits: 0=top, 5=bottom


def _quantize_colors(
    colors: NDArray[np.floating],
    n_colors: int,
) -> tuple[NDArray[np.uint8], NDArray[np.floating]]:
    """Quantize RGB colors to a limited palette using simple binning.

    Picks the largest ``levels`` such that ``levels ** 3 <= n_colors`` and
    ``levels >= 2``, so the emitted palette never exceeds the requested
    ``n_colors``. Clamped to 6 (the DEC sixel spec's practical ceiling
    for per-channel resolution from uniform binning).

    Args:
        colors: RGB array (H, W, 3) with values 0.0-1.0
        n_colors: Maximum number of colors in palette (must be >= 8)

    Returns:
        Tuple of (indexed image, palette)
        - indexed: (H, W) array of palette indices
        - palette: (levels**3, 3) array of RGB values
    """
    h, w, _ = colors.shape

    # Find largest cube-rootable level count that fits under n_colors.
    levels = 2
    while (levels + 1) ** 3 <= n_colors and levels < 6:
        levels += 1

    # Quantize each channel
    r = (colors[:, :, 0] * (levels - 0.001)).astype(np.uint8)
    g = (colors[:, :, 1] * (levels - 0.001)).astype(np.uint8)
    b = (colors[:, :, 2] * (levels - 0.001)).astype(np.uint8)

    # Compute palette index
    indices = r * levels * levels + g * levels + b

    # Build palette
    n_actual = levels**3
    palette = np.zeros((n_actual, 3), dtype=np.float32)
    for i in range(n_actual):
        ri = i // (levels * levels)
        gi = (i // levels) % levels
        bi = i % levels
        palette[i] = [
            (ri + 0.5) / levels,
            (gi + 0.5) / levels,
            (bi + 0.5) / levels,
        ]

    return indices.astype(np.uint8), palette


def _quantize_grayscale(
    bitmap: NDArray[np.floating],
    n_colors: int,
) -> tuple[NDArray[np.uint8], NDArray[np.floating]]:
    """Quantize grayscale bitmap to indexed with palette.

    Args:
        bitmap: 2D array (H, W) with values 0.0-1.0
        n_colors: Number of gray levels

    Returns:
        Tuple of (indexed image, palette)
    """
    levels = min(n_colors, 256)
    indices = (bitmap * (levels - 0.001)).astype(np.uint8)

    palette = np.zeros((levels, 3), dtype=np.float32)
    for i in range(levels):
        v = (i + 0.5) / levels
        palette[i] = [v, v, v]

    return indices, palette


@dataclass(frozen=True)
class SixelRenderer:
    """Render bitmap as Sixel graphics (DEC VT340 style).

    Sixel outputs actual pixels encoded as escape sequences. Each "character"
    in the output encodes a 1x6 pixel column. Supported by xterm (with -ti vt340),
    mlterm, WezTerm, foot, and some other terminals.

    Attributes:
        max_colors: Maximum colors in palette (default 256).
        scale: Pixel scaling factor (default 1).

    Example:
        >>> from dapple import Canvas, sixel
        >>> canvas = Canvas(np.random.rand(48, 80))
        >>> canvas.out(sixel)  # In supported terminal
    """

    max_colors: int = 256
    scale: int = 1

    @property
    def cell_width(self) -> int:
        """Sixel outputs actual pixels (1:1)."""
        return 1

    @property
    def cell_height(self) -> int:
        """Sixel outputs actual pixels (1:1)."""
        return 1

    def __call__(
        self,
        max_colors: int | None = None,
        scale: int | None = None,
    ) -> SixelRenderer:
        """Create a new renderer with modified options.

        Args:
            max_colors: New max colors (None to keep current)
            scale: New scale factor (None to keep current)

        Returns:
            New SixelRenderer with updated settings.
        """
        return SixelRenderer(
            max_colors=max_colors if max_colors is not None else self.max_colors,
            scale=scale if scale is not None else self.scale,
        )

    def render(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating] | None = None,
        *,
        dest: TextIO,
    ) -> None:
        """Render bitmap to stream as Sixel escape sequence.

        Args:
            bitmap: 2D array (H, W) with values 0.0-1.0.
            colors: Optional 3D array (H, W, 3) with RGB values 0.0-1.0.
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

        # Scale up if requested
        if self.scale > 1:
            bitmap = np.repeat(np.repeat(bitmap, self.scale, axis=0), self.scale, axis=1)
            if colors is not None:
                colors = np.repeat(np.repeat(colors, self.scale, axis=0), self.scale, axis=1)

        h, w = bitmap.shape

        # Pad height to multiple of 6
        pad_h = (6 - h % 6) % 6
        if pad_h > 0:
            bitmap = np.pad(bitmap, ((0, pad_h), (0, 0)), constant_values=0)
            if colors is not None:
                colors = np.pad(colors, ((0, pad_h), (0, 0), (0, 0)), constant_values=0)
            h = bitmap.shape[0]

        # Quantize to palette
        if colors is not None:
            indices, palette = _quantize_colors(colors, self.max_colors)
        else:
            indices, palette = _quantize_grayscale(bitmap, min(self.max_colors, 64))

        n_colors = len(palette)

        # Write sixel sequence
        dest.write(DCS_START)

        # Define color palette (RGB percentages 0-100)
        for i, (r, g, b) in enumerate(palette):
            ri, gi, bi = int(r * 100), int(g * 100), int(b * 100)
            dest.write(f"#{i};2;{ri};{gi};{bi}")

        # Encode pixel data in 6-row bands
        for band_y in range(0, h, 6):
            band = indices[band_y : band_y + 6, :]  # 6 x W

            # For each color, output pixels that use that color
            for color_idx in range(n_colors):
                # Create mask of pixels with this color
                mask = band == color_idx

                # Skip if no pixels use this color
                if not mask.any():
                    continue

                # Select color
                dest.write(f"#{color_idx}")

                # Encode each column
                x = 0
                while x < w:
                    # Get 6-bit pattern for this column
                    pattern = 0
                    for bit in range(6):
                        if mask[bit, x]:
                            pattern |= 1 << bit

                    # Check for run-length encoding opportunity
                    run_len = 1
                    while x + run_len < w and run_len < 255:
                        next_pattern = 0
                        for bit in range(6):
                            if mask[bit, x + run_len]:
                                next_pattern |= 1 << bit
                        if next_pattern != pattern:
                            break
                        run_len += 1

                    # Encode
                    char = chr(0x3F + pattern)  # '?' = 0, '~' = 63
                    if run_len > 3:
                        dest.write(f"!{run_len}{char}")
                    else:
                        dest.write(char * run_len)

                    x += run_len

                # Carriage return to start of row (for next color)
                dest.write("$")

            # Line feed to next 6-row band
            dest.write("-")

        dest.write(DCS_END)


# Convenience instance for default usage
sixel = SixelRenderer()
