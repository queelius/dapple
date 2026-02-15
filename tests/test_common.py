"""Tests for dapple.extras.common shared utilities."""

from __future__ import annotations


class TestUnescapeDelimiter:
    def test_tab(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter(r"\t") == "\t"

    def test_newline(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter(r"\n") == "\n"

    def test_backslash(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter("\\\\") == "\\"

    def test_plain_char(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter(",") == ","

    def test_pipe(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter("|") == "|"

    def test_already_tab(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter("\t") == "\t"


class TestAvailableFields:
    def test_dict_records(self):
        from dapple.extras.common import available_fields
        records = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
        fields = available_fields(records)
        assert "a" in fields
        assert "b" in fields
        assert "c" in fields

    def test_empty_records(self):
        from dapple.extras.common import available_fields
        assert available_fields([]) == []

    def test_non_dict_records(self):
        from dapple.extras.common import available_fields
        assert available_fields([1, 2, 3]) == []


class TestPagedOutput:
    def test_no_pager(self):
        """When pager=False, yields the original dest."""
        from io import StringIO
        from dapple.extras.common import paged_output

        buf = StringIO()
        with paged_output(buf, pager=False) as out:
            out.write("hello")
        assert buf.getvalue() == "hello"

    def test_non_stdout_ignores_pager(self):
        """When dest is not stdout, pager is ignored."""
        from io import StringIO
        from dapple.extras.common import paged_output

        buf = StringIO()
        with paged_output(buf, pager=True) as out:
            out.write("hello")
        assert buf.getvalue() == "hello"


class TestStdinToTempfile:
    def test_creates_and_cleans(self):
        """Creates a temp file from stdin bytes and cleans up."""
        import io
        from unittest.mock import patch
        from dapple.extras.common import stdin_to_tempfile

        fake_stdin = io.BytesIO(b"fake image data")
        with patch("dapple.extras.common.sys.stdin", new_callable=lambda: type(
            "FakeStdin", (), {"buffer": fake_stdin}
        )):
            with stdin_to_tempfile(suffix=".png") as path:
                assert path.exists()
                assert path.read_bytes() == b"fake image data"
                assert path.suffix == ".png"
            # Cleaned up
            assert not path.exists()
