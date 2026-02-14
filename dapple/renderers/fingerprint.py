"""Fingerprint renderer - Glyph matching via visual similarity.

Experimental renderer that matches bitmap regions to the closest Unicode glyph
by minimizing visual distance (MSE). Pre-renders candidate glyphs to small
bitmaps and finds the best match for each input region.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TextIO

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Glyph set definitions
GLYPH_SETS = {
    # ASCII printable characters (classic ASCII art)
    "basic": "".join(chr(i) for i in range(32, 127)),
    # Block elements and box drawing
    "blocks": (
        " ▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏▐░▒▓"
        "─━│┃┄┅┆┇┈┉┊┋┌┍┎┏┐┑┒┓└┕┖┗┘┙┚┛├┝┞┟┠┡┢┣┤┥┦┧┨┩┪┫┬┭┮┯┰┱┲┳┴┵┶┷┸┹┺┻┼┽┾┿╀╁╂╃╄╅╆╇╈╉╊╋"
        "╌╍╎╏═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬"
        "▖▗▘▙▚▛▜▝▞▟"
    ),
    # Braille patterns (all 256)
    "braille": "".join(chr(0x2800 + i) for i in range(256)),
    # Extended: combination of all above
    "extended": None,  # Built dynamically
}

# Build extended set
GLYPH_SETS["extended"] = (
    GLYPH_SETS["basic"] + GLYPH_SETS["blocks"] + GLYPH_SETS["braille"]
)


def _render_glyph_bitmap(
    char: str,
    width: int,
    height: int,
    font_path: str | None = None,
) -> NDArray[np.floating]:
    """Render a single character to a grayscale bitmap.

    Args:
        char: Single character to render.
        width: Output bitmap width in pixels.
        height: Output bitmap height in pixels.
        font_path: Optional path to TTF/OTF font file.

    Returns:
        2D numpy array of shape (height, width) with values 0.0-1.0.

    Raises:
        ImportError: If PIL is not available.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise ImportError(
            "fingerprint renderer requires PIL. Install with: pip install pillow"
        ) from e

    # Create image with white background
    img = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(img)

    # Load font
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    if font_path:
        font = ImageFont.truetype(font_path, size=height - 2)
    else:
        # Try to use a monospace font, fall back to default
        try:
            font = ImageFont.truetype("DejaVuSansMono.ttf", size=height - 2)
        except OSError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size=height - 2)
            except OSError:
                try:
                    font = ImageFont.truetype("Consolas.ttf", size=height - 2)
                except OSError:
                    # Last resort: PIL's built-in font
                    font = ImageFont.load_default()

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), char, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center the character
    x = (width - text_width) // 2 - bbox[0]
    y = (height - text_height) // 2 - bbox[1]

    # Draw character in black on white background
    draw.text((x, y), char, font=font, fill=0)

    # Convert to numpy array and normalize to 0-1 (invert so black=1, white=0)
    arr = np.array(img, dtype=np.float32) / 255.0
    return 1.0 - arr  # Invert: ink (dark) becomes high value


class GlyphCache:
    """Lazy-loaded cache of pre-rendered glyph bitmaps."""

    def __init__(
        self,
        glyph_set: str,
        cell_width: int,
        cell_height: int,
        font_path: str | None = None,
    ):
        self.glyph_set = glyph_set
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.font_path = font_path
        self._cache: dict[str, NDArray[np.floating]] | None = None
        self._glyphs: str | None = None
        self._bitmap_stack: NDArray[np.floating] | None = None

    def _ensure_loaded(self) -> None:
        """Load glyph bitmaps on first access."""
        if self._cache is not None:
            return

        glyphs = GLYPH_SETS.get(self.glyph_set)
        if glyphs is None:
            raise ValueError(f"Unknown glyph set: {self.glyph_set}")

        self._glyphs = glyphs
        self._cache = {}

        # Pre-render all glyphs
        bitmaps = []
        for char in glyphs:
            try:
                bitmap = _render_glyph_bitmap(
                    char, self.cell_width, self.cell_height, self.font_path
                )
                self._cache[char] = bitmap
                bitmaps.append(bitmap.flatten())
            except Exception:
                # Skip glyphs that fail to render
                continue

        # Stack all bitmaps for vectorized comparison
        if bitmaps:
            self._bitmap_stack = np.array(bitmaps, dtype=np.float32)
            self._glyphs = "".join(self._cache.keys())

    @property
    def glyphs(self) -> str:
        """Get the string of all cached glyphs."""
        self._ensure_loaded()
        return self._glyphs or ""

    @property
    def bitmap_stack(self) -> NDArray[np.floating]:
        """Get stacked array of all glyph bitmaps (N, cell_width*cell_height)."""
        self._ensure_loaded()
        if self._bitmap_stack is None:
            raise RuntimeError("No glyphs were successfully rendered")
        return self._bitmap_stack


# Global cache for glyph bitmaps (keyed by (glyph_set, cell_width, cell_height))
_glyph_caches: dict[tuple[str, int, int, str | None], GlyphCache] = {}


def _get_glyph_cache(
    glyph_set: str,
    cell_width: int,
    cell_height: int,
    font_path: str | None = None,
) -> GlyphCache:
    """Get or create a glyph cache for the given parameters."""
    key = (glyph_set, cell_width, cell_height, font_path)
    if key not in _glyph_caches:
        _glyph_caches[key] = GlyphCache(glyph_set, cell_width, cell_height, font_path)
    return _glyph_caches[key]


@dataclass(frozen=True)
class FingerprintRenderer:
    """Render bitmap by matching regions to closest Unicode glyphs.

    Each output character is chosen by finding the glyph whose pre-rendered
    bitmap most closely matches the corresponding region of the input bitmap.
    This creates ASCII art that attempts to preserve visual structure.

    Attributes:
        glyph_set: Which characters to use for matching.
            - "basic": ASCII printable (32-126, 95 characters) - classic ASCII art
            - "blocks": Block elements and box drawing - geometric shapes
            - "braille": Braille patterns (U+2800-U+28FF) - high detail dots
            - "extended": All of the above combined
        cell_width: Pixels per character horizontally (default 8).
        cell_height: Pixels per character vertically (default 16).
        metric: Distance metric for matching.
            - "mse": Mean squared error (default)
            - "mae": Mean absolute error
        font_path: Optional path to TTF/OTF font for glyph rendering.

    Example:
        >>> from dapple import Canvas, fingerprint
        >>> canvas = Canvas(np.random.rand(48, 80))
        >>> canvas.out(fingerprint)                     # to stdout
        >>> canvas.out(fingerprint(glyph_set="blocks")) # use blocks
    """

    glyph_set: str = "basic"
    cell_width: int = 8
    cell_height: int = 16
    metric: Literal["mse", "mae"] = "mse"
    font_path: str | None = None

    def __call__(
        self,
        glyph_set: str | None = None,
        cell_width: int | None = None,
        cell_height: int | None = None,
        metric: Literal["mse", "mae"] | None = None,
        font_path: str | None = None,
    ) -> FingerprintRenderer:
        """Create a new renderer with modified options.

        Args:
            glyph_set: Character set for matching (None to keep current)
            cell_width: Cell width in pixels (None to keep current)
            cell_height: Cell height in pixels (None to keep current)
            metric: Distance metric (None to keep current)
            font_path: Font file path (None to keep current)

        Returns:
            New FingerprintRenderer with updated settings.
        """
        return FingerprintRenderer(
            glyph_set=glyph_set if glyph_set is not None else self.glyph_set,
            cell_width=cell_width if cell_width is not None else self.cell_width,
            cell_height=cell_height if cell_height is not None else self.cell_height,
            metric=metric if metric is not None else self.metric,
            font_path=font_path if font_path is not None else self.font_path,
        )

    def render(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating] | None = None,
        *,
        dest: TextIO,
    ) -> None:
        """Render bitmap to stream by matching regions to glyphs.

        Args:
            bitmap: 2D array (H, W) with values 0.0-1.0.
            colors: Optional color array (ignored - fingerprint is grayscale only).
            dest: Stream to write output to.

        Raises:
            ValueError: If bitmap is not 2D.
            ImportError: If PIL is not installed.
        """
        if bitmap.ndim != 2:
            raise ValueError(f"bitmap must be 2D, got shape {bitmap.shape}")

        h, w = bitmap.shape
        rows = h // self.cell_height
        cols = w // self.cell_width

        if rows == 0 or cols == 0:
            return

        # Get glyph cache
        cache = _get_glyph_cache(
            self.glyph_set, self.cell_width, self.cell_height, self.font_path
        )
        glyphs = cache.glyphs
        glyph_bitmaps = cache.bitmap_stack  # Shape: (N, cell_width*cell_height)

        if len(glyphs) == 0:
            raise RuntimeError("No glyphs available for matching")

        # Extract all regions at once
        # Reshape bitmap to (rows, cell_height, cols, cell_width) -> (rows, cols, cell_height, cell_width)
        cropped = bitmap[: rows * self.cell_height, : cols * self.cell_width]
        regions = (
            cropped.reshape(rows, self.cell_height, cols, self.cell_width)
            .transpose(0, 2, 1, 3)
            .reshape(rows * cols, self.cell_height * self.cell_width)
        )

        # Compute distances from each region to all glyphs
        # regions: (R, P) where R = rows*cols, P = pixels per cell
        # glyph_bitmaps: (G, P) where G = number of glyphs
        # distances: (R, G)
        if self.metric == "mse":
            # Vectorized MSE: ||region - glyph||^2 / P
            # Expand dims for broadcasting
            diff = regions[:, np.newaxis, :] - glyph_bitmaps[np.newaxis, :, :]
            distances = (diff ** 2).mean(axis=2)
        else:  # mae
            diff = regions[:, np.newaxis, :] - glyph_bitmaps[np.newaxis, :, :]
            distances = np.abs(diff).mean(axis=2)

        # Find best glyph for each region
        best_indices = distances.argmin(axis=1)

        # Write output
        first_row = True
        for y in range(rows):
            if not first_row:
                dest.write("\n")
            first_row = False

            row_chars = []
            for x in range(cols):
                idx = y * cols + x
                row_chars.append(glyphs[best_indices[idx]])
            dest.write("".join(row_chars))


# Convenience instance for default usage
fingerprint = FingerprintRenderer()
