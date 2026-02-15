# thumbcat -- Image Contact Sheet

Display multiple images as a thumbnail grid.

## Installation

```bash
pip install dapple[thumbcat]
```

## Usage

```bash
thumbcat photos/*.jpg --cols 4 -w 120
thumbcat *.png --cols 3 --no-titles
thumbcat -r sextants images/*.jpg
```

| Flag | Meaning |
|------|---------|
| `--cols N` | Number of columns (default: 4) |
| `--no-titles` | Hide filenames above thumbnails |
| `-w` / `-r` | Standard width and renderer flags |
