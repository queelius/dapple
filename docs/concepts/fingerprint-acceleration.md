# Glyph-Based Image Rendering: Fast Matching via BLAS and Mask-Driven Color Separation

## Problem

The fingerprint renderer converts a raster image into Unicode text art by
partitioning the image into cells and finding, for each cell, the Unicode glyph
whose pre-rendered bitmap most closely matches that region. With **R** image
regions, **G** candidate glyphs, and **P** pixels per cell (e.g., 8×16 = 128),
the naive approach requires computing all R×G pairwise distances — each
involving P pixel comparisons.

## 1. BLAS-Accelerated Glyph Matching

**The naive formulation.** For MSE matching, we want:

```
best[i] = argmin_j  ||region_i - glyph_j||²
```

The textbook implementation broadcasts both matrices into an (R, G, P) tensor,
computes element-wise differences, squares, and sums over P. For a 120×80
character output with the "basic" glyph set (95 glyphs), this means:

```
R = 9,600 regions × G = 95 glyphs × P = 128 pixels = 117M floats
```

At float32, that's ~468 MB of intermediate memory — and it scales linearly with
glyph set size. The "full" set (~1,200 glyphs) would need ~6 GB.

**The algebraic trick.** Expanding the squared Euclidean distance:

```
||a - b||² = ||a||² + ||b||² - 2·a·b
```

Each term has a different computational profile:

| Term | Shape | Cost | Notes |
|------|-------|------|-------|
| `\|\|region_i\|\|²` | (R,) | O(R·P) | Sum of squared pixels per region |
| `\|\|glyph_j\|\|²` | (G,) | O(G·P) | **Pre-computed once** at cache load |
| `region · glyphᵀ` | (R, G) | O(R·G·P) | **Matrix multiply** — BLAS `sgemm` |

The critical insight: the dot-product term `regions @ glyphs.T` is a standard
matrix multiplication. NumPy delegates this to BLAS (OpenBLAS, MKL, or
Accelerate), which uses SIMD, cache-tiled loops, and multi-threading. The full
distance matrix is then assembled from three terms via broadcasting:

```python
distances = regions_sq[:, np.newaxis] + glyphs_sq[np.newaxis, :] - 2.0 * dot
```

This produces an (R, G) matrix — no P dimension ever materializes as an
intermediate. Memory drops from O(R·G·P) to O(R·G), and the compute-intensive
part runs at near-hardware-peak throughput.

**Pre-computation.** The `glyphs_sq_norms` vector is computed once when the
glyph cache is first loaded and reused across all subsequent render calls. Since
glyph bitmaps are deterministic (same font, same cell size), this is a one-time
cost amortized over the renderer's lifetime.

## 2. Adaptive Local Contrast Normalization

Before matching, each image region is normalized to [0, 1]:

```python
normalized = (region - region.min()) / (region.max() - region.min())
```

This is the fingerprint analogue of native renderers' adaptive thresholding
(e.g., sextants threshold at `(max + min) / 2`). Without normalization, MSE
matching uses an implicit global threshold at 0.5 — a region where all pixels
are between 0.6 and 0.9 would match an almost-full-block, discarding the local
structure. After normalization, the same region spans 0.0 to 1.0, and the
matcher sees the internal contrast.

Uniform regions (max ≈ min) are mapped to all-ones (full block), matching the
convention used by native sextants and quadrants renderers. Color handles the
brightness; the glyph handles the shape.

## 3. Glyph-Mask Color Separation

Traditional text-art renderers choose a character for *shape* but have no way to
independently control the color of the "ink" versus the "paper" within that
character cell. Terminal emulators, however, support independent foreground and
background colors via ANSI escape codes. The question is: what colors should
each get?

**The mask.** After matching, we already have the best glyph's bitmap — a
grayscale image where high values represent ink and low values represent paper.
We threshold this at 0.5 to get a binary mask:

```python
glyph_masks = glyph_bitmaps[best_indices]  # (R, P)
ink_mask = glyph_masks > 0.5               # (R, P) boolean
paper_mask = ~ink_mask
```

**Color averaging.** For each cell, we split the source image's RGB pixels into
two groups using the mask, and average each group independently:

```
fg_color = mean(source_pixels where ink_mask is True)
bg_color = mean(source_pixels where ink_mask is False)
```

The vectorized form handles all R cells simultaneously:

```python
ink_mask_3 = ink_mask[:, :, np.newaxis]     # broadcast to (R, P, 3)
fg = (color_regions * ink_mask_3).sum(axis=1) / ink_count   # (R, 3)
bg = (color_regions * ~ink_mask_3).sum(axis=1) / paper_count # (R, 3)
```

**Why this works well.** The glyph was chosen to match the *spatial distribution
of brightness* within the cell. The mask therefore naturally separates the cell
into regions of similar brightness. Within each region, colors tend to be
locally coherent (edges in natural images coincide with both brightness and
color changes). The foreground color captures the hue of the bright or dark
features, and the background captures the rest — giving each cell three
independent channels of information: shape (glyph), foreground color, and
background color.

**Edge case: uniform cells.** When all pixels in a glyph bitmap are on the same
side of the threshold (all-ink or all-paper), one group has zero pixels. We
clamp the count to `max(1, count)` to avoid division by zero, and the
degenerate group inherits a safe default.

## 4. Synthetic Sextant Bitmaps

Sextant characters (U+1FB00–U+1FB3B) represent a 2×3 binary grid — 64 possible
patterns covering all combinations of six cells. Most terminal fonts (DejaVu
Sans Mono, Consolas, etc.) lack these characters entirely; PIL renders them all
as identical "missing glyph" boxes, collapsing 64 patterns down to ~5 unique
bitmaps.

Rather than depending on font coverage, the fingerprint renderer generates
sextant bitmaps synthetically. Each of the 64 patterns is a known 6-bit value
mapping to a 2-column × 3-row grid:

```python
def _synthetic_sextant_bitmap(pattern, width, height):
    bitmap = np.zeros((height, width), dtype=np.float32)
    for bit in range(6):
        if pattern & (1 << bit):
            # fill the corresponding sub-cell
            col, row = bit % 2, bit // 2
            bitmap[row_slice, col_slice] = 1.0
    return bitmap
```

This bypasses PIL entirely for sextant characters, producing pixel-perfect
binary bitmaps that are:
- **Font-independent** — works on any system
- **Perfectly distinct** — all 64 patterns produce unique bitmaps
- **Faster** — array slicing vs. PIL image creation + font rendering

The `_sextant_pattern()` function maps Unicode codepoints to 6-bit patterns,
covering the 60 sextant codepoints plus space (pattern 0), ▌ (left half, 21),
▐ (right half, 42), and █ (full block, 63).

## 5. Native Cell-Size Auto-Selection

Different glyph sets have different natural resolutions. Sextant characters
encode a 2×3 grid; braille encodes a 2×4 grid. When the fingerprint renderer
uses more pixels per cell than the glyph's native resolution (e.g., 8×16 for
sextants), the extra pixels contribute nothing to glyph selection (the same 64
patterns) but degrade color quality through over-averaging.

The renderer auto-selects optimal cell dimensions when a glyph set is specified:

| Glyph set | Auto cell size | Rationale |
|-----------|---------------|-----------|
| `sextants` | 2×3 | Matches native sextant grid |
| `braille` | 2×4 | Matches native braille grid |
| others | 8×16 (default) | Arbitrary glyphs need higher resolution for shape matching |

At native resolution, fingerprint sextants converges to the same visual quality
as the native sextants renderer at comparable speed (~10ms vs ~7ms for an 80-col
image), confirming that the MSE matching + mask averaging pipeline is equivalent
to the native threshold + extreme-value approach when operating at the same
resolution.

Explicit `cell_width`/`cell_height` overrides still work for experimentation.

## 6. Composability and Arbitrary Glyph Sets

The fingerprint renderer's key advantage over native renderers is generality:
**any set of Unicode characters can be used as the glyph vocabulary**. Native
renderers are hard-coded to their character set — sextants can only use 64
sextant patterns, braille can only use 256 braille patterns. Fingerprint treats
every glyph as a bitmap and selects the best visual match, regardless of what
Unicode block it comes from.

This enables:
- **Custom character sets**: `fingerprint(glyph_set=" .:-=+*#%@")` for
  classic ASCII art with hand-chosen density ramp
- **Mixed vocabularies**: the "extended" set combines ASCII + blocks + braille
  (607 glyphs); the "full" set adds geometric, math, sextants, symbols, and
  dingbats (~1,200 glyphs)
- **Domain-specific glyphs**: pass any string of 2+ characters as a custom set

All techniques in this document (BLAS matching, normalization, mask color
separation, synthetic bitmaps) apply uniformly regardless of glyph set.

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Distance computation | O(R·G·P) broadcast | O(R·G) BLAS matmul |
| Memory (9600 regions, 95 glyphs) | ~468 MB intermediate | ~3.6 MB distance matrix |
| Color support | None | fg + bg via glyph mask |
| Local contrast | Global threshold at 0.5 | Adaptive per-region normalization |
| Sextant matching | ~5 unique (font-dependent) | 64 unique (synthetic bitmaps) |
| Cell size | Fixed 8×16 | Auto-selected per glyph set |
| Glyph sets | 1 fixed (basic) | 10 named + custom strings |

The optimizations compose without interference: BLAS acceleration speeds up
matching, normalization adapts to local contrast, mask-driven color separation
adds visual fidelity, synthetic bitmaps bypass font limitations, and auto cell
sizing achieves native-quality convergence — all operating on the same
pre-computed glyph bitmap matrix.
