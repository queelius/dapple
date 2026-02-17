# dapple

**Unified terminal graphics — one Canvas API, seven renderers, 12 CLI tools.**

Terminal-centric development is now mainstream. Claude Code runs in your terminal. AI assistants stream their work as text. Developers SSH into remote machines, pair with tmux, and live in the command line. In this world, there's a gap: we want to see graphics without leaving the terminal.

dapple fills that gap. Load a bitmap once, output to any format — braille, quadrants, sextants, ASCII, sixel, kitty, or fingerprint. Compose layouts with Frame and Grid. Create charts with the character-dimension charts API.

## Quick Example

```python
import numpy as np
from dapple import Canvas, braille, quadrants

bitmap = np.random.rand(40, 80).astype(np.float32)
canvas = Canvas(bitmap)

canvas.out(braille)      # Unicode braille (2x4 dots)
canvas.out(quadrants)    # Block chars with ANSI color
```

## Seven Renderers

| Renderer | Cell Size | Colors | Best For |
|----------|-----------|--------|----------|
| `braille` | 2x4 | mono/gray/true | Structure, edges, piping, accessibility |
| `quadrants` | 2x2 | ANSI 256/true | Photos, balanced resolution and color |
| `sextants` | 2x3 | ANSI 256/true | Higher vertical resolution |
| `ascii` | 1x2 | none | Universal compatibility, classic look |
| `sixel` | 1x1 | palette | True pixels (xterm, mlterm, foot) |
| `kitty` | 1x1 | true | True pixels (kitty, wezterm) |
| `fingerprint` | 8x16 | none | Artistic glyph matching |

## CLI Tools

```bash
imgcat photo.jpg                    # view image
pdfcat document.pdf                 # view PDF
vidcat video.mp4                    # video frames
mdcat README.md                     # render markdown
funcat "sin(x)"                     # plot function
funcat -p "cos(t),sin(t)"          # parametric curve
csvcat data.csv --plot line         # chart CSV
datcat data.jsonl --spark          # sparkline JSONL
compcat img.jpg braille sextants    # compare renderers
imgcat photos/*.jpg --cols 4        # contact sheet
plotcat data.csv --facet region      # faceted plots
dashcat layout.yaml                 # YAML dashboard
```

## What's Next

- [Getting Started](getting-started.md) — Installation and first steps
- [Canvas Guide](guide/canvas.md) — The core Canvas API
- [Layout Engine](guide/layout.md) — Frame, Grid, and Canvas.fit()
- [Charts API](guide/charts.md) — Character-dimension charts
- [CLI Tools](tools/index.md) — All 12 terminal tools
