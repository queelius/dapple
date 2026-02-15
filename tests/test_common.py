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
