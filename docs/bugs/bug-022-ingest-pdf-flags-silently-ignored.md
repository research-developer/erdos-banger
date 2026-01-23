# BUG-022: `erdos ingest --pdf` Flags Silently Ignored

**Priority:** P2 (Medium - Feature partially broken, workaround exists)

**Status:** Open

**Found:** 2026-01-23

## Description

The `erdos ingest` command advertises `--pdf`, `--pdf-converter`, and `--use-llm` flags for PDF conversion integration (SPEC-019), but these flags are **silently ignored**. The feature was scaffolded but never wired through the orchestration layer.

## Steps to Reproduce

```bash
# Pick a problem that includes at least one DOI-only reference where the chosen
# metadata source can supply an open-access `pdf_url` (e.g., via OpenAlex).
#
# Example (dataset-dependent):
uv run erdos ingest 316 --source openalex --pdf

# Observe: No PDF conversion occurs
# The flags are accepted but have no effect
```

## Expected Behavior

When `--pdf` is passed:
1. Non-arXiv references with open-access PDFs should be downloaded to `literature/cache/pdf/{reference_id}/paper.pdf`
2. PDFs should be converted using Marker (or pdfplumber)
3. Extracted text should be saved to `literature/extracts/pdf/{reference_id}/fulltext.md`
4. The manifest entry should reflect cached/extracted state (cache/extract paths)

## Actual Behavior

The `--pdf` flag is:
1. ✅ Parsed by CLI (`commands/ingest.py:217-234`)
2. ✅ Stored in `IngestOptions` (`core/ingest/app.py:60-63`)
3. ❌ **Never passed** to `run_single_ingestion()` or `create_batch_process_fn()`
4. ❌ **Not accepted** by `ingest_problem_references()` function signature

The flags have **zero effect** on execution.

## Root Cause

The orchestration layer (`core/ingest/app.py`) was not updated to pass PDF options to the service layer:

**app.py lines 147-159 (run_single_ingestion):**
```python
return ingest_problem_references(
    options.problem_id,
    repo=repo,
    repo_root=repo_root,
    force=options.force,
    no_download=options.no_download,
    # ...
    # MISSING: pdf=options.pdf,
    # MISSING: pdf_converter=options.pdf_converter,
    # MISSING: use_llm=options.use_llm,
)
```

**service.py lines 293-306 (ingest_problem_references signature):**
```python
def ingest_problem_references(
    problem_id: int,
    *,
    # ...NO PDF PARAMETERS ACCEPTED...
) -> CLIOutput:
```

### Related Dead Code

`core/literature_paths.py` contains three unused functions that were scaffolded for this feature:
- `get_pdf_cache_path()` → `literature/cache/pdf/{reference_id}/paper.pdf`
- `get_pdf_extract_path()` → `literature/extracts/pdf/{reference_id}/fulltext.md`
- `sanitize_reference_id()` → Sanitizes DOI/arXiv IDs for filesystem

These are **NOT dead code to be removed** — they are part of the incomplete implementation.

## Proposed Fix

### Phase 1: Wire through existing scaffolding

1. Add PDF parameters to `ingest_problem_references()` signature:
   ```python
   def ingest_problem_references(
       # ...existing params...
       pdf: bool = False,
       pdf_converter: str = "marker",
       use_llm: bool = False,
   ) -> CLIOutput:
   ```

2. Update `run_single_ingestion()` and `create_batch_process_fn()` to pass options:
   ```python
   return ingest_problem_references(
       # ...existing args...
       pdf=options.pdf,
       pdf_converter=options.pdf_converter,
       use_llm=options.use_llm,
   )
   ```

3. Implement PDF conversion in `ingest_problem_references()`:
   - Check if reference has open-access PDF URL
   - Download to `get_pdf_cache_path(reference_id)`
   - Convert using `convert_pdf()` from `core/pdf/converter.py`
   - Save to `get_pdf_extract_path(reference_id)`

## Workaround

Use `erdos convert` for manual PDF conversion:
```bash
# Download PDF manually
curl -o paper.pdf https://example.com/paper.pdf

# Convert to markdown
uv run erdos convert paper.pdf --output paper.md
```

## Impact

- **User Impact:** Feature advertised in `--help` doesn't work
- **Data Impact:** None (no data corruption, feature just doesn't execute)
- **Workaround Exists:** Yes (manual `erdos convert`)

## References

- SPEC-019: `docs/_archive/specs/spec-019-pdf-conversion.md` (Section 3.1, 5.2)
- DEBT-079: `docs/debt/debt-079-dead-code-literature-paths.md` (superseded by this bug)
- Related commit: b32a91d (SPEC-019 implementation)

## Detection Method

Discovered via Vulture dead code analysis, which flagged `literature_paths.py` functions as unused. Investigation revealed the flags were scaffolded but never wired in.
