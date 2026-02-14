"""mdcat - Terminal markdown viewer with inline images.

Core implementation for rendering markdown to the terminal using Rich
with dapple for inline image rendering.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import ImageItem, Markdown
from rich.segment import Segment
from rich.text import Text

if TYPE_CHECKING:
    from dapple.renderers import Renderer


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


class ImageCache:
    """SHA256-hashed cache for downloaded images."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "mdcat"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_url(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def _get_extension(self, url: str) -> str:
        path = url.split("?")[0]
        ext = Path(path).suffix.lower()
        return ext if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp"} else ".png"

    def get_cached_path(self, url: str) -> Path | None:
        hash_name = self._hash_url(url)
        ext = self._get_extension(url)
        cached = self.cache_dir / f"{hash_name}{ext}"
        return cached if cached.exists() else None

    def cache_file(self, url: str, data: bytes) -> Path:
        hash_name = self._hash_url(url)
        ext = self._get_extension(url)
        cached = self.cache_dir / f"{hash_name}{ext}"
        cached.write_bytes(data)
        return cached


class ImageResolver:
    """Resolves image paths/URLs to local files."""

    def __init__(self, cache: ImageCache | None = None, base_path: Path | None = None):
        self.cache = cache or ImageCache()
        self.base_path = base_path

    def resolve(self, path: str) -> Path | None:
        if path.startswith(("http://", "https://")):
            return self._resolve_url(path)
        if path.startswith("file://"):
            local_path = path[7:]
            return self._resolve_local(local_path)
        return self._resolve_local(path)

    def _resolve_url(self, url: str) -> Path | None:
        cached = self.cache.get_cached_path(url)
        if cached:
            return cached

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            return self.cache.cache_file(url, data)
        except Exception:
            return None

    def _resolve_local(self, path: str) -> Path | None:
        p = Path(path)

        if p.is_absolute():
            return p if p.exists() else None

        if self.base_path:
            resolved = (self.base_path.parent / p).resolve()
            if resolved.exists():
                return resolved

        resolved = p.resolve()
        return resolved if resolved.exists() else None


def get_renderer(name: str, options: MdcatOptions) -> Renderer:
    """Get a renderer by name."""
    from dapple.extras.common import get_renderer as _get_renderer

    return _get_renderer(name)


class DappleImageItem(ImageItem):
    """Renders images using dapple instead of placeholder."""

    _resolver: ImageResolver | None = None
    _renderer: Renderer | None = None
    _render_images: bool = True
    _image_width: int = 80

    @classmethod
    def configure(
        cls,
        resolver: ImageResolver | None,
        renderer: Renderer | None,
        render_images: bool = True,
        image_width: int = 80,
    ) -> None:
        cls._resolver = resolver
        cls._renderer = renderer
        cls._render_images = render_images
        cls._image_width = image_width

    @classmethod
    def reset(cls) -> None:
        cls._resolver = None
        cls._renderer = None
        cls._render_images = True
        cls._image_width = 80

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if not self._render_images:
            yield self._placeholder()
            return

        if not self._resolver or not self._renderer:
            yield self._placeholder()
            return

        local_path = self._resolver.resolve(self.destination)
        if not local_path:
            yield self._placeholder(reason="could not resolve")
            return

        # Load and render image with dapple
        try:
            from PIL import Image
            from dapple.adapters.pil import from_pil
        except ImportError:
            yield self._placeholder(reason="PIL not available")
            return

        try:
            pil_img: Image.Image = Image.open(local_path)

            # Resize to fit width
            pixel_width = self._image_width * self._renderer.cell_width
            w, h = pil_img.size
            aspect = h / w
            new_w = pixel_width
            new_h = int(new_w * aspect)

            # Aspect ratio correction for terminal cells
            TERMINAL_CELL_RATIO = 0.5
            cell_aspect = (self._renderer.cell_height / self._renderer.cell_width) * TERMINAL_CELL_RATIO
            new_h = int(new_h * cell_aspect)

            if new_h > 0:
                pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            canvas = from_pil(pil_img)

            # Render to string
            buf = StringIO()
            self._renderer.render(canvas._bitmap, canvas._colors, dest=buf)
            output = buf.getvalue()

            # Yield as text
            for line in output.split('\n'):
                if line:
                    yield Segment(line)
                    yield Segment('\n')

        except Exception as e:
            yield self._placeholder(reason=str(e))

    def _placeholder(self, reason: str | None = None) -> Text:
        alt = self.text.plain if self.text else "image"
        if not alt:
            alt = "image"

        if reason:
            return Text(f"[{alt}] ({reason})", style="dim")
        return Text(f"[{alt}]", style="dim")


class DappleMarkdown(Markdown):
    """Markdown with dapple image support."""

    elements = Markdown.elements.copy()
    elements["image"] = DappleImageItem


@contextmanager
def dapple_rendering(
    resolver: ImageResolver | None,
    renderer: Renderer | None,
    render_images: bool = True,
    image_width: int = 80,
):
    """Context manager for DappleImageItem configuration."""
    try:
        DappleImageItem.configure(resolver, renderer, render_images, image_width)
        yield
    finally:
        DappleImageItem.reset()


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
    path = Path(md_path)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return

    content = path.read_text()

    options = MdcatOptions(
        renderer=renderer,
        width=width,
        image_width=image_width,
        render_images=render_images,
        theme=theme,
        code_theme=code_theme,
        hyperlinks=hyperlinks,
    )

    # Setup renderer
    rend = get_renderer(renderer, options) if render_images else None

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
    )

    # Setup image resolver
    cache = ImageCache()
    resolver = ImageResolver(cache=cache, base_path=path)

    # Render
    with dapple_rendering(resolver, rend, render_images, img_width):
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
