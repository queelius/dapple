"""mdcat - Terminal markdown viewer with inline images.

Renders markdown files to the terminal using Rich for text formatting
and dapple for inline images.

Example:
    $ mdcat README.md              # View markdown file
    $ mdcat -r braille README.md   # Force braille for images
    $ mdcat --no-images README.md  # Skip image rendering
As a library:
    >>> from dapple.extras.mdcat import view, mdcat
    >>> view("README.md")
    >>> mdcat("README.md", renderer="quadrants", theme="nord")
"""

from __future__ import annotations

__version__ = "0.1.0"

from dapple.extras.mdcat.mdcat import view, mdcat, MdcatOptions

__all__ = ["view", "mdcat", "MdcatOptions", "__version__"]
