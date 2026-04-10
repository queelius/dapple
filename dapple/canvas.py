"""Canvas - the core bitmap container for dapple.

Canvas holds a bitmap (and optionally color data) and provides rendering
to various terminal formats via pluggable renderers.
"""

from __future__ import annotations

import sys
from io import StringIO
from typing import TYPE_CHECKING, Any, TextIO

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from dapple.renderers import Renderer


class Canvas:
    """A bitmap that renders to terminal character art.

    Canvas is the primary class for working with dapple. It holds a grayscale
    bitmap and optional color data, and can render to various formats using
    pluggable renderers.

    Attributes:
        bitmap: Read-only view of the grayscale bitmap (H, W).
        colors: Read-only view of the RGB colors (H, W, 3), or None.
        pixel_width: Width of the bitmap in pixels.
        pixel_height: Height of the bitmap in pixels.
        shape: (H, W) tuple (numpy convention).
        size: (W, H) tuple (PIL convention).

    Example:
        >>> import numpy as np
        >>> from dapple import Canvas, braille, quadrants
        >>>
        >>> # Create canvas from bitmap
        >>> bitmap = np.random.rand(40, 80).astype(np.float32)
        >>> canvas = Canvas(bitmap)
        >>>
        >>> # Output to different destinations
        >>> canvas.out(braille)              # to stdout
        >>> canvas.out(quadrants, "art.txt") # to file
        >>>
        >>> # Default renderer for REPL/debugging
        >>> canvas = Canvas(bitmap, renderer=braille)
        >>> print(canvas)  # Uses braille
    """

    __slots__ = ("_bitmap", "_colors", "_renderer")

    def __init__(
        self,
        bitmap: NDArray[np.floating],
        *,
        colors: NDArray[np.floating] | None = None,
        renderer: Renderer | None = None,
    ) -> None:
        """Create a new Canvas.

        Args:
            bitmap: 2D array of shape (H, W) with values 0.0-1.0.
                    Higher values = brighter pixels.
            colors: Optional 3D array of shape (H, W, 3) with RGB values 0.0-1.0.
            renderer: Default renderer for __str__. If None, uses braille.

        Raises:
            ValueError: If bitmap is not 2D or colors shape doesn't match.
        """
        if bitmap.ndim != 2:
            raise ValueError(f"bitmap must be 2D, got shape {bitmap.shape}")

        if colors is not None:
            if colors.ndim != 3 or colors.shape[2] != 3:
                raise ValueError(f"colors must be (H, W, 3), got shape {colors.shape}")
            if colors.shape[:2] != bitmap.shape:
                raise ValueError(
                    f"colors shape {colors.shape[:2]} must match bitmap shape {bitmap.shape}"
                )
            self._colors: NDArray[np.floating] | None = np.asarray(colors, dtype=np.float32)
        else:
            self._colors = None

        self._bitmap: NDArray[np.floating] = np.asarray(bitmap, dtype=np.float32)
        self._renderer: Renderer | None = renderer

    # Properties
    @property
    def pixel_width(self) -> int:
        """Width of the bitmap in pixels."""
        return self._bitmap.shape[1]

    @property
    def pixel_height(self) -> int:
        """Height of the bitmap in pixels."""
        return self._bitmap.shape[0]

    @property
    def shape(self) -> tuple[int, int]:
        """(H, W) tuple - numpy convention."""
        return self._bitmap.shape  # type: ignore

    @property
    def size(self) -> tuple[int, int]:
        """(W, H) tuple - PIL convention."""
        return (self._bitmap.shape[1], self._bitmap.shape[0])

    @property
    def bitmap(self) -> NDArray[np.floating]:
        """Read-only view of the grayscale bitmap."""
        view = self._bitmap.view()
        view.flags.writeable = False
        return view

    @property
    def colors(self) -> NDArray[np.floating] | None:
        """Read-only view of the RGB colors, or None."""
        if self._colors is None:
            return None
        view = self._colors.view()
        view.flags.writeable = False
        return view

    @property
    def default_renderer(self) -> Renderer | None:
        """Default renderer used by ``__str__``, or ``None`` if unset."""
        return self._renderer

    # Rendering
    def out(self, renderer: Renderer, dest: str | TextIO | None = None) -> None:
        """Output rendered canvas to a destination.

        Args:
            renderer: The renderer to use (braille, quadrants, sextants, etc.)
            dest: File path (str) or file-like object. Defaults to sys.stdout.

        Examples:
            >>> canvas.out(braille)                    # to stdout
            >>> canvas.out(quadrants, sys.stderr)      # to stderr
            >>> canvas.out(braille, "art.txt")         # to file path
            >>> canvas.out(sextants, open("f.txt","w")) # to file handle
        """
        if dest is None:
            dest = sys.stdout

        if isinstance(dest, str):
            with open(dest, "w", encoding="utf-8") as f:
                renderer.render(self._bitmap, self._colors, dest=f)
        else:
            renderer.render(self._bitmap, self._colors, dest=dest)

    def __str__(self) -> str:
        """Render using default renderer (for REPL/debugging).

        Uses ``braille`` when no default renderer is set — the documented
        behaviour in both the class docstring and CLAUDE.md. Braille works
        everywhere (no colour required) and is the safest default for print().
        For explicit control, use out() instead.
        """
        renderer = self._renderer
        if renderer is None:
            from dapple.renderers import braille

            renderer = braille
        buf = StringIO()
        renderer.render(self._bitmap, self._colors, dest=buf)
        return buf.getvalue()

    def __repr__(self) -> str:
        """Return a string representation."""
        h, w = self.shape
        color_str = ", colors=True" if self._colors is not None else ""
        renderer_str = f", renderer={type(self._renderer).__name__}" if self._renderer else ""
        return f"Canvas({h}x{w}{color_str}{renderer_str})"

    # Pixel access
    def __getitem__(self, key: Any) -> NDArray[np.floating] | float:
        """Access pixels by index.

        Supports:
            canvas[y, x] -> single pixel value
            canvas[y1:y2, x1:x2] -> sliced bitmap array

        Args:
            key: Index or slice tuple.

        Returns:
            Pixel value or sliced array.
        """
        return self._bitmap[key]

    # Builder methods
    def fit(
        self,
        renderer: Renderer,
        *,
        width: int | None = None,
        height: int | None = None,
        cell_ratio: float = 0.5,
    ) -> Canvas:
        """Return new Canvas resized to fit character dimensions.

        For character renderers (braille, sextants, etc.): resizes bitmap
        to pixel dimensions and applies aspect-ratio correction.
        For pixel renderers (sixel, kitty): returns self unchanged.

        Args:
            renderer: The renderer determining cell dimensions.
            width: Target width in characters (None = terminal width).
            height: Target height in characters (None = auto from aspect).
            cell_ratio: Terminal cell aspect ratio (default 0.5).

        Returns:
            New Canvas resized to fit the renderer.
        """
        from dapple.layout import _fit_canvas
        return _fit_canvas(self, renderer, width=width, height=height, cell_ratio=cell_ratio)

    def with_renderer(self, renderer: Renderer) -> Canvas:
        """Create a new Canvas with a different default renderer.

        Args:
            renderer: New default renderer.

        Returns:
            New Canvas with the same bitmap/colors but different renderer.
        """
        return Canvas(
            self._bitmap,
            colors=self._colors,
            renderer=renderer,
        )

    def with_invert(self) -> Canvas:
        """Create a new Canvas with inverted brightness.

        Returns:
            New Canvas with inverted bitmap (0->1, 1->0).
        """
        return Canvas(
            1.0 - self._bitmap,
            colors=self._colors,
            renderer=self._renderer,
        )

    # Composition methods
    def hstack(self, other: Canvas) -> Canvas:
        """Horizontally stack this canvas with another.

        Args:
            other: Canvas to stack to the right.

        Returns:
            New Canvas with combined width.

        Raises:
            ValueError: If heights don't match.
        """
        if self.pixel_height != other.pixel_height:
            raise ValueError(
                f"Heights must match: {self.pixel_height} vs {other.pixel_height}"
            )

        new_bitmap = np.hstack([self._bitmap, other._bitmap])

        new_colors = None
        if self._colors is not None and other._colors is not None:
            new_colors = np.hstack([self._colors, other._colors])
        elif self._colors is not None:
            # Convert other to grayscale colors
            other_gray = np.stack([other._bitmap] * 3, axis=2)
            new_colors = np.hstack([self._colors, other_gray])
        elif other._colors is not None:
            # Convert self to grayscale colors
            self_gray = np.stack([self._bitmap] * 3, axis=2)
            new_colors = np.hstack([self_gray, other._colors])

        return Canvas(new_bitmap, colors=new_colors, renderer=self._renderer)

    def vstack(self, other: Canvas) -> Canvas:
        """Vertically stack this canvas with another.

        Args:
            other: Canvas to stack below.

        Returns:
            New Canvas with combined height.

        Raises:
            ValueError: If widths don't match.
        """
        if self.pixel_width != other.pixel_width:
            raise ValueError(
                f"Widths must match: {self.pixel_width} vs {other.pixel_width}"
            )

        new_bitmap = np.vstack([self._bitmap, other._bitmap])

        new_colors = None
        if self._colors is not None and other._colors is not None:
            new_colors = np.vstack([self._colors, other._colors])
        elif self._colors is not None:
            other_gray = np.stack([other._bitmap] * 3, axis=2)
            new_colors = np.vstack([self._colors, other_gray])
        elif other._colors is not None:
            self_gray = np.stack([self._bitmap] * 3, axis=2)
            new_colors = np.vstack([self_gray, other._colors])

        return Canvas(new_bitmap, colors=new_colors, renderer=self._renderer)

    def overlay(self, other: Canvas, x: int, y: int) -> Canvas:
        """Overlay another canvas at a specific position.

        Args:
            other: Canvas to overlay.
            x: X position (left edge) in pixels.
            y: Y position (top edge) in pixels.

        Returns:
            New Canvas with the overlay applied.
        """
        new_bitmap = self._bitmap.copy()

        # Calculate overlap region
        src_x1 = max(0, -x)
        src_y1 = max(0, -y)
        src_x2 = min(other.pixel_width, self.pixel_width - x)
        src_y2 = min(other.pixel_height, self.pixel_height - y)

        dst_x1 = max(0, x)
        dst_y1 = max(0, y)
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)

        if src_x2 > src_x1 and src_y2 > src_y1:
            new_bitmap[dst_y1:dst_y2, dst_x1:dst_x2] = other._bitmap[
                src_y1:src_y2, src_x1:src_x2
            ]

        new_colors = None
        if self._colors is not None:
            new_colors = self._colors.copy()
            if other._colors is not None and src_x2 > src_x1 and src_y2 > src_y1:
                new_colors[dst_y1:dst_y2, dst_x1:dst_x2] = other._colors[
                    src_y1:src_y2, src_x1:src_x2
                ]
            elif src_x2 > src_x1 and src_y2 > src_y1:
                # Convert other to grayscale colors
                gray_region = other._bitmap[src_y1:src_y2, src_x1:src_x2]
                new_colors[dst_y1:dst_y2, dst_x1:dst_x2] = np.stack(
                    [gray_region] * 3, axis=2
                )

        return Canvas(new_bitmap, colors=new_colors, renderer=self._renderer)

    def crop(self, x1: int, y1: int, x2: int, y2: int) -> Canvas:
        """Crop the canvas to a rectangular region.

        Args:
            x1: Left edge (inclusive).
            y1: Top edge (inclusive).
            x2: Right edge (exclusive).
            y2: Bottom edge (exclusive).

        Returns:
            New Canvas with the cropped region.

        Raises:
            ValueError: If coordinates are invalid.
        """
        if x1 < 0 or y1 < 0 or x2 > self.pixel_width or y2 > self.pixel_height:
            raise ValueError(
                f"Crop region ({x1}, {y1}, {x2}, {y2}) out of bounds "
                f"for canvas of size {self.size}"
            )
        if x1 >= x2 or y1 >= y2:
            raise ValueError(f"Invalid crop region: ({x1}, {y1}, {x2}, {y2})")

        new_bitmap = self._bitmap[y1:y2, x1:x2].copy()
        new_colors = None
        if self._colors is not None:
            new_colors = self._colors[y1:y2, x1:x2].copy()

        return Canvas(new_bitmap, colors=new_colors, renderer=self._renderer)

    def __add__(self, other: Canvas) -> Canvas:
        """Horizontally stack canvases using + operator."""
        return self.hstack(other)

    # Conversion methods
    def to_bitmap(self) -> NDArray[np.floating]:
        """Return a copy of the bitmap array.

        Returns:
            Copy of the (H, W) grayscale bitmap.
        """
        return self._bitmap.copy()

    def to_pil(self) -> Any:
        """Convert to PIL Image.

        Returns:
            PIL Image object (grayscale or RGB).

        Raises:
            ImportError: If PIL is not installed.
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImportError("PIL is required for to_pil(). Install with: pip install pillow")

        if self._colors is not None:
            rgb = (self._colors * 255).astype(np.uint8)
            return Image.fromarray(rgb)
        else:
            gray = (self._bitmap * 255).astype(np.uint8)
            return Image.fromarray(gray)

    def save(self, path: str) -> None:
        """Save the canvas as an image file.

        Args:
            path: Output file path. Format determined by extension.

        Raises:
            ImportError: If PIL is not installed.
        """
        img = self.to_pil()
        img.save(path)

