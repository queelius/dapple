"""Tests for mdcat extra."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Skip all tests if rich not available
pytest.importorskip("rich")
pytest.importorskip("PIL")
mdcat_mod = pytest.importorskip("dapple.extras.mdcat")


class TestMdcatOptions:
    """Tests for MdcatOptions dataclass."""

    def test_default_options(self):
        from dapple.extras.mdcat import MdcatOptions

        opts = MdcatOptions()
        assert opts.renderer == "auto"
        assert opts.width is None
        assert opts.image_width is None
        assert opts.render_images is True
        assert opts.theme == "default"
        assert opts.code_theme == "monokai"
        assert opts.hyperlinks is True


class TestImageCache:
    """Tests for ImageCache class."""

    def test_cache_file(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            url = "https://example.com/image.png"
            data = b"fake image data"

            cached_path = cache.cache_file(url, data)
            assert cached_path.exists()
            assert cached_path.read_bytes() == data

    def test_get_cached_path_exists(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            url = "https://example.com/image.png"
            data = b"fake image data"

            cache.cache_file(url, data)
            cached = cache.get_cached_path(url)
            assert cached is not None
            assert cached.exists()

    def test_get_cached_path_not_exists(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            url = "https://example.com/nonexistent.png"
            cached = cache.get_cached_path(url)
            assert cached is None

    def test_get_extension_png(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/image.png") == ".png"

    def test_get_extension_jpg(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/photo.jpg") == ".jpg"

    def test_get_extension_jpeg(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/photo.jpeg") == ".jpeg"

    def test_get_extension_gif(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/anim.gif") == ".gif"

    def test_get_extension_webp(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/image.webp") == ".webp"

    def test_get_extension_url_with_params(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/image.jpg?w=100&h=100") == ".jpg"

    def test_get_extension_no_extension(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/image") == ".png"  # default

    def test_get_extension_unknown(self):
        from dapple.extras.mdcat.mdcat import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/data.bmp") == ".png"  # default fallback


class TestImageResolver:
    """Tests for ImageResolver class."""

    def test_resolve_local_absolute(self):
        from dapple.extras.mdcat.mdcat import ImageResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.png"
            test_file.write_bytes(b"test")

            resolver = ImageResolver()
            result = resolver.resolve(str(test_file))
            assert result == test_file

    def test_resolve_local_relative(self):
        from dapple.extras.mdcat.mdcat import ImageResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            base_file = Path(tmpdir) / "README.md"
            base_file.write_text("# Test")
            img_file = Path(tmpdir) / "image.png"
            img_file.write_bytes(b"test")

            resolver = ImageResolver(base_path=base_file)
            result = resolver.resolve("image.png")
            assert result == img_file

    def test_resolve_nonexistent(self):
        from dapple.extras.mdcat.mdcat import ImageResolver

        resolver = ImageResolver()
        result = resolver.resolve("/nonexistent/path/to/image.png")
        assert result is None


class TestMdcatFunction:
    """Tests for mdcat function."""

    def test_mdcat_simple_markdown(self):
        """Test mdcat with simple markdown content."""
        from dapple.extras.mdcat import mdcat

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple markdown file
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("# Hello World\n\nThis is a test.")

            # Render to string buffer
            output = StringIO()
            mdcat(md_path, render_images=False, dest=output)

            result = output.getvalue()
            assert "Hello World" in result

    def test_mdcat_with_code_block(self):
        """Test mdcat with code block."""
        from dapple.extras.mdcat import mdcat

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("```python\nprint('hello')\n```")

            output = StringIO()
            mdcat(md_path, render_images=False, dest=output)

            result = output.getvalue()
            assert "print" in result

    def test_mdcat_headings_and_lists(self):
        """Test mdcat with headings and bullet lists."""
        from dapple.extras.mdcat import mdcat

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("# Title\n\n## Section\n\n- Item one\n- Item two\n- Item three\n")

            output = StringIO()
            mdcat(md_path, render_images=False, dest=output)

            result = output.getvalue()
            assert "Title" in result
            assert "Section" in result

    def test_mdcat_no_images_flag(self):
        """Test mdcat with render_images=False skips image processing."""
        from dapple.extras.mdcat import mdcat

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("# Doc\n\n![alt](nonexistent.png)\n\nText after.")

            output = StringIO()
            mdcat(md_path, render_images=False, dest=output)

            result = output.getvalue()
            assert "Doc" in result

    def test_mdcat_hyperlinks_flag(self):
        """Test mdcat with hyperlinks disabled."""
        from dapple.extras.mdcat import mdcat

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("[link text](https://example.com)")

            output = StringIO()
            mdcat(md_path, render_images=False, hyperlinks=False, dest=output)

            result = output.getvalue()
            assert "link" in result.lower()

    def test_mdcat_custom_width(self):
        """Test mdcat with custom console width."""
        from dapple.extras.mdcat import mdcat

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("# Title\n\nSome paragraph text here.")

            output = StringIO()
            mdcat(md_path, render_images=False, width=40, dest=output)

            result = output.getvalue()
            assert "Title" in result

    def test_mdcat_custom_code_theme(self):
        """Test mdcat with custom code theme."""
        from dapple.extras.mdcat import mdcat

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("```python\nx = 1\n```")

            output = StringIO()
            mdcat(md_path, render_images=False, code_theme="emacs", dest=output)

            result = output.getvalue()
            assert len(result) > 0

    def test_mdcat_nonexistent_file(self, capsys):
        """Test mdcat with nonexistent file prints error."""
        from dapple.extras.mdcat import mdcat

        mdcat("/nonexistent/file.md", render_images=False)
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()


class TestGetRenderer:
    """Tests for get_renderer function."""

    def test_auto_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("auto", opts)
        assert hasattr(renderer, "render")

    def test_braille_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("braille", opts)
        assert hasattr(renderer, "render")

    def test_quadrants_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("quadrants", opts)
        assert hasattr(renderer, "render")

    def test_sextants_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("sextants", opts)
        assert hasattr(renderer, "render")

    def test_ascii_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("ascii", opts)
        assert hasattr(renderer, "render")

    def test_sixel_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("sixel", opts)
        assert hasattr(renderer, "render")

    def test_kitty_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("kitty", opts)
        assert hasattr(renderer, "render")

    def test_fingerprint_renderer(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        renderer = get_renderer("fingerprint", opts)
        assert hasattr(renderer, "render")

    def test_unknown_renderer_raises(self):
        from dapple.extras.mdcat.mdcat import get_renderer, MdcatOptions

        opts = MdcatOptions()
        with pytest.raises(ValueError, match="Unknown renderer"):
            get_renderer("unknown", opts)


class TestMdcatCLI:
    """Tests for mdcat CLI."""

    def test_help_output(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "dapple.extras.mdcat.mdcat", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "mdcat" in result.stdout.lower() or "markdown" in result.stdout.lower()

    def test_file_arg(self):
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("# Hello\n\nWorld.")

            result = subprocess.run(
                ["python", "-m", "dapple.extras.mdcat.mdcat", str(md_path), "--no-images"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert "Hello" in result.stdout

    def test_no_images_flag(self):
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test.md"
            md_path.write_text("# Test\n\n![img](missing.png)\n")

            result = subprocess.run(
                ["python", "-m", "dapple.extras.mdcat.mdcat", str(md_path), "--no-images"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0

    def test_nonexistent_file(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "dapple.extras.mdcat.mdcat", "/nonexistent/file.md"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0

