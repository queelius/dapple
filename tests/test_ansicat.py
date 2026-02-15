"""Tests for ansicat — ANSI art viewer."""

from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path

import pytest


class TestAnsicat:
    def test_braille_art(self):
        """Parse and re-render braille art."""
        from dapple.extras.ansicat.ansicat import ansicat

        # Write some braille art to a temp file
        art = "⠿⠿⠿⠿⠿⠿⠿⠿\n⠿⠿⠿⠿⠿⠿⠿⠿\n"
        with tempfile.NamedTemporaryFile(suffix=".ans", mode="w", delete=False) as f:
            f.write(art)
            temp_path = Path(f.name)

        try:
            buf = StringIO()
            ansicat(temp_path, renderer="braille", width=20, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            temp_path.unlink(missing_ok=True)

    def test_nonexistent_file(self, capsys):
        from dapple.extras.ansicat.ansicat import ansicat
        buf = StringIO()
        ansicat("/nonexistent.ans", dest=buf)
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()


class TestAnsicatCLI:
    def test_help(self):
        import subprocess
        result = subprocess.run(
            ["python", "-m", "dapple.extras.ansicat.ansicat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "ansicat" in result.stdout.lower() or "ansi" in result.stdout.lower()
