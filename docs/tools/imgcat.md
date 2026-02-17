# imgcat -- Terminal Image Viewer

Display images in the terminal using any dapple renderer.

## Installation

```bash
pip install dapple[imgcat]
```

This installs Pillow as a dependency for image loading.

## Usage

### Basic

```bash
# View an image (auto-detects best renderer for your terminal)
imgcat photo.jpg

# View multiple images
imgcat *.png
```

### Renderer Selection

```bash
# Force a specific renderer
imgcat -r braille photo.jpg       # Unicode braille dots, high detail
imgcat -r quadrants photo.jpg     # 2x2 block characters, color
imgcat -r sextants photo.jpg      # 2x3 block characters, higher resolution
imgcat -r ascii photo.jpg         # Classic ASCII art, universal
imgcat -r sixel photo.jpg         # True pixel output (xterm, mlterm, foot)
imgcat -r kitty photo.jpg         # True pixel output (Kitty, WezTerm, Ghostty)
imgcat -r fingerprint photo.jpg   # Glyph-matching, artistic
```

### Preprocessing

```bash
# Floyd-Steinberg dithering for better gradients in binary renderers
imgcat --dither photo.jpg

# Auto-contrast enhancement
imgcat --contrast photo.jpg

# Invert brightness
imgcat --invert photo.jpg

# Combine preprocessing steps
imgcat --dither --contrast photo.jpg
```

### Size Control

```bash
# Set output width in terminal columns
imgcat -w 60 photo.jpg

# Set output height in terminal rows
imgcat -H 30 photo.jpg

# Both
imgcat -w 80 -H 40 photo.jpg
```

### Color Control

```bash
# Force grayscale output
imgcat --grayscale photo.jpg

# Disable color entirely (monochrome)
imgcat --no-color photo.jpg
```

### Output to File

```bash
# Save rendered output to a file
imgcat -o output.txt photo.jpg

# Combine with renderer for file-based workflows
imgcat -r braille -o art.txt photo.jpg
```

### Grid / Contact Sheet

When multiple images are provided, imgcat renders them as a grid (contact sheet):

```bash
# Display all PNGs as a grid
imgcat *.png

# Control grid columns (default: 4)
imgcat photos/*.jpg --cols 3

# Hide filenames in grid mode
imgcat *.png --no-titles

# Combine with width control
imgcat photos/*.jpg --cols 4 -w 120

# Single image always renders directly (no grid)
imgcat photo.jpg
```

### Piping from stdin

```bash
# Display an image from a URL
curl -s https://example.com/photo.png | imgcat
```

## Supported Formats

imgcat supports any format that Pillow can load, including:

- JPEG
- PNG
- WebP
- BMP
- TIFF
- GIF (first frame)
- ICO
- PPM/PGM/PBM

## Auto-detection

When using `-r auto` (the default), imgcat queries the terminal to determine
the best available protocol:

1. **Kitty protocol** -- detected via `TERM_PROGRAM` or `KITTY_WINDOW_ID`
2. **Sixel protocol** -- detected via Device Attributes query
3. **Quadrants** -- fallback for terminals with Unicode and color support
4. **Braille** -- fallback for Unicode-capable terminals
5. **ASCII** -- universal fallback

## Python API

```python
from dapple.extras.imgcat import view, imgcat

# Quick view with defaults
view("photo.jpg")

# Full control
imgcat(
    "photo.jpg",
    renderer="braille",
    width=80,
    dither=True,
    contrast=True,
)

# Render to a file
with open("output.txt", "w") as f:
    imgcat("photo.jpg", renderer="quadrants", dest=f)
```

## Entry Point

```
imgcat = dapple.extras.imgcat.imgcat:main
```

## Reference

```
usage: imgcat [-h] [-r {auto,braille,quadrants,sextants,ascii,sixel,kitty,fingerprint}]
              [-w WIDTH] [-H HEIGHT] [--dither] [--contrast] [--invert]
              [-o OUTPUT] [--grayscale] [--no-color]
              [--cols N] [--no-titles]
              [images ...]

Display images in the terminal using dapple

positional arguments:
  images                Image file(s) to display

options:
  -r, --renderer        Renderer to use (default: auto)
  -w, --width           Output width in characters (default: terminal width)
  -H, --height          Output height in characters
  --dither              Apply Floyd-Steinberg dithering
  --contrast            Apply auto-contrast
  --invert              Invert colors
  -o, --output          Output file (default: stdout)
  --grayscale           Force grayscale output
  --no-color            Disable color output

grid options:
  --cols N              Number of grid columns for multiple images (default: 4)
  --no-titles           Hide filenames in grid mode
```
