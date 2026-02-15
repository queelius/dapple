# Layout Engine

dapple provides layout primitives for composing multi-panel terminal displays.

## Canvas.fit()

Resize a canvas to fit character dimensions with automatic aspect-ratio correction:

```python
from dapple import Canvas, braille, sextants, from_pil
from dapple.layout import terminal_fit
from PIL import Image

canvas = from_pil(Image.open("photo.jpg"))

# Fit to width with aspect correction
fitted = canvas.fit(braille, width=80)
fitted.out(braille)

# terminal_fit() handles renderer-specific sizing:
# - Character renderers: resize + aspect correction
# - Kitty: passes columns parameter, no resize
# - Sixel: resize to pixel width
canvas, renderer = terminal_fit(canvas, sextants, width=80)
canvas.out(renderer)
```

## Frame

Wrap a canvas with optional title, border, and padding:

```python
from dapple import Canvas, Frame, sextants
import numpy as np

canvas = Canvas(np.random.rand(40, 80).astype(np.float32))
frame = Frame(canvas, title="Random Noise", border=True, padding=1)
frame.render(sextants)
```

## Grid

Arrange canvases or frames in rows and columns:

```python
from dapple import Canvas, Grid, sextants
import numpy as np

c1 = Canvas(np.random.rand(40, 80).astype(np.float32))
c2 = Canvas(np.random.rand(40, 80).astype(np.float32))
c3 = Canvas(np.random.rand(40, 80).astype(np.float32))
c4 = Canvas(np.random.rand(40, 80).astype(np.float32))

# 2x2 grid
grid = Grid([[c1, c2], [c3, c4]], width=100, gap=1)
grid.render(sextants)
```

The grid automatically sizes each cell to fit the available width, preserving aspect ratios.

## Helper

```python
from dapple.layout import terminal_columns

# Get current terminal width
cols = terminal_columns(fallback=80)
```
