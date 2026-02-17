# htmlcat -- HTML Viewer

Display HTML files in the terminal. htmlcat converts HTML to markdown via
markdownify, then renders with Rich formatting and dapple inline images.
Best for documentation, articles, and READMEs -- not CSS/JS-heavy pages.

## Installation

```bash
pip install dapple[htmlcat]
```

This installs Rich (for terminal formatting) and markdownify (for HTML-to-markdown
conversion) as dependencies, plus Pillow for inline image rendering.

## Usage

### Basic Display

```bash
# View an HTML file
htmlcat page.html

# View multiple files (separated by headers)
htmlcat doc1.html doc2.html
```

### Image Control

```bash
# Skip rendering inline images
htmlcat page.html --no-images

# Use a specific renderer for images
htmlcat page.html -r sextants

# Control image width
htmlcat page.html --image-width 60
```

### Display Options

```bash
# Set console width
htmlcat page.html -w 80

# Change code block syntax theme
htmlcat page.html --code-theme dracula

# Disable clickable hyperlinks
htmlcat page.html --no-hyperlinks
```

### Debugging

```bash
# Output the intermediate markdown instead of rendering
htmlcat page.html --raw
```

### Output to File

```bash
htmlcat page.html -o output.txt
```

## How It Works

htmlcat processes HTML in two stages:

1. **Convert** -- markdownify transforms HTML into markdown, preserving
   headings, lists, code blocks, links, and inline images.
2. **Render** -- Rich renders the markdown with syntax highlighting, styled
   headings, and formatted text. Inline images are rendered through dapple
   using the selected renderer.

This two-stage approach means htmlcat works well for content-heavy HTML
(documentation, blog posts, articles) but is not designed for layout-heavy
pages that depend on CSS or JavaScript.

## Python API

```python
from dapple.extras.htmlcat.htmlcat import htmlcat

# Render HTML file to terminal
htmlcat("page.html")

# Full control
htmlcat(
    "page.html",
    renderer="sextants",
    width=80,
    image_width=60,
    render_images=True,
    code_theme="dracula",
    hyperlinks=True,
    raw=False,
    dest=None,  # stdout
)

# Output to file
with open("output.txt", "w") as f:
    htmlcat("page.html", dest=f)
```

## Entry Point

```
htmlcat = dapple.extras.htmlcat.cli:main
```

## Reference

```
usage: htmlcat [-h] [-r {auto,braille,quadrants,sextants,ascii,sixel,kitty}]
               [-w WIDTH] [--image-width WIDTH] [--no-images]
               [--code-theme THEME] [--no-hyperlinks] [--raw] [-o OUTPUT]
               [files ...]

Display HTML files in the terminal with inline images

positional arguments:
  files                 HTML file(s) to display

options:
  -r, --renderer        Renderer for inline images (default: auto)
  -w, --width           Console width in characters (default: terminal width)
  --image-width         Image width in characters (default: console width)
  --no-images           Skip rendering inline images
  --code-theme          Pygments theme for code blocks (default: monokai)
  --no-hyperlinks       Disable clickable hyperlinks
  --raw                 Output converted markdown instead of rendering
  -o, --output          Output file (default: stdout)
```
