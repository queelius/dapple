#!/usr/bin/env python3
"""funcat - Terminal function plotter with selectable renderers.

Supports chaining multiple functions via JSON piping:
    funcat "sin(x)" --json | funcat "cos(x)" --color red --json | funcat "x/3"
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys

import numpy as np

from dapple import braille, quadrants, sextants, ascii, sixel, kitty
from dapple.canvas import Canvas
from dapple.renderers import Renderer

# Available renderers mapping (used by tests + --renderer choices)
RENDERERS: dict[str, Renderer] = {
    'braille': braille,
    'quadrants': quadrants,
    'sextants': sextants,
    'ascii': ascii,
    'sixel': sixel,
    'kitty': kitty,
}


SAFE_NAMESPACE = {
    'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
    'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
    'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
    'exp': np.exp, 'log': np.log, 'log10': np.log10, 'log2': np.log2,
    'sqrt': np.sqrt, 'abs': np.abs, 'floor': np.floor, 'ceil': np.ceil,
    'pi': np.pi, 'e': np.e,
}

# Default x range for function plots (-2π to 2π)
DEFAULT_X_MIN = -2 * np.pi
DEFAULT_X_MAX = 2 * np.pi

# Default t range for parametric plots (0 to 2π)
DEFAULT_T_MIN = 0.0
DEFAULT_T_MAX = 2 * np.pi

# Default font aspect ratio (character height / character width)
# Most terminal fonts are about 2x as tall as they are wide
DEFAULT_FONT_ASPECT = 2.0

# Named colors (RGB values 0-1) - bright, saturated colors
NAMED_COLORS = {
    'cyan': (0.0, 0.8, 1.0),
    'red': (1.0, 0.2, 0.2),
    'green': (0.2, 1.0, 0.2),
    'yellow': (1.0, 1.0, 0.0),
    'magenta': (1.0, 0.0, 1.0),
    'orange': (1.0, 0.6, 0.0),
    'blue': (0.0, 0.5, 1.0),
    'pink': (1.0, 0.4, 0.8),
    'white': (1.0, 1.0, 1.0),
    'gray': (0.5, 0.5, 0.5),
}

# Color palette for auto-cycling (same order as before)
COLOR_PALETTE = [
    NAMED_COLORS['cyan'],
    NAMED_COLORS['red'],
    NAMED_COLORS['green'],
    NAMED_COLORS['yellow'],
    NAMED_COLORS['magenta'],
    NAMED_COLORS['orange'],
    NAMED_COLORS['blue'],
    NAMED_COLORS['pink'],
]

AXIS_COLOR = (0.5, 0.5, 0.5)  # Gray for axes


def parse_color(color_str: str) -> tuple[float, float, float]:
    """Parse color name or #RRGGBB hex."""
    if color_str.startswith('#'):
        # Parse hex
        hex_str = color_str[1:]
        if len(hex_str) == 3:
            # Short form #RGB -> #RRGGBB
            hex_str = ''.join(c * 2 for c in hex_str)
        if len(hex_str) != 6:
            raise ValueError(f"Invalid hex color: {color_str}")
        r = int(hex_str[0:2], 16) / 255
        g = int(hex_str[2:4], 16) / 255
        b = int(hex_str[4:6], 16) / 255
        return (r, g, b)

    color_lower = color_str.lower()
    if color_lower not in NAMED_COLORS:
        valid = ', '.join(sorted(NAMED_COLORS.keys()))
        raise ValueError(f"Unknown color '{color_str}'. Valid colors: {valid}")
    return NAMED_COLORS[color_lower]


def evaluate_expression(expr: str, x: np.ndarray) -> np.ndarray:
    """Safely evaluate a mathematical expression."""
    namespace = {**SAFE_NAMESPACE, 'x': x}
    result = eval(expr, {"__builtins__": {}}, namespace)
    # Ensure result is always an array with same shape as x
    return np.broadcast_to(result, x.shape).astype(np.float64)


def plot_function_to_mask(
    expr: str,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    width: int,
    height: int,
    samples: int | None = None,
) -> np.ndarray:
    """Generate a boolean mask of where the function curve passes."""
    samples = samples or width
    x = np.linspace(x_min, x_max, samples)
    y = evaluate_expression(expr, x)

    # Handle invalid values
    y = np.where(np.isfinite(y), y, np.nan)

    # Create mask
    mask = np.zeros((height, width), dtype=bool)

    # Map y values to pixel rows (flip because row 0 is top)
    y_range = y_max - y_min
    if y_range == 0:
        y_range = 1.0
    y_normalized = (y - y_min) / y_range
    pixel_rows = ((1 - y_normalized) * (height - 1)).astype(int)

    # Map x sample indices to pixel columns
    pixel_cols = np.linspace(0, width - 1, samples).astype(int)

    # Plot the function curve
    for i, (col, row) in enumerate(zip(pixel_cols, pixel_rows)):
        if np.isfinite(row) and 0 <= row < height and 0 <= col < width:
            mask[row, col] = True

    return mask


def compute_y_range(expr: str, x_min: float, x_max: float, samples: int) -> tuple[float, float]:
    """Compute the y range for a function."""
    x = np.linspace(x_min, x_max, samples)
    y = evaluate_expression(expr, x)
    y = np.where(np.isfinite(y), y, np.nan)
    valid_y = y[np.isfinite(y)]

    if len(valid_y) == 0:
        raise ValueError(f"Function '{expr}' produces no valid values in range")

    y_min = float(valid_y.min())
    y_max = float(valid_y.max())

    # Handle constant functions
    if y_max == y_min:
        y_min -= 0.5
        y_max += 0.5

    return y_min, y_max


def parse_parametric(expr: str) -> tuple[str, str]:
    """Parse 'x(t),y(t)' into (x_expr, y_expr)."""
    parts = expr.split(',', 1)
    if len(parts) != 2:
        raise ValueError(f"Parametric must be 'x(t),y(t)', got: {expr}")
    return parts[0].strip(), parts[1].strip()


def evaluate_parametric(
    x_expr: str,
    y_expr: str,
    t_min: float,
    t_max: float,
    samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate parametric expressions over a t range.

    Returns:
        (x, y) arrays of float64 values (may contain NaN/inf).

    Raises:
        ValueError: If no valid values are produced.
    """
    t = np.linspace(t_min, t_max, samples)
    namespace = {**SAFE_NAMESPACE, 't': t}
    x = eval(x_expr, {"__builtins__": {}}, namespace)
    y = eval(y_expr, {"__builtins__": {}}, namespace)

    x = np.broadcast_to(x, t.shape).astype(np.float64)
    y = np.broadcast_to(y, t.shape).astype(np.float64)

    return x, y


def compute_parametric_ranges(
    x_expr: str,
    y_expr: str,
    t_min: float,
    t_max: float,
    samples: int,
) -> tuple[float, float, float, float]:
    """Compute x and y ranges from parametric expressions.

    Returns:
        (x_min, x_max, y_min, y_max) tuple
    """
    x, y = evaluate_parametric(x_expr, y_expr, t_min, t_max, samples)

    valid = np.isfinite(x) & np.isfinite(y)
    if not np.any(valid):
        raise ValueError(f"Parametric '{x_expr},{y_expr}' produces no valid values")

    return float(x[valid].min()), float(x[valid].max()), float(y[valid].min()), float(y[valid].max())


def plot_parametric_to_mask(
    x_expr: str,
    y_expr: str,
    t_min: float,
    t_max: float,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    width: int,
    height: int,
    samples: int,
) -> np.ndarray:
    """Generate boolean mask for parametric curve."""
    x, y = evaluate_parametric(x_expr, y_expr, t_min, t_max, samples)

    mask = np.zeros((height, width), dtype=bool)

    # Handle degenerate ranges
    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range == 0:
        x_range = 1.0
    if y_range == 0:
        y_range = 1.0

    # Map to pixel coordinates
    x_norm = (x - x_min) / x_range
    y_norm = (y - y_min) / y_range
    cols = (x_norm * (width - 1)).astype(int)
    rows = ((1 - y_norm) * (height - 1)).astype(int)

    for col, row in zip(cols, rows):
        if np.isfinite(row) and np.isfinite(col):
            if 0 <= row < height and 0 <= col < width:
                mask[row, col] = True

    return mask


def draw_axes(
    bitmap: np.ndarray,
    colors: np.ndarray,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    """Draw axes on the bitmap and colors arrays (in-place)."""
    height, width = bitmap.shape

    # Y-axis at x=0 if in range
    if x_min <= 0 <= x_max:
        x_zero_col = int((0 - x_min) / (x_max - x_min) * (width - 1))
        for row in range(height):
            if bitmap[row, x_zero_col] < 0.3:
                bitmap[row, x_zero_col] = 0.3
                colors[row, x_zero_col] = AXIS_COLOR

    # X-axis at y=0 if in range
    if y_min <= 0 <= y_max:
        y_zero_row = int((1 - (0 - y_min) / (y_max - y_min)) * (height - 1))
        for col in range(width):
            if bitmap[y_zero_row, col] < 0.3:
                bitmap[y_zero_row, col] = 0.3
                colors[y_zero_row, col] = AXIS_COLOR


def read_json_input() -> dict | None:
    """Read JSON input from stdin if available."""
    if sys.stdin.isatty():
        return None

    try:
        data = sys.stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def write_json_output(
    expressions: list[dict],
    x_min: float,
    x_max: float,
    y_min: float | None,
    y_max: float | None,
) -> None:
    """Write JSON output to stdout."""
    output = {
        'expressions': expressions,
        'x_min': x_min,
        'x_max': x_max,
        'y_min': y_min,
        'y_max': y_max,
    }
    json.dump(output, sys.stdout)
    print()  # Newline after JSON


def render_all(
    expressions: list[dict],
    x_min: float | None,
    x_max: float | None,
    y_min: float | None,
    y_max: float | None,
    pixel_width: int,
    pixel_height: int,
    char_width: int,
    char_height: int,
    show_axes: bool,
    renderer: Renderer,
    font_aspect: float = DEFAULT_FONT_ASPECT,
    x_range_explicit: bool = False,
    y_range_explicit: bool = False,
) -> tuple[np.ndarray, np.ndarray, float, float, float, float, list[tuple[str, tuple[float, float, float]]]]:
    """Render all expressions to bitmap and colors arrays.

    Returns:
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries
        where legend_entries is a list of (expression, color) tuples.
    """
    default_samples = pixel_width

    # Compute combined ranges if not fully specified
    if x_min is None or x_max is None or y_min is None or y_max is None:
        all_x_min, all_x_max = float('inf'), float('-inf')
        all_y_min, all_y_max = float('inf'), float('-inf')

        for expr_cfg in expressions:
            samples = expr_cfg.get('samples') or default_samples
            try:
                if expr_cfg.get('parametric'):
                    x_expr, y_expr = parse_parametric(expr_cfg['expr'])
                    t_min = expr_cfg.get('t_min', DEFAULT_T_MIN)
                    t_max = expr_cfg.get('t_max', DEFAULT_T_MAX)
                    ex_min, ex_max, ey_min, ey_max = compute_parametric_ranges(
                        x_expr, y_expr, t_min, t_max, samples
                    )
                    all_x_min = min(all_x_min, ex_min)
                    all_x_max = max(all_x_max, ex_max)
                    all_y_min = min(all_y_min, ey_min)
                    all_y_max = max(all_y_max, ey_max)
                else:
                    # For non-parametric, use default x range if not specified
                    x_lo = x_min if x_min is not None else DEFAULT_X_MIN
                    x_hi = x_max if x_max is not None else DEFAULT_X_MAX
                    ey_min, ey_max = compute_y_range(expr_cfg['expr'], x_lo, x_hi, samples)
                    all_y_min = min(all_y_min, ey_min)
                    all_y_max = max(all_y_max, ey_max)
            except ValueError:
                continue  # Skip invalid expressions for range calculation

        if all_y_min == float('inf'):
            raise ValueError("No expressions produce valid values in range")

        # Use computed ranges where not specified
        if x_min is None:
            x_min = all_x_min
        if x_max is None:
            x_max = all_x_max
        y_min = y_min if y_min is not None else all_y_min
        y_max = y_max if y_max is not None else all_y_max

    # Handle degenerate x/y ranges
    if x_max == x_min:
        x_min -= 0.5
        x_max += 0.5
    if y_max == y_min:
        y_min -= 0.5
        y_max += 0.5

    # Apply aspect ratio correction for equal visual scale
    # Only adjust ranges that weren't explicitly specified by the user
    # For equal visual scale: x_range / y_range = (char_width / char_height) / font_aspect
    if not (x_range_explicit and y_range_explicit):
        x_range = x_max - x_min
        y_range = y_max - y_min
        target_ratio = char_width / (char_height * font_aspect)
        actual_ratio = x_range / y_range

        if actual_ratio < target_ratio and not x_range_explicit:
            # Need to expand x range (only if not explicitly set)
            new_x_range = y_range * target_ratio
            x_center = (x_min + x_max) / 2
            x_min = x_center - new_x_range / 2
            x_max = x_center + new_x_range / 2
        elif actual_ratio > target_ratio and not y_range_explicit:
            # Need to expand y range (only if not explicitly set)
            new_y_range = x_range / target_ratio
            y_center = (y_min + y_max) / 2
            y_min = y_center - new_y_range / 2
            y_max = y_center + new_y_range / 2

    # Create bitmap and colors
    bitmap = np.zeros((pixel_height, pixel_width), dtype=np.float32)
    colors = np.zeros((pixel_height, pixel_width, 3), dtype=np.float32)

    # Draw axes first (so functions draw over them)
    if show_axes:
        draw_axes(bitmap, colors, x_min, x_max, y_min, y_max)

    # Plot each expression
    color_index = 0
    legend_entries: list[tuple[str, tuple[float, float, float]]] = []
    for expr_cfg in expressions:
        expr = expr_cfg['expr']
        samples = expr_cfg.get('samples') or pixel_width

        # Determine color
        if expr_cfg.get('color'):
            color = parse_color(expr_cfg['color'])
        else:
            color = COLOR_PALETTE[color_index % len(COLOR_PALETTE)]
            color_index += 1

        # Track for legend
        legend_entries.append((expr, color))

        # Generate mask and apply
        if expr_cfg.get('parametric'):
            x_expr, y_expr = parse_parametric(expr)
            t_min = expr_cfg.get('t_min', DEFAULT_T_MIN)
            t_max = expr_cfg.get('t_max', DEFAULT_T_MAX)
            mask = plot_parametric_to_mask(
                x_expr, y_expr, t_min, t_max,
                x_min, x_max, y_min, y_max,
                pixel_width, pixel_height, samples
            )
        else:
            mask = plot_function_to_mask(
                expr, x_min, x_max, y_min, y_max, pixel_width, pixel_height, samples
            )
        bitmap[mask] = 1.0
        colors[mask] = color

        # Expand colors to fill renderer cells for better visibility
        cell_w = renderer.cell_width
        cell_h = renderer.cell_height
        for col in range(pixel_width):
            for row in range(pixel_height):
                if mask[row, col]:
                    cell_row = (row // cell_h) * cell_h
                    cell_col = (col // cell_w) * cell_w
                    for dr in range(min(cell_h, pixel_height - cell_row)):
                        for dc in range(min(cell_w, pixel_width - cell_col)):
                            r, c = cell_row + dr, cell_col + dc
                            if bitmap[r, c] < 0.5:  # Don't overwrite other functions
                                colors[r, c] = color

    return bitmap, colors, x_min, x_max, y_min, y_max, legend_entries


def print_legend(
    entries: list[tuple[str, tuple[float, float, float]]],
    no_color: bool = False,
) -> None:
    """Print colored legend line."""
    parts = []
    for expr, color in entries:
        if no_color:
            parts.append(f"-- {expr}")
        else:
            r, g, b = int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
            colored_dash = f"\033[38;2;{r};{g};{b}m──\033[0m"
            parts.append(f"{colored_dash} {expr}")
    print("  ".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='funcat',
        description='Plot mathematical functions in the terminal with selectable renderers',
        epilog='Chain multiple functions: funcat "sin(x)" --json | funcat "cos(x)" --color red\n'
               'Parametric curves: funcat -p "cos(t),sin(t)" -l\n'
               'For expressions starting with -, use: funcat -- "-2*x"',
    )
    parser.add_argument('expressions', nargs='*', help='Function(s) of x (e.g., "sin(x)", "x**2")')
    parser.add_argument('-p', '--parametric', type=str, metavar='X,Y',
                        help='Parametric function: "x(t),y(t)"')
    parser.add_argument('--xmin', type=float, default=-2*np.pi, help='X-axis minimum')
    parser.add_argument('--xmax', type=float, default=2*np.pi, help='X-axis maximum')
    parser.add_argument('--ymin', type=float, default=None, help='Y-axis minimum (auto)')
    parser.add_argument('--ymax', type=float, default=None, help='Y-axis maximum (auto)')
    parser.add_argument('--tmin', type=float, default=DEFAULT_T_MIN,
                        help=f'Parameter t minimum (default: {DEFAULT_T_MIN})')
    parser.add_argument('--tmax', type=float, default=DEFAULT_T_MAX,
                        help='Parameter t maximum (default: 2π)')
    parser.add_argument('--font-aspect', type=float, default=DEFAULT_FONT_ASPECT,
                        help=f'Terminal font aspect ratio (height/width, default: {DEFAULT_FONT_ASPECT})')
    parser.add_argument('-w', '--width', type=int, help='Width in characters')
    parser.add_argument('-H', '--height', type=int, help='Height in characters')
    parser.add_argument('--axes', action='store_true', help='Show axes')
    parser.add_argument('-j', '--json', action='store_true', help='Output JSON for chaining')
    parser.add_argument('-l', '--legend', action='store_true', help='Show legend for multiple functions')
    parser.add_argument('--color', type=str, default=None, help='Color for this function (name or #RRGGBB)')
    parser.add_argument('-n', '--nsamples', type=int, default=None, dest='samples', help='Sampling points for this function')
    parser.add_argument(
        '-r', '--renderer',
        choices=list(RENDERERS.keys()),
        default='braille',
        help='Renderer: braille (default), quadrants, sextants, ascii, sixel, kitty'
    )

    from dapple.extras.common import add_color_args
    add_color_args(parser)

    # Use parse_known_args to handle expressions starting with -
    args, remaining = parser.parse_known_args()

    # Collect all expressions from args.expressions and remaining
    all_expressions: list[str] = []
    if args.expressions:
        all_expressions.extend(e for e in args.expressions if e)
    if remaining:
        all_expressions.extend(e for e in remaining if e)

    # Track if we read stdin content (to avoid double-reading)
    stdin_content: str | None = None
    stdin_is_json = False

    # Read from stdin if no expressions provided and stdin has data
    if not all_expressions and args.parametric is None and not sys.stdin.isatty():
        try:
            stdin_content = sys.stdin.read()
            # Check if it's JSON (for chaining mode)
            stripped = stdin_content.strip()
            if stripped.startswith('{'):
                stdin_is_json = True
            else:
                # Treat as newline-separated expressions
                for line in stripped.split('\n'):
                    line = line.strip()
                    if line:
                        all_expressions.append(line)
        except OSError:
            # Can happen in test environments where stdin is captured
            pass

    # Require either expression(s) or --parametric (unless stdin was JSON for chaining)
    if not all_expressions and args.parametric is None and not stdin_is_json:
        parser.error('either expression(s) or -p/--parametric is required')

    # Auto-detect terminal size
    term = shutil.get_terminal_size(fallback=(80, 24))
    char_width = args.width or term.columns
    char_height = args.height or (term.lines - 2)

    # Effective no_color: CLI flag or NO_COLOR env var
    import os
    effective_no_color = args.no_color or "NO_COLOR" in os.environ

    # Get the selected renderer via common.get_renderer (honours NO_COLOR)
    from dapple.extras.common import get_renderer as _get_renderer
    renderer = _get_renderer(
        args.renderer,
        grayscale=args.grayscale,
        no_color=args.no_color,
    )

    # Convert to pixel dimensions using renderer's cell size
    pixel_width = char_width * renderer.cell_width
    pixel_height = char_height * renderer.cell_height

    # Try to read existing state from stdin (use cached content if available)
    prev_state = None
    if stdin_is_json and stdin_content:
        try:
            prev_state = json.loads(stdin_content)
        except json.JSONDecodeError:
            pass
    elif not stdin_content:
        # Only try reading stdin if we haven't already consumed it
        prev_state = read_json_input()

    # Track if x range was explicitly specified (not default)
    x_range_explicit = args.xmin != -2*np.pi or args.xmax != 2*np.pi
    y_range_explicit = args.ymin is not None or args.ymax is not None

    try:
        if prev_state:
            # Continue from previous state
            expressions = prev_state.get('expressions', [])
            x_min = prev_state.get('x_min', args.xmin)
            x_max = prev_state.get('x_max', args.xmax)
            y_min = prev_state.get('y_min', args.ymin)
            y_max = prev_state.get('y_max', args.ymax)

            # Override ranges if explicitly specified
            if args.xmin != -2*np.pi:
                x_min = args.xmin
            if args.xmax != 2*np.pi:
                x_max = args.xmax
            if args.ymin is not None:
                y_min = args.ymin
            if args.ymax is not None:
                y_max = args.ymax
        else:
            # Fresh start
            expressions = []
            # For parametric curves, use None for x range to auto-compute
            # unless explicitly specified
            if args.parametric and not x_range_explicit:
                x_min = None
                x_max = None
            else:
                x_min = args.xmin
                x_max = args.xmax
            y_min = args.ymin
            y_max = args.ymax

        # Add current expression(s) with config
        if args.parametric:
            expressions.append({
                'expr': args.parametric,
                'color': args.color,
                'samples': args.samples,
                'parametric': True,
                't_min': args.tmin,
                't_max': args.tmax,
            })
        # Add all expressions from command line
        for expr in all_expressions:
            expressions.append({
                'expr': expr,
                'color': args.color if len(all_expressions) == 1 else None,  # Use specified color only for single expr
                'samples': args.samples,
                'parametric': False,
            })

        if args.json:
            # Output JSON for chaining
            write_json_output(expressions, x_min, x_max, y_min, y_max)
        else:
            # Final render
            bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
                expressions, x_min, x_max, y_min, y_max,
                pixel_width, pixel_height,
                char_width, char_height,
                show_axes=args.axes,
                renderer=renderer,
                font_aspect=args.font_aspect,
                x_range_explicit=x_range_explicit,
                y_range_explicit=y_range_explicit,
            )

            # Print range info
            print(f"x: [{x_min:.2f}, {x_max:.2f}]  y: [{y_min:.2f}, {y_max:.2f}]")

            # Layer funcat-specific braille threshold for thin curves
            configured = renderer
            if args.renderer == 'braille' and hasattr(renderer, 'threshold'):
                configured = renderer(threshold=0.2)

            # Render to terminal
            colors_out = None if effective_no_color else colors
            canvas = Canvas(bitmap, colors=colors_out)
            canvas.out(configured)
            print()

            # Print legend if requested and multiple functions
            if args.legend and len(legend_entries) > 1:
                print_legend(legend_entries, no_color=effective_no_color)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
