# Composition and Layout

dapple started as a rendering library: bitmap in, text out. But the CLI tools kept reinventing the same code. Every tool calculated terminal width, corrected aspect ratios, handled kitty vs sixel vs braille sizing differently. imgcat had 50 lines of sizing logic. pdfcat had 70. mdcat had 40. They all did the same thing, slightly differently, with slightly different bugs.

0.6 extracts this into a layout engine and adds composition primitives that make multi-panel terminal displays trivial.

## The Sizing Problem

A terminal character cell is not square. It's roughly twice as tall as it is wide. A 100x100 pixel image rendered into 50x25 braille characters (2x4 dots each) looks squashed -- the aspect ratio is wrong because we forgot to account for cell shape.

Every dapple extra solved this independently. imgcat multiplied pixel height by 0.5. pdfcat used a different correction factor. mdcat had its own formula. And each handled kitty, sixel, and character renderers with separate code paths, because pixel renderers don't need aspect correction at all.

`Canvas.fit()` consolidates this:

```python
fitted = canvas.fit(braille, width=80)
```

One method. It knows the renderer's cell dimensions (braille is 2x4, sextants is 2x3), calculates the pixel width, preserves the aspect ratio with cell correction, and returns a resized canvas. For pixel renderers (sixel, kitty), it returns the canvas unchanged -- they handle sizing at the protocol level.

`terminal_fit()` goes one step further, handling the renderer-specific protocol differences:

```python
from dapple.layout import terminal_fit

canvas, renderer = terminal_fit(canvas, sextants, width=80)
canvas.out(renderer)
```

Kitty gets `columns=80` passed to the renderer. Sixel gets pixel-resized. Character renderers get `Canvas.fit()`. Three code paths, one function, zero decisions for the caller.

## Frame and Grid

With sizing solved, composition becomes straightforward. A `Frame` wraps a canvas with an optional title, border, and padding. A `Grid` arranges frames in rows.

```python
from dapple import Canvas, Frame, Grid, sextants

grid = Grid([
    [Frame(img1, title="before"), Frame(img2, title="after")],
    [Frame(chart, title="diff")]
], width=120)
grid.render(sextants)
```

The grid handles all the layout math: dividing available width among columns, sizing each cell's canvas proportionally, adding gap spacing between cells.

This is the foundation for the new composition extras -- compcat, thumbcat, diffcat, storycat all use Grid internally. A contact sheet is just "load N images, wrap each in a Frame, arrange in a Grid." A renderer comparison is "render the same image N ways, Grid the results." The primitives compose.

## Seven New Extras

The layout engine enables extras that would have been painful to build before:

| Tool | Purpose |
|------|---------|
| **compcat** | Compare renderers side by side |
| **thumbcat** | Image contact sheet / thumbnail grid |
| **diffcat** | Visual image diff (side-by-side, overlay, highlight) |
| **storycat** | Video storyboard grid |
| **ansicat** | ANSI art viewer |
| **plotcat** | Faceted data plots grouped by column |
| **dashcat** | YAML-driven terminal dashboards |

Each is under 150 lines. Most of the logic is argument parsing -- the actual composition is a few lines of Frame and Grid calls. That's the point of good primitives: they make the next layer trivial.

## Charts API

The other addition in 0.6 is `dapple.charts` -- character-dimension wrappers around vizlib's chart primitives:

```python
from dapple.charts import sparkline, line_plot, bar_chart

chart = sparkline([1, 4, 2, 8, 3, 7], width=40, height=4)
chart.out(braille)
```

vizlib already had these functions, but they accepted pixel dimensions. The wrapper converts character dimensions to pixels using braille's 2x4 cell size as a reference. Small thing, but it eliminates the "how many pixels is 40 columns?" arithmetic that every caller had to do.

## The Pattern

Good abstractions emerge from noticing repeated code. imgcat, pdfcat, and mdcat all had their own sizing logic -- that's three implementations of the same idea, a clear signal that an abstraction is missing.

Once the abstraction exists (Canvas.fit, terminal_fit), new tools become composition: load content, fit to terminal, render. The seven new extras are proof -- each is short because the hard problems (sizing, aspect correction, layout) are solved once in the layout engine.

---

*See also: [Layout Engine](../guide/layout.md) for the API reference. [Charts API](../guide/charts.md) for the character-dimension chart functions.*
