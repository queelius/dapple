"""Tests for vidcat module."""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from dapple.extras.vidcat.vidcat import (
    VidcatOptions,
    check_ffmpeg,
    extract_frames,
    get_video_info,
    parse_frames,
    parse_interval,
)


class TestParseInterval:
    """Tests for parse_interval function."""

    def test_seconds(self):
        assert parse_interval("1s") == 1.0
        assert parse_interval("30s") == 30.0
        assert parse_interval("1.5s") == 1.5

    def test_minutes(self):
        assert parse_interval("1m") == 60.0
        assert parse_interval("2m") == 120.0
        assert parse_interval("1.5m") == 90.0

    def test_hours(self):
        assert parse_interval("1h") == 3600.0
        assert parse_interval("2h") == 7200.0

    def test_no_unit_defaults_to_seconds(self):
        assert parse_interval("5") == 5.0
        assert parse_interval("30") == 30.0

    def test_case_insensitive(self):
        assert parse_interval("1S") == 1.0
        assert parse_interval("1M") == 60.0
        assert parse_interval("1H") == 3600.0

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid interval format"):
            parse_interval("abc")
        with pytest.raises(ValueError, match="Invalid interval format"):
            parse_interval("1x")


class TestParseFrames:
    """Tests for parse_frames function."""

    def test_single_frame(self):
        result = parse_frames("5", 100)
        assert result == [4]  # 0-indexed

    def test_multiple_frames(self):
        result = parse_frames("1,5,10", 100)
        assert result == [0, 4, 9]  # 0-indexed

    def test_range(self):
        result = parse_frames("1-5", 100)
        assert result == [0, 1, 2, 3, 4]

    def test_first_n_frames(self):
        result = parse_frames("-5", 100)
        assert result == [0, 1, 2, 3, 4]

    def test_frames_from_n(self):
        result = parse_frames("98-", 100)
        assert result == [97, 98, 99]

    def test_out_of_bounds_single(self):
        result = parse_frames("150", 100)
        assert result == []

    def test_range_clamps_to_total(self):
        result = parse_frames("95-110", 100)
        assert result == [94, 95, 96, 97, 98, 99]

    def test_complex_selection(self):
        result = parse_frames("1,5-7,10", 100)
        assert result == [0, 4, 5, 6, 9]

    def test_removes_duplicates(self):
        result = parse_frames("1,1,1-3", 100)
        assert result == [0, 1, 2]

    def test_zero_total_frames(self):
        """When total_frames is 0, all selections return empty."""
        result = parse_frames("1-10", 0)
        assert result == []

    def test_zero_start_clamps_to_first_frame(self):
        """Zero start in range (invalid in 1-indexed) clamps to frame 0."""
        result = parse_frames("0-3", 100)  # 0-1=-1, clamped to 0
        assert result == [0, 1, 2]  # First 3 frames (0-indexed)

    def test_whitespace_handling(self):
        """Whitespace around parts is stripped."""
        result = parse_frames(" 1 , 5 , 10 ", 100)
        assert result == [0, 4, 9]


class TestVidcatOptions:
    """Tests for VidcatOptions dataclass."""

    def test_defaults(self):
        opts = VidcatOptions()
        assert opts.renderer == "auto"
        assert opts.width is None
        assert opts.height is None
        assert opts.dither is False
        assert opts.contrast is False
        assert opts.invert is False
        assert opts.grayscale is False
        assert opts.no_color is False
        assert opts.max_frames == 10
        assert opts.frames is None
        assert opts.every is None
        assert opts.play is False
        assert opts.fps == 10.0

    def test_custom_values(self):
        opts = VidcatOptions(
            renderer="braille",
            width=80,
            height=24,
            dither=True,
            max_frames=20,
            frames="1-10",
        )
        assert opts.renderer == "braille"
        assert opts.width == 80
        assert opts.height == 24
        assert opts.dither is True
        assert opts.max_frames == 20
        assert opts.frames == "1-10"


class TestCheckFfmpeg:
    """Tests for check_ffmpeg function."""

    def test_ffmpeg_found(self):
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            assert check_ffmpeg() is True

    def test_ffmpeg_not_found(self):
        with mock.patch("shutil.which", return_value=None):
            assert check_ffmpeg() is False


class TestGetVideoInfo:
    """Tests for get_video_info function."""

    def test_valid_video_info(self):
        mock_output = json.dumps({
            "format": {"duration": "60.0"},
            "streams": [
                {
                    "codec_type": "video",
                    "r_frame_rate": "30/1",
                    "width": 1920,
                    "height": 1080,
                }
            ]
        })

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=mock_output, returncode=0)
            info = get_video_info(Path("test.mp4"))

        assert info["duration"] == 60.0
        assert info["fps"] == 30.0
        assert info["width"] == 1920
        assert info["height"] == 1080
        assert info["frame_count"] == 1800

    def test_fractional_fps(self):
        mock_output = json.dumps({
            "format": {"duration": "10.0"},
            "streams": [
                {
                    "codec_type": "video",
                    "r_frame_rate": "24000/1001",
                    "width": 1920,
                    "height": 1080,
                }
            ]
        })

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=mock_output, returncode=0)
            info = get_video_info(Path("test.mp4"))

        assert 23.9 < info["fps"] < 24.1

    def test_no_video_stream(self):
        mock_output = json.dumps({
            "format": {"duration": "60.0"},
            "streams": [{"codec_type": "audio"}]
        })

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=mock_output, returncode=0)
            info = get_video_info(Path("test.mp4"))

        assert info["frame_count"] == 0

    def test_ffprobe_fails(self):
        import subprocess
        with mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffprobe")):
            info = get_video_info(Path("test.mp4"))
        assert info["frame_count"] == 0

    def test_invalid_json(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout="not json", returncode=0)
            info = get_video_info(Path("test.mp4"))
        assert info["frame_count"] == 0


class TestExtractFrames:
    """Tests for extract_frames function."""

    def test_ffmpeg_failure_raises(self):
        """Test that ffmpeg failure raises RuntimeError."""
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            options = VidcatOptions(max_frames=5)
            with mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr=b"error")):
                with mock.patch("dapple.extras.vidcat.vidcat.get_video_info", return_value={"frame_count": 100, "fps": 30}):
                    with pytest.raises(RuntimeError, match="ffmpeg failed"):
                        list(extract_frames(Path("test.mp4"), options, Path(tmpdir)))

    def test_extracts_frames_to_output_dir(self):
        """Test that frames are yielded from output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create fake frame files
            (tmppath / "frame_0001.png").write_bytes(b"fake png")
            (tmppath / "frame_0002.png").write_bytes(b"fake png")

            options = VidcatOptions(max_frames=5)

            with mock.patch("subprocess.run"):  # ffmpeg succeeds
                with mock.patch("dapple.extras.vidcat.vidcat.get_video_info", return_value={"frame_count": 100, "fps": 30}):
                    frames = list(extract_frames(Path("test.mp4"), options, tmppath))

            assert len(frames) == 2
            assert frames[0].name == "frame_0001.png"
            assert frames[1].name == "frame_0002.png"


class TestVidcatFunction:
    """Tests for vidcat main function."""

    def test_ffmpeg_not_found(self):
        from dapple.extras.vidcat.vidcat import vidcat

        with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=False):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                vidcat("test.mp4")

    def test_file_not_found(self):
        from dapple.extras.vidcat.vidcat import vidcat

        with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=True):
            with pytest.raises(FileNotFoundError, match="Video not found"):
                vidcat("/nonexistent/video.mp4")


class TestViewFunction:
    """Tests for view() alias function."""

    def test_view_delegates_to_vidcat(self):
        from dapple.extras.vidcat.vidcat import view

        with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=False):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                view("test.mp4")

    def test_view_passes_kwargs(self):
        from dapple.extras.vidcat.vidcat import view

        with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=True):
            with pytest.raises(FileNotFoundError):
                view("/nonexistent/video.mp4", renderer="braille", max_frames=5)


class TestToAsciinema:
    """Tests for to_asciinema function."""

    def test_ffmpeg_not_found(self):
        from dapple.extras.vidcat.vidcat import to_asciinema

        with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=False):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                to_asciinema("test.mp4", "output.cast")

    def test_file_not_found(self):
        from dapple.extras.vidcat.vidcat import to_asciinema

        with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=True):
            with pytest.raises(FileNotFoundError, match="Video not found"):
                to_asciinema("/nonexistent/video.mp4", "output.cast")

    def test_invalid_fps(self):
        from dapple.extras.vidcat.vidcat import to_asciinema

        with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=True):
            with pytest.raises(ValueError, match="fps must be positive"):
                to_asciinema("test.mp4", "output.cast", fps=0)

            with pytest.raises(ValueError, match="fps must be positive"):
                to_asciinema("test.mp4", "output.cast", fps=-1)


class TestCLI:
    """Tests for CLI argument parsing."""

    def test_help_without_video(self, capsys):
        """Test that help is shown when no video is provided."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["vidcat"]):
            with pytest.raises(SystemExit) as exc_info:
                from dapple.extras.vidcat.vidcat import main
                main()
            assert exc_info.value.code == 1

    def test_file_not_found_cli(self, capsys):
        """Test error when video file doesn't exist."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["vidcat", "/nonexistent/video.mp4"]):
            with pytest.raises(SystemExit) as exc_info:
                from dapple.extras.vidcat.vidcat import main
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "File not found" in captured.err


class TestPlayMode:
    """Tests for in-place playback mode."""

    def test_play_emits_cursor_up(self):
        """When dest is TTY, play mode emits ANSI cursor-up codes."""
        from dapple.extras.vidcat.vidcat import _play_frames

        # Create fake frame files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            for i in range(3):
                (tmppath / f"frame_{i:04d}.png").write_bytes(b"fake")

            frame_paths = sorted(tmppath.glob("frame_*.png"))
            options = VidcatOptions(width=40)

            # Create a mock TTY dest
            buf = io.StringIO()
            buf.isatty = lambda: True  # type: ignore[assignment]

            # Mock render_frame to produce predictable output
            def fake_render(path, opts, dest):
                dest.write("line1\nline2\nline3\n")

            with mock.patch("dapple.extras.vidcat.vidcat.render_frame", side_effect=fake_render):
                with mock.patch("time.sleep"):
                    _play_frames(frame_paths, options, buf, fps=10.0)

            output = buf.getvalue()
            # Should contain ANSI cursor-up codes for frames after the first
            assert "\033[" in output
            assert "A" in output
            # First frame output, then cursor-up + clear + second frame, etc.
            assert output.count("\033[J") == 2  # Two overwrites (for frames 2 and 3)

    def test_play_non_tty_fallback(self, capsys):
        """Non-TTY dest falls back to stacked output with warning."""
        from dapple.extras.vidcat.vidcat import vidcat

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            for i in range(2):
                (tmppath / f"frame_{i:04d}.png").write_bytes(b"fake")

            frame_paths = sorted(tmppath.glob("frame_*.png"))

            buf = io.StringIO()
            # StringIO.isatty() returns False by default — non-TTY

            # Mock the whole pipeline to avoid needing real video/ffmpeg
            with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=True):
                with mock.patch("pathlib.Path.exists", return_value=True):
                    with mock.patch("dapple.extras.vidcat.vidcat.extract_frames", return_value=iter(frame_paths)):
                        with mock.patch("dapple.extras.vidcat.vidcat.render_frame") as mock_render:
                            mock_render.side_effect = lambda p, o, d: d.write("frame\n")
                            vidcat("fake.mp4", play=True, dest=buf)

            # Should have fallen back to stacked (no ANSI codes)
            output = buf.getvalue()
            assert "\033[" not in output

            # Should have printed a warning to stderr
            captured = capsys.readouterr()
            assert "play" in captured.err.lower() or "tty" in captured.err.lower()

    def test_fps_controls_delay(self):
        """Verify fps parameter controls the sleep interval."""
        from dapple.extras.vidcat.vidcat import _play_frames

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            for i in range(3):
                (tmppath / f"frame_{i:04d}.png").write_bytes(b"fake")

            frame_paths = sorted(tmppath.glob("frame_*.png"))
            options = VidcatOptions(width=40)

            buf = io.StringIO()
            buf.isatty = lambda: True  # type: ignore[assignment]

            def fake_render(path, opts, dest):
                dest.write("line1\nline2\n")

            with mock.patch("dapple.extras.vidcat.vidcat.render_frame", side_effect=fake_render):
                with mock.patch("time.sleep") as mock_sleep:
                    _play_frames(frame_paths, options, buf, fps=5.0)

            # fps=5.0 means 0.2s between frames
            assert mock_sleep.call_count == 2  # Called for frames 2 and 3
            mock_sleep.assert_called_with(pytest.approx(0.2))

    def test_play_single_frame_no_cursor_codes(self):
        """With only one frame, no cursor-up codes should be emitted."""
        from dapple.extras.vidcat.vidcat import _play_frames

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "frame_0001.png").write_bytes(b"fake")

            frame_paths = sorted(tmppath.glob("frame_*.png"))
            options = VidcatOptions(width=40)

            buf = io.StringIO()
            buf.isatty = lambda: True  # type: ignore[assignment]

            def fake_render(path, opts, dest):
                dest.write("line1\nline2\n")

            with mock.patch("dapple.extras.vidcat.vidcat.render_frame", side_effect=fake_render):
                with mock.patch("time.sleep") as mock_sleep:
                    _play_frames(frame_paths, options, buf, fps=10.0)

            output = buf.getvalue()
            # No ANSI cursor codes for single frame
            assert "\033[" not in output
            mock_sleep.assert_not_called()

    def test_play_cli_flag(self):
        """Test that --play flag is accepted by CLI parser."""
        import sys

        with mock.patch.object(sys, "argv", ["vidcat", "--play", "/nonexistent/video.mp4"]):
            with mock.patch("dapple.extras.vidcat.vidcat.check_ffmpeg", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    from dapple.extras.vidcat.vidcat import main
                    main()
                assert exc_info.value.code == 1


class TestParseErrors:
    def test_bad_frame_range(self):
        """Invalid frame range should produce clear error."""
        with pytest.raises(ValueError, match="Invalid frame number"):
            parse_frames("abc-def", 100)

    def test_bad_single_frame(self):
        """Non-numeric single frame should produce clear error."""
        with pytest.raises(ValueError, match="Invalid frame number"):
            parse_frames("xyz", 100)
