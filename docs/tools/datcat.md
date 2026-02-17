# datcat -- Structured Data Viewer

View structured data (JSON, JSONL, CSV, TSV) in the terminal with tree, table,
and syntax-colored display modes. Includes dot-path querying and chart
visualization for numeric fields. datcat is the unified data viewer -- it
handles all tabular and hierarchical data formats in one tool.

## Installation

```bash
pip install dapple[datcat]
```

No additional dependencies are required. datcat uses dapple's vizlib for
charting.

## Usage

### Basic Display

```bash
# View a JSON file (tree view by default)
datcat config.json

# View a JSONL file (one JSON object per line)
datcat events.jsonl

# View a CSV file (formatted table)
datcat data.csv

# View a TSV file (auto-detected)
datcat data.tsv

# Read from stdin
curl -s https://api.example.com/data | datcat
```

datcat auto-detects the format from the file extension (`.json`, `.jsonl`,
`.csv`, `.tsv`) or by inspecting the content when reading from stdin.

### Display Modes

```bash
# Tree view (default) -- box-drawing characters
datcat config.json --tree

# Syntax-colored JSON
datcat config.json --json

# Disable colors
datcat config.json --json --no-color

# Table view (JSONL records flattened to columns)
datcat events.jsonl --table
```

The table mode flattens JSONL records into aligned columns with type-based
coloring (numeric values in cyan, booleans in yellow, nulls dimmed).

```bash
# Table with rotating column colors
datcat events.jsonl --table --cycle-color
```

### Dot-path Queries

Extract nested values using dot-path notation:

```bash
# Query a specific field
datcat config.json .database.host

# Query nested arrays
datcat data.json .users

# Query within JSONL records
datcat events.jsonl .metadata.timestamp
```

### Row Limiting (JSONL)

```bash
# Show first N records
datcat events.jsonl --head 10

# Show last N records
datcat events.jsonl --tail 5
```

### Output to File

```bash
datcat config.json --json -o output.txt
```

## Chart Visualization

datcat can visualize numeric fields from JSONL data (arrays of records)
using four chart modes. These are mutually exclusive.

### Sparkline

A compact line chart from a numeric field:

```bash
datcat metrics.jsonl --spark value
datcat events.jsonl --spark response_time
```

### Line Plot

A line plot with optional baseline axis:

```bash
datcat metrics.jsonl --plot value
datcat sensors.jsonl --plot temperature -w 100 -H 20
```

### Bar Chart

Category counts from a field:

```bash
datcat events.jsonl --bar status
datcat logs.jsonl --bar level
```

### Histogram

Distribution of a numeric field:

```bash
datcat metrics.jsonl --histogram latency
datcat events.jsonl --histogram duration -w 80
```

### Chart Options

```bash
# Renderer selection (default: braille)
datcat metrics.jsonl --spark value -r quadrants
datcat events.jsonl --bar status -r sextants

# Size control
datcat metrics.jsonl --spark value -w 80 -H 15

# Color
datcat metrics.jsonl --spark value --color green
datcat metrics.jsonl --plot value --color "#ff6600"

# Output to file
datcat metrics.jsonl --spark value -o chart.txt
```

## CSV / TSV Mode

When given a `.csv` or `.tsv` file, datcat displays a formatted table and
supports the same chart modes as JSON/JSONL data.

### Table Display

```bash
# Formatted table (default for CSV)
datcat data.csv

# Select columns
datcat data.csv --cols name,score,department

# Sort by column
datcat data.csv --sort score
datcat data.csv --sort score --desc

# Limit rows
datcat data.csv --head 10
datcat data.csv --tail 5
```

### Delimiter Control

```bash
# Explicit delimiter
datcat -d ";" data.csv
datcat -d $'\t' data.tsv

# First row is data, not headers
datcat --no-header data.csv
```

### CSV Charts

All chart modes work with CSV columns:

```bash
datcat data.csv --spark revenue           # sparkline of a column
datcat data.csv --plot revenue            # line plot
datcat data.csv --bar department          # bar chart of categories
datcat data.csv --histogram age           # histogram
datcat data.csv --heatmap "q1,q2,q3"     # heatmap of multiple columns
```

## Examples

### API Response Inspection

```bash
# View API response structure
curl -s https://api.example.com/users | datcat

# Extract specific fields
curl -s https://api.example.com/users | datcat .data

# View as table
curl -s https://api.example.com/users | datcat .data --table
```

### Log Analysis

```bash
# Visualize error rates
cat app.jsonl | datcat --bar level

# Sparkline of response times
cat access.jsonl | datcat --spark response_ms

# First 20 records as a table
cat events.jsonl | datcat --table --head 20
```

### Metrics Dashboard

```bash
# Sparkline of CPU usage
datcat cpu_metrics.jsonl --spark usage --color cyan

# Histogram of latency distribution
datcat request_logs.jsonl --histogram latency_ms -w 100
```

## Python API

datcat's parsing and display functions can be used programmatically:

```python
from dapple.extras.datcat.datcat import (
    read_json, format_tree, format_json,
    flatten_to_table, dot_path_query,
    extract_field_values, extract_field_categories,
)

# Parse JSON/JSONL text
data = read_json(open("data.jsonl").read())

# Query nested fields
result = dot_path_query(data, ".metadata.timestamp")

# Display as tree
print(format_tree(data))

# Display as colored JSON
print(format_json(data, colorize=True))

# Flatten JSONL to table
headers, rows = flatten_to_table(data)

# Extract numeric values for custom visualization
values = extract_field_values(data, "response_time")
```

## Entry Point

```
datcat = dapple.extras.datcat.cli:main
```

## Reference

```
usage: datcat [-h] [--table] [--tree] [--json] [--no-color] [--cycle-color]
               [--head N] [--tail N] [--cols COLS] [--sort COL] [--desc]
               [-d DELIM] [--no-header]
               [--plot PATH | --spark PATH | --bar PATH | --histogram PATH
                | --heatmap COLS]
               [-r RENDERER] [-w WIDTH] [-H HEIGHT] [-o FILE] [--color COLOR]
               [file] [query]

Terminal structured data viewer (JSON/JSONL/CSV/TSV) with visualization modes

positional arguments:
  file                  Data file to display (reads stdin if omitted)
  query                 Dot-path query (e.g. .database.host)

display options:
  --table               Flatten records to a table
  --tree                Show tree view with box-drawing characters (default for JSON)
  --json                Show syntax-colored JSON
  --no-color            Disable syntax coloring
  --cycle-color         Color each column with a rotating palette (table mode)
  --head N              Show first N records
  --tail N              Show last N records

csv options:
  --cols COLS           Select columns (comma-separated)
  --sort COL            Sort by column
  --desc                Sort descending (with --sort)
  -d, --delimiter       CSV delimiter (default: auto-detect)
  --no-header           First row is data, not headers

plot modes (mutually exclusive):
  --plot PATH           Line plot of a numeric field
  --spark PATH          Sparkline of a numeric field
  --bar PATH            Bar chart of category counts
  --histogram PATH      Histogram of a numeric field
  --heatmap COLS        Heatmap of multiple numeric columns (comma-separated)

plot options:
  -r, --renderer        Renderer (default: braille)
  -w, --width           Chart width in terminal characters
  -H, --height          Chart height in terminal characters
  -o, --output          Write output to file instead of stdout
  --color               Chart color (name or #hex)
```
