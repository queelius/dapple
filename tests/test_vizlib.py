"""Tests for vizlib chart primitives."""

import numpy as np
import pytest

from dapple.canvas import Canvas

from dapple.extras.vizlib.charts import bar_chart, heatmap, histogram, line_plot, sparkline
from dapple.extras.vizlib.colors import COLOR_PALETTE, NAMED_COLORS, parse_color
from dapple.extras.vizlib.render import get_renderer, get_terminal_size, pixel_dimensions

# Renderer names supported by vizlib.get_renderer (delegates to common.get_renderer)
_RENDERER_NAMES = ["braille", "quadrants", "sextants", "ascii", "sixel", "kitty"]


# ── Color tests ──────────────────────────────────────────────────────


class TestColors:
    def test_parse_named_color(self):
        assert parse_color("cyan") == NAMED_COLORS["cyan"]
        assert parse_color("Red") == NAMED_COLORS["red"]

    def test_parse_hex_color(self):
        r, g, b = parse_color("#ff0000")
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)

    def test_parse_short_hex(self):
        r, g, b = parse_color("#f00")
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)

    def test_parse_invalid_color(self):
        with pytest.raises(ValueError, match="Unknown color"):
            parse_color("neon_purple")

    def test_parse_invalid_hex(self):
        with pytest.raises(ValueError, match="Invalid hex"):
            parse_color("#12345")

    def test_palette_length(self):
        assert len(COLOR_PALETTE) == 8


# ── Renderer tests ───────────────────────────────────────────────────


class TestRender:
    def test_get_renderer_braille(self):
        r = get_renderer("braille")
        assert r.cell_width == 2
        assert r.cell_height == 4

    def test_get_renderer_unknown(self):
        with pytest.raises(ValueError, match="Unknown renderer"):
            get_renderer("nonexistent")

    def test_all_renderers_accessible(self):
        for name in _RENDERER_NAMES:
            r = get_renderer(name)
            assert r.cell_width > 0
            assert r.cell_height > 0

    def test_terminal_size(self):
        cols, lines = get_terminal_size()
        assert cols > 0
        assert lines > 0

    def test_pixel_dimensions(self):
        from dapple import braille
        pw, ph = pixel_dimensions(braille, 80, 24)
        assert pw == 80 * 2  # braille cell_width = 2
        assert ph == 24 * 4  # braille cell_height = 4


# ── Sparkline tests ──────────────────────────────────────────────────


class TestSparkline:
    def test_basic(self):
        canvas = sparkline([1, 2, 3, 4, 5], width=40, height=20)
        assert isinstance(canvas, Canvas)
        assert canvas.pixel_width == 40
        assert canvas.pixel_height == 20

    def test_has_content(self):
        canvas = sparkline([1, 5, 2, 8, 3], width=40, height=20)
        assert canvas.bitmap.max() > 0

    def test_custom_color(self):
        canvas = sparkline([1, 2, 3], width=20, height=10, color=(1.0, 0.0, 0.0))
        assert canvas.colors is not None
        # Red channel should be present somewhere
        assert canvas.colors[:, :, 0].max() > 0

    def test_constant_values(self):
        canvas = sparkline([5, 5, 5, 5], width=20, height=10)
        assert isinstance(canvas, Canvas)
        assert canvas.bitmap.max() > 0

    def test_single_value(self):
        canvas = sparkline([42], width=20, height=10)
        assert isinstance(canvas, Canvas)

    def test_empty(self):
        canvas = sparkline([], width=20, height=10)
        assert canvas.bitmap.max() == 0

    def test_negative_values(self):
        canvas = sparkline([-3, -1, 0, 1, 3], width=40, height=20)
        assert canvas.bitmap.max() > 0


# ── Line plot tests ──────────────────────────────────────────────────


class TestLinePlot:
    def test_basic(self):
        canvas = line_plot([1, 4, 2, 8, 5], width=40, height=20)
        assert isinstance(canvas, Canvas)
        assert canvas.pixel_width == 40

    def test_with_axes(self):
        canvas = line_plot([-2, -1, 0, 1, 2], width=40, height=20, show_axes=True)
        assert canvas.bitmap.max() > 0
        # Axis should add some gray (0.3 brightness) pixels
        axis_pixels = np.isclose(canvas.colors[:, :, 0], 0.5, atol=0.1)
        assert axis_pixels.any()

    def test_without_axes(self):
        canvas = line_plot([1, 2, 3], width=40, height=20, show_axes=False)
        assert canvas.bitmap.max() > 0

    def test_empty(self):
        canvas = line_plot([], width=20, height=10)
        assert canvas.bitmap.max() == 0


# ── Bar chart tests ──────────────────────────────────────────────────


class TestBarChart:
    def test_horizontal(self):
        canvas = bar_chart(["a", "b", "c"], [3, 7, 5], width=40, height=30)
        assert isinstance(canvas, Canvas)
        assert canvas.bitmap.max() > 0

    def test_vertical(self):
        canvas = bar_chart(
            ["x", "y", "z"], [10, 20, 15],
            width=60, height=30, horizontal=False,
        )
        assert canvas.bitmap.max() > 0

    def test_single_bar(self):
        canvas = bar_chart(["only"], [42], width=40, height=20)
        assert canvas.bitmap.max() > 0

    def test_custom_color(self):
        canvas = bar_chart(
            ["a", "b"], [5, 10],
            width=40, height=20, color=(0.0, 1.0, 0.0),
        )
        assert canvas.colors[:, :, 1].max() > 0  # Green present

    def test_empty(self):
        canvas = bar_chart([], [], width=20, height=10)
        assert canvas.bitmap.max() == 0

    def test_zero_values(self):
        canvas = bar_chart(["a", "b"], [0, 0], width=40, height=20)
        assert isinstance(canvas, Canvas)


# ── Histogram tests ──────────────────────────────────────────────────


class TestHistogram:
    def test_basic(self):
        data = list(np.random.randn(100))
        canvas = histogram(data, width=60, height=20)
        assert isinstance(canvas, Canvas)
        assert canvas.bitmap.max() > 0

    def test_custom_bins(self):
        data = list(range(50))
        canvas = histogram(data, width=60, height=20, bins=10)
        assert canvas.bitmap.max() > 0

    def test_uniform_data(self):
        data = [5.0] * 20
        canvas = histogram(data, width=40, height=20, bins=5)
        assert isinstance(canvas, Canvas)

    def test_empty(self):
        canvas = histogram([], width=20, height=10)
        assert canvas.bitmap.max() == 0


# ── Heatmap tests ────────────────────────────────────────────────────


class TestHeatmap:
    def test_basic_2d(self):
        data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        canvas = heatmap(data, width=30, height=30)
        assert isinstance(canvas, Canvas)
        assert canvas.bitmap.max() > 0

    def test_1d_input(self):
        canvas = heatmap([1, 2, 3, 4, 5], width=50, height=10)
        assert isinstance(canvas, Canvas)
        assert canvas.bitmap.max() > 0

    def test_color_gradient(self):
        # Low values should be blue-ish, high values red-ish
        data = [[0, 0], [100, 100]]
        canvas = heatmap(data, width=20, height=20)
        # Top-left should be bluer (cold)
        assert canvas.colors[0, 0, 2] > 0  # Blue channel
        # Bottom-right should be redder (hot)
        assert canvas.colors[-1, -1, 0] > 0  # Red channel

    def test_constant_data(self):
        data = [[5, 5], [5, 5]]
        canvas = heatmap(data, width=20, height=20)
        assert isinstance(canvas, Canvas)

    def test_empty(self):
        canvas = heatmap([[]], width=20, height=10)
        # Empty inner array → empty data
        assert isinstance(canvas, Canvas)


# ── Integration: Canvas renders with dapple ──────────────────────────


class TestIntegration:
    def test_sparkline_renders_to_string(self):
        from dapple import braille
        canvas = sparkline([1, 3, 2, 5, 4], width=40, height=16)
        output = []
        from io import StringIO
        buf = StringIO()
        braille(threshold=0.2, color_mode="truecolor").render(
            canvas.bitmap, canvas.colors, dest=buf,
        )
        result = buf.getvalue()
        assert len(result) > 0

    def test_bar_chart_renders_to_string(self):
        from dapple import sextants
        canvas = bar_chart(["a", "b"], [3, 7], width=40, height=18)
        from io import StringIO
        buf = StringIO()
        sextants(true_color=True).render(
            canvas.bitmap, canvas.colors, dest=buf,
        )
        result = buf.getvalue()
        assert len(result) > 0
