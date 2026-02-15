"""Preprocessing utilities for bitmap images.

Composable transforms that prepare bitmaps for rendering.
All functions take and return numpy arrays (H x W, values 0.0-1.0).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def auto_contrast(bitmap: NDArray[np.floating]) -> NDArray[np.floating]:
    """Stretch histogram to full 0-1 range.

    Normalizes the bitmap so the darkest pixel becomes 0.0 and the
    brightest becomes 1.0. This maximizes contrast before thresholding.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0

    Returns:
        Contrast-stretched bitmap with same shape, values 0.0-1.0

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import auto_contrast
        >>> img = np.array([[0.3, 0.5], [0.4, 0.6]])
        >>> stretched = auto_contrast(img)
        >>> stretched.min(), stretched.max()
        (0.0, 1.0)
    """
    min_val = np.amin(bitmap)
    max_val = np.amax(bitmap)

    if max_val - min_val < 1e-6:
        # Avoid division by zero for constant images
        return np.full_like(bitmap, 0.5)

    return (bitmap - min_val) / (max_val - min_val)


def floyd_steinberg(
    bitmap: NDArray[np.floating],
    threshold: float = 0.5,
) -> NDArray[np.floating]:
    """Apply Floyd-Steinberg dithering for binary output.

    Distributes quantization error to neighboring pixels, creating the
    illusion of grayscale through varying dot density. This is the single
    most effective improvement for binary (braille) output.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        threshold: Threshold for quantization (default 0.5)

    Returns:
        Dithered bitmap with same shape, values are 0.0 or 1.0 only

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import floyd_steinberg
        >>> img = np.linspace(0, 1, 16).reshape(4, 4).astype(np.float32)
        >>> dithered = floyd_steinberg(img)
        >>> np.unique(dithered)
        array([0., 1.], dtype=float32)
    """
    # Work on a copy to avoid modifying input
    img = bitmap.astype(np.float64).copy()
    h, w = img.shape

    for y in range(h):
        for x in range(w):
            old_pixel = img[y, x]
            new_pixel = 1.0 if old_pixel > threshold else 0.0
            img[y, x] = new_pixel
            error = old_pixel - new_pixel

            # Distribute error to neighbors using Floyd-Steinberg coefficients:
            #       X   7/16
            # 3/16 5/16 1/16
            if x + 1 < w:
                img[y, x + 1] += error * 7 / 16
            if y + 1 < h:
                if x > 0:
                    img[y + 1, x - 1] += error * 3 / 16
                img[y + 1, x] += error * 5 / 16
                if x + 1 < w:
                    img[y + 1, x + 1] += error * 1 / 16

    return img.astype(np.float32)


def invert(bitmap: NDArray[np.floating]) -> NDArray[np.floating]:
    """Invert bitmap values (0 becomes 1, 1 becomes 0).

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0

    Returns:
        Inverted bitmap with same shape.

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import invert
        >>> img = np.array([[0.0, 0.5], [0.75, 1.0]])
        >>> inverted = invert(img)
        >>> inverted
        array([[1.  , 0.5 ],
               [0.25, 0.  ]])
    """
    return 1.0 - bitmap


def gamma_correct(
    bitmap: NDArray[np.floating],
    gamma: float = 2.2,
) -> NDArray[np.floating]:
    """Apply gamma correction to bitmap.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        gamma: Gamma value (>1 darkens, <1 brightens, 2.2 is standard)

    Returns:
        Gamma-corrected bitmap with same shape.

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import gamma_correct
        >>> img = np.array([[0.5]])
        >>> gamma_correct(img, 2.2)[0, 0]  # Darker
        0.21763764
    """
    # Clamp to valid range before gamma
    clamped = np.clip(bitmap, 0.0, 1.0)
    return np.power(clamped, gamma).astype(np.float32)


def sharpen(
    bitmap: NDArray[np.floating],
    strength: float = 1.0,
) -> NDArray[np.floating]:
    """Apply unsharp mask sharpening.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        strength: Sharpening strength (0=none, 1=normal, >1=aggressive)

    Returns:
        Sharpened bitmap with same shape, values clamped to 0.0-1.0

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import sharpen
        >>> img = np.array([[0.5, 0.5, 0.5],
        ...                 [0.5, 1.0, 0.5],
        ...                 [0.5, 0.5, 0.5]], dtype=np.float32)
        >>> sharpened = sharpen(img, strength=1.0)
    """
    # Simple 3x3 Laplacian kernel for edge detection
    h, w = bitmap.shape

    # Pad image with edge values
    padded = np.pad(bitmap, 1, mode="edge")

    # Compute Laplacian (center - average of neighbors)
    laplacian = (
        4 * padded[1:-1, 1:-1]
        - padded[:-2, 1:-1]  # top
        - padded[2:, 1:-1]  # bottom
        - padded[1:-1, :-2]  # left
        - padded[1:-1, 2:]  # right
    )

    # Add scaled Laplacian to original
    sharpened = bitmap + strength * laplacian

    return np.clip(sharpened, 0.0, 1.0).astype(np.float32)


def threshold(
    bitmap: NDArray[np.floating],
    level: float = 0.5,
) -> NDArray[np.floating]:
    """Apply simple binary threshold.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        level: Threshold level (default 0.5)

    Returns:
        Binary bitmap with values 0.0 or 1.0 only.
    """
    return (bitmap > level).astype(np.float32)


def _resize_2d(
    bitmap: NDArray[np.floating],
    new_height: int,
    new_width: int,
) -> NDArray[np.floating]:
    """Resize a 2D array using bilinear interpolation.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        new_height: Target height
        new_width: Target width

    Returns:
        Resized array of shape (new_height, new_width)
    """
    old_h, old_w = bitmap.shape

    # Create coordinate arrays for new image
    y_ratio = old_h / new_height
    x_ratio = old_w / new_width

    y_coords = np.arange(new_height) * y_ratio
    x_coords = np.arange(new_width) * x_ratio

    # Get integer and fractional parts
    y0 = np.floor(y_coords).astype(int)
    x0 = np.floor(x_coords).astype(int)
    y1 = np.minimum(y0 + 1, old_h - 1)
    x1 = np.minimum(x0 + 1, old_w - 1)

    y_frac = y_coords - y0
    x_frac = x_coords - x0

    # Bilinear interpolation
    result = np.zeros((new_height, new_width), dtype=np.float32)
    for y in range(new_height):
        for x in range(new_width):
            top_left = bitmap[y0[y], x0[x]]
            top_right = bitmap[y0[y], x1[x]]
            bottom_left = bitmap[y1[y], x0[x]]
            bottom_right = bitmap[y1[y], x1[x]]

            top = top_left * (1 - x_frac[x]) + top_right * x_frac[x]
            bottom = bottom_left * (1 - x_frac[x]) + bottom_right * x_frac[x]
            result[y, x] = top * (1 - y_frac[y]) + bottom * y_frac[y]

    return result


def resize(
    bitmap: NDArray[np.floating],
    new_height: int,
    new_width: int,
) -> NDArray[np.floating]:
    """Resize bitmap using simple bilinear interpolation.

    This is a basic implementation without external dependencies.
    For better quality, use the PIL adapter.

    Supports both 2D bitmaps (H, W) and 3D color arrays (H, W, 3).
    For 3D arrays, each channel is resized independently.

    Args:
        bitmap: 2D array (H, W) or 3D array (H, W, 3), values 0.0-1.0
        new_height: Target height
        new_width: Target width

    Returns:
        Resized array of shape (new_height, new_width) or
        (new_height, new_width, 3)
    """
    if bitmap.ndim == 3:
        channels = [
            _resize_2d(bitmap[:, :, c], new_height, new_width)
            for c in range(bitmap.shape[2])
        ]
        return np.stack(channels, axis=2)
    return _resize_2d(bitmap, new_height, new_width)


def crop(
    bitmap: NDArray[np.floating],
    x: int,
    y: int,
    width: int,
    height: int,
) -> NDArray[np.floating]:
    """Extract a rectangular region from the bitmap.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        x: Left edge of crop region (pixels from left)
        y: Top edge of crop region (pixels from top)
        width: Width of crop region
        height: Height of crop region

    Returns:
        Cropped bitmap of shape (height, width)

    Raises:
        ValueError: If crop region is out of bounds or has zero size.

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import crop
        >>> img = np.ones((100, 100), dtype=np.float32)
        >>> cropped = crop(img, 10, 10, 50, 50)
        >>> cropped.shape
        (50, 50)
    """
    h, w = bitmap.shape

    if width <= 0 or height <= 0:
        raise ValueError(f"Crop dimensions must be positive, got {width}x{height}")

    if x < 0 or y < 0:
        raise ValueError(f"Crop position must be non-negative, got ({x}, {y})")

    if x + width > w or y + height > h:
        raise ValueError(
            f"Crop region ({x}, {y}, {width}, {height}) exceeds "
            f"bitmap bounds ({w}, {h})"
        )

    return bitmap[y : y + height, x : x + width].copy()


def flip(
    bitmap: NDArray[np.floating],
    direction: Literal["h", "v"],
) -> NDArray[np.floating]:
    """Flip bitmap horizontally or vertically.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        direction: "h" for horizontal (left-right), "v" for vertical (top-bottom)

    Returns:
        Flipped bitmap with same shape.

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import flip
        >>> img = np.array([[1, 0], [0, 0]], dtype=np.float32)
        >>> flip(img, "h")
        array([[0., 1.],
               [0., 0.]], dtype=float32)
        >>> flip(img, "v")
        array([[0., 0.],
               [1., 0.]], dtype=float32)
    """
    if direction == "h":
        return np.flip(bitmap, axis=1).astype(np.float32)
    elif direction == "v":
        return np.flip(bitmap, axis=0).astype(np.float32)
    else:
        raise ValueError(f"direction must be 'h' or 'v', got {direction!r}")


def rotate(
    bitmap: NDArray[np.floating],
    degrees: float,
) -> NDArray[np.floating]:
    """Rotate bitmap by specified degrees (counter-clockwise).

    For 90, 180, 270 degrees, uses efficient numpy rotation.
    For arbitrary angles, uses scipy.ndimage.rotate with bilinear interpolation.

    Args:
        bitmap: 2D array of shape (H, W), values 0.0-1.0
        degrees: Rotation angle in degrees (counter-clockwise)

    Returns:
        Rotated bitmap. For 90/270, dimensions are swapped.
        For arbitrary angles, output is resized to fit rotated content.

    Example:
        >>> import numpy as np
        >>> from dapple.preprocess import rotate
        >>> img = np.array([[1, 0], [0, 0]], dtype=np.float32)
        >>> rotate(img, 90)
        array([[0., 1.],
               [0., 0.]], dtype=float32)
    """
    # Normalize to 0-360
    degrees = degrees % 360

    # Handle exact multiples of 90 with numpy
    if degrees == 0:
        return bitmap.copy().astype(np.float32)
    elif degrees == 90:
        return np.rot90(bitmap, k=1).astype(np.float32)
    elif degrees == 180:
        return np.rot90(bitmap, k=2).astype(np.float32)
    elif degrees == 270:
        return np.rot90(bitmap, k=3).astype(np.float32)
    else:
        # Arbitrary rotation requires scipy
        try:
            from scipy.ndimage import rotate as scipy_rotate
        except ImportError:
            raise ImportError(
                "Arbitrary rotation angles require scipy. "
                "Install with: pip install scipy"
            )

        rotated = scipy_rotate(
            bitmap,
            degrees,
            reshape=True,
            order=1,  # Bilinear interpolation
            mode="constant",
            cval=0.0,
        )
        return np.clip(rotated, 0.0, 1.0).astype(np.float32)
