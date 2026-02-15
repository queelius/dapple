# Error Hardening Design

**Date:** 2026-02-14
**Status:** Approved

## Problem

Testing the dapple extras CLIs revealed several error handling gaps:

1. **csvcat**: `--delimiter '\t'` fails — passes literal `\t` (2 chars) instead of tab
2. **datacat**: `--plot line` gives misleading error — doesn't suggest available fields
3. **funcat**: No `KeyboardInterrupt` handling — shows stack trace on Ctrl+C
4. **pdfcat**: Silent `except Exception:` swallows PDF open and page render failures
5. **mdcat**: Image render failures hidden behind placeholder with no stderr note
6. **vidcat**: `parse_frames()` can raise unhandled ValueError; ffmpeg stderr can be verbose
7. **imgcat**: ImportError caught at wrong scope level
8. **All tools**: Inconsistent error message formatting

## Approach

Shared utilities in `common.py` + per-tool fixes. Each tool keeps its own `main()` but uses shared helpers for common operations.

## Shared Utilities (`common.py`)

### `unescape_delimiter(s: str) -> str`
Convert escape sequences: `\t` -> tab, `\n` -> newline, `\\` -> backslash.
Used by csvcat before passing delimiter to csv.reader.

### `resolve_column(available: list[str], requested: str) -> str`
Validate column name exists. Raises `ValueError` with available columns hint.
Used by csvcat for --plot, --bar, --spark, --sort, --cols.

### `resolve_field(records: list[dict], field_path: str) -> str`
Validate field path exists in at least one JSONL record. Raises `ValueError` with available top-level keys.
Used by datacat for --plot, --spark, --bar.

## Per-Tool Fixes

| Tool | Fix |
|------|-----|
| csvcat | `unescape_delimiter()` on --delimiter; `resolve_column()` before plot/sort/select |
| datacat | `resolve_field()` before plot ops; improve JSON parse error messages |
| funcat | Add KeyboardInterrupt (exit 130); wrap individual expression eval in try/except |
| imgcat | Restructure ImportError to report clearly at first use |
| pdfcat | Replace silent except with stderr warnings for failed pages |
| mdcat | Add stderr note when image rendering fails (keep placeholder) |
| vidcat | Wrap parse_frames() int conversion; truncate verbose ffmpeg stderr |

## Error Format Standard

All tools: `"Error: {filename}: {message}"` to stderr. No raw stack traces.

## Testing

Error-path tests for each tool covering bad input, missing files, invalid fields/columns.
