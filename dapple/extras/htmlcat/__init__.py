"""htmlcat - Terminal HTML viewer via markdownify + Rich.

Converts HTML to markdown and renders it to the terminal using Rich
for text formatting and dapple for inline images.

Example:
    $ htmlcat page.html              # View HTML file
    $ htmlcat -r braille page.html   # Force braille for images
    $ htmlcat --no-images page.html  # Skip image rendering
    $ htmlcat --raw page.html        # Show intermediate markdown
As a library:
    >>> from dapple.extras.htmlcat import htmlcat, htmlcat_render
    >>> htmlcat("page.html")
    >>> htmlcat_render("<h1>Hello</h1>", dest=sys.stdout)
"""

from __future__ import annotations

__version__ = "0.1.0"

from dapple.extras.htmlcat.htmlcat import htmlcat, htmlcat_render, HtmlcatOptions

__all__ = ["htmlcat", "htmlcat_render", "HtmlcatOptions", "__version__"]
