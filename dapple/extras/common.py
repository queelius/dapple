"""Shared utilities for dapple extras.

Common renderer selection and preprocessing logic used across
imgcat, pdfcat, mdcat, and other extras.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from dapple.renderers import Renderer


def get_renderer(
    name: str,
    *,
    grayscale: bool = False,
    no_color: bool = False,
) -> Renderer:
    """Get a renderer by name with appropriate color configuration.

    Args:
        name: Renderer name ("auto", "braille", "quadrants", "sextants",
              "ascii", "sixel", "kitty", "fingerprint").
        grayscale: Force grayscale output.
        no_color: Disable color output entirely.

    Returns:
        Configured Renderer instance.

    Raises:
        ValueError: If name is not a recognized renderer.
    """
    from dapple import (
        ascii,
        braille,
        fingerprint,
        kitty,
        quadrants,
        sextants,
        sixel,
    )
    from dapple.auto import auto_renderer

    if name == "auto":
        return auto_renderer(
            prefer_color=not grayscale,
            plain=no_color,
        )

    renderers = {
        "braille": braille,
        "quadrants": quadrants,
        "sextants": sextants,
        "ascii": ascii,
        "sixel": sixel,
        "kitty": kitty,
        "fingerprint": fingerprint,
    }

    renderer = renderers.get(name)
    if renderer is None:
        raise ValueError(f"Unknown renderer: {name}")

    # Apply color configuration based on renderer type
    if name == "braille":
        if no_color:
            return braille(color_mode="none")
        if grayscale:
            return braille(color_mode="grayscale")
        return braille(color_mode="truecolor")

    if name in ("quadrants", "sextants"):
        # no_color or grayscale both map to grayscale mode (closest
        # approximation — these renderers always use ANSI codes)
        if no_color or grayscale:
            if name == "quadrants":
                return quadrants(grayscale=True)
            return sextants(grayscale=True)

    # ascii, fingerprint are inherently colorless;
    # sixel, kitty are pixel protocols where no_color doesn't apply
    return renderer  # type: ignore[return-value]


def apply_preprocessing(
    bitmap: NDArray[np.floating],
    *,
    contrast: bool = False,
    dither: bool = False,
    invert: bool = False,
) -> NDArray[np.floating]:
    """Apply preprocessing chain to a bitmap.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0.
        contrast: Apply auto-contrast stretching.
        dither: Apply Floyd-Steinberg dithering.
        invert: Invert brightness values.

    Returns:
        Modified bitmap (new array if any transforms applied, otherwise input).
    """
    from dapple.preprocess import (
        auto_contrast,
        floyd_steinberg,
        invert as invert_fn,
    )

    if contrast:
        bitmap = auto_contrast(bitmap)
    if dither:
        bitmap = floyd_steinberg(bitmap)
    if invert:
        bitmap = invert_fn(bitmap)

    return bitmap


def unescape_delimiter(s: str) -> str:
    """Unescape common escape sequences in a delimiter string.

    Handles \\t (tab), \\n (newline), \\\\ (backslash).
    Single characters and already-unescaped values pass through unchanged.
    """
    replacements = {"\\t": "\t", "\\n": "\n", "\\\\": "\\"}
    for escaped, unescaped in replacements.items():
        s = s.replace(escaped, unescaped)
    return s


def available_fields(records: list) -> list[str]:
    """Collect all unique top-level keys from a list of dicts.

    Returns sorted list of field names. Returns empty list if records
    are empty or not dicts.
    """
    keys: set[str] = set()
    for rec in records:
        if isinstance(rec, dict):
            keys.update(rec.keys())
    return sorted(keys)
