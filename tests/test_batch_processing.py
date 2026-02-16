"""Tests for batch processing across dapple extras CLIs.

Validates the consistent batch processing pattern: multiple file args,
error collection, exit codes, separators, and graceful error handling.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# csvcat batch processing
# ---------------------------------------------------------------------------

class TestCsvCatBatch:
    """Batch processing tests for csvcat."""

    def _run(self, args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "dapple.extras.csvcat.cli"] + args,
            input=stdin, capture_output=True, text=True,
        )

    def test_multiple_valid_files(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "a.csv"
            f1.write_text("name,val\nalice,1\nbob,2\n")
            f2 = Path(d) / "b.csv"
            f2.write_text("name,val\ncarol,3\n")

            r = self._run([str(f1), str(f2)])
            assert r.returncode == 0
            assert "alice" in r.stdout
            assert "carol" in r.stdout

    def test_separators_shown_for_multiple_files(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "x.csv"
            f1.write_text("a\n1\n")
            f2 = Path(d) / "y.csv"
            f2.write_text("a\n2\n")

            r = self._run([str(f1), str(f2)])
            assert r.returncode == 0
            assert "====" in r.stdout
            assert "x.csv" in r.stdout
            assert "y.csv" in r.stdout

    def test_no_separator_for_single_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "only.csv"
            f.write_text("a\n1\n")

            r = self._run([str(f)])
            assert r.returncode == 0
            assert "====" not in r.stdout

    def test_mix_valid_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "good.csv"
            f.write_text("a\n1\n")

            r = self._run([str(f), "/nonexistent/bad.csv"])
            assert r.returncode == 1
            assert "1" in r.stdout  # good file processed
            assert "Error:" in r.stderr
            assert "bad.csv" in r.stderr

    def test_all_missing_exit_1(self):
        r = self._run(["/no/a.csv", "/no/b.csv"])
        assert r.returncode == 1
        assert "Error:" in r.stderr

    def test_error_on_stderr_only(self):
        r = self._run(["/nonexistent.csv"])
        assert r.returncode == 1
        assert "Error:" in r.stderr
        assert "Error:" not in r.stdout

    def test_output_file_not_overwritten_in_batch(self):
        """Multiple files with --output should append, not overwrite."""
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "a.csv"
            f1.write_text("name\nalice\n")
            f2 = Path(d) / "b.csv"
            f2.write_text("name\nbob\n")
            out = Path(d) / "out.txt"

            r = self._run([str(f1), str(f2), "-o", str(out)])
            assert r.returncode == 0
            content = out.read_text()
            assert "alice" in content
            assert "bob" in content


# ---------------------------------------------------------------------------
# datcat batch processing
# ---------------------------------------------------------------------------

class TestDataCatBatch:
    """Batch processing tests for datcat."""

    def _run(self, args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "dapple.extras.datcat.cli"] + args,
            input=stdin, capture_output=True, text=True,
        )

    def test_multiple_valid_files(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "a.json"
            f1.write_text('{"name": "alice"}')
            f2 = Path(d) / "b.json"
            f2.write_text('{"name": "bob"}')

            r = self._run([str(f1), str(f2)])
            assert r.returncode == 0
            assert "alice" in r.stdout
            assert "bob" in r.stdout

    def test_separators_shown(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "x.json"
            f1.write_text('{"a": 1}')
            f2 = Path(d) / "y.json"
            f2.write_text('{"b": 2}')

            r = self._run([str(f1), str(f2)])
            assert r.returncode == 0
            assert "====" in r.stdout
            assert "x.json" in r.stdout
            assert "y.json" in r.stdout

    def test_no_separator_single_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "one.json"
            f.write_text('{"a": 1}')

            r = self._run([str(f)])
            assert r.returncode == 0
            assert "====" not in r.stdout

    def test_mix_valid_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "good.json"
            f.write_text('{"ok": true}')

            r = self._run([str(f), "/nonexistent/bad.json"])
            assert r.returncode == 1
            assert "ok" in r.stdout
            assert "Error:" in r.stderr

    def test_all_missing_exit_1(self):
        r = self._run(["/no/a.json", "/no/b.json"])
        assert r.returncode == 1
        assert "Error:" in r.stderr

    def test_query_flag(self):
        """--query should extract nested fields."""
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "data.json"
            f.write_text('{"db": {"host": "localhost", "port": 5432}}')

            r = self._run([str(f), "-q", ".db.host"])
            assert r.returncode == 0
            assert "localhost" in r.stdout

    def test_output_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "a.json"
            f1.write_text('{"x": "first"}')
            f2 = Path(d) / "b.json"
            f2.write_text('{"x": "second"}')
            out = Path(d) / "out.txt"

            r = self._run([str(f1), str(f2), "-o", str(out)])
            assert r.returncode == 0
            content = out.read_text()
            assert "first" in content
            assert "second" in content


# ---------------------------------------------------------------------------
# mdcat batch processing
# ---------------------------------------------------------------------------

mdcat_available = pytest.importorskip("rich", reason="rich required for mdcat")


class TestMdCatBatch:
    """Batch processing tests for mdcat."""

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "dapple.extras.mdcat.mdcat"] + args,
            capture_output=True, text=True,
        )

    def test_multiple_valid_files(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "one.md"
            f1.write_text("# First\n\nContent one.")
            f2 = Path(d) / "two.md"
            f2.write_text("# Second\n\nContent two.")

            r = self._run([str(f1), str(f2), "--no-images"])
            assert r.returncode == 0
            assert "First" in r.stdout
            assert "Second" in r.stdout

    def test_separators_shown(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "alpha.md"
            f1.write_text("# Alpha")
            f2 = Path(d) / "beta.md"
            f2.write_text("# Beta")

            r = self._run([str(f1), str(f2), "--no-images"])
            assert r.returncode == 0
            assert "====" in r.stdout
            assert "alpha.md" in r.stdout
            assert "beta.md" in r.stdout

    def test_no_separator_single_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "only.md"
            f.write_text("# Only")

            r = self._run([str(f), "--no-images"])
            assert r.returncode == 0
            assert "====" not in r.stdout

    def test_mix_valid_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "good.md"
            f.write_text("# Good File")

            r = self._run([str(f), "/nonexistent/bad.md", "--no-images"])
            assert r.returncode == 1
            assert "Good File" in r.stdout
            assert "Error:" in r.stderr

    def test_all_missing_exit_1(self):
        r = self._run(["/no/a.md", "/no/b.md"])
        assert r.returncode == 1
        assert "Error:" in r.stderr

    def test_no_files_exits_nonzero(self):
        r = self._run([])
        assert r.returncode == 1


# ---------------------------------------------------------------------------
# funcat batch processing (multiple expressions)
# ---------------------------------------------------------------------------

class TestFunCatBatch:
    """Batch processing tests for funcat (multiple expressions)."""

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "dapple.extras.funcat.funcat"] + args,
            capture_output=True, text=True,
        )

    def test_multiple_expressions(self):
        r = self._run(["sin(x)", "cos(x)", "-r", "braille"])
        assert r.returncode == 0
        assert len(r.stdout.strip()) > 0

    def test_single_expression(self):
        r = self._run(["x**2", "-r", "braille"])
        assert r.returncode == 0
        assert len(r.stdout.strip()) > 0

    def test_no_expression_exits_nonzero(self):
        r = self._run([])
        assert r.returncode != 0
