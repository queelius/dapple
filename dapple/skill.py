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
    "imgcat": (("PIL",), "Image viewer"),
    "pdfcat": (("PIL", "pypdfium2"), "PDF viewer"),
    "mdcat": (("PIL", "rich"), "Markdown viewer"),
    "vidcat": (("PIL",), "Video frame viewer"),
    "csvcat": ((), "CSV/TSV viewer & plotter"),
    "datacat": ((), "JSON/JSONL viewer & plotter"),
    "funcat": ((), "Math expression plotter"),
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
### imgcat — Image Viewer
Display image files (PNG, JPEG, GIF, BMP, TIFF, WebP, etc.) in the terminal.
Best renderer: **sextants** (fills cells with color — photos/graphics look solid).

```bash
imgcat photo.jpg -r sextants -w 80      # best for photos
imgcat chart.png -r sextants -w 100     # diagrams, screenshots
imgcat line-art.png -r braille -w 80    # line art, sketches
imgcat --contrast --dither dark.png     # enhance first
imgcat *.png -r sextants -w 60          # multiple images
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
vidcat video.mp4 --frames 1-10         # specific frame range
vidcat video.mp4 --every 1s            # 1 frame per second
vidcat video.mp4 --asciinema out.cast  # export to asciinema
vidcat -r sextants -w 80 clip.mp4      # control width
```
""",
    "csvcat": """\
### csvcat — CSV/TSV Viewer & Plotter
Display CSV/TSV data as formatted tables or terminal plots.
Best renderer for plots: **braille** (line/bar charts are line art).

```bash
csvcat data.csv                         # formatted table (no renderer)
csvcat data.csv --plot line             # line plot (braille)
csvcat data.csv --plot bar -x name -y sales  # bar chart
csvcat --delimiter '\\t' data.tsv       # TSV file
cat data.csv | csvcat                   # pipe from stdin
csvcat file1.csv file2.csv              # multiple files
```
""",
    "datacat": """\
### datacat — JSON/JSONL Viewer & Plotter
Display structured data (JSON, JSONL) as formatted tables, spark
lines, or terminal plots.
Best renderer for plots: **braille** (data charts are line art).

```bash
datacat records.json                    # formatted table
datacat records.jsonl --plot line       # line plot (braille)
datacat data.json -q .results          # query nested path
datacat --spark data.jsonl              # spark line summary
cat data.jsonl | datacat                # pipe from stdin
datacat file1.json file2.json           # multiple files
```
""",
    "funcat": """\
### funcat — Math Expression Plotter
Plot mathematical expressions in the terminal.
Best renderer: **braille** (math plots are pure line art on empty background).

```bash
funcat "sin(x)"                         # basic plot (braille)
funcat "sin(x)" "cos(x)"               # overlay multiple
funcat "x**2 - 1" --xmin -5 --xmax 5   # custom domain
funcat "exp(-x**2)" -r braille -w 80   # explicit braille
echo "sin(x)" | funcat                  # from stdin
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
  terminal — images, PDFs, markdown, video, CSV, JSON, or math plots. Pick the
  right tool by input type. Output is terminal text meant for the user to read.
---

# dapple — Terminal Graphics Toolkit

Render files and data visually in the user's terminal using Unicode art
(braille, blocks, sextants) or pixel protocols (sixel, kitty).

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
