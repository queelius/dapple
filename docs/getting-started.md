# Getting Started

## Installation

```bash
# Core library (numpy only)
pip install dapple

# Individual CLI tools
pip install dapple[imgcat]          # terminal image viewer
pip install dapple[pdfcat]          # PDF viewer (adds pypdfium2)
pip install dapple[mdcat]           # markdown viewer (adds rich)
pip install dapple[funcat]          # math/parametric plotter
pip install dapple[dashcat]         # YAML dashboard (adds pyyaml)

# Bundles
pip install dapple[all-tools]       # all 11 CLI tools
pip install dapple[adapters]        # PIL + matplotlib adapters
pip install dapple[dev]             # development (tests + all deps)
```

The core library depends only on numpy. CLI tools and adapters add optional dependencies as needed.

## Quick Start

### Render a bitmap

```python
import numpy as np
from dapple import Canvas, braille, quadrants, sextants

# Create a canvas from a bitmap (2D numpy array, values 0.0-1.0)
bitmap = np.random.rand(40, 80).astype(np.float32)
canvas = Canvas(bitmap)

# Output to terminal with different renderers
canvas.out(braille)                    # Unicode braille (2x4 dots)
canvas.out(quadrants)                  # Block chars with ANSI color
canvas.out(sextants)                   # Higher-res block chars
```

### Customize renderer options

Renderers are frozen dataclasses. Use `__call__` to create variants with different settings:

```python
canvas.out(braille(threshold=0.3))            # Custom threshold
canvas.out(quadrants(true_color=True))        # 24-bit RGB
canvas.out(braille(color_mode="grayscale"))   # Grayscale ANSI
```

### Load images with adapters

```python
from dapple import from_pil
from PIL import Image

img = Image.open("photo.jpg")
canvas = from_pil(img, width=160)
canvas.out(quadrants)
```

### Use the CLI tools

```bash
imgcat photo.jpg                     # view image in terminal
imgcat photo.jpg -r braille          # braille output
pdfcat document.pdf                  # view PDF pages
funcat "sin(x)"                      # plot a function
funcat -p "cos(t),sin(t)"           # parametric curve
```

## Preprocessing

```python
from dapple import Canvas, braille
from dapple.preprocess import auto_contrast, floyd_steinberg

bitmap = auto_contrast(bitmap)       # Stretch histogram to 0-1 range
bitmap = floyd_steinberg(bitmap)     # Dithering for tonal gradation
canvas = Canvas(bitmap)
canvas.out(braille)
```

Floyd-Steinberg dithering is the single most effective improvement for binary output like braille.

## Auto-Detection

```python
from dapple.auto import auto_renderer, render_image

renderer = auto_renderer()   # kitty > sixel > quadrants > braille > ascii
render_image("photo.jpg")    # one-liner: load, detect, render
```

## Next Steps

- [Canvas API](guide/canvas.md) — Full Canvas class documentation
- [Renderers](guide/renderers.md) — All seven renderers in detail
- [Layout Engine](guide/layout.md) — Frame, Grid, and Canvas.fit()
- [Charts API](guide/charts.md) — Character-dimension chart functions
- [CLI Tools](tools/index.md) — All 11 terminal tools
