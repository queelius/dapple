# Design Patterns

dapple's architecture is shaped by a small number of engineering patterns. Each pattern addresses a concrete problem and has a specific reason for existing. This document describes the five patterns that define how dapple works.

---

## Pattern: Framebuffer

**Accept bitmap arrays as rendering targets. Decouple content generation from display.**

The core insight behind dapple is that higher-level libraries -- plotting, drawing, image processing -- should not need to know how their output will be displayed. They produce pixels. dapple produces text.

### The problem

Without a framebuffer abstraction, every tool that wants terminal graphics must implement its own rendering. A plotting library writes braille characters inline with its axis logic. An image viewer writes ANSI escape sequences mixed with its file-loading code. When you want to support a second output format -- say, sixel alongside braille -- you rewrite the rendering layer inside every tool.

The rendering scaffolding buries the domain logic.

### How dapple solves it

dapple treats the terminal as a framebuffer target. Any code that can produce a numpy array can hand it to dapple for display:

```python
import matplotlib.pyplot as plt
import numpy as np
from dapple.adapters import from_matplotlib
from dapple import braille

# Your normal matplotlib code
fig, ax = plt.subplots()
x = np.linspace(0, 2 * np.pi, 100)
ax.plot(x, np.sin(x), linewidth=3)
ax.set_title("sin(x)")

# Render to terminal instead of window
canvas = from_matplotlib(fig, width=160)
canvas.out(braille)
plt.close()
```

The plotting code does not know or care that its output becomes braille. The abstraction boundary is clean: matplotlib produces pixels, dapple produces text.

The Canvas class is the framebuffer:

```python
from dapple import Canvas, braille, quadrants, sixel, kitty

canvas = Canvas(bitmap, colors=rgb)

canvas.out(braille)      # Works everywhere
canvas.out(quadrants)    # Works in most terminals
canvas.out(sixel)        # Works in xterm, foot, mlterm
canvas.out(kitty)        # Works in kitty, wezterm
```

Same data, different renderers. The tool author writes domain logic. The renderer handles the terminal. Switching output format is one argument, not a rewrite.

### Why it works

The framebuffer pattern separates two concerns that change at different rates. The *content* of an image (what to render) changes with every use case -- plots, photos, diagrams. The *format* of the output (how to render) changes with the environment -- SSH session, local kitty terminal, CI runner. By decoupling these through a bitmap array, each side evolves independently.

This also enables AI assistants to show their work. An LLM generating a chart renders it to a Canvas and outputs braille inline with its explanation. No window to spawn, no file to save. The picture is text.

---

## Pattern: Adapter

**Library integrations that convert foreign formats to Canvas. Keep the core dependency-free.**

### The problem

A terminal graphics library is only useful if you can get data into it. Users have images in PIL, figures in matplotlib, surfaces in Cairo, arrays in numpy. If the core library depends on all of these, it becomes heavy and fragile -- a version conflict in any dependency breaks everything.

### How dapple solves it

Adapters are thin conversion layers in `dapple/adapters/`. Each handles one external library:

```python
# From numpy array
from dapple import from_array
canvas = from_array(rgb_array)

# From PIL Image
from dapple import from_pil
canvas = from_pil(image)

# From matplotlib Figure
from dapple.adapters import from_matplotlib
canvas = from_matplotlib(fig, width=160)

# From Cairo surface
from dapple.adapters import from_cairo
canvas = from_cairo(surface)

# From ANSI escape sequences
from dapple.adapters import from_ansi
canvas = from_ansi(ansi_text)
```

Each adapter does one thing: convert a foreign format into a Canvas (a bitmap plus optional colors). The conversion is straightforward -- render the figure to a buffer, extract pixels, compute luminance for the grayscale bitmap, wrap in Canvas.

The matplotlib adapter illustrates the pattern:

```python
class MatplotlibAdapter:
    def __init__(self, figure, *, width=None, height=None, dpi=100, renderer=None):
        self._figure = figure
        self._width = width
        # ...

    def to_canvas(self) -> Canvas:
        # Render figure to PNG buffer
        buf = io.BytesIO()
        self._figure.savefig(buf, format="png", dpi=self._dpi)
        buf.seek(0)

        # Extract pixels as numpy array
        img = Image.open(buf)
        colors = np.array(img.convert("RGB"), dtype=np.float32) / 255.0

        # Compute luminance for grayscale bitmap
        from dapple.color import luminance
        bitmap = luminance(colors)

        return Canvas(bitmap, colors=colors, renderer=self._renderer)
```

Each adapter also provides a convenience function for the common case:

```python
# Class-based (full control)
adapter = MatplotlibAdapter(fig, width=160, dpi=150)
canvas = adapter.to_canvas()

# Function-based (common case)
canvas = from_matplotlib(fig, width=160)
```

### Why it works

Adapters keep the core library's dependency footprint minimal -- numpy only. Optional dependencies are declared in `pyproject.toml` extras (`pip install dapple[adapters]`) and imported lazily. If you never use matplotlib, you never need it installed. If it is missing when you try to use it, the error message tells you exactly what to install:

```
ImportError: matplotlib is required for MatplotlibAdapter.
Install with: pip install matplotlib
```

The adapter pattern also means new integrations do not touch core code. Adding support for a new library means adding one file in `dapple/adapters/` with one class and one convenience function. The Canvas API stays unchanged.

---

## Pattern: Named Presets / Frozen Dataclass Renderers

**Predefined configurations as module-level instances. `__call__` for variants. Immutable by construction.**

### The problem

Renderers have options -- thresholds, color modes, character sets. The classic approach is mutable objects: create a renderer, set properties, call render. This leads to state that leaks between calls: a renderer configured for one image accidentally retains settings for the next. Shared renderers across threads become a source of race conditions.

### How dapple solves it

Every renderer is a frozen dataclass. The module exports a default instance as a named preset:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class BrailleRenderer:
    threshold: float | None = 0.5
    color_mode: Literal["none", "grayscale", "truecolor"] = "none"

    @property
    def cell_width(self) -> int:
        return 2

    @property
    def cell_height(self) -> int:
        return 4

    def __call__(self, threshold=None, color_mode=None) -> "BrailleRenderer":
        """Create a new renderer with modified options."""
        return BrailleRenderer(
            threshold=threshold if threshold is not None else self.threshold,
            color_mode=color_mode if color_mode is not None else self.color_mode,
        )

    def render(self, bitmap, colors=None, *, dest):
        # ... write directly to dest stream
        pass

# Named preset -- the default instance
braille = BrailleRenderer()
```

Usage reads naturally at three levels of customization:

```python
from dapple import braille

# 1. Default preset -- the common case
canvas.out(braille)

# 2. One-off variant via __call__
canvas.out(braille(threshold=0.3))

# 3. Named custom preset for reuse
high_contrast = braille(threshold=0.2, color_mode="truecolor")
canvas.out(high_contrast)
```

The `__call__` pattern means `braille(threshold=0.3)` returns a *new* frozen instance. The original `braille` is never modified. No mutable state, no surprising side effects, thread-safe by construction.

### Why it works

Frozen dataclasses eliminate an entire category of bugs. You cannot accidentally mutate a shared renderer. You cannot have state leak between calls. You can safely pass renderers across thread boundaries or store them in global configuration.

The named preset pattern (`braille`, `quadrants`, `sixel`, etc.) also makes the common case concise. Most users want the defaults. They write `canvas.out(braille)` and never think about options. Users who need customization get it through `__call__`, which is discoverable and self-documenting.

All seven renderers follow this pattern identically. Learn one, know them all.

---

## Pattern: Structured Output

**JSON mode for composability. The `-j` flag switches from human display to machine-readable data.**

### The problem

A tool that only produces visual output is a dead end in a pipeline. You cannot feed a braille rendering into the next stage of processing. You cannot inspect intermediate state. You cannot reason about what the tool did -- only look at what it produced.

### How dapple tools solve it

Every dapple CLI tool that supports pipelines implements a `-j` flag. Without it, the tool renders for humans. With it, the tool emits structured JSON that can be consumed by the next stage.

```bash
# Human mode: renders the plot to the terminal
funcat "sin(x)"

# Machine mode: emits JSON describing the plot state
funcat "sin(x)" -j

# Pipeline: JSON flows between stages, final stage renders
funcat "sin(x)" -j | funcat "cos(x)" -l
```

The JSON carries accumulated state through the pipeline:

```bash
# Multi-function pipeline
funcat "sin(x)" -j | funcat "cos(x)" --color red -j | funcat "x/3" --color green -l
```

Each stage reads JSON from stdin, applies its operation, writes JSON to stdout. The final stage drops the `-j` flag and renders with `-l`. This is lazy evaluation made explicit: operations are recorded as structured data until the final materialization step.

The same pattern works for data visualization tools:

```bash
# CSV to chart
datcat data.csv --bar revenue

# JSON data to sparkline
datcat metrics.jsonl --spark latency
```

### Why it works

The `-j` flag turns every tool into an API endpoint. The protocol is JSON-over-stdin/stdout. The transport is Unix pipes. No HTTP server, no socket management, no authentication -- just text streams.

This is especially powerful for AI agents. An LLM constructing a multi-stage pipeline can inspect intermediate state by stopping before the final render:

```bash
funcat "sin(x)" -j | funcat "cos(x)" --color red -j
# LLM reads the JSON output, decides what to do next
```

The JSON is the tool's internal state made visible. An LLM can read it, reason about it, modify it, and pass it forward. The `-j` flag is a one-character switch between "display for humans" and "think with machines."

---

## Pattern: Rich CLI Help

**Self-documenting tools with usage examples, not just flag descriptions.**

### The problem

Traditional `--help` output lists flags and their types. This tells you the tool's interface but not how to use it. You know that `-r` accepts a renderer name, but not which renderer to choose for your situation. You know that `--dither` exists, but not when you should use it.

For AI agents, this gap is even more problematic. An LLM reading sparse help text must guess at usage patterns. It may construct valid commands that produce poor results because the help text did not explain the intent behind the options.

### How dapple tools solve it

Every dapple CLI tool provides help output that includes concrete usage examples alongside the flag descriptions:

```bash
imgcat photo.jpg                     # Default renderer (auto-detect)
imgcat photo.jpg -r braille          # Force braille
imgcat photo.jpg -r quadrants        # Color blocks
imgcat photo.jpg --dither --contrast # Preprocessing for better output
imgcat photo.jpg -w 120              # Scale to 120 columns wide
```

The examples demonstrate common workflows, not just individual flags. They show flags in combination, with comments explaining *why* you would use each combination.

Consistent flags across all tools reinforce the pattern:

| Flag | Meaning | Used By |
|------|---------|---------|
| `-r` | Renderer selection | imgcat, pdfcat, vidcat, mdcat, funcat |
| `-w` | Width in columns | imgcat, pdfcat, vidcat, funcat |
| `-j` | JSON output mode | funcat, datcat |
| `-o` | Output file | vidcat |
| `--dither` | Floyd-Steinberg dithering | imgcat, pdfcat, vidcat |
| `--contrast` | Auto-contrast | imgcat, pdfcat, vidcat |

Learning one tool teaches you all of them. An LLM that knows how to use imgcat already knows how to use vidcat and pdfcat -- the interface patterns are identical.

### Why it works

Help text is the contract between the tool and its user -- human or machine. Rich help text with examples reduces the gap between "I know this flag exists" and "I know when to use it."

For AI agents specifically, the examples serve as few-shot demonstrations. An LLM reading `imgcat --help` sees concrete command lines that work. It can adapt these patterns to new situations without guessing. The cost of thorough help text is a few extra lines in the source; the benefit is correct usage by every agent that encounters the tool.

The consistency across tools compounds this benefit. Once an LLM learns the `-r` / `-w` / `-j` / `--dither` pattern from one tool, it applies that knowledge to every other tool in the suite. The interface vocabulary is small and reused everywhere.
