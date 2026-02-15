# storycat -- Video Storyboard Grid

Extract video frames and display them as a storyboard grid.

## Installation

```bash
pip install dapple[storycat]
```

Requires ffmpeg.

## Usage

```bash
storycat video.mp4 --cols 5 --every 10s
storycat video.mp4 --frames 1-20 --cols 4
storycat clip.mp4 -r sextants -w 120
```

Each frame is shown in a titled grid cell with its timestamp. Uses vidcat's frame extraction internally.
