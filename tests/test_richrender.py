"""Tests for dapple.extras.richrender shared module."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests if rich not available
pytest.importorskip("rich")
pytest.importorskip("PIL")


class TestImageCache:
    """Tests for ImageCache from richrender."""

    def test_cache_file(self):
        from dapple.extras.richrender import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            url = "https://example.com/image.png"
            data = b"fake image data"

            cached_path = cache.cache_file(url, data)
            assert cached_path.exists()
            assert cached_path.read_bytes() == data

    def test_get_cached_path_exists(self):
        from dapple.extras.richrender import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            url = "https://example.com/image.png"
            data = b"fake image data"

            cache.cache_file(url, data)
            cached = cache.get_cached_path(url)
            assert cached is not None
            assert cached.exists()

    def test_get_cached_path_not_exists(self):
        from dapple.extras.richrender import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            cached = cache.get_cached_path("https://example.com/nonexistent.png")
            assert cached is None

    def test_hash_url_deterministic(self):
        from dapple.extras.richrender import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            h1 = cache._hash_url("https://example.com/img.png")
            h2 = cache._hash_url("https://example.com/img.png")
            assert h1 == h2

    def test_hash_url_different_for_different_urls(self):
        from dapple.extras.richrender import ImageCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            h1 = cache._hash_url("https://example.com/a.png")
            h2 = cache._hash_url("https://example.com/b.png")
            assert h1 != h2

    def test_get_extension_known_types(self):
        from dapple.extras.richrender import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/image.png") == ".png"
        assert cache._get_extension("https://example.com/photo.jpg") == ".jpg"
        assert cache._get_extension("https://example.com/photo.jpeg") == ".jpeg"
        assert cache._get_extension("https://example.com/anim.gif") == ".gif"
        assert cache._get_extension("https://example.com/image.webp") == ".webp"

    def test_get_extension_strips_query_params(self):
        from dapple.extras.richrender import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/image.jpg?w=100") == ".jpg"

    def test_get_extension_defaults_to_png(self):
        from dapple.extras.richrender import ImageCache

        cache = ImageCache.__new__(ImageCache)
        assert cache._get_extension("https://example.com/image") == ".png"
        assert cache._get_extension("https://example.com/data.bmp") == ".png"

    def test_default_cache_dir(self):
        from dapple.extras.richrender import ImageCache

        cache = ImageCache()
        assert cache.cache_dir == Path.home() / ".cache" / "mdcat"


class TestImageResolver:
    """Tests for ImageResolver from richrender."""

    def test_resolve_local_absolute(self):
        from dapple.extras.richrender import ImageResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.png"
            test_file.write_bytes(b"test")

            resolver = ImageResolver()
            result = resolver.resolve(str(test_file))
            assert result == test_file

    def test_resolve_local_relative_with_base_path(self):
        from dapple.extras.richrender import ImageResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "README.md"
            base_file.write_text("# Test")
            img_file = Path(tmpdir) / "image.png"
            img_file.write_bytes(b"test")

            resolver = ImageResolver(base_path=base_file)
            result = resolver.resolve("image.png")
            assert result == img_file

    def test_resolve_nonexistent(self):
        from dapple.extras.richrender import ImageResolver

        resolver = ImageResolver()
        result = resolver.resolve("/nonexistent/path/to/image.png")
        assert result is None

    def test_resolve_file_url(self):
        from dapple.extras.richrender import ImageResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.png"
            test_file.write_bytes(b"test")

            resolver = ImageResolver()
            result = resolver.resolve(f"file://{test_file}")
            assert result == test_file

    def test_resolve_file_url_nonexistent(self):
        from dapple.extras.richrender import ImageResolver

        resolver = ImageResolver()
        result = resolver.resolve("file:///nonexistent/image.png")
        assert result is None

    def test_custom_cache(self):
        from dapple.extras.richrender import ImageCache, ImageResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ImageCache(cache_dir=Path(tmpdir))
            resolver = ImageResolver(cache=cache)
            assert resolver.cache is cache


class TestDappleImageItem:
    """Tests for DappleImageItem from richrender."""

    def test_configure_and_reset(self):
        from dapple.extras.richrender import DappleImageItem, ImageResolver

        resolver = ImageResolver()
        renderer = MagicMock()

        DappleImageItem.configure(resolver, renderer, True, 60)
        assert DappleImageItem._resolver is resolver
        assert DappleImageItem._renderer is renderer
        assert DappleImageItem._render_images is True
        assert DappleImageItem._image_width == 60

        DappleImageItem.reset()
        assert DappleImageItem._resolver is None
        assert DappleImageItem._renderer is None
        assert DappleImageItem._render_images is True
        assert DappleImageItem._image_width == 80

    def test_placeholder_with_alt_text(self):
        from dapple.extras.richrender import DappleImageItem
        from rich.text import Text

        item = DappleImageItem.__new__(DappleImageItem)
        item.text = Text("my alt text")
        item.destination = "image.png"

        result = item._placeholder()
        assert "my alt text" in result.plain

    def test_placeholder_with_reason(self):
        from dapple.extras.richrender import DappleImageItem
        from rich.text import Text

        item = DappleImageItem.__new__(DappleImageItem)
        item.text = Text("alt")
        item.destination = "image.png"

        result = item._placeholder(reason="file not found")
        assert "file not found" in result.plain

    def test_placeholder_default_alt(self):
        from dapple.extras.richrender import DappleImageItem
        from rich.text import Text

        item = DappleImageItem.__new__(DappleImageItem)
        item.text = Text("")
        item.destination = "image.png"

        result = item._placeholder()
        assert "image" in result.plain


class TestDappleMarkdown:
    """Tests for DappleMarkdown from richrender."""

    def test_image_element_is_dapple(self):
        from dapple.extras.richrender import DappleImageItem, DappleMarkdown

        assert DappleMarkdown.elements["image"] is DappleImageItem

    def test_inherits_other_elements(self):
        from rich.markdown import Markdown
        from dapple.extras.richrender import DappleMarkdown

        # All non-image elements should still be the originals
        for key, value in Markdown.elements.items():
            if key != "image":
                assert DappleMarkdown.elements[key] is value

    def test_render_simple_text(self):
        from rich.console import Console
        from dapple.extras.richrender import DappleMarkdown

        md = DappleMarkdown("# Hello\n\nParagraph text.")
        buf = StringIO()
        console = Console(file=buf, width=40, force_terminal=False)
        console.print(md)
        output = buf.getvalue()
        assert "Hello" in output


class TestDappleRendering:
    """Tests for dapple_rendering context manager."""

    def test_context_manager_configures_and_resets(self):
        from dapple.extras.richrender import (
            DappleImageItem,
            ImageResolver,
            dapple_rendering,
        )

        resolver = ImageResolver()
        renderer = MagicMock()

        with dapple_rendering(resolver, renderer, True, 60):
            assert DappleImageItem._resolver is resolver
            assert DappleImageItem._renderer is renderer
            assert DappleImageItem._image_width == 60

        # After context exit, should be reset
        assert DappleImageItem._resolver is None
        assert DappleImageItem._renderer is None
        assert DappleImageItem._image_width == 80

    def test_context_manager_resets_on_exception(self):
        from dapple.extras.richrender import (
            DappleImageItem,
            ImageResolver,
            dapple_rendering,
        )

        resolver = ImageResolver()
        renderer = MagicMock()

        with pytest.raises(ValueError):
            with dapple_rendering(resolver, renderer, True, 60):
                raise ValueError("test error")

        # Should still be reset
        assert DappleImageItem._resolver is None
        assert DappleImageItem._renderer is None


class TestRichrenderImportCompatibility:
    """Verify that importing from richrender is equivalent to old mdcat imports."""

    def test_image_cache_same_class(self):
        from dapple.extras.mdcat.mdcat import ImageCache as MdcatImageCache
        from dapple.extras.richrender import ImageCache as RichrenderImageCache

        assert MdcatImageCache is RichrenderImageCache

    def test_image_resolver_same_class(self):
        from dapple.extras.mdcat.mdcat import ImageResolver as MdcatImageResolver
        from dapple.extras.richrender import ImageResolver as RichrenderImageResolver

        assert MdcatImageResolver is RichrenderImageResolver

    def test_dapple_image_item_same_class(self):
        from dapple.extras.mdcat.mdcat import DappleImageItem as MdcatItem
        from dapple.extras.richrender import DappleImageItem as RichrenderItem

        assert MdcatItem is RichrenderItem

    def test_dapple_markdown_same_class(self):
        from dapple.extras.mdcat.mdcat import DappleMarkdown as MdcatMd
        from dapple.extras.richrender import DappleMarkdown as RichrenderMd

        assert MdcatMd is RichrenderMd
