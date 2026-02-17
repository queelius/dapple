"""Tests for dapple.skill — unified Claude Code skill generation."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from dapple.skill import (
    _can_import,
    detect_extras,
    generate_skill,
    install,
)


# ─── _can_import ─────────────────────────────────────────────────────────────


class TestCanImport:
    def test_importable_module(self):
        assert _can_import("sys") is True

    def test_nonexistent_module(self):
        assert _can_import("nonexistent_module_xyz_42") is False

    def test_multiple_all_present(self):
        assert _can_import("sys", "os", "pathlib") is True

    def test_multiple_one_missing(self):
        assert _can_import("sys", "nonexistent_module_xyz_42") is False

    def test_empty(self):
        assert _can_import() is True


# ─── detect_extras ───────────────────────────────────────────────────────────


class TestDetectExtras:
    def test_returns_all_keys(self):
        result = detect_extras()
        expected_keys = {
            "imgcat", "pdfcat", "mdcat", "vidcat", "datcat", "funcat",
            "compcat", "thumbcat", "ansicat", "plotcat", "dashcat",
        }
        assert set(result.keys()) == expected_keys

    def test_all_values_are_bool(self):
        result = detect_extras()
        for val in result.values():
            assert isinstance(val, bool)

    def test_zero_dep_extras_always_available(self):
        """datcat, funcat, ansicat, plotcat have no extra deps — always True."""
        result = detect_extras()
        assert result["datcat"] is True
        assert result["funcat"] is True
        assert result["ansicat"] is True
        assert result["plotcat"] is True


# ─── generate_skill ──────────────────────────────────────────────────────────


class TestGenerateSkill:
    def test_all_available(self):
        """With all extras available, all tool names appear."""
        extras = {k: True for k in ("imgcat", "pdfcat", "mdcat", "vidcat", "datcat", "funcat")}
        content = generate_skill(extras)
        assert "imgcat" in content
        assert "pdfcat" in content
        assert "mdcat" in content
        assert "vidcat" in content
        assert "datcat" in content
        assert "funcat" in content

    def test_none_available(self):
        """With nothing available, get the 'no extras' message."""
        extras = {k: False for k in ("imgcat", "pdfcat", "mdcat", "vidcat", "datcat", "funcat")}
        content = generate_skill(extras)
        assert "No extras detected" in content
        assert "imgcat" not in content.split("No extras detected")[1]

    def test_partial_availability(self):
        """Only available tools appear in tool table."""
        extras = {
            "imgcat": True,
            "pdfcat": False,
            "mdcat": False,
            "vidcat": False,
            "datcat": True,
            "funcat": True,
        }
        content = generate_skill(extras)
        assert "| `imgcat`" in content
        assert "| `datcat`" in content
        assert "| `funcat`" in content
        assert "| `pdfcat`" not in content
        assert "| `mdcat`" not in content
        assert "### pdfcat" not in content

    def test_has_yaml_frontmatter(self):
        """Generated skill has YAML frontmatter with name and description."""
        content = generate_skill({k: True for k in ("imgcat",)})
        assert content.startswith("---\n")
        assert "name: dapple" in content
        assert "description:" in content

    def test_has_common_flags(self):
        """Generated skill includes the common flags section."""
        content = generate_skill({"imgcat": True})
        assert "## Common Flags" in content
        assert "-r RENDERER" in content
        assert "-w WIDTH" in content

    def test_has_renderer_guidance(self):
        """Generated skill includes renderer selection guidance."""
        content = generate_skill({"imgcat": True})
        assert "## Choosing a Renderer" in content
        assert "sextants" in content
        assert "braille" in content

    def test_has_regeneration_note(self):
        """Generated skill tells how to regenerate."""
        content = generate_skill({"imgcat": True})
        assert "dapple-skill --global" in content

    def test_auto_detect(self):
        """generate_skill() with no args auto-detects extras."""
        content = generate_skill()
        # Should at least have the zero-dep extras
        assert "| `datcat`" in content
        assert "| `funcat`" in content


# ─── install ─────────────────────────────────────────────────────────────────


class TestInstall:
    def test_install_global(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert install(global_=True) is True
        skill_file = tmp_path / ".claude" / "skills" / "dapple" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        assert "name: dapple" in content

    def test_install_local(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        assert install(local=True) is True
        skill_file = tmp_path / ".claude" / "skills" / "dapple" / "SKILL.md"
        assert skill_file.exists()

    def test_install_neither(self, capsys: pytest.CaptureFixture):
        assert install() is False
        captured = capsys.readouterr()
        assert "Specify --global or --local" in captured.err


# ─── CLI (main) ──────────────────────────────────────────────────────────────


class TestCLI:
    def test_show(self, capsys: pytest.CaptureFixture):
        from dapple.skill import main

        with patch("sys.argv", ["dapple-skill", "--show"]):
            main()
        output = capsys.readouterr().out
        assert "name: dapple" in output
        assert "Terminal Graphics Toolkit" in output

    def test_detect(self, capsys: pytest.CaptureFixture):
        from dapple.skill import main

        with patch("sys.argv", ["dapple-skill", "--detect"]):
            main()
        output = capsys.readouterr().out
        assert "imgcat" in output
        assert "available" in output or "missing" in output

    def test_no_args_exits(self):
        from dapple.skill import main

        with patch("sys.argv", ["dapple-skill"]):
            with pytest.raises(SystemExit, match="1"):
                main()

    def test_global_install(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        from dapple.skill import main

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch("sys.argv", ["dapple-skill", "--global"]):
            with pytest.raises(SystemExit, match="0"):
                main()
        assert (tmp_path / ".claude" / "skills" / "dapple" / "SKILL.md").exists()
