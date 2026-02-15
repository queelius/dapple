"""Tests for thumbcat — image contact sheet."""

from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path

import numpy as np
import pytest


class TestThumbcat:
    def _make_temp_images(self, count=3):
        """Create temporary image files."""
        from PIL import Image
        paths = []
        for i in range(count):
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img = Image.fromarray(
                np.random.randint(0, 255, (30, 30, 3), dtype=np.uint8)
            )
            img.save(f.name)
            paths.append(Path(f.name))
            f.close()
        return paths

    def test_basic_grid(self):
        from dapple.extras.thumbcat.thumbcat import thumbcat

        paths = self._make_temp_images(4)
        try:
            buf = StringIO()
            thumbcat(paths, cols=2, width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            for p in paths:
                p.unlink(missing_ok=True)

    def test_titles(self):
        from dapple.extras.thumbcat.thumbcat import thumbcat

        paths = self._make_temp_images(2)
        try:
            buf = StringIO()
            thumbcat(paths, cols=2, width=60, titles=True, dest=buf)
            output = buf.getvalue()
            # Filenames should appear as titles
            assert paths[0].name in output
        finally:
            for p in paths:
                p.unlink(missing_ok=True)

    def test_no_titles(self):
        from dapple.extras.thumbcat.thumbcat import thumbcat

        paths = self._make_temp_images(2)
        try:
            buf = StringIO()
            thumbcat(paths, cols=2, width=60, titles=False, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            for p in paths:
                p.unlink(missing_ok=True)

    def test_single_image(self):
        from dapple.extras.thumbcat.thumbcat import thumbcat

        paths = self._make_temp_images(1)
        try:
            buf = StringIO()
            thumbcat(paths, cols=1, width=40, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            for p in paths:
                p.unlink(missing_ok=True)
