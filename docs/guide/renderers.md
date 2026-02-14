# Renderers

dapple ships seven renderers. Each converts a bitmap into terminal output using a different encoding strategy, from pure ASCII text to true pixel protocols.

## Overview

| Renderer      | Cell Size | Pixels/Char | Color           | Requirements            |
|---------------|-----------|-------------|-----------------|-------------------------|
| `braille`     | 2 x 4     | 8           | none / grayscale / truecolor | Unicode braille support |
| `quadrants`   | 2 x 2     | 4           | 256-color or 24-bit RGB      | Unicode block elements  |
| `sextants`    | 2 x 3     | 6           | 256-color or 24-bit RGB      | Unicode 13.0+ (sextant block elements) |
| `ascii`       | 1 x 2     | 2           | none            | Any terminal            |
| `sixel`       | 1 x 1     | 1 (pixel)   | palette (up to 256 colors)   | xterm -ti vt340, mlterm, foot, WezTerm |
| `kitty`       | 1 x 1     | 1 (pixel)   | 24-bit RGB      | Kitty, WezTerm, Ghostty |
| `fingerprint` | 8 x 16    | 128         | none            | PIL (pillow) for glyph rendering |

**Cell size** is `width x height` in pixels. A braille character covers a 2-wide by 4-tall region of the input bitmap. Smaller cells mean higher effective resolution relative to the terminal grid.

## Choosing a Renderer

### By terminal capabilities

```
Does the terminal support Kitty graphics protocol?
  YES --> kitty (best possible quality — true pixels, 24-bit color)
  NO  --> Does the terminal support Sixel?
            YES --> sixel (true pixels, palette-based color)
            NO  --> Use a character renderer (see below)
```

Kitty and sixel produce actual pixels — they look the best. But they only work in terminals that support the respective protocol, and they break in many contexts (SSH, tmux, screen, CI, Claude Code TUI, piped output). When pixel protocols are unavailable, you're choosing between character renderers.

### By content type: sextants vs braille

The two practical character renderers are **sextants** and **braille**. The choice depends on what you're rendering:

| Content type | Best renderer | Why |
|-------------|--------------|-----|
| Photos, images | **sextants** | Fills cells with color — backgrounds look solid, continuous tone |
| PDFs, scanned pages | **sextants** | Layouts have backgrounds, color, filled regions |
| Video frames | **sextants** | Photographic content needs filled cells |
| Screenshots, diagrams | **sextants** | Colored UI elements, filled shapes |
| Math function plots | **braille** | Line art on empty background — crisper lines |
| Data charts (line, scatter) | **braille** | Sparse lines benefit from higher dot density |
| Line drawings, wireframes | **braille** | Pure geometry, no fill needed |

**Why not always sextants?** Braille has higher resolution (2x4 = 8 dots vs 2x3 = 6 sub-cells per character) and produces crisper lines. For plots and line art where the background is empty, braille gives sharper detail.

**Why not always braille?** Braille characters are *dots* — they can't fill a cell. Backgrounds appear as gaps between dots. A photo rendered in braille looks like a stipple drawing. Sextants (2x3 sub-cells per character) can fill entire regions, so continuous-tone content looks solid and readable.

**Why not quadrants?** Sextants are strictly better — same two-color foreground/background approach but 50% more vertical resolution (2x3 vs 2x2). Quadrants exist mainly for terminals with older Unicode support that lack sextant characters (pre-Unicode 13.0).

**What about ASCII?** Maximum compatibility but lowest quality. Only useful when Unicode support is uncertain (ancient terminals, certain logging contexts).

### Decision summary

```
Pixel protocols available?
  YES --> kitty (if supported), else sixel
  NO  --> Is the content photographic / filled?
            YES --> sextants
            NO  --> Is it line art / plots / sparse?
                      YES --> braille
                      NO  --> sextants (safe default)
```

For automated selection, use `auto_renderer()` from `dapple.auto`. See the [Auto-Detection guide](auto-detection.md).

## The Renderer Protocol

All renderers implement a `runtime_checkable` Protocol:

```python
from typing import Protocol, TextIO, runtime_checkable
import numpy as np
from numpy.typing import NDArray

@runtime_checkable
class Renderer(Protocol):
    @property
    def cell_width(self) -> int: ...

    @property
    def cell_height(self) -> int: ...

    def render(
        self,
        bitmap: NDArray[np.floating],
        colors: NDArray[np.floating] | None = None,
        *,
        dest: TextIO,
    ) -> None: ...
```

- **`cell_width`** / **`cell_height`**: how many bitmap pixels each output character covers.
- **`render`**: writes output directly to `dest`. Does not return a string.

## Stream-Based Output

Renderers write to a `TextIO` stream rather than returning strings. This design enables:

- **Streaming**: output begins before the full image is processed.
- **Memory efficiency**: no intermediate string allocation for large outputs.
- **Flexible destinations**: stdout, files, StringIO, network sockets.

```python
import sys
from io import StringIO
from dapple import Canvas, braille

canvas = Canvas(bitmap)

# Direct to stdout
braille.render(bitmap, colors=None, dest=sys.stdout)

# Capture to string
buf = StringIO()
braille.render(bitmap, colors=None, dest=buf)
text = buf.getvalue()

# Usually you go through Canvas.out() instead:
canvas.out(braille)                # stdout
canvas.out(braille, "output.txt")  # file
canvas.out(braille, buf)           # stream
```

## Frozen Dataclass Pattern

Every renderer is a frozen (immutable) dataclass with a `__call__` method that creates a new instance with modified options.

```python
from dapple import braille

# Default instance
braille.threshold   # 0.5
braille.color_mode  # "none"

# Create a variant
custom = braille(threshold=0.3, color_mode="truecolor")
custom.threshold    # 0.3
custom.color_mode   # "truecolor"

# Original is unchanged
braille.threshold   # still 0.5
```

This pattern avoids mutable state. Each call returns a new renderer; the default singleton is never modified.

---

## Braille

Unicode braille characters (U+2800--U+28FF) encode a 2x4 dot pattern into a single codepoint. Each character represents 8 binary pixels, giving the highest pseudo-pixel density of any character-based renderer.

### Options

| Option       | Type    | Default | Description                                   |
|--------------|---------|---------|-----------------------------------------------|
| `threshold`  | `float\|None` | `0.5` | Brightness cutoff for dot activation. `None` for auto (uses bitmap mean). |
| `color_mode` | `str`   | `"none"` | `"none"`, `"grayscale"` (256-color), or `"truecolor"` (24-bit RGB) |

### Usage

```python
from dapple import Canvas, braille

canvas = Canvas(bitmap)

# Plain braille (no color)
canvas.out(braille)

# Lower threshold -- more dots activated
canvas.out(braille(threshold=0.3))

# Auto threshold based on image mean
canvas.out(braille(threshold=None))

# Grayscale tinting (256-color ANSI)
canvas.out(braille(color_mode="grayscale"))

# Full RGB color per character
canvas.out(braille(color_mode="truecolor"))
```

### How it works

The bitmap is divided into 4-row by 2-column blocks. Each pixel in the block is compared against the threshold. Activated pixels set bits in the braille codepoint offset (U+2800 + bit pattern). The bit layout follows the Unicode standard:

```
col 0  col 1
  0      3     bits 0, 3
  1      4     bits 1, 4
  2      5     bits 2, 5
  6      7     bits 6, 7
```

In color modes, the average brightness or average RGB of each block is used to set the ANSI foreground color for that character.

---

## Quadrants

Quadrant block characters use 16 Unicode block elements to represent a 2x2 pixel region. Combined with ANSI foreground and background colors, each character conveys both shape and two distinct tones or colors.

### Options

| Option       | Type   | Default | Description                                     |
|--------------|--------|---------|-------------------------------------------------|
| `true_color` | `bool` | `True`  | Use 24-bit RGB (`True`) or 256-color mode (`False`) |
| `grayscale`  | `bool` | `False` | Force grayscale even when RGB colors are available  |

### Usage

```python
from dapple import Canvas, quadrants

canvas = Canvas(bitmap, colors=rgb)

# Default: 24-bit true color
canvas.out(quadrants)

# 256-color mode (wider terminal compatibility)
canvas.out(quadrants(true_color=False))

# Force grayscale
canvas.out(quadrants(grayscale=True))
```

### Character table

The 16 quadrant patterns, indexed by a 4-bit value (TL=8, TR=4, BL=2, BR=1):

| Pattern | Char | Description  |
|---------|------|--------------|
| `0000`  | ` `  | Empty        |
| `0001`  | `▗`  | Bottom-right |
| `0010`  | `▖`  | Bottom-left  |
| `0011`  | `▄`  | Lower half   |
| `0100`  | `▝`  | Top-right    |
| `0101`  | `▐`  | Right half   |
| `0110`  | `▞`  | Diagonal     |
| `0111`  | `▟`  | Missing TL   |
| `1000`  | `▘`  | Top-left     |
| `1001`  | `▚`  | Diagonal     |
| `1010`  | `▌`  | Left half    |
| `1011`  | `▙`  | Missing TR   |
| `1100`  | `▀`  | Upper half   |
| `1101`  | `▜`  | Missing BL   |
| `1110`  | `▛`  | Missing BR   |
| `1111`  | `█`  | Full block   |

### How it works

The bitmap is reshaped into 2x2 blocks. For each block, the renderer computes:

1. The brightest and darkest pixel values (or colors).
2. A threshold at the midpoint between them.
3. A 4-bit pattern from which pixels exceed the threshold.
4. ANSI foreground (bright color) and background (dark color) escape codes.

The output is the block character with foreground and background set to the two representative colors of that 2x2 region.

---

## Sextants

Sextant block characters (U+1FB00--U+1FB3B plus standard block elements) represent a 2x3 pixel region -- 6 pixels per character. This provides 50% more vertical resolution than quadrants while using the same two-color foreground/background approach.

### Options

| Option       | Type   | Default | Description                                     |
|--------------|--------|---------|-------------------------------------------------|
| `true_color` | `bool` | `True`  | Use 24-bit RGB or 256-color mode                |
| `grayscale`  | `bool` | `False` | Force grayscale even when RGB colors are available |

### Usage

```python
from dapple import Canvas, sextants

canvas = Canvas(bitmap, colors=rgb)
canvas.out(sextants)
canvas.out(sextants(true_color=False))
```

### Requirements

Sextant characters were added in Unicode 13.0 (2020). Most modern terminal emulators and fonts support them, but older systems may render them as missing-glyph boxes.

---

## ASCII

Maps pixel brightness to ASCII characters using a configurable character ramp. Uses 1x2 pixel sampling (one column wide, two rows tall) to correct for the typical 2:1 height-to-width aspect ratio of terminal characters.

### Options

| Option    | Type   | Default            | Description                              |
|-----------|--------|--------------------|------------------------------------------|
| `charset` | `str`  | `" .:-=+*#%@"`     | Characters from dark to bright           |
| `invert`  | `bool` | `False`            | Invert brightness mapping                |

### Built-in charsets

```python
from dapple.renderers.ascii import (
    CHARSET_STANDARD,   # " .:-=+*#%@"         (10 levels)
    CHARSET_DETAILED,   # " .'`^\",:;Il!..."    (70 levels)
    CHARSET_BLOCKS,     # " ░▒▓█"              (5 levels, Unicode)
    CHARSET_SIMPLE,     # " .oO@"              (5 levels)
)
```

### Usage

```python
from dapple import Canvas, ascii

canvas = Canvas(bitmap)

# Default charset
canvas.out(ascii)

# Minimal charset
canvas.out(ascii(charset=" .oO@"))

# Detailed charset for high-resolution output
canvas.out(ascii(charset=CHARSET_DETAILED))

# Inverted (bright background, dark foreground)
canvas.out(ascii(invert=True))
```

### Why 1x2 cells

Terminal characters are roughly twice as tall as they are wide. Sampling two rows of pixels per output character keeps the aspect ratio correct. Without this correction, images would appear vertically stretched.

---

## Sixel

Sixel is a bitmap graphics protocol from DEC (1984). Each "character" in the output encodes a 1x6 vertical pixel column. The terminal interprets the escape sequence and renders actual pixels. This is a true pixel renderer -- no character approximation.

### Options

| Option       | Type  | Default | Description                              |
|--------------|-------|---------|------------------------------------------|
| `max_colors` | `int` | `256`   | Maximum colors in the quantized palette  |
| `scale`      | `int` | `1`     | Pixel scaling factor (2 = double size)   |

### Usage

```python
from dapple import Canvas, sixel

canvas = Canvas(bitmap, colors=rgb)

# Default
canvas.out(sixel)

# Fewer colors (faster, smaller output)
canvas.out(sixel(max_colors=64))

# Scaled up (each pixel becomes 2x2)
canvas.out(sixel(scale=2))
```

### Supported terminals

Sixel is supported by xterm (with `-ti vt340` flag), mlterm, foot, WezTerm, mintty, contour, and yaft.

### How it works

1. Colors are quantized to a palette using uniform binning.
2. The palette is defined in the DCS (Device Control String) header.
3. For each 6-pixel-tall band, pixels are encoded per color: for each color in the palette, a mask is generated and encoded as sixel characters (0x3F + 6-bit pattern).
4. Run-length encoding compresses repeated columns.

The output is wrapped in `ESC P q ... ESC \` escape sequences.

---

## Kitty

The Kitty graphics protocol is a modern standard for inline terminal images. It transmits image data as base64-encoded PNG, RGB, or RGBA, chunked into 4096-byte segments. This is a true pixel renderer with full 24-bit color.

### Options

| Option        | Type   | Default | Description                                     |
|---------------|--------|---------|-------------------------------------------------|
| `format`      | `str`  | `"png"` | `"png"`, `"rgb"`, or `"rgba"`                   |
| `compression` | `bool` | `True`  | Use zlib compression for raw formats             |
| `columns`     | `int\|None` | `None` | Display width in terminal columns (None = native) |
| `rows`        | `int\|None` | `None` | Display height in terminal rows (None = native)   |

### Usage

```python
from dapple import Canvas, kitty

canvas = Canvas(bitmap, colors=rgb)

# Default: PNG format
canvas.out(kitty)

# Raw RGB (faster encoding, larger payload)
canvas.out(kitty(format="rgb"))

# Scale to fit 80 columns
canvas.out(kitty(columns=80))
```

### Supported terminals

Kitty, WezTerm, Ghostty, and Konsole (partial support).

### How it works

1. The bitmap/colors are encoded as PNG (using PIL if available, otherwise a minimal built-in PNG encoder) or raw RGB/RGBA bytes.
2. Raw formats can be zlib-compressed.
3. The encoded data is base64-encoded and split into chunks of up to 4096 bytes.
4. Each chunk is wrapped in `ESC _G <params>;data ESC \` with `m=1` for continuation chunks and `m=0` for the final chunk.

---

## Fingerprint

An experimental renderer that matches bitmap regions to the visually closest Unicode glyph. Instead of mapping brightness to characters (like ASCII), it pre-renders candidate glyphs to small bitmaps and finds the one with minimum mean squared error against each input region.

### Options

| Option        | Type   | Default   | Description                                      |
|---------------|--------|-----------|--------------------------------------------------|
| `glyph_set`   | `str`  | `"basic"` | `"basic"`, `"blocks"`, `"braille"`, or `"extended"` |
| `cell_width`  | `int`  | `8`       | Pixels per character horizontally                |
| `cell_height` | `int`  | `16`      | Pixels per character vertically                  |
| `metric`      | `str`  | `"mse"`   | `"mse"` (mean squared error) or `"mae"` (mean absolute error) |
| `font_path`   | `str\|None` | `None` | Path to a TTF/OTF font file for glyph rendering  |

### Glyph sets

| Set          | Characters | Description                                   |
|--------------|------------|-----------------------------------------------|
| `"basic"`    | 95         | ASCII printable characters (0x20--0x7E)       |
| `"blocks"`   | ~150       | Block elements, box drawing, quadrants        |
| `"braille"`  | 256        | All braille patterns (U+2800--U+28FF)         |
| `"extended"` | ~500       | Combination of all the above                  |

### Usage

```python
from dapple import Canvas, fingerprint

canvas = Canvas(bitmap)

# Default: ASCII characters, 8x16 cells
canvas.out(fingerprint)

# Block elements for geometric output
canvas.out(fingerprint(glyph_set="blocks"))

# Smaller cells for higher resolution
canvas.out(fingerprint(cell_width=6, cell_height=12))

# Custom font
canvas.out(fingerprint(font_path="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
```

### How it works

1. On first use, all glyphs in the selected set are rendered to small bitmaps using PIL's text drawing.
2. The glyph bitmaps are stacked into a `(N, pixels_per_cell)` array and cached.
3. The input bitmap is divided into cells and each cell is flattened to a vector.
4. MSE (or MAE) distances are computed between each input cell and all glyph bitmaps using vectorized numpy operations.
5. The glyph with minimum distance is selected for each cell.

The output is font-dependent: the same image rendered with different fonts or cell sizes produces different character selections.

> **Note:** Fingerprint requires pillow for rendering glyph bitmaps. Install with `pip install pillow`.

---

## What Dapple Does and Does Not Do

**dapple handles:**
- Bitmap to terminal character conversion
- Color quantization and ANSI escape code generation
- Stream-based output to any `TextIO` destination
- Composition (hstack, vstack, overlay, crop)
- Preprocessing (contrast, dithering, sharpening, gamma)

**dapple does not handle:**
- Image loading/decoding (that is in adapters, which depend on pillow)
- Terminal size detection or automatic resizing to fit the terminal
- Cursor positioning or TUI layout
- Animation or interactive display
- Image format encoding (beyond what is needed for sixel/kitty protocols)

For image loading, use the [adapters](adapters.md). For CLI tools that handle resizing and display, see the extras (imgcat, funcat, pdfcat, etc.).
