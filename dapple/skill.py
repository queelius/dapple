"""Unified Claude Code skill for dapple terminal graphics tools.

Detects which dapple extras are installed and generates a single
skill file covering all available tools.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _can_import(*modules: str) -> bool:
    """Check whether all named modules are importable."""
    for mod in modules:
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


# Each extra mapped to (required_modules, description for detection output)
_EXTRAS: dict[str, tuple[tuple[str, ...], str]] = {
    "imgcat": (("PIL",), "Image viewer & contact sheet"),
    "pdfcat": (("PIL", "pypdfium2"), "PDF viewer"),
    "mdcat": (("PIL", "rich"), "Markdown viewer"),
    "vidcat": (("PIL",), "Video frame viewer"),
    "datcat": ((), "Structured data viewer (JSON/JSONL/CSV/TSV) & plotter"),
    "funcat": ((), "Math expression plotter"),
    "compcat": (("PIL",), "Renderer comparison"),
    "ansicat": ((), "ANSI art viewer"),
    "plotcat": ((), "Faceted data plots"),
    "dashcat": (("yaml",), "YAML-driven dashboard"),
    "htmlcat": (("rich", "markdownify"), "HTML viewer"),
}


def detect_extras() -> dict[str, bool]:
    """Check which dapple extras have their dependencies satisfied.

    Returns:
        Mapping of extra name to availability.
    """
    return {name: _can_import(*deps) for name, (deps, _) in _EXTRAS.items()}


# ── Per-tool skill sections ──────────────────────────────────────────────────

_TOOL_SECTIONS: dict[str, str] = {
    "imgcat": """\
### imgcat — Image Viewer & Contact Sheet
Display image files (PNG, JPEG, GIF, BMP, TIFF, WebP, etc.) in the terminal.
Multiple images are automatically shown as a grid/contact sheet.
Best renderer: **sextants** (fills cells with color — photos/graphics look solid).

```bash
imgcat photo.jpg -r sextants -w 80      # best for photos
imgcat chart.png -r sextants -w 100     # diagrams, screenshots
imgcat line-art.png -r braille -w 80    # line art, sketches
imgcat --contrast --dither dark.png     # enhance first
imgcat *.png -r sextants -w 60          # multiple images as grid
imgcat photos/*.jpg --cols 4 -w 120     # 4-column contact sheet
imgcat *.png --cols 3 --no-titles       # grid without filenames
```
""",
    "pdfcat": """\
### pdfcat — PDF Viewer
Render PDF pages visually in the terminal. For reading PDF *text*, use
the Read tool with pages parameter instead.
Best renderer: **sextants** (PDF pages have backgrounds, color, layouts).

```bash
pdfcat document.pdf -r sextants         # best for most PDFs
pdfcat -r sextants -w 80 document.pdf   # control width
pdfcat --pages 1-3 document.pdf         # specific pages
pdfcat --pages "1,5,10" document.pdf    # comma-separated
pdfcat --dpi 300 document.pdf           # higher resolution
```
""",
    "mdcat": """\
### mdcat — Markdown Viewer
Render markdown files with rich formatting (syntax highlighting, styled
headings, inline images). For reading markdown *source*, use the Read
tool instead. Inline images use **sextants** by default.

```bash
mdcat README.md                         # rich-formatted view
mdcat --images README.md                # with inline images
mdcat -r sextants -w 80 README.md       # control image renderer
mdcat --code-theme dracula README.md    # code theme
mdcat doc1.md doc2.md                   # multiple files
```
""",
    "vidcat": """\
### vidcat — Video Frame Viewer
Extract and display video frames. Requires ffmpeg.
Best renderer: **sextants** (video frames are photographic content).

```bash
vidcat animation.gif -r sextants        # best for video frames
vidcat video.mp4 --play                # in-place playback animation
vidcat video.mp4 --play --fps 15       # control playback speed
vidcat video.mp4 --frames 1-10         # specific frame range
vidcat video.mp4 --every 1s            # 1 frame per second
vidcat video.mp4 --asciinema out.cast  # export to asciinema
vidcat -r sextants -w 80 clip.mp4      # control width
```
""",
    "datcat": """\
### datcat — Structured Data Viewer & Plotter
Display structured data (JSON, JSONL, CSV, TSV) as formatted tables,
tree views, sparklines, or terminal plots. One tool for all tabular
and hierarchical data.
Best renderer for plots: **braille** (data charts are line art).

```bash
# JSON / JSONL
datcat records.json                    # tree view (default)
datcat records.jsonl --table           # flatten JSONL to table
datcat records.jsonl --plot latency    # line plot of a numeric field
datcat records.jsonl --spark latency   # sparkline of a numeric field
datcat records.jsonl --bar region      # bar chart of category counts
datcat data.json -q .results          # query nested dot-path
datcat data.json --json               # syntax-colored JSON
cat data.jsonl | datcat                # pipe from stdin

# CSV / TSV
datcat data.csv                        # formatted table (auto-detected)
datcat data.csv --plot score           # line plot of a column
datcat data.csv --bar department       # bar chart of category counts
datcat data.csv --spark revenue        # sparkline of a column
datcat data.csv --histogram age        # histogram of numeric column
datcat data.csv --heatmap "q1,q2,q3"  # heatmap of multiple columns
datcat data.csv --cols name,score      # select columns
datcat data.csv --sort score --desc    # sort by column
datcat data.csv -d $'\\t'              # explicit tab delimiter
datcat data.csv --no-header            # first row is data, not headers
```
""",
    "funcat": """\
### funcat — Math Expression Plotter
Plot mathematical expressions and parametric curves in the terminal.
Best renderer: **braille** (math plots are pure line art on empty background).

**Basic plots:**
```bash
funcat "sin(x)"                         # basic plot (braille)
funcat "sin(x)" "cos(x)" --legend      # overlay multiple with legend
funcat "x**2 - 1" --xmin -5 --xmax 5   # custom domain
funcat "exp(-x**2)" -r braille -w 80   # explicit braille
```

**Parametric curves** (functions of t, default t range 0 to 2pi):
```bash
funcat -p "cos(t),sin(t)"              # circle
funcat -p "t*cos(t),t*sin(t)"          # spiral
funcat -p "cos(t),sin(t)" --tmin 0 --tmax 3.14  # half circle
```

**Chaining** (`--json` pipes plot state so multiple curves compose):
```bash
funcat "sin(x)" --json | funcat "cos(x)" --color red       # two colors
funcat -p "cos(t),sin(t)" --json \\
  | funcat -p "0.3*cos(t)+0.3,0.3*sin(t)+0.3" --color blue  # composite figure
```
""",
    "compcat": """\
### compcat — Renderer Comparison
Show the same image rendered with multiple renderers side by side.
Best for comparing visual quality across renderers.

```bash
compcat photo.jpg braille sextants quadrants    # compare renderers
compcat photo.jpg braille sextants -w 80        # control width
```
""",
    "ansicat": """\
### ansicat — ANSI Art Viewer
View ANSI art (.ans) files in the terminal, re-rendered through
dapple renderers. Best renderer: **sextants** (fills colored regions).

```bash
ansicat artwork.ans -r sextants -w 80       # re-render ANSI art
ansicat artwork.ans -r braille              # braille style
cat artwork.ans | ansicat -                 # from stdin
```
""",
    "plotcat": """\
### plotcat — Faceted Data Plots
Group data by a column and create a grid of small-multiple charts.
Best renderer: **braille** (charts are line art).

```bash
plotcat data.csv --facet region --plot line -y sales
plotcat data.jsonl --facet category --plot bar -y type
plotcat data.csv --facet group --plot spark -y value
plotcat data.csv --facet group --plot histogram -y score
```
""",
    "dashcat": """\
### dashcat — YAML Dashboard
Build terminal dashboards from a YAML layout file.
Charts use **braille** by default.

```bash
dashcat layout.yaml                         # render dashboard
dashcat layout.yaml -w 120                  # wider dashboard
```

YAML format:
```yaml
rows:
  - cells:
    - type: sparkline
      source: metrics.jsonl
      query: .cpu
      title: CPU Usage
    - type: bar_chart
      source: sales.csv
      x: region
      y: revenue
      title: Revenue
```
""",
    "htmlcat": """\
### htmlcat — HTML Viewer
Display HTML files in the terminal. Converts HTML to markdown via
markdownify then renders with Rich formatting and dapple inline images.
Best for documentation, articles, READMEs — not CSS/JS-heavy pages.

```bash
htmlcat page.html                          # rich-formatted view
htmlcat page.html -r sextants              # images via sextants
htmlcat page.html --no-images              # skip images
htmlcat page.html --raw                    # show intermediate markdown
htmlcat page.html -w 80 -o out.txt         # fixed width, save to file
htmlcat doc1.html doc2.html                # multiple files
```
""",
}


def generate_skill(extras: dict[str, bool] | None = None) -> str:
    """Build unified skill content with only available tools.

    Args:
        extras: Mapping of extra name to availability.
            If None, detects automatically.

    Returns:
        Complete SKILL.md content.
    """
    if extras is None:
        extras = detect_extras()

    available = [name for name in _EXTRAS if extras.get(name, False)]

    # Build the tool dispatch table
    table_rows = []
    for name in available:
        _, desc = _EXTRAS[name]
        table_rows.append(f"| `{name}` | {desc} |")

    table = "| Tool | Purpose |\n|------|---------|"
    if table_rows:
        table += "\n" + "\n".join(table_rows)

    # Build per-tool sections
    tool_sections = "\n".join(
        _TOOL_SECTIONS[name] for name in available if name in _TOOL_SECTIONS
    )

    # Assemble
    parts = [
        _HEADER,
        table,
        "",
        "## Tools\n",
        tool_sections if tool_sections else "_No extras detected. Install with e.g. `pip install dapple[all-tools]`._\n",
        _COMMON_FLAGS,
        _FOOTER,
    ]

    return "\n".join(parts)


_HEADER = """\
---
name: dapple
description: >-
  Use when the user asks to display, preview, or view files visually in their
  terminal, OR to plot mathematical functions, parametric curves, equations, or
  data charts. Covers: images, PDFs, markdown, video, structured data (JSON,
  JSONL, CSV, TSV), math/parametric plots (funcat), ANSI art, HTML pages,
  contact sheets, dashboards, renderer comparisons, or faceted data plots.
  Tools: imgcat, pdfcat, mdcat, vidcat, datcat, funcat, compcat, ansicat,
  plotcat, dashcat, htmlcat. Output is terminal text meant for the user to read.
---

# dapple — Terminal Graphics Toolkit

Render files and data visually in the user's terminal using Unicode art
(braille, blocks, sextants) or pixel protocols (sixel, kitty). Also plot
mathematical functions, parametric curves, and data charts.

The output is terminal text that the user sees. You can see it too, but these
tools are meant for **human viewing** — do not use them to analyze file
contents. Use the Read tool (or other appropriate tools) when you need to
understand file contents yourself.
"""

_COMMON_FLAGS = """\
## Common Flags

All tools share these flags (where applicable):

| Flag | Purpose |
|------|---------|
| `-r RENDERER` | `auto`, `braille`, `quadrants`, `sextants`, `ascii`, `sixel`, `kitty` |
| `-w WIDTH` | Output width in characters (recommended: 60-100) |
| `-H HEIGHT` | Output height in characters |
| `--dither` | Floyd-Steinberg dithering for smoother gradients |
| `--contrast` | Auto-contrast enhancement |
| `--invert` | Invert brightness |
| `--grayscale` | Force grayscale output |
| `--no-color` | Disable ANSI color codes entirely |
| `-o FILE` | Write output to file instead of stdout |

## Choosing a Renderer

The two main renderers are **sextants** and **braille**. Pick based on content:

| Content type | Best renderer | Why |
|-------------|--------------|-----|
| Photos, images | **sextants** | Fills cells with color — solid backgrounds, continuous tone |
| PDFs, screenshots | **sextants** | Layouts have backgrounds, color, filled regions |
| Video frames | **sextants** | Photographic content needs filled cells |
| Math plots | **braille** | Line art on empty background — higher dot resolution (2×4) |
| Data charts | **braille** | Line/bar/scatter plots are line art |
| Line drawings | **braille** | Crisp dots, no fill needed |

**Why not always braille?** Braille characters are *dots* — they can't fill a
cell, so backgrounds appear as gaps. A photo rendered in braille looks like a
stipple drawing. Sextants (2×3 sub-cells per character) can fill entire regions,
so photos, PDFs, and anything with continuous tone looks solid and readable.

**Why not always sextants?** Braille has higher resolution (2×4 = 8 dots vs
2×3 = 6 sub-cells) and produces crisper lines. For plots and line art where
the background is empty, braille gives sharper detail.

Other renderers:
- **`auto`** — auto-detects best for the terminal (usually sextants or braille).
- **`quadrants`** — 2×2 color blocks, lower resolution than sextants.
- **`ascii`** — ASCII characters only, maximum compatibility.
- **`sixel`** / **`kitty`** — true-pixel protocols, only work in supported
  terminals (not in Claude Code TUI).
"""

_FOOTER = """\
## Regenerating This Skill

If you install additional dapple extras later, regenerate with:

```bash
dapple-skill --global    # or --local for project-specific
```
"""


def install(*, global_: bool = False, local: bool = False) -> bool:
    """Write the unified skill file.

    Args:
        global_: Install to ~/.claude/skills/dapple/
        local: Install to ./.claude/skills/dapple/

    Returns:
        True if successful.
    """
    if global_:
        skill_dir = Path.home() / ".claude" / "skills" / "dapple"
    elif local:
        skill_dir = Path.cwd() / ".claude" / "skills" / "dapple"
    else:
        print("Error: Specify --global or --local", file=sys.stderr)
        return False

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    content = generate_skill()
    skill_file.write_text(content)
    print(f"Installed dapple skill to: {skill_file}")

    # Report what was detected
    extras = detect_extras()
    available = [n for n, ok in extras.items() if ok]
    missing = [n for n, ok in extras.items() if not ok]
    if available:
        print(f"  Available tools: {', '.join(available)}")
    if missing:
        print(f"  Not installed:   {', '.join(missing)}")
        print(f"  Install with:    pip install dapple[all-tools]")

    return True


def show() -> None:
    """Print the generated skill to stdout."""
    print(generate_skill())


def main() -> None:
    """CLI entry point for dapple-skill."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="dapple-skill",
        description="Install the unified dapple Claude Code skill",
    )
    parser.add_argument(
        "--global", dest="global_", action="store_true",
        help="Install skill globally (~/.claude/skills/dapple/)",
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Install skill to current project (.claude/skills/dapple/)",
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Print generated skill content to stdout (don't install)",
    )
    parser.add_argument(
        "--detect", action="store_true",
        help="Show which extras are available",
    )

    args = parser.parse_args()

    if args.detect:
        extras = detect_extras()
        for name, available in extras.items():
            _, desc = _EXTRAS[name]
            status = "available" if available else "missing deps"
            print(f"  {name:10s}  {status:14s}  ({desc})")
        return

    if args.show:
        show()
        return

    if not args.global_ and not args.local:
        parser.print_help()
        sys.exit(1)

    success = install(global_=args.global_, local=args.local)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
