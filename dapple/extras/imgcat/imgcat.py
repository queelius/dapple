"""imgcat - Terminal image viewer.

Core implementation for rendering images to the terminal using dapple.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from dapple.renderers import Renderer


@dataclass
class ImgcatOptions:
    """Options for image rendering.

    Attributes:
        renderer: Renderer name or instance ("auto", "braille", "quadrants", etc.)
        width: Output width in characters (None = terminal width)
        height: Output height in characters (None = auto)
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output entirely
    """
    renderer: str = "auto"
    width: int | None = None
    height: int | None = None
    dither: bool = False
    contrast: bool = False
    invert: bool = False
    grayscale: bool = False
    no_color: bool = False


def get_renderer(name: str, options: ImgcatOptions) -> Renderer:
    """Get a renderer by name with appropriate configuration."""
    from dapple.extras.common import get_renderer as _get_renderer

    return _get_renderer(name, grayscale=options.grayscale, no_color=options.no_color)


def imgcat(
    image_path: str | Path,
    *,
    renderer: str = "auto",
    width: int | None = None,
    height: int | None = None,
    dither: bool = False,
    contrast: bool = False,
    invert: bool = False,
    grayscale: bool = False,
    no_color: bool = False,
    dest: TextIO | None = None,
) -> None:
    """Render an image to the terminal.

    Args:
        image_path: Path to the image file.
        renderer: Renderer name ("auto", "braille", "quadrants", etc.)
        width: Output width in characters (None = terminal width)
        height: Output height in characters (None = auto)
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output entirely
        dest: Output stream (default: stdout)

    Example:
        >>> imgcat("photo.jpg")  # Auto-detect and render
        >>> imgcat("photo.jpg", renderer="braille", dither=True)
    """
    try:
        from PIL import Image
        from dapple.adapters.pil import from_pil, load_image
    except ImportError:
        raise ImportError(
            "PIL is required for imgcat. Install with: pip install dapple[imgcat]"
        )

    from dapple.canvas import Canvas
    from dapple.extras.common import apply_preprocessing

    options = ImgcatOptions(
        renderer=renderer,
        width=width,
        height=height,
        dither=dither,
        contrast=contrast,
        invert=invert,
        grayscale=grayscale,
        no_color=no_color,
    )

    # Get renderer
    rend = get_renderer(renderer, options)

    # Determine output width
    if width:
        char_width = width
    else:
        terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        char_width = terminal_size.columns

    # Calculate pixel dimensions
    CELL_PIXEL_WIDTH = 8
    if renderer in ("sixel", "kitty"):
        pixel_width = char_width * CELL_PIXEL_WIDTH
    else:
        pixel_width = char_width * rend.cell_width
    pixel_height = height * rend.cell_height if height else None

    # Load image
    path = Path(image_path)
    canvas = load_image(path, width=pixel_width, height=pixel_height)

    # Correct aspect ratio for character-based renderers
    # Pixel renderers (sixel, kitty) don't need aspect correction
    needs_aspect_correction = renderer not in ("sixel", "kitty")
    if renderer == "auto":
        from dapple.auto import detect_terminal, Protocol
        info = detect_terminal()
        needs_aspect_correction = info.protocol not in (Protocol.KITTY, Protocol.SIXEL)

    if needs_aspect_correction:
        TERMINAL_CELL_RATIO = 0.5
        cell_aspect = (rend.cell_height / rend.cell_width) * TERMINAL_CELL_RATIO
        pil_img = canvas.to_pil()
        w, h = pil_img.size
        new_h = int(h * cell_aspect)
        if new_h > 0:
            pil_img = pil_img.resize((w, new_h), Image.Resampling.LANCZOS)
            canvas = from_pil(pil_img)

    # Apply preprocessing
    if contrast or dither or invert:
        bitmap = apply_preprocessing(
            canvas.bitmap.copy(), contrast=contrast, dither=dither, invert=invert
        )
        canvas = Canvas(bitmap, colors=canvas.colors)

    # Output
    output = dest or sys.stdout
    colors_to_use = None if no_color else canvas._colors
    rend.render(canvas._bitmap, colors_to_use, dest=output)
    output.write("\n")


def view(image_path: str | Path, **kwargs) -> None:
    """Quick view of an image with default settings.

    Alias for imgcat() with default options.

    Args:
        image_path: Path to the image file.
        **kwargs: Additional options passed to imgcat().

    Example:
        >>> view("photo.jpg")
    """
    imgcat(image_path, **kwargs)


# Claude Code skill content
SKILL_CONTENT = '''\
---
name: imgcat
description: >-
  Use when the user asks to show, display, or preview an image file in
  their terminal. This renders images TO THE USER — the output is Unicode
  text (braille dots, block characters) that the user sees visually.
  Do NOT use this to inspect images yourself; you cannot see the rendered output.
---

Display images in the user's terminal using `imgcat` from the dapple library.

**Important**: imgcat renders images as Unicode text to the user's terminal.
You (Claude) cannot visually interpret the output — it appears as encoded
braille/block characters in your context. Use this tool when the *user* wants
to see an image, not when you need to analyze image contents.

## When to use

Invoke this skill when the user asks you to show, display, preview, or view an
image file (PNG, JPEG, GIF, BMP, TIFF, WebP, etc.) in their terminal.

## How to invoke

Run `imgcat` via the Bash tool:

```bash
imgcat <path> -r braille -w 80
```

Always pass `-w 80` (or similar) to keep output readable. Without it, imgcat
uses the full terminal width, which may be too wide for comfortable viewing.

## Key flags

| Flag | Purpose |
|------|---------|
| `-r <name>` | Renderer: `auto`, `braille`, `quadrants`, `sextants`, `ascii`, `sixel`, `kitty` |
| `-w <cols>` | Output width in characters (recommended: 60-100) |
| `-H <rows>` | Output height in characters |
| `--dither` | Floyd-Steinberg dithering for smoother gradients |
| `--contrast` | Auto-contrast enhancement |
| `--invert` | Invert light/dark |
| `--grayscale` | Force grayscale output |
| `--no-color` | Disable ANSI color codes entirely |

## Renderer guidance

- **`braille`** (recommended default) — high-detail Unicode dots, works in every
  terminal, produces text that always displays correctly even when piped or
  captured. Best choice for Claude Code sessions.
- **`quadrants`** — color block characters, good balance of color and detail.
- **`auto`** — auto-detects the best renderer for the current terminal (may
  choose sixel/kitty which won't render in all contexts).
- **`sixel`** / **`kitty`** — true-pixel protocols, only work in supported
  terminals (not in Claude Code TUI).

## Examples

```bash
# Show an image at a comfortable width
imgcat photo.jpg -r braille -w 80

# Color preview with quadrants
imgcat chart.png -r quadrants -w 100

# Enhanced contrast for dark images
imgcat scan.png -r braille -w 80 --contrast

# Multiple images
imgcat *.png -r braille -w 60
```
'''


def skill_install(local: bool = False, global_: bool = False) -> bool:
    """Install the imgcat skill for Claude Code.

    Args:
        local: Install to current project (.claude/skills/)
        global_: Install globally (~/.claude/skills/)

    Returns:
        True if successful
    """
    if local:
        skill_dir = Path.cwd() / ".claude" / "skills" / "imgcat"
    elif global_:
        skill_dir = Path.home() / ".claude" / "skills" / "imgcat"
    else:
        print("Error: Specify --local or --global", file=sys.stderr)
        return False

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(SKILL_CONTENT)
    print(f"Installed skill to: {skill_file}")
    return True


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="imgcat",
        description="Display images in the terminal using dapple",
    )

    # Main arguments first
    parser.add_argument(
        "images", type=Path, nargs="*", help="Image file(s) to display"
    )
    parser.add_argument(
        "-r",
        "--renderer",
        choices=[
            "auto",
            "braille",
            "quadrants",
            "sextants",
            "ascii",
            "sixel",
            "kitty",
            "fingerprint",
        ],
        default="auto",
        help="Renderer to use (default: auto)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters (default: terminal width)"
    )
    parser.add_argument("-H", "--height", type=int, help="Output height in characters")
    parser.add_argument(
        "--dither", action="store_true", help="Apply Floyd-Steinberg dithering"
    )
    parser.add_argument(
        "--contrast", action="store_true", help="Apply auto-contrast"
    )
    parser.add_argument("--invert", action="store_true", help="Invert colors")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--grayscale", action="store_true",
        help="Force grayscale output"
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable color output"
    )

    # Skill management options (as flags instead of subcommand)
    parser.add_argument(
        "--skill-install", action="store_true",
        help="Install Claude Code skill"
    )
    parser.add_argument(
        "--skill-show", action="store_true",
        help="Show Claude Code skill content"
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Install skill to current project (use with --skill-install)"
    )
    parser.add_argument(
        "--global", dest="global_", action="store_true",
        help="Install skill globally (use with --skill-install)"
    )

    args = parser.parse_args()

    # Handle skill options
    if args.skill_show:
        print(SKILL_CONTENT)
        return
    if args.skill_install:
        success = skill_install(local=args.local, global_=args.global_)
        sys.exit(0 if success else 1)

    # Main command
    if not args.images:
        parser.print_help()
        sys.exit(1)

    # Determine output destination
    dest: TextIO
    if args.output:
        dest = open(args.output, "w", encoding="utf-8")
    else:
        dest = sys.stdout

    errors: list[str] = []
    exit_code = 0
    try:
        for image_path in args.images:
            if not image_path.exists():
                errors.append(f"{image_path}: File not found")
                continue

            try:
                imgcat(
                    image_path,
                    renderer=args.renderer,
                    width=args.width,
                    height=args.height,
                    dither=args.dither,
                    contrast=args.contrast,
                    invert=args.invert,
                    grayscale=args.grayscale,
                    no_color=args.no_color,
                    dest=dest,
                )
            except Exception as e:
                errors.append(f"{image_path}: {e}")
                continue
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        exit_code = 1
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if args.output:
            dest.close()

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        exit_code = 1  # Any errors means exit 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
