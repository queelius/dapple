"""pdfcat - Terminal PDF viewer.

Core implementation for rendering PDF pages to the terminal using dapple.
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from dapple.renderers import Renderer

# pypdfium2 is optional
try:
    import pypdfium2 as pdfium
    HAS_PYPDFIUM2 = True
except ImportError:
    HAS_PYPDFIUM2 = False
    pdfium = None


@dataclass
class PdfcatOptions:
    """Options for PDF rendering.

    Attributes:
        renderer: Renderer name or instance ("auto", "braille", "quadrants", etc.)
        width: Output width in characters (None = terminal width)
        height: Output height in characters per page (None = auto)
        pages: Page range string ("1-3", "5", "1,3,5", etc.)
        dpi: DPI for PDF rendering (default: 150)
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output entirely
    """
    renderer: str = "auto"
    width: int | None = None
    height: int | None = None
    pages: str | None = None
    dpi: int = 150
    dither: bool = False
    contrast: bool = False
    invert: bool = False
    grayscale: bool = False
    no_color: bool = False


@dataclass
class RenderedPage:
    """A rendered page image."""
    number: int
    image_path: Path


@dataclass
class RenderResult:
    """Result of PDF rendering."""
    pages: list[RenderedPage] = field(default_factory=list)
    temp_dir: tempfile.TemporaryDirectory | None = None
    total_pages: int = 0

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None


def parse_page_range(page_str: str, total_pages: int) -> list[int]:
    """Parse a page range string into a list of page numbers.

    Args:
        page_str: Page range like "1-3", "5", "1,3,5", "1-3,7,9-11"
        total_pages: Total number of pages in document

    Returns:
        List of 1-indexed page numbers
    """
    pages: set[int] = set()
    for part in page_str.split(","):
        part = part.strip()
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str) if start_str else 1
            end = int(end_str) if end_str else total_pages
            pages.update(range(start, min(end, total_pages) + 1))
        else:
            page = int(part)
            if 1 <= page <= total_pages:
                pages.add(page)
    return sorted(pages)


def render_pdf_to_images(
    path: Path,
    dpi: int = 150,
    pages: str | None = None,
) -> RenderResult:
    """Render PDF pages to images using pypdfium2.

    Args:
        path: Path to PDF file.
        dpi: Resolution for rendering.
        pages: Optional page range string.

    Returns:
        RenderResult with rendered page images.
    """
    if not HAS_PYPDFIUM2:
        return RenderResult()

    try:
        pdf = pdfium.PdfDocument(path)
    except Exception as e:
        print(f"Error: {path.name}: Failed to open PDF: {e}", file=sys.stderr)
        return RenderResult()

    total_pages = len(pdf)

    if pages:
        page_nums = parse_page_range(pages, total_pages)
    else:
        page_nums = list(range(1, total_pages + 1))

    temp_dir = tempfile.TemporaryDirectory(prefix="pdfcat_")
    temp_path = Path(temp_dir.name)

    rendered: list[RenderedPage] = []

    for page_num in page_nums:
        page_idx = page_num - 1

        try:
            page = pdf[page_idx]
            scale = dpi / 72.0
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()

            img_path = temp_path / f"page_{page_num:04d}.png"
            pil_image.save(img_path, "PNG")

            rendered.append(RenderedPage(number=page_num, image_path=img_path))
        except Exception as e:
            print(
                f"Warning: {path.name}: Failed to render page {page_num}: {e}",
                file=sys.stderr,
            )
            continue

    pdf.close()

    return RenderResult(
        pages=rendered,
        temp_dir=temp_dir,
        total_pages=total_pages,
    )


def get_renderer(name: str, options: PdfcatOptions) -> Renderer:
    """Get a renderer by name with appropriate configuration."""
    from dapple.extras.common import get_renderer as _get_renderer

    return _get_renderer(name, grayscale=options.grayscale, no_color=options.no_color)


def pdfcat(
    pdf_path: str | Path,
    *,
    renderer: str = "auto",
    width: int | None = None,
    height: int | None = None,
    pages: str | None = None,
    dpi: int = 150,
    dither: bool = False,
    contrast: bool = False,
    invert: bool = False,
    grayscale: bool = False,
    no_color: bool = False,
    dest: TextIO | None = None,
) -> bool:
    """Render a PDF to the terminal.

    Args:
        pdf_path: Path to the PDF file.
        renderer: Renderer name ("auto", "braille", "quadrants", etc.)
        width: Output width in characters (None = terminal width)
        height: Output height in characters per page (None = auto)
        pages: Page range string ("1-3", "5", "1,3,5", etc.)
        dpi: DPI for PDF rendering (default: 150)
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output entirely
        dest: Output stream (default: stdout)

    Returns:
        True if rendering succeeded, False otherwise.
    """
    if not HAS_PYPDFIUM2:
        print(
            "pdfcat requires pypdfium2. Install with: pip install dapple[pdfcat]",
            file=sys.stderr,
        )
        return False

    try:
        from PIL import Image
        from dapple.adapters.pil import from_pil
    except ImportError:
        print(
            "pdfcat requires pillow. Install with: pip install dapple[pdfcat]",
            file=sys.stderr,
        )
        return False

    from dapple.canvas import Canvas
    from dapple.extras.common import apply_preprocessing

    path = Path(pdf_path)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return False

    options = PdfcatOptions(
        renderer=renderer,
        width=width,
        height=height,
        pages=pages,
        dpi=dpi,
        dither=dither,
        contrast=contrast,
        invert=invert,
        grayscale=grayscale,
        no_color=no_color,
    )

    rend = get_renderer(renderer, options)
    result = render_pdf_to_images(path, dpi=dpi, pages=pages)

    if not result.pages:
        print(f"Error: Failed to render PDF: {path}", file=sys.stderr)
        return False

    from dapple.layout import terminal_fit

    output = dest if dest is not None else sys.stdout

    # Print header
    output.write(f"# {path.name}: {result.total_pages} pages\n")

    try:
        for page in result.pages:
            if result.total_pages > 1:
                output.write(f"\n## Page {page.number}\n")

            # Load page image
            pil_img: Image.Image = Image.open(page.image_path)
            canvas = from_pil(pil_img)

            # Size for terminal
            canvas, rend = terminal_fit(canvas, rend, width=width)

            # Apply preprocessing
            if contrast or dither or invert:
                bitmap = apply_preprocessing(
                    canvas.bitmap.copy(), contrast=contrast, dither=dither, invert=invert
                )
                canvas = Canvas(bitmap, colors=canvas.colors)

            # Render
            colors_to_use = None if no_color else canvas._colors
            rend.render(canvas._bitmap, colors_to_use, dest=output)
            output.write("\n")

        return True

    finally:
        result.cleanup()


def view(pdf_path: str | Path, **kwargs) -> bool:
    """Quick view of a PDF with default settings.

    Alias for pdfcat() with default options.
    """
    return pdfcat(pdf_path, **kwargs)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="pdfcat",
        description="Display PDF pages in the terminal using dapple",
    )

    # Main command arguments
    parser.add_argument(
        "pdfs", type=Path, nargs="*", help="PDF file(s) to display"
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
        "-p", "--pages", type=str,
        help='Page range (e.g., "1-3", "5", "1,3,5")'
    )
    parser.add_argument(
        "--dpi", type=int, default=150,
        help="DPI for PDF rendering (default: 150)"
    )
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

    args = parser.parse_args()

    # Main command
    if not args.pdfs:
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
    first_pdf = True
    try:
        for pdf_path in args.pdfs:
            if not pdf_path.exists():
                errors.append(f"{pdf_path}: File not found")
                continue

            # Print separator for multiple PDFs
            if len(args.pdfs) > 1:
                if not first_pdf:
                    dest.write("\n")
                dest.write(f"{'='*60}\n")
                dest.write(f"  {pdf_path.name}\n")
                dest.write(f"{'='*60}\n\n")
                first_pdf = False

            try:
                success = pdfcat(
                    pdf_path,
                    renderer=args.renderer,
                    width=args.width,
                    height=args.height,
                    pages=args.pages,
                    dpi=args.dpi,
                    dither=args.dither,
                    contrast=args.contrast,
                    invert=args.invert,
                    grayscale=args.grayscale,
                    no_color=args.no_color,
                    dest=dest,
                )
                if not success:
                    errors.append(f"{pdf_path}: Failed to render")
            except Exception as e:
                errors.append(f"{pdf_path}: {e}")
                continue
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if args.output:
            dest.close()

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
