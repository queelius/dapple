"""Tests for dapple.textchart text-based chart formatters."""

from __future__ import annotations

import math

import pytest

from dapple.textchart import _format_value, text_bar_chart, text_sparkline


class TestTextBarChart:
    def test_basic_output(self):
        output = text_bar_chart(["A", "B", "C"], [10, 20, 30], width=60)
        assert "A" in output
        assert "B" in output
        assert "C" in output

    def test_values_shown(self):
        output = text_bar_chart(["X"], [42], width=60)
        assert "42" in output

    def test_proportional_bars(self):
        output = text_bar_chart(["Small", "Big"], [10, 100], width=80)
        lines = [l for l in output.split("\n") if l.strip()]
        small_blocks = sum(1 for c in lines[0] if c == "█")
        big_blocks = sum(1 for c in lines[1] if c == "█")
        assert big_blocks > small_blocks

    def test_empty_input(self):
        assert text_bar_chart([], []) == ""

    def test_empty_values_only(self):
        assert text_bar_chart(["A"], []) == ""

    def test_empty_labels_only(self):
        assert text_bar_chart([], [1]) == ""

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError, match="must have the same length"):
            text_bar_chart(["A", "B"], [1], width=60)

    def test_inf_value(self):
        output = text_bar_chart(["A"], [math.inf], width=60)
        assert "inf" in output

    def test_neg_inf_value(self):
        output = text_bar_chart(["A", "B"], [-math.inf, 10], width=60)
        assert "-inf" in output
        assert "10" in output

    def test_nan_value(self):
        output = text_bar_chart(["A"], [math.nan], width=60)
        assert "nan" in output

    def test_mixed_inf_and_finite(self):
        output = text_bar_chart(["A", "B", "C"], [math.inf, 10, math.nan], width=60)
        assert "A" in output
        assert "B" in output
        assert "C" in output

    def test_all_zero_values(self):
        output = text_bar_chart(["A", "B"], [0, 0], width=60)
        assert "A" in output
        assert "B" in output
        assert "0" in output

    def test_negative_values(self):
        output = text_bar_chart(["A", "B"], [-10, -20], width=60)
        lines = [l for l in output.split("\n") if l.strip()]
        assert "-10" in output
        assert "-20" in output
        # Bars should be proportional to abs(val): -20 should have a bigger bar
        big_blocks = sum(1 for c in lines[1] if c == "█")
        small_blocks = sum(1 for c in lines[0] if c == "█")
        assert big_blocks > small_blocks

    def test_large_number_of_items(self):
        n = 60
        labels = [f"item_{i}" for i in range(n)]
        values = [float(i) for i in range(n)]
        output = text_bar_chart(labels, values, width=80)
        assert "item_0" in output
        assert "item_59" in output

    def test_title_shown(self):
        output = text_bar_chart(["A"], [1], width=60, title="score")
        assert "score" in output


class TestTextSparkline:
    def test_basic_output(self):
        output = text_sparkline(["A", "B", "C"], [10, 20, 30])
        assert "A" in output
        assert "B" in output
        assert "C" in output

    def test_values_shown(self):
        output = text_sparkline(["X"], [42])
        assert "42" in output

    def test_spark_chars(self):
        output = text_sparkline(["Lo", "Hi"], [1, 100])
        assert "▁" in output
        assert "█" in output

    def test_min_max_summary(self):
        output = text_sparkline(["A", "B"], [10, 50])
        assert "min:" in output
        assert "max:" in output

    def test_empty_input(self):
        assert text_sparkline([], []) == ""

    def test_empty_values_only(self):
        assert text_sparkline(["A"], []) == ""

    def test_empty_labels_only(self):
        assert text_sparkline([], [1]) == ""

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError, match="must have the same length"):
            text_sparkline(["A", "B"], [1])

    def test_single_value(self):
        """When min==max, the function adjusts range by +/-0.5 to avoid division by zero."""
        output = text_sparkline(["X"], [42])
        assert "X" in output
        assert "42" in output
        # Should have a spark character and min/max summary
        assert "min:" in output
        assert "max:" in output

    def test_inf_value(self):
        output = text_sparkline(["A", "B"], [math.inf, 10])
        assert "A" in output
        assert "B" in output

    def test_neg_inf_value(self):
        output = text_sparkline(["A", "B"], [-math.inf, 10])
        assert "A" in output
        assert "B" in output

    def test_nan_value(self):
        output = text_sparkline(["A", "B"], [math.nan, 10])
        assert "A" in output
        assert "B" in output

    def test_all_nan_values(self):
        output = text_sparkline(["A", "B"], [math.nan, math.nan])
        assert "A" in output
        assert "B" in output

    def test_all_zero_values(self):
        """All-zero triggers the min==max adjustment."""
        output = text_sparkline(["A", "B"], [0, 0])
        assert "A" in output
        assert "B" in output
        assert "0" in output

    def test_large_number_of_items(self):
        n = 60
        labels = [f"item_{i}" for i in range(n)]
        values = [float(i) for i in range(n)]
        output = text_sparkline(labels, values)
        assert "item_0" in output
        assert "item_59" in output

    def test_title_shown(self):
        output = text_sparkline(["A"], [1], title="score")
        assert "score" in output


class TestFormatValue:
    def test_integer(self):
        assert _format_value(42.0) == "42"

    def test_float(self):
        assert _format_value(3.14) == "3.1"

    def test_inf(self):
        assert _format_value(math.inf) == "inf"

    def test_neg_inf(self):
        assert _format_value(-math.inf) == "-inf"

    def test_nan(self):
        assert _format_value(math.nan) == "nan"
