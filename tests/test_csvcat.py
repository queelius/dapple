"""Tests for csvcat core and CLI."""

from __future__ import annotations

import io
import subprocess
import sys
import textwrap

import pytest

from dapple.extras.csvcat.csvcat import (
    CsvData,
    detect_delimiter,
    extract_categories,
    extract_numeric,
    format_table,
    head,
    read_csv,
    select_columns,
    sort_by,
    tail,
)


# ── detect_delimiter ─────────────────────────────────────────────────


class TestDetectDelimiter:
    def test_comma(self):
        assert detect_delimiter("a,b,c\n1,2,3") == ","

    def test_tab(self):
        assert detect_delimiter("a\tb\tc\n1\t2\t3") == "\t"

    def test_pipe(self):
        assert detect_delimiter("a|b|c\n1|2|3") == "|"

    def test_semicolon(self):
        assert detect_delimiter("a;b;c\n1;2;3") == ";"

    def test_fallback_to_comma(self):
        # Single column or ambiguous => fallback
        assert detect_delimiter("abc") == ","


# ── read_csv ─────────────────────────────────────────────────────────


class TestReadCsv:
    def test_basic_csv(self):
        text = "name,age,score\nAlice,30,95\nBob,25,87"
        data = read_csv(io.StringIO(text))
        assert data.headers == ["name", "age", "score"]
        assert len(data.rows) == 2
        assert data.rows[0] == ["Alice", "30", "95"]

    def test_tsv(self):
        text = "name\tage\nAlice\t30\nBob\t25"
        data = read_csv(io.StringIO(text))
        assert data.headers == ["name", "age"]
        assert data.rows[0] == ["Alice", "30"]

    def test_explicit_delimiter(self):
        text = "a|b\n1|2"
        data = read_csv(io.StringIO(text), delimiter="|")
        assert data.headers == ["a", "b"]
        assert data.rows[0] == ["1", "2"]

    def test_no_header(self):
        text = "Alice,30\nBob,25"
        data = read_csv(io.StringIO(text), has_header=False)
        assert data.headers == ["0", "1"]
        assert len(data.rows) == 2
        assert data.rows[0] == ["Alice", "30"]

    def test_empty_input(self):
        data = read_csv(io.StringIO(""))
        assert data.headers == []
        assert data.rows == []

    def test_header_only(self):
        data = read_csv(io.StringIO("a,b,c"))
        assert data.headers == ["a", "b", "c"]
        assert data.rows == []

    def test_ragged_rows(self):
        text = "a,b,c\n1,2\n4,5,6"
        data = read_csv(io.StringIO(text))
        assert data.headers == ["a", "b", "c"]
        assert data.rows[0] == ["1", "2"]  # Missing col c
        assert data.rows[1] == ["4", "5", "6"]


# ── select_columns ───────────────────────────────────────────────────


class TestSelectColumns:
    def _sample(self) -> CsvData:
        return CsvData(
            headers=["name", "age", "score"],
            rows=[["Alice", "30", "95"], ["Bob", "25", "87"]],
        )

    def test_select_subset(self):
        result = select_columns(self._sample(), ["name", "score"])
        assert result.headers == ["name", "score"]
        assert result.rows[0] == ["Alice", "95"]

    def test_select_single(self):
        result = select_columns(self._sample(), ["age"])
        assert result.headers == ["age"]
        assert result.rows[1] == ["25"]

    def test_reorder(self):
        result = select_columns(self._sample(), ["score", "name"])
        assert result.headers == ["score", "name"]
        assert result.rows[0] == ["95", "Alice"]

    def test_unknown_column(self):
        with pytest.raises(ValueError, match="Column 'missing' not found"):
            select_columns(self._sample(), ["missing"])


# ── sort_by ──────────────────────────────────────────────────────────


class TestSortBy:
    def _sample(self) -> CsvData:
        return CsvData(
            headers=["name", "age"],
            rows=[["Charlie", "35"], ["Alice", "30"], ["Bob", "25"]],
        )

    def test_sort_numeric(self):
        result = sort_by(self._sample(), "age")
        assert result.rows[0][0] == "Bob"  # 25
        assert result.rows[2][0] == "Charlie"  # 35

    def test_sort_descending(self):
        result = sort_by(self._sample(), "age", reverse=True)
        assert result.rows[0][0] == "Charlie"  # 35

    def test_sort_string(self):
        result = sort_by(self._sample(), "name")
        assert result.rows[0][0] == "Alice"
        assert result.rows[2][0] == "Charlie"

    def test_sort_unknown_column(self):
        with pytest.raises(ValueError, match="Column 'missing' not found"):
            sort_by(self._sample(), "missing")


# ── head / tail ──────────────────────────────────────────────────────


class TestHeadTail:
    def _sample(self) -> CsvData:
        return CsvData(
            headers=["x"],
            rows=[["1"], ["2"], ["3"], ["4"], ["5"]],
        )

    def test_head(self):
        result = head(self._sample(), 3)
        assert len(result.rows) == 3
        assert result.rows[0] == ["1"]

    def test_tail(self):
        result = tail(self._sample(), 2)
        assert len(result.rows) == 2
        assert result.rows[0] == ["4"]

    def test_head_exceeds(self):
        result = head(self._sample(), 100)
        assert len(result.rows) == 5

    def test_tail_exceeds(self):
        result = tail(self._sample(), 100)
        assert len(result.rows) == 5


# ── format_table ─────────────────────────────────────────────────────


class TestFormatTable:
    def test_basic_format(self):
        data = CsvData(
            headers=["name", "age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )
        output = format_table(data)
        assert "name" in output
        assert "Alice" in output
        assert "Bob" in output
        # Should have 4 lines: header, separator, 2 data rows
        lines = output.split("\n")
        assert len(lines) == 4

    def test_empty_data(self):
        data = CsvData(headers=[], rows=[])
        assert format_table(data) == ""

    def test_numeric_right_aligned(self):
        data = CsvData(
            headers=["val"],
            rows=[["42"], ["7"]],
        )
        output = format_table(data)
        lines = output.split("\n")
        # Data rows — numeric values should be right-aligned
        data_lines = lines[2:]
        # "42" should appear after spaces, " 7" should have leading space
        assert "42" in data_lines[0]
        assert " 7" in data_lines[1]

    def test_type_coloring_numbers_cyan(self):
        data = CsvData(headers=["val"], rows=[["42"]])
        output = format_table(data)
        # Numbers get cyan ANSI: \033[36m
        assert "\033[36m" in output

    def test_type_coloring_booleans_yellow(self):
        data = CsvData(headers=["flag"], rows=[["true"]])
        output = format_table(data)
        # Booleans get yellow ANSI: \033[33m
        assert "\033[33m" in output

    def test_type_coloring_null_dim(self):
        data = CsvData(headers=["val"], rows=[["null"]])
        output = format_table(data)
        # Null-like values get dim: \033[2m
        # (separator also uses dim, so check data row specifically)
        lines = output.split("\n")
        assert "\033[2m" in lines[2]

    def test_cycle_colors(self):
        data = CsvData(
            headers=["a", "b", "c"],
            rows=[["x", "y", "z"]],
        )
        output = format_table(data, cycle_colors=True)
        # Should contain multiple different ANSI color codes
        assert "\033[36m" in output  # cyan
        assert "\033[32m" in output  # green
        assert "\033[33m" in output  # yellow


# ── extract_numeric ──────────────────────────────────────────────────


class TestExtractNumeric:
    def test_basic(self):
        data = CsvData(
            headers=["val"],
            rows=[["1.5"], ["2.0"], ["3.7"]],
        )
        result = extract_numeric(data, "val")
        assert result == [1.5, 2.0, 3.7]

    def test_skips_non_numeric(self):
        data = CsvData(
            headers=["val"],
            rows=[["1"], ["N/A"], ["3"]],
        )
        result = extract_numeric(data, "val")
        assert result == [1.0, 3.0]

    def test_integer_values(self):
        data = CsvData(
            headers=["count"],
            rows=[["10"], ["20"], ["30"]],
        )
        result = extract_numeric(data, "count")
        assert result == [10.0, 20.0, 30.0]

    def test_unknown_column(self):
        data = CsvData(headers=["a"], rows=[])
        with pytest.raises(ValueError, match="not found"):
            extract_numeric(data, "b")

    def test_no_numeric_values(self):
        data = CsvData(
            headers=["name"],
            rows=[["Alice"], ["Bob"]],
        )
        with pytest.raises(ValueError, match="No numeric"):
            extract_numeric(data, "name")


# ── extract_categories ───────────────────────────────────────────────


class TestExtractCategories:
    def test_basic(self):
        data = CsvData(
            headers=["color"],
            rows=[["red"], ["blue"], ["red"], ["red"], ["blue"]],
        )
        labels, counts = extract_categories(data, "color")
        assert labels[0] == "red"
        assert counts[0] == 3.0
        assert labels[1] == "blue"
        assert counts[1] == 2.0

    def test_single_category(self):
        data = CsvData(
            headers=["x"],
            rows=[["a"], ["a"], ["a"]],
        )
        labels, counts = extract_categories(data, "x")
        assert labels == ["a"]
        assert counts == [3.0]

    def test_unknown_column(self):
        data = CsvData(headers=["a"], rows=[])
        with pytest.raises(ValueError, match="not found"):
            extract_categories(data, "b")

    def test_numeric_column_uses_values_directly(self):
        """Numeric column should use values as bar lengths, not count occurrences."""
        data = CsvData(
            headers=["product", "q1"],
            rows=[
                ["Widget A", "12000"],
                ["Widget B", "8000"],
                ["Gadget X", "25000"],
            ],
        )
        labels, values = extract_categories(data, "q1")
        assert labels == ["Widget A", "Widget B", "Gadget X"]
        assert values == [12000.0, 8000.0, 25000.0]

    def test_numeric_column_uses_first_text_column_as_labels(self):
        """When bar-charting a numeric column, labels come from first text column."""
        data = CsvData(
            headers=["id", "name", "score"],
            rows=[["1", "Alice", "95"], ["2", "Bob", "87"]],
        )
        labels, values = extract_categories(data, "score")
        assert labels == ["Alice", "Bob"]
        assert values == [95.0, 87.0]

    def test_numeric_column_no_label_column_uses_indices(self):
        """If no text column exists, use row indices as labels."""
        data = CsvData(
            headers=["a", "b"],
            rows=[["10", "20"], ["30", "40"]],
        )
        labels, values = extract_categories(data, "b")
        # 'a' is also numeric, so row indices are used
        assert labels == ["1", "2"]
        assert values == [20.0, 40.0]


# ── CLI integration ──────────────────────────────────────────────────


class TestCLI:
    def _run(self, args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "dapple.extras.csvcat.cli"] + args,
            input=stdin,
            capture_output=True,
            text=True,
        )

    def test_stdin_table(self):
        result = self._run([], stdin="name,age\nAlice,30\nBob,25")
        assert result.returncode == 0
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout

    def test_head_flag(self):
        csv = "x\n1\n2\n3\n4\n5"
        result = self._run(["--head", "2"], stdin=csv)
        assert result.returncode == 0
        assert "1" in result.stdout
        assert "2" in result.stdout
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        # header + separator + 2 data rows = 4 lines
        assert len(lines) == 4

    def test_tail_flag(self):
        csv = "x\n1\n2\n3\n4\n5"
        result = self._run(["--tail", "2"], stdin=csv)
        assert result.returncode == 0
        assert "4" in result.stdout
        assert "5" in result.stdout

    def test_sort_flag(self):
        csv = "name,age\nCharlie,35\nAlice,30\nBob,25"
        result = self._run(["--sort", "age"], stdin=csv)
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        # Data lines (after header + separator)
        data_lines = lines[2:]
        assert "Bob" in data_lines[0]  # 25 first

    def test_cols_flag(self):
        csv = "name,age,score\nAlice,30,95"
        result = self._run(["--cols", "name,score"], stdin=csv)
        assert result.returncode == 0
        assert "name" in result.stdout
        assert "score" in result.stdout
        # age should not appear in header
        header_line = result.stdout.strip().split("\n")[0]
        assert "age" not in header_line

    def test_no_header_flag(self):
        csv = "Alice,30\nBob,25"
        result = self._run(["--no-header"], stdin=csv)
        assert result.returncode == 0
        assert "Alice" in result.stdout
        # Numeric headers
        assert "0" in result.stdout

    def test_backslash_t_parsed_as_tab(self, tmp_path):
        """--delimiter '\\t' should work as tab delimiter."""
        tsv = tmp_path / "data.tsv"
        tsv.write_text("a\tb\n1\t2\n")
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.csvcat.cli",
             str(tsv), "--delimiter", r"\t"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "a" in result.stdout
        assert "b" in result.stdout

    def test_no_input_error(self):
        # No file, TTY stdin => should exit with error
        # We can't really test TTY detection, but we can test the file path
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.csvcat.cli", "/nonexistent/file.csv"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
