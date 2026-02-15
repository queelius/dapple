# Charts API

`dapple.charts` provides character-dimension wrappers around vizlib's chart primitives. Specify width and height in terminal characters instead of pixels.

## Functions

```python
from dapple.charts import sparkline, line_plot, bar_chart, histogram, heatmap
from dapple import braille
```

### sparkline

```python
chart = sparkline([1, 4, 2, 8, 3, 7], width=40, height=4)
chart.out(braille)
```

### line_plot

```python
chart = line_plot(y=[1, 4, 2, 8, 3, 7], width=60, height=20)
chart.out(braille)
```

### bar_chart

```python
chart = bar_chart(["A", "B", "C"], [10, 25, 15], width=60, height=20)
chart.out(braille)
```

### histogram

```python
import numpy as np
chart = histogram(np.random.randn(1000), width=60, height=20, bins=30)
chart.out(braille)
```

### heatmap

```python
import numpy as np
data = np.random.rand(10, 10)
chart = heatmap(data, width=40, height=20)
chart.out(braille)
```

All functions default to terminal width when `width` is omitted. Charts are sized for braille rendering (2x4 cell dimensions) but work with any renderer.
