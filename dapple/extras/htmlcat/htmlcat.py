"""htmlcat - Terminal HTML viewer via markdownify + Rich.

Core implementation for rendering HTML to the terminal. Converts HTML
to markdown via markdownify, then renders via Rich with dapple for
inline image rendering.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from dapple.extras.richrender import (
    DappleMarkdown,
    ImageCache,
    ImageResolver,
    dapple_rendering,
)

if TYPE_CHECKING:
    from dapple.renderers import Renderer


@dataclass
class HtmlcatOptions:
    """Options for HTML rendering.

    Attributes:
        renderer: Renderer name for images ("auto", "braille", "quadrants", etc.)
        width: Console width in characters (None = terminal width)
        image_width: Image width in characters (None = same as console)
        render_images: Whether to render inline images
        code_theme: Pygments theme for code blocks
        hyperlinks: Enable clickable hyperlinks
    """

    renderer: str = "auto"
    width: int | None = None
    image_width: int | None = None
    render_images: bool = True
    code_theme: str = "monokai"
    hyperlinks: bool = True


def _get_renderer(name: str) -> Renderer:
    """Get a renderer by name."""
    from dapple.extras.common import get_renderer

    return get_renderer(name)


def html_to_markdown(html: str) -> str:
    """Convert HTML to markdown, stripping script/style tags.

    Args:
        html: HTML string to convert.

    Returns:
        Markdown string.
    """
    from markdownify import markdownify as md

    # Strip <script> and <style> tags before conversion
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    return md(cleaned, heading_style="ATX", strip=["nav", "footer", "header"])


def htmlcat_render(
    html: str,
    *,
    renderer: str = "auto",
    width: int | None = None,
    image_width: int | None = None,
    render_images: bool = True,
    code_theme: str = "monokai",
    hyperlinks: bool = True,
    raw: bool = False,
    dest: TextIO | None = None,
) -> None:
    """Render an HTML string to the terminal.

    Converts HTML to markdown via markdownify, then renders through
    Rich with DappleMarkdown for inline image support.

    Args:
        html: HTML string to render.
        renderer: Renderer name for images ("auto", "braille", "quadrants", etc.)
        width: Console width in characters (None = terminal width)
        image_width: Image width in characters (None = same as console)
        render_images: Whether to render inline images
        code_theme: Pygments theme for code blocks
        hyperlinks: Enable clickable hyperlinks
        raw: If True, output the intermediate markdown instead of rendering
        dest: Output stream (default: stdout)
    """
    from rich.console import Console

    # Convert HTML to markdown
    markdown_text = html_to_markdown(html)

    output = dest if dest is not None else sys.stdout

    # Raw mode: dump the converted markdown
    if raw:
        output.write(markdown_text)
        if markdown_text and not markdown_text.endswith("\n"):
            output.write("\n")
        return

    # Setup renderer
    rend = _get_renderer(renderer) if render_images else None

    # Setup console
    term_width = shutil.get_terminal_size().columns
    console_width = width or term_width
    img_width = image_width or min(console_width, 80)

    # Create console
    console = Console(
        width=console_width,
        file=output,
        force_terminal=dest is None,
    )

    # Setup image resolver (no base_path since we're rendering a string)
    cache = ImageCache()
    resolver = ImageResolver(cache=cache)

    # Render
    with dapple_rendering(resolver, rend, render_images, img_width):
        md = DappleMarkdown(
            markdown_text,
            code_theme=code_theme,
            hyperlinks=hyperlinks,
        )
        console.print(md)


def htmlcat(
    source: str | Path,
    *,
    renderer: str = "auto",
    width: int | None = None,
    image_width: int | None = None,
    render_images: bool = True,
    code_theme: str = "monokai",
    hyperlinks: bool = True,
    raw: bool = False,
    dest: TextIO | None = None,
) -> None:
    """Render an HTML file to the terminal.

    Args:
        source: Path to the HTML file.
        renderer: Renderer name for images ("auto", "braille", "quadrants", etc.)
        width: Console width in characters (None = terminal width)
        image_width: Image width in characters (None = same as console)
        render_images: Whether to render inline images
        code_theme: Pygments theme for code blocks
        hyperlinks: Enable clickable hyperlinks
        raw: If True, output the intermediate markdown instead of rendering
        dest: Output stream (default: stdout)
    """
    from rich.console import Console

    path = Path(source)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return

    html_content = path.read_text()

    # Convert HTML to markdown
    markdown_text = html_to_markdown(html_content)

    output = dest if dest is not None else sys.stdout

    # Raw mode: dump the converted markdown
    if raw:
        output.write(markdown_text)
        if markdown_text and not markdown_text.endswith("\n"):
            output.write("\n")
        return

    # Setup renderer
    rend = _get_renderer(renderer) if render_images else None

    # Setup console
    term_width = shutil.get_terminal_size().columns
    console_width = width or term_width
    img_width = image_width or min(console_width, 80)

    # Create console
    console = Console(
        width=console_width,
        file=output,
        force_terminal=dest is None,
    )

    # Setup image resolver with base_path for resolving relative image refs
    cache = ImageCache()
    resolver = ImageResolver(cache=cache, base_path=path)

    # Render
    with dapple_rendering(resolver, rend, render_images, img_width):
        md = DappleMarkdown(
            markdown_text,
            code_theme=code_theme,
            hyperlinks=hyperlinks,
        )
        console.print(md)


def view(source: str | Path, **kwargs) -> None:
    """Quick view of an HTML file with default settings."""
    htmlcat(source, **kwargs)
