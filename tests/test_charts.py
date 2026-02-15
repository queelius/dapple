"""Tests for dapple.charts character-dimension chart API."""

from __future__ import annotations

import pytest

from dapple.charts import sparkline, line_plot, bar_chart, histogram, heatmap


class TestSparkline:
    def test_returns_canvas(self):
        chart = sparkline([1, 4, 2, 8, 3, 7], width=40, height=4)
        assert chart.shape[1] == 40 * 2  # 2 px per char
        assert chart.shape[0] == 4 * 4   # 4 px per char

    def test_empty_values(self):
        chart = sparkline([], width=20, height=4)
        assert chart.shape == (16, 40)

    def test_has_colors(self):
        chart = sparkline([1, 2, 3], width=20, height=4)
        assert chart.colors is not None


class TestLinePlot:
    def test_returns_canvas(self):
        chart = line_plot([1, 2, 3, 4, 5], width=40, height=20)
        assert chart.shape[1] == 80
        assert chart.shape[0] == 80

    def test_custom_color(self):
        chart = line_plot([1, 2, 3], width=20, height=10, color=(1.0, 0.0, 0.0))
        assert chart.colors is not None


class TestBarChart:
    def test_returns_canvas(self):
        chart = bar_chart(["A", "B", "C"], [10, 20, 30], width=40, height=20)
        assert chart.shape[1] == 80
        assert chart.shape[0] == 80

    def test_vertical(self):
        chart = bar_chart(["A", "B"], [10, 20], width=30, height=15, horizontal=False)
        assert chart.shape == (60, 60)


class TestHistogram:
    def test_returns_canvas(self):
        import numpy as np
        values = np.random.randn(100).tolist()
        chart = histogram(values, width=40, height=20, bins=10)
        assert chart.shape[1] == 80


class TestHeatmap:
    def test_returns_canvas(self):
        data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        chart = heatmap(data, width=30, height=10)
        assert chart.shape[1] == 60
        assert chart.shape[0] == 40

    def test_auto_height(self):
        data = [[1, 2], [3, 4]]
        chart = heatmap(data, width=20)
        assert chart.shape[1] == 40
