"""Tests for htmlcat extra."""

import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Skip all tests if dependencies not available
pytest.importorskip("rich")
pytest.importorskip("markdownify")
htmlcat_mod = pytest.importorskip("dapple.extras.htmlcat")


class TestHtmlcatOptions:
    """Tests for HtmlcatOptions dataclass."""

    def test_default_options(self):
        from dapple.extras.htmlcat import HtmlcatOptions

        opts = HtmlcatOptions()
        assert opts.renderer == "auto"
        assert opts.width is None
        assert opts.render_images is True
        assert opts.code_theme == "monokai"
        assert opts.hyperlinks is True

    def test_custom_options(self):
        from dapple.extras.htmlcat import HtmlcatOptions

        opts = HtmlcatOptions(
            renderer="braille",
            width=60,
            render_images=False,
            code_theme="dracula",
            hyperlinks=False,
        )
        assert opts.renderer == "braille"
        assert opts.width == 60
        assert opts.render_images is False
        assert opts.code_theme == "dracula"
        assert opts.hyperlinks is False


class TestHtmlcatRender:
    """Tests for htmlcat_render function (string-based HTML rendering)."""

    def test_basic_html(self):
        """Simple HTML renders without error."""
        from dapple.extras.htmlcat import htmlcat_render

        html = "<h1>Hello</h1><p>World</p>"
        buf = StringIO()
        htmlcat_render(html, dest=buf)
        output = buf.getvalue()
        assert "Hello" in output
        assert "World" in output

    def test_html_with_list(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = "<ul><li>One</li><li>Two</li></ul>"
        buf = StringIO()
        htmlcat_render(html, dest=buf)
        assert "One" in buf.getvalue()

    def test_html_table(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = "<table><tr><th>Name</th></tr><tr><td>Alice</td></tr></table>"
        buf = StringIO()
        htmlcat_render(html, dest=buf)
        assert "Alice" in buf.getvalue()

    def test_empty_html(self):
        from dapple.extras.htmlcat import htmlcat_render

        buf = StringIO()
        htmlcat_render("", dest=buf)
        # Should not crash

    def test_no_images_flag(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = '<img src="missing.png"><p>Text</p>'
        buf = StringIO()
        htmlcat_render(html, dest=buf, render_images=False)
        assert "Text" in buf.getvalue()

    def test_html_with_code_block(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = "<pre><code>print('hello')</code></pre>"
        buf = StringIO()
        htmlcat_render(html, dest=buf)
        output = buf.getvalue()
        assert "print" in output

    def test_html_with_links(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = '<a href="https://example.com">Click here</a>'
        buf = StringIO()
        htmlcat_render(html, dest=buf)
        assert "Click" in buf.getvalue()

    def test_html_with_emphasis(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = "<p><strong>Bold</strong> and <em>italic</em></p>"
        buf = StringIO()
        htmlcat_render(html, dest=buf)
        output = buf.getvalue()
        assert "Bold" in output
        assert "italic" in output

    def test_nested_html(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = "<div><h2>Section</h2><p>Paragraph in a div</p></div>"
        buf = StringIO()
        htmlcat_render(html, dest=buf)
        output = buf.getvalue()
        assert "Section" in output
        assert "Paragraph" in output

    def test_custom_width(self):
        from dapple.extras.htmlcat import htmlcat_render

        html = "<h1>Title</h1><p>Some paragraph text here.</p>"
        buf = StringIO()
        htmlcat_render(html, dest=buf, width=40)
        output = buf.getvalue()
        assert "Title" in output

    def test_raw_mode(self):
        """Raw mode outputs the intermediate markdown instead of rendering."""
        from dapple.extras.htmlcat import htmlcat_render

        html = "<h1>Hello</h1><p>World</p>"
        buf = StringIO()
        htmlcat_render(html, dest=buf, raw=True)
        output = buf.getvalue()
        # Raw mode should give us the markdown text, not Rich-formatted output
        assert "Hello" in output
        assert "World" in output


class TestHtmlcatFile:
    """Tests for htmlcat function (file-based HTML rendering)."""

    def test_html_file(self):
        from dapple.extras.htmlcat import htmlcat

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "test.html"
            html_path.write_text("<h1>Hello</h1><p>World</p>")

            output = StringIO()
            htmlcat(html_path, render_images=False, dest=output)

            result = output.getvalue()
            assert "Hello" in result

    def test_nonexistent_file(self, capsys):
        from dapple.extras.htmlcat import htmlcat

        htmlcat("/nonexistent/file.html", render_images=False)
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()

    def test_html_file_with_raw(self):
        from dapple.extras.htmlcat import htmlcat

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "test.html"
            html_path.write_text("<h1>Title</h1><p>Content</p>")

            output = StringIO()
            htmlcat(html_path, render_images=False, raw=True, dest=output)

            result = output.getvalue()
            assert "Title" in result
            assert "Content" in result


class TestHtmlToMarkdown:
    """Tests for the HTML-to-markdown conversion step."""

    def test_convert_simple(self):
        from dapple.extras.htmlcat.htmlcat import html_to_markdown

        md = html_to_markdown("<h1>Hello</h1><p>World</p>")
        assert "Hello" in md
        assert "World" in md

    def test_convert_empty(self):
        from dapple.extras.htmlcat.htmlcat import html_to_markdown

        md = html_to_markdown("")
        assert isinstance(md, str)

    def test_convert_preserves_links(self):
        from dapple.extras.htmlcat.htmlcat import html_to_markdown

        md = html_to_markdown('<a href="https://example.com">Link</a>')
        assert "Link" in md
        assert "example.com" in md

    def test_convert_preserves_images(self):
        from dapple.extras.htmlcat.htmlcat import html_to_markdown

        md = html_to_markdown('<img src="photo.png" alt="A photo">')
        assert "photo.png" in md

    def test_convert_list(self):
        from dapple.extras.htmlcat.htmlcat import html_to_markdown

        md = html_to_markdown("<ul><li>Alpha</li><li>Beta</li></ul>")
        assert "Alpha" in md
        assert "Beta" in md

    def test_strips_script_tags(self):
        from dapple.extras.htmlcat.htmlcat import html_to_markdown

        md = html_to_markdown(
            "<p>Content</p><script>alert('xss')</script>"
        )
        assert "Content" in md
        assert "alert" not in md

    def test_strips_style_tags(self):
        from dapple.extras.htmlcat.htmlcat import html_to_markdown

        md = html_to_markdown(
            "<p>Content</p><style>body { color: red; }</style>"
        )
        assert "Content" in md
        assert "color:" not in md


class TestHtmlcatCLI:
    """Tests for htmlcat CLI."""

    def test_help_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.htmlcat.cli", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "html" in result.stdout.lower()

    def test_file_arg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "test.html"
            html_path.write_text("<h1>Hello</h1><p>World</p>")

            result = subprocess.run(
                [sys.executable, "-m", "dapple.extras.htmlcat.cli",
                 str(html_path), "--no-images"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert "Hello" in result.stdout

    def test_raw_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "test.html"
            html_path.write_text("<h1>Title</h1><p>Body text</p>")

            result = subprocess.run(
                [sys.executable, "-m", "dapple.extras.htmlcat.cli",
                 str(html_path), "--raw"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert "Title" in result.stdout

    def test_nonexistent_file(self):
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.htmlcat.cli",
             "/nonexistent/file.html"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_no_args_shows_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "dapple.extras.htmlcat.cli"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_output_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "test.html"
            html_path.write_text("<h1>Hello</h1>")
            out_path = Path(tmpdir) / "output.txt"

            result = subprocess.run(
                [sys.executable, "-m", "dapple.extras.htmlcat.cli",
                 str(html_path), "--no-images", "-o", str(out_path)],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert out_path.exists()
            content = out_path.read_text()
            assert "Hello" in content

    def test_multiple_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html1 = Path(tmpdir) / "a.html"
            html1.write_text("<h1>First</h1>")
            html2 = Path(tmpdir) / "b.html"
            html2.write_text("<h1>Second</h1>")

            result = subprocess.run(
                [sys.executable, "-m", "dapple.extras.htmlcat.cli",
                 str(html1), str(html2), "--no-images"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert "First" in result.stdout
            assert "Second" in result.stdout
