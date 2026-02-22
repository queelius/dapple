"""imgcat - Terminal image viewer.

Core implementation for rendering images to the terminal using dapple.
Supports single-image display and multi-image grid/contact-sheet mode.
"""

from __future__ import annotations

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


def _imgcat_single(
    image_path: Path,
    *,
    options: ImgcatOptions,
    rend: Renderer,
    dest: TextIO,
) -> None:
    """Render a single image to the terminal (internal helper)."""
    from dapple.adapters.pil import load_image
    from dapple.canvas import Canvas
    from dapple.extras.common import apply_preprocessing
    from dapple.layout import terminal_fit

    canvas = load_image(image_path)

    # Size for terminal
    canvas, rend = terminal_fit(canvas, rend, width=options.width)

    # Apply preprocessing
    if options.contrast or options.dither or options.invert:
        bitmap = apply_preprocessing(
            canvas.bitmap.copy(),
            contrast=options.contrast,
            dither=options.dither,
            invert=options.invert,
        )
        canvas = Canvas(bitmap, colors=canvas.colors)

    # Output
    colors_to_use = None if options.no_color else canvas._colors
    rend.render(canvas._bitmap, colors_to_use, dest=dest)
    dest.write("\n")


def _imgcat_grid(
    image_paths: list[Path],
    *,
    options: ImgcatOptions,
    rend: Renderer,
    grid_cols: int = 4,
    titles: bool = True,
    dest: TextIO,
) -> None:
    """Render multiple images as a contact-sheet grid (internal helper)."""
    from dapple.adapters.pil import load_image
    from dapple.layout import Frame, Grid, terminal_columns

    total_width = options.width or terminal_columns()

    # Load all images into frames
    frames: list[Frame] = []
    for path in image_paths:
        if not path.exists():
            print(f"Warning: {path}: File not found", file=sys.stderr)
            continue
        try:
            canvas = load_image(path)
            # Apply preprocessing (contrast, dither, invert)
            if options.contrast or options.dither or options.invert:
                from dapple.canvas import Canvas
                from dapple.extras.common import apply_preprocessing

                bitmap = apply_preprocessing(
                    canvas.bitmap.copy(),
                    contrast=options.contrast,
                    dither=options.dither,
                    invert=options.invert,
                )
                canvas = Canvas(bitmap, colors=canvas.colors)
            title = path.name if titles else None
            frames.append(Frame(canvas=canvas, title=title))
        except Exception as e:
            print(f"Warning: {path}: {e}", file=sys.stderr)
            continue

    if not frames:
        print("Error: No images to display", file=sys.stderr)
        return

    # Arrange into rows
    rows: list[list[Frame]] = []
    for i in range(0, len(frames), grid_cols):
        rows.append(frames[i:i + grid_cols])

    grid = Grid(rows, width=total_width)
    grid.render(rend, dest=dest)


def imgcat(
    image_path: str | Path | list[str | Path],
    *,
    renderer: str = "auto",
    width: int | None = None,
    height: int | None = None,
    dither: bool = False,
    contrast: bool = False,
    invert: bool = False,
    grayscale: bool = False,
    no_color: bool = False,
    grid_cols: int = 4,
    titles: bool = True,
    dest: TextIO | None = None,
) -> None:
    """Render an image (or images) to the terminal.

    When *image_path* is a single path, renders that image at full size.
    When it is a list with more than one path, renders a contact-sheet grid.
    A single-element list renders the image directly (no grid).

    Args:
        image_path: Path to image file, or list of paths for grid mode.
        renderer: Renderer name ("auto", "braille", "quadrants", etc.)
        width: Output width in characters (None = terminal width)
        height: Output height in characters (None = auto)
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output entirely
        grid_cols: Number of columns in grid mode (default: 4).
        titles: Show filenames as titles in grid mode (default: True).
        dest: Output stream (default: stdout)

    Example:
        >>> imgcat("photo.jpg")  # Auto-detect and render
        >>> imgcat("photo.jpg", renderer="braille", dither=True)
        >>> imgcat(["a.png", "b.png", "c.png"], grid_cols=2)  # grid
    """
    try:
        from dapple.adapters.pil import load_image  # noqa: F401
    except ImportError:
        raise ImportError(
            "PIL is required for imgcat. Install with: pip install dapple[imgcat]"
        )

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

    from dapple.extras.common import get_renderer

    rend = get_renderer(renderer, grayscale=grayscale, no_color=no_color)
    output = dest or sys.stdout

    # Normalise to list
    if isinstance(image_path, (str, Path)):
        paths = [Path(image_path)]
    else:
        paths = [Path(p) for p in image_path]

    # Single image -> direct render; multiple -> grid
    if len(paths) == 1:
        _imgcat_single(paths[0], options=options, rend=rend, dest=output)
    else:
        _imgcat_grid(
            paths,
            options=options,
            rend=rend,
            grid_cols=grid_cols,
            titles=titles,
            dest=output,
        )


def view(image_path: str | Path | list[str | Path], **kwargs) -> None:
    """Quick view of an image (or images) with default settings.

    Alias for imgcat() with default options.

    Args:
        image_path: Path to image file, or list of paths for grid mode.
        **kwargs: Additional options passed to imgcat().

    Example:
        >>> view("photo.jpg")
        >>> view(["a.png", "b.png"], grid_cols=2)
    """
    imgcat(image_path, **kwargs)


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

    from dapple.extras.common import add_color_args
    add_color_args(parser)

    parser.add_argument(
        "--pager", action="store_true",
        help="Pipe output through a pager (less -R)"
    )

    # Grid / contact-sheet flags
    parser.add_argument(
        "--cols", type=int, default=4,
        help="Number of grid columns when displaying multiple images (default: 4)"
    )
    parser.add_argument(
        "--no-titles", action="store_true",
        help="Hide filenames in grid mode"
    )

    args = parser.parse_args()

    # Handle stdin ("-" argument)
    from dapple.extras.common import paged_output, stdin_to_tempfile

    images = list(args.images) if args.images else []
    stdin_ctx = None
    if images and str(images[0]) == "-":
        stdin_ctx = stdin_to_tempfile(suffix=".png")
        stdin_path = stdin_ctx.__enter__()
        images[0] = stdin_path

    if not images:
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
        with paged_output(dest, pager=args.pager) as output:
            # Multiple images -> grid mode (imgcat handles the grid internally)
            if len(images) > 1:
                try:
                    imgcat(
                        images,
                        renderer=args.renderer,
                        width=args.width,
                        height=args.height,
                        dither=args.dither,
                        contrast=args.contrast,
                        invert=args.invert,
                        grayscale=args.grayscale,
                        no_color=args.no_color,
                        grid_cols=args.cols,
                        titles=not args.no_titles,
                        dest=output,
                    )
                except ImportError as e:
                    errors.append(f"Missing dependency: {e}")
                except Exception as e:
                    errors.append(f"{e}")
            else:
                # Single image
                image_path = Path(images[0])
                if not image_path.exists():
                    errors.append(f"{image_path}: File not found")
                else:
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
                            dest=output,
                        )
                    except ImportError as e:
                        errors.append(f"{image_path.name}: Missing dependency: {e}")
                    except Exception as e:
                        errors.append(f"{image_path}: {e}")
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if args.output:
            dest.close()
        if stdin_ctx:
            stdin_ctx.__exit__(None, None, None)

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        exit_code = 1  # Any errors means exit 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
