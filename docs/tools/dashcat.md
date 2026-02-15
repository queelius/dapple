# dashcat -- YAML-Driven Dashboard

Compose terminal dashboards from a YAML layout file.

## Installation

```bash
pip install dapple[dashcat]
```

Adds pyyaml dependency.

## Usage

```bash
dashcat layout.yaml
dashcat --preset system    # built-in system metrics
```

## Layout Format

```yaml
rows:
  - cells:
    - type: sparkline
      source: metrics.jsonl
      query: .cpu
      title: CPU
    - type: sparkline
      source: metrics.jsonl
      query: .memory
      title: Memory
  - cells:
    - type: bar_chart
      source: sales.csv
      x: region
      y: revenue
      title: Revenue by Region
```

Supported cell types: `sparkline`, `line_plot`, `bar_chart`, `histogram`, `heatmap`.
