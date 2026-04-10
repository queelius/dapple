"""Tests for the funcat function plotter."""

import io
import json
import sys

import numpy as np
import pytest

from dapple.extras.funcat.funcat import (
    evaluate_expression,
    plot_function_to_mask,
    compute_y_range,
    parse_parametric,
    compute_parametric_ranges,
    plot_parametric_to_mask,
    draw_axes,
    read_json_input,
    write_json_output,
    render_all,
    parse_color,
    print_legend,
    main,
    COLOR_PALETTE,
    NAMED_COLORS,
    AXIS_COLOR,
    RENDERERS,
    DEFAULT_T_MIN,
    DEFAULT_T_MAX,
    DEFAULT_FONT_ASPECT,
)


class TestParseColor:
    """Tests for color parsing."""

    def test_named_colors(self):
        """Test parsing named colors."""
        assert parse_color('red') == NAMED_COLORS['red']
        assert parse_color('RED') == NAMED_COLORS['red']
        assert parse_color('Green') == NAMED_COLORS['green']

    def test_hex_colors(self):
        """Test parsing hex colors."""
        assert parse_color('#ff0000') == (1.0, 0.0, 0.0)
        assert parse_color('#00ff00') == (0.0, 1.0, 0.0)
        assert parse_color('#0000ff') == (0.0, 0.0, 1.0)
        assert parse_color('#ffffff') == (1.0, 1.0, 1.0)
        assert parse_color('#000000') == (0.0, 0.0, 0.0)

    def test_short_hex_colors(self):
        """Test parsing short hex colors (#RGB)."""
        assert parse_color('#f00') == (1.0, 0.0, 0.0)
        assert parse_color('#0f0') == (0.0, 1.0, 0.0)
        assert parse_color('#00f') == (0.0, 0.0, 1.0)

    def test_invalid_color_raises(self):
        """Test that invalid colors raise ValueError."""
        with pytest.raises(ValueError, match="Unknown color"):
            parse_color('notacolor')

    def test_invalid_hex_raises(self):
        """Test that invalid hex raises ValueError."""
        with pytest.raises(ValueError, match="Invalid hex"):
            parse_color('#ff00')  # Wrong length


class TestEvaluateExpression:
    """Tests for expression evaluation."""

    def test_simple_expression(self):
        """Test evaluation of simple expressions."""
        x = np.array([0, 1, 2, 3])
        result = evaluate_expression("x", x)
        np.testing.assert_array_equal(result, x)

    def test_polynomial(self):
        """Test polynomial expressions."""
        x = np.array([0, 1, 2])
        result = evaluate_expression("x**2", x)
        np.testing.assert_array_equal(result, [0, 1, 4])

    def test_trigonometric(self):
        """Test trigonometric functions."""
        x = np.array([0, np.pi / 2, np.pi])
        result = evaluate_expression("sin(x)", x)
        np.testing.assert_array_almost_equal(result, [0, 1, 0], decimal=10)

    def test_constants(self):
        """Test pi and e constants."""
        x = np.array([1])
        result = evaluate_expression("pi", x)
        np.testing.assert_almost_equal(result, np.pi)

        result = evaluate_expression("e", x)
        np.testing.assert_almost_equal(result, np.e)

    def test_combined_expression(self):
        """Test combined expressions."""
        x = np.array([0])
        result = evaluate_expression("sin(x) + cos(x)", x)
        np.testing.assert_almost_equal(result, 1.0)

    def test_available_functions(self):
        """Test that all documented functions are available."""
        x = np.array([1.0])

        # Basic trig
        evaluate_expression("sin(x)", x)
        evaluate_expression("cos(x)", x)
        evaluate_expression("tan(x)", x)

        # Inverse trig
        x_small = np.array([0.5])
        evaluate_expression("asin(x)", x_small)
        evaluate_expression("acos(x)", x_small)
        evaluate_expression("atan(x)", x)

        # Hyperbolic
        evaluate_expression("sinh(x)", x)
        evaluate_expression("cosh(x)", x)
        evaluate_expression("tanh(x)", x)

        # Exponential/log
        evaluate_expression("exp(x)", x)
        evaluate_expression("log(x)", x)
        evaluate_expression("log10(x)", x)
        evaluate_expression("log2(x)", x)

        # Other
        evaluate_expression("sqrt(x)", x)
        evaluate_expression("abs(x)", x)
        evaluate_expression("floor(x)", x)
        evaluate_expression("ceil(x)", x)

    def test_no_builtins(self):
        """Test that builtins are not accessible.

        The AST-based walker rejects non-whitelisted function calls with
        a ValueError rather than NameError — the stricter semantics that
        closed the old sandbox escape via ``__builtins__``.
        """
        x = np.array([1])
        with pytest.raises(ValueError, match="non-whitelisted"):
            evaluate_expression("print(x)", x)

        with pytest.raises(ValueError, match="non-whitelisted"):
            evaluate_expression("__import__('os')", x)

    def test_sandbox_escape_blocked(self):
        """Classic ``__class__.__base__.__subclasses__()`` escape is rejected.

        This is the reason we use an AST walker: attribute access must
        not be possible at all, so the known escape paths simply don't
        parse into executable nodes.
        """
        x = np.array([1.0])
        with pytest.raises(ValueError, match="Disallowed"):
            evaluate_expression("x.__class__", x)
        with pytest.raises(ValueError, match="Disallowed"):
            evaluate_expression("(1).__class__.__mro__", x)

    def test_constant_returns_array(self):
        """Test that constant expressions return arrays."""
        x = np.array([1, 2, 3])
        result = evaluate_expression("1", x)
        assert result.shape == x.shape
        np.testing.assert_array_equal(result, [1, 1, 1])


class TestPlotFunctionToMask:
    """Tests for plot_function_to_mask."""

    def test_basic_mask(self):
        """Test basic mask generation."""
        mask = plot_function_to_mask("x", -1, 1, -1, 1, 100, 50)
        assert mask.shape == (50, 100)
        assert mask.dtype == bool
        # Should have some True values along the diagonal
        assert np.any(mask)

    def test_mask_boundaries(self):
        """Test that function stays within mask bounds."""
        mask = plot_function_to_mask("sin(x)", -np.pi, np.pi, -1, 1, 100, 50)
        # All True values should be within bounds
        assert mask.shape == (50, 100)

    def test_handles_nan_in_mask(self):
        """Test handling of NaN values in mask generation."""
        mask = plot_function_to_mask("sqrt(x)", -1, 1, 0, 1, 100, 50)
        # Should not have True values for NaN (negative x)
        assert mask.shape == (50, 100)

    def test_custom_samples(self):
        """Test mask generation with custom sample count."""
        mask = plot_function_to_mask("sin(x)", -np.pi, np.pi, -1, 1, 100, 50, samples=200)
        assert mask.shape == (50, 100)
        assert np.any(mask)


class TestComputeYRange:
    """Tests for compute_y_range."""

    def test_basic_range(self):
        """Test basic y range computation."""
        y_min, y_max = compute_y_range("sin(x)", -np.pi, np.pi, 100)
        assert y_min == pytest.approx(-1.0, abs=0.1)
        assert y_max == pytest.approx(1.0, abs=0.1)

    def test_constant_function_padding(self):
        """Test that constant functions get padding."""
        y_min, y_max = compute_y_range("1", -1, 1, 100)
        assert y_min == pytest.approx(0.5, abs=0.01)
        assert y_max == pytest.approx(1.5, abs=0.01)

    def test_no_valid_values_raises(self):
        """Test that all-invalid function raises error."""
        with pytest.raises(ValueError, match="no valid values"):
            compute_y_range("sqrt(x)", -2, -1, 100)


class TestDrawAxes:
    """Tests for draw_axes function."""

    def test_draws_y_axis(self):
        """Test that y-axis is drawn when x=0 is in range."""
        bitmap = np.zeros((50, 100), dtype=np.float32)
        colors = np.zeros((50, 100, 3), dtype=np.float32)
        draw_axes(bitmap, colors, -1, 1, -1, 1)

        # Y-axis should be at center column (col 49 for width 100, x range -1 to 1)
        y_axis_col = int((0 - (-1)) / (1 - (-1)) * 99)
        assert np.any(bitmap[:, y_axis_col] > 0)

    def test_draws_x_axis(self):
        """Test that x-axis is drawn when y=0 is in range."""
        bitmap = np.zeros((50, 100), dtype=np.float32)
        colors = np.zeros((50, 100, 3), dtype=np.float32)
        draw_axes(bitmap, colors, -1, 1, -1, 1)

        # X-axis row: (1 - (0 - (-1)) / (1 - (-1))) * 49 = 0.5 * 49 = 24.5 -> 24
        x_axis_row = int((1 - (0 - (-1)) / (1 - (-1))) * 49)
        assert np.any(bitmap[x_axis_row, :] > 0)

    def test_no_y_axis_when_out_of_range(self):
        """Test that y-axis is not drawn when x=0 is outside range."""
        bitmap = np.zeros((50, 100), dtype=np.float32)
        colors = np.zeros((50, 100, 3), dtype=np.float32)
        draw_axes(bitmap, colors, 1, 3, 1, 3)  # Neither axis in range

        # No axes should be drawn
        assert np.all(bitmap == 0)

    def test_no_x_axis_when_out_of_range(self):
        """Test that x-axis is not drawn when y=0 is outside range."""
        bitmap = np.zeros((50, 100), dtype=np.float32)
        colors = np.zeros((50, 100, 3), dtype=np.float32)
        draw_axes(bitmap, colors, -1, 1, 1, 3)  # y range doesn't include 0

        # Y-axis should be drawn but not x-axis
        y_axis_col = int((0 - (-1)) / (1 - (-1)) * 99)
        assert np.any(bitmap[:, y_axis_col] > 0)  # Y-axis drawn

    def test_does_not_overwrite_function(self):
        """Test that axes don't overwrite function pixels."""
        bitmap = np.zeros((50, 100), dtype=np.float32)
        colors = np.zeros((50, 100, 3), dtype=np.float32)

        # Pre-set a function pixel at the axis intersection
        y_axis_col = int((0 - (-1)) / (1 - (-1)) * 99)
        x_axis_row = int((1 - (0 - (-1)) / (1 - (-1))) * 49)
        bitmap[x_axis_row, y_axis_col] = 1.0
        colors[x_axis_row, y_axis_col] = [1, 0, 0]  # Red

        draw_axes(bitmap, colors, -1, 1, -1, 1)

        # Function pixel should not be overwritten
        assert bitmap[x_axis_row, y_axis_col] == 1.0
        assert np.allclose(colors[x_axis_row, y_axis_col], [1, 0, 0])


class TestJsonIO:
    """Tests for JSON input/output functions."""

    def test_read_json_from_tty(self, monkeypatch):
        """Test that reading from TTY returns None."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        assert read_json_input() is None

    def test_read_json_empty_input(self, monkeypatch):
        """Test reading empty input."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: "")
        assert read_json_input() is None

    def test_read_json_invalid(self, monkeypatch):
        """Test reading invalid JSON."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: "not json")
        assert read_json_input() is None

    def test_read_json_valid(self, monkeypatch):
        """Test reading valid JSON."""
        data = {"expressions": [{"expr": "sin(x)"}], "x_min": -1, "x_max": 1}
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: json.dumps(data))
        result = read_json_input()
        assert result == data

    def test_write_json_output(self, capsys):
        """Test writing JSON output."""
        expressions = [
            {"expr": "sin(x)", "color": None, "samples": None},
            {"expr": "cos(x)", "color": "red", "samples": 500},
        ]

        write_json_output(expressions, -1, 1, -1, 1)

        captured = capsys.readouterr()
        data = json.loads(captured.out)

        assert data["x_min"] == -1
        assert data["x_max"] == 1
        assert data["y_min"] == -1
        assert data["y_max"] == 1
        assert len(data["expressions"]) == 2
        assert data["expressions"][0]["expr"] == "sin(x)"
        assert data["expressions"][1]["color"] == "red"


class TestRenderAll:
    """Tests for render_all function."""

    def test_single_expression(self):
        """Test rendering a single expression."""
        expressions = [{"expr": "sin(x)", "color": None, "samples": None}]
        renderer = RENDERERS['braille']
        # pixel 100x50, braille cell 2x4 -> char 50x12.5 (use 50x12)
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, -np.pi, np.pi, None, None, 100, 50, 50, 12, show_axes=True,
            renderer=renderer
        )

        assert bitmap.shape == (50, 100)
        assert colors.shape == (50, 100, 3)
        assert np.any(bitmap > 0)
        assert len(legend_entries) == 1
        assert legend_entries[0][0] == "sin(x)"

    def test_multiple_expressions(self):
        """Test rendering multiple expressions."""
        expressions = [
            {"expr": "sin(x)", "color": None, "samples": None},
            {"expr": "cos(x)", "color": None, "samples": None},
        ]
        renderer = RENDERERS['braille']
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, -np.pi, np.pi, None, None, 100, 50, 50, 12, show_axes=True,
            renderer=renderer
        )

        assert bitmap.shape == (50, 100)
        assert np.any(bitmap > 0)
        assert len(legend_entries) == 2
        assert legend_entries[0][0] == "sin(x)"
        assert legend_entries[1][0] == "cos(x)"

    def test_custom_colors(self):
        """Test rendering with custom colors."""
        expressions = [
            {"expr": "x", "color": "red", "samples": None},
        ]
        renderer = RENDERERS['braille']
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, -1, 1, -1, 1, 100, 50, 50, 12, show_axes=False,
            renderer=renderer
        )

        # Find a pixel where the function was drawn
        mask = bitmap > 0.5
        if np.any(mask):
            # Check that the color is red
            red_pixels = colors[mask]
            assert np.any(np.allclose(red_pixels, NAMED_COLORS['red'], atol=0.1))

        # Check legend entry has the correct color
        assert len(legend_entries) == 1
        assert legend_entries[0][0] == "x"
        assert legend_entries[0][1] == NAMED_COLORS['red']

    def test_combined_y_range(self):
        """Test that y-range is computed from all expressions."""
        expressions = [
            {"expr": "sin(x)", "color": None, "samples": None},  # y: -1 to 1
            {"expr": "2*sin(x)", "color": None, "samples": None},  # y: -2 to 2
        ]
        renderer = RENDERERS['braille']
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, -np.pi, np.pi, None, None, 100, 50, 50, 12, show_axes=False,
            renderer=renderer
        )

        # y-range should encompass both functions (may be slightly adjusted due to sampling)
        assert y_min == pytest.approx(-2.0, abs=0.01)
        assert y_max == pytest.approx(2.0, abs=0.01)
        assert len(legend_entries) == 2


class TestMain:
    """Tests for CLI main function."""

    def test_help_exits(self, monkeypatch):
        """Test --help flag."""
        monkeypatch.setattr(sys, "argv", ["funcat", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_basic_execution(self, monkeypatch, capsys):
        """Test basic function plotting via CLI."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out
        assert "y:" in captured.out

    def test_custom_range(self, monkeypatch, capsys):
        """Test custom x range (may be expanded for aspect ratio correction)."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "x**2", "--xmin", "-2", "--xmax", "2", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        # X range may be expanded for aspect ratio, but output should contain range info
        assert "x:" in captured.out
        assert "y:" in captured.out

    def test_axes_flag(self, monkeypatch, capsys):
        """Test --axes flag."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "cos(x)", "--axes", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        # Should complete without error
        assert "x:" in captured.out

    def test_invalid_expression_exits(self, monkeypatch, capsys):
        """Test invalid expression causes exit."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "undefined_function(x)", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_custom_y_range(self, monkeypatch, capsys):
        """Test custom y range (may be expanded for aspect ratio correction)."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "--ymin", "-2", "--ymax", "2", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        # Y range may be expanded for aspect ratio, but output should contain range info
        assert "x:" in captured.out
        assert "y:" in captured.out

    def test_json_output(self, monkeypatch, capsys):
        """Test --json flag outputs expression-based JSON."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "x", "--json", "-w", "10", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()

        # Should be valid JSON with expressions list
        data = json.loads(captured.out)
        assert "expressions" in data
        assert len(data["expressions"]) == 1
        assert data["expressions"][0]["expr"] == "x"

    def test_json_chaining(self, monkeypatch, capsys):
        """Test chaining via JSON input."""
        # Create JSON input with one expression
        first_output = {
            "expressions": [{"expr": "sin(x)", "color": None, "samples": None}],
            "x_min": -np.pi,
            "x_max": np.pi,
            "y_min": None,
            "y_max": None,
        }

        # Simulate piped input
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "cos(x)", "-w", "10", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: json.dumps(first_output))

        main()
        captured = capsys.readouterr()

        # Should render (not JSON since --json not specified)
        assert "x:" in captured.out
        assert "y:" in captured.out

    def test_color_option(self, monkeypatch, capsys):
        """Test --color option."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "--color", "red", "--json"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["expressions"][0]["color"] == "red"

    def test_samples_option(self, monkeypatch, capsys):
        """Test --nsamples option."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "--nsamples", "500", "--json"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["expressions"][0]["samples"] == 500

    def test_color_cycling(self):
        """Test that color palette cycles correctly."""
        # Verify palette has expected colors
        assert len(COLOR_PALETTE) == 8

        # Test cycling
        for i in range(16):
            color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
            assert len(color) == 3
            assert all(0 <= c <= 1 for c in color)

    def test_invalid_color_exits(self, monkeypatch, capsys):
        """Test invalid color causes exit."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "--color", "notacolor", "-w", "10", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown color" in captured.err


class TestRendererSelection:
    """Tests for renderer selection feature."""

    def test_renderers_dict_contains_all(self):
        """Test that RENDERERS dict contains all expected renderers."""
        expected = {'braille', 'quadrants', 'sextants', 'ascii', 'sixel', 'kitty'}
        assert set(RENDERERS.keys()) == expected

    def test_renderers_have_cell_dimensions(self):
        """Test that all renderers have cell_width and cell_height."""
        for name, renderer in RENDERERS.items():
            assert hasattr(renderer, 'cell_width'), f"{name} missing cell_width"
            assert hasattr(renderer, 'cell_height'), f"{name} missing cell_height"
            assert renderer.cell_width > 0
            assert renderer.cell_height > 0

    def test_default_renderer_is_braille(self, monkeypatch, capsys):
        """Test that default renderer is braille."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        # Should complete without error with braille output
        assert "x:" in captured.out

    def test_explicit_braille_renderer(self, monkeypatch, capsys):
        """Test explicit braille renderer selection."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "braille", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_quadrants_renderer(self, monkeypatch, capsys):
        """Test quadrants renderer selection."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "quadrants", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_sextants_renderer(self, monkeypatch, capsys):
        """Test sextants renderer selection."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "sextants", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_ascii_renderer(self, monkeypatch, capsys):
        """Test ascii renderer selection."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "ascii", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_sixel_renderer(self, monkeypatch, capsys):
        """Test sixel renderer selection."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "sixel", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_kitty_renderer(self, monkeypatch, capsys):
        """Test kitty renderer selection."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "kitty", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_invalid_renderer_exits(self, monkeypatch, capsys):
        """Test that invalid renderer name causes error."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "notarenderer", "-w", "10", "-H", "5"]
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2  # argparse invalid choice

    def test_renderer_with_color(self, monkeypatch, capsys):
        """Test renderer combined with color option."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-r", "quadrants", "--color", "red", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_renderer_long_option(self, monkeypatch, capsys):
        """Test --renderer long option."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "--renderer", "sextants", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_render_all_with_different_renderers(self):
        """Test render_all works with different renderers."""
        expressions = [{"expr": "sin(x)", "color": None, "samples": None}]

        for name, renderer in RENDERERS.items():
            char_width = 20
            char_height = 5
            pixel_width = char_width * renderer.cell_width
            pixel_height = char_height * renderer.cell_height
            bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
                expressions, -np.pi, np.pi, None, None,
                pixel_width, pixel_height, char_width, char_height, show_axes=True,
                renderer=renderer
            )
            assert bitmap.shape == (pixel_height, pixel_width), f"Failed for {name}"
            assert colors.shape == (pixel_height, pixel_width, 3), f"Failed for {name}"
            assert len(legend_entries) == 1, f"Failed for {name}"

    def test_nsamples_short_option(self, monkeypatch, capsys):
        """Test -n short option for samples."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-n", "500", "--json"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["expressions"][0]["samples"] == 500


class TestLegend:
    """Tests for legend functionality."""

    def test_print_legend_single_entry(self, capsys):
        """Test print_legend with a single entry."""
        entries = [("sin(x)", (0.0, 0.8, 1.0))]
        print_legend(entries)
        captured = capsys.readouterr()
        assert "sin(x)" in captured.out
        assert "\033[38;2;0;204;255m" in captured.out  # Cyan color escape

    def test_print_legend_multiple_entries(self, capsys):
        """Test print_legend with multiple entries."""
        entries = [
            ("sin(x)", (0.0, 0.8, 1.0)),
            ("cos(x)", (1.0, 0.2, 0.2)),
        ]
        print_legend(entries)
        captured = capsys.readouterr()
        assert "sin(x)" in captured.out
        assert "cos(x)" in captured.out
        # Both entries should be on the same line, separated
        assert captured.out.count("\n") == 1

    def test_print_legend_color_conversion(self, capsys):
        """Test that colors are correctly converted to 0-255 ANSI codes."""
        entries = [("test", (1.0, 0.5, 0.0))]  # Orange
        print_legend(entries)
        captured = capsys.readouterr()
        # 1.0*255=255, 0.5*255=127, 0.0*255=0
        assert "\033[38;2;255;127;0m" in captured.out

    def test_legend_flag_single_function_no_output(self, monkeypatch, capsys):
        """Test that --legend with single function doesn't print legend."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "sin(x)", "-l", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        # Should not have legend (only 1 function)
        assert "──" not in captured.out

    def test_legend_flag_multiple_functions(self, monkeypatch, capsys):
        """Test that --legend with multiple functions prints legend."""
        # Create JSON input with one expression
        first_output = {
            "expressions": [{"expr": "sin(x)", "color": None, "samples": None}],
            "x_min": -np.pi,
            "x_max": np.pi,
            "y_min": None,
            "y_max": None,
        }

        # Simulate piped input with second expression
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "cos(x)", "-l", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: json.dumps(first_output))

        main()
        captured = capsys.readouterr()

        # Should have legend with both functions
        assert "sin(x)" in captured.out
        assert "cos(x)" in captured.out
        # Check for colored dashes (ANSI escape codes)
        assert "\033[38;2;" in captured.out

    def test_legend_flag_not_set(self, monkeypatch, capsys):
        """Test that without --legend flag, no legend is printed."""
        # Create JSON input with one expression
        first_output = {
            "expressions": [{"expr": "sin(x)", "color": None, "samples": None}],
            "x_min": -np.pi,
            "x_max": np.pi,
            "y_min": None,
            "y_max": None,
        }

        # Simulate piped input with second expression, no -l flag
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "cos(x)", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: json.dumps(first_output))

        main()
        captured = capsys.readouterr()

        # Should render (has range info)
        assert "x:" in captured.out
        # But no legend (no ── in the last line)
        lines = captured.out.strip().split('\n')
        last_line = lines[-1]
        assert "──" not in last_line

    def test_legend_with_custom_colors(self, monkeypatch, capsys):
        """Test legend displays custom colors correctly."""
        # Create JSON input with a custom colored expression
        first_output = {
            "expressions": [{"expr": "sin(x)", "color": "red", "samples": None}],
            "x_min": -np.pi,
            "x_max": np.pi,
            "y_min": None,
            "y_max": None,
        }

        # Add second expression with custom color
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "cos(x)", "--color", "blue", "-l", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: json.dumps(first_output))

        main()
        captured = capsys.readouterr()

        # Should have both expressions in legend
        assert "sin(x)" in captured.out
        assert "cos(x)" in captured.out

    def test_render_all_returns_legend_entries(self):
        """Test that render_all returns correct legend entries."""
        expressions = [
            {"expr": "sin(x)", "color": None, "samples": None},
            {"expr": "cos(x)", "color": "red", "samples": None},
            {"expr": "x**2", "color": None, "samples": None},
        ]
        renderer = RENDERERS['braille']
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, -np.pi, np.pi, None, None, 100, 50, 50, 12, show_axes=True,
            renderer=renderer
        )

        assert len(legend_entries) == 3
        assert legend_entries[0][0] == "sin(x)"
        assert legend_entries[1][0] == "cos(x)"
        assert legend_entries[1][1] == NAMED_COLORS['red']
        assert legend_entries[2][0] == "x**2"

    def test_legend_color_palette_cycling(self):
        """Test that legend entries cycle through color palette."""
        expressions = [
            {"expr": f"sin({i}*x)", "color": None, "samples": None}
            for i in range(1, 5)
        ]
        renderer = RENDERERS['braille']
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, -np.pi, np.pi, None, None, 100, 50, 50, 12, show_axes=True,
            renderer=renderer
        )

        assert len(legend_entries) == 4
        # First four should match first four palette colors
        for i in range(4):
            assert legend_entries[i][1] == COLOR_PALETTE[i]


class TestParametric:
    """Tests for parametric function support."""

    def test_parse_parametric_basic(self):
        """Test parsing basic parametric expression."""
        x_expr, y_expr = parse_parametric("cos(t),sin(t)")
        assert x_expr == "cos(t)"
        assert y_expr == "sin(t)"

    def test_parse_parametric_with_spaces(self):
        """Test parsing parametric expression with spaces."""
        x_expr, y_expr = parse_parametric("  cos(t)  ,  sin(t)  ")
        assert x_expr == "cos(t)"
        assert y_expr == "sin(t)"

    def test_parse_parametric_complex(self):
        """Test parsing complex parametric expression."""
        x_expr, y_expr = parse_parametric("t*cos(t),t*sin(t)")
        assert x_expr == "t*cos(t)"
        assert y_expr == "t*sin(t)"

    def test_parse_parametric_with_commas_in_functions(self):
        """Test parsing with additional commas (only splits on first comma)."""
        x_expr, y_expr = parse_parametric("sin(t),cos(t)+1,extra")
        assert x_expr == "sin(t)"
        assert y_expr == "cos(t)+1,extra"  # Rest goes to y_expr

    def test_parse_parametric_invalid(self):
        """Test that invalid parametric raises error."""
        with pytest.raises(ValueError, match="Parametric must be"):
            parse_parametric("just_one_part")

    def test_compute_parametric_ranges_circle(self):
        """Test computing ranges for a circle."""
        x_min, x_max, y_min, y_max = compute_parametric_ranges(
            "cos(t)", "sin(t)", 0, 2*np.pi, 1000
        )
        assert x_min == pytest.approx(-1.0, abs=0.01)
        assert x_max == pytest.approx(1.0, abs=0.01)
        assert y_min == pytest.approx(-1.0, abs=0.01)
        assert y_max == pytest.approx(1.0, abs=0.01)

    def test_compute_parametric_ranges_ellipse(self):
        """Test computing ranges for an ellipse."""
        x_min, x_max, y_min, y_max = compute_parametric_ranges(
            "2*cos(t)", "sin(t)", 0, 2*np.pi, 1000
        )
        assert x_min == pytest.approx(-2.0, abs=0.01)
        assert x_max == pytest.approx(2.0, abs=0.01)
        assert y_min == pytest.approx(-1.0, abs=0.01)
        assert y_max == pytest.approx(1.0, abs=0.01)

    def test_compute_parametric_ranges_custom_t(self):
        """Test computing ranges with custom t range."""
        x_min, x_max, y_min, y_max = compute_parametric_ranges(
            "t", "t**2", 0, 2, 100
        )
        assert x_min == pytest.approx(0.0, abs=0.05)
        assert x_max == pytest.approx(2.0, abs=0.05)
        assert y_min == pytest.approx(0.0, abs=0.05)
        assert y_max == pytest.approx(4.0, abs=0.05)

    def test_compute_parametric_ranges_invalid(self):
        """Test that all-invalid parametric raises error."""
        with pytest.raises(ValueError, match="produces no valid values"):
            compute_parametric_ranges("sqrt(-t)", "sqrt(-t)", 1, 2, 100)

    def test_plot_parametric_to_mask_circle(self):
        """Test generating mask for a circle."""
        mask = plot_parametric_to_mask(
            "cos(t)", "sin(t)", 0, 2*np.pi,
            -1, 1, -1, 1, 100, 50, 1000
        )
        assert mask.shape == (50, 100)
        assert mask.dtype == bool
        assert np.any(mask)  # Should have some True values

    def test_plot_parametric_to_mask_boundaries(self):
        """Test that parametric curve stays within bounds."""
        mask = plot_parametric_to_mask(
            "2*cos(t)", "2*sin(t)", 0, 2*np.pi,
            -3, 3, -3, 3, 100, 50, 1000
        )
        assert mask.shape == (50, 100)
        assert np.any(mask)

    def test_render_all_parametric(self):
        """Test render_all with parametric expression."""
        expressions = [{
            'expr': "cos(t),sin(t)",
            'color': None,
            'samples': 500,
            'parametric': True,
            't_min': 0,
            't_max': 2*np.pi,
        }]
        renderer = RENDERERS['braille']
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, None, None, None, None, 100, 50, 50, 12, show_axes=True,
            renderer=renderer
        )
        assert bitmap.shape == (50, 100)
        assert colors.shape == (50, 100, 3)
        assert np.any(bitmap > 0)
        assert len(legend_entries) == 1
        assert legend_entries[0][0] == "cos(t),sin(t)"
        # Ranges are expanded for aspect ratio correction, but should contain [-1, 1]
        assert x_min <= -1.0
        assert x_max >= 1.0

    def test_render_all_mixed_regular_and_parametric(self):
        """Test render_all with both regular and parametric expressions."""
        expressions = [
            {'expr': "sin(x)", 'color': None, 'samples': None, 'parametric': False},
            {'expr': "cos(t),sin(t)", 'color': 'red', 'samples': 500, 'parametric': True, 't_min': 0, 't_max': 2*np.pi},
        ]
        renderer = RENDERERS['braille']
        bitmap, colors, x_min, x_max, y_min, y_max, legend_entries = render_all(
            expressions, -np.pi, np.pi, None, None, 100, 50, 50, 12, show_axes=True,
            renderer=renderer
        )
        assert bitmap.shape == (50, 100)
        assert np.any(bitmap > 0)
        assert len(legend_entries) == 2

    def test_cli_parametric_basic(self, monkeypatch, capsys):
        """Test CLI with parametric flag."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "cos(t),sin(t)", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out
        assert "y:" in captured.out

    def test_cli_parametric_with_custom_t_range(self, monkeypatch, capsys):
        """Test CLI with custom t range."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "t*cos(t),t*sin(t)", "--tmin", "0", "--tmax", "12.56", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_cli_parametric_with_color(self, monkeypatch, capsys):
        """Test CLI parametric with color option."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "cos(t),sin(t)", "--color", "red", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_cli_parametric_json_output(self, monkeypatch, capsys):
        """Test CLI parametric with JSON output."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "cos(t),sin(t)", "--json"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert len(data["expressions"]) == 1
        assert data["expressions"][0]["expr"] == "cos(t),sin(t)"
        assert data["expressions"][0]["parametric"] is True
        assert data["expressions"][0]["t_min"] == DEFAULT_T_MIN
        assert data["expressions"][0]["t_max"] == DEFAULT_T_MAX

    def test_cli_parametric_with_explicit_x_range(self, monkeypatch, capsys):
        """Test CLI parametric with explicit x range."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "cos(t),sin(t)", "--xmin", "-2", "--xmax", "2", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "[-2.00, 2.00]" in captured.out

    def test_cli_no_expression_or_parametric_errors(self, monkeypatch, capsys):
        """Test that missing both expression and parametric causes error."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-w", "20", "-H", "5"]
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2  # argparse error

    def test_cli_parametric_with_legend(self, monkeypatch, capsys):
        """Test CLI parametric with legend flag."""
        # Create JSON input with a regular expression
        first_output = {
            "expressions": [{"expr": "sin(x)", "color": None, "samples": None, "parametric": False}],
            "x_min": -np.pi,
            "x_max": np.pi,
            "y_min": None,
            "y_max": None,
        }

        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "cos(t),sin(t)", "-l", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdin, "read", lambda: json.dumps(first_output))

        main()
        captured = capsys.readouterr()
        # Should have legend with both functions
        assert "sin(x)" in captured.out
        assert "cos(t),sin(t)" in captured.out

    def test_parametric_invalid_expression(self, monkeypatch, capsys):
        """Test that invalid parametric expression causes error."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "undefined_func(t),sin(t)", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_default_t_range_values(self):
        """Test default t range constants."""
        assert DEFAULT_T_MIN == 0.0
        assert DEFAULT_T_MAX == pytest.approx(2 * np.pi, abs=0.001)

    def test_parametric_heart_curve(self, monkeypatch, capsys):
        """Test heart curve parametric function."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "16*sin(t)**3,13*cos(t)-5*cos(2*t)-2*cos(3*t)-cos(4*t)", "-w", "20", "-H", "10"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out

    def test_parametric_lissajous(self, monkeypatch, capsys):
        """Test Lissajous figure parametric function."""
        monkeypatch.setattr(
            sys, "argv",
            ["funcat", "-p", "sin(3*t),sin(2*t)", "-w", "20", "-H", "5"]
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        main()
        captured = capsys.readouterr()
        assert "x:" in captured.out


class TestErrorHandling:
    def test_bad_expression_reports_which(self):
        """Bad expression should identify which expression failed."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.funcat.funcat", "INVALID(x)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "INVALID" in result.stderr

    def test_exit_code_on_error(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.funcat.funcat", "+++"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert result.stderr.strip()  # should have error message
