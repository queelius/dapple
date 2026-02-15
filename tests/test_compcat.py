"""Tests for compcat — renderer comparison tool."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from dapple import Canvas


class TestCompcat:
    def test_compcat_with_canvas(self):
        """compcat renders a grid of renderers."""
        from dapple.extras.compcat.compcat import compcat

        # Create a temp image
        import tempfile
        from PIL import Image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
            img.save(f.name)
            temp_path = Path(f.name)

        try:
            buf = StringIO()
            compcat(temp_path, ["braille", "sextants"], width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            temp_path.unlink(missing_ok=True)

    def test_compcat_default_renderers(self):
        """compcat works with default renderer list."""
        from dapple.extras.compcat.compcat import DEFAULT_RENDERERS
        assert "braille" in DEFAULT_RENDERERS
        assert len(DEFAULT_RENDERERS) >= 3


class TestCompCLI:
    def test_help(self):
        """CLI --help should work."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "dapple.extras.compcat.compcat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "compcat" in result.stdout.lower() or "compare" in result.stdout.lower()
