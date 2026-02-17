# dapple

Terminal-centric development is now mainstream. Claude Code runs in your terminal. AI assistants stream their work as text. Developers SSH into remote machines, pair with tmux, and live in the command line. In this world, there's a gap: we want to see graphics without leaving the terminal.

dapple is a unified terminal graphics library. One Canvas API, multiple renderers: braille, quadrants, sextants, ASCII, sixel, kitty, and fingerprint. Choose the renderer that matches your terminal's capabilities and your visual needs.

## Why a Unified Library?

Terminal graphics tools are fragmented. One library does braille. Another does quadrant blocks. A third handles sixel. Each has its own API, its own conventions.

dapple unifies these approaches:

- **Single Canvas class** - Load your bitmap once, output anywhere
- **Pluggable renderers** - Switch formats with one line: `canvas.out(braille)` or `canvas.out(quadrants)`
- **Layout primitives** - Frame and Grid for composing multi-panel displays
- **Charts API** - Sparklines, line plots, bar charts, histograms, heatmaps
- **14 CLI tools** - View images, PDFs, markdown, video, data, math plots, and more
- **Stream-based output** - Write to stdout, files, or any text stream

## Installation

```bash
# Core library (numpy only)
pip install dapple

# Individual CLI tools
pip install dapple[imgcat]          # terminal image viewer
pip install dapple[pdfcat]          # PDF viewer (adds pypdfium2)
pip install dapple[mdcat]           # markdown viewer (adds rich)
pip install dapple[funcat]          # math/parametric plotter
pip install dapple[vidcat]          # video frame viewer
pip install dapple[csvcat]          # CSV/TSV viewer & plotter
pip install dapple[datcat]          # JSON/JSONL viewer & plotter
pip install dapple[compcat]         # renderer comparison
pip install dapple[ansicat]         # ANSI art viewer
pip install dapple[plotcat]         # faceted data plots
pip install dapple[dashcat]         # YAML-driven dashboard (adds pyyaml)

# Bundles
pip install dapple[all-tools]       # all 11 CLI tools
pip install dapple[adapters]        # PIL + matplotlib adapters
pip install dapple[dev]             # development (tests + all deps)
```

## Quick Start

```python
import numpy as np
from dapple import Canvas, braille, quadrants, sextants

# Create a canvas from a bitmap
bitmap = np.random.rand(40, 80).astype(np.float32)
canvas = Canvas(bitmap)

# Output to terminal with different renderers
canvas.out(braille)                    # Unicode braille (2x4 dots)
canvas.out(quadrants)                  # Block chars with ANSI color
canvas.out(sextants)                   # Higher-res block chars

# Customize renderer options
canvas.out(braille(threshold=0.3))     # Custom threshold
canvas.out(quadrants(true_color=True)) # 24-bit RGB
canvas.out(braille(color_mode="grayscale"))  # Grayscale ANSI

# Output to file
canvas.out(braille, "output.txt")

# Set default renderer for print()
canvas = Canvas(bitmap, renderer=quadrants)
print(canvas)  # Uses quadrants
```

## Renderers

dapple includes seven renderers, each with different trade-offs:

| Renderer | Cell Size | Colors | Best For |
|----------|-----------|--------|----------|
| `braille` | 2x4 | mono/gray/true | Structure, edges, piping, accessibility |
| `quadrants` | 2x2 | ANSI 256/true | Photos, balanced resolution and color |
| `sextants` | 2x3 | ANSI 256/true | Higher vertical resolution |
| `ascii` | 1x2 | none | Universal compatibility, classic look |
| `sixel` | 1x1 | palette | True pixels (xterm, mlterm, foot) |
| `kitty` | 1x1 | true | True pixels (kitty, wezterm) |
| `fingerprint` | 8x16 | none | Artistic glyph matching |

### Braille (Structure)

```python
from dapple import braille

# Binary threshold
canvas.out(braille)                      # Default threshold 0.5
canvas.out(braille(threshold=0.3))       # Darker threshold
canvas.out(braille(threshold=None))      # Auto-detect from mean

# Color modes
canvas.out(braille(color_mode="none"))       # Plain braille
canvas.out(braille(color_mode="grayscale"))  # 24-level grayscale
canvas.out(braille(color_mode="truecolor"))  # Full 24-bit RGB
```

### Quadrants (Color)

```python
from dapple import quadrants

# Block characters with ANSI colors
canvas.out(quadrants)                    # True color (default)
canvas.out(quadrants(true_color=False))  # 256-color mode
canvas.out(quadrants(grayscale=True))    # Grayscale only
```

### Sixel & Kitty (True Pixels)

```python
from dapple import sixel, kitty

# Sixel for xterm-compatible terminals
canvas.out(sixel)
canvas.out(sixel(max_colors=256, scale=2))

# Kitty graphics protocol
canvas.out(kitty)
canvas.out(kitty(format="png"))          # PNG compression
canvas.out(kitty(format="rgb"))          # Raw RGB
```

### Fingerprint (Artistic)

```python
from dapple import fingerprint

# Glyph matching using font bitmap correlation
canvas.out(fingerprint)
canvas.out(fingerprint(glyph_set="blocks"))    # Block characters
canvas.out(fingerprint(glyph_set="braille"))   # Braille glyphs
canvas.out(fingerprint(cell_width=10, cell_height=20))
```

## Layout Engine

dapple provides layout primitives for composing multi-panel terminal displays.

### Canvas.fit()

Resize a canvas to fit character dimensions, handling aspect-ratio correction automatically:

```python
from dapple import Canvas, braille, sextants
from dapple.layout import terminal_fit

canvas = from_pil(Image.open("photo.jpg"))

# Fit to terminal width with aspect correction
fitted = canvas.fit(braille, width=80)
fitted.out(braille)

# Or use terminal_fit() for renderer-aware sizing
# (handles kitty/sixel/character renderers differently)
canvas, renderer = terminal_fit(canvas, sextants, width=80)
canvas.out(renderer)
```

### Frame and Grid

Compose multiple canvases into structured layouts:

```python
from dapple import Canvas, Frame, Grid, sextants
import numpy as np

# Frame adds title, border, padding
c1 = Canvas(np.random.rand(40, 80).astype(np.float32))
frame = Frame(c1, title="Random Noise", border=True)
frame.render(sextants)

# Grid arranges frames in rows and columns
c2 = Canvas(np.random.rand(40, 80).astype(np.float32))
grid = Grid([[c1, c2]], width=100, gap=1)
grid.render(sextants)
```

## Charts API

Character-dimension wrappers around the built-in vizlib chart primitives. Specify width and height in characters instead of pixels:

```python
from dapple.charts import sparkline, line_plot, bar_chart, histogram, heatmap
from dapple import braille

# Sparkline
chart = sparkline([1, 4, 2, 8, 3, 7], width=40, height=4)
chart.out(braille)

# Line plot
chart = line_plot(y=[1, 4, 2, 8, 3, 7], width=60, height=20)
chart.out(braille)

# Bar chart
chart = bar_chart(["A", "B", "C"], [10, 25, 15], width=60, height=20)
chart.out(braille)

# Histogram
import numpy as np
chart = histogram(np.random.randn(1000), width=60, height=20, bins=30)
chart.out(braille)
```

## Preprocessing

dapple includes preprocessing functions for improved output:

```python
from dapple import (
    auto_contrast,    # Stretch histogram to 0-1 range
    floyd_steinberg,  # Dithering for binary output
    invert,          # Flip brightness values
    gamma_correct,   # Gamma correction
    sharpen,         # Edge enhancement
    threshold,       # Binary threshold
    resize,          # Resize with bilinear interpolation (2D and 3D)
    crop,            # Extract rectangular region
    flip,            # Mirror horizontally or vertically
    rotate,          # Rotate by degrees
)

# Chain preprocessing
bitmap = auto_contrast(bitmap)
bitmap = floyd_steinberg(bitmap)  # Best for braille
canvas = Canvas(bitmap)
canvas.out(braille)
```

**Floyd-Steinberg dithering** is the single most effective improvement for binary output. It creates the illusion of grayscale through varying dot density.

## Color Support

Pass RGB colors alongside the bitmap:

```python
import numpy as np
from dapple import Canvas, quadrants

# Grayscale bitmap + RGB colors
bitmap = np.random.rand(40, 80).astype(np.float32)
colors = np.random.rand(40, 80, 3).astype(np.float32)

canvas = Canvas(bitmap, colors=colors)
canvas.out(quadrants)  # Uses RGB colors
canvas.out(braille(color_mode="truecolor"))  # RGB braille
```

Or use `from_array` to auto-extract luminance from RGB:

```python
from dapple import from_array

rgb = np.random.rand(40, 80, 3).astype(np.float32)
canvas = from_array(rgb)  # Auto-computes grayscale bitmap
```

## Adapters

Load images from common formats:

```python
# PIL/Pillow
from dapple import from_pil
from PIL import Image

img = Image.open("photo.jpg")
canvas = from_pil(img)                   # original size
canvas = from_pil(img, width=160)        # resize on load
canvas.out(quadrants)

# Matplotlib
from dapple.adapters import MatplotlibAdapter
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 2])

adapter = MatplotlibAdapter()
canvas = adapter.to_canvas(fig, width=60)
canvas.out(braille)
plt.close(fig)

# Cairo
from dapple.adapters import CairoAdapter
import cairo

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 100)
ctx = cairo.Context(surface)
# ... draw with cairo ...

adapter = CairoAdapter()
canvas = adapter.to_canvas(surface)
canvas.out(quadrants)
```

## Canvas Operations

```python
# Composition
left = Canvas(bitmap1)
right = Canvas(bitmap2)
combined = left.hstack(right)  # Horizontal stack
combined = left + right        # Same as hstack

top = Canvas(bitmap1)
bottom = Canvas(bitmap2)
combined = top.vstack(bottom)  # Vertical stack

# Overlay
base = Canvas(background)
overlay = Canvas(sprite)
result = base.overlay(overlay, x=10, y=5)

# Crop
cropped = canvas.crop(x1=10, y1=10, x2=50, y2=40)

# Transform
inverted = canvas.with_invert()
```

## CLI Tools

dapple ships 14 command-line tools, each installed as a standalone entry point.

### Viewers

```bash
imgcat photo.jpg                    # view image in terminal
imgcat photo.jpg -r sextants -w 80  # sextants for photos
imgcat photo.jpg --dither           # Floyd-Steinberg dithering

pdfcat document.pdf                 # view PDF pages
pdfcat document.pdf --pages 1-3     # specific pages
pdfcat document.pdf --dpi 300       # higher resolution

mdcat README.md                     # render markdown with formatting
mdcat README.md --images            # with inline images

vidcat video.mp4                    # play video in terminal
vidcat video.mp4 --every 1s         # 1 frame per second

ansicat artwork.ans -r sextants     # view ANSI art
```

### Data & Math

```bash
csvcat data.csv                     # formatted table
csvcat data.csv --plot line -y revenue,cost  # multi-series line plot

datcat records.jsonl --plot line    # line plot from JSONL
datcat data.json -q .results       # query nested path
datcat records.jsonl --spark        # sparkline summary

funcat "sin(x)"                    # plot math expression
funcat "sin(x)" "cos(x)" --legend  # overlay with legend
funcat "x**2" --xmin -5 --xmax 5   # custom domain
funcat -p "cos(t),sin(t)"          # parametric curve (circle)
funcat -p "t*cos(t),t*sin(t)"      # parametric spiral
```

### Composition

```bash
compcat photo.jpg braille sextants quadrants  # compare renderers side-by-side
imgcat photos/*.jpg --cols 4 -w 120           # image contact sheet
```

### Analysis

```bash
plotcat data.csv --facet region --plot line -x date -y sales  # faceted plots
dashcat layout.yaml                                           # YAML-driven dashboard
dashcat --preset system                                       # built-in system metrics
```

### Chaining (funcat)

funcat supports `--json` for composing multi-curve figures:

```bash
funcat -p "cos(t),sin(t)" --color yellow --json \
  | funcat -p "0.1*cos(t)-0.3,0.1*sin(t)+0.3" --color blue --json \
  | funcat -p "0.1*cos(t)+0.3,0.1*sin(t)+0.3" --color blue --json \
  | funcat -p "0.4*cos(t),-0.3+0.2*sin(t)" --color red --tmin 3.14 --tmax 6.28 \
      --xmin -1.5 --xmax 1.5 --ymin -1.5 --ymax 1.5
```

All tools support `-r` / `--renderer` to select the output format and common preprocessing flags (`--dither`, `--contrast`, `--invert`).

## Auto-Detection

dapple can detect terminal capabilities and select the best renderer automatically:

```python
from dapple.auto import auto_renderer, detect_terminal, render_image

# Detect terminal capabilities
info = detect_terminal()
print(info.protocol)       # Protocol.KITTY, Protocol.SIXEL, etc.
print(info.color_support)  # True/False

# Get the best renderer for this terminal
renderer = auto_renderer()             # kitty > sixel > quadrants > braille > ascii
renderer = auto_renderer(plain=True)   # force ASCII (for pipes)

# One-liner: load, detect, render
render_image("photo.jpg")
render_image("photo.jpg", width=640)
```

## When to Use Each Renderer

| Scenario | Recommended Renderer |
|----------|---------------------|
| SSH sessions, tmux, screen | `braille`, `quadrants`, `ascii` |
| Piping output to files | `braille`, `ascii` |
| Screen readers / accessibility | `braille` |
| Photo previews | `quadrants`, `sextants` |
| High-quality local display | `sixel` (xterm), `kitty` (kitty/wezterm) |
| Universal compatibility | `ascii` |
| Artistic/experimental | `fingerprint` |

## Claude Code Integration

dapple includes a skill generator for [Claude Code](https://claude.ai/code):

```bash
dapple-skill --global    # install skill for all projects
dapple-skill --local     # install for current project only
```

This teaches Claude Code how to use all installed dapple tools.

## License

MIT
