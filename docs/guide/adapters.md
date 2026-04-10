# Adapters

Adapters bridge external image libraries into dapple's Canvas. Each adapter converts from a specific source format to a Canvas object with the appropriate bitmap and color arrays.

The core dapple library depends only on numpy. Adapters are optional and import their dependencies lazily -- you only need pillow installed if you use the PIL adapter, matplotlib if you use the matplotlib adapter, and so on.

## The Adapter Protocol

All adapters implement a simple protocol:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Adapter(Protocol):
    def to_canvas(self) -> Canvas: ...
```

Each adapter also provides a convenience function (`from_array`, `from_pil`, etc.) that wraps the adapter class in a single call.

## The Framebuffer Pattern

The common pattern across all adapters:

1. Some library renders to a bitmap (numpy array, PIL Image, matplotlib figure, Cairo surface).
2. The adapter extracts the pixel data as a numpy array.
3. For RGB data, luminance is computed using ITU-R BT.601 coefficients: `0.299R + 0.587G + 0.114B`.
4. A Canvas is constructed with the grayscale bitmap and optional RGB colors.

This means any library that can produce a bitmap can feed into dapple. The adapter just handles the conversion.

---

## NumpyAdapter / `from_array`

Converts numpy arrays directly to Canvas. This is the most basic adapter since Canvas already stores numpy arrays internally.

**Dependency:** numpy (always available -- it is a core dependency).

### Usage

```python
import numpy as np
from dapple.adapters import from_array

# 2D grayscale array
grayscale = np.random.rand(48, 80).astype(np.float32)
canvas = from_array(grayscale)

# 3D RGB array -- luminance bitmap is computed automatically
rgb = np.random.rand(48, 80, 3).astype(np.float32)
canvas = from_array(rgb)
```

### Class interface

```python
from dapple.adapters import NumpyAdapter

adapter = NumpyAdapter(array, renderer=braille)
canvas = adapter.to_canvas()
```

### Input requirements

| Shape      | Interpretation          | Canvas result                    |
|------------|-------------------------|----------------------------------|
| `(H, W)`   | Grayscale bitmap        | bitmap only, no colors           |
| `(H, W, 3)` | RGB color image       | bitmap from luminance, colors from RGB |

Values should be in the range 0.0--1.0. Arrays with integer dtype or values outside this range should be normalized before passing to the adapter.

### Normalizing integer arrays

```python
# uint8 image (0-255)
uint8_array = np.random.randint(0, 256, (48, 80, 3), dtype=np.uint8)
float_array = uint8_array.astype(np.float32) / 255.0
canvas = from_array(float_array)
```

---

## PILAdapter / `from_pil` / `load_image`

Converts PIL (Pillow) Image objects to Canvas. Handles L (grayscale), RGB, RGBA, and other PIL modes.

**Dependency:** `pip install pillow`

### `from_pil` -- convert an existing PIL Image

```python
from PIL import Image
from dapple.adapters import from_pil

img = Image.open("photo.jpg")
canvas = from_pil(img)

# With resizing
canvas = from_pil(img, width=160)              # scale to 160px wide
canvas = from_pil(img, height=80)              # scale to 80px tall
canvas = from_pil(img, width=160, height=80)   # exact dimensions
```

| Parameter  | Type       | Default | Description                                  |
|------------|------------|---------|----------------------------------------------|
| `image`    | `Image`    | *(required)* | PIL Image object                        |
| `width`    | `int\|None` | `None` | Target width (proportional scaling if height omitted) |
| `height`   | `int\|None` | `None` | Target height (proportional scaling if width omitted) |
| `renderer` | `Renderer\|None` | `None` | Default renderer for the Canvas       |

Resizing uses Lanczos resampling (high quality).

### `load_image` -- load from file path

```python
from dapple.adapters.pil import load_image

canvas = load_image("photo.jpg")
canvas = load_image("photo.jpg", width=160)
```

This is a shorthand for `Image.open(path)` followed by `from_pil(...)`.

### Color mode handling

| PIL Mode | Canvas Result                                    |
|----------|--------------------------------------------------|
| `L`      | Grayscale bitmap, no colors                      |
| `RGB`    | Bitmap from luminance, colors from RGB           |
| `RGBA`   | Converted to RGB (alpha discarded), then as RGB  |
| Other    | Converted to grayscale (`L`), bitmap only        |

### Class interface

```python
from dapple.adapters import PILAdapter

adapter = PILAdapter(img, width=160, renderer=quadrants)
canvas = adapter.to_canvas()
```

---

## MatplotlibAdapter / `from_matplotlib`

Captures a matplotlib Figure as a Canvas. The figure is rendered to a PNG in memory, then converted to pixel arrays.

**Dependency:** `pip install matplotlib` (and optionally `pillow` for better PNG decoding)

### Usage

```python
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
from dapple.adapters import from_matplotlib
from dapple import braille

# Create a plot
fig, ax = plt.subplots()
ax.plot([0, 1, 2, 3], [0, 1, 0, 1])
ax.set_title("Example")

# Convert to canvas
canvas = from_matplotlib(fig, width=160)
canvas.out(braille)

plt.close(fig)
```

| Parameter  | Type       | Default | Description                                     |
|------------|------------|---------|-------------------------------------------------|
| `figure`   | `Figure`   | *(required)* | Matplotlib Figure object                   |
| `width`    | `int\|None` | `None` | Target width in pixels                          |
| `height`   | `int\|None` | `None` | Target height in pixels                         |
| `dpi`      | `int`      | `100`   | Rendering DPI                                   |
| `renderer` | `Renderer\|None` | `None` | Default renderer for the Canvas            |

### How it works

1. `fig.savefig()` renders the figure to a PNG in a BytesIO buffer.
2. If pillow is available, the PNG is decoded with `Image.open()`.
3. Otherwise, `fig.canvas.draw()` and `fig.canvas.tostring_rgb()` extract raw pixel data.
4. RGB is converted to Canvas with luminance bitmap.

The figure's size is adjusted before rendering if `width` or `height` are specified. The `dpi` parameter controls the rendering resolution.

> **Tip:** Use the `Agg` backend (`matplotlib.use("Agg")`) to avoid opening a GUI window. This is especially important in headless environments (servers, CI, SSH).

### Class interface

```python
from dapple.adapters import MatplotlibAdapter

adapter = MatplotlibAdapter(fig, width=160, dpi=150)
canvas = adapter.to_canvas()
```

---

## CairoAdapter / `from_cairo`

Converts Cairo ImageSurface objects to Canvas. Handles ARGB32, RGB24, and A8 surface formats.

**Dependency:** `pip install pycairo`

### Usage

```python
import cairo
from dapple.adapters import from_cairo
from dapple import quadrants

# Create a Cairo surface and draw on it
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 100)
ctx = cairo.Context(surface)

# White background
ctx.set_source_rgb(1, 1, 1)
ctx.paint()

# Red rectangle
ctx.set_source_rgb(1, 0, 0)
ctx.rectangle(20, 20, 60, 60)
ctx.fill()

# Blue circle
ctx.set_source_rgb(0, 0, 1)
ctx.arc(150, 50, 30, 0, 2 * 3.14159)
ctx.fill()

# Convert to canvas
canvas = from_cairo(surface)
canvas.out(quadrants)
```

| Parameter  | Type             | Default | Description                          |
|------------|------------------|---------|--------------------------------------|
| `surface`  | `ImageSurface`   | *(required)* | Cairo ImageSurface object       |
| `renderer` | `Renderer\|None` | `None`  | Default renderer for the Canvas      |

### Surface format handling

| Cairo Format      | Canvas Result                                 |
|-------------------|-----------------------------------------------|
| `FORMAT_ARGB32`   | RGB colors (alpha ignored), luminance bitmap  |
| `FORMAT_RGB24`    | RGB colors, luminance bitmap                  |
| `FORMAT_A8`       | Grayscale bitmap only                         |

Cairo stores pixels in BGRA order on little-endian systems. The adapter handles the byte-order conversion to RGB.

### Class interface

```python
from dapple.adapters import CairoAdapter

adapter = CairoAdapter(surface, renderer=braille)
canvas = adapter.to_canvas()
```

---

## ANSIAdapter / `from_ansi`

Parses ANSI-colored terminal output back into a Canvas. This reverses the rendering process: given braille, quadrant, sextant, or ASCII terminal art (with or without ANSI color codes), it reconstructs the bitmap and color arrays.

**Dependency:** none (uses only numpy and the standard library)

### Usage

```python
from dapple.adapters.ansi import from_ansi

# Parse braille art
text = "\u283f\u283f\u283f"  # three full braille characters
canvas = from_ansi(text)
# canvas.bitmap.shape == (4, 6)

# Parse with explicit format
canvas = from_ansi(colored_text, format="quadrants")

# Auto-detect format
canvas = from_ansi(mystery_text)  # detects braille/quadrants/sextants/ascii
```

| Parameter | Type       | Default     | Description                                     |
|-----------|------------|-------------|-------------------------------------------------|
| `text`    | `str`      | *(required)* | ANSI-colored terminal art                      |
| `format`  | `str\|None` | `None`     | `"braille"`, `"quadrants"`, `"sextants"`, `"ascii"`, or `None` for auto-detect |
| `charset` | `str`      | `" .:-=+*#%@"` | Character ramp for ASCII format parsing     |

### Format detection

When `format=None`, the parser counts the number of braille, quadrant, sextant, and ASCII characters in the input and picks the dominant format.

### Color parsing

The parser handles the following ANSI SGR (Select Graphic Rendition) sequences:

- Basic 16 colors (codes 30--37, 90--97 for foreground; 40--47, 100--107 for background)
- 256-color mode (`38;5;N` / `48;5;N`)
- 24-bit true color (`38;2;R;G;B` / `48;2;R;G;B`)
- Reset (`0`)

Colors are mapped to the reconstructed Canvas: foreground colors are applied to "active" pixels (dots, filled quadrants), and the bitmap structure is derived from the character encoding.

### Class interface

```python
from dapple.adapters.ansi import ANSIAdapter

adapter = ANSIAdapter(text, format="braille")
canvas = adapter.to_canvas()
```

### Use cases

- **Round-trip testing**: render to text, parse back, compare bitmaps.
- **Terminal art processing**: load existing ANSI art, apply transforms, re-render in a different format.
- **Format conversion**: parse quadrant art, re-render as braille (or vice versa).

---

## Summary

| Adapter             | Source           | Dependency   | Function          | Class              |
|---------------------|------------------|--------------|-------------------|--------------------|
| NumpyAdapter        | numpy array      | *(core)*     | `from_array()`    | `NumpyAdapter`     |
| PILAdapter          | PIL Image        | pillow       | `from_pil()`      | `PILAdapter`       |
| *(file loading)*    | image file path  | pillow       | `load_image()`    | --                 |
| MatplotlibAdapter   | mpl Figure       | matplotlib   | `from_matplotlib()` | `MatplotlibAdapter` |
| CairoAdapter        | Cairo surface    | pycairo      | `from_cairo()`    | `CairoAdapter`     |
| ANSIAdapter         | ANSI text        | *(core)*     | `from_ansi()`     | `ANSIAdapter`      |

### Imports

```python
# Convenience functions
from dapple.adapters import from_array, from_pil, from_matplotlib, from_cairo, from_ansi

# Or from specific modules
from dapple.adapters.pil import load_image
from dapple.adapters.ansi import from_ansi, detect_format

# Classes
from dapple.adapters import (
    NumpyAdapter, PILAdapter, MatplotlibAdapter, CairoAdapter, ANSIAdapter,
)
```

### Installation

```bash
# Core only (numpy adapter always available)
pip install dapple

# With PIL adapter
pip install dapple[imgcat]    # or: pip install pillow

# With matplotlib adapter
pip install dapple[adapters]  # includes pillow + matplotlib

# Everything
pip install dapple[dev]
```
