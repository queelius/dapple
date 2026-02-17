# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

dapple is a unified terminal graphics library. One Canvas API, multiple pluggable renderers (braille, quadrants, sextants, ASCII, sixel, kitty, fingerprint) for displaying bitmaps in the terminal. Core depends only on numpy.

**Related sibling repos:**
- **pixdot** (../pixdot): Focused braille renderer (dapple's `braille` renderer is equivalent)
- **cel** (../cel): Focused quadrant block renderer (dapple's `quadrants` renderer is equivalent)
- **chop** (../chop): Standalone image manipulation CLI, pure PIL/numpy, no dapple dependency

## Commands

```bash
pip install -e ".[dev]"                              # install with all dev deps
pytest                                                # run tests (verbose by default via pyproject.toml)
pytest --cov=dapple --cov-report=term-missing         # with coverage
pytest tests/test_renderers.py::TestBrailleRenderer::test_render_basic -v  # single test
python -c "from dapple import Canvas, braille; print('OK')"               # verify imports
```

## Architecture

### Three layers

1. **Core** (`dapple/canvas.py`, `dapple/renderers/`, `dapple/color.py`, `dapple/preprocess.py`, `dapple/auto.py`) — numpy only, no optional deps
2. **Adapters** (`dapple/adapters/`) — bridge external libraries (PIL, matplotlib, cairo, ANSI) to Canvas; optional deps
3. **Extras** (`dapple/extras/`) — CLI tools built on dapple (imgcat, funcat, pdfcat, mdcat, vidcat, datcat, htmlcat, compcat, ansicat, plotcat, dashcat, vizlib); each has its own optional dependency group in pyproject.toml

### Data conventions

- **Bitmap**: 2D `NDArray[np.floating]` of shape `(H, W)`, values `0.0`-`1.0`, `float32`. Higher = brighter.
- **Colors**: Optional 3D `NDArray[np.floating]` of shape `(H, W, 3)`, same range. Must match bitmap's `(H, W)`.
- **Luminance**: ITU-R BT.601 coefficients (0.299, 0.587, 0.114) in `dapple/color.py`.
- Canvas properties: `.shape` returns `(H, W)` (numpy convention), `.size` returns `(W, H)` (PIL convention).

### Renderer pattern (frozen dataclass + `__call__`)

Every renderer follows the same template:
1. `@dataclass(frozen=True)` with configuration fields (e.g., `threshold`, `color_mode`)
2. `cell_width` / `cell_height` properties defining pixel-to-character ratio
3. `render(bitmap, colors, *, dest: TextIO)` — writes directly to stream, never returns strings
4. `__call__(**overrides)` — returns a new instance with modified options
5. Module-level convenience instance (e.g., `braille = BrailleRenderer()`)

Both the class and the default instance are exported from `dapple/renderers/__init__.py` and re-exported from `dapple/__init__.py`.

### Adapter pattern

Each adapter in `dapple/adapters/` provides:
- A class (e.g., `NumpyAdapter`, `PILAdapter`) with a `to_canvas()` method
- A module-level convenience function (e.g., `from_array`, `from_pil`) wrapping the class
- Convenience functions are re-exported from `dapple/__init__.py`
- For RGB input, adapters compute luminance via `dapple.color.luminance()` to produce the grayscale bitmap, keeping the original RGB as colors

### Extras / CLI tool pattern

Each extra in `dapple/extras/<tool>/` provides:
- An options dataclass
- A core function (e.g., `imgcat()`, `view()`)
- A `main()` function with argparse, registered as a console script in `pyproject.toml`
- All share `dapple/extras/common.py` for renderer selection (`get_renderer`) and preprocessing (`apply_preprocessing`)
- Import via `dapple.extras.X` namespace (e.g., `from dapple.extras.imgcat import imgcat`)

### Canvas output flow

`Canvas.out(renderer, dest)` is the primary output method. It handles:
- `dest=None` → stdout
- `dest="path.txt"` → opens file
- `dest=TextIO` → writes directly

`Canvas.__str__()` uses the default renderer (set at construction or defaults to braille) and writes to a `StringIO`, used for `print(canvas)`.

## Key design rules

- **Stream-based output**: Renderers write to `TextIO` dest, never allocate intermediate strings for the full output.
- **Bitmap and colors are separate**: Canvas holds both. Renderers decide which to use.
- **No image I/O in core**: Core only needs numpy. Image loading lives in adapters.
- **Frozen dataclasses**: Renderers are immutable; `__call__` creates new variants.
- **`from __future__ import annotations`**: Used in every module for PEP 604 union syntax (`X | None`).
- **TYPE_CHECKING guards**: Heavy imports like `NDArray` and `Renderer` are behind `if TYPE_CHECKING:` blocks.

## Dependencies

- **Core**: numpy only
- **Adapters** (`[adapters]`): pillow, matplotlib
- **Individual tools**: `[imgcat]`, `[pdfcat]` (adds pypdfium2), `[mdcat]` (adds rich), `[vidcat]`, etc.
- **All tools** (`[all-tools]`): all extras deps bundled
- **Dev** (`[dev]`): pytest, pytest-cov, all tools, all adapters

## Test structure

Tests mirror source modules: `test_canvas.py`, `test_renderers.py`, `test_adapters.py`, `test_auto.py`, etc. Each extra has its own test file (`test_imgcat.py`, `test_funcat.py`, ...). All under `tests/`. Coverage config excludes `TYPE_CHECKING` blocks and abstract methods.
