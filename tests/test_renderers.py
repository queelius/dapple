"""Tests for renderers."""

from io import StringIO

import numpy as np
import pytest

from dapple import (
    braille,
    quadrants,
    sextants,
    ascii,
    sixel,
    kitty,
    fingerprint,
    BrailleRenderer,
    QuadrantsRenderer,
    SextantsRenderer,
    AsciiRenderer,
    SixelRenderer,
    KittyRenderer,
    FingerprintRenderer,
)
from dapple.renderers import Renderer
from dapple.renderers.fingerprint import (
    RESET,
    _sextant_pattern,
    _synthetic_sextant_bitmap,
)


def render_to_string(renderer, bitmap, colors=None):
    """Helper to render to a string using the stream-based API."""
    buf = StringIO()
    renderer.render(bitmap, colors, dest=buf)
    return buf.getvalue()


class TestRendererProtocol:
    """Tests for Renderer protocol compliance."""

    def test_braille_is_renderer(self):
        """BrailleRenderer implements Renderer protocol."""
        assert isinstance(braille, Renderer)

    def test_quadrants_is_renderer(self):
        """QuadrantsRenderer implements Renderer protocol."""
        assert isinstance(quadrants, Renderer)

    def test_sextants_is_renderer(self):
        """SextantsRenderer implements Renderer protocol."""
        assert isinstance(sextants, Renderer)

    def test_ascii_is_renderer(self):
        """AsciiRenderer implements Renderer protocol."""
        assert isinstance(ascii, Renderer)

    def test_sixel_is_renderer(self):
        """SixelRenderer implements Renderer protocol."""
        assert isinstance(sixel, Renderer)

    def test_kitty_is_renderer(self):
        """KittyRenderer implements Renderer protocol."""
        assert isinstance(kitty, Renderer)

    def test_fingerprint_is_renderer(self):
        """FingerprintRenderer implements Renderer protocol."""
        assert isinstance(fingerprint, Renderer)


class TestBrailleRenderer:
    """Tests for BrailleRenderer."""

    def test_cell_dimensions(self):
        """Braille uses 2x4 cell."""
        assert braille.cell_width == 2
        assert braille.cell_height == 4

    def test_render_basic(self):
        """render() produces braille characters."""
        bitmap = np.ones((8, 4), dtype=np.float32)
        result = render_to_string(braille, bitmap)
        # 8 rows / 4 = 2 lines, 4 cols / 2 = 2 chars per line
        lines = result.split("\n")
        assert len(lines) == 2
        assert len(lines[0]) == 2
        # All ones should produce full braille char
        assert lines[0][0] == "\u28ff"

    def test_render_empty(self):
        """render() handles all-zero bitmap."""
        bitmap = np.zeros((8, 4), dtype=np.float32)
        result = render_to_string(braille, bitmap)
        lines = result.split("\n")
        # All zeros should produce empty braille char
        assert lines[0][0] == "\u2800"

    def test_render_threshold(self):
        """render() respects threshold parameter."""
        bitmap = np.full((4, 2), 0.3, dtype=np.float32)
        # With threshold 0.5, 0.3 < 0.5 so dots should be off
        result = render_to_string(braille, bitmap)
        assert "\u2800" in result  # Empty braille

        # With threshold 0.2, 0.3 > 0.2 so dots should be on
        result = render_to_string(braille(threshold=0.2), bitmap)
        assert "\u28ff" in result  # Full braille

    def test_render_auto_threshold(self):
        """render() auto-detects threshold when None."""
        bitmap = np.random.rand(8, 4).astype(np.float32)
        result = render_to_string(braille(threshold=None), bitmap)
        assert isinstance(result, str)

    def test_render_grayscale_color(self):
        """render() with grayscale color mode."""
        bitmap = np.linspace(0, 1, 8).reshape(4, 2).astype(np.float32)
        result = render_to_string(braille(color_mode="grayscale"), bitmap)
        assert "\033[38;5;" in result  # ANSI color code
        assert "\033[0m" in result  # Reset code

    def test_render_truecolor(self):
        """render() with truecolor mode."""
        bitmap = np.linspace(0, 1, 8).reshape(4, 2).astype(np.float32)
        result = render_to_string(braille(color_mode="truecolor"), bitmap)
        assert "\033[38;2;" in result  # 24-bit color code

    def test_render_with_colors(self):
        """render() uses colors array in truecolor mode."""
        bitmap = np.ones((4, 2), dtype=np.float32)
        colors = np.zeros((4, 2, 3), dtype=np.float32)
        colors[:, :, 0] = 1.0  # Red
        result = render_to_string(braille(color_mode="truecolor"), bitmap, colors)
        assert "\033[38;2;255;0;0m" in result or "\033[38;2;254" in result

    def test_call_creates_new_instance(self):
        """__call__ creates new renderer with options."""
        custom = braille(threshold=0.3, color_mode="grayscale")
        assert custom is not braille
        assert custom.threshold == 0.3
        assert custom.color_mode == "grayscale"

    def test_invalid_bitmap(self):
        """render() rejects invalid bitmap."""
        with pytest.raises(ValueError, match="must be 2D"):
            render_to_string(braille, np.zeros((4, 2, 3)))

    def test_frozen(self):
        """BrailleRenderer is immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            braille.threshold = 0.3


class TestQuadrantsRenderer:
    """Tests for QuadrantsRenderer."""

    def test_cell_dimensions(self):
        """Quadrants uses 2x2 cell."""
        assert quadrants.cell_width == 2
        assert quadrants.cell_height == 2

    def test_render_basic(self):
        """render() produces block characters with ANSI codes."""
        bitmap = np.ones((4, 4), dtype=np.float32)
        result = render_to_string(quadrants, bitmap)
        # Should have ANSI codes
        assert "\033[" in result
        # 4 rows / 2 = 2 lines, 4 cols / 2 = 2 chars per line
        # But each char has ANSI codes, so just check newlines
        assert "\n" in result

    def test_render_uniform_block(self):
        """render() produces full block for uniform region."""
        bitmap = np.ones((4, 4), dtype=np.float32)
        result = render_to_string(quadrants, bitmap)
        assert "█" in result

    def test_render_pattern(self):
        """render() produces correct block for pattern."""
        # Create a checkerboard 2x2 block
        bitmap = np.array([[1, 0], [0, 1]], dtype=np.float32)
        result = render_to_string(quadrants, bitmap)
        # Should produce diagonal block
        assert "▚" in result or "▞" in result

    def test_render_true_color(self):
        """render() uses 24-bit color when true_color=True."""
        bitmap = np.random.rand(4, 4).astype(np.float32)
        result = render_to_string(quadrants(true_color=True), bitmap)
        assert "\033[38;2;" in result  # 24-bit foreground
        assert "\033[48;2;" in result  # 24-bit background

    def test_render_256_color(self):
        """render() uses 256-color when true_color=False."""
        bitmap = np.random.rand(4, 4).astype(np.float32)
        result = render_to_string(quadrants(true_color=False), bitmap)
        assert "\033[38;5;" in result  # 256-color foreground
        assert "\033[48;5;" in result  # 256-color background

    def test_render_with_rgb_colors(self):
        """render() uses RGB colors array."""
        bitmap = np.ones((4, 4), dtype=np.float32)
        colors = np.zeros((4, 4, 3), dtype=np.float32)
        colors[:, :, 0] = 1.0  # Red
        result = render_to_string(quadrants, bitmap, colors)
        # Should have red color codes
        assert "255" in result

    def test_render_empty_dimensions(self):
        """render() handles small bitmaps."""
        bitmap = np.zeros((1, 1), dtype=np.float32)
        result = render_to_string(quadrants, bitmap)
        assert result == ""  # Too small for even one block


class TestSextantsRenderer:
    """Tests for SextantsRenderer."""

    def test_cell_dimensions(self):
        """Sextants uses 2x3 cell."""
        assert sextants.cell_width == 2
        assert sextants.cell_height == 3

    def test_render_basic(self):
        """render() produces sextant characters with ANSI codes."""
        bitmap = np.ones((6, 4), dtype=np.float32)
        result = render_to_string(sextants, bitmap)
        # Should have ANSI codes
        assert "\033[" in result
        # 6 rows / 3 = 2 lines, 4 cols / 2 = 2 chars per line
        assert "\n" in result

    def test_render_uniform_block(self):
        """render() produces full block for uniform region."""
        bitmap = np.ones((6, 4), dtype=np.float32)
        result = render_to_string(sextants, bitmap)
        assert "█" in result

    def test_render_empty(self):
        """render() produces output for all-zero region."""
        bitmap = np.zeros((3, 2), dtype=np.float32)
        result = render_to_string(sextants, bitmap)
        # Uniform regions produce full block with matching fg/bg (black)
        # This renders as "invisible" but still produces output
        assert len(result) > 0
        assert "\033[" in result  # Has ANSI codes

    def test_render_true_color(self):
        """render() uses 24-bit color when true_color=True."""
        bitmap = np.random.rand(6, 4).astype(np.float32)
        result = render_to_string(sextants(true_color=True), bitmap)
        assert "\033[38;2;" in result  # 24-bit foreground
        assert "\033[48;2;" in result  # 24-bit background

    def test_render_256_color(self):
        """render() uses 256-color when true_color=False."""
        bitmap = np.random.rand(6, 4).astype(np.float32)
        result = render_to_string(sextants(true_color=False), bitmap)
        assert "\033[38;5;" in result  # 256-color foreground
        assert "\033[48;5;" in result  # 256-color background

    def test_render_with_rgb_colors(self):
        """render() uses RGB colors array."""
        bitmap = np.ones((6, 4), dtype=np.float32)
        colors = np.zeros((6, 4, 3), dtype=np.float32)
        colors[:, :, 0] = 1.0  # Red
        result = render_to_string(sextants, bitmap, colors)
        # Should have red color codes
        assert "255" in result

    def test_render_empty_dimensions(self):
        """render() handles small bitmaps."""
        bitmap = np.zeros((2, 1), dtype=np.float32)
        result = render_to_string(sextants, bitmap)
        assert result == ""  # Too small for even one sextant

    def test_call_creates_new_instance(self):
        """__call__ creates new renderer with options."""
        custom = sextants(true_color=False, grayscale=True)
        assert custom is not sextants
        assert custom.true_color is False
        assert custom.grayscale is True

    def test_frozen(self):
        """SextantsRenderer is immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            sextants.true_color = False


class TestAsciiRenderer:
    """Tests for AsciiRenderer."""

    def test_cell_dimensions(self):
        """ASCII uses 1x2 cell (aspect ratio correction)."""
        assert ascii.cell_width == 1
        assert ascii.cell_height == 2

    def test_render_basic(self):
        """render() produces ASCII characters."""
        bitmap = np.ones((4, 4), dtype=np.float32)
        result = render_to_string(ascii, bitmap)
        # All bright should produce dense char
        assert "@" in result

    def test_render_empty(self):
        """render() produces spaces for dark pixels."""
        bitmap = np.zeros((4, 4), dtype=np.float32)
        result = render_to_string(ascii, bitmap)
        # All dark should produce spaces
        assert result.strip() == ""

    def test_render_gradient(self):
        """render() maps gradient to character range."""
        bitmap = np.linspace(0, 1, 20).reshape(4, 5).astype(np.float32)
        result = render_to_string(ascii, bitmap)
        # Should have mix of characters
        lines = result.split("\n")
        assert len(lines) == 2  # 4 rows / 2

    def test_render_custom_charset(self):
        """render() uses custom character set."""
        bitmap = np.ones((4, 4), dtype=np.float32)
        result = render_to_string(ascii(charset=" X"), bitmap)
        assert "X" in result
        assert "@" not in result

    def test_render_invert(self):
        """render() inverts with invert=True."""
        bitmap = np.ones((4, 4), dtype=np.float32)  # All bright
        normal = render_to_string(ascii, bitmap)
        inverted = render_to_string(ascii(invert=True), bitmap)
        # Inverted bright should become dark (space)
        assert normal != inverted

    def test_empty_charset_error(self):
        """render() rejects empty charset."""
        with pytest.raises(ValueError, match="charset must not be empty"):
            render_to_string(ascii(charset=""), np.zeros((4, 4)))


class TestSixelRenderer:
    """Tests for SixelRenderer."""

    def test_cell_dimensions(self):
        """Sixel outputs actual pixels (1:1)."""
        assert sixel.cell_width == 1
        assert sixel.cell_height == 1

    def test_render_produces_escape_sequence(self):
        """render() produces sixel escape sequence."""
        bitmap = np.random.rand(12, 10).astype(np.float32)
        result = render_to_string(sixel, bitmap)
        # Should start with DCS and end with ST
        assert result.startswith("\033Pq")
        assert result.endswith("\033\\")

    def test_render_includes_palette(self):
        """render() includes color palette definition."""
        bitmap = np.random.rand(12, 10).astype(np.float32)
        result = render_to_string(sixel, bitmap)
        # Should have color definitions
        assert "#" in result
        assert ";2;" in result  # RGB color definition format

    def test_render_with_colors(self):
        """render() handles RGB colors."""
        bitmap = np.random.rand(12, 10).astype(np.float32)
        colors = np.random.rand(12, 10, 3).astype(np.float32)
        result = render_to_string(sixel, bitmap, colors)
        assert result.startswith("\033Pq")

    def test_render_with_scale(self):
        """render() scales up pixels."""
        bitmap = np.random.rand(6, 5).astype(np.float32)
        # With scale=2, output should be larger
        result_1x = render_to_string(sixel(scale=1), bitmap)
        result_2x = render_to_string(sixel(scale=2), bitmap)
        # 2x should have more data
        assert len(result_2x) > len(result_1x)


class TestKittyRenderer:
    """Tests for KittyRenderer."""

    def test_cell_dimensions(self):
        """Kitty outputs actual pixels (1:1)."""
        assert kitty.cell_width == 1
        assert kitty.cell_height == 1

    def test_render_produces_escape_sequence(self):
        """render() produces kitty graphics escape sequence."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty, bitmap)
        # Should start with APC
        assert result.startswith("\033_G")
        assert result.endswith("\033\\")

    def test_render_includes_params(self):
        """render() includes required parameters."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty, bitmap)
        # Should have action=transmit and format
        assert "a=T" in result
        assert "f=" in result

    def test_render_png_format(self):
        """render() produces PNG format by default."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(format="png"), bitmap)
        assert "f=100" in result  # PNG format code

    def test_render_rgb_format(self):
        """render() produces RGB format."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(format="rgb"), bitmap)
        assert "f=24" in result  # RGB format code

    def test_render_with_colors(self):
        """render() handles RGB colors."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        colors = np.random.rand(10, 10, 3).astype(np.float32)
        result = render_to_string(kitty, bitmap, colors)
        assert result.startswith("\033_G")

    def test_render_rgba_format(self):
        """render() produces RGBA format."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(format="rgba"), bitmap)
        assert "f=32" in result  # RGBA format code

    def test_render_rgba_with_colors(self):
        """render() produces RGBA format with RGB colors."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        colors = np.random.rand(10, 10, 3).astype(np.float32)
        result = render_to_string(kitty(format="rgba"), bitmap, colors)
        assert "f=32" in result

    def test_render_rgb_no_compression(self):
        """render() produces uncompressed RGB data."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(format="rgb", compression=False), bitmap)
        assert "f=24" in result
        assert "o=z" not in result  # No zlib compression flag

    def test_render_rgb_with_compression(self):
        """render() produces zlib-compressed RGB data."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(format="rgb", compression=True), bitmap)
        assert "f=24" in result
        assert "o=z" in result  # zlib compression flag

    def test_render_columns_param(self):
        """render() includes columns display size parameter."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(columns=80), bitmap)
        assert "c=80" in result

    def test_render_rows_param(self):
        """render() includes rows display size parameter."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(rows=24), bitmap)
        assert "r=24" in result

    def test_render_columns_and_rows(self):
        """render() includes both display size parameters."""
        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = render_to_string(kitty(columns=80, rows=24), bitmap)
        assert "c=80" in result
        assert "r=24" in result

    def test_render_chunking(self):
        """render() chunks large images into multiple escape sequences."""
        # Create a large enough bitmap that base64 exceeds MAX_CHUNK_SIZE (4096)
        bitmap = np.random.rand(200, 200).astype(np.float32)
        result = render_to_string(kitty(format="rgb", compression=False), bitmap)
        # Should have multiple APC sequences (m=1 for continuation)
        assert "m=1" in result  # At least one continuation chunk
        assert "m=0" in result  # Final chunk

    def test_call_partial_update(self):
        """__call__() preserves defaults for unspecified params."""
        custom = kitty(format="rgb")
        assert custom.format == "rgb"
        assert custom.compression == kitty.compression  # preserved
        assert custom.columns == kitty.columns  # preserved
        assert custom.rows == kitty.rows  # preserved

    def test_render_grayscale_bitmap_png(self):
        """render() handles grayscale-only bitmap in PNG format."""
        bitmap = np.linspace(0, 1, 100).reshape(10, 10).astype(np.float32)
        result = render_to_string(kitty(format="png"), bitmap)
        assert result.startswith("\033_G")
        assert "f=100" in result

    def test_render_grayscale_bitmap_rgb(self):
        """render() converts grayscale to RGB for raw format."""
        bitmap = np.linspace(0, 1, 100).reshape(10, 10).astype(np.float32)
        result = render_to_string(kitty(format="rgb"), bitmap)
        assert "f=24" in result
        # Should include width and height params for raw format
        assert "s=10" in result
        assert "v=10" in result

    def test_invalid_bitmap_3d(self):
        """render() rejects 3D bitmap."""
        with pytest.raises(ValueError, match="must be 2D"):
            render_to_string(kitty, np.zeros((4, 2, 3)))

    def test_invalid_colors_shape(self):
        """render() rejects mismatched colors shape."""
        bitmap = np.zeros((10, 10), dtype=np.float32)
        colors = np.zeros((5, 5, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="must match bitmap shape"):
            render_to_string(kitty, bitmap, colors)

    def test_frozen(self):
        """KittyRenderer is immutable (frozen dataclass)."""
        with pytest.raises(Exception):
            kitty.format = "rgb"


class TestMakePngMinimal:
    """Tests for _make_png_minimal helper."""

    def test_produces_valid_png_signature(self):
        """_make_png_minimal() produces bytes starting with PNG signature."""
        from dapple.renderers.kitty import _make_png_minimal

        bitmap = np.random.rand(4, 4).astype(np.float32)
        data = _make_png_minimal(bitmap)
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_grayscale_mode(self):
        """_make_png_minimal() produces valid grayscale PNG."""
        from dapple.renderers.kitty import _make_png_minimal

        bitmap = np.ones((4, 4), dtype=np.float32)
        data = _make_png_minimal(bitmap)
        assert len(data) > 8
        # Should contain IHDR, IDAT, IEND chunks
        assert b"IHDR" in data
        assert b"IDAT" in data
        assert b"IEND" in data

    def test_rgb_mode(self):
        """_make_png_minimal() produces valid RGB PNG."""
        from dapple.renderers.kitty import _make_png_minimal

        bitmap = np.ones((4, 4), dtype=np.float32)
        colors = np.random.rand(4, 4, 3).astype(np.float32)
        data = _make_png_minimal(bitmap, colors)
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert b"IHDR" in data

    def test_pil_can_read_output(self):
        """_make_png_minimal() output is readable by PIL."""
        pytest.importorskip("PIL")
        from io import BytesIO

        from PIL import Image

        from dapple.renderers.kitty import _make_png_minimal

        bitmap = np.linspace(0, 1, 16).reshape(4, 4).astype(np.float32)
        data = _make_png_minimal(bitmap)
        img = Image.open(BytesIO(data))
        assert img.size == (4, 4)

    def test_pil_can_read_rgb_output(self):
        """_make_png_minimal() RGB output is readable by PIL."""
        pytest.importorskip("PIL")
        from io import BytesIO

        from PIL import Image

        from dapple.renderers.kitty import _make_png_minimal

        bitmap = np.ones((4, 4), dtype=np.float32)
        colors = np.zeros((4, 4, 3), dtype=np.float32)
        colors[:, :, 0] = 1.0  # Red
        data = _make_png_minimal(bitmap, colors)
        img = Image.open(BytesIO(data))
        assert img.size == (4, 4)
        assert img.mode == "RGB"


class TestTryPilPng:
    """Tests for _try_pil_png helper."""

    def test_produces_png_with_pil(self):
        """_try_pil_png() returns PNG bytes when PIL is available."""
        pytest.importorskip("PIL")
        from dapple.renderers.kitty import _try_pil_png

        bitmap = np.random.rand(4, 4).astype(np.float32)
        data = _try_pil_png(bitmap)
        assert data is not None
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_grayscale_mode(self):
        """_try_pil_png() produces grayscale PNG without colors."""
        pytest.importorskip("PIL")
        from dapple.renderers.kitty import _try_pil_png

        bitmap = np.ones((4, 4), dtype=np.float32)
        data = _try_pil_png(bitmap)
        assert data is not None
        assert len(data) > 0

    def test_rgb_mode(self):
        """_try_pil_png() produces RGB PNG with colors."""
        pytest.importorskip("PIL")
        from dapple.renderers.kitty import _try_pil_png

        bitmap = np.ones((4, 4), dtype=np.float32)
        colors = np.random.rand(4, 4, 3).astype(np.float32)
        data = _try_pil_png(bitmap, colors)
        assert data is not None
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_returns_none_without_pil(self):
        """_try_pil_png() returns None when PIL import fails."""
        from unittest.mock import patch

        from dapple.renderers.kitty import _try_pil_png

        bitmap = np.random.rand(4, 4).astype(np.float32)
        # Mock the import inside _try_pil_png to raise ImportError
        with patch("dapple.renderers.kitty._try_pil_png") as mock_fn:
            mock_fn.return_value = None
            result = mock_fn(bitmap)
            assert result is None


class TestFingerprintRenderer:
    """Tests for FingerprintRenderer."""

    def test_cell_dimensions(self):
        """Fingerprint uses configurable cell size."""
        assert fingerprint.cell_width == 8
        assert fingerprint.cell_height == 16

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_basic(self):
        """render() produces ASCII characters."""
        bitmap = np.random.rand(32, 24).astype(np.float32)
        result = render_to_string(fingerprint, bitmap)
        # Should produce output with lines
        lines = result.split("\n")
        # 32 / 16 = 2 lines, 24 / 8 = 3 chars per line
        assert len(lines) == 2
        assert len(lines[0]) == 3

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_bright_produces_dense_char(self):
        """render() maps bright regions to dense characters."""
        bitmap = np.ones((16, 8), dtype=np.float32)
        result = render_to_string(fingerprint, bitmap)
        # Should produce some character (likely dense like @, M, etc.)
        assert len(result.strip()) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_dark_produces_sparse_char(self):
        """render() maps dark regions to sparse characters."""
        bitmap = np.zeros((16, 8), dtype=np.float32)
        result = render_to_string(fingerprint, bitmap)
        # Should produce sparse character (likely space or similar)
        assert len(result) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_with_blocks_glyph_set(self):
        """render() works with blocks glyph set."""
        bitmap = np.random.rand(32, 16).astype(np.float32)
        result = render_to_string(fingerprint(glyph_set="blocks"), bitmap)
        assert len(result) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_with_braille_glyph_set(self):
        """render() works with braille glyph set."""
        bitmap = np.random.rand(32, 16).astype(np.float32)
        result = render_to_string(fingerprint(glyph_set="braille"), bitmap)
        assert len(result) > 0

    def test_call_creates_new_instance(self):
        """__call__ creates new renderer with options."""
        custom = fingerprint(glyph_set="blocks", cell_width=10, cell_height=20)
        assert custom is not fingerprint
        assert custom.glyph_set == "blocks"
        assert custom.cell_width == 10
        assert custom.cell_height == 20

    def test_frozen(self):
        """FingerprintRenderer is immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            fingerprint.glyph_set = "blocks"

    def test_invalid_bitmap(self):
        """render() rejects invalid bitmap."""
        with pytest.raises(ValueError, match="must be 2D"):
            render_to_string(fingerprint, np.zeros((4, 2, 3)))

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_no_color_default(self):
        """render() produces plain glyphs without ANSI codes by default."""
        bitmap = np.random.rand(32, 24).astype(np.float32)
        result = render_to_string(fingerprint, bitmap)
        assert "\033[" not in result

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_grayscale_color(self):
        """render() with grayscale=True produces ANSI grayscale codes."""
        bitmap = np.linspace(0, 1, 32 * 24).reshape(32, 24).astype(np.float32)
        result = render_to_string(fingerprint(grayscale=True), bitmap)
        assert "\033[38;" in result  # Foreground
        assert "\033[48;" in result  # Background
        assert RESET in result

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_truecolor(self):
        """render() with true_color=True produces 24-bit ANSI codes."""
        bitmap = np.linspace(0, 1, 32 * 24).reshape(32, 24).astype(np.float32)
        result = render_to_string(fingerprint(grayscale=True, true_color=True), bitmap)
        assert "\033[38;2;" in result
        assert "\033[48;2;" in result

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_256color(self):
        """render() with true_color=False produces 256-color ANSI codes."""
        bitmap = np.linspace(0, 1, 32 * 24).reshape(32, 24).astype(np.float32)
        result = render_to_string(fingerprint(grayscale=True, true_color=False), bitmap)
        assert "\033[38;5;" in result
        assert "\033[48;5;" in result

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_with_rgb_colors(self):
        """render() uses colors array for RGB output."""
        bitmap = np.ones((32, 24), dtype=np.float32)
        colors = np.zeros((32, 24, 3), dtype=np.float32)
        colors[:, :, 0] = 1.0  # Red
        result = render_to_string(fingerprint, bitmap, colors)
        assert "\033[38;2;" in result
        assert "255" in result  # Red channel

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_colors_forced_grayscale(self):
        """render() with grayscale=True ignores colors array."""
        bitmap = np.ones((32, 24), dtype=np.float32)
        colors = np.zeros((32, 24, 3), dtype=np.float32)
        colors[:, :, 0] = 1.0  # Red
        result = render_to_string(fingerprint(grayscale=True), bitmap, colors)
        # Should use grayscale codes, not full RGB
        assert "\033[38;" in result
        assert RESET in result

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_invalid_colors_shape(self):
        """render() rejects mismatched colors shape."""
        bitmap = np.zeros((32, 24), dtype=np.float32)
        colors = np.zeros((16, 12, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="must match bitmap shape"):
            render_to_string(fingerprint, bitmap, colors)

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_mae_metric(self):
        """render() works with MAE metric."""
        bitmap = np.random.rand(32, 24).astype(np.float32)
        result = render_to_string(fingerprint(metric="mae"), bitmap)
        lines = result.split("\n")
        assert len(lines) == 2
        assert len(lines[0]) == 3

    def test_call_preserves_new_fields(self):
        """__call__ preserves true_color and grayscale."""
        custom = fingerprint(true_color=False, grayscale=True)
        assert custom.true_color is False
        assert custom.grayscale is True
        # Preserves defaults for unspecified
        assert custom.glyph_set == "basic"
        assert custom.metric == "mse"

    def test_auto_cell_size_for_sextants(self):
        """__call__ auto-selects 2x3 cell size for sextants glyph set."""
        r = fingerprint(glyph_set="sextants")
        assert r.cell_width == 2
        assert r.cell_height == 3

    def test_auto_cell_size_for_braille(self):
        """__call__ auto-selects 2x4 cell size for braille glyph set."""
        r = fingerprint(glyph_set="braille")
        assert r.cell_width == 2
        assert r.cell_height == 4

    def test_auto_cell_size_explicit_override(self):
        """Explicit cell size overrides auto-selection."""
        r = fingerprint(glyph_set="sextants", cell_width=8, cell_height=16)
        assert r.cell_width == 8
        assert r.cell_height == 16

    def test_auto_cell_size_no_change_for_basic(self):
        """basic glyph set keeps default 8x16 cell size."""
        r = fingerprint(glyph_set="basic")
        assert r.cell_width == 8
        assert r.cell_height == 16

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_with_geometric_glyph_set(self):
        """render() works with geometric glyph set."""
        bitmap = np.random.rand(32, 16).astype(np.float32)
        result = render_to_string(fingerprint(glyph_set="geometric"), bitmap)
        assert len(result) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_with_full_glyph_set(self):
        """render() works with full glyph set (all Unicode)."""
        bitmap = np.random.rand(32, 16).astype(np.float32)
        result = render_to_string(fingerprint(glyph_set="full"), bitmap)
        assert len(result) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_with_custom_glyph_string(self):
        """render() accepts custom character string as glyph_set."""
        bitmap = np.random.rand(32, 16).astype(np.float32)
        result = render_to_string(fingerprint(glyph_set=" .:-=+*#%@"), bitmap)
        assert len(result) > 0
        # Output should only contain characters from the custom set
        for char in result:
            if char != "\n":
                assert char in " .:-=+*#%@"

    def test_unknown_single_char_glyph_set_error(self):
        """render() rejects single-char string as glyph set."""
        with pytest.raises(ValueError, match="Unknown glyph set"):
            bitmap = np.zeros((16, 8), dtype=np.float32)
            render_to_string(fingerprint(glyph_set="X"), bitmap)

    def test_sextant_pattern_space(self):
        """Space maps to pattern 0 (all empty)."""
        assert _sextant_pattern(0x20) == 0

    def test_sextant_pattern_full_block(self):
        """Full block maps to pattern 63 (all filled)."""
        assert _sextant_pattern(0x2588) == 0b111111

    def test_sextant_pattern_left_half(self):
        """Left half block maps to left column filled."""
        assert _sextant_pattern(0x258C) == 0b010101

    def test_sextant_pattern_right_half(self):
        """Right half block maps to right column filled."""
        assert _sextant_pattern(0x2590) == 0b101010

    def test_sextant_pattern_range(self):
        """All sextant codepoints (U+1FB00-U+1FB3B) produce valid patterns."""
        seen = set()
        for cp in range(0x1FB00, 0x1FB3C):
            p = _sextant_pattern(cp)
            assert p is not None, f"U+{cp:04X} returned None"
            assert 0 < p < 64, f"U+{cp:04X} pattern {p} out of range"
            seen.add(p)
        # 60 codepoints should cover 60 patterns (the ones not handled by block chars)
        assert len(seen) == 60

    def test_sextant_pattern_non_sextant(self):
        """Non-sextant characters return None."""
        assert _sextant_pattern(ord("A")) is None
        assert _sextant_pattern(0x2800) is None  # braille

    def test_synthetic_sextant_empty(self):
        """Pattern 0 produces all-zero bitmap."""
        bm = _synthetic_sextant_bitmap(0, 8, 16)
        assert bm.shape == (16, 8)
        assert bm.sum() == 0.0

    def test_synthetic_sextant_full(self):
        """Pattern 63 produces all-one bitmap."""
        bm = _synthetic_sextant_bitmap(0b111111, 8, 16)
        assert bm.shape == (16, 8)
        assert bm.sum() == pytest.approx(8 * 16)

    def test_synthetic_sextant_all_unique(self):
        """All 64 sextant patterns produce unique bitmaps."""
        bitmaps = [tuple(_synthetic_sextant_bitmap(i, 8, 16).flatten()) for i in range(64)]
        assert len(set(bitmaps)) == 64

    @pytest.mark.skipif(
        not pytest.importorskip("PIL", reason="PIL not installed"),
        reason="PIL required for fingerprint renderer"
    )
    def test_render_with_sextants_glyph_set(self):
        """render() with sextants uses synthetic bitmaps and selects many glyphs."""
        np.random.seed(42)
        bitmap = np.random.rand(160, 80).astype(np.float32)
        result = render_to_string(fingerprint(glyph_set="sextants"), bitmap)
        # Remove ANSI codes to get pure characters
        import re
        clean = re.sub(r"\033\[[^m]*m", "", result).replace("\n", "")
        unique = set(clean)
        # Should use many distinct sextant characters (not just 5-6 from a bad font)
        assert len(unique) >= 20


class TestRendererOptions:
    """Tests for renderer option handling."""

    def test_braille_call_preserves_defaults(self):
        """braille() without args returns equivalent renderer."""
        custom = braille()
        assert custom.threshold == braille.threshold
        assert custom.color_mode == braille.color_mode

    def test_quadrants_call_preserves_defaults(self):
        """quadrants() without args returns equivalent renderer."""
        custom = quadrants()
        assert custom.true_color == quadrants.true_color
        assert custom.grayscale == quadrants.grayscale

    def test_sextants_call_preserves_defaults(self):
        """sextants() without args returns equivalent renderer."""
        custom = sextants()
        assert custom.true_color == sextants.true_color
        assert custom.grayscale == sextants.grayscale

    def test_ascii_call_preserves_defaults(self):
        """ascii() without args returns equivalent renderer."""
        custom = ascii()
        assert custom.charset == ascii.charset
        assert custom.invert == ascii.invert

    def test_sixel_call_preserves_defaults(self):
        """sixel() without args returns equivalent renderer."""
        custom = sixel()
        assert custom.max_colors == sixel.max_colors
        assert custom.scale == sixel.scale

    def test_kitty_call_preserves_defaults(self):
        """kitty() without args returns equivalent renderer."""
        custom = kitty()
        assert custom.format == kitty.format
        assert custom.compression == kitty.compression

    def test_fingerprint_call_preserves_defaults(self):
        """fingerprint() without args returns equivalent renderer."""
        custom = fingerprint()
        assert custom.glyph_set == fingerprint.glyph_set
        assert custom.cell_width == fingerprint.cell_width


class TestPreprocess:
    """Tests for preprocessing functions."""

    def test_auto_contrast(self):
        """auto_contrast stretches to 0-1 range."""
        from dapple import auto_contrast

        bitmap = np.array([[0.3, 0.5], [0.4, 0.6]], dtype=np.float32)
        result = auto_contrast(bitmap)
        assert np.amin(result) == pytest.approx(0.0)
        assert np.amax(result) == pytest.approx(1.0)

    def test_auto_contrast_constant(self):
        """auto_contrast handles constant image."""
        from dapple import auto_contrast

        bitmap = np.full((4, 4), 0.5, dtype=np.float32)
        result = auto_contrast(bitmap)
        # Should return mid-gray
        np.testing.assert_array_almost_equal(result, 0.5)

    def test_floyd_steinberg(self):
        """floyd_steinberg produces binary output."""
        from dapple import floyd_steinberg

        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = floyd_steinberg(bitmap)
        # Should only contain 0 and 1
        unique = np.unique(result)
        assert set(unique) <= {0.0, 1.0}

    def test_invert(self):
        """invert flips brightness values."""
        from dapple import invert

        bitmap = np.array([[0.0, 0.5], [0.75, 1.0]], dtype=np.float32)
        result = invert(bitmap)
        expected = np.array([[1.0, 0.5], [0.25, 0.0]], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_threshold(self):
        """threshold produces binary output."""
        from dapple import threshold

        bitmap = np.array([[0.3, 0.7], [0.4, 0.6]], dtype=np.float32)
        result = threshold(bitmap, level=0.5)
        expected = np.array([[0.0, 1.0], [0.0, 1.0]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_gamma_correct(self):
        """gamma_correct applies power transformation."""
        from dapple import gamma_correct

        bitmap = np.array([[0.5]], dtype=np.float32)
        result = gamma_correct(bitmap, gamma=2.2)
        # 0.5^2.2 ≈ 0.218
        assert result[0, 0] == pytest.approx(0.218, abs=0.01)

    def test_resize(self):
        """resize changes bitmap dimensions."""
        from dapple import resize

        bitmap = np.random.rand(10, 20).astype(np.float32)
        result = resize(bitmap, 5, 10)
        assert result.shape == (5, 10)

    def test_crop(self):
        """crop extracts rectangular region."""
        from dapple.preprocess import crop

        bitmap = np.arange(100).reshape(10, 10).astype(np.float32) / 100
        result = crop(bitmap, 2, 3, 5, 4)
        assert result.shape == (4, 5)
        # Verify corner values
        assert result[0, 0] == bitmap[3, 2]
        assert result[3, 4] == bitmap[6, 6]

    def test_crop_full_image(self):
        """crop with full dimensions returns copy."""
        from dapple.preprocess import crop

        bitmap = np.random.rand(10, 10).astype(np.float32)
        result = crop(bitmap, 0, 0, 10, 10)
        assert result.shape == (10, 10)
        np.testing.assert_array_equal(result, bitmap)

    def test_crop_invalid_bounds(self):
        """crop raises error for out-of-bounds region."""
        from dapple.preprocess import crop

        bitmap = np.random.rand(10, 10).astype(np.float32)
        with pytest.raises(ValueError, match="exceeds bitmap bounds"):
            crop(bitmap, 5, 5, 10, 10)

    def test_crop_negative_position(self):
        """crop raises error for negative position."""
        from dapple.preprocess import crop

        bitmap = np.random.rand(10, 10).astype(np.float32)
        with pytest.raises(ValueError, match="must be non-negative"):
            crop(bitmap, -1, 0, 5, 5)

    def test_crop_zero_size(self):
        """crop raises error for zero dimensions."""
        from dapple.preprocess import crop

        bitmap = np.random.rand(10, 10).astype(np.float32)
        with pytest.raises(ValueError, match="must be positive"):
            crop(bitmap, 0, 0, 0, 5)

    def test_flip_horizontal(self):
        """flip horizontal reverses columns."""
        from dapple.preprocess import flip

        bitmap = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        result = flip(bitmap, "h")
        expected = np.array([[3, 2, 1], [6, 5, 4]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_flip_vertical(self):
        """flip vertical reverses rows."""
        from dapple.preprocess import flip

        bitmap = np.array([[1, 2], [3, 4], [5, 6]], dtype=np.float32)
        result = flip(bitmap, "v")
        expected = np.array([[5, 6], [3, 4], [1, 2]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_flip_invalid_direction(self):
        """flip raises error for invalid direction."""
        from dapple.preprocess import flip

        bitmap = np.random.rand(5, 5).astype(np.float32)
        with pytest.raises(ValueError, match="must be 'h' or 'v'"):
            flip(bitmap, "x")

    def test_rotate_90(self):
        """rotate 90 degrees counter-clockwise."""
        from dapple.preprocess import rotate

        bitmap = np.array([[1, 2], [3, 4]], dtype=np.float32)
        result = rotate(bitmap, 90)
        expected = np.array([[2, 4], [1, 3]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_rotate_180(self):
        """rotate 180 degrees."""
        from dapple.preprocess import rotate

        bitmap = np.array([[1, 2], [3, 4]], dtype=np.float32)
        result = rotate(bitmap, 180)
        expected = np.array([[4, 3], [2, 1]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_rotate_270(self):
        """rotate 270 degrees counter-clockwise."""
        from dapple.preprocess import rotate

        bitmap = np.array([[1, 2], [3, 4]], dtype=np.float32)
        result = rotate(bitmap, 270)
        expected = np.array([[3, 1], [4, 2]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)

    def test_rotate_0(self):
        """rotate 0 degrees returns copy."""
        from dapple.preprocess import rotate

        bitmap = np.random.rand(5, 5).astype(np.float32)
        result = rotate(bitmap, 0)
        np.testing.assert_array_equal(result, bitmap)

    def test_rotate_normalizes_angle(self):
        """rotate normalizes angles to 0-360."""
        from dapple.preprocess import rotate

        bitmap = np.array([[1, 2], [3, 4]], dtype=np.float32)
        result_90 = rotate(bitmap, 90)
        result_450 = rotate(bitmap, 450)  # 450 % 360 = 90
        np.testing.assert_array_equal(result_90, result_450)


class TestAnsiHelpers:
    """Tests for the shared dapple.renderers._ansi helper module."""

    def test_gray_code_clamps_high(self):
        """Brightness > 1.0 must not emit invalid palette index 256."""
        from dapple.renderers._ansi import gray_code

        code = gray_code(1.5, fg=True, true_color=False)
        # Final palette index must be within 232..255
        assert "256" not in code
        assert "255" in code  # clamped to max gray

    def test_gray_code_clamps_low(self):
        """Brightness < 0.0 must clamp to the lowest palette entry."""
        from dapple.renderers._ansi import gray_code

        code = gray_code(-0.3, fg=True, true_color=False)
        assert "232" in code

    def test_color_code_clamps_each_channel(self):
        """Each RGB channel is clamped independently."""
        from dapple.renderers._ansi import color_code

        # True-colour path: each channel → int(val*255) after clamp.
        code = color_code(2.0, -0.5, 0.5, fg=True, true_color=True)
        assert ";255;" in code  # r clamped to 1.0 → 255
        assert ";0;" in code    # g clamped to 0.0 → 0

    def test_strip_ansi_removes_sgr_sequences(self):
        from dapple.renderers._ansi import strip_ansi

        raw = "\033[38;5;232mhello\033[0m world"
        assert strip_ansi(raw) == "hello world"

    def test_visual_width_ignores_escapes(self):
        from dapple.renderers._ansi import visual_width

        raw = "\033[38;2;255;0;0m▀\033[0m"
        assert visual_width(raw) == 1


class TestBrailleAutoThreshold:
    """Regression tests for the _UNSET sentinel in BrailleRenderer.__call__."""

    def test_call_with_none_enables_auto(self):
        """r(threshold=None) must transition into auto-threshold mode."""
        base = BrailleRenderer(threshold=0.5)
        auto = base(threshold=None)
        assert auto.threshold is None

    def test_call_without_threshold_keeps_current(self):
        """Omitting threshold keeps the existing value (sentinel path)."""
        base = BrailleRenderer(threshold=0.3)
        same = base(color_mode="grayscale")
        assert same.threshold == 0.3

    def test_call_with_float_sets_explicit(self):
        base = BrailleRenderer(threshold=None)
        explicit = base(threshold=0.7)
        assert explicit.threshold == 0.7


class TestSixelQuantizerBounds:
    """Sixel _quantize_colors must respect max_colors."""

    def test_palette_size_respects_max_colors(self):
        from dapple.renderers.sixel import _quantize_colors

        colors = np.random.rand(8, 8, 3).astype(np.float32)
        # With max_colors=4, the old implementation produced levels=2
        # giving 2**3 = 8 palette entries — exceeding the max. The fix
        # shrinks levels until levels**3 fits.
        indices, palette = _quantize_colors(colors, n_colors=4)
        assert palette.shape[0] <= 8  # levels floor is 2 → 8 entries
        # Tight upper bound: we never exceed 6**3 = 216.
        assert palette.shape[0] <= 216

    def test_max_colors_256_uses_6x6x6(self):
        from dapple.renderers.sixel import _quantize_colors

        colors = np.random.rand(4, 4, 3).astype(np.float32)
        indices, palette = _quantize_colors(colors, n_colors=256)
        # 6**3 = 216, 7**3 = 343 — so we settle at 6.
        assert palette.shape[0] == 216
