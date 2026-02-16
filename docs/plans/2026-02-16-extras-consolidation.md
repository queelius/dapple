# Extras Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate dapple extras — merge csvcat into datcat, thumbcat into imgcat, add htmlcat, add vidcat --play, fix vidcat --asciinema.

**Architecture:** Each extra owns a *domain* (images, data, video, etc.), not a file extension. Consolidate tools that share a domain. Add htmlcat for a new domain. Enhance vidcat with in-place playback.

**Tech Stack:** Python 3.12, numpy, rich, markdownify, pillow, ffmpeg (external)

---

## Phase 1: datcat (rename datacat + absorb csvcat)

### Task 1: Rename datacat → datcat directory and module

**Files:**
- Rename: `dapple/extras/datacat/` → `dapple/extras/datcat/`
- Rename: `tests/test_datacat.py` → `tests/test_datcat.py`
- Modify: `pyproject.toml` — update console script and dep group
- Modify: `dapple/skill.py` — update tool registry

**Step 1: Rename the directory**

```bash
git mv dapple/extras/datacat dapple/extras/datcat
git mv tests/test_datacat.py tests/test_datcat.py
```

**Step 2: Update all internal imports**

In `dapple/extras/datcat/__init__.py`, `cli.py`, and `datcat.py`:
- `dapple.extras.datacat` → `dapple.extras.datcat`

In `tests/test_datcat.py`:
- `dapple.extras.datacat` → `dapple.extras.datcat`
- CLI subprocess calls: `dapple.extras.datacat.cli` → `dapple.extras.datcat.cli`

In `pyproject.toml`:
- `datacat = "dapple.extras.datacat.cli:main"` → `datcat = "dapple.extras.datcat.cli:main"`
- Rename dep group `[datacat]` → `[datcat]`

In `dapple/skill.py`:
- `"datacat"` → `"datcat"` in `_EXTRAS` and `_TOOL_SECTIONS`

**Step 3: Run tests**

```bash
pytest tests/test_datcat.py -v
```

**Step 4: Commit**

```bash
git commit -m "Rename datacat → datcat"
```

### Task 2: Absorb csvcat parsing into datcat

**Files:**
- Modify: `dapple/extras/datcat/datcat.py` — add CSV/TSV parsing functions
- Modify: `dapple/extras/datcat/cli.py` — add CSV-specific CLI flags and format routing
- Delete: `dapple/extras/csvcat/` (entire directory)
- Delete: `tests/test_csvcat.py`
- Modify: `tests/test_datcat.py` — absorb csvcat unit tests
- Modify: `pyproject.toml` — remove csvcat entries

**Step 1: Write failing tests for CSV support in datcat**

Add to `tests/test_datcat.py`:
- `TestDetectFormat` — add tests for CSV/TSV detection
- `TestReadCsv` — move all csvcat parsing tests (basic_csv, tsv, explicit_delimiter, no_header, empty_input, header_only, ragged_rows)
- `TestCLI` — add CSV input tests (stdin csv table, --head, --tail, --sort, --cols, --delimiter, --no-header)

```bash
pytest tests/test_datcat.py -v
# Expected: new tests FAIL (no CSV support yet)
```

**Step 2: Add CSV/TSV support to datcat.py**

Move from `csvcat.py` into `datcat.py`:
- `detect_delimiter(sample: str) -> str`
- `read_csv(text: str, delimiter: str | None, has_header: bool) -> list[dict]` — note: returns `list[dict]` now, not `CsvData`
- `format_table(records: list[dict], cycle_colors: bool) -> str` — unified table formatter for both JSON and CSV
- `select_columns(records: list[dict], cols: list[str]) -> list[dict]`
- `sort_by(records: list[dict], column: str, reverse: bool) -> list[dict]`
- `head(records: list[dict], n: int) -> list[dict]`
- `tail(records: list[dict], n: int) -> list[dict]`
- `extract_numeric(records: list[dict], column: str) -> list[float]`
- `extract_categories(records: list[dict], column: str) -> tuple[list[str], list[float]]`

Update `detect_format()` to detect CSV/TSV:
```python
def detect_format(text: str, filename: str | None = None) -> str:
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in (".csv", ".tsv"): return "csv"
        if ext == ".jsonl": return "jsonl"
        if ext == ".json": return "json"
    # Content sniffing: try JSON first, then CSV
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")):
        return "json"  # or "jsonl" per existing logic
    return "csv"  # fallback
```

**Step 3: Add CSV flags to datcat CLI**

Add to `cli.py` parser:
- `--delimiter CHAR` / `-d` — explicit delimiter
- `--no-header` — treat first row as data
- `--sort COLUMN` — sort by column
- `--cols COL1,COL2` — select columns
- `--desc` — reverse sort

Route CSV input through the new parsing path in `_get_inputs()` or a new `_read_input()` dispatcher.

**Step 4: Run tests**

```bash
pytest tests/test_datcat.py -v
# Expected: all tests PASS
```

**Step 5: Delete csvcat**

```bash
git rm -r dapple/extras/csvcat/
git rm tests/test_csvcat.py
```

Update `pyproject.toml`: remove `csvcat` console script and dep group.
Update `dapple/skill.py`: remove `"csvcat"` entries.

**Step 6: Run full suite**

```bash
pytest --cov=dapple --cov-report=term-missing
```

**Step 7: Commit**

```bash
git commit -m "Absorb csvcat into datcat — unified data viewer"
```

---

## Phase 2: imgcat absorbs thumbcat

### Task 3: Add --grid mode to imgcat, delete thumbcat

**Files:**
- Modify: `dapple/extras/imgcat/imgcat.py` — add grid/contact-sheet function
- Modify: imgcat CLI — add `--grid` / `--cols` flags
- Delete: `dapple/extras/thumbcat/` (entire directory)
- Modify: `tests/test_imgcat.py` — add grid tests
- Delete: `tests/test_thumbcat.py` (if exists)
- Modify: `pyproject.toml` — remove thumbcat entries
- Modify: `dapple/skill.py` — remove thumbcat, update imgcat description

**Step 1: Write failing tests for grid mode**

Add to `tests/test_imgcat.py`:
- `TestGrid.test_multiple_images_grid` — renders 4 images in 2x2
- `TestGrid.test_single_image_no_grid` — single image still works normally
- `TestGrid.test_no_titles` — `titles=False` suppresses filenames

**Step 2: Move thumbcat's grid logic into imgcat**

The core is small — `thumbcat()` loads images into `Frame`s, arranges in `Grid`, renders. Add this as `imgcat_grid()` or fold into `imgcat()` when multiple paths given:

```python
def imgcat(
    image_path: str | Path | list[str | Path],  # accept list for grid mode
    *,
    grid_cols: int = 4,     # columns when grid mode
    titles: bool = True,    # show filenames in grid
    ...
)
```

When `image_path` is a list with >1 item, switch to grid mode automatically.

**Step 3: Update CLI**

Add flags:
- `--cols N` — grid columns (implies grid mode with multiple images)
- `--no-titles` — hide filenames in grid

**Step 4: Delete thumbcat**

```bash
git rm -r dapple/extras/thumbcat/
```

Update `pyproject.toml` and `dapple/skill.py`.

**Step 5: Run tests and commit**

```bash
pytest tests/test_imgcat.py -v
pytest --cov=dapple --cov-report=term-missing
git commit -m "Absorb thumbcat into imgcat --grid mode"
```

---

## Phase 3: vidcat --play

### Task 4: Add in-place playback to vidcat

**Files:**
- Modify: `dapple/extras/vidcat/vidcat.py` — add `play` parameter, `_play_frames()` helper
- Modify: `VidcatOptions` — add `play: bool`, `fps: float`
- Modify: vidcat CLI — add `--play` and update `--fps`
- Create: test cases for play mode

**Step 1: Write failing tests**

Add to `tests/test_vidcat.py`:
- `TestPlayMode.test_play_emits_cursor_up` — verify ANSI cursor-up codes in output
- `TestPlayMode.test_play_non_tty_fallback` — non-TTY dest falls back to stacked
- `TestPlayMode.test_fps_controls_delay` — verify timing parameter is accepted

**Step 2: Implement `_play_frames()`**

```python
def _play_frames(
    frame_paths: list[Path],
    options: VidcatOptions,
    dest: TextIO,
    fps: float = 10.0,
) -> None:
    """Play frames in-place using ANSI cursor movement."""
    import io

    frame_interval = 1.0 / fps

    # Render first frame to count lines
    buf = io.StringIO()
    render_frame(frame_paths[0], options, buf)
    first_output = buf.getvalue()
    line_count = first_output.count("\n")

    # Write first frame
    dest.write(first_output)
    dest.flush()

    # Overwrite for subsequent frames
    for frame_path in frame_paths[1:]:
        time.sleep(frame_interval)
        # Cursor up + clear
        dest.write(f"\033[{line_count}A\033[J")
        render_frame(frame_path, options, dest)
        dest.flush()
```

**Step 3: Wire into vidcat() and CLI**

Add `play: bool = False` and `fps: float = 10.0` to `vidcat()`.
Add `--play` flag to CLI. Reuse existing `--fps` flag (already exists for asciinema).

When `--play` and dest is TTY: use `_play_frames()`.
When `--play` and dest is not TTY: warn to stderr, fall back to stacked.

**Step 4: Run tests and commit**

```bash
pytest tests/test_vidcat.py -v
git commit -m "Add vidcat --play for in-place terminal playback"
```

### Task 5: Investigate and fix --asciinema

**Files:**
- Modify: `dapple/extras/vidcat/vidcat.py` — fix `to_asciinema()` if broken

**Step 1: Test current behavior**

```bash
vidcat examples/bunny.mp4 --asciinema /tmp/test.cast --max-frames 5
asciinema play /tmp/test.cast
```

Document the actual failure mode. From initial testing, the function runs without error — may be a rendering/playback issue (wrong dimensions, missing clear codes, or timing).

**Step 2: Fix identified issues**

Common issues to check:
- `width`/`height` in header vs actual frame dimensions
- Clear screen escape before first frame
- Frame data encoding (Unicode characters in JSON)
- TTY dimensions baked into cast vs actual playback terminal

**Step 3: Add tests and commit**

```bash
git commit -m "Fix vidcat --asciinema output"
```

---

## Phase 4: htmlcat

### Task 6: Extract shared Rich image rendering from mdcat

**Files:**
- Create: `dapple/extras/richrender.py` — shared `DappleImageItem`, `DappleMarkdown` classes
- Modify: `dapple/extras/mdcat/mdcat.py` — import from richrender instead of defining locally

**Step 1: Write test that mdcat still works after extraction**

```bash
pytest tests/test_mdcat.py -v
```

**Step 2: Extract classes**

Move `DappleImageItem`, `DappleMarkdown`, and `ImageResolver` from `mdcat.py` into `dapple/extras/richrender.py`. Update mdcat to import from the new location.

**Step 3: Run tests and commit**

```bash
pytest tests/test_mdcat.py -v
git commit -m "Extract shared Rich image rendering into richrender.py"
```

### Task 7: Create htmlcat

**Files:**
- Create: `dapple/extras/htmlcat/__init__.py`
- Create: `dapple/extras/htmlcat/htmlcat.py` — core HTML rendering
- Create: `dapple/extras/htmlcat/cli.py` — CLI entry point
- Create: `tests/test_htmlcat.py`
- Modify: `pyproject.toml` — add dep group and console script
- Modify: `dapple/skill.py` — register htmlcat

**Step 1: Write failing tests**

```python
class TestHtmlcat:
    def test_basic_html(self):
        """Simple HTML renders without error."""
        html = "<h1>Hello</h1><p>World</p>"
        buf = io.StringIO()
        htmlcat_render(html, dest=buf)
        output = buf.getvalue()
        assert "Hello" in output
        assert "World" in output

    def test_html_with_list(self):
        html = "<ul><li>One</li><li>Two</li></ul>"
        buf = io.StringIO()
        htmlcat_render(html, dest=buf)
        assert "One" in buf.getvalue()

    def test_html_table(self):
        html = "<table><tr><th>Name</th></tr><tr><td>Alice</td></tr></table>"
        buf = io.StringIO()
        htmlcat_render(html, dest=buf)
        assert "Alice" in buf.getvalue()

    def test_empty_html(self):
        buf = io.StringIO()
        htmlcat_render("", dest=buf)
        # Should not crash

    def test_no_images_flag(self):
        html = '<img src="missing.png"><p>Text</p>'
        buf = io.StringIO()
        htmlcat_render(html, dest=buf, render_images=False)
        assert "Text" in buf.getvalue()
```

**Step 2: Implement htmlcat.py**

```python
def htmlcat(
    source: str | Path,
    *,
    width: int | None = None,
    renderer: str = "auto",
    render_images: bool = True,
    no_color: bool = False,
    dest: TextIO | None = None,
) -> None:
```

Core logic:
1. Read HTML from file or string
2. Convert to markdown via `markdownify.markdownify(html)`
3. Render via Rich using `DappleMarkdown` from `richrender.py`
4. Write to dest

**Step 3: Implement CLI**

Standard pattern: argparse, `--width`, `--renderer`, `--no-images`, `--raw`, `-o`.

**Step 4: Update pyproject.toml**

```toml
htmlcat = ["pillow>=9.0", "rich>=13.0", "markdownify>=0.11"]
```

Console script:
```toml
htmlcat = "dapple.extras.htmlcat.cli:main"
```

**Step 5: Run tests and commit**

```bash
pytest tests/test_htmlcat.py -v
pytest --cov=dapple --cov-report=term-missing
git commit -m "Add htmlcat — HTML terminal viewer via markdownify + Rich"
```

---

## Phase 5: Docs and cleanup

### Task 8: Update all docs, README, blog posts, skill registry

**Files:**
- Modify: `README.md` — update tool list
- Modify: `docs/tools/index.md` — update tool listing
- Delete: `docs/tools/csvcat.md` (if exists) or redirect
- Create: `docs/tools/datcat.md`
- Create: `docs/tools/htmlcat.md`
- Modify: `docs/tools/imgcat.md` — document --grid
- Modify: `docs/tools/vidcat.md` — document --play
- Modify: `dapple/skill.py` — final audit of all tool descriptions
- Modify: blog posts if they reference old tool names

**Step 1: Update docs**

**Step 2: Run full test suite**

```bash
pytest --cov=dapple --cov-report=term-missing
```

**Step 3: Commit**

```bash
git commit -m "Update docs for extras consolidation"
```

---

## Summary of deletions

| Deleted | Absorbed by |
|---------|-------------|
| `dapple/extras/csvcat/` | datcat |
| `dapple/extras/datacat/` | datcat (renamed) |
| `dapple/extras/thumbcat/` | imgcat `--grid` |
| `tests/test_csvcat.py` | `tests/test_datcat.py` |
| `tests/test_datacat.py` | `tests/test_datcat.py` (renamed) |
| `tests/test_thumbcat.py` | `tests/test_imgcat.py` |

## Final tool inventory

| Tool | Domain | Status |
|------|--------|--------|
| imgcat | Images (single + grid) | Enhanced |
| datcat | Structured data (JSON/JSONL/CSV/TSV) | New (merged) |
| vidcat | Video (stacked + play + asciinema) | Enhanced |
| mdcat | Markdown | Unchanged |
| htmlcat | HTML | New |
| funcat | Math plots | Unchanged |
| pdfcat | PDFs | Unchanged |
| ansicat | ANSI art | Unchanged |
| compcat | Renderer comparison | Unchanged |
| plotcat | Data plots via vizlib | Unchanged |
| dashcat | Dashboard layouts | Unchanged |
