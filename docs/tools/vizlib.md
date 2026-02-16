# vizlib -- Chart Primitives

Programmatic chart primitives for terminal visualization. vizlib provides
functions that produce dapple `Canvas` objects, which can then be rendered
with any dapple renderer.

vizlib is a **Python library**, not a CLI tool. It is used internally by
csvcat and datcat for their chart modes, and can be used directly for custom
visualizations.

## Installation

```bash
pip install dapple[vizlib]
```

No additional dependencies beyond dapple's core numpy requirement.

## Components

### sparkline

A compact line chart without axes, connecting data points with Bresenham
line segments.

```python
from dapple.extras.vizlib import sparkline
from dapple import braille

values = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]

canvas = sparkline(values, width=160, height=32)
canvas.out(braille(threshold=0.2, color_mode="truecolor"))
```

Parameters:

- `values` -- sequence of numeric data points
- `width` -- bitmap width in pixels
- `height` -- bitmap height in pixels
- `color` -- RGB tuple (0-1 range), defaults to cyan

### line_plot

A line chart with an optional baseline axis at `y=0`.

```python
from dapple.extras.vizlib import line_plot

values = [10, -5, 3, -8, 12, 7, -2]

canvas = line_plot(values, width=160, height=64, show_axes=True)
canvas.out(braille(threshold=0.2, color_mode="truecolor"))
```

Parameters:

- `values` -- sequence of numeric data points
- `width` -- bitmap width in pixels
- `height` -- bitmap height in pixels
- `color` -- RGB tuple (0-1 range), defaults to cyan
- `show_axes` -- draw a baseline at y=0 if it falls within the data range
  (default: True)

### bar_chart

Horizontal or vertical bar chart with automatic color cycling.

```python
from dapple.extras.vizlib import bar_chart

labels = ["Python", "Rust", "Go", "Java"]
values = [45, 30, 20, 15]

# Horizontal bars (default)
canvas = bar_chart(labels, values, width=160, height=64)
canvas.out(braille(threshold=0.2, color_mode="truecolor"))

# Vertical bars
canvas = bar_chart(labels, values, width=160, height=64, horizontal=False)
canvas.out(braille(threshold=0.2, color_mode="truecolor"))

# Single color for all bars
canvas = bar_chart(labels, values, width=160, height=64, color=(0.0, 0.8, 1.0))
```

Parameters:

- `labels` -- category labels
- `values` -- numeric values per category
- `width` -- bitmap width in pixels
- `height` -- bitmap height in pixels
- `horizontal` -- if True (default), bars go left-to-right; if False,
  bottom-to-top
- `color` -- RGB tuple (0-1 range); if None, cycles through the palette

### histogram

Distribution histogram with configurable bin count.

```python
from dapple.extras.vizlib import histogram
import numpy as np

values = np.random.normal(0, 1, 1000).tolist()

canvas = histogram(values, width=160, height=64, bins=30)
canvas.out(braille(threshold=0.2, color_mode="truecolor"))
```

Parameters:

- `values` -- sequence of numeric data points
- `width` -- bitmap width in pixels
- `height` -- bitmap height in pixels
- `bins` -- number of histogram bins (default: 20)
- `color` -- RGB tuple (0-1 range), defaults to cyan

### heatmap

A 2D heatmap with a blue-to-white-to-red color gradient.

```python
from dapple.extras.vizlib import heatmap

# 2D array of values
grid = [
    [1, 2, 3, 4, 5],
    [5, 4, 3, 2, 1],
    [2, 4, 6, 4, 2],
]

canvas = heatmap(grid, width=160, height=48)
canvas.out(quadrants(true_color=True))
```

Parameters:

- `values` -- 2D array (list of lists) of numeric values
- `width` -- bitmap width in pixels
- `height` -- bitmap height in pixels

Values are normalized to the range of the input data. Low values map to blue,
mid values to white, and high values to red.

## Helper Functions

vizlib also exports helper functions for working with renderers:

### get_renderer

Look up a renderer by name string:

```python
from dapple.extras.vizlib import get_renderer

renderer = get_renderer("braille")
renderer = get_renderer("quadrants")
```

### get_terminal_size

Get terminal dimensions:

```python
from dapple.extras.vizlib import get_terminal_size

cols, lines = get_terminal_size()
```

### pixel_dimensions

Convert character dimensions to pixel dimensions for a given renderer:

```python
from dapple.extras.vizlib import pixel_dimensions, get_renderer

renderer = get_renderer("braille")
pixel_w, pixel_h = pixel_dimensions(renderer, char_w=80, char_h=24)
# braille: 160 x 96 (cell is 2x4 pixels)
```

## Color Utilities

```python
from dapple.extras.vizlib import parse_color, NAMED_COLORS, COLOR_PALETTE

# Parse color from name or hex string
color = parse_color("cyan")        # (0.0, 0.8, 1.0)
color = parse_color("#ff6600")     # (1.0, 0.4, 0.0)

# Available named colors
print(NAMED_COLORS.keys())
# cyan, red, green, yellow, magenta, orange, blue, pink, white, gray

# Auto-cycling palette (used by bar_chart when no color specified)
first_color = COLOR_PALETTE[0]
```

## Full Example

Combining vizlib with dapple for a custom dashboard:

```python
import sys
from dapple import braille, quadrants
from dapple.extras.vizlib import sparkline, bar_chart, histogram, pixel_dimensions

# Configure renderer
renderer = braille(threshold=0.2, color_mode="truecolor")
px_w, px_h = pixel_dimensions(renderer, 80, 12)

# Revenue sparkline
revenue = [120, 135, 142, 138, 155, 160, 175, 180, 195, 210]
canvas = sparkline(revenue, width=px_w, height=px_h, color=(0.0, 0.8, 1.0))
print("Revenue Trend:")
canvas.out(renderer)
print()

# Category breakdown
labels = ["Web", "Mobile", "API", "Other"]
counts = [450, 320, 180, 50]
px_w2, px_h2 = pixel_dimensions(renderer, 80, 16)
canvas = bar_chart(labels, counts, width=px_w2, height=px_h2)
print("Traffic by Channel:")
canvas.out(renderer)
print()

# Latency distribution
import numpy as np
latencies = np.random.exponential(50, 500).tolist()
canvas = histogram(latencies, width=px_w, height=px_h, bins=25)
print("Latency Distribution (ms):")
canvas.out(renderer)
```

## API Summary

```python
from dapple.extras.vizlib import (
    # Chart functions (return Canvas)
    sparkline,
    bar_chart,
    line_plot,
    histogram,
    heatmap,

    # Renderer helpers
    get_renderer,
    get_terminal_size,
    pixel_dimensions,

    # Color utilities
    parse_color,
    NAMED_COLORS,
    COLOR_PALETTE,
)
```
