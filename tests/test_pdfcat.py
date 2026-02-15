"""Tests for pdfcat extra."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Skip all tests if pypdfium2 not available
pytest.importorskip("pypdfium2")
pytest.importorskip("PIL")
pdfcat_mod = pytest.importorskip("dapple.extras.pdfcat")


class TestPageRangeParsing:
    """Tests for page range parsing."""

    def test_single_page(self):
        from dapple.extras.pdfcat.pdfcat import parse_page_range

        assert parse_page_range("1", 10) == [1]
        assert parse_page_range("5", 10) == [5]

    def test_page_range(self):
        from dapple.extras.pdfcat.pdfcat import parse_page_range

        assert parse_page_range("1-3", 10) == [1, 2, 3]
        assert parse_page_range("5-7", 10) == [5, 6, 7]

    def test_multiple_pages(self):
        from dapple.extras.pdfcat.pdfcat import parse_page_range

        assert parse_page_range("1,3,5", 10) == [1, 3, 5]

    def test_mixed_ranges(self):
        from dapple.extras.pdfcat.pdfcat import parse_page_range

        assert parse_page_range("1-3,7,9-10", 10) == [1, 2, 3, 7, 9, 10]

    def test_open_ended_range(self):
        from dapple.extras.pdfcat.pdfcat import parse_page_range

        assert parse_page_range("-3", 10) == [1, 2, 3]
        assert parse_page_range("8-", 10) == [8, 9, 10]

    def test_out_of_bounds_ignored(self):
        from dapple.extras.pdfcat.pdfcat import parse_page_range

        # Page 15 is beyond the 10-page document
        assert parse_page_range("1,15", 10) == [1]


class TestPdfcatOptions:
    """Tests for PdfcatOptions dataclass."""

    def test_default_options(self):
        from dapple.extras.pdfcat import PdfcatOptions

        opts = PdfcatOptions()
        assert opts.renderer == "auto"
        assert opts.width is None
        assert opts.pages is None
        assert opts.dpi == 150
        assert opts.dither is False


class TestGetRenderer:
    """Tests for get_renderer function."""

    def test_auto_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("auto", opts)
        assert hasattr(renderer, "render")

    def test_braille_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("braille", opts)
        assert hasattr(renderer, "render")

    def test_quadrants_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("quadrants", opts)
        assert hasattr(renderer, "render")
        assert renderer.cell_width == 2
        assert renderer.cell_height == 2

    def test_sextants_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("sextants", opts)
        assert hasattr(renderer, "render")
        assert renderer.cell_width == 2
        assert renderer.cell_height == 3

    def test_ascii_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("ascii", opts)
        assert hasattr(renderer, "render")

    def test_sixel_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("sixel", opts)
        assert hasattr(renderer, "render")

    def test_kitty_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("kitty", opts)
        assert hasattr(renderer, "render")

    def test_fingerprint_renderer(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        renderer = get_renderer("fingerprint", opts)
        assert hasattr(renderer, "render")

    def test_unknown_renderer_raises(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions()
        with pytest.raises(ValueError, match="Unknown renderer"):
            get_renderer("unknown", opts)

    def test_braille_no_color(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions(no_color=True)
        renderer = get_renderer("braille", opts)
        assert renderer.color_mode == "none"

    def test_braille_grayscale(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions(grayscale=True)
        renderer = get_renderer("braille", opts)
        assert renderer.color_mode == "grayscale"

    def test_quadrants_grayscale(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions(grayscale=True)
        renderer = get_renderer("quadrants", opts)
        assert renderer.grayscale is True

    def test_sextants_grayscale(self):
        from dapple.extras.pdfcat.pdfcat import get_renderer, PdfcatOptions

        opts = PdfcatOptions(grayscale=True)
        renderer = get_renderer("sextants", opts)
        assert renderer.grayscale is True


class TestRenderPdfToImages:
    """Tests for render_pdf_to_images function."""

    def _make_test_pdf(self, tmpdir: str) -> Path:
        """Create a minimal 1-page PDF for testing."""
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument.new()
        page = pdf.new_page(200, 200)
        pdf_path = Path(tmpdir) / "test.pdf"
        pdf.save(str(pdf_path))
        pdf.close()
        return pdf_path

    def test_renders_single_page(self):
        from dapple.extras.pdfcat.pdfcat import render_pdf_to_images

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            result = render_pdf_to_images(pdf_path)
            assert result.total_pages == 1
            assert len(result.pages) == 1
            assert result.pages[0].number == 1
            assert result.pages[0].image_path.exists()
            result.cleanup()

    def test_page_range_filter(self):
        from dapple.extras.pdfcat.pdfcat import render_pdf_to_images

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            result = render_pdf_to_images(pdf_path, pages="1")
            assert len(result.pages) == 1
            result.cleanup()

    def test_nonexistent_file(self):
        from dapple.extras.pdfcat.pdfcat import render_pdf_to_images

        result = render_pdf_to_images(Path("/nonexistent/file.pdf"))
        assert result.total_pages == 0
        assert len(result.pages) == 0

    def test_custom_dpi(self):
        from dapple.extras.pdfcat.pdfcat import render_pdf_to_images

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            result = render_pdf_to_images(pdf_path, dpi=72)
            assert len(result.pages) == 1
            result.cleanup()

    def test_cleanup(self):
        from dapple.extras.pdfcat.pdfcat import render_pdf_to_images

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            result = render_pdf_to_images(pdf_path)
            temp_dir_path = Path(result.temp_dir.name)
            assert temp_dir_path.exists()
            result.cleanup()
            assert not temp_dir_path.exists()


class TestPdfcatFunction:
    """Tests for pdfcat function."""

    def _make_test_pdf(self, tmpdir: str) -> Path:
        """Create a minimal 1-page PDF for testing."""
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument.new()
        page = pdf.new_page(200, 200)
        pdf_path = Path(tmpdir) / "test.pdf"
        pdf.save(str(pdf_path))
        pdf.close()
        return pdf_path

    def test_basic_render_braille(self):
        from io import StringIO

        from dapple.extras.pdfcat import pdfcat

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            output = StringIO()
            result = pdfcat(pdf_path, renderer="braille", width=40, dest=output)
            assert result is True
            text = output.getvalue()
            assert "test.pdf" in text  # Header includes filename

    def test_file_not_found(self):
        from io import StringIO

        from dapple.extras.pdfcat import pdfcat

        output = StringIO()
        result = pdfcat("/nonexistent/file.pdf", dest=output)
        assert result is False

    def test_preprocessing_dither(self):
        from io import StringIO

        from dapple.extras.pdfcat import pdfcat

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            output = StringIO()
            result = pdfcat(pdf_path, renderer="braille", width=40, dither=True, dest=output)
            assert result is True

    def test_preprocessing_contrast(self):
        from io import StringIO

        from dapple.extras.pdfcat import pdfcat

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            output = StringIO()
            result = pdfcat(pdf_path, renderer="braille", width=40, contrast=True, dest=output)
            assert result is True

    def test_preprocessing_invert(self):
        from io import StringIO

        from dapple.extras.pdfcat import pdfcat

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            output = StringIO()
            result = pdfcat(pdf_path, renderer="braille", width=40, invert=True, dest=output)
            assert result is True

    def test_width_and_height(self):
        from io import StringIO

        from dapple.extras.pdfcat import pdfcat

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            output = StringIO()
            result = pdfcat(pdf_path, renderer="braille", width=60, height=30, dest=output)
            assert result is True

    def test_page_range(self):
        from io import StringIO

        from dapple.extras.pdfcat import pdfcat

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = self._make_test_pdf(tmpdir)
            output = StringIO()
            result = pdfcat(pdf_path, renderer="braille", width=40, pages="1", dest=output)
            assert result is True


class TestPdfcatCLI:
    """Tests for pdfcat CLI."""

    def test_help_output(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "dapple.extras.pdfcat.pdfcat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "pdfcat" in result.stdout.lower() or "pdf" in result.stdout.lower()

    def test_file_not_found_cli(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "dapple.extras.pdfcat.pdfcat", "/nonexistent/file.pdf"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


class TestErrorMessages:
    def test_corrupt_pdf_reports_error(self, tmp_path):
        """Corrupt PDF should produce error message, not silent failure."""
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_text("this is not a PDF")
        from io import StringIO
        from dapple.extras.pdfcat.pdfcat import render_pdf_to_images
        import sys

        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = captured = StringIO()
        try:
            result = render_pdf_to_images(bad_pdf)
        finally:
            sys.stderr = old_stderr

        # Should report the error on stderr (not silently return empty)
        stderr_output = captured.getvalue()
        assert "Failed to open PDF" in stderr_output
