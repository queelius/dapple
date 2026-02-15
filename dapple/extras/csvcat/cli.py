"""CLI entry point for csvcat — terminal CSV/TSV viewer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterator, TextIO

from dapple.extras.common import unescape_delimiter
from dapple.extras.csvcat.csvcat import (
    CsvData,
    extract_categories,
    extract_numeric,
    format_table,
    head,
    read_csv,
    select_columns,
    sort_by,
    tail,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csvcat",
        description="Terminal CSV/TSV viewer with visualization modes.",
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="CSV/TSV file(s) to display (reads stdin if omitted)",
    )

    # Table mode options
    table_group = parser.add_argument_group("table options")
    table_group.add_argument(
        "--cols",
        help="Comma-separated column names to select",
    )
    table_group.add_argument(
        "--sort",
        metavar="COLUMN",
        help="Sort by column",
    )
    table_group.add_argument(
        "--desc",
        action="store_true",
        help="Sort descending (use with --sort)",
    )
    table_group.add_argument(
        "--head",
        type=int,
        metavar="N",
        dest="head_n",
        help="Show first N rows",
    )
    table_group.add_argument(
        "--tail",
        type=int,
        metavar="N",
        dest="tail_n",
        help="Show last N rows",
    )
    table_group.add_argument(
        "--no-header",
        action="store_true",
        help="Data has no header row",
    )
    table_group.add_argument(
        "-d", "--delimiter",
        help="Explicit delimiter (default: auto-detect)",
    )
    table_group.add_argument(
        "--cycle-color",
        action="store_true",
        help="Color each column with a rotating palette instead of type-based coloring",
    )

    # Plot mode (mutually exclusive)
    plot_group = parser.add_argument_group("plot modes (mutually exclusive)")
    plot_mx = plot_group.add_mutually_exclusive_group()
    plot_mx.add_argument(
        "--plot",
        metavar="COLUMN",
        help="Line plot of a numeric column",
    )
    plot_mx.add_argument(
        "--spark",
        metavar="COLUMN",
        help="Sparkline of a numeric column",
    )
    plot_mx.add_argument(
        "--bar",
        metavar="COLUMN",
        help="Bar chart of category counts",
    )
    plot_mx.add_argument(
        "--histogram",
        metavar="COLUMN",
        help="Histogram of a numeric column",
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

    return parser


def _get_inputs(args: argparse.Namespace) -> Iterator[tuple[str, TextIO | None, str | None]]:
    """Yield (name, file_handle, error) tuples for each input source.

    If error is not None, file_handle will be None and error contains the message.
    """
    if args.files:
        for path in args.files:
            path_obj = Path(path)
            if not path_obj.exists():
                yield (str(path), None, f"{path}: File not found")
            else:
                try:
                    yield (str(path), open(path, "r"), None)
                except Exception as e:
                    yield (str(path), None, f"{path}: {e}")
    elif not sys.stdin.isatty():
        yield ("<stdin>", sys.stdin, None)
    else:
        print("csvcat: no input (provide a file or pipe data via stdin)", file=sys.stderr)
        sys.exit(1)


def _is_plot_mode(args: argparse.Namespace) -> bool:
    return any((args.plot, args.spark, args.bar, args.histogram, args.heatmap))


def _run_table_mode(data: CsvData, args: argparse.Namespace, dest: TextIO) -> None:
    """Apply table transformations and print."""
    if args.cols:
        col_names = [c.strip() for c in args.cols.split(",")]
        data = select_columns(data, col_names)

    if args.sort:
        data = sort_by(data, args.sort, reverse=args.desc)

    if args.head_n is not None:
        data = head(data, args.head_n)
    elif args.tail_n is not None:
        data = tail(data, args.tail_n)

    output = format_table(data, cycle_colors=args.cycle_color)
    dest.write(output + "\n")


def _run_plot_mode(data: CsvData, args: argparse.Namespace, dest: TextIO) -> None:
    """Render a chart from CSV data using vizlib."""
    from dapple.extras.vizlib import get_renderer, get_terminal_size, pixel_dimensions
    from dapple.extras.vizlib.charts import bar_chart, heatmap, histogram, line_plot, sparkline

    renderer = get_renderer(args.renderer)
    term_cols, term_lines = get_terminal_size()
    char_w = args.width or term_cols
    char_h = args.height or max(10, term_lines // 3)
    px_w, px_h = pixel_dimensions(renderer, char_w, char_h)

    if args.spark:
        values = extract_numeric(data, args.spark)
        canvas = sparkline(values, width=px_w, height=px_h)
    elif args.plot:
        values = extract_numeric(data, args.plot)
        canvas = line_plot(values, width=px_w, height=px_h)
    elif args.bar:
        labels, counts = extract_categories(data, args.bar)
        canvas = bar_chart(labels, counts, width=px_w, height=px_h)
    elif args.histogram:
        values = extract_numeric(data, args.histogram)
        canvas = histogram(values, width=px_w, height=px_h)
    elif args.heatmap:
        col_names = [c.strip() for c in args.heatmap.split(",")]
        grid: list[list[float]] = []
        for col in col_names:
            grid.append(extract_numeric(data, col))
        canvas = heatmap(grid, width=px_w, height=px_h)
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
        for name, source, error in _get_inputs(args):
            if error:
                errors.append(error)
                continue

            try:
                delimiter = unescape_delimiter(args.delimiter) if args.delimiter else None
                data = read_csv(
                    source,
                    delimiter=delimiter,
                    has_header=not args.no_header,
                )

                # Print separator for multiple files
                if args.files and len(args.files) > 1:
                    if not first_file:
                        dest.write("\n")
                    dest.write(f"{'='*60}\n")
                    dest.write(f"  {name}\n")
                    dest.write(f"{'='*60}\n\n")
                    first_file = False

                if _is_plot_mode(args):
                    _run_plot_mode(data, args, dest)
                else:
                    _run_table_mode(data, args, dest)
            except Exception as e:
                errors.append(f"{name}: {e}")
                continue
            finally:
                if source is not sys.stdin:
                    source.close()
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
