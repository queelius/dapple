# diffcat -- Visual Image Diff

Compare two images visually in the terminal.

## Installation

```bash
pip install dapple[diffcat]
```

## Usage

```bash
diffcat before.png after.png                    # side-by-side (default)
diffcat before.png after.png --mode overlay     # difference heatmap
diffcat before.png after.png --mode highlight   # highlight changed regions
```

| Mode | Description |
|------|-------------|
| `side` | Side-by-side with labeled frames (default) |
| `overlay` | Pixel difference rendered as a heatmap |
| `highlight` | Changed regions overlaid on the original |
