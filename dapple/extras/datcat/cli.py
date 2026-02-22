"""CLI entry point for datcat — terminal data viewer (JSON, JSONL, CSV, TSV)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterator, TextIO

from dapple.extras.common import unescape_delimiter
from dapple.extras.datcat.datcat import (
    detect_format,
    dot_path_query,
    extract_field_categories,
    extract_field_values,
    flatten_to_table,
    format_json,
    format_tree,
    read_csv,
    read_json,
    select_columns,
    sort_records,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datcat",
        description="Terminal data viewer for JSON, JSONL, CSV, and TSV with visualization modes.",
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="Data file(s) to display (reads stdin if omitted)",
    )
    parser.add_argument(
        "-q", "--query",
        metavar="PATH",
        help="Dot-path query (e.g. .database.host) — JSON/JSONL only",
    )

    # Display mode options
    display_group = parser.add_argument_group("display options")
    display_group.add_argument(
        "--table",
        action="store_true",
        help="Flatten JSONL records to a table (CSV/TSV always shown as table)",
    )
    display_group.add_argument(
        "--tree",
        action="store_true",
        help="Show tree view with box-drawing characters (default for JSON)",
    )
    display_group.add_argument(
        "--json",
        action="store_true",
        help="Show syntax-colored JSON instead of tree",
    )
    display_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable syntax coloring",
    )
    display_group.add_argument(
        "--grayscale",
        action="store_true",
        help="Force grayscale chart output",
    )
    display_group.add_argument(
        "--cycle-color",
        action="store_true",
        help="Color each column with a rotating palette instead of type-based coloring (table mode)",
    )
    display_group.add_argument(
        "--head",
        type=int,
        metavar="N",
        dest="head_n",
        help="Show first N records/rows",
    )
    display_group.add_argument(
        "--tail",
        type=int,
        metavar="N",
        dest="tail_n",
        help="Show last N records/rows",
    )

    # CSV-specific options
    csv_group = parser.add_argument_group("CSV/TSV options")
    csv_group.add_argument(
        "-d", "--delimiter",
        help="Explicit delimiter (default: auto-detect)",
    )
    csv_group.add_argument(
        "--no-header",
        action="store_true",
        help="Data has no header row (CSV/TSV only)",
    )
    csv_group.add_argument(
        "--sort",
        metavar="COLUMN",
        help="Sort by column",
    )
    csv_group.add_argument(
        "--cols",
        help="Comma-separated column names to select",
    )
    csv_group.add_argument(
        "--desc",
        action="store_true",
        help="Sort descending (use with --sort)",
    )

    # Plot mode (mutually exclusive)
    plot_group = parser.add_argument_group("plot modes (mutually exclusive)")
    plot_mx = plot_group.add_mutually_exclusive_group()
    plot_mx.add_argument(
        "--plot",
        metavar="PATH",
        help="Line plot of a numeric field (dot-path or column name)",
    )
    plot_mx.add_argument(
        "--spark",
        metavar="PATH",
        help="Sparkline of a numeric field (dot-path or column name)",
    )
    plot_mx.add_argument(
        "--bar",
        metavar="PATH",
        help="Bar chart of category counts (dot-path or column name)",
    )
    plot_mx.add_argument(
        "--histogram",
        metavar="PATH",
        help="Histogram of a numeric field (dot-path or column name)",
    )
    plot_mx.add_argument(
        "--heatmap",
        metavar="COLUMNS",
        help="Heatmap of multiple numeric columns (comma-separated)",
    )

    # Plot options
    plot_opts = parser.add_argument_group("plot options")
    plot_opts.add_argument(
        "-r", "--renderer",
        default="braille",
        help="Renderer: braille (default), quadrants, sextants, ascii, sixel, kitty",
    )
    plot_opts.add_argument(
        "-w", "--width",
        type=int,
        help="Chart width in terminal characters",
    )
    plot_opts.add_argument(
        "-H", "--height",
        type=int,
        help="Chart height in terminal characters",
    )
    plot_opts.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Write output to file instead of stdout",
    )
    plot_opts.add_argument(
        "--color",
        type=str,
        help="Chart color (name or #hex, e.g. green, #ff0000)",
    )

    return parser


def _get_inputs(args: argparse.Namespace) -> Iterator[tuple[str, str | None, str | None]]:
    """Yield (name, text_content, error) tuples for each input source.

    If error is not None, text_content will be None and error contains the message.
    """
    if args.files:
        for path in args.files:
            path_obj = Path(path)
            if not path_obj.exists():
                yield (str(path), None, f"{path}: File not found")
            else:
                try:
                    with open(path, "r") as f:
                        yield (str(path), f.read(), None)
                except Exception as e:
                    yield (str(path), None, f"{path}: {e}")
    elif not sys.stdin.isatty():
        yield ("<stdin>", sys.stdin.read(), None)
    else:
        print("datcat: no input (provide a file or pipe data via stdin)", file=sys.stderr)
        sys.exit(1)


def _is_plot_mode(args: argparse.Namespace) -> bool:
    return any((args.plot, args.spark, args.bar, args.histogram,
                getattr(args, "heatmap", None)))


_BOOL_STRINGS = {"true", "false"}
_NULL_STRINGS = {"", "null", "none"}

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
    """Return ANSI color code based on value type."""
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


def _format_table_output(
    headers: list[str],
    rows: list[list[str]],
    cycle_colors: bool = False,
) -> str:
    """Format headers + rows as an aligned text table with ANSI styling."""
    if not headers:
        return ""

    BOLD = "\033[1m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    lines: list[str] = []

    header_cells = []
    for i, h in enumerate(headers):
        if cycle_colors:
            color = _COLUMN_COLORS[i % len(_COLUMN_COLORS)]
            header_cells.append(f"{BOLD}{color}{h:<{widths[i]}}{RESET}")
        else:
            header_cells.append(f"{BOLD}{CYAN}{h:<{widths[i]}}{RESET}")
    lines.append("  ".join(header_cells))

    sep_cells = [DIM + "\u2500" * w + RESET for w in widths]
    lines.append("  ".join(sep_cells))

    for row in rows:
        cells = []
        for i in range(len(headers)):
            w = widths[i]
            val = row[i] if i < len(row) else ""

            if cycle_colors:
                color = _COLUMN_COLORS[i % len(_COLUMN_COLORS)]
            else:
                color = _type_color(val)

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


def _read_input(
    text: str, name: str, args: argparse.Namespace,
) -> tuple[object, str]:
    """Parse text and return (data, fmt).

    Returns:
        (data, fmt) where data is parsed data and fmt is "json", "jsonl", or "csv".
    """
    filename = name if name != "<stdin>" else None
    fmt = detect_format(text, filename=filename)

    if fmt == "csv":
        delimiter = unescape_delimiter(args.delimiter) if args.delimiter else None
        records = read_csv(
            text,
            delimiter=delimiter,
            has_header=not args.no_header,
        )
        return records, "csv"
    else:
        data = read_json(text)
        return data, fmt


def _run_display_mode(data, fmt: str, args: argparse.Namespace, dest: TextIO) -> None:
    """Handle display/query mode output."""
    if fmt == "csv":
        # CSV data is always list[dict] — show as table
        records = data

        # Apply column selection
        if args.cols:
            col_names = [c.strip() for c in args.cols.split(",")]
            records = select_columns(records, col_names)

        # Apply sorting
        if args.sort:
            records = sort_records(records, args.sort, reverse=args.desc)

        # Apply head/tail
        if args.head_n is not None:
            records = records[:args.head_n]
        elif args.tail_n is not None:
            records = records[-args.tail_n:]

        headers, rows = flatten_to_table(records)
        output = _format_table_output(headers, rows, cycle_colors=args.cycle_color)
        dest.write(output + "\n")
        return

    # JSON/JSONL path
    # Apply head/tail for list data
    if isinstance(data, list):
        if args.head_n is not None:
            data = data[:args.head_n]
        elif args.tail_n is not None:
            data = data[-args.tail_n:]

    # Apply dot-path query
    if args.query:
        data = dot_path_query(data, args.query)

    # Choose display format (default: tree)
    if args.table and isinstance(data, list):
        headers, rows = flatten_to_table(data)
        output = _format_table_output(headers, rows, cycle_colors=args.cycle_color)
    elif args.json:
        output = format_json(data, colorize=not args.no_color)
    else:
        output = format_tree(data)

    dest.write(output + "\n")


def _run_plot_mode(data, fmt: str, args: argparse.Namespace, dest: TextIO) -> None:
    """Render a chart from data using vizlib or text charts."""
    if fmt == "csv":
        records = data
        # Apply column selection before plotting
        if args.cols:
            col_names = [c.strip() for c in args.cols.split(",")]
            records = select_columns(records, col_names)
        # Apply sorting before plotting
        if args.sort:
            records = sort_records(records, args.sort, reverse=args.desc)
    else:
        records = data
        if not isinstance(records, list):
            raise ValueError("plot mode requires JSONL input (array of records)")

    # Text chart modes (bar, spark) — use textchart for inline display
    if args.bar:
        from dapple.textchart import text_bar_chart
        labels, values = extract_field_categories(records, args.bar)
        dest.write(text_bar_chart(labels, values, width=args.width, title=args.bar) + "\n")
        return

    if args.spark:
        # For CSV data, use text sparkline; for JSON, use vizlib sparkline
        if fmt == "csv":
            from dapple.textchart import text_sparkline
            labels, values = extract_field_categories(records, args.spark)
            dest.write(text_sparkline(labels, values, title=args.spark) + "\n")
            return

    # Bitmap chart modes — require vizlib / numpy
    from dapple.extras.vizlib import get_renderer, get_terminal_size, pixel_dimensions
    from dapple.extras.vizlib.charts import heatmap as heatmap_chart
    from dapple.extras.vizlib.charts import histogram, line_plot, sparkline
    from dapple.extras.vizlib.colors import COLOR_PALETTE, parse_color

    # Parse --color if provided
    color = None
    if args.color:
        color = parse_color(args.color)

    renderer = get_renderer(
        args.renderer,
        grayscale=args.grayscale,
        no_color=args.no_color,
    )
    term_cols, term_lines = get_terminal_size()
    char_w = args.width or min(term_cols // 2, 60)
    char_h = args.height or min(10, max(6, term_lines // 5))
    px_w, px_h = pixel_dimensions(renderer, char_w, char_h)
    line_thick = max(1, min(3, px_h // 10))

    if args.spark:
        values = extract_field_values(records, args.spark)
        canvas = sparkline(values, width=px_w, height=px_h, color=color, thickness=line_thick)
    elif args.plot:
        # Support comma-separated field paths for multi-series
        field_paths = [p.strip() for p in args.plot.split(",")]
        primary_values = extract_field_values(records, field_paths[0])
        if len(field_paths) > 1:
            extra_series = []
            for i, fp in enumerate(field_paths[1:]):
                s_values = extract_field_values(records, fp)
                s_color = COLOR_PALETTE[(i + 1) % len(COLOR_PALETTE)]
                extra_series.append((s_values, s_color))
            canvas = line_plot(
                primary_values, width=px_w, height=px_h, color=color, series=extra_series,
                thickness=line_thick,
            )
        else:
            canvas = line_plot(primary_values, width=px_w, height=px_h, color=color, thickness=line_thick)
    elif args.histogram:
        values = extract_field_values(records, args.histogram)
        canvas = histogram(values, width=px_w, height=px_h, color=color)
    elif getattr(args, "heatmap", None):
        col_names = [c.strip() for c in args.heatmap.split(",")]
        grid: list[list[float]] = []
        for col in col_names:
            grid.append(extract_field_values(records, col))
        canvas = heatmap_chart(grid, width=px_w, height=px_h)
    else:
        return

    canvas.out(renderer, dest=dest)


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    errors: list[str] = []
    exit_code = 0
    first_file = True
    dest = open(args.output, "w") if args.output else sys.stdout

    try:
        for name, text, error in _get_inputs(args):
            if error:
                errors.append(error)
                continue

            try:
                data, fmt = _read_input(text, name, args)

                # Print separator for multiple files
                if args.files and len(args.files) > 1:
                    if not first_file:
                        dest.write("\n")
                    dest.write(f"{'='*60}\n")
                    dest.write(f"  {name}\n")
                    dest.write(f"{'='*60}\n\n")
                    first_file = False

                if _is_plot_mode(args):
                    _run_plot_mode(data, fmt, args, dest)
                else:
                    _run_display_mode(data, fmt, args, dest)
            except Exception as e:
                errors.append(f"{name}: {e}")
                continue
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if dest is not sys.stdout:
            dest.close()

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
