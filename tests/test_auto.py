"""Tests for dapple.auto module."""

import os
from unittest.mock import patch

import pytest

from dapple.auto import (
    Protocol,
    TerminalInfo,
    auto_renderer,
    detect_kitty,
    detect_sixel,
    detect_color_support,
    detect_protocol,
    detect_terminal,
)


class TestProtocolDetection:
    """Tests for terminal protocol detection."""

    def test_detect_kitty_with_kitty_window_id(self):
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1"}):
            assert detect_kitty() is True

    def test_detect_kitty_with_ghostty(self):
        with patch.dict(os.environ, {"GHOSTTY_RESOURCES_DIR": "/path"}, clear=True):
            assert detect_kitty() is True

    def test_detect_kitty_absent(self):
        with patch.dict(os.environ, {}, clear=True):
            assert detect_kitty() is False

    def test_detect_sixel_foot(self):
        with patch.dict(os.environ, {"TERM": "foot"}, clear=True):
            assert detect_sixel() is True

    def test_detect_sixel_wezterm(self):
        with patch.dict(os.environ, {"TERM_PROGRAM": "WezTerm"}, clear=True):
            assert detect_sixel() is True

    def test_detect_sixel_absent(self):
        with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True):
            assert detect_sixel() is False

    def test_detect_color_support_no_color(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert detect_color_support() is False

    def test_detect_color_support_colorterm(self):
        with patch.dict(os.environ, {"COLORTERM": "truecolor"}, clear=True):
            assert detect_color_support() is True

    def test_detect_color_support_term_dumb(self):
        """TERM=dumb should disable colour output (POSIX convention)."""
        with patch.dict(os.environ, {"TERM": "dumb"}, clear=True):
            assert detect_color_support() is False

    def test_detect_color_support_unknown_defaults_false(self):
        """No markers at all → err on the side of no colour."""
        with patch.dict(os.environ, {}, clear=True):
            assert detect_color_support() is False

    def test_detect_color_support_xterm_256color(self):
        """xterm-256color is the standard colour-capable TERM."""
        with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True):
            assert detect_color_support() is True


class TestProtocol:
    """Tests for Protocol enum."""

    def test_protocol_values(self):
        assert Protocol.KITTY.value == "kitty"
        assert Protocol.SIXEL.value == "sixel"
        assert Protocol.QUADRANTS.value == "quadrants"
        assert Protocol.BRAILLE.value == "braille"
        assert Protocol.ASCII.value == "ascii"


class TestTerminalInfo:
    """Tests for TerminalInfo dataclass."""

    def test_is_pixel_renderer_kitty(self):
        info = TerminalInfo(protocol=Protocol.KITTY)
        assert info.is_pixel_renderer is True

    def test_is_pixel_renderer_sixel(self):
        info = TerminalInfo(protocol=Protocol.SIXEL)
        assert info.is_pixel_renderer is True

    def test_is_pixel_renderer_quadrants(self):
        info = TerminalInfo(protocol=Protocol.QUADRANTS)
        assert info.is_pixel_renderer is False

    def test_is_pixel_renderer_braille(self):
        info = TerminalInfo(protocol=Protocol.BRAILLE)
        assert info.is_pixel_renderer is False


class TestDetectProtocol:
    """Tests for detect_protocol function."""

    def test_prefers_kitty(self):
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1", "TERM": "foot"}, clear=True):
            assert detect_protocol() == Protocol.KITTY

    def test_falls_back_to_sixel(self):
        with patch.dict(os.environ, {"TERM": "foot"}, clear=True):
            assert detect_protocol() == Protocol.SIXEL

    def test_falls_back_to_quadrants(self):
        with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True):
            assert detect_protocol() == Protocol.QUADRANTS


class TestAutoRenderer:
    """Tests for auto_renderer function."""

    def test_plain_mode_returns_ascii(self):
        renderer = auto_renderer(plain=True)
        from dapple import ascii
        assert renderer is ascii

    def test_returns_renderer(self):
        """auto_renderer returns a valid renderer."""
        renderer = auto_renderer()
        # Should have required renderer protocol attributes
        assert hasattr(renderer, "cell_width")
        assert hasattr(renderer, "cell_height")
        assert hasattr(renderer, "render")

    def test_prefer_color_false(self):
        """prefer_color=False should work without error."""
        renderer = auto_renderer(prefer_color=False)
        assert hasattr(renderer, "render")
