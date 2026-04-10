"""ANSI input adapter - Parse terminal art back to Canvas.

Reverses the rendering process: takes ANSI-colored terminal output
(braille, quadrants, sextants, ASCII) and converts back to bitmap/colors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from dapple import Canvas
    from numpy.typing import NDArray


# ANSI escape sequence patterns
ANSI_ESCAPE = re.compile(r"\033\[([0-9;]*)m")

# Braille range
BRAILLE_START = 0x2800
BRAILLE_END = 0x28FF

# Sextant range (plus special block chars)
SEXTANT_START = 0x1FB00
SEXTANT_END = 0x1FB3B

# Quadrant block characters
QUADRANT_CHARS = {
    " ": 0b0000,  # empty
    "▗": 0b0001,  # BR
    "▖": 0b0010,  # BL
    "▄": 0b0011,  # lower half
    "▝": 0b0100,  # TR
    "▐": 0b0101,  # right half
    "▞": 0b0110,  # diagonal
    "▟": 0b0111,  # TR+BL+BR
    "▘": 0b1000,  # TL
    "▚": 0b1001,  # diagonal
    "▌": 0b1010,  # left half
    "▙": 0b1011,  # TL+BL+BR
    "▀": 0b1100,  # upper half
    "▜": 0b1101,  # TL+TR+BR
    "▛": 0b1110,  # TL+TR+BL
    "█": 0b1111,  # full
}

# Default ASCII charset (from ascii.py)
DEFAULT_CHARSET = " .:-=+*#%@"

# Basic 16 ANSI colors (standard terminal palette)
BASIC_COLORS = {
    30: (0, 0, 0),        # Black
    31: (128, 0, 0),      # Red
    32: (0, 128, 0),      # Green
    33: (128, 128, 0),    # Yellow
    34: (0, 0, 128),      # Blue
    35: (128, 0, 128),    # Magenta
    36: (0, 128, 128),    # Cyan
    37: (192, 192, 192),  # White
    90: (128, 128, 128),  # Bright Black
    91: (255, 0, 0),      # Bright Red
    92: (0, 255, 0),      # Bright Green
    93: (255, 255, 0),    # Bright Yellow
    94: (0, 0, 255),      # Bright Blue
    95: (255, 0, 255),    # Bright Magenta
    96: (0, 255, 255),    # Bright Cyan
    97: (255, 255, 255),  # Bright White
}


@dataclass
class ColoredChar:
    """A character with foreground and background colors."""

    char: str
    fg: tuple[int, int, int] | None = None  # RGB 0-255
    bg: tuple[int, int, int] | None = None  # RGB 0-255


def _parse_ansi_color(params: list[int], is_fg: bool) -> tuple[int, int, int] | None:
    """Parse ANSI color parameters to RGB.

    Args:
        params: List of SGR parameters after 38; or 48;
        is_fg: True if foreground, False if background

    Returns:
        RGB tuple (0-255) or None if not a color code.
    """
    if len(params) >= 2 and params[0] == 2:
        # 24-bit: 2;R;G;B
        if len(params) >= 4:
            return (params[1], params[2], params[3])
    elif len(params) >= 2 and params[0] == 5:
        # 256-color: 5;N
        n = params[1]
        if n < 16:
            # Basic 16 colors
            return BASIC_COLORS.get(30 + n if n < 8 else 90 + n - 8, (128, 128, 128))
        elif n < 232:
            # 216 color cube: 16 + 36*r + 6*g + b
            n -= 16
            r = (n // 36) * 51
            g = ((n % 36) // 6) * 51
            b = (n % 6) * 51
            return (r, g, b)
        else:
            # Grayscale ramp 232-255: xterm spec is 8 + (index * 10)
            # producing RGB values 8, 18, 28, ..., 238.
            gray = 8 + (n - 232) * 10
            return (gray, gray, gray)
    return None


def parse_colors(text: str) -> list[list[ColoredChar]]:
    """Parse ANSI-colored text into a grid of colored characters.

    Args:
        text: ANSI-escaped text with potential colors.

    Returns:
        2D list of ColoredChar objects, one list per line.
    """
    lines = text.split("\n")
    result: list[list[ColoredChar]] = []

    for line in lines:
        current_fg: tuple[int, int, int] | None = None
        current_bg: tuple[int, int, int] | None = None
        chars: list[ColoredChar] = []
        pos = 0

        while pos < len(line):
            # Check for ANSI escape
            match = ANSI_ESCAPE.match(line, pos)
            if match:
                params_str = match.group(1)
                if params_str:
                    params = [int(p) if p else 0 for p in params_str.split(";")]
                else:
                    params = [0]

                # Process SGR parameters
                i = 0
                while i < len(params):
                    p = params[i]
                    if p == 0:
                        # Reset
                        current_fg = None
                        current_bg = None
                    elif p == 38 and i + 1 < len(params):
                        # Foreground color
                        color = _parse_ansi_color(params[i + 1 :], is_fg=True)
                        if color:
                            current_fg = color
                        # Skip consumed params
                        if i + 1 < len(params) and params[i + 1] == 2:
                            i += 4
                        elif i + 1 < len(params) and params[i + 1] == 5:
                            i += 2
                    elif p == 48 and i + 1 < len(params):
                        # Background color
                        color = _parse_ansi_color(params[i + 1 :], is_fg=False)
                        if color:
                            current_bg = color
                        if i + 1 < len(params) and params[i + 1] == 2:
                            i += 4
                        elif i + 1 < len(params) and params[i + 1] == 5:
                            i += 2
                    elif 30 <= p <= 37 or 90 <= p <= 97:
                        # Basic foreground
                        current_fg = BASIC_COLORS.get(p, (128, 128, 128))
                    elif 40 <= p <= 47 or 100 <= p <= 107:
                        # Basic background
                        current_bg = BASIC_COLORS.get(p - 10, (128, 128, 128))
                    i += 1

                pos = match.end()
            else:
                # Regular character
                chars.append(ColoredChar(line[pos], current_fg, current_bg))
                pos += 1

        result.append(chars)

    return result


def _braille_to_bitmap(char: str) -> NDArray[np.floating]:
    """Convert a braille character to a 4x2 bitmap.

    Args:
        char: Unicode braille character (U+2800-U+28FF)

    Returns:
        4x2 float32 array with 0.0 or 1.0 values.
    """
    code = ord(char) - BRAILLE_START
    bitmap = np.zeros((4, 2), dtype=np.float32)

    # DOT_MAP from braille.py
    dot_map = [
        (0, 0, 0),  # dot 1 -> bit 0
        (1, 0, 1),  # dot 2 -> bit 1
        (2, 0, 2),  # dot 3 -> bit 2
        (3, 0, 6),  # dot 7 -> bit 6
        (0, 1, 3),  # dot 4 -> bit 3
        (1, 1, 4),  # dot 5 -> bit 4
        (2, 1, 5),  # dot 6 -> bit 5
        (3, 1, 7),  # dot 8 -> bit 7
    ]

    for row, col, bit in dot_map:
        if code & (1 << bit):
            bitmap[row, col] = 1.0

    return bitmap


def _quadrant_to_bitmap(char: str) -> NDArray[np.floating]:
    """Convert a quadrant block character to a 2x2 bitmap.

    Args:
        char: Unicode quadrant character

    Returns:
        2x2 float32 array with 0.0 or 1.0 values.
    """
    pattern = QUADRANT_CHARS.get(char, 0)
    bitmap = np.zeros((2, 2), dtype=np.float32)

    # Bit positions: TL=8, TR=4, BL=2, BR=1
    if pattern & 8:
        bitmap[0, 0] = 1.0  # TL
    if pattern & 4:
        bitmap[0, 1] = 1.0  # TR
    if pattern & 2:
        bitmap[1, 0] = 1.0  # BL
    if pattern & 1:
        bitmap[1, 1] = 1.0  # BR

    return bitmap


def _build_sextant_reverse_table() -> dict[str, int]:
    """Build reverse lookup from sextant chars to unicode pattern."""
    table = {}

    # Special patterns
    table[" "] = 0
    table["█"] = 63
    table["▌"] = 21  # Left half
    table["▐"] = 42  # Right half

    # Build sextant chars
    for unicode_pattern in range(1, 63):
        if unicode_pattern in (21, 42):
            continue
        offset = sum(1 for x in (21, 42) if x < unicode_pattern)
        char = chr(0x1FB00 + unicode_pattern - 1 - offset)
        table[char] = unicode_pattern

    return table


SEXTANT_REVERSE = _build_sextant_reverse_table()


def _sextant_to_bitmap(char: str) -> NDArray[np.floating]:
    """Convert a sextant block character to a 3x2 bitmap.

    Args:
        char: Unicode sextant character

    Returns:
        3x2 float32 array with 0.0 or 1.0 values.
    """
    unicode_pattern = SEXTANT_REVERSE.get(char, 0)
    bitmap = np.zeros((3, 2), dtype=np.float32)

    # Unicode sextant bit layout:
    # cell_i contributes 2^i where layout is:
    # 0 1
    # 2 3
    # 4 5
    for i in range(6):
        if unicode_pattern & (1 << i):
            row = i // 2
            col = i % 2
            bitmap[row, col] = 1.0

    return bitmap


def _ascii_to_brightness(char: str, charset: str = DEFAULT_CHARSET) -> float:
    """Convert ASCII character to brightness value.

    Args:
        char: ASCII character
        charset: Character set from dark to bright

    Returns:
        Brightness value 0.0-1.0
    """
    if char in charset:
        idx = charset.index(char)
        return idx / max(1, len(charset) - 1)
    # Unknown char -> middle brightness
    return 0.5


def detect_format(text: str) -> Literal["braille", "quadrants", "sextants", "ascii"] | None:
    """Auto-detect the terminal art format.

    Args:
        text: Terminal art text (with or without ANSI codes)

    Returns:
        Detected format name, or None if unknown.
    """
    # Strip ANSI codes for detection
    stripped = ANSI_ESCAPE.sub("", text)

    braille_count = 0
    quadrant_count = 0
    sextant_count = 0
    ascii_count = 0

    for char in stripped:
        cp = ord(char)
        if BRAILLE_START <= cp <= BRAILLE_END:
            braille_count += 1
        elif char in QUADRANT_CHARS:
            quadrant_count += 1
        elif char in SEXTANT_REVERSE:
            sextant_count += 1
        elif char.isascii() and char.isprintable():
            ascii_count += 1

    # Determine dominant format
    counts: dict[Literal["braille", "quadrants", "sextants", "ascii"], int] = {
        "braille": braille_count,
        "quadrants": quadrant_count,
        "sextants": sextant_count,
        "ascii": ascii_count,
    }

    if all(c == 0 for c in counts.values()):
        return None

    # Find key with maximum count
    best: Literal["braille", "quadrants", "sextants", "ascii"] = "braille"
    best_count = 0
    for fmt, count in counts.items():
        if count > best_count:
            best = fmt
            best_count = count
    return best


def from_ansi(
    text: str,
    format: Literal["braille", "quadrants", "sextants", "ascii"] | None = None,
    charset: str = DEFAULT_CHARSET,
) -> "Canvas":
    """Parse ANSI-colored terminal art back to Canvas.

    Args:
        text: Terminal art text with potential ANSI color codes.
        format: Force specific format, or None to auto-detect.
        charset: Character set for ASCII format (dark to bright).

    Returns:
        Canvas with reconstructed bitmap and colors.

    Raises:
        ValueError: If format cannot be detected or is unsupported.

    Example:
        >>> from dapple.adapters.ansi import from_ansi
        >>> canvas = from_ansi("⠿⠿⠿")
        >>> canvas.bitmap.shape
        (4, 6)
    """
    from dapple import Canvas

    if format is None:
        format = detect_format(text)
        if format is None:
            raise ValueError("Could not detect terminal art format")

    # Parse colors
    grid = parse_colors(text)

    if not grid or not grid[0]:
        raise ValueError("Empty terminal art")

    # Determine cell dimensions
    if format == "braille":
        cell_h, cell_w = 4, 2
    elif format == "quadrants":
        cell_h, cell_w = 2, 2
    elif format == "sextants":
        cell_h, cell_w = 3, 2
    elif format == "ascii":
        cell_h, cell_w = 2, 1
    else:
        raise ValueError(f"Unsupported format: {format}")

    # Calculate dimensions
    rows = len(grid)
    cols = max(len(row) for row in grid) if grid else 0

    height = rows * cell_h
    width = cols * cell_w

    bitmap = np.zeros((height, width), dtype=np.float32)
    colors = np.zeros((height, width, 3), dtype=np.float32)

    for row_idx, row in enumerate(grid):
        for col_idx, cchar in enumerate(row):
            char = cchar.char

            # Skip ANSI-stripped empty content
            if not char or char == "\n":
                continue

            # Convert character to bitmap
            if format == "braille":
                cp = ord(char)
                if BRAILLE_START <= cp <= BRAILLE_END:
                    cell_bitmap = _braille_to_bitmap(char)
                else:
                    cell_bitmap = np.zeros((cell_h, cell_w), dtype=np.float32)
            elif format == "quadrants":
                if char in QUADRANT_CHARS:
                    cell_bitmap = _quadrant_to_bitmap(char)
                else:
                    cell_bitmap = np.zeros((cell_h, cell_w), dtype=np.float32)
            elif format == "sextants":
                if char in SEXTANT_REVERSE:
                    cell_bitmap = _sextant_to_bitmap(char)
                else:
                    cell_bitmap = np.zeros((cell_h, cell_w), dtype=np.float32)
            elif format == "ascii":
                brightness = _ascii_to_brightness(char, charset)
                cell_bitmap = np.full((cell_h, cell_w), brightness, dtype=np.float32)

            # Place in output
            y = row_idx * cell_h
            x = col_idx * cell_w
            if y + cell_h <= height and x + cell_w <= width:
                bitmap[y : y + cell_h, x : x + cell_w] = cell_bitmap

                # Apply color
                if cchar.fg:
                    fg_normalized = np.array(cchar.fg, dtype=np.float32) / 255.0
                    # Color active pixels
                    mask = cell_bitmap > 0.5
                    for c in range(3):
                        colors[y : y + cell_h, x : x + cell_w, c][mask] = fg_normalized[c]
                else:
                    # Default white for active pixels
                    mask = cell_bitmap > 0.5
                    colors[y : y + cell_h, x : x + cell_w][mask] = 1.0

    return Canvas(bitmap, colors=colors)


@dataclass
class ANSIAdapter:
    """Adapter for parsing ANSI terminal art.

    The text to parse is stored at construction so that ``to_canvas()`` takes
    no arguments — matching the :class:`Adapter` protocol that every other
    adapter (PIL, numpy, matplotlib, cairo) implements.

    Attributes:
        text: ANSI-colored terminal art to parse.
        format: Force specific format (None for auto-detect).
        charset: ASCII charset for density mapping.

    Example:
        >>> from dapple.adapters.ansi import ANSIAdapter
        >>> adapter = ANSIAdapter("⠿⠿⠿", format="braille")
        >>> canvas = adapter.to_canvas()
    """

    text: str
    format: Literal["braille", "quadrants", "sextants", "ascii"] | None = None
    charset: str = DEFAULT_CHARSET

    def to_canvas(self) -> "Canvas":
        """Parse the stored terminal art and return a Canvas."""
        return from_ansi(self.text, format=self.format, charset=self.charset)

    def parse(self, text: str | None = None) -> "Canvas":
        """Parse terminal art to Canvas.

        Args:
            text: Override the stored text for a one-off parse. If omitted,
                uses the text supplied at construction.

        Returns:
            Canvas with bitmap and colors.
        """
        return from_ansi(
            text if text is not None else self.text,
            format=self.format,
            charset=self.charset,
        )
