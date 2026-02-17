"""CLI entry point for htmlcat — terminal HTML viewer."""

from __future__ import annotations

import sys
from pathlib import Path

from dapple.extras.htmlcat.htmlcat import htmlcat


def _build_parser():
    """Build the argparse parser for htmlcat."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="htmlcat",
        description="Display HTML files in the terminal with inline images",
    )

    parser.add_argument(
        "files", type=Path, nargs="*",
        help="HTML file(s) to display",
    )
    parser.add_argument(
        "-r", "--renderer",
        choices=["auto", "braille", "quadrants", "sextants", "ascii", "sixel", "kitty"],
        default="auto",
        help="Renderer for inline images (default: auto)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Console width in characters (default: terminal width)",
    )
    parser.add_argument(
        "--image-width", type=int,
        help="Image width in characters (default: console width)",
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="Skip rendering inline images",
    )
    parser.add_argument(
        "--code-theme", default="monokai",
        help="Pygments theme for code blocks (default: monokai)",
    )
    parser.add_argument(
        "--no-hyperlinks", action="store_true",
        help="Disable clickable hyperlinks",
    )
    parser.add_argument(
        "--raw", action="store_true",
        help="Output converted markdown instead of rendering (debug mode)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    if not args.files:
        parser.print_help()
        sys.exit(1)

    # Determine output destination
    if args.output:
        dest = open(args.output, "w", encoding="utf-8")
    else:
        dest = None  # Use stdout via console

    errors: list[str] = []
    exit_code = 0
    first_file = True
    try:
        for file_path in args.files:
            if not file_path.exists():
                errors.append(f"{file_path}: File not found")
                continue

            # Print separator for multiple files
            if len(args.files) > 1:
                prefix = "\n" if not first_file else ""
                separator = f"{prefix}{'=' * 60}\n  {file_path.name}\n{'=' * 60}\n"
                if dest:
                    dest.write(separator)
                else:
                    print(separator)
                first_file = False

            try:
                htmlcat(
                    file_path,
                    renderer=args.renderer,
                    width=args.width,
                    image_width=args.image_width,
                    render_images=not args.no_images,
                    code_theme=args.code_theme,
                    hyperlinks=not args.no_hyperlinks,
                    raw=args.raw,
                    dest=dest,
                )
            except Exception as e:
                errors.append(f"{file_path}: {e}")
                continue
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if dest:
            dest.close()

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
