# CLI Tools

dapple ships 12 CLI tools as extras. Install individually or all at once:

```bash
pip install dapple[all-tools]
```

## Shared Flags

All tools that produce graphical output share these flags:

| Flag | Meaning |
|------|---------|
| `-r` / `--renderer` | `braille`, `quadrants`, `sextants`, `ascii`, `sixel`, `kitty`, `fingerprint`, or `auto` |
| `-w` / `--width` | Output width in terminal columns |
| `-H` / `--height` | Output height in terminal rows |
| `--dither` | Floyd-Steinberg dithering |
| `--contrast` | Auto-contrast stretching |
| `--invert` | Invert brightness |
| `--grayscale` | Force grayscale |
| `--no-color` | Disable color output |
| `-o` / `--output` | Write to file instead of stdout |

## Viewers

- **[imgcat](imgcat.md)** — Display images (JPEG, PNG, WebP, etc.)
- **[vidcat](vidcat.md)** — Video frames, asciinema export
- **[pdfcat](pdfcat.md)** — PDF page rendering
- **[mdcat](mdcat.md)** — Markdown with Rich formatting and inline images
- **[ansicat](ansicat.md)** — ANSI art viewer

## Data & Math

- **[funcat](funcat.md)** — Math expressions and parametric curves, with pipeline chaining
- **[csvcat](csvcat.md)** — CSV/TSV tables and multi-series charts
- **[datcat](datcat.md)** — JSON/JSONL tables, sparklines, and charts
- **[vizlib](vizlib.md)** — Programmatic chart primitives (used by csvcat/datcat)

## Composition

- **[compcat](compcat.md)** — Compare renderers side by side
- **[thumbcat](thumbcat.md)** — Image contact sheet / thumbnail grid

## Analysis

- **[plotcat](plotcat.md)** — Faceted data plots grouped by column
- **[dashcat](dashcat.md)** — YAML-driven terminal dashboards
