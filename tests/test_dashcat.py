"""Tests for dashcat — YAML-driven dashboard."""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path

import pytest


def _make_data_file(records: list[dict]) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False)
    for rec in records:
        f.write(json.dumps(rec) + "\n")
    f.close()
    return Path(f.name)


def _make_yaml(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


class TestDashcat:
    def test_sparkline_dashboard(self):
        from dapple.extras.dashcat.dashcat import dashcat

        data_path = _make_data_file([
            {"cpu": 10 + i, "mem": 50 + i} for i in range(20)
        ])
        yaml_content = f"""
rows:
  - cells:
    - type: sparkline
      source: {data_path}
      query: .cpu
      title: CPU
    - type: sparkline
      source: {data_path}
      query: .mem
      title: Memory
"""
        yaml_path = _make_yaml(yaml_content)

        try:
            buf = StringIO()
            dashcat(yaml_path, width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            data_path.unlink(missing_ok=True)
            yaml_path.unlink(missing_ok=True)

    def test_bar_chart_dashboard(self):
        from dapple.extras.dashcat.dashcat import dashcat

        import csv
        import tempfile
        csv_f = tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False)
        writer = csv.writer(csv_f)
        writer.writerow(["region", "revenue"])
        for r, v in [("east", 100), ("west", 200), ("north", 150)]:
            writer.writerow([r, v])
        csv_f.close()
        csv_path = Path(csv_f.name)

        yaml_content = f"""
rows:
  - cells:
    - type: bar_chart
      source: {csv_path}
      x: region
      y: revenue
      title: Revenue
"""
        yaml_path = _make_yaml(yaml_content)

        try:
            buf = StringIO()
            dashcat(yaml_path, width=60, dest=buf)
            output = buf.getvalue()
            assert len(output) > 0
        finally:
            csv_path.unlink(missing_ok=True)
            yaml_path.unlink(missing_ok=True)

    def test_invalid_layout(self, capsys):
        from dapple.extras.dashcat.dashcat import dashcat

        yaml_path = _make_yaml("invalid: true")
        try:
            buf = StringIO()
            dashcat(yaml_path, width=60, dest=buf)
            captured = capsys.readouterr()
            assert "error" in captured.err.lower() or "rows" in captured.err.lower()
        finally:
            yaml_path.unlink(missing_ok=True)


class TestDashcatCLI:
    def test_help(self):
        import subprocess
        result = subprocess.run(
            ["python", "-m", "dapple.extras.dashcat.dashcat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
