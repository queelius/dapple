"""ansicat - ANSI art viewer.

Renders ANSI terminal art files using dapple renderers.
Wraps the existing dapple.adapters.ansi.from_ansi() adapter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO


def ansicat(
    art_path: str | Path,
    *,
    renderer: str = "sextants",
    width: int | None = None,
    dest: TextIO | None = None,
) -> None:
    """Render an ANSI art file to the terminal.

    Args:
        art_path: Path to the ANSI art file (or "-" for stdin).
        renderer: Renderer name for output.
        width: Output width in characters (None = terminal width).
        dest: Output stream (default: stdout).
    """
    from dapple.adapters.ansi import from_ansi
    from dapple.extras.common import get_renderer
    from dapple.layout import terminal_fit

    output = dest or sys.stdout
    rend = get_renderer(renderer)

    # Read the ANSI art text
    path = Path(art_path)
    if str(art_path) == "-":
        text = sys.stdin.read()
    elif path.exists():
        text = path.read_text(errors="replace")
    else:
        print(f"Error: File not found: {path}", file=sys.stderr)
        return

    # Parse ANSI art to canvas
    canvas = from_ansi(text)

    # Size for terminal
    canvas, rend = terminal_fit(canvas, rend, width=width)

    # Render
    rend.render(canvas._bitmap, canvas._colors, dest=output)
    output.write("\n")


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="ansicat",
        description="Display ANSI art in the terminal using dapple renderers",
    )
    parser.add_argument(
        "files", nargs="*",
        help='ANSI art file(s) to display (use "-" for stdin)',
    )
    parser.add_argument(
        "-r", "--renderer", default="sextants",
        help="Renderer to use (default: sextants)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters (default: terminal width)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    if not args.files:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        args.files = ["-"]

    dest = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    errors: list[str] = []
    try:
        for art_path in args.files:
            try:
                ansicat(
                    art_path,
                    renderer=args.renderer,
                    width=args.width,
                    dest=dest,
                )
            except Exception as e:
                errors.append(f"{art_path}: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        if args.output:
            dest.close()

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
