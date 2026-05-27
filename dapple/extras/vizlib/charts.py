"""Chart primitives that produce dapple Canvas objects.

Each function maps data values to pixel coordinates in a numpy bitmap,
then wraps the result in a Canvas. This bitmap-based approach (adapted
from funcat's plot_function_to_mask) means every chart works with every
dapple renderer — braille, sextants, sixel, kitty, etc.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from dapple.canvas import Canvas

from dapple.extras.vizlib.colors import COLOR_PALETTE


def sparkline(
    values: Sequence[float],
    *,
    width: int,
    height: int,
    color: tuple[float, float, float] | None = None,
    thickness: int = 1,
) -> Canvas:
    """Render a sparkline — a compact line chart without axes.

    Args:
        values: Numeric data points.
        width: Bitmap width in pixels.
        height: Bitmap height in pixels.
        color: RGB color tuple (0-1). Defaults to cyan.
        thickness: Line thickness in pixels (default 1).

    Returns:
        Canvas with the sparkline rendered.
    """
    if len(values) == 0:
        return _empty_canvas(width, height)

    vals = np.array(values, dtype=np.float64)
    color = color or COLOR_PALETTE[0]

    bitmap = np.zeros((height, width), dtype=np.float32)
    colors = np.zeros((height, width, 3), dtype=np.float32)

    v_min, v_max = float(vals.min()), float(vals.max())
    if v_max == v_min:
        v_min -= 0.5
        v_max += 0.5

    # Map values to pixel rows (row 0 = top = max value)
    normalized = (vals - v_min) / (v_max - v_min)
    pixel_rows = ((1 - normalized) * (height - 1)).astype(int)
    pixel_cols = np.linspace(0, width - 1, len(vals)).astype(int)

    # Draw the line with vertical fill between consecutive points
    for i in range(len(vals)):
        col = pixel_cols[i]
        row = np.clip(pixel_rows[i], 0, height - 1)
        if thickness > 1:
            _set_thick_pixel(bitmap, colors, col, row, color, thickness)
        elif 0 <= col < width:
            bitmap[row, col] = 1.0
            colors[row, col] = color

        # Connect consecutive points vertically
        if i > 0:
            prev_row = np.clip(pixel_rows[i - 1], 0, height - 1)
            prev_col = pixel_cols[i - 1]
            _draw_line(bitmap, colors, prev_col, prev_row, col, row, color, thickness)

    return Canvas(bitmap, colors=colors)


def line_plot(
    values: Sequence[float],
    *,
    width: int,
    height: int,
    color: tuple[float, float, float] | None = None,
    show_axes: bool = True,
    series: list[tuple[Sequence[float], tuple[float, float, float] | None]] | None = None,
    thickness: int = 1,
) -> Canvas:
    """Render a line plot with optional axes and multiple series.

    Args:
        values: Numeric data points (primary series).
        width: Bitmap width in pixels.
        height: Bitmap height in pixels.
        color: RGB color tuple (0-1). Defaults to cycling palette.
        show_axes: Draw a baseline axis at y=0 if in range.
        series: Additional series as (values, color) tuples. Colors auto-cycle
                from COLOR_PALETTE if None. When provided, `values` and `color`
                are used as the first series.
        thickness: Line thickness in pixels (default 1).

    Returns:
        Canvas with the line plot rendered.
    """
    # Build full list of (values, color) series
    all_series: list[tuple[Sequence[float], tuple[float, float, float]]] = [
        (values, color or COLOR_PALETTE[0]),
    ]
    if series is not None:
        for i, (s_vals, s_color) in enumerate(series):
            all_series.append((s_vals, s_color or COLOR_PALETTE[(i + 1) % len(COLOR_PALETTE)]))

    # Check for any data
    if all(len(s[0]) == 0 for s in all_series):
        return _empty_canvas(width, height)

    axis_color = (0.5, 0.5, 0.5)
    bitmap = np.zeros((height, width), dtype=np.float32)
    colors = np.zeros((height, width, 3), dtype=np.float32)

    # Find global min/max across all series
    all_vals = np.concatenate([np.array(s[0], dtype=np.float64) for s in all_series if len(s[0]) > 0])
    v_min, v_max = float(all_vals.min()), float(all_vals.max())
    if v_max == v_min:
        v_min -= 0.5
        v_max += 0.5

    # Draw baseline axis
    if show_axes and v_min <= 0 <= v_max:
        zero_row = int((1 - (0 - v_min) / (v_max - v_min)) * (height - 1))
        zero_row = np.clip(zero_row, 0, height - 1)
        bitmap[zero_row, :] = 0.3
        colors[zero_row, :] = axis_color

    # Draw each series
    for s_vals, s_color in all_series:
        if len(s_vals) == 0:
            continue
        vals = np.array(s_vals, dtype=np.float64)
        normalized = (vals - v_min) / (v_max - v_min)
        pixel_rows = ((1 - normalized) * (height - 1)).astype(int)
        pixel_cols = np.linspace(0, width - 1, len(vals)).astype(int)

        for i in range(len(vals)):
            col = pixel_cols[i]
            row = np.clip(pixel_rows[i], 0, height - 1)
            if thickness > 1:
                _set_thick_pixel(bitmap, colors, col, row, s_color, thickness)
            elif 0 <= col < width:
                bitmap[row, col] = 1.0
                colors[row, col] = s_color

            if i > 0:
                prev_row = np.clip(pixel_rows[i - 1], 0, height - 1)
                prev_col = pixel_cols[i - 1]
                _draw_line(bitmap, colors, prev_col, prev_row, col, row, s_color, thickness)

    return Canvas(bitmap, colors=colors)


def bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    width: int,
    height: int,
    horizontal: bool = True,
    color: tuple[float, float, float] | None = None,
) -> Canvas:
    """Render a bar chart.

    Args:
        labels: Category labels (used for proportional sizing).
        values: Numeric values per category.
        width: Bitmap width in pixels.
        height: Bitmap height in pixels.
        horizontal: If True, bars go left-to-right. If False, bottom-to-top.
        color: RGB color tuple (0-1). Defaults to cycling palette.

    Returns:
        Canvas with the bar chart rendered.
    """
    n = len(values)
    if n == 0:
        return _empty_canvas(width, height)

    vals = np.array(values, dtype=np.float64)
    v_max = float(np.abs(vals).max())
    if v_max == 0:
        v_max = 1.0

    bitmap = np.zeros((height, width), dtype=np.float32)
    colors = np.zeros((height, width, 3), dtype=np.float32)

    if horizontal:
        # Horizontal bars: each bar is a horizontal row band
        bar_height = max(1, height // n)
        gap = max(1, bar_height // 4)
        bar_height = max(1, (height - gap * (n - 1)) // n) if n > 1 else height

        for i, val in enumerate(vals):
            bar_color = color or COLOR_PALETTE[i % len(COLOR_PALETTE)]
            y_start = i * (bar_height + gap)
            y_end = min(y_start + bar_height, height)
            bar_width = int(abs(val) / v_max * (width - 1))
            bar_width = max(1, bar_width)

            bitmap[y_start:y_end, 0:bar_width] = 1.0
            colors[y_start:y_end, 0:bar_width] = bar_color
    else:
        # Vertical bars: each bar is a vertical column band
        bar_width = max(1, width // n)
        gap = max(1, bar_width // 4)
        bar_width = max(1, (width - gap * (n - 1)) // n) if n > 1 else width

        for i, val in enumerate(vals):
            bar_color = color or COLOR_PALETTE[i % len(COLOR_PALETTE)]
            x_start = i * (bar_width + gap)
            x_end = min(x_start + bar_width, width)
            bar_height_px = int(abs(val) / v_max * (height - 1))
            bar_height_px = max(1, bar_height_px)

            bitmap[height - bar_height_px:height, x_start:x_end] = 1.0
            colors[height - bar_height_px:height, x_start:x_end] = bar_color

    return Canvas(bitmap, colors=colors)


def histogram(
    values: Sequence[float],
    *,
    width: int,
    height: int,
    bins: int = 20,
    color: tuple[float, float, float] | None = None,
) -> Canvas:
    """Render a histogram of value distribution.

    Args:
        values: Numeric data points.
        width: Bitmap width in pixels.
        height: Bitmap height in pixels.
        bins: Number of histogram bins.
        color: RGB color tuple (0-1). Defaults to cyan.

    Returns:
        Canvas with the histogram rendered.
    """
    if len(values) == 0:
        return _empty_canvas(width, height)

    vals = np.array(values, dtype=np.float64)
    color = color or COLOR_PALETTE[0]

    counts, _ = np.histogram(vals, bins=bins)
    max_count = float(counts.max())
    if max_count == 0:
        max_count = 1.0

    bitmap = np.zeros((height, width), dtype=np.float32)
    colors = np.zeros((height, width, 3), dtype=np.float32)

    bin_width = max(1, width // bins)

    for i, count in enumerate(counts):
        x_start = i * bin_width
        x_end = min(x_start + bin_width, width)
        # Leave 1px gap between bins for visual separation
        if bin_width > 2 and x_end > x_start + 1:
            x_end -= 1

        bar_height = int(count / max_count * (height - 1))
        bar_height = max(1, bar_height) if count > 0 else 0

        if bar_height > 0:
            bitmap[height - bar_height:height, x_start:x_end] = 1.0
            colors[height - bar_height:height, x_start:x_end] = color

    return Canvas(bitmap, colors=colors)


def heatmap(
    values: Sequence[Sequence[float]],
    *,
    width: int,
    height: int,
) -> Canvas:
    """Render a heatmap from a 2D array of values.

    Values are mapped to brightness (0=dark, max=bright) with a
    blue-to-red color gradient.

    Args:
        values: 2D array of numeric values.
        width: Bitmap width in pixels.
        height: Bitmap height in pixels.

    Returns:
        Canvas with the heatmap rendered.
    """
    data = np.array(values, dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.size == 0:
        return _empty_canvas(width, height)

    rows, cols = data.shape
    v_min, v_max = float(data.min()), float(data.max())
    if v_max == v_min:
        v_min -= 0.5
        v_max += 0.5

    normalized = (data - v_min) / (v_max - v_min)

    bitmap = np.zeros((height, width), dtype=np.float32)
    colors = np.zeros((height, width, 3), dtype=np.float32)

    cell_h = max(1, height // rows)
    cell_w = max(1, width // cols)

    for r in range(rows):
        for c in range(cols):
            val = normalized[r, c]
            y_start = r * cell_h
            y_end = min(y_start + cell_h, height)
            x_start = c * cell_w
            x_end = min(x_start + cell_w, width)

            # Blue (cold) -> White (mid) -> Red (hot)
            if val < 0.5:
                t = val * 2
                rgb = (t, t, 1.0)
            else:
                t = (val - 0.5) * 2
                rgb = (1.0, 1.0 - t, 1.0 - t)

            bitmap[y_start:y_end, x_start:x_end] = max(0.2, val)
            colors[y_start:y_end, x_start:x_end] = rgb

    return Canvas(bitmap, colors=colors)


# ── Helpers ──────────────────────────────────────────────────────────


def _empty_canvas(width: int, height: int) -> Canvas:
    """Return a blank canvas."""
    bitmap = np.zeros((height, width), dtype=np.float32)
    return Canvas(bitmap)


def _set_thick_pixel(
    bitmap: np.ndarray,
    colors: np.ndarray,
    x: int,
    y: int,
    color: tuple[float, float, float],
    thickness: int,
) -> None:
    """Paint a `thickness` x `thickness` brush centered on (x, y).

    For odd thickness the brush is centered exactly. For even thickness it
    is offset to the top-left (standard convention), so thickness=2 paints
    the 2x2 block covering (y-1, x-1), (y-1, x), (y, x-1), (y, x).
    """
    h, w = bitmap.shape
    half = thickness // 2
    for dy in range(thickness):
        for dx in range(thickness):
            ny = y + dy - half
            nx = x + dx - half
            if 0 <= ny < h and 0 <= nx < w:
                bitmap[ny, nx] = 1.0
                colors[ny, nx] = color


def _draw_line(
    bitmap: np.ndarray,
    colors: np.ndarray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[float, float, float],
    thickness: int = 1,
) -> None:
    """Draw a line between two points using Bresenham's algorithm."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    h, w = bitmap.shape

    while True:
        if thickness > 1:
            _set_thick_pixel(bitmap, colors, x0, y0, color, thickness)
        elif 0 <= y0 < h and 0 <= x0 < w:
            bitmap[y0, x0] = 1.0
            colors[y0, x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
