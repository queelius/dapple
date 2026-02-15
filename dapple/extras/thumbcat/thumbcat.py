"""thumbcat - Image contact sheet.

Displays multiple images as thumbnails in a grid layout.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO


def thumbcat(
    image_paths: list[str | Path],
    *,
    cols: int = 4,
    width: int | None = None,
    renderer: str = "sextants",
    titles: bool = True,
    dest: TextIO | None = None,
) -> None:
    """Display images as a contact sheet grid.

    Args:
        image_paths: Paths to image files.
        cols: Number of columns per row.
        width: Total output width in characters (None = terminal width).
        renderer: Renderer name for display.
        titles: Show filenames as titles.
        dest: Output stream (default: stdout).
    """
    try:
        from dapple.adapters.pil import load_image
    except ImportError:
        raise ImportError(
            "PIL is required for thumbcat. Install with: pip install dapple[imgcat]"
        )

    from dapple.extras.common import get_renderer
    from dapple.layout import Frame, Grid, terminal_columns

    output = dest or sys.stdout
    rend = get_renderer(renderer)
    total_width = width or terminal_columns()

    # Load all images into frames
    frames = []
    for path in image_paths:
        path = Path(path)
        if not path.exists():
            print(f"Warning: {path}: File not found", file=sys.stderr)
            continue
        try:
            canvas = load_image(path)
            title = path.name if titles else None
            frames.append(Frame(canvas=canvas, title=title))
        except Exception as e:
            print(f"Warning: {path}: {e}", file=sys.stderr)
            continue

    if not frames:
        print("Error: No images to display", file=sys.stderr)
        return

    # Arrange into rows
    rows = []
    for i in range(0, len(frames), cols):
        rows.append(frames[i:i + cols])

    grid = Grid(rows, width=total_width)
    grid.render(rend, dest=output)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="thumbcat",
        description="Display images as a contact sheet grid",
    )
    parser.add_argument(
        "images", type=Path, nargs="+",
        help="Image file(s) to display",
    )
    parser.add_argument(
        "--cols", type=int, default=4,
        help="Number of columns (default: 4)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters (default: terminal width)",
    )
    parser.add_argument(
        "-r", "--renderer", default="sextants",
        help="Renderer to use (default: sextants)",
    )
    parser.add_argument(
        "--no-titles", action="store_true",
        help="Hide filenames",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    dest = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        thumbcat(
            args.images,
            cols=args.cols,
            width=args.width,
            renderer=args.renderer,
            titles=not args.no_titles,
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
