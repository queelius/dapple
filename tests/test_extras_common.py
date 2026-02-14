"""Tests for dapple.extras.common shared utilities."""

from __future__ import annotations

import numpy as np
import pytest

from dapple.extras.common import apply_preprocessing, get_renderer
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
