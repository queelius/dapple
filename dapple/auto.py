"""Auto-detection of terminal capabilities and renderer selection.

Detects the best renderer for the current terminal based on its graphics
capabilities (kitty, sixel, etc.) and falls back to character-based renderers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dapple.renderers import Renderer


class Protocol(Enum):
    """Terminal graphics protocols supported by dapple."""
    KITTY = "kitty"       # Kitty graphics protocol (PNG inline)
    SIXEL = "sixel"       # Sixel graphics (DEC standard)
    QUADRANTS = "quadrants"  # Unicode quadrant blocks (color)
    BRAILLE = "braille"   # Unicode braille patterns (monochrome/color)
    ASCII = "ascii"       # Pure ASCII (universal fallback)


@dataclass
class TerminalInfo:
    """Detected terminal capabilities."""
    protocol: Protocol
    terminal_name: str | None = None
    color_support: bool = True

    @property
    def is_pixel_renderer(self) -> bool:
        """Check if this is a true pixel renderer (kitty/sixel)."""
        return self.protocol in (Protocol.KITTY, Protocol.SIXEL)


def detect_kitty() -> bool:
    """Detect Kitty terminal or compatible (e.g., Ghostty)."""
    # KITTY_WINDOW_ID is set by Kitty
    if os.environ.get("KITTY_WINDOW_ID"):
        return True
    # Ghostty also supports Kitty protocol
    if os.environ.get("GHOSTTY_RESOURCES_DIR"):
        return True
    return False


def detect_sixel() -> bool:
    """Detect Sixel-capable terminals.

    Checks for common sixel-capable terminals via TERM/TERM_PROGRAM.
    """
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()

    # Known sixel-capable terminals
    sixel_terms = {"mlterm", "yaft", "foot", "contour", "wezterm", "mintty"}

    for sixel_term in sixel_terms:
        if sixel_term in term or sixel_term in term_program:
            return True

    # xterm with sixel support (xterm-direct, xterm-256color with -ti vt340)
    if "xterm" in term and os.environ.get("XTERM_VERSION"):
        return True

    return False


def detect_color_support() -> bool:
    """Detect if the terminal supports color output.

    Returns ``False`` for the standard no-colour cases — ``NO_COLOR`` in
    the environment (https://no-color.org/) and ``TERM=dumb`` (the POSIX
    convention used by CI runners, Emacs shell buffers, and many script
    harnesses) — and otherwise ``True`` when the environment contains any
    of the usual markers.
    """
    # Check for NO_COLOR convention: even NO_COLOR="" should disable colour.
    if "NO_COLOR" in os.environ:
        return False

    term = os.environ.get("TERM", "").lower()

    # POSIX "dumb" terminal - no control sequences, no colour.
    if term == "dumb":
        return False

    # Common colour-capable TERM values.
    if any(x in term for x in ("color", "256", "direct", "truecolor", "kitty", "xterm")):
        return True

    # COLORTERM is often set for true-colour support.
    if os.environ.get("COLORTERM"):
        return True

    # Default: assume no colour rather than silently emitting escape codes
    # into terminals that can't render them.
    return False


def detect_protocol() -> Protocol:
    """Detect the best available graphics protocol.

    Returns:
        Protocol enum value for the best available protocol.
    """
    # Check in order of capability
    if detect_kitty():
        return Protocol.KITTY
    if detect_sixel():
        return Protocol.SIXEL
    # Default to quadrants (good balance of resolution and compatibility)
    return Protocol.QUADRANTS


def detect_terminal() -> TerminalInfo:
    """Detect terminal capabilities.

    Returns:
        TerminalInfo with detected protocol and capabilities.
    """
    protocol = detect_protocol()
    color_support = detect_color_support()

    # Get terminal name for debugging
    terminal_name = os.environ.get("TERM_PROGRAM") or os.environ.get("TERM")

    return TerminalInfo(
        protocol=protocol,
        terminal_name=terminal_name,
        color_support=color_support,
    )


def auto_renderer(
    *,
    prefer_color: bool = True,
    plain: bool = False,
) -> Renderer:
    """Get the best renderer for the current terminal.

    Auto-detects terminal capabilities and returns the most suitable renderer:
    - Color terminals → sextants renderer (safe, high-resolution)
    - Monochrome/plain → braille or ascii

    Pixel protocols (kitty, sixel) are available but not auto-selected
    because they require specific terminal support and break in many
    contexts (tmux, screen, CI, piped output). Use them explicitly.

    Args:
        prefer_color: If True, prefer color-capable renderers (default: True).
        plain: If True, force ASCII output for pipes/redirects (default: False).

    Returns:
        Renderer instance configured for the terminal.

    Example:
        >>> from dapple import from_pil, auto_renderer
        >>> canvas = from_pil(image)
        >>> canvas.out(auto_renderer())
    """
    from dapple.renderers import ascii, braille, sextants

    # Plain mode - use ASCII for maximum compatibility
    if plain:
        return ascii

    # Check if we're outputting to a pipe/file
    import sys
    if not sys.stdout.isatty():
        # Output is being piped - use safe fallback
        return braille if prefer_color else ascii

    # Sextants: safe, high-resolution, works in every terminal
    info = detect_terminal()
    if prefer_color and info.color_support:
        return sextants
    return braille


# Convenience function for common use case
def render_image(
    image_path: str,
    *,
    width: int | None = None,
    height: int | None = None,
    renderer: Renderer | None = None,
) -> None:
    """Render an image file to the terminal.

    Convenience function that handles loading, resizing, and rendering.

    Args:
        image_path: Path to the image file.
        width: Target width in pixels (auto-calculated if None).
        height: Target height in pixels (optional).
        renderer: Renderer to use (auto-detected if None).

    Raises:
        ImportError: If PIL is not installed.
        FileNotFoundError: If image file doesn't exist.

    Example:
        >>> from dapple.auto import render_image
        >>> render_image("photo.jpg")  # Auto-detects terminal and renders
    """
    try:
        from dapple.adapters.pil import load_image
    except ImportError:
        raise ImportError(
            "PIL is required for render_image(). "
            "Install with: pip install dapple[imgcat]"
        )

    # Load and resize image
    canvas = load_image(image_path, width=width, height=height)

    # Use auto-detected renderer if not specified
    if renderer is None:
        renderer = auto_renderer()

    # Render to stdout
    canvas.out(renderer)


__all__ = [
    "Protocol",
    "TerminalInfo",
    "detect_terminal",
    "detect_protocol",
    "auto_renderer",
    "render_image",
]
