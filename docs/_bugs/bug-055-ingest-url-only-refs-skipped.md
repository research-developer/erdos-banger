# BUG-055: Ingest Skips URL-Only References (No PDF Download)

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-30
**Fixed:** 2026-01-31
**Commit:** `005dc83`
**Component:** `erdos ingest`

## Summary

References added with `--url` (pointing directly to a PDF) are not processed by `erdos ingest`. The pipeline only handles:
- arXiv IDs → downloads LaTeX source
- DOIs → looks up metadata via OpenAlex/Crossref

URL-only references are silently skipped, even when `--pdf` flag is provided.

## Steps to Reproduce

```bash
# 1. Add a URL-only reference (pointing to a PDF)
uv run erdos refs add 74 \
  --url "https://korandi.org/docs/misc/setsgraphsnumbers/setsgraphsnumbers14.pdf" \
  --key "erdos-gyori-1991-edges-bipartite" \
  --citation "Erdos, Gyori (1991) - How Many Edges to Make Triangle-Free Bipartite?"

# 2. Verify it was added
uv run erdos refs problem 74 | grep erdos-gyori
# Shows: erdos-gyori-1991-edges-bipartite with citation but no DOI/arXiv

# 3. Run ingest with PDF flag
uv run erdos ingest 74 --pdf --force

# 4. Check manifest - URL reference is NOT in the manifest
grep "erdos-gyori-1991" literature/manifests/0074.yaml
# No output - reference was skipped
```

## Expected Behavior

When `--pdf` is enabled and a reference has a URL pointing to a PDF:
1. Download the PDF to `literature/cache/pdf/<key>.pdf`
2. Convert PDF to markdown via marker
3. Store extract in `literature/extracts/pdf/<problem_id>/<key>.md`
4. Add entry to manifest

## Actual Behavior

URL-only references are silently skipped. No download, no conversion, no manifest entry.

## Root Cause

The ingest pipeline in `src/erdos/core/ingest/` filters references by:
1. Has arXiv ID → process via arXiv download
2. Has DOI → process via OpenAlex/Crossref lookup
3. Otherwise → skip

There's no code path for "has URL but no DOI/arXiv" → download PDF directly.

## Impact

- Cannot ingest papers that only exist as PDFs on academic websites
- Cannot ingest conference proceedings without DOIs
- Cannot ingest older Erdos papers from renyi.hu/~p_erdos/ archive
- Blocks research on Problem 74 (need Erdos-Gyori 1991 paper)

## Proposed Fix

Add a third code path in the ingest pipeline:

```python
if ref.arxiv_id:
    # existing arXiv path
elif ref.doi:
    # existing DOI path
elif ref.url and ref.url.endswith('.pdf'):
    # NEW: direct PDF download path
    pdf_path = download_pdf(ref.url, cache_dir)
    if pdf_enabled:
        extract = convert_pdf_to_markdown(pdf_path)
        # ...
```

## Workaround

Manual download and conversion:

```bash
# 1. Download PDF manually
curl -sL "https://korandi.org/docs/misc/setsgraphsnumbers/setsgraphsnumbers14.pdf" \
  -o literature/cache/pdf/erdos-gyori-1991.pdf

# 2. Convert with marker
uv run marker_single literature/cache/pdf/erdos-gyori-1991.pdf \
  --output_dir literature/extracts/pdf/0074/

# 3. Manually update manifest (tedious)
```

## Resolution

Added URL-only PDF reference handling to `process_all_references()`:

1. Added `_is_url_only_pdf_ref()` helper to detect URL-only PDF references
2. Added `_process_url_only_pdf_reference()` to create a minimal `ReferenceRecord` with synthetic `openalex_id` and process via `_build_manifest_entry_with_pdf()`
3. Updated `_error_manifest_entry()` to handle references without DOI/arXiv by using synthetic `openalex_id`

**Changes:**
- `src/erdos/core/ingest/fetch.py`: Added URL-only PDF processing path
- `tests/unit/ingest/test_fetch.py`: Added 3 tests for URL-only handling
- `docs/_debt/debt-122-ingest-fetch-module-size.md`: Created debt deck for module size (568 LOC, 14% over threshold)

**Note:** Module size increased to 571 LOC (threshold: 500). Exempted via DEBT-122 as the complexity is justified for feature completeness.

## Related

- BUG-039: Ingest cannot discover papers (different issue - this is about URL refs being skipped)
- SPEC-036: Lead enrichment pipeline (may need update to cover URL-only refs)
- DEBT-122: Ingest fetch module size exemption
- Problem 74 research blocked on Erdos-Gyori 1991 paper
