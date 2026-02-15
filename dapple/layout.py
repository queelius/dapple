"""Layout engine for composing canvases in the terminal.

Provides terminal sizing helpers, Frame/Grid primitives for layout,
and Canvas.fit() support for resizing to terminal dimensions.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from io import StringIO
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from typing import TextIO

    from numpy.typing import NDArray

    from dapple.canvas import Canvas
    from dapple.renderers import Renderer


def terminal_columns(fallback: int = 80) -> int:
    """Terminal width in characters."""
    return shutil.get_terminal_size(fallback=(fallback, 24)).columns


def terminal_fit(
    canvas: Canvas,
    renderer: Renderer,
    *,
    width: int | None = None,
    cell_ratio: float = 0.5,
) -> tuple[Canvas, Renderer]:
    """One-stop sizing: returns (canvas, renderer) ready for output.

    Character renderers: resizes canvas via canvas.fit().
    Kitty: returns original canvas + kitty(columns=width).
    Sixel: resizes canvas with standardized pixel width.

    Args:
        canvas: The canvas to size.
        renderer: The renderer to use.
        width: Target width in characters (None = terminal width).
        cell_ratio: Terminal cell aspect ratio (default 0.5).

    Returns:
        (sized_canvas, configured_renderer) tuple.
    """
    w = width or terminal_columns()

    # Kitty: configure renderer columns, don't resize image
    if hasattr(renderer, 'columns'):
        return canvas, renderer(columns=w)

    # Sixel: resize to pixel width (standardize on 10px per cell)
    if renderer.cell_width == 1 and renderer.cell_height == 1:
        SIXEL_CELL_PX = 10
        pixel_w = w * SIXEL_CELL_PX
        h, orig_w = canvas.shape
        if orig_w > 0:
            aspect = h / orig_w
            pixel_h = max(1, int(pixel_w * aspect))
            from dapple.preprocess import resize
            new_bitmap = resize(canvas.bitmap, pixel_h, pixel_w)
            new_colors = None
            if canvas.colors is not None:
                new_colors = resize(canvas.colors, pixel_h, pixel_w)
            from dapple.canvas import Canvas as CanvasCls
            return CanvasCls(new_bitmap, colors=new_colors), renderer
        return canvas, renderer

    # Character renderers: use Canvas.fit()
    return canvas.fit(renderer, width=w, cell_ratio=cell_ratio), renderer


def _fit_canvas(
    canvas: Canvas,
    renderer: Renderer,
    *,
    width: int | None = None,
    height: int | None = None,
    cell_ratio: float = 0.5,
) -> Canvas:
    """Resize canvas to fit character dimensions.

    For character renderers (braille, sextants, etc.): resizes bitmap
    to pixel dimensions and applies aspect-ratio correction.
    For pixel renderers (sixel, kitty): returns self unchanged.

    Args:
        canvas: The canvas to resize.
        renderer: The renderer determining cell dimensions.
        width: Target width in characters (None = terminal width).
        height: Target height in characters (None = auto from aspect).
        cell_ratio: Terminal cell aspect ratio (default 0.5).

    Returns:
        New Canvas resized to fit the renderer.
    """
    # Pixel renderers (sixel, kitty): return unchanged
    if renderer.cell_width == 1 and renderer.cell_height == 1:
        return canvas

    char_w = width or terminal_columns()
    pixel_w = char_w * renderer.cell_width

    # Calculate pixel height preserving aspect ratio
    orig_h, orig_w = canvas.shape
    if orig_w == 0:
        return canvas

    aspect = orig_h / orig_w
    pixel_h = int(pixel_w * aspect)

    # Apply terminal cell aspect correction
    cell_aspect = (renderer.cell_height / renderer.cell_width) * cell_ratio
    pixel_h = max(1, int(pixel_h * cell_aspect))

    # If explicit height requested, use it
    if height is not None:
        pixel_h = height * renderer.cell_height

    # Resize bitmap and colors
    from dapple.preprocess import resize
    new_bitmap = resize(canvas.bitmap, pixel_h, pixel_w)
    new_colors = None
    if canvas.colors is not None:
        new_colors = resize(canvas.colors, pixel_h, pixel_w)

    from dapple.canvas import Canvas as CanvasCls
    return CanvasCls(new_bitmap, colors=new_colors, renderer=canvas._renderer)


# ── Frame ───────────────────────────────────────────────────────────


# Box-drawing characters
_BOX_TL = "┌"
_BOX_TR = "┐"
_BOX_BL = "└"
_BOX_BR = "┘"
_BOX_H = "─"
_BOX_V = "│"


@dataclass
class Frame:
    """A framed canvas with optional title, border, and padding.

    Attributes:
        canvas: The canvas to frame.
        width: Target width in characters (None = auto).
        height: Target height in characters (None = auto).
        title: Optional title displayed above content.
        border: Draw a box-drawing border.
        padding: Blank character columns/rows around content.
    """

    canvas: Canvas
    width: int | None = None
    height: int | None = None
    title: str | None = None
    border: bool = False
    padding: int = 0

    def sized_canvas(self, renderer: Renderer) -> Canvas:
        """Return canvas resized for this frame's dimensions."""
        content_w = self._content_width()
        content_h = self._content_height()
        return _fit_canvas(
            self.canvas, renderer,
            width=content_w,
            height=content_h,
        )

    def render(self, renderer: Renderer, *, dest: TextIO | None = None) -> None:
        """Size canvas, render title/border/content."""
        output = dest or sys.stdout
        canvas = self.sized_canvas(renderer)

        # Render canvas to string
        buf = StringIO()
        renderer.render(canvas._bitmap, canvas._colors, dest=buf)
        lines = buf.getvalue().rstrip("\n").split("\n")

        content_w = self._content_width()

        # Title
        if self.title:
            title = self.title[:content_w] if content_w else self.title
            if self.border:
                # Title in top border
                border_fill = content_w - len(title) - 2 if content_w else 20
                output.write(f"{_BOX_TL}{_BOX_H}{title}{_BOX_H * max(0, border_fill)}{_BOX_TR}\n")
            else:
                output.write(f"{title}\n")

        elif self.border:
            w = content_w or (max(len(l) for l in lines) if lines else 0)
            output.write(f"{_BOX_TL}{_BOX_H * w}{_BOX_TR}\n")

        # Padding top
        for _ in range(self.padding):
            if self.border:
                w = content_w or (max(len(l) for l in lines) if lines else 0)
                output.write(f"{_BOX_V}{' ' * w}{_BOX_V}\n")
            else:
                output.write("\n")

        # Content lines
        for line in lines:
            pad = " " * self.padding
            if self.border:
                output.write(f"{_BOX_V}{pad}{line}{pad}{_BOX_V}\n")
            else:
                output.write(f"{pad}{line}{pad}\n")

        # Padding bottom
        for _ in range(self.padding):
            if self.border:
                w = content_w or (max(len(l) for l in lines) if lines else 0)
                output.write(f"{_BOX_V}{' ' * w}{_BOX_V}\n")
            else:
                output.write("\n")

        # Bottom border
        if self.border:
            w = content_w or (max(len(l) for l in lines) if lines else 0)
            output.write(f"{_BOX_BL}{_BOX_H * w}{_BOX_BR}\n")

    def _content_width(self) -> int | None:
        """Width available for canvas content."""
        if self.width is None:
            return None
        w = self.width
        if self.border:
            w -= 2  # left + right border
        w -= self.padding * 2
        return max(1, w)

    def _content_height(self) -> int | None:
        """Height available for canvas content."""
        if self.height is None:
            return None
        h = self.height
        if self.title:
            h -= 1
        if self.border:
            h -= 2  # top + bottom border
        h -= self.padding * 2
        return max(1, h)


# ── Grid ────────────────────────────────────────────────────────────


@dataclass
class Grid:
    """A grid of canvases or frames, laid out in rows.

    Each element in cells is a row (list of Canvas or Frame).

    Attributes:
        cells: 2D list of canvases or frames.
        width: Total width in characters (None = terminal width).
        gap: Gap between cells in characters.
    """

    cells: list[list[Canvas | Frame]]
    width: int | None = None
    gap: int = 1

    def render(self, renderer: Renderer, *, dest: TextIO | None = None) -> None:
        """Lay out cells in rows, render row by row."""
        output = dest or sys.stdout
        total_width = self.width or terminal_columns()

        for row_idx, row in enumerate(self.cells):
            if row_idx > 0 and self.gap > 0:
                # Gap rows between grid rows
                output.write("\n" * self.gap)

            if not row:
                continue

            num_cols = len(row)
            total_gaps = self.gap * (num_cols - 1)
            cell_width = max(1, (total_width - total_gaps) // num_cols)

            # Render each cell to string lines
            cell_line_lists: list[list[str]] = []
            max_lines = 0

            for cell in row:
                buf = StringIO()
                if isinstance(cell, Frame):
                    frame = Frame(
                        canvas=cell.canvas,
                        width=cell_width if cell.width is None else cell.width,
                        height=cell.height,
                        title=cell.title,
                        border=cell.border,
                        padding=cell.padding,
                    )
                    frame.render(renderer, dest=buf)
                else:
                    # Plain canvas: fit to cell_width
                    fitted = _fit_canvas(cell, renderer, width=cell_width)
                    renderer.render(fitted._bitmap, fitted._colors, dest=buf)

                lines = buf.getvalue().rstrip("\n").split("\n")
                cell_line_lists.append(lines)
                max_lines = max(max_lines, len(lines))

            # Merge lines horizontally
            gap_str = " " * self.gap
            for line_idx in range(max_lines):
                parts = []
                for col_idx, cell_lines in enumerate(cell_line_lists):
                    if line_idx < len(cell_lines):
                        parts.append(cell_lines[line_idx])
                    else:
                        parts.append("")
                output.write(gap_str.join(parts) + "\n")

    def to_canvas(self, renderer: Renderer) -> Canvas:
        """Flatten grid into a single Canvas by rendering and re-parsing.

        For simple composition, prefer render() directly.
        """
        buf = StringIO()
        self.render(renderer, dest=buf)
        # This is a best-effort: returns the text representation
        # For pixel-accurate composition, use Canvas.hstack/vstack
        raise NotImplementedError(
            "Grid.to_canvas() is not yet implemented. "
            "Use Grid.render() for direct output, or manually "
            "compose with Canvas.hstack()/vstack()."
        )
