"""Tests for ANSI input adapter."""

import numpy as np
import pytest

from dapple.adapters.ansi import (
    ANSIAdapter,
    ColoredChar,
    detect_format,
    from_ansi,
    parse_colors,
    _braille_to_bitmap,
    _quadrant_to_bitmap,
    _sextant_to_bitmap,
    _ascii_to_brightness,
)


class TestColorParsing:
    """Tests for ANSI color code parsing."""

    def test_parse_no_colors(self):
        """parse_colors handles text without ANSI codes."""
        result = parse_colors("hello")
        assert len(result) == 1
        assert len(result[0]) == 5
        assert result[0][0].char == "h"
        assert result[0][0].fg is None
        assert result[0][0].bg is None

    def test_parse_24bit_foreground(self):
        """parse_colors extracts 24-bit foreground color."""
        text = "\033[38;2;255;128;64mX\033[0m"
        result = parse_colors(text)
        assert result[0][0].fg == (255, 128, 64)
        assert result[0][0].char == "X"

    def test_parse_24bit_background(self):
        """parse_colors extracts 24-bit background color."""
        text = "\033[48;2;100;150;200mY\033[0m"
        result = parse_colors(text)
        assert result[0][0].bg == (100, 150, 200)

    def test_parse_256_color_rgb(self):
        """parse_colors handles 256-color cube."""
        # Color 196 = 16 + 36*4 + 6*0 + 0 = red
        text = "\033[38;5;196mR\033[0m"
        result = parse_colors(text)
        assert result[0][0].fg is not None
        # 196-16 = 180, 180/36 = 5, so r=5*51=255
        assert result[0][0].fg[0] == 255  # Red

    def test_parse_256_color_grayscale(self):
        """parse_colors handles 256-color grayscale."""
        text = "\033[38;5;244mG\033[0m"  # Middle gray
        result = parse_colors(text)
        assert result[0][0].fg is not None
        # 244-232=12, should be middle gray
        r, g, b = result[0][0].fg
        assert r == g == b  # Grayscale

    def test_parse_basic_color(self):
        """parse_colors handles basic 16 colors."""
        text = "\033[31mR\033[0m"  # Red
        result = parse_colors(text)
        assert result[0][0].fg == (128, 0, 0)

    def test_parse_bright_color(self):
        """parse_colors handles bright colors."""
        text = "\033[91mR\033[0m"  # Bright red
        result = parse_colors(text)
        assert result[0][0].fg == (255, 0, 0)

    def test_parse_reset(self):
        """parse_colors resets colors on code 0."""
        text = "\033[38;2;255;0;0mR\033[0mX"
        result = parse_colors(text)
        assert result[0][0].fg == (255, 0, 0)
        assert result[0][1].fg is None

    def test_parse_multiline(self):
        """parse_colors handles multiple lines."""
        text = "A\nB\nC"
        result = parse_colors(text)
        assert len(result) == 3
        assert result[0][0].char == "A"
        assert result[1][0].char == "B"
        assert result[2][0].char == "C"


class TestFormatDetection:
    """Tests for terminal art format detection."""

    def test_detect_braille(self):
        """detect_format identifies braille text."""
        text = "⠿⠿⠿⠿⠿"
        assert detect_format(text) == "braille"

    def test_detect_quadrants(self):
        """detect_format identifies quadrant blocks."""
        text = "▀▄▌▐█"
        assert detect_format(text) == "quadrants"

    def test_detect_ascii(self):
        """detect_format identifies ASCII art."""
        text = "  .:-=+*#%@"
        assert detect_format(text) == "ascii"

    def test_detect_with_ansi_codes(self):
        """detect_format ignores ANSI codes."""
        text = "\033[38;2;255;0;0m⠿⠿⠿\033[0m"
        assert detect_format(text) == "braille"

    def test_detect_empty(self):
        """detect_format returns None for empty input."""
        assert detect_format("") is None


class TestBrailleReversal:
    """Tests for braille to bitmap conversion."""

    def test_empty_braille(self):
        """Empty braille character produces zero bitmap."""
        result = _braille_to_bitmap("\u2800")
        np.testing.assert_array_equal(result, np.zeros((4, 2)))

    def test_full_braille(self):
        """Full braille character produces ones bitmap."""
        result = _braille_to_bitmap("\u28ff")
        np.testing.assert_array_equal(result, np.ones((4, 2)))

    def test_single_dot(self):
        """Single dot braille produces correct pattern."""
        # U+2801 has only dot 1 (top-left)
        result = _braille_to_bitmap("\u2801")
        expected = np.zeros((4, 2), dtype=np.float32)
        expected[0, 0] = 1.0
        np.testing.assert_array_equal(result, expected)

    def test_bottom_dots(self):
        """Bottom dots (bits 6,7) produce correct pattern."""
        # U+28C0 has dots 7 and 8 (bottom row)
        result = _braille_to_bitmap("\u28c0")
        expected = np.zeros((4, 2), dtype=np.float32)
        expected[3, 0] = 1.0  # dot 7
        expected[3, 1] = 1.0  # dot 8
        np.testing.assert_array_equal(result, expected)


class TestQuadrantReversal:
    """Tests for quadrant to bitmap conversion."""

    def test_empty_quadrant(self):
        """Space produces zero bitmap."""
        result = _quadrant_to_bitmap(" ")
        np.testing.assert_array_equal(result, np.zeros((2, 2)))

    def test_full_quadrant(self):
        """Full block produces ones bitmap."""
        result = _quadrant_to_bitmap("█")
        np.testing.assert_array_equal(result, np.ones((2, 2)))

    def test_upper_half(self):
        """Upper half block produces correct pattern."""
        result = _quadrant_to_bitmap("▀")
        expected = np.array([[1, 1], [0, 0]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_lower_half(self):
        """Lower half block produces correct pattern."""
        result = _quadrant_to_bitmap("▄")
        expected = np.array([[0, 0], [1, 1]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_left_half(self):
        """Left half block produces correct pattern."""
        result = _quadrant_to_bitmap("▌")
        expected = np.array([[1, 0], [1, 0]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)


class TestSextantReversal:
    """Tests for sextant to bitmap conversion."""

    def test_empty_sextant(self):
        """Space produces zero bitmap."""
        result = _sextant_to_bitmap(" ")
        np.testing.assert_array_equal(result, np.zeros((3, 2)))

    def test_full_sextant(self):
        """Full block produces ones bitmap."""
        result = _sextant_to_bitmap("█")
        np.testing.assert_array_equal(result, np.ones((3, 2)))

    def test_left_half(self):
        """Left half block produces correct pattern."""
        result = _sextant_to_bitmap("▌")
        expected = np.array([[1, 0], [1, 0], [1, 0]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_right_half(self):
        """Right half block produces correct pattern."""
        result = _sextant_to_bitmap("▐")
        expected = np.array([[0, 1], [0, 1], [0, 1]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)


class TestASCIIReversal:
    """Tests for ASCII to brightness conversion."""

    def test_space_is_dark(self):
        """Space has brightness 0."""
        assert _ascii_to_brightness(" ") == pytest.approx(0.0)

    def test_at_is_bright(self):
        """@ has maximum brightness."""
        assert _ascii_to_brightness("@") == pytest.approx(1.0)

    def test_mid_char(self):
        """Middle characters have intermediate brightness."""
        brightness = _ascii_to_brightness("=")  # Position 4 in default charset
        assert 0.3 < brightness < 0.6

    def test_unknown_char(self):
        """Unknown characters return 0.5."""
        assert _ascii_to_brightness("X") == pytest.approx(0.5)


class TestFromANSI:
    """Tests for from_ansi function."""

    def test_simple_braille(self):
        """from_ansi parses simple braille."""
        canvas = from_ansi("⠿⠿⠿")
        assert canvas.bitmap.shape == (4, 6)  # 1 row x 3 chars, 4x2 each

    def test_multiline_braille(self):
        """from_ansi parses multiline braille."""
        canvas = from_ansi("⠿⠿\n⠿⠿")
        assert canvas.bitmap.shape == (8, 4)  # 2 rows x 2 chars

    def test_colored_braille(self):
        """from_ansi preserves colors."""
        text = "\033[38;2;255;0;0m⠿\033[0m"
        canvas = from_ansi(text)
        # Active pixels should have red color
        active = canvas.bitmap > 0.5
        assert canvas.colors[active, 0].mean() > 0.9  # Red channel

    def test_quadrants_format(self):
        """from_ansi parses quadrants with format hint."""
        canvas = from_ansi("██", format="quadrants")
        assert canvas.bitmap.shape == (2, 4)  # 1 row x 2 chars, 2x2 each

    def test_ascii_format(self):
        """from_ansi parses ASCII with format hint."""
        canvas = from_ansi("@@@@", format="ascii")
        assert canvas.bitmap.shape == (2, 4)  # 1 row x 4 chars, 2x1 each
        # Bright chars should have high values
        assert canvas.bitmap.mean() > 0.9

    def test_empty_input_raises(self):
        """from_ansi raises on empty input."""
        with pytest.raises(ValueError, match="Could not detect"):
            from_ansi("")

    def test_undetectable_format_raises(self):
        """from_ansi raises when format cannot be detected."""
        with pytest.raises(ValueError, match="Could not detect"):
            from_ansi("\x00\x01\x02")


class TestANSIAdapter:
    """Tests for ANSIAdapter class."""

    def test_parse_method(self):
        """ANSIAdapter.parse works with explicit override text."""
        adapter = ANSIAdapter("")
        canvas = adapter.parse("⠿⠿⠿")
        assert canvas.bitmap.shape == (4, 6)

    def test_to_canvas_uses_stored_text(self):
        """ANSIAdapter.to_canvas parses the text supplied at construction."""
        adapter = ANSIAdapter("⠿⠿⠿")
        canvas = adapter.to_canvas()
        assert canvas.bitmap.shape == (4, 6)

    def test_forced_format(self):
        """ANSIAdapter respects format hint."""
        adapter = ANSIAdapter("⠿⠿⠿", format="braille")
        canvas = adapter.to_canvas()
        assert canvas.bitmap.shape == (4, 6)

    def test_custom_charset(self):
        """ANSIAdapter uses custom charset for ASCII."""
        adapter = ANSIAdapter("X", format="ascii", charset=" X")
        canvas = adapter.to_canvas()
        assert canvas.bitmap.mean() > 0.9  # X is bright in this charset
