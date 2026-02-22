"""Shared utilities for dapple extras.

Common renderer selection and preprocessing logic used across
imgcat, pdfcat, mdcat, and other extras.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

import numpy as np

if TYPE_CHECKING:
    from typing import TextIO

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

    The ``NO_COLOR`` environment variable (https://no-color.org/) is
    honoured automatically: when set (even to an empty string), colour
    output is suppressed for text-art renderers.
    """
    # Honour the NO_COLOR convention (https://no-color.org/)
    if "NO_COLOR" in os.environ:
        no_color = True

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

    if name == "fingerprint":
        if no_color:
            return fingerprint  # plain glyphs; callers also strip colors array
        if grayscale:
            return fingerprint(grayscale=True)
        return fingerprint

    # ascii is inherently colorless;
    # sixel, kitty are pixel protocols where no_color doesn't apply
    return renderer  # type: ignore[return-value]


def add_color_args(parser: argparse.ArgumentParser) -> None:
    """Add ``--grayscale`` and ``--no-color`` flags to an argparse parser.

    This is the single source of truth for colour-control CLI flags.
    Every dapple extra should call this instead of adding the flags
    manually, ensuring uniform naming and help text.
    """
    parser.add_argument(
        "--grayscale",
        action="store_true",
        help="Force grayscale output",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output",
    )


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


@contextmanager
def paged_output(dest: TextIO, pager: bool = False) -> Iterator[TextIO]:
    """Wrap output in a pager (less -R) if requested.

    Args:
        dest: The output stream.
        pager: Whether to pipe through a pager.

    Yields:
        The output stream (pager stdin or original dest).
    """
    if not pager or dest is not sys.stdout:
        yield dest
        return

    proc = subprocess.Popen(
        [os.environ.get("PAGER", "less"), "-R"],
        stdin=subprocess.PIPE,
        text=True,
    )
    try:
        yield proc.stdin  # type: ignore[misc]
    finally:
        proc.stdin.close()  # type: ignore[union-attr]
        proc.wait()


@contextmanager
def stdin_to_tempfile(suffix: str = ".bin") -> Iterator[Path]:
    """Read binary stdin to a temp file, yield its path.

    Args:
        suffix: File extension for the temp file.

    Yields:
        Path to the temporary file containing stdin data.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(sys.stdin.buffer.read())
        f.flush()
        path = Path(f.name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
