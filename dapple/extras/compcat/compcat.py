"""compcat - Compare renderers side-by-side.

Shows the same image rendered with different dapple renderers in a grid.
"""

from __future__ import annotations

import sys
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
    from dapple.layout import Frame, Grid, terminal_columns

    renderer_names = renderers or DEFAULT_RENDERERS
    output = dest or sys.stdout

    # Load image once
    canvas = load_image(Path(image_path))

    # Build grid row: one Frame per renderer
    frames = [Frame(canvas=canvas, title=name) for name in renderer_names]

    grid = Grid([frames], width=width or terminal_columns())

    # Render with sextants (good default for comparison output)
    display_rend = get_renderer("sextants", grayscale=grayscale, no_color=no_color)
    grid.render(display_rend, dest=output)


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
