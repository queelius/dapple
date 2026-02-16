"""Core CSV/TSV parsing, formatting, and data extraction.

Provides CsvData as the central representation, with functions for
reading, filtering, sorting, and formatting tabular data. All I/O
uses stdlib csv — no pandas dependency.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass


@dataclass
class CsvData:
    """Parsed CSV data: headers + rows."""

    headers: list[str]
    rows: list[list[str]]


def detect_delimiter(sample: str) -> str:
    """Auto-detect the delimiter from a text sample.

    Uses csv.Sniffer with a fallback to comma if detection fails.
    """
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t|;")
        return dialect.delimiter
    except csv.Error:
        return ","


def read_csv(
    source: io.TextIOBase,
    delimiter: str | None = None,
    has_header: bool = True,
) -> CsvData:
    """Read CSV/TSV from a text stream.

    Args:
        source: Readable text stream.
        delimiter: Explicit delimiter, or None for auto-detect.
        has_header: If True, first row is treated as headers.

    Returns:
        CsvData with headers and rows.
    """
    text = source.read()
    if not text.strip():
        return CsvData(headers=[], rows=[])

    if delimiter is None:
        # Use first ~8KB for sniffing
        delimiter = detect_delimiter(text[:8192])

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = list(reader)

    if not all_rows:
        return CsvData(headers=[], rows=[])

    if has_header:
        headers = all_rows[0]
        rows = all_rows[1:]
    else:
        # Generate numeric column headers
        ncols = max(len(r) for r in all_rows) if all_rows else 0
        headers = [str(i) for i in range(ncols)]
        rows = all_rows

    return CsvData(headers=headers, rows=rows)


def select_columns(data: CsvData, cols: list[str]) -> CsvData:
    """Select a subset of columns by name.

    Args:
        data: Input data.
        cols: Column names to keep.

    Returns:
        New CsvData with only the selected columns.

    Raises:
        ValueError: If a column name is not found.
    """
    indices = []
    for col in cols:
        try:
            indices.append(data.headers.index(col))
        except ValueError:
            available = ", ".join(data.headers)
            raise ValueError(f"Column '{col}' not found. Available: {available}")

    new_headers = [data.headers[i] for i in indices]
    new_rows = [[row[i] if i < len(row) else "" for i in indices] for row in data.rows]
    return CsvData(headers=new_headers, rows=new_rows)


def sort_by(data: CsvData, column: str, reverse: bool = False) -> CsvData:
    """Sort rows by a column. Attempts numeric sort, falls back to string.

    Args:
        data: Input data.
        column: Column name to sort by.
        reverse: If True, sort descending.

    Returns:
        New CsvData with sorted rows.
    """
    try:
        idx = data.headers.index(column)
    except ValueError:
        available = ", ".join(data.headers)
        raise ValueError(f"Column '{column}' not found. Available: {available}")

    def sort_key(row: list[str]) -> tuple:
        val = row[idx] if idx < len(row) else ""
        try:
            return (0, float(val))
        except (ValueError, TypeError):
            return (1, val.lower())

    sorted_rows = sorted(data.rows, key=sort_key, reverse=reverse)
    return CsvData(headers=list(data.headers), rows=sorted_rows)


def head(data: CsvData, n: int) -> CsvData:
    """Return the first n rows."""
    return CsvData(headers=list(data.headers), rows=data.rows[:n])


def tail(data: CsvData, n: int) -> CsvData:
    """Return the last n rows."""
    return CsvData(headers=list(data.headers), rows=data.rows[-n:])


_BOOL_STRINGS = {"true", "false", "yes", "no"}
_NULL_STRINGS = {"", "null", "none", "n/a", "na", "-"}

# Column color cycling palette (ANSI 256-color)
_COLUMN_COLORS = [
    "\033[36m",   # cyan
    "\033[32m",   # green
    "\033[33m",   # yellow
    "\033[35m",   # magenta
    "\033[34m",   # blue
    "\033[91m",   # bright red
    "\033[96m",   # bright cyan
    "\033[93m",   # bright yellow
]


def _type_color(val: str) -> str:
    """Return ANSI color code based on heuristic type detection."""
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    DIM = "\033[2m"

    low = val.strip().lower()
    if low in _NULL_STRINGS:
        return DIM
    if low in _BOOL_STRINGS:
        return YELLOW
    try:
        float(val)
        return CYAN
    except (ValueError, TypeError):
        return ""


def format_table(data: CsvData, cycle_colors: bool = False) -> str:
    """Format data as an aligned text table with ANSI header highlighting.

    Args:
        data: Input data.
        cycle_colors: If True, assign a rotating color to each column.
            If False (default), color by value type (numbers=cyan,
            booleans=yellow, nulls=dim).

    Returns:
        Formatted table string with newlines.
    """
    if not data.headers:
        return ""

    # Compute column widths
    widths = [len(h) for h in data.headers]
    for row in data.rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
            else:
                widths.append(len(cell))

    # ANSI codes
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    lines: list[str] = []

    # Header row
    header_cells = []
    for i, h in enumerate(data.headers):
        w = widths[i] if i < len(widths) else len(h)
        if cycle_colors:
            color = _COLUMN_COLORS[i % len(_COLUMN_COLORS)]
            header_cells.append(f"{BOLD}{color}{h:<{w}}{RESET}")
        else:
            header_cells.append(f"{BOLD}{CYAN}{h:<{w}}{RESET}")
    lines.append("  ".join(header_cells))

    # Separator
    sep_cells = [DIM + "─" * w + RESET for w in widths]
    lines.append("  ".join(sep_cells))

    # Data rows
    for row in data.rows:
        cells = []
        for i in range(len(data.headers)):
            w = widths[i] if i < len(widths) else 0
            val = row[i] if i < len(row) else ""

            if cycle_colors:
                color = _COLUMN_COLORS[i % len(_COLUMN_COLORS)]
            else:
                color = _type_color(val)

            # Right-align numbers
            try:
                float(val)
                formatted = f"{val:>{w}}"
            except (ValueError, TypeError):
                formatted = f"{val:<{w}}"

            if color:
                cells.append(f"{color}{formatted}{RESET}")
            else:
                cells.append(formatted)
        lines.append("  ".join(cells))

    return "\n".join(lines)


def extract_numeric(data: CsvData, column: str) -> list[float]:
    """Extract numeric values from a column, skipping non-numeric rows.

    Args:
        data: Input data.
        column: Column name.

    Returns:
        List of float values.

    Raises:
        ValueError: If column not found or no numeric values.
    """
    try:
        idx = data.headers.index(column)
    except ValueError:
        available = ", ".join(data.headers)
        raise ValueError(f"Column '{column}' not found. Available: {available}")

    values: list[float] = []
    for row in data.rows:
        if idx < len(row):
            try:
                values.append(float(row[idx]))
            except (ValueError, TypeError):
                continue

    if not values:
        raise ValueError(f"No numeric values found in column '{column}'")

    return values


def _is_numeric_column(data: CsvData, idx: int) -> bool:
    """Check if a column is predominantly numeric."""
    numeric_count = 0
    for row in data.rows:
        if idx < len(row):
            try:
                float(row[idx])
                numeric_count += 1
            except (ValueError, TypeError):
                pass
    return numeric_count > len(data.rows) // 2


def _find_label_column(data: CsvData, exclude_idx: int) -> int | None:
    """Find the first non-numeric column to use as labels."""
    for i, header in enumerate(data.headers):
        if i == exclude_idx:
            continue
        if not _is_numeric_column(data, i):
            return i
    return None


def extract_categories(
    data: CsvData, column: str
) -> tuple[list[str], list[float]]:
    """Extract bar chart data from a column.

    If the column is numeric, uses the values directly as bar lengths
    and finds a text column for labels. If categorical, counts occurrences.

    Args:
        data: Input data.
        column: Column name.

    Returns:
        (labels, values) tuple.

    Raises:
        ValueError: If column not found.
    """
    try:
        idx = data.headers.index(column)
    except ValueError:
        available = ", ".join(data.headers)
        raise ValueError(f"Column '{column}' not found. Available: {available}")

    # If the column is numeric, plot values directly with labels from
    # the first text column (or row indices).
    if _is_numeric_column(data, idx):
        label_idx = _find_label_column(data, idx)
        labels = []
        values = []
        for i, row in enumerate(data.rows):
            if idx < len(row):
                try:
                    val = float(row[idx])
                except (ValueError, TypeError):
                    continue
                if label_idx is not None and label_idx < len(row):
                    labels.append(row[label_idx])
                else:
                    labels.append(str(i + 1))
                values.append(val)
        return labels, values

    # Categorical: count occurrences
    values_str = [row[idx] for row in data.rows if idx < len(row)]
    counts = Counter(values_str)

    # Sort by count descending
    sorted_items = counts.most_common()
    labels = [item[0] for item in sorted_items]
    counts_list = [float(item[1]) for item in sorted_items]

    return labels, counts_list
