# BUG-018: OpenAlex Client Implementation Bugs

**Status:** Open
**Severity:** HIGH (broken implementation + 5 failing tests)
**Found:** 2026-01-21
**Found By:** Post-Ralph adversarial audit

---

## Summary

The OpenAlex client has TWO critical bugs:

1. **`get_by_arxiv()` uses invalid API filter** - `ids.arxiv` is not a valid OpenAlex filter parameter
2. **Integration tests use wrong DOI format** - arXiv-minted DOIs (10.48550) are not recognized

## Bug 1: `get_by_arxiv()` Implementation Broken

**Location:** `src/erdos/core/openalex_client.py:289`

```python
params = self._params(filter=f"ids.arxiv:{arxiv_id}")  # INVALID FILTER
```

**Evidence:**
```bash
curl -s "https://api.openalex.org/works?filter=ids.arxiv:1706.03762"
# Returns: {"error":"Invalid query parameters error.","message":"ids.arxiv is not a valid field..."}
```

**Valid OpenAlex ID filters per [documentation](https://docs.openalex.org/api-entities/works/filter-works):**
- `ids.pmcid` - PubMed Central
- `ids.pmid` - PubMed
- `ids.openalex` - OpenAlex ID
- `ids.mag` - Microsoft Academic Graph
- `doi` - DOI

**There is NO `ids.arxiv` filter.**

### Fix Options

**Option A: Search fallback (safest)**
```python
def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord:
    # Search by arXiv URL in title/abstract
    results = self.search(f"arxiv.org/abs/{arxiv_id}", limit=5)
    for ref in results:
        if ref.arxiv_id == arxiv_id:
            return ref
    raise ValueError(f"No work found for arXiv:{arxiv_id}")
```

**Option B: Direct OpenAlex ID lookup (if known)**
```python
# OpenAlex works have predictable IDs for some arXiv papers
# But requires maintaining a mapping or scraping
```

## Bug 2: Integration Tests Use Wrong DOI

**Failing Tests:**
```
tests/integration/test_openalex_integration.py::TestOpenAlexClientLive::test_get_by_doi_real_paper
tests/integration/test_openalex_integration.py::TestOpenAlexClientLive::test_get_by_arxiv_real_paper
tests/integration/test_openalex_integration.py::TestOpenAlexClientLive::test_get_citations_for_famous_paper
tests/integration/test_openalex_integration.py::TestOpenAlexClientLive::test_reference_record_fields_populated
tests/integration/test_openalex_integration.py::TestOpenAlexClientLive::test_abstract_reconstruction
```

**Root Cause:** Tests use DOI `10.48550/arXiv.1706.03762` (arXiv-minted) which OpenAlex returns 404 for.

```bash
curl -s "https://api.openalex.org/works/doi:10.48550/arXiv.1706.03762"
# Returns: 404 Not Found
```

### Fix Required

Use a paper with a known, working OpenAlex entry. Test with:
```bash
curl -s "https://api.openalex.org/works?search=attention%20is%20all%20you%20need&per_page=1"
# Returns the paper with DOI: https://doi.org/10.65215/2q58a426
```

## Acceptance Criteria

1. [ ] Fix `get_by_arxiv()` to use valid lookup method
2. [ ] Update integration tests with working DOIs
3. [ ] All 8 integration tests pass: `uv run pytest tests/integration/test_openalex_integration.py -m requires_network`
4. [ ] Add unit tests that mock the API response to prevent future breakage

## Lesson Learned

**Ralph Wiggum shipped code that was never tested against the real API.** The unit tests mocked the responses, and the integration tests used invalid identifiers. This is a reward hack - tests passed but implementation is broken.

---

## References

- [OpenAlex Filter Works](https://docs.openalex.org/api-entities/works/filter-works)
- [OpenAlex Work Object IDs](https://docs.openalex.org/api-entities/works/work-object#ids)
- [arXiv DOI policy](https://info.arxiv.org/help/doi.html)
