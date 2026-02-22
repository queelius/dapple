"""mdcat - Terminal markdown viewer with inline images.

Core implementation for rendering markdown to the terminal using Rich
with dapple for inline image rendering.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from dapple.extras.richrender import (
    DappleMarkdown,
    ImageCache,
    ImageResolver,
    dapple_rendering,
)


@dataclass
class MdcatOptions:
    """Options for markdown rendering.

    Attributes:
        renderer: Renderer name for images ("auto", "braille", "quadrants", etc.)
        width: Console width in characters (None = terminal width)
        image_width: Image width in characters (None = same as console)
        render_images: Whether to render inline images
        theme: Rich markdown theme (default, monokai, etc.)
        code_theme: Pygments theme for code blocks
        hyperlinks: Enable clickable hyperlinks
    """
    renderer: str = "auto"
    width: int | None = None
    image_width: int | None = None
    render_images: bool = True
    theme: str = "default"
    code_theme: str = "monokai"
    hyperlinks: bool = True
    grayscale: bool = False
    no_color: bool = False


def mdcat(
    md_path: str | Path,
    *,
    renderer: str = "auto",
    width: int | None = None,
    image_width: int | None = None,
    render_images: bool = True,
    theme: str = "default",
    code_theme: str = "monokai",
    hyperlinks: bool = True,
    grayscale: bool = False,
    no_color: bool = False,
    dest: TextIO | None = None,
) -> None:
    """Render a markdown file to the terminal.

    Args:
        md_path: Path to the markdown file.
        renderer: Renderer name for images ("auto", "braille", "quadrants", etc.)
        width: Console width in characters (None = terminal width)
        image_width: Image width in characters (None = same as console)
        render_images: Whether to render inline images
        theme: Rich markdown theme
        code_theme: Pygments theme for code blocks
        hyperlinks: Enable clickable hyperlinks
        dest: Output stream (default: stdout)
    """
    from rich.console import Console

    path = Path(md_path)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return

    content = path.read_text()

    # Setup renderer
    from dapple.extras.common import get_renderer
    rend = get_renderer(renderer, grayscale=grayscale, no_color=no_color) if render_images else None

    # Setup console
    term_width = shutil.get_terminal_size().columns
    console_width = width or term_width
    img_width = image_width or min(console_width, 80)

    output = dest if dest is not None else sys.stdout

    # Create console
    console = Console(
        width=console_width,
        file=output,
        force_terminal=dest is None,
        no_color=no_color,
    )

    # Setup image resolver
    cache = ImageCache()
    resolver = ImageResolver(cache=cache, base_path=path)

    # Render
    with dapple_rendering(resolver, rend, render_images, img_width, no_color=no_color):
        md = DappleMarkdown(
            content,
            code_theme=code_theme,
            hyperlinks=hyperlinks,
        )
        console.print(md)


def view(md_path: str | Path, **kwargs) -> None:
    """Quick view of a markdown file with default settings."""
    mdcat(md_path, **kwargs)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="mdcat",
        description="Display markdown files in the terminal with inline images",
    )

    parser.add_argument("files", type=Path, nargs="*", help="Markdown file(s) to display")
    parser.add_argument(
        "-r",
        "--renderer",
        choices=["auto", "braille", "quadrants", "sextants", "ascii", "sixel", "kitty"],
        default="auto",
        help="Renderer for inline images (default: auto)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Console width in characters (default: terminal width)"
    )
    parser.add_argument(
        "--image-width", type=int,
        help="Image width in characters (default: console width)"
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="Skip rendering inline images"
    )
    parser.add_argument(
        "--code-theme", default="monokai",
        help="Pygments theme for code blocks (default: monokai)"
    )
    parser.add_argument(
        "--no-hyperlinks", action="store_true",
        help="Disable clickable hyperlinks"
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)"
    )

    from dapple.extras.common import add_color_args
    add_color_args(parser)

    args = parser.parse_args()

    if not args.files:
        parser.print_help()
        sys.exit(1)

    # Determine output destination
    if args.output:
        dest = open(args.output, "w", encoding="utf-8")
    else:
        dest = None  # Use stdout via console

    errors: list[str] = []
    exit_code = 0
    first_file = True
    try:
        for file_path in args.files:
            if not file_path.exists():
                errors.append(f"{file_path}: File not found")
                continue

            # Print separator for multiple files
            if len(args.files) > 1:
                prefix = "\n" if not first_file else ""
                separator = f"{prefix}{'='*60}\n  {file_path.name}\n{'='*60}\n"
                if dest:
                    dest.write(separator)
                else:
                    print(separator)
                first_file = False

            try:
                mdcat(
                    file_path,
                    renderer=args.renderer,
                    width=args.width,
                    image_width=args.image_width,
                    render_images=not args.no_images,
                    code_theme=args.code_theme,
                    hyperlinks=not args.no_hyperlinks,
                    grayscale=args.grayscale,
                    no_color=args.no_color,
                    dest=dest,
                )
            except Exception as e:
                errors.append(f"{file_path}: {e}")
                continue
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if dest:
            dest.close()

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
