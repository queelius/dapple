"""Core data parsing, queries, formatting, and extraction.

Handles JSON, JSONL, CSV, and TSV. Provides functions for reading,
querying, formatting, and extracting numeric/categorical data.
All parsing uses stdlib json and csv -- no external dependencies.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


# ── Format detection ──────────────────────────────────────────────────


def detect_format(text: str, filename: str | None = None) -> str:
    """Detect data format: json, jsonl, or csv.

    Uses filename extension first (if provided), then content sniffing.

    Args:
        text: Input text.
        filename: Optional filename for extension-based detection.

    Returns:
        "json", "jsonl", or "csv"
    """
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in (".csv", ".tsv"):
            return "csv"
        if ext == ".jsonl":
            return "jsonl"
        if ext == ".json":
            return "json"

    stripped = text.strip()
    if not stripped:
        return "json"

    # Content sniffing: try JSON first
    if stripped.startswith(("{", "[")):
        # Check for JSONL (multiple JSON values on separate lines)
        lines = [line.strip() for line in stripped.split("\n") if line.strip()]
        if len(lines) <= 1:
            return "json"

        first = lines[0]
        try:
            json.loads(first)
            if len(lines) > 1:
                try:
                    json.loads(lines[1])
                    return "jsonl"
                except json.JSONDecodeError:
                    return "json"
        except json.JSONDecodeError:
            pass

        return "json"

    # Not JSON-looking — treat as CSV/TSV
    return "csv"


# ── JSON reading ─────────────────────────────────────────────────────


def read_json(text: str) -> list[dict] | dict | list:
    """Parse JSON or JSONL text.

    For JSONL, returns a list of parsed records.
    For JSON, returns the parsed value as-is.

    Raises:
        json.JSONDecodeError: If parsing fails.
    """
    fmt = detect_format(text)

    if fmt == "jsonl":
        records = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records

    return json.loads(text)


# ── CSV reading ──────────────────────────────────────────────────────


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
    text: str,
    delimiter: str | None = None,
    has_header: bool = True,
) -> list[dict]:
    """Read CSV/TSV text into a list of dicts.

    Args:
        text: CSV/TSV text content.
        delimiter: Explicit delimiter, or None for auto-detect.
        has_header: If True, first row is treated as headers.

    Returns:
        List of dicts (one per row), with header names as keys.
        Returns empty list for empty input.
    """
    if not text.strip():
        return []

    if delimiter is None:
        delimiter = detect_delimiter(text[:8192])

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = list(reader)

    if not all_rows:
        return []

    if has_header:
        headers = all_rows[0]
        data_rows = all_rows[1:]
    else:
        ncols = max(len(r) for r in all_rows) if all_rows else 0
        headers = [str(i) for i in range(ncols)]
        data_rows = all_rows

    records: list[dict] = []
    for row in data_rows:
        rec: dict[str, str] = {}
        for i, h in enumerate(headers):
            rec[h] = row[i] if i < len(row) else ""
        records.append(rec)

    return records


# ── Record manipulation ──────────────────────────────────────────────


def select_columns(records: list[dict], cols: list[str]) -> list[dict]:
    """Select a subset of columns by name.

    Args:
        records: List of dicts.
        cols: Column names to keep.

    Returns:
        New list of dicts with only the selected keys.

    Raises:
        ValueError: If a column name is not found.
    """
    if not records:
        return []

    # Validate column names against first record
    available_keys = list(records[0].keys())
    for col in cols:
        if col not in records[0]:
            available = ", ".join(available_keys)
            raise ValueError(f"Column '{col}' not found. Available: {available}")

    return [{col: rec.get(col, "") for col in cols} for rec in records]


def sort_records(
    records: list[dict], column: str, reverse: bool = False
) -> list[dict]:
    """Sort records by a column. Attempts numeric sort, falls back to string.

    Args:
        records: List of dicts.
        column: Column name to sort by.
        reverse: If True, sort descending.

    Returns:
        New sorted list of dicts.

    Raises:
        ValueError: If column not found.
    """
    if not records:
        return []

    if column not in records[0]:
        available = ", ".join(records[0].keys())
        raise ValueError(f"Column '{column}' not found. Available: {available}")

    def sort_key(rec: dict) -> tuple:
        val = str(rec.get(column, ""))
        try:
            return (0, float(val))
        except (ValueError, TypeError):
            return (1, val.lower())

    return sorted(records, key=sort_key, reverse=reverse)


# ── Dot-path queries ─────────────────────────────────────────────────


def dot_path_query(data: Any, path: str) -> Any:
    """Resolve a dot-path query like '.foo.bar[0].baz'.

    Path syntax:
        .key        - object key lookup
        [N]         - array index
        .key[N]     - key then index

    When applied to a list of records, maps the remaining path
    across all items.

    Args:
        data: Parsed JSON data.
        path: Dot-path string (must start with '.').

    Returns:
        The resolved value, or a list of values for JSONL records.

    Raises:
        KeyError: If a key is not found.
        IndexError: If an array index is out of range.
        TypeError: If the data structure doesn't match the path.
    """
    if not path or path == ".":
        return data

    # Parse path into segments
    segments = _parse_path(path)
    return _resolve(data, segments)


def _parse_path(path: str) -> list[str | int]:
    """Parse '.foo.bar[0].baz' into ['foo', 'bar', 0, 'baz']."""
    segments: list[str | int] = []
    # Remove leading dot
    p = path.lstrip(".")
    if not p:
        return segments

    # Split into tokens on '.' but preserve [N] indexing
    parts = re.split(r"\.", p)
    for part in parts:
        if not part:
            continue
        # Check for array indexing: 'key[0]' or just '[0]'
        bracket_match = re.match(r"^([^\[]*?)(\[(\d+)\](.*))?$", part)
        if bracket_match:
            key = bracket_match.group(1)
            if key:
                segments.append(key)
            if bracket_match.group(3) is not None:
                segments.append(int(bracket_match.group(3)))
            # Handle chained brackets like [0][1]
            rest = bracket_match.group(4) or ""
            while rest:
                m = re.match(r"^\[(\d+)\](.*)", rest)
                if m:
                    segments.append(int(m.group(1)))
                    rest = m.group(2)
                else:
                    break
        else:
            segments.append(part)

    return segments


def _resolve(data: Any, segments: list[str | int]) -> Any:
    """Walk data along the parsed path segments."""
    current = data
    for i, seg in enumerate(segments):
        if isinstance(current, list) and isinstance(seg, str):
            # Map across list of records
            remaining = segments[i:]
            return [_resolve(item, remaining) for item in current]
        if isinstance(seg, int):
            current = current[seg]
        elif isinstance(current, dict):
            current = current[seg]
        else:
            raise TypeError(
                f"Cannot index {type(current).__name__} with key '{seg}'"
            )
    return current


# ── Formatting ────────────────────────────────────────────────────────


# ANSI color constants
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_GRAY = "\033[90m"
_WHITE_BOLD = "\033[1;37m"


def format_json(data: Any, colorize: bool = True) -> str:
    """Pretty-print JSON with optional ANSI syntax coloring.

    Colors:
        strings = green, numbers = cyan, keys = white bold,
        null = gray, booleans = yellow

    Uses a single-pass tokenizer to avoid regex passes corrupting
    previously-inserted ANSI escape sequences.

    Args:
        data: Parsed JSON data.
        colorize: Apply ANSI colors.

    Returns:
        Formatted JSON string.
    """
    text = json.dumps(data, indent=2, ensure_ascii=False)

    if not colorize:
        return text

    # Single-pass tokenization: match JSON tokens and colorize each one.
    # This avoids the problem of regex passes matching digits inside
    # ANSI escape codes inserted by earlier passes.
    token_re = re.compile(
        r'("(?:[^"\\]|\\.)*")\s*:'   # key: string followed by colon
        r'|("(?:[^"\\]|\\.)*")'       # string value
        r'|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'  # number
        r'|\b(true|false)\b'          # boolean
        r'|\b(null)\b'                # null
    )

    def _colorize_match(m: re.Match) -> str:
        if m.group(1) is not None:  # key
            return f"{_WHITE_BOLD}{m.group(1)}{_RESET}:"
        if m.group(2) is not None:  # string
            return f"{_GREEN}{m.group(2)}{_RESET}"
        if m.group(3) is not None:  # number
            return f"{_CYAN}{m.group(3)}{_RESET}"
        if m.group(4) is not None:  # boolean
            return f"{_YELLOW}{m.group(4)}{_RESET}"
        if m.group(5) is not None:  # null
            return f"{_GRAY}{m.group(5)}{_RESET}"
        return m.group(0)

    return token_re.sub(_colorize_match, text)


def format_tree(data: Any, prefix: str = "", is_last: bool = True) -> str:
    """Format JSON as a box-drawing tree view.

    Args:
        data: Parsed JSON data.
        prefix: Current indentation prefix (for recursion).
        is_last: Whether this is the last item at current level.

    Returns:
        Tree-formatted string.
    """
    lines: list[str] = []
    _build_tree(data, lines, prefix, is_last, is_root=True)
    return "\n".join(lines)


def _build_tree(
    data: Any,
    lines: list[str],
    prefix: str,
    is_last: bool,
    is_root: bool = False,
    label: str = "",
) -> None:
    """Recursively build tree lines."""
    connector = "" if is_root else ("\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 ")
    child_prefix = prefix + ("" if is_root else ("    " if is_last else "\u2502   "))

    if isinstance(data, dict):
        if label:
            lines.append(f"{prefix}{connector}{_BOLD}{label}{_RESET}")
        elif not is_root:
            lines.append(f"{prefix}{connector}{_DIM}{{}}{_RESET}")

        items = list(data.items())
        for i, (key, val) in enumerate(items):
            last = i == len(items) - 1
            if isinstance(val, (dict, list)):
                _build_tree(val, lines, child_prefix, last, label=key)
            else:
                branch = "\u2514\u2500\u2500 " if last else "\u251c\u2500\u2500 "
                formatted_val = _format_leaf(val)
                lines.append(f"{child_prefix}{branch}{_WHITE_BOLD}{key}{_RESET}: {formatted_val}")

    elif isinstance(data, list):
        if label:
            lines.append(f"{prefix}{connector}{_BOLD}{label}{_RESET} [{len(data)}]")
        elif not is_root:
            lines.append(f"{prefix}{connector}{_DIM}[{len(data)}]{_RESET}")

        for i, item in enumerate(data):
            last = i == len(data) - 1
            if isinstance(item, (dict, list)):
                _build_tree(item, lines, child_prefix, last, label=f"[{i}]")
            else:
                branch = "\u2514\u2500\u2500 " if last else "\u251c\u2500\u2500 "
                formatted_val = _format_leaf(item)
                lines.append(f"{child_prefix}{branch}{_DIM}[{i}]{_RESET}: {formatted_val}")
    else:
        formatted_val = _format_leaf(data)
        if label:
            lines.append(f"{prefix}{connector}{_WHITE_BOLD}{label}{_RESET}: {formatted_val}")
        else:
            lines.append(f"{prefix}{connector}{formatted_val}")


def _format_leaf(val: Any) -> str:
    """Format a leaf value with ANSI color."""
    if val is None:
        return f"{_GRAY}null{_RESET}"
    elif isinstance(val, bool):
        return f"{_YELLOW}{str(val).lower()}{_RESET}"
    elif isinstance(val, (int, float)):
        return f"{_CYAN}{val}{_RESET}"
    elif isinstance(val, str):
        return f'{_GREEN}"{val}"{_RESET}'
    return str(val)


# ── Tabular flattening ────────────────────────────────────────────────


def flatten_to_table(
    records: list[dict],
) -> tuple[list[str], list[list[str]]]:
    """Flatten a list of dicts into headers + rows for table display.

    Collects all unique keys across records as headers. Missing values
    become empty strings.

    Args:
        records: List of JSON objects.

    Returns:
        (headers, rows) tuple.
    """
    if not records:
        return [], []

    # Collect headers preserving insertion order
    seen: dict[str, None] = {}
    for rec in records:
        if isinstance(rec, dict):
            for key in rec:
                seen[key] = None
    headers = list(seen.keys())

    rows: list[list[str]] = []
    for rec in records:
        if isinstance(rec, dict):
            row = [_stringify(rec.get(h, "")) for h in headers]
        else:
            row = [_stringify(rec)] + [""] * (len(headers) - 1)
        rows.append(row)

    return headers, rows


def _stringify(val: Any) -> str:
    """Convert a value to a display string."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return str(val)


# ── Data extraction for plotting ──────────────────────────────────────


def _normalize_path(path: str) -> str:
    """Normalize a field path: add leading dot if missing.

    For CSV data, users pass plain column names like 'score'.
    For JSON data, users pass dot-paths like '.data.val'.
    This normalizes both to dot-path form.
    """
    if not path:
        return path
    if not path.startswith(".") and not path.startswith("["):
        return f".{path}"
    return path


def extract_field_values(
    records: list[dict], path: str
) -> list[float]:
    """Extract numeric values from records using a field name or dot-path.

    Args:
        records: List of dicts.
        path: Dot-path to a numeric field (e.g. '.latency') or plain
            column name (e.g. 'score').

    Returns:
        List of float values (skips non-numeric).

    Raises:
        ValueError: If no numeric values found.
    """
    normalized = _normalize_path(path)
    values: list[float] = []
    segments = _parse_path(normalized)

    for rec in records:
        try:
            val = _resolve(rec, segments)
            values.append(float(val))
        except (KeyError, IndexError, TypeError, ValueError):
            continue

    if not values:
        from dapple.extras.common import available_fields
        fields = available_fields(records)
        hint = f" Available fields: {', '.join(fields)}" if fields else ""
        raise ValueError(f"No numeric values found at path '{path}'.{hint}")

    return values


def extract_field_categories(
    records: list[dict], path: str
) -> tuple[list[str], list[float]]:
    """Extract category labels and counts from records.

    Counts occurrences of each unique value at the given path.

    Args:
        records: List of dicts.
        path: Dot-path or plain column name.

    Returns:
        (labels, counts) tuple sorted by count descending.

    Raises:
        ValueError: If no values found.
    """
    normalized = _normalize_path(path)
    raw_values: list[str] = []
    segments = _parse_path(normalized)

    for rec in records:
        try:
            val = _resolve(rec, segments)
            raw_values.append(str(val))
        except (KeyError, IndexError, TypeError):
            continue

    if not raw_values:
        from dapple.extras.common import available_fields
        fields = available_fields(records)
        hint = f" Available fields: {', '.join(fields)}" if fields else ""
        raise ValueError(f"No values found at path '{path}'.{hint}")

    counts = Counter(raw_values)
    sorted_items = counts.most_common()
    labels = [item[0] for item in sorted_items]
    counts_list = [float(item[1]) for item in sorted_items]

    return labels, counts_list
