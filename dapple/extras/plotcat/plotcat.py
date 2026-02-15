"""plotcat - Faceted data plots.

Groups data by a facet column and renders a chart per group in a grid.
"""

from __future__ import annotations

import csv
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Literal, TextIO


def _read_data(path: Path) -> list[dict]:
    """Read CSV or JSONL file into a list of dicts."""
    suffix = path.suffix.lower()
    text = path.read_text()

    if suffix in (".json", ".jsonl"):
        records = []
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        # If the whole thing is a JSON array
        if not records and text.strip().startswith("["):
            records = json.loads(text)
        return records
    else:
        # CSV/TSV
        reader = csv.DictReader(StringIO(text))
        return list(reader)


def _extract_numeric(records: list[dict], field: str) -> list[float]:
    """Extract numeric values from a field."""
    values = []
    for rec in records:
        val = rec.get(field)
        if val is not None:
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                pass
    return values


def _extract_categories(records: list[dict], field: str) -> tuple[list[str], list[float]]:
    """Count categories in a field."""
    counts: dict[str, int] = {}
    for rec in records:
        val = str(rec.get(field, ""))
        counts[val] = counts.get(val, 0) + 1
    labels = list(counts.keys())
    values = [float(c) for c in counts.values()]
    return labels, values


def plotcat(
    data_path: str | Path,
    *,
    facet: str,
    plot: Literal["line", "bar", "spark", "histogram"] = "line",
    x: str | None = None,
    y: str | None = None,
    cols: int = 3,
    width: int | None = None,
    height: int = 10,
    renderer: str = "braille",
    dest: TextIO | None = None,
) -> None:
    """Render faceted data plots in a grid.

    Args:
        data_path: Path to CSV or JSONL file.
        facet: Column/field to group by.
        plot: Chart type.
        x: X-axis field (ignored for bar/histogram).
        y: Y-axis field (required for line/spark).
        cols: Grid columns.
        width: Total output width in characters.
        height: Chart height in characters.
        renderer: Renderer name.
        dest: Output stream.
    """
    from dapple.extras.common import get_renderer
    from dapple.extras.vizlib import pixel_dimensions
    from dapple.extras.vizlib.charts import (
        bar_chart,
        histogram as hist_chart,
        line_plot,
        sparkline,
    )
    from dapple.extras.vizlib.colors import COLOR_PALETTE
    from dapple.layout import Frame, Grid, terminal_columns

    output = dest or sys.stdout
    rend = get_renderer(renderer)
    total_width = width or terminal_columns()

    # Read data
    records = _read_data(Path(data_path))
    if not records:
        print("Error: No data found", file=sys.stderr)
        return

    # Group by facet
    groups: dict[str, list[dict]] = {}
    for rec in records:
        key = str(rec.get(facet, "unknown"))
        groups.setdefault(key, []).append(rec)

    # Calculate cell dimensions
    cell_w = max(1, (total_width - (cols - 1)) // cols)
    px_w, px_h = pixel_dimensions(rend, cell_w, height)

    # Build frames
    frames = []
    for i, (group_name, group_records) in enumerate(sorted(groups.items())):
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        if plot == "line":
            field = y or (x or list(group_records[0].keys())[0])
            values = _extract_numeric(group_records, field)
            if not values:
                continue
            canvas = line_plot(values, width=px_w, height=px_h, color=color)
        elif plot == "spark":
            field = y or (x or list(group_records[0].keys())[0])
            values = _extract_numeric(group_records, field)
            if not values:
                continue
            canvas = sparkline(values, width=px_w, height=px_h, color=color)
        elif plot == "bar":
            field = y or (x or list(group_records[0].keys())[0])
            labels, counts = _extract_categories(group_records, field)
            canvas = bar_chart(labels, counts, width=px_w, height=px_h, color=color)
        elif plot == "histogram":
            field = y or (x or list(group_records[0].keys())[0])
            values = _extract_numeric(group_records, field)
            if not values:
                continue
            canvas = hist_chart(values, width=px_w, height=px_h, color=color)
        else:
            continue

        frames.append(Frame(canvas=canvas, title=group_name))

    if not frames:
        print("Error: No plottable data found", file=sys.stderr)
        return

    # Arrange into grid
    rows = []
    for i in range(0, len(frames), cols):
        rows.append(frames[i:i + cols])

    grid = Grid(rows, width=total_width)
    grid.render(rend, dest=output)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="plotcat",
        description="Faceted data plots in the terminal",
    )
    parser.add_argument("data", type=Path, help="CSV or JSONL file")
    parser.add_argument(
        "--facet", required=True,
        help="Column to group by",
    )
    parser.add_argument(
        "--plot", choices=["line", "bar", "spark", "histogram"], default="line",
        help="Chart type (default: line)",
    )
    parser.add_argument("-x", help="X-axis field")
    parser.add_argument("-y", help="Y-axis field")
    parser.add_argument(
        "--cols", type=int, default=3,
        help="Grid columns (default: 3)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters",
    )
    parser.add_argument(
        "-H", "--height", type=int, default=10,
        help="Chart height in characters (default: 10)",
    )
    parser.add_argument(
        "-r", "--renderer", default="braille",
        help="Renderer (default: braille)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file",
    )

    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: File not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    dest = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        plotcat(
            args.data,
            facet=args.facet,
            plot=args.plot,
            x=args.x,
            y=args.y,
            cols=args.cols,
            width=args.width,
            height=args.height,
            renderer=args.renderer,
            dest=dest,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if args.output:
            dest.close()


if __name__ == "__main__":
    main()
