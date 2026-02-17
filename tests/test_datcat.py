"""Tests for datcat core and CLI — JSON, JSONL, CSV, TSV."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from dapple.extras.datcat.datcat import (
    detect_delimiter,
    detect_format,
    dot_path_query,
    extract_field_categories,
    extract_field_values,
    flatten_to_table,
    format_json,
    format_tree,
    read_csv,
    read_json,
    select_columns,
    sort_records,
)


# ── detect_format ────────────────────────────────────────────────────


class TestDetectFormat:
    def test_json_object(self):
        assert detect_format('{"key": "value"}') == "json"

    def test_json_array(self):
        assert detect_format('[1, 2, 3]') == "json"

    def test_jsonl(self):
        text = '{"a": 1}\n{"a": 2}\n{"a": 3}'
        assert detect_format(text) == "jsonl"

    def test_single_line(self):
        assert detect_format('{"a": 1}') == "json"

    def test_empty(self):
        assert detect_format("") == "json"

    def test_multiline_json(self):
        text = '{\n  "key": "value",\n  "num": 42\n}'
        assert detect_format(text) == "json"

    def test_jsonl_arrays(self):
        text = '[1, 2]\n[3, 4]'
        assert detect_format(text) == "jsonl"

    # CSV/TSV detection
    def test_csv_by_filename(self):
        assert detect_format("anything here", filename="data.csv") == "csv"

    def test_tsv_by_filename(self):
        assert detect_format("anything here", filename="data.tsv") == "csv"

    def test_json_by_filename(self):
        assert detect_format("anything here", filename="data.json") == "json"

    def test_jsonl_by_filename(self):
        assert detect_format("anything here", filename="data.jsonl") == "jsonl"

    def test_csv_by_content_sniffing(self):
        """Non-JSON text that looks like CSV should be detected as csv."""
        text = "name,age,score\nAlice,30,95\nBob,25,87"
        assert detect_format(text) == "csv"

    def test_tsv_by_content_sniffing(self):
        text = "name\tage\nAlice\t30"
        assert detect_format(text) == "csv"


# ── read_json ────────────────────────────────────────────────────────


class TestReadJson:
    def test_json_object(self):
        result = read_json('{"name": "Alice", "age": 30}')
        assert result == {"name": "Alice", "age": 30}

    def test_json_array(self):
        result = read_json("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_jsonl(self):
        text = '{"v": 1}\n{"v": 2}\n{"v": 3}'
        result = read_json(text)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == {"v": 1}

    def test_jsonl_with_blank_lines(self):
        text = '{"a": 1}\n\n{"a": 2}\n'
        result = read_json(text)
        assert len(result) == 2

    def test_invalid_json(self):
        with pytest.raises(Exception):
            read_json("{invalid}")


# ── read_csv ─────────────────────────────────────────────────────────


class TestReadCsv:
    def test_basic_csv(self):
        text = "name,age,score\nAlice,30,95\nBob,25,87"
        records = read_csv(text)
        assert len(records) == 2
        assert records[0] == {"name": "Alice", "age": "30", "score": "95"}
        assert records[1] == {"name": "Bob", "age": "25", "score": "87"}

    def test_tsv(self):
        text = "name\tage\nAlice\t30\nBob\t25"
        records = read_csv(text)
        assert len(records) == 2
        assert records[0] == {"name": "Alice", "age": "30"}

    def test_explicit_delimiter(self):
        text = "a|b\n1|2"
        records = read_csv(text, delimiter="|")
        assert records[0] == {"a": "1", "b": "2"}

    def test_no_header(self):
        text = "Alice,30\nBob,25"
        records = read_csv(text, has_header=False)
        assert len(records) == 2
        assert records[0] == {"0": "Alice", "1": "30"}

    def test_empty_input(self):
        records = read_csv("")
        assert records == []

    def test_header_only(self):
        records = read_csv("a,b,c")
        assert records == []

    def test_ragged_rows(self):
        text = "a,b,c\n1,2\n4,5,6"
        records = read_csv(text)
        assert len(records) == 2
        assert records[0] == {"a": "1", "b": "2", "c": ""}
        assert records[1] == {"a": "4", "b": "5", "c": "6"}


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
        assert detect_delimiter("abc") == ","


# ── select_columns ───────────────────────────────────────────────────


class TestSelectColumns:
    def _sample(self) -> list[dict]:
        return [
            {"name": "Alice", "age": "30", "score": "95"},
            {"name": "Bob", "age": "25", "score": "87"},
        ]

    def test_select_subset(self):
        result = select_columns(self._sample(), ["name", "score"])
        assert result == [
            {"name": "Alice", "score": "95"},
            {"name": "Bob", "score": "87"},
        ]

    def test_select_single(self):
        result = select_columns(self._sample(), ["age"])
        assert result == [{"age": "30"}, {"age": "25"}]

    def test_reorder(self):
        result = select_columns(self._sample(), ["score", "name"])
        assert result[0] == {"score": "95", "name": "Alice"}

    def test_unknown_column(self):
        with pytest.raises(ValueError, match="Column 'missing' not found"):
            select_columns(self._sample(), ["missing"])


# ── sort_records ─────────────────────────────────────────────────────


class TestSortRecords:
    def _sample(self) -> list[dict]:
        return [
            {"name": "Charlie", "age": "35"},
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]

    def test_sort_numeric(self):
        result = sort_records(self._sample(), "age")
        assert result[0]["name"] == "Bob"
        assert result[2]["name"] == "Charlie"

    def test_sort_descending(self):
        result = sort_records(self._sample(), "age", reverse=True)
        assert result[0]["name"] == "Charlie"

    def test_sort_string(self):
        result = sort_records(self._sample(), "name")
        assert result[0]["name"] == "Alice"
        assert result[2]["name"] == "Charlie"

    def test_sort_unknown_column(self):
        with pytest.raises(ValueError, match="Column 'missing' not found"):
            sort_records(self._sample(), "missing")


# ── dot_path_query ───────────────────────────────────────────────────


class TestDotPathQuery:
    def test_simple_key(self):
        data = {"name": "Alice", "age": 30}
        assert dot_path_query(data, ".name") == "Alice"

    def test_nested_key(self):
        data = {"db": {"host": "localhost", "port": 5432}}
        assert dot_path_query(data, ".db.host") == "localhost"

    def test_array_index(self):
        data = {"items": [10, 20, 30]}
        assert dot_path_query(data, ".items[0]") == 10
        assert dot_path_query(data, ".items[2]") == 30

    def test_nested_array(self):
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        assert dot_path_query(data, ".users[1].name") == "Bob"

    def test_identity(self):
        data = {"x": 1}
        assert dot_path_query(data, ".") == {"x": 1}

    def test_empty_path(self):
        data = {"x": 1}
        assert dot_path_query(data, "") == {"x": 1}

    def test_map_over_list(self):
        data = [{"v": 1}, {"v": 2}, {"v": 3}]
        result = dot_path_query(data, ".v")
        assert result == [1, 2, 3]

    def test_missing_key(self):
        data = {"a": 1}
        with pytest.raises(KeyError):
            dot_path_query(data, ".b")

    def test_index_out_of_range(self):
        data = {"items": [1]}
        with pytest.raises(IndexError):
            dot_path_query(data, ".items[5]")

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": {"d": 42}}}}
        assert dot_path_query(data, ".a.b.c.d") == 42

    def test_chained_array_index(self):
        data = {"matrix": [[1, 2], [3, 4]]}
        assert dot_path_query(data, ".matrix[1][0]") == 3


# ── format_json ──────────────────────────────────────────────────────


class TestFormatJson:
    def test_basic_output(self):
        data = {"name": "Alice", "age": 30}
        output = format_json(data, colorize=False)
        parsed = json.loads(output)
        assert parsed == data

    def test_colorized_contains_ansi(self):
        data = {"name": "Alice"}
        output = format_json(data, colorize=True)
        assert "\033[" in output

    def test_no_color_flag(self):
        data = {"key": "val"}
        output = format_json(data, colorize=False)
        assert "\033[" not in output

    def test_nested_structure(self):
        data = {"a": {"b": [1, True, None, "str"]}}
        output = format_json(data, colorize=False)
        parsed = json.loads(output)
        assert parsed == data

    def test_null_boolean_coloring(self):
        data = {"active": True, "deleted": False, "extra": None}
        output = format_json(data, colorize=True)
        # Should contain ANSI codes for true/false/null
        assert "true" in output
        assert "false" in output
        assert "null" in output


# ── format_tree ──────────────────────────────────────────────────────


class TestFormatTree:
    def test_simple_object(self):
        data = {"name": "Alice", "age": 30}
        output = format_tree(data)
        assert "name" in output
        assert "Alice" in output
        assert "age" in output

    def test_nested_object(self):
        data = {"db": {"host": "localhost", "port": 5432}}
        output = format_tree(data)
        assert "db" in output
        assert "host" in output
        assert "localhost" in output

    def test_array(self):
        data = {"items": [1, 2, 3]}
        output = format_tree(data)
        assert "items" in output
        assert "[0]" in output

    def test_box_drawing_chars(self):
        data = {"a": 1, "b": 2}
        output = format_tree(data)
        # Should use tree characters
        assert "\u251c" in output or "\u2514" in output

    def test_empty_object(self):
        output = format_tree({})
        # Should produce some output (at least empty tree)
        assert isinstance(output, str)

    def test_null_and_bool_leaves(self):
        data = {"active": True, "deleted": None}
        output = format_tree(data)
        assert "true" in output
        assert "null" in output


# ── flatten_to_table ─────────────────────────────────────────────────


class TestFlattenToTable:
    def test_basic(self):
        records = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        headers, rows = flatten_to_table(records)
        assert headers == ["name", "age"]
        assert rows[0] == ["Alice", "30"]
        assert rows[1] == ["Bob", "25"]

    def test_mixed_keys(self):
        records = [
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
        ]
        headers, rows = flatten_to_table(records)
        assert "a" in headers
        assert "b" in headers
        assert "c" in headers
        # Missing values become ""
        assert rows[0][headers.index("c")] == ""
        assert rows[1][headers.index("a")] == ""

    def test_empty(self):
        headers, rows = flatten_to_table([])
        assert headers == []
        assert rows == []

    def test_nested_values_stringified(self):
        records = [{"data": {"nested": True}, "name": "x"}]
        headers, rows = flatten_to_table(records)
        # Nested dict should be JSON-stringified
        data_val = rows[0][headers.index("data")]
        assert "nested" in data_val

    def test_boolean_and_null(self):
        records = [{"active": True, "deleted": None}]
        headers, rows = flatten_to_table(records)
        assert rows[0][headers.index("active")] == "true"
        assert rows[0][headers.index("deleted")] == ""


# ── extract_field_values ─────────────────────────────────────────────


class TestExtractFieldValues:
    def test_basic(self):
        records = [{"v": 1}, {"v": 2}, {"v": 3}]
        result = extract_field_values(records, ".v")
        assert result == [1.0, 2.0, 3.0]

    def test_nested(self):
        records = [{"data": {"val": 10}}, {"data": {"val": 20}}]
        result = extract_field_values(records, ".data.val")
        assert result == [10.0, 20.0]

    def test_skips_missing(self):
        records = [{"v": 1}, {"x": 2}, {"v": 3}]
        result = extract_field_values(records, ".v")
        assert result == [1.0, 3.0]

    def test_skips_non_numeric(self):
        records = [{"v": 1}, {"v": "hello"}, {"v": 3}]
        result = extract_field_values(records, ".v")
        assert result == [1.0, 3.0]

    def test_no_values(self):
        records = [{"a": "x"}, {"a": "y"}]
        with pytest.raises(ValueError, match="No numeric"):
            extract_field_values(records, ".a")

    def test_empty_records(self):
        with pytest.raises(ValueError, match="No numeric"):
            extract_field_values([], ".v")

    # CSV-style column name access (no dot prefix)
    def test_csv_column_name(self):
        """extract_field_values with a plain column name (CSV style)."""
        records = [{"score": "95"}, {"score": "87"}, {"score": "92"}]
        result = extract_field_values(records, "score")
        assert result == [95.0, 87.0, 92.0]


# ── extract_field_categories ─────────────────────────────────────────


class TestExtractFieldCategories:
    def test_basic(self):
        records = [
            {"status": "ok"},
            {"status": "err"},
            {"status": "ok"},
            {"status": "ok"},
        ]
        labels, counts = extract_field_categories(records, ".status")
        assert labels[0] == "ok"
        assert counts[0] == 3.0
        assert labels[1] == "err"
        assert counts[1] == 1.0

    def test_skips_missing(self):
        records = [{"s": "a"}, {"x": "b"}, {"s": "a"}]
        labels, counts = extract_field_categories(records, ".s")
        assert labels == ["a"]
        assert counts == [2.0]

    def test_no_values(self):
        with pytest.raises(ValueError, match="No values"):
            extract_field_categories([], ".s")

    def test_csv_column_name(self):
        """extract_field_categories with a plain column name."""
        records = [
            {"color": "red"},
            {"color": "blue"},
            {"color": "red"},
            {"color": "red"},
            {"color": "blue"},
        ]
        labels, counts = extract_field_categories(records, "color")
        assert labels[0] == "red"
        assert counts[0] == 3.0


# ── CLI integration ──────────────────────────────────────────────────


class TestCLI:
    def _run(self, args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "dapple.extras.datcat.cli"] + args,
            input=stdin,
            capture_output=True,
            text=True,
        )

    # JSON tests
    def test_default_is_tree(self):
        data = json.dumps({"name": "Alice", "age": 30})
        result = self._run([], stdin=data)
        assert result.returncode == 0
        assert "Alice" in result.stdout
        assert "age" in result.stdout
        # Default output is tree format (box-drawing), not raw JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(result.stdout)

    def test_json_flag(self):
        data = json.dumps({"name": "Alice", "age": 30})
        result = self._run(["--json", "--no-color"], stdin=data)
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["name"] == "Alice"

    def test_dot_path_query(self):
        data = json.dumps({"db": {"host": "localhost"}})
        result = self._run([], stdin=data)
        assert result.returncode == 0
        assert "localhost" in result.stdout

    def test_query_on_stdin(self):
        data = json.dumps({"db": {"host": "myhost", "port": 5432}})
        result = self._run(["--json", "--no-color"], stdin=data)
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["db"]["host"] == "myhost"

    def test_jsonl_table(self):
        jsonl = '{"name":"Alice","age":30}\n{"name":"Bob","age":25}'
        result = self._run(["--table"], stdin=jsonl)
        assert result.returncode == 0
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout
        assert "name" in result.stdout

    def test_tree_view(self):
        data = json.dumps({"a": {"b": 1}, "c": [1, 2]})
        result = self._run(["--tree"], stdin=data)
        assert result.returncode == 0
        assert "a" in result.stdout
        assert "b" in result.stdout

    def test_head_jsonl(self):
        jsonl = '{"v":1}\n{"v":2}\n{"v":3}\n{"v":4}\n{"v":5}'
        result = self._run(["--head", "2", "--json", "--no-color"], stdin=jsonl)
        assert result.returncode == 0
        # Should only show first 2 records
        parsed = json.loads(result.stdout)
        assert len(parsed) == 2
        assert parsed[0]["v"] == 1

    def test_tail_jsonl(self):
        jsonl = '{"v":1}\n{"v":2}\n{"v":3}\n{"v":4}\n{"v":5}'
        result = self._run(["--tail", "2", "--json", "--no-color"], stdin=jsonl)
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert len(parsed) == 2
        assert parsed[0]["v"] == 4

    def test_no_input_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.datcat.cli", "/nonexistent/file.json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_invalid_json_error(self):
        result = self._run([], stdin="{not valid json}")
        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "Error" in result.stderr

    def test_spark_nonexistent_field_clean_error(self):
        """--spark with a path that yields no numeric values should print a clean error."""
        jsonl = '{"a":"x"}\n{"a":"y"}'
        result = self._run(["--spark", ".bogus"], stdin=jsonl)
        assert result.returncode != 0
        assert "No numeric values" in result.stderr
        # Should NOT show a Python traceback
        assert "Traceback" not in result.stderr

    def test_spark_with_color_flag(self):
        """--spark with --color should render without error."""
        jsonl = '{"v":1}\n{"v":2}\n{"v":3}'
        result = self._run(["--spark", ".v", "--color", "red"], stdin=jsonl)
        assert result.returncode == 0

    def test_color_invalid_name_clean_error(self):
        """--color with an unrecognized name should print a clean error."""
        jsonl = '{"v":1}\n{"v":2}'
        result = self._run(["--spark", ".v", "--color", "neonpurple"], stdin=jsonl)
        assert result.returncode != 0
        assert "Unknown color" in result.stderr
        assert "Traceback" not in result.stderr

    def test_color_hex_value(self):
        """--color with hex value should work."""
        jsonl = '{"v":1}\n{"v":2}\n{"v":3}'
        result = self._run(["--spark", ".v", "--color", "#ff0000"], stdin=jsonl)
        assert result.returncode == 0

    # CSV tests
    def test_csv_stdin_table(self):
        result = self._run([], stdin="name,age\nAlice,30\nBob,25")
        assert result.returncode == 0
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout

    def test_csv_head_flag(self):
        csv = "x\n1\n2\n3\n4\n5"
        result = self._run(["--head", "2"], stdin=csv)
        assert result.returncode == 0
        assert "1" in result.stdout
        assert "2" in result.stdout
        lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
        # header + separator + 2 data rows = 4 lines
        assert len(lines) == 4

    def test_csv_tail_flag(self):
        csv = "x\n1\n2\n3\n4\n5"
        result = self._run(["--tail", "2"], stdin=csv)
        assert result.returncode == 0
        assert "4" in result.stdout
        assert "5" in result.stdout

    def test_csv_sort_flag(self):
        csv = "name,age\nCharlie,35\nAlice,30\nBob,25"
        result = self._run(["--sort", "age"], stdin=csv)
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        data_lines = lines[2:]
        assert "Bob" in data_lines[0]  # 25 first

    def test_csv_cols_flag(self):
        csv = "name,age,score\nAlice,30,95"
        result = self._run(["--cols", "name,score"], stdin=csv)
        assert result.returncode == 0
        assert "name" in result.stdout
        assert "score" in result.stdout
        header_line = result.stdout.strip().split("\n")[0]
        assert "age" not in header_line

    def test_csv_no_header_flag(self):
        csv = "Alice,30\nBob,25"
        result = self._run(["--no-header"], stdin=csv)
        assert result.returncode == 0
        assert "Alice" in result.stdout
        # Numeric headers
        assert "0" in result.stdout

    def test_csv_delimiter_flag(self):
        csv = "a|b\n1|2"
        result = self._run(["--delimiter", "|"], stdin=csv)
        assert result.returncode == 0
        assert "a" in result.stdout
        assert "b" in result.stdout

    def test_csv_backslash_t_delimiter(self, tmp_path):
        """--delimiter '\\t' should work as tab delimiter."""
        tsv = tmp_path / "data.tsv"
        tsv.write_text("a\tb\n1\t2\n")
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.datcat.cli",
             str(tsv), "--delimiter", r"\t"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "a" in result.stdout
        assert "b" in result.stdout

    def test_csv_sort_desc_flag(self):
        csv = "name,age\nCharlie,35\nAlice,30\nBob,25"
        result = self._run(["--sort", "age", "--desc"], stdin=csv)
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        data_lines = lines[2:]
        assert "Charlie" in data_lines[0]  # 35 first (descending)

    def test_csv_file_input(self, tmp_path):
        """CSV file should be auto-detected by extension."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.datcat.cli", str(csv_file)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout


class TestFieldNotFoundMessage:
    def _run(self, args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "dapple.extras.datcat.cli"] + args,
            input=stdin,
            capture_output=True,
            text=True,
        )

    def test_plot_suggests_available_fields(self):
        """--plot with wrong field should list available fields."""
        jsonl = '{"latency": 100, "status": "ok"}\n{"latency": 200, "status": "err"}\n'
        result = self._run(["--plot", "nonexistent"], stdin=jsonl)
        assert result.returncode == 1
        assert "nonexistent" in result.stderr
        assert "latency" in result.stderr  # should suggest available fields

    def test_spark_suggests_available_fields(self):
        jsonl = '{"latency": 100, "region": "us"}\n{"latency": 200, "region": "eu"}\n'
        result = self._run(["--spark", "bogus"], stdin=jsonl)
        assert result.returncode == 1
        assert "latency" in result.stderr
