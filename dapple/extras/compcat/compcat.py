"""compcat - Compare renderers side-by-side.

Shows the same image rendered with different dapple renderers in a grid.
Each cell uses its own named renderer — the whole point of the tool.
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from typing import TextIO

DEFAULT_RENDERERS = ["braille", "sextants", "quadrants", "ascii"]


def compcat(
    image_path: str | Path,
    renderers: list[str] | None = None,
    *,
    width: int | None = None,
    grayscale: bool = False,
    no_color: bool = False,
    dest: TextIO | None = None,
) -> None:
    """Compare an image across multiple renderers.

    Renders the image once per requested renderer, then lays the results
    out side-by-side in a single row. Each cell shows the renderer's own
    output, so fidelity differences between braille/sextants/quadrants/etc.
    are directly visible.

    Args:
        image_path: Path to the image file.
        renderers: List of renderer names to compare.
        width: Total output width in characters (None = terminal width).
        grayscale: Force grayscale output.
        no_color: Disable color output.
        dest: Output stream (default: stdout).
    """
    try:
        from dapple.adapters.pil import load_image
    except ImportError:
        raise ImportError(
            "PIL is required for compcat. Install with: pip install dapple[imgcat]"
        )

    from dapple.extras.common import get_renderer
    from dapple.layout import terminal_columns, terminal_fit

    renderer_names = renderers or DEFAULT_RENDERERS
    output = dest or sys.stdout

    # Load image once; each renderer gets its own fitted copy.
    source_canvas = load_image(Path(image_path))

    total_width = width or terminal_columns()
    num_cells = len(renderer_names)
    gap = 1
    cell_width = max(4, (total_width - gap * (num_cells - 1)) // num_cells)

    # Render every cell with its own named renderer. For pixel renderers
    # (sixel, kitty) the output contains escape sequences that don't
    # line-align naturally — we still include them, but callers are warned.
    rendered: list[list[str]] = []
    titles: list[str] = []

    for name in renderer_names:
        rend = get_renderer(name, grayscale=grayscale, no_color=no_color)
        fitted, fitted_rend = terminal_fit(source_canvas, rend, width=cell_width)

        buf = StringIO()
        fitted_rend.render(fitted.bitmap, fitted.colors, dest=buf)
        lines = buf.getvalue().rstrip("\n").split("\n")
        rendered.append(lines)
        titles.append(name)

    # Emit titles row, then the rendered content row-by-row.
    title_parts = [title.center(cell_width)[:cell_width] for title in titles]
    output.write((" " * gap).join(title_parts) + "\n")

    max_lines = max(len(cell_lines) for cell_lines in rendered) if rendered else 0
    for line_idx in range(max_lines):
        parts: list[str] = []
        for cell_lines in rendered:
            parts.append(cell_lines[line_idx] if line_idx < len(cell_lines) else "")
        output.write((" " * gap).join(parts) + "\n")


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="compcat",
        description="Compare image renderers side-by-side",
    )
    parser.add_argument("image", type=Path, help="Image file to compare")
    parser.add_argument(
        "renderers",
        nargs="*",
        default=DEFAULT_RENDERERS,
        help=f"Renderers to compare (default: {' '.join(DEFAULT_RENDERERS)})",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters (default: terminal width)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)",
    )

    from dapple.extras.common import add_color_args
    add_color_args(parser)

    args = parser.parse_args()

    if not args.image.exists():
        print(f"Error: File not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    dest = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        compcat(
            args.image, args.renderers,
            width=args.width,
            grayscale=args.grayscale,
            no_color=args.no_color,
            dest=dest,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if args.output:
            dest.close()


if __name__ == "__main__":
    main()
