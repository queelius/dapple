"""diffcat - Visual image diff.

Shows differences between two images side-by-side, as an overlay, or highlighted.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, TextIO

import numpy as np


def diffcat(
    image_a: str | Path,
    image_b: str | Path,
    *,
    mode: Literal["side", "overlay", "highlight"] = "side",
    renderer: str = "sextants",
    width: int | None = None,
    dest: TextIO | None = None,
) -> None:
    """Show visual differences between two images.

    Args:
        image_a: Path to the first image (before).
        image_b: Path to the second image (after).
        mode: Comparison mode:
            - "side": Side-by-side comparison.
            - "overlay": Difference heatmap (abs difference).
            - "highlight": Overlay difference onto original.
        renderer: Renderer name for output.
        width: Output width in characters (None = terminal width).
        dest: Output stream (default: stdout).
    """
    try:
        from dapple.adapters.pil import load_image
    except ImportError:
        raise ImportError(
            "PIL is required for diffcat. Install with: pip install dapple[imgcat]"
        )

    from dapple.canvas import Canvas
    from dapple.extras.common import get_renderer
    from dapple.layout import Frame, Grid, terminal_columns, terminal_fit
    from dapple.preprocess import resize

    output = dest or sys.stdout
    rend = get_renderer(renderer)
    total_width = width or terminal_columns()

    # Load both images
    canvas_a = load_image(Path(image_a))
    canvas_b = load_image(Path(image_b))

    # Match dimensions (resize B to A's size)
    if canvas_a.shape != canvas_b.shape:
        h, w = canvas_a.shape
        new_bitmap = resize(canvas_b.bitmap, h, w)
        new_colors = None
        if canvas_b.colors is not None:
            new_colors = resize(canvas_b.colors, h, w)
        canvas_b = Canvas(new_bitmap, colors=new_colors)

    if mode == "side":
        # Side-by-side with titles
        name_a = Path(image_a).name
        name_b = Path(image_b).name
        frame_a = Frame(canvas=canvas_a, title=name_a)
        frame_b = Frame(canvas=canvas_b, title=name_b)
        grid = Grid([[frame_a, frame_b]], width=total_width)
        grid.render(rend, dest=output)

    elif mode == "overlay":
        # Absolute difference as heatmap
        diff = np.abs(canvas_a.bitmap - canvas_b.bitmap)
        # Color: black=same, red=different
        colors = np.zeros((*diff.shape, 3), dtype=np.float32)
        colors[:, :, 0] = diff  # Red channel
        diff_canvas = Canvas(diff, colors=colors)
        diff_canvas, rend = terminal_fit(diff_canvas, rend, width=total_width)
        rend.render(diff_canvas._bitmap, diff_canvas._colors, dest=output)
        output.write("\n")

    elif mode == "highlight":
        # Overlay diff heat onto original at 50% opacity
        diff = np.abs(canvas_a.bitmap - canvas_b.bitmap)
        blended = canvas_a.bitmap * 0.5 + diff * 0.5
        colors = None
        if canvas_a.colors is not None:
            # Tint changed regions red
            colors = canvas_a.colors.copy()
            mask = diff > 0.05  # threshold for "changed"
            colors[mask, 0] = np.minimum(1.0, colors[mask, 0] + diff[mask] * 0.5)
            colors[mask, 1] = colors[mask, 1] * 0.5
            colors[mask, 2] = colors[mask, 2] * 0.5
        highlight_canvas = Canvas(blended.astype(np.float32), colors=colors)
        highlight_canvas, rend = terminal_fit(highlight_canvas, rend, width=total_width)
        rend.render(highlight_canvas._bitmap, highlight_canvas._colors, dest=output)
        output.write("\n")


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="diffcat",
        description="Visual image diff in the terminal",
    )
    parser.add_argument("image_a", type=Path, help="First image (before)")
    parser.add_argument("image_b", type=Path, help="Second image (after)")
    parser.add_argument(
        "--mode", choices=["side", "overlay", "highlight"], default="side",
        help="Comparison mode (default: side)",
    )
    parser.add_argument(
        "-r", "--renderer", default="sextants",
        help="Renderer to use (default: sextants)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters (default: terminal width)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    for img in [args.image_a, args.image_b]:
        if not img.exists():
            print(f"Error: File not found: {img}", file=sys.stderr)
            sys.exit(1)

    dest = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        diffcat(
            args.image_a, args.image_b,
            mode=args.mode,
            renderer=args.renderer,
            width=args.width,
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
