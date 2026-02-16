# Example Data for Testing Dapple

A mixed collection of files for testing dapple's rendering and extras.

## Quick test commands

```bash
# Images
imgcat examples/landscape.jpg
imgcat examples/starry_night.jpg
imgcat examples/transparency.png
imgcat examples/lena.png

# Video
vidcat examples/bunny.mp4

# CSV / TSV
csvcat examples/sample.csv
csvcat examples/weather.csv --bar temp_c
csvcat examples/weather.csv --spark rainfall_mm
csvcat examples/stocks.csv --plot AAPL,MSFT,GOOGL
csvcat examples/sales.tsv

# JSON / JSONL
datcat examples/config.json
datcat examples/users.json
datcat examples/metrics.jsonl --plot latency
datcat examples/events.jsonl --bar event
datcat examples/sensors.jsonl --plot value

# Markdown
mdcat examples/readme.md
```

## File inventory

| File | Format | Size | Good for testing |
|------|--------|------|------------------|
| landscape.jpg | JPEG | 800x600 | Standard photo, color |
| photo2.jpg | JPEG | 640x480 | Different aspect ratio |
| photo3.jpg | JPEG | 1024x768 | Larger image |
| square.jpg | JPEG | 400x400 | Square aspect |
| portrait.jpg | JPEG | 200x300 | Portrait orientation |
| starry_night.jpg | JPEG | 600x475 | Rich color palette |
| ant_macro.jpg | JPEG | 320x213 | Small, detailed |
| lena.png | PNG | 512x512 | Classic test image |
| transparency.png | PNG | 800x600 | RGBA with alpha channel |
| bunny.mp4 | MP4 | ~770KB | Big Buck Bunny clip |
| movie.mp4 | MP4 | ~310KB | Short clip |
| sample.csv | CSV | 10 rows | Names, scores, departments |
| weather.csv | CSV | 30 rows | Multi-city weather data |
| stocks.csv | CSV | 20 rows | Daily stock prices, 5 tickers |
| sales.tsv | TSV | 5 rows | Quarterly sales |
| config.json | JSON | nested | App configuration |
| users.json | JSON | array | User records |
| metrics.jsonl | JSONL | 15 rows | API latency time series |
| events.jsonl | JSONL | 16 rows | Web analytics events |
| sensors.jsonl | JSONL | 15 rows | IoT sensor readings |
