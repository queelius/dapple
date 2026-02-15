"""Tests for dapple.layout — Canvas.fit(), terminal_fit(), Frame, Grid."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import numpy as np
import pytest

from dapple import Canvas, braille, sextants, quadrants, kitty, sixel
from dapple.layout import (
    Frame,
    Grid,
    _fit_canvas,
    terminal_columns,
    terminal_fit,
)


# ── terminal_columns ────────────────────────────────────────────────


class TestTerminalColumns:
    def test_returns_int(self):
        result = terminal_columns()
        assert isinstance(result, int)
        assert result > 0

    def test_fallback(self):
        fake_size = type("terminal_size", (), {"columns": 60, "lines": 24})()
        with patch("dapple.layout.shutil.get_terminal_size", return_value=fake_size):
            assert terminal_columns() == 60


# ── Canvas.fit() ────────────────────────────────────────────────────


class TestCanvasFit:
    def test_braille_resize(self):
        """Braille (2x4): 40-char width → 80px wide bitmap."""
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted = c.fit(braille, width=40)
        assert fitted.shape[1] == 40 * braille.cell_width  # 80
        assert fitted.shape[0] > 0

    def test_sextants_resize(self):
        """Sextants (2x3): 40-char width → 80px wide bitmap."""
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted = c.fit(sextants, width=40)
        assert fitted.shape[1] == 40 * sextants.cell_width  # 80

    def test_quadrants_resize(self):
        """Quadrants (2x2): 40-char width → 80px wide bitmap."""
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted = c.fit(quadrants, width=40)
        assert fitted.shape[1] == 40 * quadrants.cell_width  # 80

    def test_pixel_renderer_passthrough(self):
        """Sixel (1x1): should return unchanged canvas."""
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted = c.fit(sixel, width=40)
        assert fitted.shape == c.shape

    def test_kitty_passthrough(self):
        """Kitty (1x1): should return unchanged canvas."""
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted = c.fit(kitty, width=40)
        assert fitted.shape == c.shape

    def test_preserves_colors(self):
        """Should resize colors along with bitmap."""
        bitmap = np.random.rand(100, 200).astype(np.float32)
        colors = np.random.rand(100, 200, 3).astype(np.float32)
        c = Canvas(bitmap, colors=colors)
        fitted = c.fit(braille, width=40)
        assert fitted.colors is not None
        assert fitted.colors.shape[0] == fitted.shape[0]
        assert fitted.colors.shape[1] == fitted.shape[1]
        assert fitted.colors.shape[2] == 3

    def test_no_colors(self):
        """Should work fine without colors."""
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted = c.fit(braille, width=40)
        assert fitted.colors is None

    def test_explicit_height(self):
        """Explicit height overrides aspect-ratio calculation."""
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted = c.fit(braille, width=40, height=10)
        assert fitted.shape[0] == 10 * braille.cell_height  # 40

    def test_zero_width_canvas(self):
        """Edge case: zero-width canvas should return self."""
        c = Canvas(np.zeros((10, 0), dtype=np.float32))
        fitted = c.fit(braille, width=40)
        assert fitted.shape == (10, 0)


# ── terminal_fit() ──────────────────────────────────────────────────


class TestTerminalFit:
    def test_character_renderer(self):
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted, rend = terminal_fit(c, braille, width=40)
        assert fitted.shape[1] == 40 * braille.cell_width
        assert rend is braille

    def test_kitty_configures_columns(self):
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted, rend = terminal_fit(c, kitty, width=60)
        assert fitted.shape == c.shape  # Not resized
        assert rend.columns == 60

    def test_sixel_resizes_pixels(self):
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        fitted, rend = terminal_fit(c, sixel, width=40)
        # Sixel: 40 chars * 10 px/cell = 400 pixels wide
        assert fitted.shape[1] == 400


# ── Frame ───────────────────────────────────────────────────────────


class TestFrame:
    def test_render_plain(self):
        c = Canvas(np.ones((8, 16), dtype=np.float32))
        f = Frame(canvas=c)
        buf = StringIO()
        f.render(braille, dest=buf)
        output = buf.getvalue()
        assert len(output) > 0

    def test_render_with_title(self):
        c = Canvas(np.ones((8, 16), dtype=np.float32))
        f = Frame(canvas=c, title="Test")
        buf = StringIO()
        f.render(braille, dest=buf)
        output = buf.getvalue()
        assert "Test" in output

    def test_render_with_border(self):
        c = Canvas(np.ones((8, 16), dtype=np.float32))
        f = Frame(canvas=c, border=True)
        buf = StringIO()
        f.render(braille, dest=buf)
        output = buf.getvalue()
        assert "┌" in output
        assert "└" in output

    def test_render_with_title_and_border(self):
        c = Canvas(np.ones((8, 16), dtype=np.float32))
        f = Frame(canvas=c, title="My Frame", border=True)
        buf = StringIO()
        f.render(braille, dest=buf)
        output = buf.getvalue()
        assert "My Frame" in output
        assert "┌" in output

    def test_sized_canvas(self):
        c = Canvas(np.random.rand(100, 200).astype(np.float32))
        f = Frame(canvas=c, width=40)
        sized = f.sized_canvas(braille)
        assert sized.shape[1] <= 40 * braille.cell_width


# ── Grid ────────────────────────────────────────────────────────────


class TestGrid:
    def test_single_cell(self):
        c = Canvas(np.ones((8, 16), dtype=np.float32))
        g = Grid([[c]], width=20)
        buf = StringIO()
        g.render(braille, dest=buf)
        output = buf.getvalue()
        assert len(output) > 0

    def test_two_columns(self):
        c1 = Canvas(np.ones((8, 16), dtype=np.float32))
        c2 = Canvas(np.zeros((8, 16), dtype=np.float32))
        g = Grid([[c1, c2]], width=40)
        buf = StringIO()
        g.render(braille, dest=buf)
        output = buf.getvalue()
        assert len(output) > 0

    def test_two_rows(self):
        c1 = Canvas(np.ones((8, 16), dtype=np.float32))
        c2 = Canvas(np.zeros((8, 16), dtype=np.float32))
        g = Grid([[c1], [c2]], width=20)
        buf = StringIO()
        g.render(braille, dest=buf)
        output = buf.getvalue()
        lines = output.strip().split("\n")
        assert len(lines) >= 2

    def test_2x2_grid(self):
        canvases = [
            [Canvas(np.random.rand(8, 16).astype(np.float32)) for _ in range(2)]
            for _ in range(2)
        ]
        g = Grid(canvases, width=40)
        buf = StringIO()
        g.render(braille, dest=buf)
        output = buf.getvalue()
        assert len(output) > 0

    def test_frame_cells(self):
        c1 = Canvas(np.ones((8, 16), dtype=np.float32))
        c2 = Canvas(np.zeros((8, 16), dtype=np.float32))
        f1 = Frame(canvas=c1, title="A")
        f2 = Frame(canvas=c2, title="B")
        g = Grid([[f1, f2]], width=40)
        buf = StringIO()
        g.render(braille, dest=buf)
        output = buf.getvalue()
        assert "A" in output
        assert "B" in output

    def test_gap_zero(self):
        c1 = Canvas(np.ones((8, 16), dtype=np.float32))
        c2 = Canvas(np.ones((8, 16), dtype=np.float32))
        g = Grid([[c1, c2]], width=40, gap=0)
        buf = StringIO()
        g.render(braille, dest=buf)
        output = buf.getvalue()
        assert len(output) > 0

    def test_to_canvas_not_implemented(self):
        c = Canvas(np.ones((8, 16), dtype=np.float32))
        g = Grid([[c]], width=20)
        with pytest.raises(NotImplementedError):
            g.to_canvas(braille)

    def test_empty_row(self):
        c = Canvas(np.ones((8, 16), dtype=np.float32))
        g = Grid([[], [c]], width=20)
        buf = StringIO()
        g.render(braille, dest=buf)
        output = buf.getvalue()
        assert len(output) > 0
