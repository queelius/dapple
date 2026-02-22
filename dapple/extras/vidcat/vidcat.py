"""vidcat - Terminal video frame viewer.

Extracts frames from video files and renders them to the terminal using dapple.
Requires ffmpeg to be installed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, TextIO



@dataclass
class VidcatOptions:
    """Options for video frame rendering.

    Attributes:
        renderer: Renderer name ("auto", "braille", "quadrants", etc.)
        width: Output width in characters (None = terminal width)
        height: Output height in characters (None = auto)
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output entirely
        max_frames: Maximum number of frames to extract
        frames: Frame selection string (e.g., "1-10", "1,5,10", "-5", "100-")
        every: Extract interval (e.g., "1s", "30s", "1m")
        play: Enable in-place playback using ANSI cursor movement
        fps: Playback frames per second (used with play mode and asciinema)
    """

    renderer: str = "auto"
    width: int | None = None
    height: int | None = None
    dither: bool = False
    contrast: bool = False
    invert: bool = False
    grayscale: bool = False
    no_color: bool = False
    max_frames: int = 10
    frames: str | None = None
    every: str | None = None
    play: bool = False
    fps: float = 10.0


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    return shutil.which("ffmpeg") is not None


def get_video_info(video_path: Path) -> dict:
    """Get video metadata using ffprobe.

    Returns:
        Dict with 'duration', 'fps', 'width', 'height', 'frame_count'
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return {"duration": 0, "fps": 30, "width": 0, "height": 0, "frame_count": 0}

    # Find video stream
    video_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    if not video_stream:
        return {"duration": 0, "fps": 30, "width": 0, "height": 0, "frame_count": 0}

    # Parse fps
    fps_str = video_stream.get("r_frame_rate", "30/1")
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    # Get duration
    duration = float(data.get("format", {}).get("duration", 0))

    # Get dimensions
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # Estimate frame count
    frame_count = int(duration * fps) if duration and fps else 0

    return {
        "duration": duration,
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": frame_count,
    }


def parse_interval(interval: str) -> float:
    """Parse interval string to seconds.

    Args:
        interval: String like "1s", "30s", "1m", "1.5m"

    Returns:
        Interval in seconds
    """
    match = re.match(r"^(\d+(?:\.\d+)?)(s|m|h)?$", interval.lower())
    if not match:
        raise ValueError(f"Invalid interval format: {interval}")

    value = float(match.group(1))
    unit = match.group(2) or "s"

    if unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600
    else:
        return value


def parse_frames(frames_str: str, total_frames: int) -> list[int]:
    """Parse frame selection string.

    Args:
        frames_str: Frame selection (e.g., "1-10", "1,5,10", "-5", "100-")
        total_frames: Total number of frames in video

    Returns:
        List of 0-indexed frame numbers
    """
    result: list[int] = []

    for part in frames_str.split(","):
        part = part.strip()

        try:
            if "-" in part:
                if part.startswith("-"):
                    # -5 means first 5 frames
                    end = int(part[1:])
                    result.extend(range(0, min(end, total_frames)))
                elif part.endswith("-"):
                    # 100- means frame 100 onwards
                    start_idx = int(part[:-1]) - 1  # Convert to 0-indexed
                    result.extend(range(max(0, start_idx), total_frames))
                else:
                    # 1-10 means frames 1 through 10
                    start_str, end_str = part.split("-")
                    start_idx = int(start_str) - 1  # Convert to 0-indexed
                    end_idx = int(end_str)
                    result.extend(range(max(0, start_idx), min(end_idx, total_frames)))
            else:
                # Single frame number
                frame = int(part) - 1  # Convert to 0-indexed
                if 0 <= frame < total_frames:
                    result.append(frame)
        except ValueError:
            raise ValueError(f"Invalid frame number: '{part}' in range '{frames_str}'")

    return sorted(set(result))


def extract_frames(
    video_path: Path,
    options: VidcatOptions,
    output_dir: Path,
) -> Iterator[Path]:
    """Extract frames from video using ffmpeg.

    Args:
        video_path: Path to video file
        options: Extraction options
        output_dir: Directory to save frames

    Yields:
        Paths to extracted frame images
    """
    info = get_video_info(video_path)

    # Build ffmpeg command
    cmd = ["ffmpeg", "-y", "-i", str(video_path)]

    if options.every:
        # Extract at interval
        interval = parse_interval(options.every)
        cmd.extend(["-vf", f"fps=1/{interval}"])
    elif options.frames and info["frame_count"] > 0:
        # Extract specific frames - use select filter
        frame_list = parse_frames(options.frames, info["frame_count"])
        if frame_list:
            select_expr = "+".join(f"eq(n,{f})" for f in frame_list[:options.max_frames])
            cmd.extend(["-vf", f"select='{select_expr}'", "-vsync", "vfr"])
    else:
        # Default: extract up to max_frames evenly spaced
        if info["frame_count"] > options.max_frames:
            step = info["frame_count"] // options.max_frames
            cmd.extend(["-vf", f"select='not(mod(n,{step}))'", "-vsync", "vfr"])

    # Limit total frames
    cmd.extend(["-frames:v", str(options.max_frames)])

    # Output pattern
    output_pattern = output_dir / "frame_%04d.png"
    cmd.append(str(output_pattern))

    # Run ffmpeg
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        stderr_msg = (e.stderr or b"").decode(errors="replace")[:200]
        raise RuntimeError(f"ffmpeg failed: {stderr_msg}")

    # Yield extracted frames in order
    for frame_path in sorted(output_dir.glob("frame_*.png")):
        yield frame_path


def render_frame(
    frame_path: Path,
    options: VidcatOptions,
    dest: TextIO,
) -> None:
    """Render a single frame to the terminal.

    Args:
        frame_path: Path to frame image
        options: Rendering options
        dest: Output stream
    """
    from dapple.extras.imgcat import imgcat

    imgcat(
        frame_path,
        renderer=options.renderer,
        width=options.width,
        height=options.height,
        dither=options.dither,
        contrast=options.contrast,
        invert=options.invert,
        grayscale=options.grayscale,
        no_color=options.no_color,
        dest=dest,
    )


def _play_frames(
    frame_paths: list[Path],
    options: VidcatOptions,
    dest: TextIO,
    fps: float = 10.0,
) -> None:
    """Play frames in-place using ANSI cursor movement.

    Each frame after the first overwrites the previous frame by moving the
    cursor up and clearing to end of screen.

    Args:
        frame_paths: List of frame image paths (in order)
        options: Rendering options
        dest: Output stream (should be a TTY for proper display)
        fps: Playback frames per second
    """
    import io as _io

    if not frame_paths:
        return

    frame_interval = 1.0 / fps

    # Render first frame to count lines
    buf = _io.StringIO()
    render_frame(frame_paths[0], options, buf)
    first_output = buf.getvalue()
    line_count = first_output.count("\n")

    # Write first frame
    dest.write(first_output)
    dest.flush()

    # Overwrite for subsequent frames
    for frame_path in frame_paths[1:]:
        time.sleep(frame_interval)
        # Cursor up + clear from cursor to end of screen
        dest.write(f"\033[{line_count}A\033[J")
        render_frame(frame_path, options, dest)
        dest.flush()


def vidcat(
    video_path: str | Path,
    *,
    renderer: str = "auto",
    width: int | None = None,
    height: int | None = None,
    dither: bool = False,
    contrast: bool = False,
    invert: bool = False,
    grayscale: bool = False,
    no_color: bool = False,
    max_frames: int = 10,
    frames: str | None = None,
    every: str | None = None,
    dest: TextIO | None = None,
    frame_delay: float = 0.0,
    play: bool = False,
    fps: float = 10.0,
) -> None:
    """Extract and render video frames to the terminal.

    Args:
        video_path: Path to video file
        renderer: Renderer name ("auto", "braille", "quadrants", etc.)
        width: Output width in characters (None = terminal width)
        height: Output height in characters (None = auto)
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output entirely
        max_frames: Maximum number of frames to extract
        frames: Frame selection string (e.g., "1-10", "1,5,10")
        every: Extract interval (e.g., "1s", "30s", "1m")
        dest: Output stream (default: stdout)
        frame_delay: Delay between frames in seconds (for animation)
        play: Enable in-place playback using ANSI cursor movement
        fps: Playback frames per second (used with play mode)

    Example:
        >>> vidcat("animation.gif")
        >>> vidcat("video.mp4", frames="1-10", renderer="braille")
        >>> vidcat("animation.gif", play=True, fps=15)
    """
    if not check_ffmpeg():
        raise RuntimeError(
            "ffmpeg not found. Install with: apt install ffmpeg (or brew install ffmpeg)"
        )

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    options = VidcatOptions(
        renderer=renderer,
        width=width,
        height=height,
        dither=dither,
        contrast=contrast,
        invert=invert,
        grayscale=grayscale,
        no_color=no_color,
        max_frames=max_frames,
        frames=frames,
        every=every,
        play=play,
        fps=fps,
    )

    output = dest if dest is not None else sys.stdout

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        if play:
            # In-place playback mode
            if not hasattr(output, "isatty") or not output.isatty():
                print(
                    "Warning: --play requires a TTY; falling back to stacked output",
                    file=sys.stderr,
                )
                # Fall through to stacked rendering below
            else:
                frame_paths = list(extract_frames(path, options, tmppath))
                if not frame_paths:
                    print("No frames extracted", file=sys.stderr)
                    return
                _play_frames(frame_paths, options, output, fps=fps)
                return

        # Stacked rendering (default, or fallback from non-TTY play)
        frame_count = 0

        for frame_path in extract_frames(path, options, tmppath):
            if frame_count > 0:
                output.write("\n")
                if frame_delay > 0:
                    output.flush()
                    time.sleep(frame_delay)

            render_frame(frame_path, options, output)
            frame_count += 1

        if frame_count == 0:
            print("No frames extracted", file=sys.stderr)


def view(video_path: str | Path, **kwargs) -> None:
    """Quick view of a video with default settings.

    Alias for vidcat() with default options.

    Args:
        video_path: Path to video file
        **kwargs: Additional options passed to vidcat()

    Example:
        >>> view("animation.gif")
    """
    vidcat(video_path, **kwargs)


def to_asciinema(
    video_path: str | Path,
    output_path: str | Path,
    *,
    fps: float = 10.0,
    renderer: str = "braille",
    width: int | None = None,
    height: int | None = None,
    dither: bool = False,
    contrast: bool = False,
    invert: bool = False,
    grayscale: bool = False,
    no_color: bool = False,
    max_frames: int = 100,
    title: str | None = None,
) -> None:
    """Export video as asciinema cast file.

    Creates an asciicast v2 file that can be played with asciinema play
    or embedded on asciinema.org.

    Args:
        video_path: Path to video file
        output_path: Path for output .cast file
        fps: Playback frames per second
        renderer: Renderer to use
        width: Output width in characters
        height: Output height in characters
        dither: Apply Floyd-Steinberg dithering
        contrast: Apply auto-contrast
        invert: Invert colors
        grayscale: Force grayscale output
        no_color: Disable color output
        max_frames: Maximum frames to extract
        title: Recording title

    Example:
        >>> to_asciinema("animation.gif", "output.cast", fps=15)
    """
    import io

    if not check_ffmpeg():
        raise RuntimeError("ffmpeg not found")

    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")

    path = Path(video_path)
    out_path = Path(output_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    # Determine terminal dimensions
    term_size = shutil.get_terminal_size(fallback=(80, 24))
    term_width = width or term_size.columns
    term_height = height or term_size.lines

    options = VidcatOptions(
        renderer=renderer,
        width=term_width,
        height=term_height,
        dither=dither,
        contrast=contrast,
        invert=invert,
        grayscale=grayscale,
        no_color=no_color,
        max_frames=max_frames,
    )

    frame_interval = 1.0 / fps

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Extract frames
        frame_paths = list(extract_frames(path, options, tmppath))

        if not frame_paths:
            raise RuntimeError("No frames extracted")

        # Render each frame to string
        frames_data = []
        for frame_path in frame_paths:
            buf = io.StringIO()
            render_frame(frame_path, options, buf)
            frames_data.append(buf.getvalue())

        # Measure actual dimensions from rendered first frame
        if frames_data:
            first_lines = frames_data[0].split("\n")
            # Strip trailing empty line (renderer output ends with \n)
            if first_lines and first_lines[-1] == "":
                first_lines = first_lines[:-1]
            actual_height = len(first_lines)
            actual_width = max(len(line) for line in first_lines) if first_lines else term_width
        else:
            actual_height = term_height
            actual_width = term_width

        # Write asciicast v2 file
        with open(out_path, "w", encoding="utf-8") as f:
            # Header
            header = {
                "version": 2,
                "width": actual_width,
                "height": actual_height + 1,  # +1 for cursor row
                "timestamp": int(time.time()),
                "env": {"TERM": "xterm-256color"},
            }
            if title:
                header["title"] = title

            f.write(json.dumps(header) + "\n")

            # Clear screen escape sequence
            clear = "\033[2J\033[H"

            # Frame events
            timestamp = 0.0
            for frame_data in frames_data:
                # Clear and draw frame
                event = [timestamp, "o", clear + frame_data]
                f.write(json.dumps(event) + "\n")
                timestamp += frame_interval

            # Hold last frame visible for 1 second
            event = [timestamp + 1.0, "o", ""]
            f.write(json.dumps(event) + "\n")

    print(f"Created: {out_path}", file=sys.stderr)
    print(f"Play with: asciinema play {out_path}", file=sys.stderr)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="vidcat",
        description="Display video frames in the terminal using dapple",
    )

    parser.add_argument(
        "videos", type=Path, nargs="*", help="Video file(s) to display"
    )
    parser.add_argument(
        "-r", "--renderer",
        choices=["auto", "braille", "quadrants", "sextants", "ascii", "sixel", "kitty"],
        default="auto",
        help="Renderer to use (default: auto)",
    )
    parser.add_argument(
        "-w", "--width", type=int,
        help="Output width in characters",
    )
    parser.add_argument(
        "-H", "--height", type=int,
        help="Output height in characters",
    )
    parser.add_argument(
        "--frames", type=str,
        help="Frame selection (e.g., '1-10', '1,5,10', '-5', '100-')",
    )
    parser.add_argument(
        "--every", type=str,
        help="Extract interval (e.g., '1s', '30s', '1m')",
    )
    parser.add_argument(
        "--max-frames", type=int, default=10,
        help="Maximum frames to extract (default: 10)",
    )
    parser.add_argument(
        "--dither", action="store_true",
        help="Apply Floyd-Steinberg dithering",
    )
    parser.add_argument(
        "--contrast", action="store_true",
        help="Apply auto-contrast",
    )
    parser.add_argument(
        "--invert", action="store_true",
        help="Invert colors",
    )
    from dapple.extras.common import add_color_args
    add_color_args(parser)

    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.0,
        help="Delay between frames in seconds",
    )

    # Playback mode
    parser.add_argument(
        "--play", action="store_true",
        help="Play frames in-place (overwrites previous frame in terminal)",
    )

    # Asciinema output
    parser.add_argument(
        "--asciinema", type=Path, metavar="FILE",
        help="Export to asciinema .cast file",
    )
    parser.add_argument(
        "--fps", type=float, default=10.0,
        help="Playback FPS for --play and --asciinema (default: 10)",
    )
    parser.add_argument(
        "--title", type=str,
        help="Title for asciinema recording",
    )

    args = parser.parse_args()

    # Main command
    if not args.videos:
        parser.print_help()
        sys.exit(1)

    # Determine output destination
    if args.output:
        dest = open(args.output, "w", encoding="utf-8")
    else:
        dest = sys.stdout

    errors: list[str] = []
    exit_code = 0
    first_video = True
    try:
        for video_path in args.videos:
            if not video_path.exists():
                errors.append(f"{video_path}: File not found")
                continue

            # Asciinema export (only makes sense for single video)
            if args.asciinema:
                if len(args.videos) > 1:
                    errors.append("--asciinema only supports a single video file")
                    break
                try:
                    to_asciinema(
                        video_path,
                        args.asciinema,
                        fps=args.fps,
                        renderer=args.renderer,
                        width=args.width,
                        height=args.height,
                        dither=args.dither,
                        contrast=args.contrast,
                        invert=args.invert,
                        grayscale=args.grayscale,
                        no_color=args.no_color,
                        max_frames=args.max_frames,
                        title=args.title,
                    )
                except Exception as e:
                    errors.append(f"{video_path}: {e}")
                continue

            # Print separator for multiple videos
            if len(args.videos) > 1:
                if not first_video:
                    dest.write("\n")
                dest.write(f"{'='*60}\n")
                dest.write(f"  {video_path.name}\n")
                dest.write(f"{'='*60}\n\n")
                first_video = False

            try:
                vidcat(
                    video_path,
                    renderer=args.renderer,
                    width=args.width,
                    height=args.height,
                    dither=args.dither,
                    contrast=args.contrast,
                    invert=args.invert,
                    grayscale=args.grayscale,
                    no_color=args.no_color,
                    max_frames=args.max_frames,
                    frames=args.frames,
                    every=args.every,
                    dest=dest,
                    frame_delay=args.delay,
                    play=args.play,
                    fps=args.fps,
                )
            except Exception as e:
                errors.append(f"{video_path}: {e}")
                continue
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if args.output:
            dest.close()

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
