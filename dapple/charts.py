"""Character-dimension chart API.

Thin wrappers around dapple.extras.vizlib.charts that accept character
dimensions instead of pixel dimensions. All functions return a Canvas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from dapple.canvas import Canvas

from dapple.layout import terminal_columns

# Reference cell dimensions (braille: 2 wide, 4 tall)
_REF_CELL_W = 2
_REF_CELL_H = 4


# ── Bitmap charts (return Canvas) ───────────────────────────────────


def sparkline(
    values: Sequence[float],
    *,
    width: int | None = None,
    height: int = 4,
    color: tuple[float, float, float] | None = None,
    thickness: int = 1,
) -> Canvas:
    """Sparkline chart. Width/height in characters.

    Args:
        values: Numeric data points.
        width: Width in characters (None = terminal width).
        height: Height in characters (default 4).
        color: RGB color tuple (0-1).
        thickness: Line thickness in pixels (default 1).

    Returns:
        Canvas with the sparkline rendered.
    """
    from dapple.extras.vizlib.charts import sparkline as _sparkline

    w = width or terminal_columns()
    return _sparkline(
        values, width=w * _REF_CELL_W, height=height * _REF_CELL_H,
        color=color, thickness=thickness,
    )


def line_plot(
    values: Sequence[float],
    *,
    width: int | None = None,
    height: int = 20,
    color: tuple[float, float, float] | None = None,
    show_axes: bool = True,
    series: list[tuple[Sequence[float], tuple[float, float, float] | None]] | None = None,
    thickness: int = 1,
) -> Canvas:
    """Line plot with optional axes. Width/height in characters.

    Args:
        values: Numeric data points (primary series).
        width: Width in characters (None = terminal width).
        height: Height in characters (default 20).
        color: RGB color tuple (0-1).
        show_axes: Draw a baseline axis at y=0 if in range.
        series: Additional series as (values, color) tuples. Colors auto-cycle
                from COLOR_PALETTE when None.
        thickness: Line thickness in pixels (default 1).

    Returns:
        Canvas with the line plot rendered.
    """
    from dapple.extras.vizlib.charts import line_plot as _line_plot

    w = width or terminal_columns()
    return _line_plot(
        values, width=w * _REF_CELL_W, height=height * _REF_CELL_H,
        color=color, show_axes=show_axes,
        series=series, thickness=thickness,
    )


def bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    width: int | None = None,
    height: int = 20,
    horizontal: bool = True,
    color: tuple[float, float, float] | None = None,
) -> Canvas:
    """Bar chart. Width/height in characters.

    Args:
        labels: Category labels.
        values: Numeric values per category.
        width: Width in characters (None = terminal width).
        height: Height in characters (default 20).
        horizontal: Bars go left-to-right (True) or bottom-to-top (False).
        color: RGB color tuple (0-1).

    Returns:
        Canvas with the bar chart rendered.
    """
    from dapple.extras.vizlib.charts import bar_chart as _bar_chart

    w = width or terminal_columns()
    return _bar_chart(
        labels, values, width=w * _REF_CELL_W, height=height * _REF_CELL_H,
        horizontal=horizontal, color=color,
    )


def histogram(
    values: Sequence[float],
    *,
    width: int | None = None,
    height: int = 20,
    bins: int = 20,
    color: tuple[float, float, float] | None = None,
) -> Canvas:
    """Histogram. Width/height in characters.

    Args:
        values: Numeric data points.
        width: Width in characters (None = terminal width).
        height: Height in characters (default 20).
        bins: Number of histogram bins.
        color: RGB color tuple (0-1).

    Returns:
        Canvas with the histogram rendered.
    """
    from dapple.extras.vizlib.charts import histogram as _histogram

    w = width or terminal_columns()
    return _histogram(
        values, width=w * _REF_CELL_W, height=height * _REF_CELL_H,
        bins=bins, color=color,
    )


def heatmap(
    data: Sequence[Sequence[float]],
    *,
    width: int | None = None,
    height: int | None = None,
) -> Canvas:
    """Heatmap from 2D data. Width/height in characters.

    Args:
        data: 2D array of numeric values.
        width: Width in characters (None = terminal width).
        height: Height in characters (None = auto from data rows).

    Returns:
        Canvas with the heatmap rendered.
    """
    from dapple.extras.vizlib.charts import heatmap as _heatmap

    w = width or terminal_columns()
    h = height or max(10, len(data))
    return _heatmap(data, width=w * _REF_CELL_W, height=h * _REF_CELL_H)
