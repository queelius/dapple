"""Text-based chart formatters. Return ANSI-colored strings for inline terminal display."""

from __future__ import annotations

import math
import shutil
from typing import Sequence

# ANSI color codes
_BAR_COLORS = [
    "\033[31m",  # red
    "\033[32m",  # green
    "\033[33m",  # yellow
    "\033[34m",  # blue
    "\033[35m",  # magenta
    "\033[36m",  # cyan
]
_RESET = "\033[0m"
_BOLD = "\033[1m"
_CYAN = "\033[36m"

# Unicode block elements for fractional fill
_BLOCKS = " ▏▎▍▌▋▊▉█"

# Unicode sparkline characters (8 levels)
_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _format_value(v: float) -> str:
    """Format a numeric value for display."""
    if not math.isfinite(v):
        return str(v)
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


def text_bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    width: int | None = None,
    title: str = "",
) -> str:
    """Text-based horizontal bar chart with Unicode block characters.

    Args:
        labels: Category labels.
        values: Numeric values per category.
        width: Total output width in characters (None = terminal width).
        title: Optional title displayed above the chart.

    Returns:
        Formatted bar chart as ANSI-colored string.
    """
    if not labels or not values:
        return ""
    if len(labels) != len(values):
        raise ValueError(f"labels ({len(labels)}) and values ({len(values)}) must have the same length")

    width = width or shutil.get_terminal_size(fallback=(80, 24)).columns

    finite_vals = [abs(v) for v in values if math.isfinite(v)]
    v_max = max(finite_vals) if finite_vals else 1.0
    if v_max == 0:
        v_max = 1.0

    formatted_vals = [_format_value(v) for v in values]
    label_width = max(len(l) for l in labels)
    val_width = max(len(v) for v in formatted_vals)
    # Layout: "label  ████████  value"
    bar_space = width - label_width - val_width - 4  # 4 = 2 spaces + 2 spaces
    bar_space = max(10, bar_space)

    lines: list[str] = []

    if title:
        lines.append(f"{_BOLD}{title}{_RESET}")
        lines.append("")

    for i, (label, val, fval) in enumerate(zip(labels, values, formatted_vals)):
        color = _BAR_COLORS[i % len(_BAR_COLORS)]
        fill_fraction = abs(val) / v_max * bar_space if math.isfinite(val) else 0.0
        full_blocks = int(fill_fraction)
        remainder = fill_fraction - full_blocks
        partial_idx = int(remainder * 8)
        bar = "█" * full_blocks
        if partial_idx > 0 and full_blocks < bar_space:
            bar += _BLOCKS[partial_idx]

        lines.append(
            f"{label:<{label_width}}  {color}{bar}{_RESET}"
            f"  {fval:>{val_width}}"
        )

    return "\n".join(lines)


def text_sparkline(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    title: str = "",
) -> str:
    """Text-based sparkline with Unicode block characters.

    Each value maps to one of 8 block heights (▁▂▃▄▅▆▇█),
    producing a compact single-line visualization with a
    labeled value breakdown below.

    Args:
        labels: Row labels.
        values: Numeric values.
        title: Optional title displayed above the chart.

    Returns:
        Formatted sparkline as ANSI-colored string.
    """
    if not labels or not values:
        return ""
    if len(labels) != len(values):
        raise ValueError(f"labels ({len(labels)}) and values ({len(values)}) must have the same length")

    finite_vals = [v for v in values if math.isfinite(v)]
    v_min = min(finite_vals) if finite_vals else 0.0
    v_max = max(finite_vals) if finite_vals else 0.0
    if v_max == v_min:
        v_min -= 0.5
        v_max += 0.5

    def _spark_index(v: float) -> int:
        if not math.isfinite(v):
            return 0
        normalized = (v - v_min) / (v_max - v_min)
        return max(0, min(7, int(normalized * 7)))

    # Build spark characters
    spark = ""
    for v in values:
        spark += _SPARK_CHARS[_spark_index(v)]

    formatted_vals = [_format_value(v) for v in values]

    lines: list[str] = []

    if title:
        lines.append(f"{_BOLD}{title}{_RESET}")
        lines.append("")

    # Sparkline
    lines.append(f"  {_CYAN}{spark}{_RESET}")
    lines.append("")

    # Value summary with labels
    label_width = max(len(l) for l in labels) if labels else 0
    val_width = max(len(v) for v in formatted_vals)
    for i, (label, fval) in enumerate(zip(labels, formatted_vals)):
        char = _SPARK_CHARS[_spark_index(values[i])]
        lines.append(f"  {_CYAN}{char}{_RESET} {label:<{label_width}}  {_CYAN}{fval:>{val_width}}{_RESET}")

    # Min/max summary
    finite_formatted = [fv for fv, v in zip(formatted_vals, values) if math.isfinite(v)]
    if finite_formatted:
        lines.append("")
        lines.append(f"  min: {min(finite_formatted, key=lambda x: float(x))}  max: {max(finite_formatted, key=lambda x: float(x))}")
    else:
        lines.append("")
        lines.append("  min: -  max: -")

    return "\n".join(lines)
