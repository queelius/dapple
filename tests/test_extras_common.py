"""Tests for dapple.extras.common shared utilities."""

from __future__ import annotations

import argparse
import os

import numpy as np
import pytest

from dapple.extras.common import add_color_args, apply_preprocessing, get_renderer
from dapple.renderers import Renderer


# ─── get_renderer ────────────────────────────────────────────────────────────


class TestGetRenderer:
    """Tests for the shared get_renderer function."""

    @pytest.mark.parametrize(
        "name",
        ["braille", "quadrants", "sextants", "ascii", "sixel", "kitty", "fingerprint"],
    )
    def test_all_named_renderers_valid(self, name: str):
        """All 7 named renderers return a valid Renderer."""
        renderer = get_renderer(name)
        assert isinstance(renderer, Renderer)

    def test_unknown_renderer_raises(self):
        """Unknown renderer name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown renderer"):
            get_renderer("bogus")

    def test_braille_no_color(self):
        """braille + no_color produces color_mode='none'."""
        renderer = get_renderer("braille", no_color=True)
        assert isinstance(renderer, Renderer)
        assert renderer.color_mode == "none"

    def test_braille_grayscale(self):
        """braille + grayscale produces color_mode='grayscale'."""
        renderer = get_renderer("braille", grayscale=True)
        assert isinstance(renderer, Renderer)
        assert renderer.color_mode == "grayscale"

    def test_braille_default_truecolor(self):
        """braille with no flags produces color_mode='truecolor'."""
        renderer = get_renderer("braille")
        assert isinstance(renderer, Renderer)
        assert renderer.color_mode == "truecolor"

    def test_quadrants_grayscale(self):
        """quadrants + grayscale=True produces grayscale renderer."""
        renderer = get_renderer("quadrants", grayscale=True)
        assert isinstance(renderer, Renderer)
        assert renderer.grayscale is True

    def test_sextants_grayscale(self):
        """sextants + grayscale=True produces grayscale renderer."""
        renderer = get_renderer("sextants", grayscale=True)
        assert isinstance(renderer, Renderer)
        assert renderer.grayscale is True

    def test_quadrants_default_not_grayscale(self):
        """quadrants with no flags is not grayscale."""
        renderer = get_renderer("quadrants")
        assert isinstance(renderer, Renderer)
        assert renderer.grayscale is False

    def test_quadrants_no_color(self):
        """quadrants + no_color falls back to grayscale mode."""
        renderer = get_renderer("quadrants", no_color=True)
        assert isinstance(renderer, Renderer)
        assert renderer.grayscale is True

    def test_sextants_no_color(self):
        """sextants + no_color falls back to grayscale mode."""
        renderer = get_renderer("sextants", no_color=True)
        assert isinstance(renderer, Renderer)
        assert renderer.grayscale is True

    def test_ascii_no_color_unchanged(self):
        """ascii + no_color returns default (already colorless)."""
        renderer = get_renderer("ascii", no_color=True)
        assert isinstance(renderer, Renderer)

    def test_fingerprint_no_color_unchanged(self):
        """fingerprint + no_color returns default (already colorless)."""
        renderer = get_renderer("fingerprint", no_color=True)
        assert isinstance(renderer, Renderer)

    def test_auto_returns_renderer(self):
        """'auto' returns a valid Renderer."""
        renderer = get_renderer("auto")
        assert isinstance(renderer, Renderer)


# ─── NO_COLOR env var ─────────────────────────────────────────────────────────


class TestNoColorEnv:
    """Tests for NO_COLOR environment variable support."""

    def test_no_color_env_forces_braille_no_color(self, monkeypatch):
        """NO_COLOR=1 forces braille to color_mode='none'."""
        monkeypatch.setenv("NO_COLOR", "1")
        renderer = get_renderer("braille")
        assert renderer.color_mode == "none"

    def test_no_color_env_empty_string(self, monkeypatch):
        """NO_COLOR="" (empty string) also forces no-color per spec."""
        monkeypatch.setenv("NO_COLOR", "")
        renderer = get_renderer("braille")
        assert renderer.color_mode == "none"

    def test_no_color_env_forces_quadrants_grayscale(self, monkeypatch):
        """NO_COLOR=1 forces quadrants to grayscale."""
        monkeypatch.setenv("NO_COLOR", "1")
        renderer = get_renderer("quadrants")
        assert renderer.grayscale is True

    def test_no_color_env_forces_sextants_grayscale(self, monkeypatch):
        """NO_COLOR=1 forces sextants to grayscale."""
        monkeypatch.setenv("NO_COLOR", "1")
        renderer = get_renderer("sextants")
        assert renderer.grayscale is True

    def test_no_color_env_absent_keeps_color(self, monkeypatch):
        """Without NO_COLOR, braille defaults to truecolor."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        renderer = get_renderer("braille")
        assert renderer.color_mode == "truecolor"

    def test_no_color_env_ascii_unchanged(self, monkeypatch):
        """ascii is already colorless — NO_COLOR is a no-op."""
        monkeypatch.setenv("NO_COLOR", "1")
        renderer = get_renderer("ascii")
        assert isinstance(renderer, Renderer)


# ─── add_color_args ───────────────────────────────────────────────────────────


class TestAddColorArgs:
    """Tests for the shared add_color_args() helper."""

    def test_adds_grayscale_flag(self):
        """add_color_args adds --grayscale flag."""
        parser = argparse.ArgumentParser()
        add_color_args(parser)
        args = parser.parse_args([])
        assert args.grayscale is False
        args = parser.parse_args(["--grayscale"])
        assert args.grayscale is True

    def test_adds_no_color_flag(self):
        """add_color_args adds --no-color flag."""
        parser = argparse.ArgumentParser()
        add_color_args(parser)
        args = parser.parse_args([])
        assert args.no_color is False
        args = parser.parse_args(["--no-color"])
        assert args.no_color is True

    def test_both_flags_together(self):
        """Both --grayscale and --no-color can be set simultaneously."""
        parser = argparse.ArgumentParser()
        add_color_args(parser)
        args = parser.parse_args(["--grayscale", "--no-color"])
        assert args.grayscale is True
        assert args.no_color is True

    def test_does_not_conflict_with_existing_args(self):
        """add_color_args works alongside existing parser args."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-r", "--renderer", default="braille")
        add_color_args(parser)
        args = parser.parse_args(["-r", "sextants", "--no-color"])
        assert args.renderer == "sextants"
        assert args.no_color is True


# ─── apply_preprocessing ─────────────────────────────────────────────────────


class TestApplyPreprocessing:
    """Tests for the shared apply_preprocessing function."""

    def _make_bitmap(self) -> np.ndarray:
        """Create a test bitmap with a gradient."""
        return np.linspace(0.2, 0.8, 100).reshape(10, 10).astype(np.float32)

    def test_no_transforms(self):
        """With no flags, returns input unchanged."""
        bitmap = self._make_bitmap()
        result = apply_preprocessing(bitmap)
        np.testing.assert_array_equal(result, bitmap)

    def test_contrast(self):
        """contrast=True applies auto-contrast (stretches to 0-1)."""
        bitmap = self._make_bitmap()
        result = apply_preprocessing(bitmap, contrast=True)
        assert result.min() == pytest.approx(0.0, abs=1e-6)
        assert result.max() == pytest.approx(1.0, abs=1e-6)

    def test_dither(self):
        """dither=True produces binary output (0 or 1 only)."""
        bitmap = self._make_bitmap()
        result = apply_preprocessing(bitmap, dither=True)
        unique = set(np.unique(result))
        assert unique <= {0.0, 1.0}

    def test_invert(self):
        """invert=True flips brightness values."""
        bitmap = np.array([[0.0, 0.25], [0.75, 1.0]], dtype=np.float32)
        result = apply_preprocessing(bitmap, invert=True)
        expected = np.array([[1.0, 0.75], [0.25, 0.0]], dtype=np.float32)
        np.testing.assert_allclose(result, expected)

    def test_combined_contrast_and_invert(self):
        """contrast + invert applies both in order."""
        bitmap = self._make_bitmap()
        result = apply_preprocessing(bitmap, contrast=True, invert=True)
        # After contrast: 0..1; after invert: 1..0
        assert result.min() == pytest.approx(0.0, abs=1e-6)
        assert result.max() == pytest.approx(1.0, abs=1e-6)

    def test_combined_all(self):
        """All three transforms applied together don't crash."""
        bitmap = self._make_bitmap()
        result = apply_preprocessing(bitmap, contrast=True, dither=True, invert=True)
        assert result.shape == bitmap.shape
        unique = set(np.unique(result))
        assert unique <= {0.0, 1.0}
