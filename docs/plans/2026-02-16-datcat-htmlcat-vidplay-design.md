# Design: datcat unification, htmlcat, vidcat --play

Date: 2026-02-16

Three changes to dapple's extras: unify data viewing into datcat, add HTML terminal viewing, and add in-place video playback.

## 1. datcat — unified data viewer

### What

Rename `datacat` → `datcat`. Absorb `csvcat` entirely. One tool for all structured data: JSON, JSONL, CSV, TSV.

### Why

- Users think in "data", not file formats
- csvcat and datacat share 80% of their output logic (tables, bar charts, sparklines, plots)
- Two tools for the same domain is friction

### Internal representation

Standardize on `list[dict]` for all formats. CSV rows get converted to dicts on parse. One representation means no branching in downstream functions (table formatting, chart extraction, plotting).

### Changes

| Action | Path |
|--------|------|
| RENAME | `dapple/extras/datacat/` → `dapple/extras/datcat/` |
| ABSORB | csvcat parsing code (`read_csv`, `detect_delimiter`, `CsvData` → `list[dict]` conversion, `format_table`, `extract_categories`, `extract_numeric`) into `datcat.py` |
| DELETE | `dapple/extras/csvcat/` (entire directory) |
| UPDATE | `pyproject.toml` — rename dep group, console script: `datcat = "dapple.extras.datcat.cli:main"`, remove csvcat entry |
| UPDATE | `dapple/skill.py` — update tool registry |
| UPDATE | `dapple/extras/__init__.py` if needed |
| DELETE | `tests/test_csvcat.py` |
| RENAME+MERGE | `tests/test_datacat.py` → `tests/test_datcat.py`, absorb csvcat tests |
| UPDATE | docs, README, blog posts — s/datacat/datcat/, s/csvcat/datcat/ |

### Format detection

`detect_format(text, filename=None)`:
- `.json` extension or `{`/`[` start → JSON
- `.jsonl` extension or every line parses as JSON → JSONL
- `.csv`/`.tsv` extension or delimiter detected → CSV/TSV
- Fallback: try CSV with comma delimiter

### CLI flags

All existing datacat + csvcat flags unified:
- Display: `--table` (default), `--tree`, `--json` (pretty-print)
- Charts: `--bar COL`, `--spark COL`, `--plot COL[,COL2]`, `--histogram COL`, `--heatmap COL1,COL2`
- Filtering: `--head N`, `--tail N`, `--sort COL`, `--cols COL1,COL2`, `--query EXPR`
- CSV-specific: `--delimiter CHAR`, `--no-header`
- Common: `--renderer`, `--width`, `--height`, `--output`

## 2. htmlcat — HTML terminal viewer

### What

New extra: render HTML files in the terminal with syntax highlighting, styled text, and inline dapple images.

### Approach

HTML → markdown (via `markdownify`) → Rich rendering (same pipeline as mdcat).

This handles 90% of terminal-viewable HTML (documentation, articles, READMEs). Complex CSS/JS-heavy pages aren't the use case.

### Shared components

Extract mdcat's `DappleImageItem` (Rich image rendering via dapple) into `dapple/extras/common.py` so both mdcat and htmlcat can use it.

### Changes

| Action | Path |
|--------|------|
| CREATE | `dapple/extras/htmlcat/__init__.py` |
| CREATE | `dapple/extras/htmlcat/htmlcat.py` — core: read HTML, convert via markdownify, render via Rich |
| CREATE | `dapple/extras/htmlcat/cli.py` — argparse, main() |
| EXTRACT | mdcat's `DappleImageItem` + `DappleMarkdown` → `dapple/extras/common.py` (or `dapple/extras/richrender.py`) |
| UPDATE | mdcat to import shared component |
| UPDATE | `pyproject.toml` — dep group: `htmlcat = ["pillow>=9.0", "rich>=13.0", "markdownify>=0.11"]`, console script |
| UPDATE | `dapple/skill.py` — register htmlcat |
| CREATE | `tests/test_htmlcat.py` |
| CREATE | `docs/tools/htmlcat.md` |

### CLI flags

- `htmlcat file.html` — render to terminal
- `--width N` — output width
- `--renderer` — for inline images
- `--no-images` — skip image rendering
- `--raw` — dump converted markdown instead of rendering

## 3. vidcat `--play` — in-place playback

### What

New `--play` flag for vidcat. Renders video frames in-place by overwriting previous frame output using ANSI cursor movement. No terminal scrolling.

### Mechanism

1. Extract frames (using existing `extract_frames()`)
2. Render first frame, count output lines (N)
3. For each subsequent frame:
   - Write `\033[{N}A` (cursor up N lines)
   - Write `\033[J` (clear from cursor to end)
   - Render new frame
   - `flush()` for real-time display
4. Sleep `1/fps` between frames

### Counting lines

Render first frame to a `StringIO`, count `\n` occurrences, then write to real dest. Use that count for all subsequent cursor-up operations (frame dimensions are fixed).

### Fallback

If dest is not a TTY (`not dest.isatty()`), fall back to normal stacked output. Print a warning to stderr.

### Changes

| Action | Path |
|--------|------|
| UPDATE | `dapple/extras/vidcat/vidcat.py` — add `play` param to `vidcat()`, add `_play_frames()` helper |
| UPDATE | `VidcatOptions` — add `play: bool = False`, `fps: float = 10.0` |
| UPDATE | vidcat CLI — add `--play` and `--fps` flags |
| UPDATE | `dapple/skill.py` — update vidcat description |
| CREATE | tests for play mode (mock TTY, verify cursor codes emitted) |

### CLI

```
vidcat video.mp4 --play              # play at 10fps (default)
vidcat video.mp4 --play --fps 24     # play at 24fps
vidcat video.mp4 --play --width 60   # smaller playback
vidcat animation.gif --play          # works for GIFs too
```

## Implementation order

1. **datcat** — biggest structural change, rename+merge, gets it out of the way
2. **vidcat --play** — isolated change to one file, quick win
3. **htmlcat** — new module, depends on shared component extraction from mdcat

## Dependencies summary

No new core dependencies. Per-extra:
- datcat: no new deps (csvcat was pure stdlib)
- htmlcat: `markdownify>=0.11` (new), `rich>=13.0` + `pillow>=9.0` (shared with mdcat)
- vidcat: no new deps
