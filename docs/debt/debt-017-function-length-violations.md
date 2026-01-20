# Technical Debt 017: Function Length Violations

**Date:** 2026-01-19
**Status:** Partially Fixed (Phase B complete)
**Priority:** P1 (Blocks planned work or causes frequent breakage)
**Impact:** Maintainability, testability, readability, bug surface area

## Summary

Multiple functions exceed reasonable length limits (Uncle Bob recommends ~20 lines max). Long functions are harder to understand, test, and maintain. They indicate missing abstractions.

## Violations

Function sizes below are measured as `end_lineno - lineno + 1` from the Python AST (so the numbers are reproducible and include decorators/docstrings).

### Critical (>100 lines)

| Function | File | Span | Lines | Notes |
|----------|------|------|-------|-------|
| ~~`ingest_problem_references()`~~ | `src/erdos/core/ingest.py` | ~~43-332~~ 536-625 | ~~290~~ **90** | ~~`# noqa: PLR0911,PLR0912,PLR0915`~~ **FIXED** |
| `ask_question()` | `src/erdos/core/ask.py` | 198-380 | 183 | `# noqa: PLR0911,PLR0912` |
| ~~`_fetch_reference_entry()`~~ | `src/erdos/core/ingest.py` | ~~353-489~~ 470-565 | ~~137~~ **96** | ~~`# noqa: PLR0915`~~ **FIXED (DEBT-018-A)** |
| `ingest()` | `src/erdos/commands/ingest.py` | 80-191 | 112 | CLI callback (options + orchestration) |
| `ask()` | `src/erdos/commands/ask.py` | 72-183 | 112 | CLI callback (stdin handling + orchestration) |
| `list_()` | `src/erdos/commands/list_cmd.py` | 96-197 | 102 | CLI callback (options + orchestration) |

### Severe (51-100 lines)

| Function | File | Span | Lines |
|----------|------|------|-------|
| `LeanRunner.check()` | `src/erdos/core/lean_runner.py` | 162-252 | 91 |
| `search()` | `src/erdos/commands/search.py` | 191-280 | 90 |
| `ProblemLoader._parse_problem()` | `src/erdos/core/problem_loader.py` | 129-211 | 83 |
| `SearchIndex._ensure_schema()` | `src/erdos/core/search_index.py` | 90-163 | 74 |
| `parse_arxiv_atom()` | `src/erdos/core/arxiv_client.py` | 28-97 | 70 |
| `build_prompt()` | `src/erdos/core/ask.py` | 15-83 | 69 |
| `SearchIndex.search()` | `src/erdos/core/search_index.py` | 245-312 | 68 |
| `parse_crossref_work()` | `src/erdos/core/crossref_client.py` | 16-82 | 67 |
| `search_problems_fts()` | `src/erdos/commands/search.py` | 64-129 | 66 |
| `LeanRunner.init()` | `src/erdos/core/lean_runner.py` | 108-160 | 53 |

### Moderate (30-50 lines)

There are currently 24 functions in the 30-50 line range (examples):

| Function | File | Span | Lines |
|----------|------|------|-------|
| `search_problems_basic()` | `src/erdos/commands/search.py` | 132-181 | 50 |
| `check()` | `src/erdos/commands/lean.py` | 210-259 | 50 |
| `ProblemLoader.from_default()` | `src/erdos/core/problem_loader.py` | 53-100 | 48 |
| `SearchIndex.index_problem()` | `src/erdos/core/search_index.py` | 165-210 | 46 |
| `ProblemLoader.load_all()` | `src/erdos/core/problem_loader.py` | 213-258 | 46 |
| `ProblemLoader.filter()` | `src/erdos/core/problem_loader.py` | 305-350 | 46 |

## Root Cause Analysis

### `ingest_problem_references()` - 290 lines (43-332)

This function does everything:
1. Load problem (construct loader, fetch problem, validate existence)
2. Load/parse existing manifest (YAML + Pydantic)
3. Loop over references
   - Skip invalid refs
   - Check for existing entries
   - Fetch new entries
   - Handle 6 different exception types
   - Rate limiting
4. Duplicate detection
5. Create manifest
6. Write manifest atomically
7. Build response (including partial-failure aggregation)

Should be split into:
- `_load_or_create_manifest()`
- `_process_reference()`
- `_write_manifest_atomic()`
- `_build_response()`

### `_fetch_reference_entry()` - ~~137~~ 96 lines (470-565) **[RESOLVED via DEBT-018-A]**

**Status**: Target met (<100 lines). The arXiv download duplication was resolved in DEBT-018-A by extracting `_download_and_extract_arxiv()`.

Original issue: Had three nearly-identical code paths with ~90% duplicated arXiv download logic.

Resolution: DEBT-018-A extracted the common arXiv download logic, reducing function from 137 to 96 lines. No further extraction needed as remaining code is cohesive and readable.

### `ask_question()` - 183 lines (198-380)

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

- [ ] No function exceeds 50 lines (split into phases A-D)
- [ ] Remove all `# noqa: PLR0911, PLR0912, PLR0915` suppressions
- [ ] All tests pass
- [ ] Coverage maintained at 80%+
- [ ] Each extracted function has its own unit test

### Progress by Phase

- [x] **Phase A**: `_fetch_reference_entry()` reduced to <100 lines (96 lines, met via DEBT-018-A)
- [x] **Phase B**: `ingest_problem_references()` reduced to <100 lines (90 lines after extracting helpers)
  - Fixed in commit: 693fe24
  - Extracted helpers: `_load_problem()`, `_load_existing_manifest()`, `_process_single_reference()`, `_process_all_references()`, `_check_duplicate_keys()`, `_create_manifest()`, `_write_manifest_atomic()`, `_build_ingest_result()`
  - Removed `# noqa: PLR0911, PLR0912, PLR0915` suppressions
- [ ] **Phase C**: `ask_question()` reduced to <100 lines (currently 183 lines)
- [ ] **Phase D**: All remaining functions <50 lines, remove noqa suppressions

## Effort Estimate

Medium-High - requires careful extraction to maintain behavior and test coverage.

## References

- Robert C. Martin, "Clean Code" Chapter 3: Functions
- "The first rule of functions is that they should be small. The second rule of functions is that they should be smaller than that."
