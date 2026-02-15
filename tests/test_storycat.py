"""Tests for storycat — video storyboard grid."""

from __future__ import annotations

import subprocess
import pytest


class TestStorycatCLI:
    def test_help(self):
        result = subprocess.run(
            ["python", "-m", "dapple.extras.storycat.storycat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "storycat" in result.stdout.lower() or "storyboard" in result.stdout.lower()

    def test_nonexistent_file(self):
        result = subprocess.run(
            ["python", "-m", "dapple.extras.storycat.storycat", "/nonexistent.mp4"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


class TestStorycatImports:
    def test_import(self):
        from dapple.extras.storycat import storycat, main
        assert callable(storycat)
        assert callable(main)
