# vidcat -- Terminal Video Player

Extract and display video frames in the terminal, with optional asciinema
export for sharing recordings.

## Installation

```bash
pip install dapple[vidcat]
```

This installs Pillow as a dependency. You also need **ffmpeg** installed
on your system for video decoding:

```bash
# Debian/Ubuntu
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

## Usage

### Basic Playback

```bash
# Display frames from a video (default: up to 10 evenly spaced frames)
vidcat video.mp4

# Display frames from an animated GIF
vidcat animation.gif
```

### Frame Selection

```bash
# Extract specific frames (1-indexed)
vidcat video.mp4 --frames 1-10         # Frames 1 through 10
vidcat video.mp4 --frames "1,5,10"     # Specific frames
vidcat video.mp4 --frames -5           # First 5 frames
vidcat video.mp4 --frames 100-         # Frame 100 onward

# Extract at time intervals
vidcat video.mp4 --every 1s            # One frame per second
vidcat video.mp4 --every 30s           # One every 30 seconds
vidcat video.mp4 --every 1m            # One per minute

# Control maximum frames extracted
vidcat video.mp4 --max-frames 20       # Up to 20 frames (default: 10)
```

### Renderer Selection

```bash
vidcat video.mp4 -r braille            # Unicode braille dots
vidcat video.mp4 -r quadrants          # 2x2 block characters
vidcat video.mp4 -r sextants           # 2x3 block characters
vidcat video.mp4 -r ascii              # ASCII art
vidcat video.mp4 -r sixel              # True pixel (xterm, mlterm, foot)
vidcat video.mp4 -r kitty              # True pixel (Kitty, WezTerm, Ghostty)
```

### Preprocessing

```bash
vidcat video.mp4 --dither              # Floyd-Steinberg dithering
vidcat video.mp4 --contrast            # Auto-contrast
vidcat video.mp4 --invert              # Invert brightness
vidcat video.mp4 --grayscale           # Force grayscale
vidcat video.mp4 --no-color            # Disable color
```

### In-Place Playback

The `--play` flag renders frames in-place (using ANSI cursor movement) for
smooth animation directly in the terminal:

```bash
# Play video as in-place animation
vidcat video.mp4 --play

# Control playback speed
vidcat video.mp4 --play --fps 15       # 15 frames per second
vidcat animation.gif --play --fps 30   # Faster playback

# Combine with renderer and width
vidcat video.mp4 --play -r sextants -w 80
```

`--play` requires a TTY (interactive terminal). When piped or redirected, it
falls back to stacked frame output with a warning.

### Animation (Stacked)

```bash
# Add delay between frames for animation effect (stacked output)
vidcat animation.gif --delay 0.1       # 100ms between frames
vidcat video.mp4 --frames 1-30 --delay 0.05
```

### Size Control

```bash
vidcat video.mp4 -w 60                 # Width in terminal columns
vidcat video.mp4 -H 20                 # Height in terminal rows
```

### Asciinema Export

Convert video to asciinema `.cast` files for playback with `asciinema play`
or embedding on asciinema.org:

```bash
# Export to asciinema format
vidcat video.mp4 --asciinema output.cast

# Control playback FPS (default: 10)
vidcat video.mp4 --asciinema output.cast --fps 15

# Add a title
vidcat video.mp4 --asciinema output.cast --title "My Video"

# Use a specific renderer for the recording
vidcat video.mp4 --asciinema output.cast -r braille --max-frames 100

# Play the recording
asciinema play output.cast
```

The exported `.cast` file uses the asciicast v2 format. Each frame is rendered
with the selected dapple renderer, then written as a timed output event.

### Output to File

```bash
vidcat video.mp4 -o frames.txt
```

## Supported Formats

vidcat supports any format that ffmpeg can decode, including:

- MP4 (H.264, H.265)
- WebM (VP8, VP9, AV1)
- GIF (animated)
- AVI
- MOV
- MKV
- FLV
- WMV

## Python API

```python
from dapple.extras.vidcat import vidcat, view, to_asciinema

# Quick view with defaults
view("animation.gif")

# Full control
vidcat(
    "video.mp4",
    renderer="braille",
    width=80,
    max_frames=20,
    frames="1-10",
    frame_delay=0.1,
)

# Export to asciinema
to_asciinema(
    "video.mp4",
    "output.cast",
    fps=15,
    renderer="braille",
    max_frames=100,
    title="Demo Video",
)
```

## Entry Point

```
vidcat = dapple.extras.vidcat.vidcat:main
```

## Reference

```
usage: vidcat [-h] [-r {auto,braille,quadrants,sextants,ascii,sixel,kitty}]
              [-w WIDTH] [-H HEIGHT] [--frames FRAMES] [--every EVERY]
              [--max-frames MAX_FRAMES] [--dither] [--contrast] [--invert]
              [--grayscale] [--no-color] [-o OUTPUT] [--delay DELAY]
              [--play] [--asciinema FILE] [--fps FPS] [--title TITLE]
              [video]

Display video frames in the terminal using dapple

positional arguments:
  video                 Video file to display

options:
  -r, --renderer        Renderer to use (default: auto)
  -w, --width           Output width in characters
  -H, --height          Output height in characters
  --frames              Frame selection (e.g., '1-10', '1,5,10', '-5', '100-')
  --every               Extract interval (e.g., '1s', '30s', '1m')
  --max-frames          Maximum frames to extract (default: 10)
  --dither              Apply Floyd-Steinberg dithering
  --contrast            Apply auto-contrast
  --invert              Invert colors
  --grayscale           Force grayscale output
  --no-color            Disable color output
  -o, --output          Output file (default: stdout)
  --delay               Delay between frames in seconds

playback:
  --play                In-place playback (ANSI cursor movement, requires TTY)
  --asciinema FILE      Export to asciinema .cast file
  --fps                 Playback FPS for --play and --asciinema (default: 10)
  --title               Title for asciinema recording
```
