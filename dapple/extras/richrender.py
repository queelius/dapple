"""richrender - Shared Rich image rendering components for dapple extras.

Provides DappleImageItem, DappleMarkdown, ImageCache, and ImageResolver
for use by mdcat, htmlcat, and other Rich-based rendering tools.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.error
import urllib.request
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import ImageItem, Markdown
from rich.segment import Segment
from rich.text import Text

if TYPE_CHECKING:
    from dapple.renderers import Renderer


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


class DappleImageItem(ImageItem):
    """Renders images using dapple instead of placeholder."""

    _resolver: ImageResolver | None = None
    _renderer: Renderer | None = None
    _render_images: bool = True
    _image_width: int = 80
    _no_color: bool = False

    @classmethod
    def configure(
        cls,
        resolver: ImageResolver | None,
        renderer: Renderer | None,
        render_images: bool = True,
        image_width: int = 80,
        no_color: bool = False,
    ) -> None:
        cls._resolver = resolver
        cls._renderer = renderer
        cls._render_images = render_images
        cls._image_width = image_width
        cls._no_color = no_color

    @classmethod
    def reset(cls) -> None:
        cls._resolver = None
        cls._renderer = None
        cls._render_images = True
        cls._image_width = 80
        cls._no_color = False

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
            canvas = from_pil(pil_img)

            # Size for display width
            from dapple.layout import terminal_fit
            canvas, _ = terminal_fit(canvas, self._renderer, width=self._image_width)

            # Render to string (strip colors when no_color is active)
            buf = StringIO()
            colors = None if self._no_color else canvas._colors
            self._renderer.render(canvas._bitmap, colors, dest=buf)
            output = buf.getvalue()

            # Yield as text
            for line in output.split('\n'):
                if line:
                    yield Segment(line)
                    yield Segment('\n')

        except Exception as e:
            print(
                f"Warning: Failed to render image: {e}",
                file=sys.stderr,
            )
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
    no_color: bool = False,
):
    """Context manager for DappleImageItem configuration."""
    try:
        DappleImageItem.configure(
            resolver, renderer, render_images, image_width, no_color=no_color,
        )
        yield
    finally:
        DappleImageItem.reset()
