"""Shared ANSI colour helpers used by multiple renderers.

Centralises the grayscale/RGB escape-code generators and the visual-width
helper so every renderer uses the same clamped, tested implementation.

The previous design duplicated nearly-identical helpers in
``quadrants.py``, ``sextants.py``, and ``fingerprint.py`` with subtle
divergence (e.g. fingerprint hard-coded ``23`` without clamping, so
brightness values slightly above ``1.0`` could emit ANSI code ``256``
which is invalid). Having one source of truth avoids that drift.
"""

from __future__ import annotations

import re

# Reset
RESET = "\033[0m"

# 256-color palette layout
_GRAY_LEVELS = 23  # 24 grayscale steps: 232..255
_GRAY_BASE = 232
_RGB_LEVELS = 5  # 6×6×6 color cube: levels 0..5
_RGB_BASE = 16

# Regex matching the SGR escape sequences we emit.
# Kept narrow (colour + reset) since those are all the renderers produce.
_ANSI_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")


def _clamp_unit(v: float) -> float:
    """Clamp a float into ``[0.0, 1.0]``."""
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def gray_code(brightness: float, fg: bool, true_color: bool = False) -> str:
    """Generate an ANSI escape for a grayscale colour.

    Args:
        brightness: Value in ``[0.0, 1.0]``. Clamped to that range.
        fg: ``True`` for foreground, ``False`` for background.
        true_color: Emit 24-bit RGB instead of the 256-colour grayscale ramp.

    Returns:
        ANSI escape sequence setting the requested colour.
    """
    brightness = _clamp_unit(brightness)
    prefix = 38 if fg else 48
    if true_color:
        v = int(brightness * 255)
        return f"\033[{prefix};2;{v};{v};{v}m"
    # int(brightness * 23) maxes out at 23 when brightness is exactly 1.0;
    # after clamping above there is no way to overshoot the palette.
    level = int(brightness * _GRAY_LEVELS)
    if level > _GRAY_LEVELS:
        level = _GRAY_LEVELS
    return f"\033[{prefix};5;{_GRAY_BASE + level}m"


def color_code(
    r: float,
    g: float,
    b: float,
    fg: bool,
    true_color: bool = False,
) -> str:
    """Generate an ANSI escape for an RGB colour.

    Args:
        r, g, b: Channels in ``[0.0, 1.0]``. Each is clamped.
        fg: ``True`` for foreground, ``False`` for background.
        true_color: Emit 24-bit RGB instead of the 6×6×6 palette.

    Returns:
        ANSI escape sequence setting the requested colour.
    """
    r = _clamp_unit(r)
    g = _clamp_unit(g)
    b = _clamp_unit(b)
    prefix = 38 if fg else 48
    if true_color:
        ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
        return f"\033[{prefix};2;{ri};{gi};{bi}m"
    ri = int(r * _RGB_LEVELS)
    gi = int(g * _RGB_LEVELS)
    bi = int(b * _RGB_LEVELS)
    # Guard against rounding edge cases even though clamp above keeps us safe.
    if ri > _RGB_LEVELS:
        ri = _RGB_LEVELS
    if gi > _RGB_LEVELS:
        gi = _RGB_LEVELS
    if bi > _RGB_LEVELS:
        bi = _RGB_LEVELS
    return f"\033[{prefix};5;{_RGB_BASE + 36 * ri + 6 * gi + bi}m"


def strip_ansi(text: str) -> str:
    """Return *text* with all SGR escape sequences removed.

    Used when measuring visual width of rendered output — ``len()`` on a
    coloured string counts the invisible escape bytes and gives wrong
    answers for anything that frames the output (``Frame``, ``Grid``).
    """
    return _ANSI_SGR_RE.sub("", text)


def visual_width(text: str) -> int:
    """Approximate visual width of *text* in terminal cells.

    Strips ANSI colour codes before measuring. This does **not** handle
    East Asian wide characters or combining marks — callers that need
    that precision should depend on ``wcwidth``.
    """
    return len(strip_ansi(text))
