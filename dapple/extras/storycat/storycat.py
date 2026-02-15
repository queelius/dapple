"""storycat - Video storyboard grid.

Extracts frames from a video and displays them as a grid of thumbnails.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import TextIO

from dapple.extras.vidcat.vidcat import VidcatOptions, extract_frames, get_video_info


def storycat(
    video_path: str | Path,
    *,
    cols: int = 5,
    width: int | None = None,
    renderer: str = "sextants",
    max_frames: int = 20,
    every: str | None = None,
    frames: str | None = None,
    dest: TextIO | None = None,
) -> None:
    """Display video frames as a storyboard grid.

    Args:
        video_path: Path to the video file.
        cols: Number of columns per row.
        width: Total output width in characters (None = terminal width).
        renderer: Renderer name for display.
        max_frames: Maximum number of frames to extract.
        every: Extract a frame every N seconds (e.g., "10s", "5").
        frames: Frame range string (e.g., "1-20").
        dest: Output stream (default: stdout).
    """
    try:
        from dapple.adapters.pil import load_image
    except ImportError:
        raise ImportError(
            "PIL is required for storycat. Install with: pip install dapple[vidcat]"
        )

    from dapple.extras.common import get_renderer
    from dapple.layout import Frame, Grid, terminal_columns

    output = dest or sys.stdout
    rend = get_renderer(renderer)
    total_width = width or terminal_columns()

    path = Path(video_path)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return

    info = get_video_info(path)
    duration = info.get("duration", 0)
    fps = info.get("fps", 30)

    # Extract frames
    options = VidcatOptions(
        max_frames=max_frames,
        every=every,
        frames=frames,
    )

    with tempfile.TemporaryDirectory(prefix="storycat_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        frame_paths = list(extract_frames(path, options, tmp_path))

        if not frame_paths:
            print(f"Error: No frames extracted from {path}", file=sys.stderr)
            return

        # Build frames with timestamps
        grid_frames = []
        for i, frame_path in enumerate(frame_paths):
            canvas = load_image(frame_path)

            # Estimate timestamp
            if duration > 0 and len(frame_paths) > 1:
                t = duration * i / (len(frame_paths) - 1)
            elif duration > 0:
                t = 0
            else:
                t = i / fps if fps else i

            mins, secs = divmod(int(t), 60)
            title = f"{mins}:{secs:02d}"
            grid_frames.append(Frame(canvas=canvas, title=title))

        # Arrange into grid
        rows = []
        for i in range(0, len(grid_frames), cols):
            rows.append(grid_frames[i:i + cols])

        grid = Grid(rows, width=total_width)
        grid.render(rend, dest=output)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="storycat",
        description="Display video frames as a storyboard grid",
    )
    parser.add_argument("video", type=Path, help="Video file")
    parser.add_argument(
        "--cols", type=int, default=5,
        help="Number of columns (default: 5)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters (default: terminal width)",
    )
    parser.add_argument(
        "-r", "--renderer", default="sextants",
        help="Renderer to use (default: sextants)",
    )
    parser.add_argument(
        "-n", "--max-frames", type=int, default=20,
        help="Maximum frames to extract (default: 20)",
    )
    parser.add_argument(
        "--every", type=str,
        help="Extract a frame every N seconds (e.g., 10s)",
    )
    parser.add_argument(
        "--frames", type=str,
        help="Frame range (e.g., 1-20)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    if not args.video.exists():
        print(f"Error: File not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    dest = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        storycat(
            args.video,
            cols=args.cols,
            width=args.width,
            renderer=args.renderer,
            max_frames=args.max_frames,
            every=args.every,
            frames=args.frames,
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
