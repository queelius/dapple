"""Tests for 3D array support in preprocess.resize()."""

from __future__ import annotations

import numpy as np
import pytest

from dapple.preprocess import resize, _resize_2d


class TestResize2D:
    """Verify _resize_2d is equivalent to the old resize behavior."""

    def test_basic_downscale(self):
        bitmap = np.ones((100, 200), dtype=np.float32)
        result = _resize_2d(bitmap, 50, 100)
        assert result.shape == (50, 100)
        assert result.dtype == np.float32
        np.testing.assert_allclose(result, 1.0)

    def test_basic_upscale(self):
        bitmap = np.ones((10, 10), dtype=np.float32) * 0.5
        result = _resize_2d(bitmap, 20, 20)
        assert result.shape == (20, 20)
        np.testing.assert_allclose(result, 0.5)


class TestResize3D:
    """Test resize() with 3D color arrays (H, W, 3)."""

    def test_resize_3d_shape(self):
        colors = np.random.rand(100, 200, 3).astype(np.float32)
        result = resize(colors, 50, 100)
        assert result.shape == (50, 100, 3)
        assert result.dtype == np.float32

    def test_resize_3d_uniform(self):
        colors = np.full((100, 200, 3), 0.5, dtype=np.float32)
        result = resize(colors, 50, 100)
        np.testing.assert_allclose(result, 0.5, atol=1e-5)

    def test_resize_3d_channels_independent(self):
        colors = np.zeros((10, 10, 3), dtype=np.float32)
        colors[:, :, 0] = 1.0  # Red channel only
        result = resize(colors, 20, 20)
        np.testing.assert_allclose(result[:, :, 0], 1.0, atol=1e-5)
        np.testing.assert_allclose(result[:, :, 1], 0.0, atol=1e-5)
        np.testing.assert_allclose(result[:, :, 2], 0.0, atol=1e-5)

    def test_resize_2d_still_works(self):
        bitmap = np.ones((100, 200), dtype=np.float32)
        result = resize(bitmap, 50, 100)
        assert result.shape == (50, 100)
        assert result.ndim == 2

    def test_resize_3d_upscale(self):
        colors = np.random.rand(10, 10, 3).astype(np.float32)
        result = resize(colors, 20, 20)
        assert result.shape == (20, 20, 3)
