"""Braille renderer - Unicode braille characters (2x4 dots per character).

Braille characters (U+2800-U+28FF) encode a 2x4 dot pattern directly into the
Unicode codepoint. Each character can represent 8 binary pixels, giving 8x the
pseudo-pixel density of regular characters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TextIO

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

from dapple.renderers._ansi import RESET

# Sentinel distinguishing "argument not passed" from "explicit None (auto)".
# Used by BrailleRenderer.__call__ so callers can transition into
# auto-threshold mode by passing ``threshold=None`` — previously impossible
# because ``None`` was both the sentinel and a valid field value.
_UNSET: object = object()

# Mapping from (row, col) in 2x4 region to bit index in braille codepoint.
# Standard Unicode braille layout:
#   col 0   col 1
#   +---+---+
#   | 0 | 3 |  bits 0, 3
#   +---+---+
#   | 1 | 4 |  bits 1, 4
#   +---+---+
#   | 2 | 5 |  bits 2, 5
#   +---+---+
#   | 6 | 7 |  bits 6, 7
#   +---+---+
DOT_MAP = [
    (0, 0, 0),  # dot 1 -> bit 0
    (1, 0, 1),  # dot 2 -> bit 1
    (2, 0, 2),  # dot 3 -> bit 2
    (3, 0, 6),  # dot 7 -> bit 6
    (0, 1, 3),  # dot 4 -> bit 3
    (1, 1, 4),  # dot 5 -> bit 4
    (2, 1, 5),  # dot 6 -> bit 5
    (3, 1, 7),  # dot 8 -> bit 7
]


def _region_to_braille_code(region: NDArray[np.floating], threshold: float) -> int:
    """Convert a 2x4 region to a braille codepoint offset.

    Args:
        region: 4x2 array of brightness values (row-major: 4 rows, 2 cols)
        threshold: Brightness threshold for dot activation

    Returns:
        Integer offset from U+2800 (0-255)
    """
    code = 0
    for row, col, bit in DOT_MAP:
        if region[row, col] > threshold:
            code |= 1 << bit
    return code


def _grayscale_fg(level: int) -> str:
    """Generate 256-color grayscale foreground escape code.

    Args:
        level: Grayscale level 0-23 (0=darkest, 23=brightest).

    Returns:
        ANSI escape sequence for grayscale foreground.
    """
    code = 232 + min(23, max(0, level))
    return f"\033[38;5;{code}m"


def _truecolor_fg(r: int, g: int, b: int) -> str:
    """Generate 24-bit true color foreground escape code.

    Args:
        r, g, b: Color components 0-255.

    Returns:
        ANSI escape sequence for RGB foreground.
    """
    r = min(255, max(0, r))
    g = min(255, max(0, g))
    b = min(255, max(0, b))
    return f"\033[38;2;{r};{g};{b}m"


@dataclass(frozen=True)
class BrailleRenderer:
    """Render bitmap as Unicode braille (2x4 dots per character).

    Each character represents a 2-wide by 4-tall pixel region. Dots are activated
    when pixel brightness exceeds the threshold.

    Attributes:
        threshold: Brightness threshold (0.0-1.0) for dot activation.
                   If None, auto-detects from bitmap mean.
        color_mode: "none" for plain braille, "grayscale" for 24-level grayscale,
                    or "truecolor" for full 24-bit RGB.

    Example:
        >>> from dapple import Canvas, braille
        >>> canvas = Canvas(np.random.rand(24, 40))
        >>> canvas.out(braille)                      # to stdout
        >>> canvas.out(braille(threshold=0.3))       # custom threshold
    """

    threshold: float | None = 0.5
    color_mode: Literal["none", "grayscale", "truecolor"] = "none"

    @property
    def cell_width(self) -> int:
        """Pixels per character horizontally."""
        return 2

    @property
    def cell_height(self) -> int:
        """Pixels per character vertically."""
        return 4

    def __call__(
        self,
        threshold: float | None | object = _UNSET,
        color_mode: Literal["none", "grayscale", "truecolor"] | None = None,
    ) -> BrailleRenderer:
        """Create a new renderer with modified options.

        Args:
            threshold: New threshold value. Pass ``None`` to enable
                auto-threshold mode (computed from the bitmap mean at
                render time). Omit the argument to keep the current value.
            color_mode: New color mode (None to keep current).

        Returns:
            New BrailleRenderer with updated settings.
        """
        new_threshold = self.threshold if threshold is _UNSET else threshold  # type: ignore[assignment]
        return BrailleRenderer(
            threshold=new_threshold,
            color_mode=color_mode if color_mode is not None else self.color_mode,
        )

    def render(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating] | None = None,
        *,
        dest: TextIO,
    ) -> None:
        """Render bitmap to stream.

        Args:
            bitmap: 2D array of shape (H, W), values 0.0-1.0 (brightness).
                    Higher values = brighter pixels.
            colors: Optional 3D array of shape (H, W, 3) with RGB values 0.0-1.0.
                    Used only when color_mode="truecolor".
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

        # Determine threshold
        threshold = self.threshold
        if threshold is None:
            threshold = max(0.1, min(0.9, float(bitmap.mean())))

        h, w = bitmap.shape
        first_row = True

        for cy in range(0, h, 4):
            if not first_row:
                dest.write("\n")
            first_row = False

            row_parts = []
            for cx in range(0, w, 2):
                # Extract 2x4 region, pad with zeros if needed
                region = np.zeros((4, 2), dtype=np.float32)
                region_h = min(4, h - cy)
                region_w = min(2, w - cx)
                region[:region_h, :region_w] = bitmap[cy : cy + region_h, cx : cx + region_w]

                # Encode to braille codepoint
                code = _region_to_braille_code(region, threshold)
                braille_char = chr(0x2800 + code)

                if self.color_mode == "none":
                    row_parts.append(braille_char)
                elif self.color_mode == "grayscale":
                    avg_brightness = region[:region_h, :region_w].mean()
                    level = int(avg_brightness * 23.999)
                    row_parts.append(f"{_grayscale_fg(level)}{braille_char}")
                else:  # truecolor
                    if colors is not None:
                        color_region = colors[cy : cy + region_h, cx : cx + region_w]
                        avg_color = color_region.mean(axis=(0, 1))
                        r = int(avg_color[0] * 255.999)
                        g = int(avg_color[1] * 255.999)
                        b = int(avg_color[2] * 255.999)
                    else:
                        avg_brightness = region[:region_h, :region_w].mean()
                        gray = int(avg_brightness * 255.999)
                        r = g = b = gray
                    row_parts.append(f"{_truecolor_fg(r, g, b)}{braille_char}")

            # Add reset at end of row if using color
            row = "".join(row_parts)
            if self.color_mode != "none":
                row += RESET
            dest.write(row)


# Convenience instance for default usage
braille = BrailleRenderer()
