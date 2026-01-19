# Technical Debt 017: Function Length Violations

**Date:** 2026-01-19
**Status:** Open
**Priority:** P1 (Blocks planned work or causes frequent breakage)
**Impact:** Maintainability, testability, readability, bug surface area

## Summary

Multiple functions exceed reasonable length limits (Uncle Bob recommends ~20 lines max). Long functions are harder to understand, test, and maintain. They indicate missing abstractions.

## Violations

### Critical (>100 lines)

| Function | File | Lines | Complexity |
|----------|------|-------|------------|
| `ingest_problem_references()` | `core/ingest.py` | 269 | PLR0911, PLR0912, PLR0915 |
| `ask_question()` | `core/ask.py` | 174 | PLR0911, PLR0912 |
| `_fetch_reference_entry()` | `core/ingest.py` | 128 | PLR0915 |

### Severe (50-100 lines)

| Function | File | Lines |
|----------|------|-------|
| `_parse_problem()` | `core/problem_loader.py` | 82 |
| `check()` | `core/lean_runner.py` | 77 |

### Moderate (30-50 lines)

| Function | File | Lines |
|----------|------|-------|
| `load_all()` | `core/problem_loader.py` | 45 |
| `search()` | `core/search_index.py` | 48 |
| `from_default()` | `core/problem_loader.py` | 48 |

## Root Cause Analysis

### `ingest_problem_references()` - 269 lines

This function does everything:
1. Load problem (lines 72-98)
2. Load existing manifest (lines 100-114)
3. Loop over references (lines 125-239)
   - Skip invalid refs
   - Check for existing entries
   - Fetch new entries
   - Handle 6 different exception types
   - Rate limiting
4. Duplicate detection (lines 244-254)
5. Create manifest (lines 257-264)
6. Write manifest atomically (lines 267-281)
7. Build response (lines 284-332)

Should be split into:
- `_load_or_create_manifest()`
- `_process_reference()`
- `_write_manifest_atomic()`
- `_build_response()`

### `_fetch_reference_entry()` - 128 lines

Has three nearly-identical code paths:
1. DOI + arXiv (lines 367-422) - 55 lines
2. DOI only (lines 425-432) - 8 lines
3. arXiv only (lines 435-487) - 52 lines

Paths 1 and 3 share ~90% of code (arXiv download logic). Should extract:
- `_download_arxiv_source(arxiv_id, repo_root, timeout)`
- `_fetch_doi_metadata(doi, mailto, timeout)`
- `_fetch_arxiv_metadata(arxiv_id, timeout)`

### `ask_question()` - 174 lines

Does too much:
1. Load problem
2. Build/rebuild index (optional)
3. Open search index
4. Perform retrieval (with fallback)
5. Deduplicate sources
6. Build prompt
7. Execute LLM (optional)
8. Build response

Should be split into:
- `_ensure_index_ready()`
- `_retrieve_sources()`
- `_execute_llm_if_enabled()`

## Evidence of Problem

The codebase uses `# noqa` to suppress complexity warnings:

```python
def ingest_problem_references(  # noqa: PLR0911, PLR0912, PLR0915
def ask_question(  # noqa: PLR0911, PLR0912
```

These are admissions that the code violates complexity thresholds:
- PLR0911: Too many return statements
- PLR0912: Too many branches
- PLR0915: Too many statements

## Proposed Fix

### Phase 1: Extract `_fetch_reference_entry()` helpers

```python
def _download_arxiv_source(
    arxiv_id: str,
    repo_root: Path,
    timeout: float,
) -> tuple[Path | None, str | None, Path | None, bool, str | None]:
    """Download arXiv source and extract text.

    Returns: (cache_path, cache_hash, extract_path, extracted, error)
    """
    # ~40 lines of currently-duplicated code
```

### Phase 2: Extract `ingest_problem_references()` helpers

```python
def _load_existing_manifest(manifest_path: Path) -> ProblemManifest | None:
    """Load manifest if exists and not forcing refresh."""

def _process_single_reference(
    ref: ReferenceEntry,
    existing_manifest: ProblemManifest | None,
    **kwargs
) -> tuple[ManifestEntry, bool]:  # (entry, is_failure)
    """Process one reference, returning entry and failure status."""

def _write_manifest_atomic(manifest: ProblemManifest, path: Path) -> None:
    """Write manifest with atomic rename."""
```

### Phase 3: Extract `ask_question()` helpers

```python
def _retrieve_with_fallback(
    index: SearchIndex,
    problem: ProblemRecord,
    question: str,
    limit: int,
) -> tuple[list[SearchResult], bool]:  # (sources, used_fts)
    """Retrieve sources, falling back to problem statement if index empty."""
```

## Acceptance Criteria

- [ ] No function exceeds 50 lines
- [ ] Remove all `# noqa: PLR0911, PLR0912, PLR0915` suppressions
- [ ] All tests pass
- [ ] Coverage maintained at 80%+
- [ ] Each extracted function has its own unit test

## Effort Estimate

Medium-High - requires careful extraction to maintain behavior and test coverage.

## References

- Robert C. Martin, "Clean Code" Chapter 3: Functions
- "The first rule of functions is that they should be small. The second rule of functions is that they should be smaller than that."
