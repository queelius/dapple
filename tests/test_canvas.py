"""Tests for Canvas class."""

import sys
from io import StringIO

import numpy as np
import pytest

from dapple import Canvas, braille, quadrants, ascii


class TestCanvasInit:
    """Tests for Canvas initialization."""

    def test_basic_init(self):
        """Canvas initializes with 2D bitmap."""
        bitmap = np.zeros((10, 20), dtype=np.float32)
        canvas = Canvas(bitmap)
        assert canvas.pixel_height == 10
        assert canvas.pixel_width == 20

    def test_init_with_colors(self):
        """Canvas accepts colors array."""
        bitmap = np.zeros((10, 20), dtype=np.float32)
        colors = np.zeros((10, 20, 3), dtype=np.float32)
        canvas = Canvas(bitmap, colors=colors)
        assert canvas.colors is not None
        assert canvas.colors.shape == (10, 20, 3)

    def test_init_with_renderer(self):
        """Canvas accepts default renderer."""
        bitmap = np.zeros((10, 20), dtype=np.float32)
        canvas = Canvas(bitmap, renderer=quadrants)
        assert canvas.default_renderer is quadrants

    def test_invalid_bitmap_1d(self):
        """Canvas rejects 1D array."""
        with pytest.raises(ValueError, match="must be 2D"):
            Canvas(np.zeros(10))

    def test_invalid_bitmap_3d(self):
        """Canvas rejects 3D array without colors."""
        with pytest.raises(ValueError, match="must be 2D"):
            Canvas(np.zeros((10, 20, 3)))

    def test_invalid_colors_shape(self):
        """Canvas rejects mismatched colors shape."""
        bitmap = np.zeros((10, 20), dtype=np.float32)
        colors = np.zeros((5, 10, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="must match bitmap"):
            Canvas(bitmap, colors=colors)

    def test_invalid_colors_channels(self):
        """Canvas rejects non-RGB colors."""
        bitmap = np.zeros((10, 20), dtype=np.float32)
        colors = np.zeros((10, 20, 4), dtype=np.float32)
        with pytest.raises(ValueError, match="must be.*H, W, 3"):
            Canvas(bitmap, colors=colors)


class TestCanvasProperties:
    """Tests for Canvas properties."""

    def test_shape(self):
        """shape returns (H, W) tuple."""
        canvas = Canvas(np.zeros((10, 20)))
        assert canvas.shape == (10, 20)

    def test_size(self):
        """size returns (W, H) tuple (PIL convention)."""
        canvas = Canvas(np.zeros((10, 20)))
        assert canvas.size == (20, 10)

    def test_bitmap_readonly(self):
        """bitmap property returns read-only view."""
        canvas = Canvas(np.zeros((10, 20)))
        bitmap = canvas.bitmap
        with pytest.raises(ValueError):
            bitmap[0, 0] = 1.0

    def test_colors_readonly(self):
        """colors property returns read-only view."""
        bitmap = np.zeros((10, 20), dtype=np.float32)
        colors = np.zeros((10, 20, 3), dtype=np.float32)
        canvas = Canvas(bitmap, colors=colors)
        colors_view = canvas.colors
        with pytest.raises(ValueError):
            colors_view[0, 0, 0] = 1.0

    def test_colors_none(self):
        """colors returns None when no colors set."""
        canvas = Canvas(np.zeros((10, 20)))
        assert canvas.colors is None


class TestCanvasOut:
    """Tests for Canvas out() method."""

    def test_out_to_stringio(self):
        """out() writes to StringIO."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        buf = StringIO()
        canvas.out(braille, buf)
        result = buf.getvalue()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_out_braille(self):
        """out() with braille writes output."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        buf = StringIO()
        canvas.out(braille, buf)
        assert len(buf.getvalue()) > 0

    def test_out_quadrants(self):
        """out() with quadrants writes output with ANSI codes."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        buf = StringIO()
        canvas.out(quadrants, buf)
        result = buf.getvalue()
        assert "\033[" in result

    def test_out_ascii(self):
        """out() with ascii writes output."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        buf = StringIO()
        canvas.out(ascii, buf)
        assert len(buf.getvalue()) > 0

    def test_out_to_file(self, tmp_path):
        """out() writes to file path."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        file_path = tmp_path / "output.txt"
        canvas.out(braille, str(file_path))
        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_out_to_file_handle(self, tmp_path):
        """out() writes to open file handle."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        file_path = tmp_path / "output.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            canvas.out(braille, f)
        content = file_path.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_out_default_stdout(self, monkeypatch):
        """out() defaults to stdout."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        buf = StringIO()
        monkeypatch.setattr(sys, "stdout", buf)
        canvas.out(braille)
        assert len(buf.getvalue()) > 0

    def test_out_to_stderr(self, monkeypatch):
        """out() can write to stderr."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        buf = StringIO()
        monkeypatch.setattr(sys, "stderr", buf)
        canvas.out(braille, sys.stderr)
        assert len(buf.getvalue()) > 0


class TestCanvasStr:
    """Tests for Canvas __str__ method."""

    def test_str_uses_default_braille(self):
        """__str__ uses braille by default."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap)
        result = str(canvas)
        # Braille uses unicode braille characters
        assert isinstance(result, str)
        assert len(result) > 0

    def test_str_uses_custom_renderer(self):
        """__str__ uses custom default renderer."""
        bitmap = np.random.rand(8, 8).astype(np.float32)
        canvas = Canvas(bitmap, renderer=quadrants)
        result = str(canvas)
        # Should be quadrants output (with ANSI codes)
        assert "\033[" in result


class TestCanvasRepr:
    """Tests for Canvas repr."""

    def test_repr_basic(self):
        """__repr__ shows dimensions."""
        canvas = Canvas(np.zeros((10, 20)))
        r = repr(canvas)
        assert "Canvas" in r
        assert "10x20" in r

    def test_repr_with_colors(self):
        """__repr__ indicates colors."""
        bitmap = np.zeros((10, 20), dtype=np.float32)
        colors = np.zeros((10, 20, 3), dtype=np.float32)
        canvas = Canvas(bitmap, colors=colors)
        r = repr(canvas)
        assert "colors=True" in r

    def test_repr_with_renderer(self):
        """__repr__ indicates renderer."""
        canvas = Canvas(np.zeros((10, 20)), renderer=quadrants)
        r = repr(canvas)
        assert "QuadrantsRenderer" in r


class TestCanvasPixelAccess:
    """Tests for Canvas pixel access."""

    def test_getitem_single(self):
        """__getitem__ returns single pixel."""
        bitmap = np.arange(20).reshape(4, 5).astype(np.float32)
        canvas = Canvas(bitmap)
        assert canvas[0, 0] == 0.0
        assert canvas[1, 2] == 7.0

    def test_getitem_slice(self):
        """__getitem__ returns sliced array."""
        bitmap = np.arange(20).reshape(4, 5).astype(np.float32)
        canvas = Canvas(bitmap)
        sliced = canvas[1:3, 2:4]
        assert sliced.shape == (2, 2)
        np.testing.assert_array_equal(sliced, [[7, 8], [12, 13]])


class TestCanvasBuilder:
    """Tests for Canvas builder methods."""

    def test_with_renderer(self):
        """with_renderer returns new Canvas with different renderer."""
        canvas1 = Canvas(np.zeros((10, 20)))
        canvas2 = canvas1.with_renderer(quadrants)
        assert canvas1._renderer is None
        assert canvas2._renderer is quadrants
        # Same bitmap
        np.testing.assert_array_equal(canvas1.bitmap, canvas2.bitmap)

    def test_with_invert(self):
        """with_invert returns new Canvas with inverted bitmap."""
        bitmap = np.array([[0.0, 0.5], [0.25, 1.0]], dtype=np.float32)
        canvas = Canvas(bitmap)
        inverted = canvas.with_invert()
        expected = np.array([[1.0, 0.5], [0.75, 0.0]], dtype=np.float32)
        np.testing.assert_array_almost_equal(inverted.bitmap, expected)


class TestCanvasComposition:
    """Tests for Canvas composition methods."""

    def test_hstack(self):
        """hstack combines canvases horizontally."""
        left = Canvas(np.ones((4, 2)))
        right = Canvas(np.zeros((4, 3)))
        combined = left.hstack(right)
        assert combined.shape == (4, 5)
        np.testing.assert_array_equal(combined.bitmap[:, :2], 1.0)
        np.testing.assert_array_equal(combined.bitmap[:, 2:], 0.0)

    def test_hstack_height_mismatch(self):
        """hstack rejects mismatched heights."""
        left = Canvas(np.ones((4, 2)))
        right = Canvas(np.zeros((6, 3)))
        with pytest.raises(ValueError, match="Heights must match"):
            left.hstack(right)

    def test_vstack(self):
        """vstack combines canvases vertically."""
        top = Canvas(np.ones((2, 4)))
        bottom = Canvas(np.zeros((3, 4)))
        combined = top.vstack(bottom)
        assert combined.shape == (5, 4)
        np.testing.assert_array_equal(combined.bitmap[:2, :], 1.0)
        np.testing.assert_array_equal(combined.bitmap[2:, :], 0.0)

    def test_vstack_width_mismatch(self):
        """vstack rejects mismatched widths."""
        top = Canvas(np.ones((2, 4)))
        bottom = Canvas(np.zeros((3, 6)))
        with pytest.raises(ValueError, match="Widths must match"):
            top.vstack(bottom)

    def test_add_operator(self):
        """+ operator performs hstack."""
        left = Canvas(np.ones((4, 2)))
        right = Canvas(np.zeros((4, 3)))
        combined = left + right
        assert combined.shape == (4, 5)

    def test_overlay(self):
        """overlay places one canvas on another."""
        base = Canvas(np.zeros((10, 10)))
        overlay = Canvas(np.ones((4, 4)))
        result = base.overlay(overlay, 3, 2)
        # Check overlay region
        np.testing.assert_array_equal(result.bitmap[2:6, 3:7], 1.0)
        # Check surrounding is still zero
        assert result.bitmap[0, 0] == 0.0
        assert result.bitmap[9, 9] == 0.0

    def test_overlay_partial(self):
        """overlay handles partial overlap."""
        base = Canvas(np.zeros((10, 10)))
        overlay = Canvas(np.ones((4, 4)))
        # Overlay extends past edge
        result = base.overlay(overlay, 8, 8)
        # Only 2x2 region should be affected
        np.testing.assert_array_equal(result.bitmap[8:10, 8:10], 1.0)
        assert result.bitmap[7, 7] == 0.0

    def test_crop(self):
        """crop extracts rectangular region."""
        bitmap = np.arange(20).reshape(4, 5).astype(np.float32)
        canvas = Canvas(bitmap)
        cropped = canvas.crop(1, 1, 4, 3)
        assert cropped.shape == (2, 3)
        np.testing.assert_array_equal(
            cropped.bitmap,
            [[6, 7, 8], [11, 12, 13]],
        )

    def test_crop_invalid(self):
        """crop rejects invalid coordinates."""
        canvas = Canvas(np.zeros((10, 10)))
        with pytest.raises(ValueError, match="out of bounds"):
            canvas.crop(-1, 0, 5, 5)
        with pytest.raises(ValueError, match="out of bounds"):
            canvas.crop(0, 0, 15, 5)
        with pytest.raises(ValueError, match="Invalid crop"):
            canvas.crop(5, 5, 3, 3)


class TestCanvasConversion:
    """Tests for Canvas conversion methods."""

    def test_to_bitmap(self):
        """to_bitmap returns copy of bitmap."""
        bitmap = np.arange(20).reshape(4, 5).astype(np.float32)
        canvas = Canvas(bitmap)
        result = canvas.to_bitmap()
        np.testing.assert_array_equal(result, bitmap)
        # Should be a copy
        result[0, 0] = 999
        assert canvas.bitmap[0, 0] != 999


class TestFromArray:
    """Tests for from_array factory function."""

    def test_from_grayscale(self):
        """from_array handles 2D grayscale."""
        from dapple import from_array

        array = np.random.rand(10, 20).astype(np.float32)
        canvas = from_array(array)
        assert canvas.shape == (10, 20)
        assert canvas.colors is None

    def test_from_rgb(self):
        """from_array handles 3D RGB."""
        from dapple import from_array

        array = np.random.rand(10, 20, 3).astype(np.float32)
        canvas = from_array(array)
        assert canvas.shape == (10, 20)
        assert canvas.colors is not None
        assert canvas.colors.shape == (10, 20, 3)


class TestFromPilUnified:
    """Tests for unified from_pil (from adapters.pil via __init__)."""

    def test_from_pil_supports_width(self):
        """from dapple import from_pil now supports width parameter."""
        from PIL import Image

        from dapple import from_pil

        img = Image.new("RGB", (100, 50), color=(255, 0, 0))
        canvas = from_pil(img, width=50)
        assert canvas.pixel_width == 50
        assert canvas.pixel_height == 25  # proportional

    def test_from_pil_supports_height(self):
        """from dapple import from_pil now supports height parameter."""
        from PIL import Image

        from dapple import from_pil

        img = Image.new("RGB", (100, 50), color=(0, 255, 0))
        canvas = from_pil(img, height=25)
        assert canvas.pixel_height == 25
        assert canvas.pixel_width == 50  # proportional


class TestPreprocessExports:
    """Tests for preprocessing function exports from dapple package."""

    def test_crop_export(self):
        """crop is importable from dapple."""
        from dapple import crop

        bitmap = np.ones((10, 20), dtype=np.float32)
        result = crop(bitmap, 2, 2, 5, 5)
        assert result.shape == (5, 5)

    def test_flip_export(self):
        """flip is importable from dapple."""
        from dapple import flip

        bitmap = np.array([[1, 0], [0, 0]], dtype=np.float32)
        result = flip(bitmap, "h")
        assert result[0, 0] == 0.0
        assert result[0, 1] == 1.0

    def test_rotate_export(self):
        """rotate is importable from dapple."""
        from dapple import rotate

        bitmap = np.array([[1, 0], [0, 0]], dtype=np.float32)
        result = rotate(bitmap, 90)
        assert result.shape == (2, 2)


class TestCanvasColorComposition:
    """Tests for Canvas composition with colors."""

    def test_hstack_both_colors(self):
        """hstack preserves colors when both have them."""
        left_bm = np.ones((4, 2), dtype=np.float32)
        left_colors = np.zeros((4, 2, 3), dtype=np.float32)
        left_colors[:, :, 0] = 1.0  # Red

        right_bm = np.ones((4, 3), dtype=np.float32)
        right_colors = np.zeros((4, 3, 3), dtype=np.float32)
        right_colors[:, :, 2] = 1.0  # Blue

        left = Canvas(left_bm, colors=left_colors)
        right = Canvas(right_bm, colors=right_colors)
        combined = left.hstack(right)

        assert combined.colors is not None
        assert combined.colors.shape == (4, 5, 3)
        # Left should be red
        np.testing.assert_array_equal(combined.colors[:, :2, 0], 1.0)
        np.testing.assert_array_equal(combined.colors[:, :2, 2], 0.0)
        # Right should be blue
        np.testing.assert_array_equal(combined.colors[:, 2:, 0], 0.0)
        np.testing.assert_array_equal(combined.colors[:, 2:, 2], 1.0)

    def test_hstack_one_color(self):
        """hstack converts grayscale to colors when one has colors."""
        left_bm = np.ones((4, 2), dtype=np.float32) * 0.5
        left_colors = np.zeros((4, 2, 3), dtype=np.float32)
        left_colors[:, :, 0] = 1.0  # Red

        right_bm = np.ones((4, 3), dtype=np.float32) * 0.8

        left = Canvas(left_bm, colors=left_colors)
        right = Canvas(right_bm)  # No colors
        combined = left.hstack(right)

        assert combined.colors is not None
        # Right should be converted to grayscale colors
        np.testing.assert_array_almost_equal(combined.colors[:, 2:, 0], 0.8)
        np.testing.assert_array_almost_equal(combined.colors[:, 2:, 1], 0.8)
        np.testing.assert_array_almost_equal(combined.colors[:, 2:, 2], 0.8)
