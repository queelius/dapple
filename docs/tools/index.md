# CLI Tools

dapple ships 11 CLI tools as extras. Install individually or all at once:

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

- **[imgcat](imgcat.md)** — Display images (JPEG, PNG, WebP, etc.) with grid/contact sheet mode
- **[vidcat](vidcat.md)** — Video frames, in-place playback, asciinema export
- **[pdfcat](pdfcat.md)** — PDF page rendering
- **[mdcat](mdcat.md)** — Markdown with Rich formatting and inline images
- **[htmlcat](htmlcat.md)** — HTML viewer with Rich formatting and inline images
- **[ansicat](ansicat.md)** — ANSI art viewer

## Data & Math

- **[funcat](funcat.md)** — Math expressions and parametric curves, with pipeline chaining
- **[datcat](datcat.md)** — Structured data (JSON/JSONL/CSV/TSV) tables, sparklines, and charts
- **[vizlib](vizlib.md)** — Programmatic chart primitives (used by datcat)

## Composition

- **[compcat](compcat.md)** — Compare renderers side by side

## Analysis

- **[plotcat](plotcat.md)** — Faceted data plots grouped by column
- **[dashcat](dashcat.md)** — YAML-driven terminal dashboards
