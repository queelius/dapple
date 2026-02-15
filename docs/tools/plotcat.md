# plotcat -- Faceted Data Plots

Create faceted charts from CSV or JSONL data, grouped by a column.

## Installation

```bash
pip install dapple[plotcat]
```

No additional dependencies beyond dapple core.

## Usage

```bash
plotcat data.csv --facet region --plot line -x date -y sales
plotcat data.jsonl --facet category -q .metrics --plot bar
plotcat sales.csv --facet quarter --plot histogram -y revenue
```

Groups data by the `--facet` column, creates a chart per group, and arranges them in a grid.
