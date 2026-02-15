# ansicat -- ANSI Art Viewer

View ANSI art files in the terminal using dapple renderers.

## Installation

```bash
pip install dapple[ansicat]
```

No additional dependencies beyond dapple core.

## Usage

```bash
ansicat artwork.ans
ansicat artwork.ans -r sextants -w 80
cat artwork.ans | ansicat -
```

Uses dapple's `from_ansi()` adapter to parse ANSI escape sequences into a Canvas, then renders with the selected renderer.
