"""pdfcat - Terminal PDF viewer built on dapple.

Renders PDF pages as images in the terminal using various
rendering methods (braille, quadrants, sixel, kitty, etc.).

Example:
    $ pdfcat document.pdf              # View with auto-detected renderer
    $ pdfcat -r braille document.pdf   # Force braille renderer
    $ pdfcat --pages 1-3 document.pdf  # View specific pages
As a library:
    >>> from dapple.extras.pdfcat import view, pdfcat
    >>> view("document.pdf")
    >>> pdfcat("document.pdf", pages="1-3", renderer="quadrants")
"""

from __future__ import annotations

__version__ = "0.1.0"

from dapple.extras.pdfcat.pdfcat import view, pdfcat, PdfcatOptions

__all__ = ["view", "pdfcat", "PdfcatOptions", "__version__"]
