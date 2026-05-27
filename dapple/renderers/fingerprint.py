"""Fingerprint renderer - Glyph matching via visual similarity.

Renderer that matches bitmap regions to the closest Unicode glyph
by minimizing visual distance (MSE). Pre-renders candidate glyphs to small
bitmaps and finds the best match for each input region. Supports ANSI
foreground and background colors for enhanced visual fidelity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TextIO

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

from dapple.renderers._ansi import (
    RESET,
    color_code as _color_code,
    gray_code as _gray_code,
)

# Glyph set definitions
GLYPH_SETS: dict[str, str] = {
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
    # Geometric shapes (U+25A0-U+25FF)
    "geometric": "".join(chr(i) for i in range(0x25A0, 0x2600)),
    # Math symbols — operators and misc math (selected visually distinct glyphs)
    "math": (
        "∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟"
        "∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿"
        "≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟"
        "≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿"
    ),
    # Sextant characters (U+1FB00-U+1FB3B) + block elements
    "sextants": (
        " "
        + "".join(chr(i) for i in range(0x1FB00, 0x1FB3C))
        + "▌▐█"
    ),
    # Miscellaneous symbols (U+2600-U+26FF) — weather, chess, cards, etc.
    "symbols": "".join(chr(i) for i in range(0x2600, 0x2700)),
    # Dingbats (U+2700-U+27BF)
    "dingbats": "".join(chr(i) for i in range(0x2700, 0x27C0)),
    # Extended: combination of all above
    "extended": "",  # Built dynamically below
    # Full: everything including geometric, math, symbols, dingbats
    "full": "",  # Built dynamically below
}

# Build composite sets
GLYPH_SETS["extended"] = (
    GLYPH_SETS["basic"] + GLYPH_SETS["blocks"] + GLYPH_SETS["braille"]
)
GLYPH_SETS["full"] = (
    GLYPH_SETS["basic"]
    + GLYPH_SETS["blocks"]
    + GLYPH_SETS["braille"]
    + GLYPH_SETS["geometric"]
    + GLYPH_SETS["math"]
    + GLYPH_SETS["sextants"]
    + GLYPH_SETS["symbols"]
    + GLYPH_SETS["dingbats"]
)


def _sextant_pattern(cp: int) -> int | None:
    """Return the 6-bit pattern for a sextant-like character, or None.

    Sextant layout (2 columns × 3 rows, bits numbered row-major):
        bit0 bit1
        bit2 bit3
        bit4 bit5

    The extraction in :func:`_synthetic_sextant_bitmap` is
    ``col = bit % 2; row = bit // 2`` — row-major, matching the visual
    layout above. Covers: space (0), U+1FB00-U+1FB3B (1-60),
    ▌ (0b010101=21→handled), ▐ (0b101010=42→handled), █ (63).
    """
    if cp == 0x20:       # space → all empty
        return 0
    if cp == 0x2588:     # █ → all filled
        return 0b111111
    if cp == 0x258C:     # ▌ left half → left column filled
        return 0b010101
    if cp == 0x2590:     # ▐ right half → right column filled
        return 0b101010
    if 0x1FB00 <= cp <= 0x1FB3B:
        # Unicode encodes sextants as patterns 1-60 (skipping 0, 21, 42, 63
        # which are space, ▌, ▐, █ respectively)
        raw = cp - 0x1FB00 + 1  # 1-based pattern index
        # Adjust for the three skipped codepoints (21, 42, 63 are block chars)
        pattern = raw
        if pattern >= 21:
            pattern += 1  # skip ▌ (pattern 21)
        if pattern >= 42:
            pattern += 1  # skip ▐ (pattern 42)
        return pattern
    return None


def _synthetic_sextant_bitmap(
    pattern: int,
    width: int,
    height: int,
) -> NDArray[np.floating]:
    """Generate a sextant bitmap from its 6-bit pattern.

    Creates a clean 2×3 grid where filled sextant cells are 1.0 and empty
    cells are 0.0. This is pixel-perfect and font-independent.
    """
    bitmap = np.zeros((height, width), dtype=np.float32)
    col_w = width // 2
    row_h = height // 3

    for bit in range(6):
        if pattern & (1 << bit):
            col = bit % 2
            row = bit // 2
            r0 = row * row_h
            r1 = r0 + row_h if row < 2 else height  # last row gets remainder
            c0 = col * col_w
            c1 = c0 + col_w if col < 1 else width  # last col gets remainder
            bitmap[r0:r1, c0:c1] = 1.0

    return bitmap


def _load_font(
    height: int,
    font_path: str | None = None,
) -> tuple:
    """Load a PIL font, returning (font, ImageFont module).

    Tries font_path first, then common monospace fonts, then PIL default.
    """
    from PIL import ImageFont

    if font_path:
        return ImageFont.truetype(font_path, size=height - 2), ImageFont

    for name in (
        "DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "Consolas.ttf",
    ):
        try:
            return ImageFont.truetype(name, size=height - 2), ImageFont
        except OSError:
            continue

    return ImageFont.load_default(), ImageFont


def _render_glyph_bitmap(
    char: str,
    width: int,
    height: int,
    font_path: str | None = None,
) -> NDArray[np.floating]:
    """Render a single character to a grayscale bitmap.

    For sextant characters (U+1FB00-U+1FB3B, space, ▌, ▐, █), generates
    synthetic pixel-perfect bitmaps instead of relying on font rendering.
    This avoids the common problem of fonts lacking sextant glyphs.

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
    # Check for synthetic sextant rendering first
    pattern = _sextant_pattern(ord(char))
    if pattern is not None:
        return _synthetic_sextant_bitmap(pattern, width, height)

    try:
        from PIL import Image, ImageDraw
    except ImportError as e:
        raise ImportError(
            "fingerprint renderer requires PIL. Install with: pip install pillow"
        ) from e

    # Create image with white background
    img = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(img)

    font, _ = _load_font(height, font_path)

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
        self._glyphs_sq_norms: NDArray[np.floating] | None = None

    def _ensure_loaded(self) -> None:
        """Load glyph bitmaps on first access."""
        if self._cache is not None:
            return

        # Try named set first, then treat as custom character string
        glyphs = GLYPH_SETS.get(self.glyph_set)
        if glyphs is None:
            if len(self.glyph_set) >= 2:
                # Treat as custom character string
                glyphs = self.glyph_set
            else:
                raise ValueError(
                    f"Unknown glyph set: {self.glyph_set!r}. "
                    f"Available sets: {', '.join(sorted(GLYPH_SETS))}. "
                    f"Or pass a string of 2+ characters as a custom glyph set."
                )

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_glyphs = []
        for ch in glyphs:
            if ch not in seen:
                seen.add(ch)
                unique_glyphs.append(ch)

        self._cache = {}

        # Pre-render all glyphs
        bitmaps = []
        for char in unique_glyphs:
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
            # Pre-compute squared norms for fast distance computation
            self._glyphs_sq_norms = (self._bitmap_stack ** 2).sum(axis=1)

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

    @property
    def glyphs_sq_norms(self) -> NDArray[np.floating]:
        """Get pre-computed squared norms of glyph bitmaps (N,)."""
        self._ensure_loaded()
        if self._glyphs_sq_norms is None:
            raise RuntimeError("No glyphs were successfully rendered")
        return self._glyphs_sq_norms


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


def clear_glyph_caches() -> None:
    """Drop all cached glyph bitmaps.

    Useful for benchmarking (to time cold cache builds) or for reclaiming
    memory after rendering with large custom glyph sets.
    """
    _glyph_caches.clear()


def warm_glyph_cache(
    glyph_set: str,
    cell_width: int = 8,
    cell_height: int = 16,
    font_path: str | None = None,
) -> int:
    """Pre-build the fingerprint glyph cache for a given configuration.

    Returns the number of glyphs successfully rendered, which may be
    smaller than the requested set if the active font lacks some glyphs.
    """
    cache = _get_glyph_cache(glyph_set, cell_width, cell_height, font_path)
    return len(cache.glyphs)


# Optimal cell sizes for glyph sets with known native renderers.
# Using native dimensions avoids over-averaging in color computation.
_NATIVE_CELL_SIZES: dict[str, tuple[int, int]] = {
    "sextants": (2, 3),
    "braille": (2, 4),
}


@dataclass(frozen=True)
class FingerprintRenderer:
    """Render bitmap by matching regions to closest Unicode glyphs.

    Each output character is chosen by finding the glyph whose pre-rendered
    bitmap most closely matches the corresponding region of the input bitmap.
    Supports ANSI foreground and background colors for enhanced visual fidelity:
    the glyph handles shape, while fg/bg colors handle tone and hue.

    Attributes:
        glyph_set: Which characters to use for matching. Named sets:
            - "basic": ASCII printable (32-126, 95 chars) - classic ASCII art
            - "blocks": Block elements + box drawing - geometric shapes
            - "braille": Braille patterns (U+2800-U+28FF, 256 chars)
            - "geometric": Geometric shapes (U+25A0-U+25FF)
            - "math": Mathematical operators and symbols
            - "sextants": Unicode sextant characters (U+1FB00-U+1FB3B)
            - "symbols": Miscellaneous symbols (U+2600-U+26FF)
            - "dingbats": Dingbats (U+2700-U+27BF)
            - "extended": basic + blocks + braille combined
            - "full": all named sets combined (~1200 chars)
            Or pass a custom string of 2+ characters to use as the glyph set.
        cell_width: Pixels per character horizontally (default 8).
        cell_height: Pixels per character vertically (default 16).
        metric: Distance metric for matching.
            - "mse": Mean squared error (default)
            - "mae": Mean absolute error
        true_color: Use 24-bit RGB instead of 256-color mode (default True).
        grayscale: Force grayscale output even for RGB input (default False).
        font_path: Optional path to TTF/OTF font for glyph rendering.

    Example:
        >>> from dapple import Canvas, fingerprint
        >>> canvas = Canvas(np.random.rand(48, 80))
        >>> canvas.out(fingerprint)                         # plain ASCII art
        >>> canvas.out(fingerprint(glyph_set="full"))       # all Unicode glyphs
        >>> canvas.out(fingerprint(glyph_set=" .:-=+*#%@")) # custom chars
    """

    glyph_set: str = "basic"
    cell_width: int = 8
    cell_height: int = 16
    metric: Literal["mse", "mae"] = "mse"
    true_color: bool = True
    grayscale: bool = False
    font_path: str | None = None

    def __call__(
        self,
        glyph_set: str | None = None,
        cell_width: int | None = None,
        cell_height: int | None = None,
        metric: Literal["mse", "mae"] | None = None,
        true_color: bool | None = None,
        grayscale: bool | None = None,
        font_path: str | None = None,
    ) -> FingerprintRenderer:
        """Create a new renderer with modified options.

        When glyph_set is changed and cell size is not explicitly given,
        auto-selects the optimal cell size for glyph sets with known native
        renderers (e.g. sextants → 2×3, braille → 2×4).
        """
        new_glyph_set = glyph_set if glyph_set is not None else self.glyph_set

        # Auto-select native cell size when glyph_set changes
        new_cw = cell_width if cell_width is not None else self.cell_width
        new_ch = cell_height if cell_height is not None else self.cell_height
        if glyph_set is not None and cell_width is None and cell_height is None:
            native = _NATIVE_CELL_SIZES.get(new_glyph_set)
            if native is not None:
                new_cw, new_ch = native

        return FingerprintRenderer(
            glyph_set=new_glyph_set,
            cell_width=new_cw,
            cell_height=new_ch,
            metric=metric if metric is not None else self.metric,
            true_color=true_color if true_color is not None else self.true_color,
            grayscale=grayscale if grayscale is not None else self.grayscale,
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
            colors: Optional 3D array (H, W, 3) with RGB values 0.0-1.0.
                    When provided (and grayscale=False), renders with ANSI
                    fg/bg colors derived from the image.
            dest: Stream to write output to.

        Raises:
            ValueError: If bitmap is not 2D or colors shape doesn't match.
            ImportError: If PIL is not installed.
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
        rows = h // self.cell_height
        cols = w // self.cell_width

        if rows == 0 or cols == 0:
            return

        # Get glyph cache
        cache = _get_glyph_cache(
            self.glyph_set, self.cell_width, self.cell_height, self.font_path
        )
        glyphs = cache.glyphs
        glyph_bitmaps = cache.bitmap_stack  # Shape: (G, P)

        if len(glyphs) == 0:
            raise RuntimeError("No glyphs available for matching")

        # Extract all regions at once
        cropped = bitmap[: rows * self.cell_height, : cols * self.cell_width]
        regions = (
            cropped.reshape(rows, self.cell_height, cols, self.cell_width)
            .transpose(0, 2, 1, 3)
            .reshape(rows * cols, self.cell_height * self.cell_width)
        )

        # Find best glyph for each region using fast distance computation
        best_indices = self._find_best_glyphs(regions, cache)

        # Determine color mode
        use_color = colors is not None or self.grayscale
        use_rgb = colors is not None and not self.grayscale

        # Compute per-cell colors if needed
        if use_color:
            fg_colors, bg_colors = self._compute_cell_colors(
                bitmap, colors, rows, cols, best_indices, glyph_bitmaps, glyphs
            )

        # Write output
        first_row = True
        for y in range(rows):
            if not first_row:
                dest.write("\n")
            first_row = False

            parts = []
            for x in range(cols):
                idx = y * cols + x
                char = glyphs[best_indices[idx]]

                if not use_color:
                    parts.append(char)
                elif use_rgb:
                    fg = fg_colors[idx]
                    bg = bg_colors[idx]
                    parts.append(
                        f"{_color_code(fg[0], fg[1], fg[2], True, self.true_color)}"
                        f"{_color_code(bg[0], bg[1], bg[2], False, self.true_color)}"
                        f"{char}"
                    )
                else:  # grayscale
                    parts.append(
                        f"{_gray_code(fg_colors[idx], True, self.true_color)}"
                        f"{_gray_code(bg_colors[idx], False, self.true_color)}"
                        f"{char}"
                    )

            row = "".join(parts)
            if use_color:
                row += RESET
            dest.write(row)

    def _find_best_glyphs(
        self,
        regions: NDArray[np.floating],
        cache: GlyphCache,
    ) -> NDArray[np.intp]:
        """Find the best-matching glyph index for each region.

        Normalizes each region to [0, 1] before matching so that glyph
        selection adapts to local contrast (like native sextants' adaptive
        threshold).  Uses expanded squared-distance for MSE:
        ||a - b||^2 = ||a||^2 + ||b||^2 - 2*a.b
        """
        glyph_bitmaps = cache.bitmap_stack

        # Normalize each region to [0, 1] for adaptive local contrast.
        # A region of [0.6, 0.9, 0.7] becomes [0, 1, 0.33] — local structure
        # is preserved regardless of absolute brightness.
        # Uniform regions (span ≈ 0) map to all-ones (full block), matching
        # native sextants/quadrants convention; color handles brightness.
        rmin = regions.min(axis=1, keepdims=True)  # (R, 1)
        rmax = regions.max(axis=1, keepdims=True)  # (R, 1)
        span = rmax - rmin
        normalized = np.where(
            span > 1e-3,
            (regions - rmin) / span.clip(min=1e-6),
            1.0,  # uniform → full block
        )

        if self.metric == "mse":
            # Fast squared-distance via dot products (BLAS-accelerated)
            regions_sq = (normalized ** 2).sum(axis=1)  # (R,)
            glyphs_sq = cache.glyphs_sq_norms  # (G,) — pre-computed
            dot = normalized @ glyph_bitmaps.T  # (R, G) — fast matmul
            distances = regions_sq[:, np.newaxis] + glyphs_sq[np.newaxis, :] - 2.0 * dot
        else:  # mae — no matmul shortcut, use chunked computation
            # Chunk size trades memory for vectorization: 64 rows × G glyphs
            # × P pixels stays under a few MB for typical (G, P) sizes.
            CHUNK_SIZE = 64
            n_regions = normalized.shape[0]
            n_glyphs = glyph_bitmaps.shape[0]
            distances = np.empty((n_regions, n_glyphs), dtype=np.float32)
            for i in range(0, n_regions, CHUNK_SIZE):
                chunk = normalized[i : i + CHUNK_SIZE]
                diff = chunk[:, np.newaxis, :] - glyph_bitmaps[np.newaxis, :, :]
                distances[i : i + CHUNK_SIZE] = np.abs(diff).mean(axis=2)

        return distances.argmin(axis=1)

    def _compute_cell_colors(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating] | None,
        rows: int,
        cols: int,
        best_indices: NDArray[np.intp],
        glyph_bitmaps: NDArray[np.floating],
        glyphs: str,
    ) -> tuple:
        """Compute fg/bg colors per cell using glyph-mask averaging.

        The matched glyph's bitmap divides each cell into foreground (ink)
        and background (paper) regions.  Each region's color is the average
        of the pixels in that group — stable and noise-free even at high
        per-cell pixel counts (e.g. 8×16 = 128 pixels).

        Returns:
            For RGB mode: (fg_colors, bg_colors) each shape (R, 3)
            For grayscale mode: (fg_brightness, bg_brightness) each shape (R,)
        """
        ch = self.cell_height
        cw = self.cell_width
        pixels = ch * cw
        use_rgb = colors is not None and not self.grayscale

        # Extract glyph masks for matched glyphs: (R, P)
        glyph_masks = glyph_bitmaps[best_indices]  # (R, P)
        ink_mask = glyph_masks > 0.5  # Boolean (R, P)
        paper_mask = ~ink_mask

        # Count ink/paper pixels per cell, clamp to at least 1 for safe division
        ink_count = ink_mask.sum(axis=1, keepdims=True).clip(min=1)  # (R, 1)
        paper_count = paper_mask.sum(axis=1, keepdims=True).clip(min=1)  # (R, 1)

        if use_rgb:
            # Extract color regions: (R, P, 3)
            cropped_colors = colors[: rows * ch, : cols * cw]
            color_regions = (
                cropped_colors.reshape(rows, ch, cols, cw, 3)
                .transpose(0, 2, 1, 3, 4)
                .reshape(rows * cols, pixels, 3)
            )

            ink_mask_3 = ink_mask[:, :, np.newaxis]   # (R, P, 1)
            paper_mask_3 = paper_mask[:, :, np.newaxis]

            fg_colors = (color_regions * ink_mask_3).sum(axis=1) / ink_count  # (R, 3)
            bg_colors = (color_regions * paper_mask_3).sum(axis=1) / paper_count

            return fg_colors.clip(0, 1), bg_colors.clip(0, 1)
        else:
            # Grayscale: average brightness in each group
            cropped = bitmap[: rows * ch, : cols * cw]
            brightness_regions = (
                cropped.reshape(rows, ch, cols, cw)
                .transpose(0, 2, 1, 3)
                .reshape(rows * cols, pixels)
            )

            fg_brightness = (brightness_regions * ink_mask).sum(axis=1) / ink_count.squeeze()
            bg_brightness = (brightness_regions * paper_mask).sum(axis=1) / paper_count.squeeze()

            return np.clip(fg_brightness, 0, 1), np.clip(bg_brightness, 0, 1)


# Convenience instance for default usage
fingerprint = FingerprintRenderer()
