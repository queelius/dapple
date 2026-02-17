"""datcat - Terminal data viewer with visualization modes.

Unified viewer for structured data: JSON, JSONL, CSV, and TSV.
Pretty-prints with syntax coloring, supports dot-path queries,
tree views, table display, and chart visualization via
vizlib/dapple renderers.
"""

from dapple.extras.datcat.cli import main

__all__ = ["main"]
