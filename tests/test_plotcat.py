"""Tests for plotcat — faceted data plots."""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path

import pytest


def _make_csv(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def _make_jsonl(records: list[dict]) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False)
    for rec in records:
        f.write(json.dumps(rec) + "\n")
    f.close()
    return Path(f.name)


class TestPlotcat:
    def test_line_plot_csv(self):
        from dapple.extras.plotcat.plotcat import plotcat

        csv_path = _make_csv(
            "region,sales\neast,10\neast,20\nwest,15\nwest,25\nnorth,5\nnorth,30\n"
        )
        try:
            buf = StringIO()
            plotcat(csv_path, facet="region", plot="line", y="sales", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            csv_path.unlink(missing_ok=True)

    def test_bar_chart_jsonl(self):
        from dapple.extras.plotcat.plotcat import plotcat

        jsonl_path = _make_jsonl([
            {"category": "A", "type": "x", "value": 10},
            {"category": "A", "type": "y", "value": 20},
            {"category": "B", "type": "x", "value": 15},
            {"category": "B", "type": "y", "value": 25},
        ])
        try:
            buf = StringIO()
            plotcat(jsonl_path, facet="category", plot="bar", y="type", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            jsonl_path.unlink(missing_ok=True)

    def test_spark_plot(self):
        from dapple.extras.plotcat.plotcat import plotcat

        csv_path = _make_csv(
            "group,val\na,1\na,4\na,2\nb,8\nb,3\nb,7\n"
        )
        try:
            buf = StringIO()
            plotcat(csv_path, facet="group", plot="spark", y="val", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            csv_path.unlink(missing_ok=True)

    def test_histogram_plot(self):
        from dapple.extras.plotcat.plotcat import plotcat

        csv_path = _make_csv(
            "group,val\na,1\na,4\na,2\na,3\nb,8\nb,3\nb,7\nb,5\n"
        )
        try:
            buf = StringIO()
            plotcat(csv_path, facet="group", plot="histogram", y="val", width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            csv_path.unlink(missing_ok=True)


class TestPlotcatCLI:
    def test_help(self):
        import subprocess
        result = subprocess.run(
            ["python", "-m", "dapple.extras.plotcat.plotcat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
