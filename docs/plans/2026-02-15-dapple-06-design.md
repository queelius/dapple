> **STATUS:** Historical plan (2026-02-15). The `diffcat` tool described
> below was removed in 0.9.0. See the current README and `docs/tools/`
> for the up-to-date tool inventory.

# dapple 0.6 Design: Layout Engine + vizlib Promotion + Extras

**Goal:** Strengthen dapple's programmatic foundation (sizing, layout, composition), promote chart primitives to a first-class API, then refactor and extend CLI extras on that foundation.

**Motivation:** Every extra reinvents terminal sizing and aspect-ratio correction. vizlib chart primitives exist but aren't accessible. Canvas composition requires manual pixel math. Fixing these core gaps makes both the library and the CLI tools better.

**Compatibility:** v0.5 is early enough that breaking changes are acceptable. This design targets v0.6.

---

## Phase 1: Layout Engine (Core)

### Canvas.fit() — Smart Sizing

Add a method to Canvas that handles the resize-to-terminal-columns math that every extra currently does manually.

```python
class Canvas:
    def fit(
        self,
        renderer: Renderer,
        *,
        width: int | None = None,    # target columns (None = terminal width)
        height: int | None = None,   # target rows (None = auto from aspect)
        cell_ratio: float = 0.5,     # terminal cell aspect ratio
    ) -> Canvas:
        """Return a new Canvas resized to fit character dimensions.

        Handles:
        - Pixel-to-character math via renderer.cell_width / cell_height
        - Aspect ratio correction for character renderers (braille, sextants, etc.)
        - Passthrough for pixel protocols (sixel, kitty)
        - width=None auto-detects terminal width
        """
```

**Key decisions:**
- Character dimensions at API boundary, pixels internally
- Pixel renderers (sixel, kitty) skip aspect correction
- Returns a new Canvas (immutable pattern)

### Frame — Canvas Wrapper with Metadata

```python
@dataclass
class Frame:
    canvas: Canvas
    width: int | None = None      # target character columns
    height: int | None = None     # target character rows
    title: str | None = None      # optional title text above content
    border: bool = False          # thin box-drawing border
    padding: int = 0              # character padding around content

    def render(self, renderer: Renderer, *, dest: TextIO = None) -> None:
        """Size canvas to fit, apply aspect correction, render."""

    def sized_canvas(self, renderer: Renderer) -> Canvas:
        """Return a new Canvas resized to fit the frame constraints."""
```

**Purpose:** Wraps a Canvas with sizing constraints and presentation metadata. One Frame replaces 15+ lines of sizing boilerplate in each extra.

### Grid — Multi-Canvas Layout

```python
@dataclass
class Grid:
    cells: list[list[Canvas | Frame]]  # rows of cells
    width: int | None = None           # total width in chars (None = terminal)
    gap: int = 1                       # gap between cells (chars)

    def render(self, renderer: Renderer, *, dest: TextIO = None) -> None:
        """Lay out cells, size each proportionally, render row by row."""

    def to_canvas(self, renderer: Renderer) -> Canvas:
        """Flatten the grid into a single Canvas."""
```

**Design constraints (YAGNI):**
- Equal column widths per row — no colspan, no weighted widths
- Rows can have different column counts
- Accepts both Canvas and Frame (plain Canvas auto-wrapped)
- to_canvas() enables nesting and further composition

### terminal_columns() Helper

```python
def terminal_columns(fallback: int = 80) -> int:
    """Get terminal width with fallback."""
```

Lives in `dapple/layout.py` alongside Frame and Grid.

---

## Phase 2: vizlib Promotion

### dapple.charts — Character-Dimension Wrappers

Thin wrapper module around existing vizlib primitives. The key change: accept **character dimensions** instead of pixel dimensions.

```python
# dapple/charts.py

def sparkline(values, *, width=None, height=4, color=None) -> Canvas:
    """Compact line chart. Width/height in characters."""

def line_plot(x, y, *, width=None, height=20, colors=None, labels=None) -> Canvas:
    """Line plot with optional multi-series."""

def bar_chart(labels, values, *, width=None, height=20, horizontal=False) -> Canvas:
    """Bar chart."""

def histogram(values, *, width=None, height=20, bins=20) -> Canvas:
    """Histogram."""

def heatmap(data, *, width=None, height=None) -> Canvas:
    """2D heatmap."""
```

**Import path:** `from dapple.charts import sparkline` (not re-exported at top level to keep namespace clean).

**Internal conversion:** Character dimensions are multiplied by a reference renderer's cell dimensions (braille by default: 2x4) to get pixel dimensions for the underlying vizlib functions.

**vizlib stays in place.** `dapple.extras.vizlib` continues to exist with pixel-dimension APIs for advanced use. `dapple.charts` is a convenience layer, not a replacement.

---

## Phase 3: Extras Refactor + Improvements

### 3a. Dedup Sizing Logic

Replace the 10-20 lines of sizing/aspect-correction code in each extra with `canvas.fit()`:

**Before (in every extra):**
```python
terminal_size = shutil.get_terminal_size()
char_width = width or terminal_size.columns
pixel_width = char_width * rend.cell_width
w, h = pil_img.size
aspect = h / w
new_w = pixel_width
new_h = int(new_w * aspect)
TERMINAL_CELL_RATIO = 0.5
cell_aspect = (rend.cell_height / rend.cell_width) * TERMINAL_CELL_RATIO
new_h = int(new_h * cell_aspect)
pil_img = pil_img.resize((new_w, new_h), ...)
canvas = from_pil(pil_img)
```

**After:**
```python
canvas = from_pil(pil_img)
canvas = canvas.fit(rend, width=args.width)
```

Affected: imgcat, pdfcat, mdcat (image rendering), vidcat.

### 3b. Shared Pager Support

Add `--pager` flag to all extras via `common.py`:

```python
# dapple/extras/common.py
def paged_output(dest: TextIO, pager: bool = False) -> ContextManager[TextIO]:
    """Wrap output in a pager (less -R) if requested."""
```

All CLIs gain `--pager` flag. When enabled, output is piped through `less -R` (or `$PAGER`).

### 3c. Multi-Series Overlay

csvcat and datacat `--plot line` mode gains multi-series support:

```bash
csvcat data.csv --plot line -y revenue,cost    # overlay two series
datacat data.jsonl --plot line -y latency,throughput
```

Uses vizlib's existing `line_plot()` multi-series support (the `colors` and `labels` parameters already exist).

### 3d. stdin for Binary Tools

imgcat and vidcat gain `-` argument for stdin:

```bash
curl -s https://example.com/photo.jpg | imgcat -
ffmpeg -i video.mp4 -f image2pipe - | imgcat -
```

Implementation: detect `-` argument, read stdin to a temp file, process normally, clean up.

---

## Phase 4: New Extras

### ansicat — ANSI Art Viewer

**Motivation:** The `from_ansi` adapter already exists in `dapple/adapters/ansi.py`. It parses ANSI escape sequences into Canvas. This extra is just CLI wiring.

```bash
ansicat artwork.ans                  # render ANSI art
ansicat artwork.ans -r sextants      # re-render through dapple renderer
ansicat artwork.ans -w 80            # fit to width
cat artwork.ans | ansicat -          # stdin support
```

**Files:** `dapple/extras/ansicat/ansicat.py`, `dapple/extras/ansicat/__init__.py`

### diffcat — Visual Image Diff

**Motivation:** Canvas already has hstack and overlay. A visual diff is a natural composition: render two images side-by-side, optionally highlight pixel differences.

```bash
diffcat before.png after.png                    # side-by-side
diffcat before.png after.png --mode overlay     # difference overlay
diffcat before.png after.png --mode highlight   # highlight changed regions
```

**Implementation:**
1. Load both images as Canvas
2. `side-by-side` mode: Frame each, hstack with gap
3. `overlay` mode: compute `abs(canvas1.bitmap - canvas2.bitmap)` as difference bitmap
4. `highlight` mode: overlay difference heat on original

**Files:** `dapple/extras/diffcat/diffcat.py`, `dapple/extras/diffcat/__init__.py`

---

## File Structure

New files:
```
dapple/layout.py          # Frame, Grid, terminal_columns
dapple/charts.py          # Character-dimension chart wrappers
dapple/extras/ansicat/    # ANSI art viewer
dapple/extras/diffcat/    # Visual image diff
```

Modified files:
```
dapple/canvas.py          # Add .fit() method
dapple/__init__.py        # Export Frame, Grid
dapple/extras/common.py   # Add paged_output()
dapple/extras/imgcat/     # Use canvas.fit(), add stdin, --pager
dapple/extras/pdfcat/     # Use canvas.fit(), add --pager
dapple/extras/mdcat/      # Use canvas.fit(), add --pager
dapple/extras/vidcat/     # Use canvas.fit(), add stdin, --pager
dapple/extras/csvcat/     # Multi-series, --pager
dapple/extras/datacat/    # Multi-series, --pager
dapple/extras/funcat/     # --pager
pyproject.toml            # New entry points, dependency groups
```

## Implementation Order

1. `Canvas.fit()` — foundation, no dependencies
2. `dapple/layout.py` (Frame, Grid) — depends on Canvas.fit()
3. `dapple/charts.py` — depends on layout for auto-sizing
4. Refactor extras to use Canvas.fit() — mechanical, one at a time
5. Pager support in common.py — independent of above
6. Multi-series overlay — depends on charts/vizlib
7. stdin for binary tools — independent
8. ansicat — depends on Canvas.fit()
9. diffcat — depends on Canvas.fit() and Frame/Grid
10. Tests throughout
