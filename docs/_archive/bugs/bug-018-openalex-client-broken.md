# BUG-018: OpenAlex Client Bugs (arXiv lookup + arXiv ID extraction)

**Status:** Fixed
**Priority:** P1
**Found:** 2026-01-21
**Found By:** Post-Ralph adversarial audit
**Fixed:** 2026-01-21
**Commit:** b2dcdfe

---

## Summary

The OpenAlex integration was unreliable for arXiv references because:

1. `OpenAlexClient.get_by_arxiv()` uses a **non-existent OpenAlex filter** (`ids.arxiv`).
2. `openalex_to_reference()` attempts to read `ids["arxiv"]`, but real OpenAlex payloads expose arXiv via
   `primary_location.landing_page_url` and (sometimes) via an arXiv DataCite DOI (`10.48550/...`) — **not** an `ids.arxiv` field.

This broke:
- `--source openalex` ingestion for arXiv-only references
- Any downstream logic/tests that expect `ReferenceRecord.arxiv_id` to be populated from OpenAlex

---

## Bug 1: Invalid `ids.arxiv` Filter

**Location (pre-fix):** `src/erdos/core/openalex_client.py` (pre-`b2dcdfe`)

**Broken code (pre-fix):**
```python
params = self._params(filter=f"ids.arxiv:{arxiv_id}")
```

**Evidence (OpenAlex docs):** The “Filter works” documentation lists supported identifier filters (`doi`, `ids.openalex`, `ids.pmid`, `ids.pmcid`, `ids.mag`) and does **not** include `ids.arxiv`.
Reference: https://docs.openalex.org/api-entities/works/filter-works

---

## Bug 2: arXiv ID Extraction Assumes Non-existent `ids["arxiv"]`

**Location (pre-fix):** `src/erdos/core/openalex_client.py` (pre-`b2dcdfe`)

**Why this fails:** OpenAlex “work object” `ids` contains fields like `doi`, `openalex`, `mag`, `pmid`, `pmcid` — not `arxiv`.
Reference: https://docs.openalex.org/api-entities/works/work-object#ids

**Live payload example (known arXiv paper):**

- DOI filter works:
```bash
curl -sS 'https://api.openalex.org/works?filter=doi:10.48550%2Farxiv.math%2F0404188&per-page=1' \
  | jq '.results[0].ids'
# => {"openalex": "...", "doi": "https://doi.org/10.48550/arxiv.math/0404188", "mag": "..."}
```

- The arXiv link is in `primary_location.landing_page_url`:
```bash
curl -sS 'https://api.openalex.org/works?filter=doi:10.48550%2Farxiv.math%2F0404188&per-page=1' \
  | jq '.results[0].primary_location.landing_page_url'
# => "http://arxiv.org/abs/math/0404188"
```

---

## Fix Implemented

### Option A (Recommended): arXiv ID → DataCite DOI → `get_by_doi()`

arXiv assigns DataCite DOIs in the form:
- Modern: `10.48550/arxiv.<YYMM.NNNNN>`
- Legacy: `10.48550/arxiv.<archive>/<YYMMNNN>`

So for an arXiv ID `math/0404188`:
`doi = "10.48550/arxiv.math/0404188"`

Implementation outline:
1. Strip version suffix (`vN`) from the arXiv ID.
2. Build DOI `10.48550/arxiv.{arxiv_id_clean}`.
3. Call `get_by_doi(doi)` (documented OpenAlex DOI lookup path).
4. Set `ref.arxiv_id = arxiv_id_clean` explicitly (don’t rely on OpenAlex payload shape).

This is deterministic and uses supported OpenAlex capabilities.

### Option B: Search fallback (only if Option A fails)

Use OpenAlex `search=` (fuzzy) to search for the arXiv URL, then select a candidate where
`primary_location.landing_page_url` matches the arXiv ID. This is less reliable because OpenAlex’s `search`
is not guaranteed to index URLs.

### Option C: Bypass OpenAlex for arXiv

If OpenAlex cannot reliably resolve arXiv, ingest can treat `arxiv_id` as an arXiv-first reference:
use `arXiv export API + e-print tarball` for metadata + text extraction, and reserve OpenAlex for DOI-only references.

---

## Test Fixes Implemented

1. Update unit tests to reflect real OpenAlex payload shape (no `ids["arxiv"]`).
2. Update `tests/integration/test_openalex_integration.py` to use a DOI/arXiv pair that OpenAlex demonstrably supports.
   Recommended stable choice: `math/0404188` (already used in this repo’s sample problems).
3. Keep the live integration tests under `@pytest.mark.requires_network` (not in CI), but ensure they pass when run:
   `uv run pytest tests/integration/test_openalex_integration.py -m requires_network`.

---

## Acceptance Criteria

1. [x] `get_by_arxiv()` no longer uses `filter=ids.arxiv:...`.
2. [x] `ReferenceRecord.arxiv_id` is populated for OpenAlex-derived references when appropriate.
3. [x] Unit tests cover DOI mapping + arXiv extraction logic (offline, deterministic).
4. [x] Network integration tests pass when invoked explicitly.

---

## References

- OpenAlex filters: https://docs.openalex.org/api-entities/works/filter-works
- OpenAlex work IDs schema: https://docs.openalex.org/api-entities/works/work-object#ids
- arXiv DOI policy: https://info.arxiv.org/help/doi.html
