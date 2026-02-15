"""Tests for diffcat — visual image diff."""

from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path

import numpy as np
import pytest


def _make_temp_image(arr=None):
    """Create a temp image file."""
    from PIL import Image
    if arr is None:
        arr = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.fromarray(arr)
    img.save(f.name)
    f.close()
    return Path(f.name)


class TestDiffcat:
    def test_side_mode(self):
        from dapple.extras.diffcat.diffcat import diffcat

        a = _make_temp_image()
        b = _make_temp_image()
        try:
            buf = StringIO()
            diffcat(a, b, mode="side", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            a.unlink(missing_ok=True)
            b.unlink(missing_ok=True)

    def test_overlay_mode(self):
        from dapple.extras.diffcat.diffcat import diffcat

        a = _make_temp_image(np.zeros((50, 50, 3), dtype=np.uint8))
        b = _make_temp_image(np.full((50, 50, 3), 128, dtype=np.uint8))
        try:
            buf = StringIO()
            diffcat(a, b, mode="overlay", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            a.unlink(missing_ok=True)
            b.unlink(missing_ok=True)

    def test_highlight_mode(self):
        from dapple.extras.diffcat.diffcat import diffcat

        a = _make_temp_image()
        b = _make_temp_image()
        try:
            buf = StringIO()
            diffcat(a, b, mode="highlight", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            a.unlink(missing_ok=True)
            b.unlink(missing_ok=True)

    def test_different_sizes(self):
        """Images of different sizes should still work (B resized to A)."""
        from dapple.extras.diffcat.diffcat import diffcat

        a = _make_temp_image(np.zeros((50, 50, 3), dtype=np.uint8))
        b = _make_temp_image(np.zeros((100, 80, 3), dtype=np.uint8))
        try:
            buf = StringIO()
            diffcat(a, b, mode="side", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            a.unlink(missing_ok=True)
            b.unlink(missing_ok=True)


class TestDiffcatCLI:
    def test_help(self):
        import subprocess
        result = subprocess.run(
            ["python", "-m", "dapple.extras.diffcat.diffcat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
