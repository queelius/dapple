"""dashcat - YAML-driven terminal dashboard.

Renders a grid of charts from a YAML layout specification.
"""

from __future__ import annotations

import csv
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any, TextIO


def _load_data(source: str, query: str | None = None) -> list[float]:
    """Load numeric data from a file, optionally extracting a field."""
    path = Path(source)
    if not path.exists():
        return []

    text = path.read_text()
    suffix = path.suffix.lower()

    # Parse the data
    records: list[dict] = []
    if suffix in (".json", ".jsonl"):
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        if not records and text.strip().startswith("["):
            try:
                records = json.loads(text)
            except json.JSONDecodeError:
                pass
    else:
        reader = csv.DictReader(StringIO(text))
        records = list(reader)

    if not records:
        return []

    # Extract field
    field = query.lstrip(".") if query else None
    if field:
        values = []
        for rec in records:
            val = rec.get(field)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        return values

    # Try to extract first numeric field
    if records and isinstance(records[0], dict):
        for key in records[0]:
            values = []
            for rec in records:
                try:
                    values.append(float(rec.get(key, "")))
                except (ValueError, TypeError):
                    break
            else:
                if values:
                    return values

    return []


def _load_category_data(
    source: str, x: str | None, y: str | None,
) -> tuple[list[str], list[float]]:
    """Load category data for bar charts."""
    path = Path(source)
    if not path.exists():
        return [], []

    text = path.read_text()
    suffix = path.suffix.lower()

    records: list[dict] = []
    if suffix in (".json", ".jsonl"):
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    else:
        reader = csv.DictReader(StringIO(text))
        records = list(reader)

    if not records:
        return [], []

    x_field = x or list(records[0].keys())[0]
    y_field = y

    if y_field:
        labels = [str(r.get(x_field, "")) for r in records]
        values = []
        for r in records:
            try:
                values.append(float(r.get(y_field, 0)))
            except (ValueError, TypeError):
                values.append(0)
        return labels, values

    # Count categories
    counts: dict[str, int] = {}
    for r in records:
        key = str(r.get(x_field, ""))
        counts[key] = counts.get(key, 0) + 1
    return list(counts.keys()), [float(c) for c in counts.values()]


def dashcat(
    layout_path: str | Path,
    *,
    width: int | None = None,
    renderer: str = "braille",
    height: int = 8,
    grayscale: bool = False,
    no_color: bool = False,
    dest: TextIO | None = None,
) -> None:
    """Render a dashboard from a YAML layout file.

    Args:
        layout_path: Path to the YAML layout file.
        width: Total output width in characters.
        renderer: Renderer name.
        height: Default chart height in characters.
        dest: Output stream.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for dashcat. Install with: pip install dapple[dashcat]"
        )

    from dapple.extras.common import get_renderer
    from dapple.extras.vizlib import pixel_dimensions
    from dapple.extras.vizlib.charts import (
        bar_chart,
        heatmap,
        histogram,
        line_plot,
        sparkline,
    )
    from dapple.extras.vizlib.colors import COLOR_PALETTE
    from dapple.layout import Frame, Grid, terminal_columns

    output = dest or sys.stdout
    rend = get_renderer(renderer, grayscale=grayscale, no_color=no_color)
    total_width = width or terminal_columns()

    # Load layout
    path = Path(layout_path)
    layout = yaml.safe_load(path.read_text())

    if not isinstance(layout, dict) or "rows" not in layout:
        print("Error: Layout must have a 'rows' key", file=sys.stderr)
        return

    grid_rows: list[list[Frame]] = []

    for row_spec in layout["rows"]:
        cells_spec = row_spec.get("cells", [])
        if not cells_spec:
            continue

        cell_w = max(1, (total_width - (len(cells_spec) - 1)) // len(cells_spec))
        cell_h = row_spec.get("height", height)
        px_w, px_h = pixel_dimensions(rend, cell_w, cell_h)

        frames: list[Frame] = []
        for i, cell in enumerate(cells_spec):
            chart_type = cell.get("type", "sparkline")
            source = cell.get("source", "")
            query = cell.get("query")
            title = cell.get("title", "")
            color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

            if chart_type == "sparkline":
                values = _load_data(source, query)
                if not values:
                    continue
                canvas = sparkline(values, width=px_w, height=px_h, color=color)
            elif chart_type == "line_plot":
                values = _load_data(source, query)
                if not values:
                    continue
                canvas = line_plot(values, width=px_w, height=px_h, color=color)
            elif chart_type == "bar_chart":
                x_field = cell.get("x")
                y_field = cell.get("y")
                labels, values = _load_category_data(source, x_field, y_field)
                if not labels:
                    continue
                canvas = bar_chart(labels, values, width=px_w, height=px_h, color=color)
            elif chart_type == "histogram":
                values = _load_data(source, query)
                if not values:
                    continue
                canvas = histogram(values, width=px_w, height=px_h, color=color)
            elif chart_type == "heatmap":
                values = _load_data(source, query)
                if not values:
                    continue
                # Reshape into rows for heatmap
                cols_count = cell.get("cols", 10)
                grid_data = []
                for j in range(0, len(values), cols_count):
                    grid_data.append(values[j:j + cols_count])
                canvas = heatmap(grid_data, width=px_w, height=px_h)
            else:
                continue

            frames.append(Frame(canvas=canvas, title=title))

        if frames:
            grid_rows.append(frames)

    if not grid_rows:
        print("Error: No charts could be rendered", file=sys.stderr)
        return

    grid = Grid(grid_rows, width=total_width)
    grid.render(rend, dest=output)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="dashcat",
        description="YAML-driven terminal dashboard",
    )
    parser.add_argument("layout", type=Path, help="YAML layout file")
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters",
    )
    parser.add_argument(
        "-r", "--renderer", default="braille",
        help="Renderer (default: braille)",
    )
    parser.add_argument(
        "-H", "--height", type=int, default=8,
        help="Default chart height in characters (default: 8)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file",
    )

    from dapple.extras.common import add_color_args
    add_color_args(parser)

    args = parser.parse_args()

    if not args.layout.exists():
        print(f"Error: File not found: {args.layout}", file=sys.stderr)
        sys.exit(1)

    dest = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        dashcat(
            args.layout,
            width=args.width,
            renderer=args.renderer,
            height=args.height,
            grayscale=args.grayscale,
            no_color=args.no_color,
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
