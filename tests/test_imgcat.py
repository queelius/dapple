"""Tests for imgcat extra."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

# Skip all tests if extras not importable
pytest.importorskip("PIL")
imgcat_mod = pytest.importorskip("dapple.extras.imgcat")


class TestImgcatOptions:
    """Tests for ImgcatOptions dataclass."""

    def test_default_options(self):
        from dapple.extras.imgcat import ImgcatOptions

        opts = ImgcatOptions()
        assert opts.renderer == "auto"
        assert opts.width is None
        assert opts.height is None
        assert opts.dither is False
        assert opts.contrast is False
        assert opts.invert is False
        assert opts.grayscale is False
        assert opts.no_color is False


class TestGetRenderer:
    """Tests for get_renderer function."""

    def test_auto_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("auto", opts)
        assert hasattr(renderer, "render")

    def test_braille_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("braille", opts)
        assert hasattr(renderer, "render")
        assert renderer.cell_width == 2
        assert renderer.cell_height == 4

    def test_quadrants_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("quadrants", opts)
        assert hasattr(renderer, "render")
        assert renderer.cell_width == 2
        assert renderer.cell_height == 2

    def test_unknown_renderer_raises(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        with pytest.raises(ValueError, match="Unknown renderer"):
            get_renderer("unknown", opts)


class TestGetRendererAll:
    """Extended tests for get_renderer covering all renderers."""

    def test_sextants_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("sextants", opts)
        assert hasattr(renderer, "render")
        assert renderer.cell_width == 2
        assert renderer.cell_height == 3

    def test_ascii_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("ascii", opts)
        assert hasattr(renderer, "render")
        assert renderer.cell_width == 1

    def test_sixel_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("sixel", opts)
        assert hasattr(renderer, "render")

    def test_kitty_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("kitty", opts)
        assert hasattr(renderer, "render")

    def test_fingerprint_renderer(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions()
        renderer = get_renderer("fingerprint", opts)
        assert hasattr(renderer, "render")

    def test_braille_no_color(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions(no_color=True)
        renderer = get_renderer("braille", opts)
        assert renderer.color_mode == "none"

    def test_braille_grayscale(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions(grayscale=True)
        renderer = get_renderer("braille", opts)
        assert renderer.color_mode == "grayscale"

    def test_quadrants_grayscale(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions(grayscale=True)
        renderer = get_renderer("quadrants", opts)
        assert renderer.grayscale is True

    def test_sextants_grayscale(self):
        from dapple.extras.imgcat.imgcat import get_renderer, ImgcatOptions

        opts = ImgcatOptions(grayscale=True)
        renderer = get_renderer("sextants", opts)
        assert renderer.grayscale is True


class TestImgcatFunction:
    """Tests for imgcat function."""

    def _make_test_image(self, tmpdir, name="test.png", size=(20, 20), color="red"):
        """Create a test image and return its path."""
        from PIL import Image

        img = Image.new("RGB", size, color=color)
        img_path = Path(tmpdir) / name
        img.save(img_path)
        return img_path

    def test_imgcat_with_test_image(self):
        """Test imgcat with a simple generated image."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)

            # Render to string buffer
            output = StringIO()
            imgcat(img_path, renderer="braille", width=20, dest=output)

            result = output.getvalue()
            assert len(result) > 0  # Should have some output

    def test_imgcat_quadrants(self):
        """Test imgcat with quadrants renderer."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="quadrants", width=20, dest=output)
            result = output.getvalue()
            assert len(result) > 0
            assert "\033[" in result  # ANSI color codes

    def test_imgcat_sextants(self):
        """Test imgcat with sextants renderer."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="sextants", width=20, dest=output)
            result = output.getvalue()
            assert len(result) > 0

    def test_imgcat_ascii(self):
        """Test imgcat with ascii renderer."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="ascii", width=20, dest=output)
            result = output.getvalue()
            assert len(result) > 0

    def test_imgcat_dither(self):
        """Test imgcat with dither preprocessing."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="braille", width=20, dither=True, dest=output)
            assert len(output.getvalue()) > 0

    def test_imgcat_contrast(self):
        """Test imgcat with contrast preprocessing."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="braille", width=20, contrast=True, dest=output)
            assert len(output.getvalue()) > 0

    def test_imgcat_invert(self):
        """Test imgcat with invert preprocessing."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="braille", width=20, invert=True, dest=output)
            assert len(output.getvalue()) > 0

    def test_imgcat_no_color(self):
        """Test imgcat with no_color flag."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="braille", width=20, no_color=True, dest=output)
            assert len(output.getvalue()) > 0

    def test_imgcat_grayscale(self):
        """Test imgcat with grayscale flag."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir)
            output = StringIO()
            imgcat(img_path, renderer="quadrants", width=20, grayscale=True, dest=output)
            assert len(output.getvalue()) > 0

    def test_imgcat_custom_width_and_height(self):
        """Test imgcat with custom width and height."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = self._make_test_image(tmpdir, size=(40, 40))
            output = StringIO()
            imgcat(img_path, renderer="braille", width=30, height=15, dest=output)
            assert len(output.getvalue()) > 0


class TestErrorHandling:
    """Tests for imgcat error handling."""

    def test_nonexistent_file_reports_not_found(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "dapple.extras.imgcat.imgcat", "/nonexistent/file.png"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_import_error_reports_missing_dependency(self, capsys):
        """ImportError caught per-image with clear 'Missing dependency' message."""
        from dapple.extras.imgcat.imgcat import main
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real file so file-not-found doesn't trigger first
            img_path = Path(tmpdir) / "test.png"
            img_path.write_bytes(b"fake")

            with patch.object(sys, "argv", ["imgcat", "-r", "braille", str(img_path)]):
                with patch("dapple.extras.imgcat.imgcat.imgcat", side_effect=ImportError("No module named 'PIL'")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "Missing dependency" in captured.err


class TestImgcatCLI:
    """Tests for imgcat CLI."""

    def test_help_output(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "dapple.extras.imgcat.imgcat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "imgcat" in result.stdout.lower() or "image" in result.stdout.lower()

    def test_nonexistent_file(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "dapple.extras.imgcat.imgcat", "/nonexistent/file.png"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_multiple_images(self):
        """Test CLI with multiple image arguments."""
        import subprocess

        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["a.png", "b.png"]:
                img = Image.new("RGB", (10, 10), color="blue")
                img.save(Path(tmpdir) / name)

            result = subprocess.run(
                [
                    "python", "-m", "dapple.extras.imgcat.imgcat",
                    "-r", "braille", "-w", "20",
                    str(Path(tmpdir) / "a.png"),
                    str(Path(tmpdir) / "b.png"),
                ],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert len(result.stdout) > 0

    def test_output_file(self):
        """Test CLI with output file flag."""
        import subprocess

        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Image.new("RGB", (10, 10), color="green")
            img_path = Path(tmpdir) / "test.png"
            img.save(img_path)
            out_path = Path(tmpdir) / "output.txt"

            result = subprocess.run(
                [
                    "python", "-m", "dapple.extras.imgcat.imgcat",
                    "-r", "braille", "-w", "20",
                    "-o", str(out_path),
                    str(img_path),
                ],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert out_path.exists()
            assert len(out_path.read_text()) > 0


# ─── Grid mode tests ────────────────────────────────────────────────────────


class TestGrid:
    """Tests for imgcat grid / contact sheet mode."""

    def _make_temp_images(self, tmpdir, count=3, size=(30, 30)):
        """Create temporary image files and return their paths."""
        from PIL import Image

        paths = []
        for i in range(count):
            img = Image.fromarray(
                np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
            )
            p = Path(tmpdir) / f"img_{i}.png"
            img.save(p)
            paths.append(p)
        return paths

    def test_multiple_images_grid(self):
        """Passing a list of 4 images renders a 2x2 grid."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._make_temp_images(tmpdir, count=4)
            buf = StringIO()
            imgcat(paths, renderer="sextants", width=60, grid_cols=2, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
            # Grid should show filenames by default
            assert paths[0].name in output

    def test_single_image_no_grid(self):
        """A single image path still renders normally (no grid)."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._make_temp_images(tmpdir, count=1)
            buf = StringIO()
            imgcat(paths[0], renderer="braille", width=20, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
            # Single-image path should NOT show filename title
            assert paths[0].name not in output

    def test_no_titles(self):
        """titles=False suppresses filenames in grid mode."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._make_temp_images(tmpdir, count=2)
            buf = StringIO()
            imgcat(paths, renderer="sextants", width=60, titles=False, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
            # No filenames should appear
            for p in paths:
                assert p.name not in output

    def test_grid_with_titles(self):
        """titles=True (default) shows filenames in grid mode."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._make_temp_images(tmpdir, count=2)
            buf = StringIO()
            imgcat(paths, renderer="sextants", width=60, titles=True, dest=buf)
            output = buf.getvalue()
            assert paths[0].name in output
            assert paths[1].name in output

    def test_single_item_list_no_grid(self):
        """A list with one image renders that image directly (no grid)."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._make_temp_images(tmpdir, count=1)
            buf = StringIO()
            imgcat(paths, renderer="braille", width=20, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0

    def test_grid_missing_file_skipped(self):
        """Missing files in a grid are skipped with warnings, not fatal."""
        from dapple.extras.imgcat import imgcat

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._make_temp_images(tmpdir, count=2)
            paths.insert(1, Path(tmpdir) / "nonexistent.png")
            buf = StringIO()
            # Should not raise; missing file is skipped
            imgcat(paths, renderer="sextants", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0


class TestGridCLI:
    """Tests for grid-mode CLI flags."""

    def test_cli_cols_flag(self):
        """--cols flag works with multiple images."""
        import subprocess

        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["a.png", "b.png", "c.png", "d.png"]:
                img = Image.new("RGB", (20, 20), color="blue")
                img.save(Path(tmpdir) / name)

            result = subprocess.run(
                [
                    "python", "-m", "dapple.extras.imgcat.imgcat",
                    "-r", "sextants", "-w", "60", "--cols", "2",
                    str(Path(tmpdir) / "a.png"),
                    str(Path(tmpdir) / "b.png"),
                    str(Path(tmpdir) / "c.png"),
                    str(Path(tmpdir) / "d.png"),
                ],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert len(result.stdout) > 0

    def test_cli_no_titles_flag(self):
        """--no-titles flag suppresses filenames in grid output."""
        import subprocess

        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["a.png", "b.png"]:
                img = Image.new("RGB", (20, 20), color="red")
                img.save(Path(tmpdir) / name)

            result = subprocess.run(
                [
                    "python", "-m", "dapple.extras.imgcat.imgcat",
                    "-r", "sextants", "-w", "60", "--no-titles",
                    str(Path(tmpdir) / "a.png"),
                    str(Path(tmpdir) / "b.png"),
                ],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert "a.png" not in result.stdout
            assert "b.png" not in result.stdout
