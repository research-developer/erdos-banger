# Technical Debt 018: DRY Violations (Code Duplication)

**Date:** 2026-01-19
**Status:** Open
**Priority:** P1 (Blocks planned work or causes frequent breakage)
**Impact:** Maintainability, consistency, bug propagation

## Summary

Multiple patterns are copy-pasted across the codebase. When these patterns need to change, all copies must be updated - and they won't be. This leads to inconsistent behavior and bugs.

## Violations

### 1. Loader Bootstrap + Error Translation (7+ occurrences)

**Locations:**
- `src/erdos/commands/list_cmd.py:173-183`
- `src/erdos/commands/show.py:117-127`
- `src/erdos/commands/refs.py:99-109`
- `src/erdos/commands/search.py:265-274` (fallback path)
- `src/erdos/commands/lean.py:126-134` (formalize core helper)
- `src/erdos/core/ask.py:222-240` (plus a second duplicated `get_by_id()` error block)
- `src/erdos/core/ingest.py:71-90` (plus a second duplicated `get_by_id()` error block)

**Pattern:**
```python
try:
    loader = ProblemLoader.from_default()
except ProblemLoaderError as e:
    result = CLIOutput.err(
        command="erdos <cmd>",
        error_type="LoaderError",
        message=str(e),
        code=ExitCode.ERROR,
    )
    exit_with_result(ctx, result)
    return
```

**Risk:** If error handling logic changes (e.g., add structured logging, add hints, change error taxonomy), multiple sites need updating and will drift.

### 2. Time Measurement Pattern (9 occurrences)

**Locations:**
- `src/erdos/commands/list_cmd.py:172,193-196`
- `src/erdos/commands/show.py:116,130-133`
- `src/erdos/commands/refs.py:98,112-115`
- `src/erdos/commands/search.py:235,276-279` (plus an early-error path at 246-257)
- `src/erdos/commands/ask.py:166,179-180`
- `src/erdos/commands/ingest.py:166,187-188`
- `src/erdos/commands/lean.py:198,202-205` (init)
- `src/erdos/commands/lean.py:245,248-251` (check)
- `src/erdos/commands/lean.py:301,304-305` (formalize)

**Pattern:**
```python
start_time = time.perf_counter()
# ... do work ...
duration_ms = int((time.perf_counter() - start_time) * 1000)
result.duration_ms = duration_ms
```

**Risk:** If timing fields change (precision, naming, monotonic clock choice), multiple sites need updating.

### 3. JSON Output Setup Pattern (9 occurrences)

**Locations:**
- `src/erdos/commands/list_cmd.py:168-170`
- `src/erdos/commands/show.py:112-114`
- `src/erdos/commands/refs.py:94-96`
- `src/erdos/commands/search.py:228-230`
- `src/erdos/commands/ask.py:139-141`
- `src/erdos/commands/ingest.py:155-157`
- `src/erdos/commands/lean.py:194-196` (init)
- `src/erdos/commands/lean.py:241-243` (check)
- `src/erdos/commands/lean.py:297-299` (formalize)

**Pattern:**
```python
ctx.ensure_object(dict)
if json_output:
    ctx.obj["json"] = True
```

### 4. arXiv Download Logic (CRITICAL - 2 near-identical blocks)

**Locations:**
- `src/erdos/core/ingest.py:380-422` (DOI+arXiv case)
- `src/erdos/core/ingest.py:445-487` (arXiv-only case)

**Duplicated code (~40 lines each):**
```python
if not no_download:
    try:
        arxiv_cache_path = repo_root / get_arxiv_cache_path(ref.arxiv_id)
        arxiv_extract_path = repo_root / get_arxiv_extract_path(ref.arxiv_id)

        # Download source
        source_url = f"https://arxiv.org/e-print/{ref.arxiv_id}"
        response = requests.get(source_url, timeout=timeout)
        response.raise_for_status()
        tarball_bytes = response.content

        # Write cache
        arxiv_cache_path.parent.mkdir(parents=True, exist_ok=True)
        arxiv_cache_path.write_bytes(tarball_bytes)

        # Compute hash
        cache_hash = hashlib.md5(tarball_bytes).hexdigest()
        cache_path = get_arxiv_cache_path(ref.arxiv_id)

        # Extract text
        try:
            text_bytes = extract_arxiv_text(tarball_bytes)
            text = text_bytes.decode("utf-8", errors="replace")
            arxiv_extract_path.parent.mkdir(parents=True, exist_ok=True)
            arxiv_extract_path.write_text(text, encoding="utf-8")
            extract_path = get_arxiv_extract_path(ref.arxiv_id)
            extracted = True
        except (OSError, ValueError, tarfile.TarError) as e:
            error = f"Extraction failed: {e}"
            extracted = False
    except (OSError, requests.RequestException) as e:
        error = f"Download failed: {e}"
```

**Risk:** A bug fix in one copy won't be applied to the other. This WILL cause inconsistent behavior.

### 5. Stable Key Functions (2 near-duplicates)

**Locations:**
- `src/erdos/core/ingest.py:335-341` - `_get_stable_key(ref: ReferenceEntry)`
- `src/erdos/core/ingest.py:344-350` - `_get_stable_key_from_record(record: ReferenceRecord)`

**Pattern:**
```python
def _get_stable_key(ref: ReferenceEntry) -> str:
    if ref.doi:
        return f"doi:{ref.doi.lower()}"
    if ref.arxiv_id:
        return f"arxiv:{ref.arxiv_id}"
    return ""

def _get_stable_key_from_record(record: ReferenceRecord) -> str:
    if record.doi:
        return f"doi:{record.doi.lower()}"
    if record.arxiv_id:
        return f"arxiv:{record.arxiv_id}"
    return ""
```

**Risk:** Same logic, different types. If key format changes, both need updating.

## Proposed Fixes

### Fix 1: Command Decorator for Common Patterns

Spec-009 already centralized JSON/human output into `src/erdos/commands/presenter.py`. The remaining duplication is command setup (ctx/json), timing, and loader bootstrap. Create a decorator (or small helper) that handles loader, timing, and JSON setup:

```python
# src/erdos/commands/common.py (to create)
from functools import wraps

def erdos_command(command_name: str):
    """Decorator that handles common CLI patterns."""
    def decorator(func):
        @wraps(func)
        def wrapper(ctx: typer.Context, *args, json_output: bool = False, **kwargs):
            ctx.ensure_object(dict)
            if json_output:
                ctx.obj["json"] = True

            start_time = time.perf_counter()

            try:
                loader = ProblemLoader.from_default()
            except ProblemLoaderError as e:
                result = CLIOutput.err(
                    command=command_name,
                    error_type="LoaderError",
                    message=str(e),
                    code=ExitCode.ERROR,
                )
                exit_with_result(ctx, result)
                return

            result = func(ctx, loader, *args, **kwargs)

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            result.duration_ms = duration_ms
            return result
        return wrapper
    return decorator
```

### Fix 2: Extract arXiv Download Helper

```python
# src/erdos/core/ingest.py
@dataclass
class ArxivDownloadResult:
    cache_path: Path | None
    cache_hash: str | None
    extract_path: Path | None
    extracted: bool
    error: str | None

def _download_and_extract_arxiv(
    arxiv_id: str,
    repo_root: Path,
    timeout: float,
) -> ArxivDownloadResult:
    """Download arXiv source and extract text.

    Single implementation used by both DOI+arXiv and arXiv-only paths.
    """
    # ~40 lines, ONE copy
```

### Fix 3: Generic Stable Key Function

```python
# src/erdos/core/ingest.py
from typing import Protocol

class HasIdentifiers(Protocol):
    doi: str | None
    arxiv_id: str | None

def get_stable_key(obj: HasIdentifiers) -> str:
    """Get stable deduplication key for any object with identifiers."""
    if obj.doi:
        return f"doi:{obj.doi.lower()}"
    if obj.arxiv_id:
        return f"arxiv:{obj.arxiv_id}"
    return ""
```

## Acceptance Criteria

- [ ] Loader error handling consolidated to one location
- [x] Time measurement consolidated (decorator or context manager)
- [ ] JSON setup consolidated
- [x] arXiv download logic exists in exactly ONE place
- [x] Stable key function exists in exactly ONE place
- [x] All tests pass
- [x] No functionality changes (pure refactor)

## Effort Estimate

Medium - the decorator approach requires careful testing to ensure all command signatures still work.

## References

- Robert C. Martin, "Clean Code" Chapter 17: Smells and Heuristics - "Duplication"
- DRY Principle: "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system"
