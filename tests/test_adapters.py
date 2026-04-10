"""Tests for dapple adapters (numpy, pil, matplotlib, cairo)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from dapple.canvas import Canvas

# ─── NumpyAdapter ────────────────────────────────────────────────────────────


class TestNumpyAdapter:
    """Tests for dapple.adapters.numpy."""

    def test_from_array_2d_grayscale(self):
        """2D array produces Canvas with bitmap only."""
        from dapple.adapters.numpy import from_array

        arr = np.random.rand(20, 40).astype(np.float32)
        canvas = from_array(arr)

        assert isinstance(canvas, Canvas)
        assert canvas.shape == (20, 40)
        assert canvas.colors is None
        np.testing.assert_allclose(canvas.bitmap, arr, atol=1e-6)

    def test_from_array_3d_rgb(self):
        """3D RGB array produces Canvas with bitmap + colors."""
        from dapple.adapters.numpy import from_array

        arr = np.random.rand(20, 40, 3).astype(np.float32)
        canvas = from_array(arr)

        assert isinstance(canvas, Canvas)
        assert canvas.shape == (20, 40)
        assert canvas.colors is not None
        assert canvas.colors.shape == (20, 40, 3)
        # Bitmap should be luminance
        expected_bitmap = (
            0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        )
        np.testing.assert_allclose(canvas.bitmap, expected_bitmap, atol=1e-5)

    def test_from_array_invalid_1d(self):
        """1D array raises ValueError."""
        from dapple.adapters.numpy import from_array

        with pytest.raises(ValueError, match="2D or 3D"):
            from_array(np.zeros(10))

    def test_from_array_invalid_4d(self):
        """4D array raises ValueError."""
        from dapple.adapters.numpy import from_array

        with pytest.raises(ValueError, match="2D or 3D"):
            from_array(np.zeros((2, 3, 4, 5)))

    def test_from_array_wrong_channels(self):
        """3D array with wrong channel count raises ValueError."""
        from dapple.adapters.numpy import from_array

        with pytest.raises(ValueError, match="H, W, 3"):
            from_array(np.zeros((10, 10, 4)))

    def test_numpy_adapter_class(self):
        """NumpyAdapter class works directly."""
        from dapple.adapters.numpy import NumpyAdapter

        arr = np.ones((8, 16), dtype=np.float32) * 0.5
        adapter = NumpyAdapter(arr)
        canvas = adapter.to_canvas()
        assert canvas.shape == (8, 16)

    def test_from_array_with_renderer(self):
        """from_array accepts renderer parameter."""
        from dapple.adapters.numpy import from_array
        from dapple import braille

        arr = np.zeros((10, 10), dtype=np.float32)
        canvas = from_array(arr, renderer=braille)
        assert canvas.default_renderer is braille


# ─── PILAdapter ──────────────────────────────────────────────────────────────


_has_pil = True
try:
    from PIL import Image as _Image
except ImportError:
    _has_pil = False


@pytest.mark.skipif(not _has_pil, reason="PIL not installed")
class TestPILAdapter:
    """Tests for dapple.adapters.pil."""

    def test_from_pil_rgb(self):
        """RGB PIL image produces Canvas with colors."""
        from PIL import Image
        from dapple.adapters.pil import from_pil

        img = Image.new("RGB", (40, 20), color=(255, 128, 0))
        canvas = from_pil(img)

        assert isinstance(canvas, Canvas)
        assert canvas.shape == (20, 40)
        assert canvas.colors is not None
        assert canvas.colors.shape == (20, 40, 3)

    def test_from_pil_grayscale(self):
        """Grayscale (L) PIL image produces Canvas without colors."""
        from PIL import Image
        from dapple.adapters.pil import from_pil

        img = Image.new("L", (40, 20), color=128)
        canvas = from_pil(img)

        assert canvas.shape == (20, 40)
        assert canvas.colors is None
        # All pixels should be ~128/255 ≈ 0.502
        np.testing.assert_allclose(canvas.bitmap, 128.0 / 255.0, atol=1e-3)

    def test_from_pil_rgba(self):
        """RGBA PIL image converts to RGB and produces Canvas with colors."""
        from PIL import Image
        from dapple.adapters.pil import from_pil

        img = Image.new("RGBA", (30, 15), color=(100, 200, 50, 128))
        canvas = from_pil(img)

        assert canvas.shape == (15, 30)
        assert canvas.colors is not None
        assert canvas.colors.shape == (15, 30, 3)

    def test_from_pil_palette_mode(self):
        """P mode (palette) image converts to grayscale."""
        from PIL import Image
        from dapple.adapters.pil import from_pil

        img = Image.new("P", (20, 10))
        canvas = from_pil(img)

        assert canvas.shape == (10, 20)
        assert canvas.colors is None

    def test_from_pil_binary_mode(self):
        """1 mode (binary) image converts to grayscale."""
        from PIL import Image
        from dapple.adapters.pil import from_pil

        img = Image.new("1", (20, 10), color=1)
        canvas = from_pil(img)

        assert canvas.shape == (10, 20)

    def test_load_image(self):
        """load_image loads a file and returns Canvas."""
        from PIL import Image
        from dapple.adapters.pil import load_image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (60, 30), color=(255, 0, 0))
            img.save(f.name)
            path = Path(f.name)

        try:
            canvas = load_image(path)
            assert canvas.shape == (30, 60)
            assert canvas.colors is not None
        finally:
            path.unlink()

    def test_load_image_with_width(self):
        """load_image resizes proportionally when width is given."""
        from PIL import Image
        from dapple.adapters.pil import load_image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 50), color=(0, 255, 0))
            img.save(f.name)
            path = Path(f.name)

        try:
            canvas = load_image(path, width=50)
            assert canvas.pixel_width == 50
            assert canvas.pixel_height == 25  # proportional
        finally:
            path.unlink()

    def test_load_image_with_width_and_height(self):
        """load_image resizes to exact dims when both width and height given."""
        from PIL import Image
        from dapple.adapters.pil import load_image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 50), color=(0, 0, 255))
            img.save(f.name)
            path = Path(f.name)

        try:
            canvas = load_image(path, width=40, height=30)
            assert canvas.pixel_width == 40
            assert canvas.pixel_height == 30
        finally:
            path.unlink()

    def test_pil_adapter_type_check(self):
        """PILAdapter rejects non-Image objects."""
        from dapple.adapters.pil import PILAdapter

        with pytest.raises(TypeError, match="Expected PIL Image"):
            PILAdapter("not an image")

    def test_from_pil_with_renderer(self):
        """from_pil accepts renderer parameter."""
        from PIL import Image
        from dapple.adapters.pil import from_pil
        from dapple import braille

        img = Image.new("L", (20, 10))
        canvas = from_pil(img, renderer=braille)
        assert canvas.default_renderer is braille

    def test_pil_adapter_resize_height_only(self):
        """PILAdapter resizes proportionally with height only."""
        from PIL import Image
        from dapple.adapters.pil import PILAdapter

        img = Image.new("RGB", (100, 50))
        adapter = PILAdapter(img, height=25)
        canvas = adapter.to_canvas()
        assert canvas.pixel_height == 25
        assert canvas.pixel_width == 50  # proportional


# ─── MatplotlibAdapter ───────────────────────────────────────────────────────

_has_matplotlib = True
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    _has_matplotlib = False


@pytest.mark.skipif(not _has_matplotlib, reason="matplotlib not installed")
class TestMatplotlibAdapter:
    """Tests for dapple.adapters.matplotlib."""

    def test_to_canvas(self):
        """to_canvas renders a figure to Canvas with bitmap and colors."""
        from dapple.adapters.matplotlib import from_matplotlib

        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([0, 1, 2], [0, 1, 0])

        canvas = from_matplotlib(fig)
        plt.close(fig)

        assert isinstance(canvas, Canvas)
        assert canvas.bitmap.ndim == 2
        assert canvas.colors is not None
        assert canvas.colors.shape[2] == 3
        assert canvas.pixel_height > 0
        assert canvas.pixel_width > 0

    def test_to_canvas_with_width(self):
        """to_canvas respects width parameter."""
        from dapple.adapters.matplotlib import from_matplotlib

        fig, ax = plt.subplots(figsize=(4, 3))
        ax.bar([1, 2, 3], [10, 20, 15])

        canvas = from_matplotlib(fig, width=200, dpi=100)
        plt.close(fig)

        assert isinstance(canvas, Canvas)
        assert canvas.colors is not None

    def test_matplotlib_adapter_type_check(self):
        """MatplotlibAdapter rejects non-Figure objects."""
        from dapple.adapters.matplotlib import MatplotlibAdapter

        with pytest.raises(TypeError, match="Expected Matplotlib Figure"):
            MatplotlibAdapter("not a figure")

    def test_matplotlib_adapter_class(self):
        """MatplotlibAdapter class works directly."""
        from dapple.adapters.matplotlib import MatplotlibAdapter

        fig, ax = plt.subplots(figsize=(3, 2))
        ax.scatter([1, 2], [3, 4])

        adapter = MatplotlibAdapter(fig)
        canvas = adapter.to_canvas()
        plt.close(fig)

        assert canvas.bitmap.ndim == 2
        assert canvas.colors is not None

    def test_figure_size_not_permanently_mutated(self):
        """to_canvas must restore the original figure size.

        Regression test: the adapter used to call set_size_inches() and
        leave the caller's figure at the new size, which surprised callers
        who thought they had a plot-and-export pipeline.
        """
        from dapple.adapters.matplotlib import from_matplotlib

        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([0, 1, 2], [0, 1, 0])
        original_size = tuple(fig.get_size_inches())

        # Force a size change that is different from the original.
        from_matplotlib(fig, width=800, dpi=100)

        new_size = tuple(fig.get_size_inches())
        plt.close(fig)

        assert new_size == original_size, (
            f"Figure size was mutated: {original_size} -> {new_size}"
        )


# ─── CairoAdapter ────────────────────────────────────────────────────────────

_has_cairo = True
try:
    import cairo as _cairo
except ImportError:
    _has_cairo = False


@pytest.mark.skipif(not _has_cairo, reason="pycairo not installed")
class TestCairoAdapter:
    """Tests for dapple.adapters.cairo."""

    def test_to_canvas_argb32(self):
        """ARGB32 surface produces Canvas with bitmap and colors."""
        import cairo
        from dapple.adapters.cairo import from_cairo

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 80, 40)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(1, 0, 0)
        ctx.rectangle(0, 0, 80, 40)
        ctx.fill()
        surface.flush()

        canvas = from_cairo(surface)

        assert isinstance(canvas, Canvas)
        assert canvas.shape == (40, 80)
        assert canvas.colors is not None
        assert canvas.colors.shape == (40, 80, 3)
        # Red rectangle: R=1, G=0, B=0
        np.testing.assert_allclose(canvas.colors[20, 40, 0], 1.0, atol=0.01)
        np.testing.assert_allclose(canvas.colors[20, 40, 1], 0.0, atol=0.01)
        np.testing.assert_allclose(canvas.colors[20, 40, 2], 0.0, atol=0.01)

    def test_to_canvas_rgb24(self):
        """RGB24 surface produces Canvas with bitmap and colors."""
        import cairo
        from dapple.adapters.cairo import from_cairo

        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 50, 30)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(0, 1, 0)
        ctx.rectangle(0, 0, 50, 30)
        ctx.fill()
        surface.flush()

        canvas = from_cairo(surface)

        assert canvas.shape == (30, 50)
        assert canvas.colors is not None
        # Green fill
        np.testing.assert_allclose(canvas.colors[15, 25, 1], 1.0, atol=0.01)

    def test_to_canvas_a8(self):
        """A8 surface produces grayscale Canvas without colors."""
        import cairo
        from dapple.adapters.cairo import from_cairo

        surface = cairo.ImageSurface(cairo.FORMAT_A8, 40, 20)
        ctx = cairo.Context(surface)
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(0, 0, 40, 20)
        ctx.fill()
        surface.flush()

        canvas = from_cairo(surface)

        assert canvas.shape == (20, 40)
        assert canvas.colors is None

    def test_cairo_adapter_type_check(self):
        """CairoAdapter rejects non-ImageSurface objects."""
        from dapple.adapters.cairo import CairoAdapter

        with pytest.raises(TypeError, match="Expected Cairo ImageSurface"):
            CairoAdapter("not a surface")

    def test_cairo_adapter_with_renderer(self):
        """CairoAdapter accepts renderer parameter."""
        import cairo
        from dapple.adapters.cairo import CairoAdapter
        from dapple import braille

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 20, 10)
        surface.flush()

        adapter = CairoAdapter(surface, renderer=braille)
        canvas = adapter.to_canvas()
        assert canvas.default_renderer is braille
