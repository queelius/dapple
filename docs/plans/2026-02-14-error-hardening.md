# Error Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden all 7 dapple extras CLIs with graceful error handling, informative messages, and no stack traces.

**Architecture:** Add shared error utilities to `dapple/extras/common.py`, then apply them across all extras. Each tool keeps its own `main()` but uses shared helpers for delimiter parsing, field validation, and available-field hints.

**Tech Stack:** Python stdlib only (no new dependencies). pytest for error-path tests.

---

### Task 1: Add shared error utilities to common.py

**Files:**
- Modify: `dapple/extras/common.py` (after line 122)
- Test: `tests/test_common.py`

**Step 1: Write failing tests for the new utilities**

```python
# In tests/test_common.py — add these test classes

class TestUnescapeDelimiter:
    def test_tab(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter(r"\t") == "\t"

    def test_newline(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter(r"\n") == "\n"

    def test_backslash(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter("\\\\") == "\\"

    def test_plain_char(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter(",") == ","

    def test_pipe(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter("|") == "|"

    def test_already_tab(self):
        from dapple.extras.common import unescape_delimiter
        assert unescape_delimiter("\t") == "\t"


class TestAvailableFields:
    def test_dict_records(self):
        from dapple.extras.common import available_fields
        records = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
        fields = available_fields(records)
        assert "a" in fields
        assert "b" in fields
        assert "c" in fields

    def test_empty_records(self):
        from dapple.extras.common import available_fields
        assert available_fields([]) == []

    def test_non_dict_records(self):
        from dapple.extras.common import available_fields
        assert available_fields([1, 2, 3]) == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_common.py::TestUnescapeDelimiter tests/test_common.py::TestAvailableFields -v`
Expected: FAIL with ImportError

**Step 3: Implement the utilities**

Add to `dapple/extras/common.py` after the `apply_preprocessing` function:

```python
def unescape_delimiter(s: str) -> str:
    """Unescape common escape sequences in a delimiter string.

    Handles \\t (tab), \\n (newline), \\\\ (backslash).
    Single characters and already-unescaped values pass through unchanged.
    """
    replacements = {"\\t": "\t", "\\n": "\n", "\\\\": "\\"}
    for escaped, unescaped in replacements.items():
        s = s.replace(escaped, unescaped)
    return s


def available_fields(records: list) -> list[str]:
    """Collect all unique top-level keys from a list of dicts.

    Returns sorted list of field names. Returns empty list if records
    are empty or not dicts.
    """
    keys: set[str] = set()
    for rec in records:
        if isinstance(rec, dict):
            keys.update(rec.keys())
    return sorted(keys)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_common.py::TestUnescapeDelimiter tests/test_common.py::TestAvailableFields -v`
Expected: PASS

**Step 5: Commit**

```
feat: add unescape_delimiter and available_fields utilities to common.py
```

---

### Task 2: Fix csvcat delimiter handling

**Files:**
- Modify: `dapple/extras/csvcat/cli.py` (around line 233 where delimiter is passed to read_csv)
- Test: `tests/test_csvcat.py`

**Step 1: Write failing test**

```python
# In tests/test_csvcat.py — add to existing tests

class TestDelimiterUnescape:
    def test_backslash_t_parsed_as_tab(self, tmp_path):
        """--delimiter '\\t' should work as tab delimiter."""
        tsv = tmp_path / "data.tsv"
        tsv.write_text("a\tb\n1\t2\n")
        result = subprocess.run(
            ["csvcat", str(tsv), "--delimiter", r"\t"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "a" in result.stdout
        assert "b" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_csvcat.py::TestDelimiterUnescape -v`
Expected: FAIL — delimiter '\t' is 2 chars, causes error

**Step 3: Implement the fix**

In `dapple/extras/csvcat/cli.py`, import `unescape_delimiter` and apply it before passing to `read_csv`:

```python
from dapple.extras.common import unescape_delimiter
```

At the point where delimiter is used (around line 233), add:
```python
delimiter = unescape_delimiter(args.delimiter) if args.delimiter else None
```

**Step 4: Run tests**

Run: `pytest tests/test_csvcat.py -v`
Expected: All PASS

**Step 5: Commit**

```
fix: csvcat accepts \\t as tab delimiter
```

---

### Task 3: Fix datacat field-not-found error messages

**Files:**
- Modify: `dapple/extras/datacat/datacat.py` (lines 380-381, 415-416)
- Test: `tests/test_datacat.py`

**Step 1: Write failing test**

```python
# In tests/test_datacat.py

class TestFieldNotFoundMessage:
    def test_plot_suggests_available_fields(self, tmp_path):
        """--plot with wrong field should list available fields."""
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"latency": 100, "status": "ok"}\n')
        result = subprocess.run(
            ["datacat", str(jsonl), "--plot", "nonexistent"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "nonexistent" in result.stderr
        assert "latency" in result.stderr  # should suggest available fields

    def test_spark_suggests_available_fields(self, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"latency": 100, "region": "us"}\n')
        result = subprocess.run(
            ["datacat", str(jsonl), "--spark", "bogus"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "latency" in result.stderr
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_datacat.py::TestFieldNotFoundMessage -v`
Expected: FAIL — current message doesn't include available fields

**Step 3: Implement the fix**

In `dapple/extras/datacat/datacat.py`, modify `extract_field_values()` (line 380-381) and `extract_field_categories()` (line 415-416) to include available fields in the error:

```python
# In extract_field_values, replace line 380-381:
    if not values:
        from dapple.extras.common import available_fields
        fields = available_fields(records)
        hint = f" Available fields: {', '.join(fields)}" if fields else ""
        raise ValueError(
            f"No numeric values found at path '{path}'.{hint}"
        )

# In extract_field_categories, replace line 415-416:
    if not raw_values:
        from dapple.extras.common import available_fields
        fields = available_fields(records)
        hint = f" Available fields: {', '.join(fields)}" if fields else ""
        raise ValueError(f"No values found at path '{path}'.{hint}")
```

**Step 4: Run tests**

Run: `pytest tests/test_datacat.py -v`
Expected: All PASS

**Step 5: Commit**

```
fix: datacat shows available fields when field path not found
```

---

### Task 4: Fix funcat missing KeyboardInterrupt and per-expression error handling

**Files:**
- Modify: `dapple/extras/funcat/funcat.py` (lines 676-678)
- Test: `tests/test_funcat.py`

**Step 1: Write failing tests**

```python
# In tests/test_funcat.py

class TestErrorHandling:
    def test_bad_expression_reports_which(self):
        """Bad expression should identify which expression failed."""
        result = subprocess.run(
            ["funcat", "sin(x)", "INVALID(x)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "INVALID" in result.stderr

    def test_exit_code_on_error(self):
        result = subprocess.run(
            ["funcat", "+++"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert result.stderr.strip()  # should have error message
```

**Step 2: Run tests to verify behavior**

Run: `pytest tests/test_funcat.py::TestErrorHandling -v`

**Step 3: Implement the fix**

In `dapple/extras/funcat/funcat.py`, add `KeyboardInterrupt` handling before the generic Exception handler (after line 675):

```python
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

Also wrap individual expression evaluation (inside the expression processing loop) in try/except to report which expression failed, rather than halting all processing.

**Step 4: Run tests**

Run: `pytest tests/test_funcat.py -v`
Expected: All PASS

**Step 5: Commit**

```
fix: funcat handles KeyboardInterrupt, reports which expression failed
```

---

### Task 5: Fix pdfcat silent exception handlers

**Files:**
- Modify: `dapple/extras/pdfcat/pdfcat.py` (lines 119-122, 139-150)
- Test: `tests/test_pdfcat.py`

**Step 1: Write failing test**

```python
# In tests/test_pdfcat.py

class TestErrorMessages:
    def test_corrupt_pdf_reports_error(self, tmp_path):
        """Corrupt PDF should produce error message, not silent failure."""
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_text("this is not a PDF")
        result = subprocess.run(
            ["pdfcat", str(bad_pdf)],
            capture_output=True, text=True,
        )
        # Should report something, not silently produce empty output
        assert result.returncode != 0 or "error" in result.stderr.lower() or "no pages" in result.stderr.lower()
```

**Step 2: Run test**

Run: `pytest tests/test_pdfcat.py::TestErrorMessages -v`

**Step 3: Implement the fix**

In `render_pdf_to_images()` (`pdfcat.py` lines 119-122), replace silent except with stderr warning:

```python
    try:
        pdf = pdfium.PdfDocument(path)
    except Exception as e:
        print(f"Error: {path.name}: Failed to open PDF: {e}", file=sys.stderr)
        return RenderResult()
```

For page render failures (lines 139-150):

```python
        except Exception as e:
            print(
                f"Warning: {path.name}: Failed to render page {page_num}: {e}",
                file=sys.stderr,
            )
            continue
```

**Step 4: Run tests**

Run: `pytest tests/test_pdfcat.py -v`
Expected: All PASS

**Step 5: Commit**

```
fix: pdfcat reports PDF open and page render failures instead of silent skip
```

---

### Task 6: Fix mdcat image render error reporting

**Files:**
- Modify: `dapple/extras/mdcat/mdcat.py` (around lines 181-213)
- Test: `tests/test_mdcat.py`

**Step 1: Write test (verify current behavior)**

```python
# In tests/test_mdcat.py

class TestImageErrors:
    def test_broken_image_ref_warns(self, tmp_path):
        """Markdown with broken image ref should warn, not crash."""
        md = tmp_path / "doc.md"
        md.write_text("# Title\n\n![img](nonexistent.png)\n")
        result = subprocess.run(
            ["mdcat", str(md), "--images"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0  # should not crash
```

**Step 2: Run test**

Run: `pytest tests/test_mdcat.py::TestImageErrors -v`

**Step 3: Implement the fix**

In the `DappleImageItem.__rich_console__()` exception handler, add a stderr warning when image rendering fails so user knows what happened:

```python
        except Exception as e:
            print(
                f"Warning: Failed to render image: {e}",
                file=sys.stderr,
            )
            yield Text(f"[image: {self.path}]")
```

**Step 4: Run tests**

Run: `pytest tests/test_mdcat.py -v`
Expected: All PASS

**Step 5: Commit**

```
fix: mdcat warns on stderr when inline image rendering fails
```

---

### Task 7: Fix vidcat frame parsing and ffmpeg error handling

**Files:**
- Modify: `dapple/extras/vidcat/vidcat.py`
- Test: `tests/test_vidcat.py`

**Step 1: Write failing test**

```python
# In tests/test_vidcat.py

class TestParseErrors:
    def test_bad_frame_range(self):
        """Invalid frame range should produce clear error."""
        result = subprocess.run(
            ["vidcat", "dummy.mp4", "--frames", "abc-def"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "frame" in result.stderr.lower() or "invalid" in result.stderr.lower()

    def test_missing_video_file(self):
        """Missing video file should report clearly."""
        result = subprocess.run(
            ["vidcat", "nonexistent.mp4"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()
```

**Step 2: Run tests**

Run: `pytest tests/test_vidcat.py::TestParseErrors -v`

**Step 3: Implement the fix**

In `parse_frames()`, wrap int conversions in try/except:

```python
try:
    start = int(start_str)
except ValueError:
    raise ValueError(f"Invalid frame number: '{start_str}' in range '{frames}'")
```

For ffmpeg subprocess errors, truncate verbose stderr:
```python
except subprocess.CalledProcessError as e:
    stderr_msg = (e.stderr or "")[:200]  # truncate verbose ffmpeg output
    raise RuntimeError(f"ffmpeg failed: {stderr_msg}")
```

**Step 4: Run tests**

Run: `pytest tests/test_vidcat.py -v`
Expected: All PASS

**Step 5: Commit**

```
fix: vidcat validates frame ranges and truncates ffmpeg errors
```

---

### Task 8: Fix imgcat ImportError scope

**Files:**
- Modify: `dapple/extras/imgcat/imgcat.py` (lines 240-264)
- Test: `tests/test_imgcat.py`

**Step 1: Write test**

```python
# In tests/test_imgcat.py

class TestErrorHandling:
    def test_nonexistent_file(self):
        result = subprocess.run(
            ["imgcat", "nonexistent.png"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()
```

**Step 2: Run test**

Run: `pytest tests/test_imgcat.py::TestErrorHandling -v`

**Step 3: Implement the fix**

Move the ImportError catch inside the per-image loop so one import failure is reported as an error for that image rather than crashing the entire batch. The error message should say what's missing:

```python
    except ImportError as e:
        errors.append(f"{image_path.name}: Missing dependency: {e}")
        continue
```

**Step 4: Run tests**

Run: `pytest tests/test_imgcat.py -v`
Expected: All PASS

**Step 5: Commit**

```
fix: imgcat reports ImportError per-image instead of halting batch
```

---

### Task 9: Full test suite verification

**Step 1: Run full test suite with coverage**

Run: `pytest --cov=dapple --cov-report=term-missing`
Expected: All tests PASS, no regressions

**Step 2: Manual smoke test of error paths**

```bash
csvcat nonexistent.csv                      # file not found
csvcat examples/sample.csv --delimiter '\t' # unescape works
csvcat examples/sample.csv --plot bogus     # column not found, shows available
datacat examples/metrics.jsonl --plot line  # field hint
funcat "INVALID(x)"                        # expression error
pdfcat /dev/null                            # corrupt PDF warning
vidcat nonexistent.mp4                      # file not found
```

**Step 3: Commit any remaining fixes**

```
chore: error hardening smoke test fixes
```
