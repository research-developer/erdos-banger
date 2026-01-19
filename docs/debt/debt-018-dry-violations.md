# Technical Debt 018: DRY Violations (Code Duplication)

**Date:** 2026-01-19
**Status:** Open
**Priority:** P1 (Blocks planned work or causes frequent breakage)
**Impact:** Maintainability, consistency, bug propagation

## Summary

Multiple patterns are copy-pasted across the codebase. When these patterns need to change, all copies must be updated - and they won't be. This leads to inconsistent behavior and bugs.

## Violations

### 1. Loader Error Handling Pattern (8 occurrences)

**Locations:**
- `commands/list_cmd.py:173-183`
- `commands/show.py:117-127`
- `commands/refs.py:99-109`
- `commands/search.py:265-274`
- `commands/lean.py:127-134`
- `commands/ingest.py` (via core)
- `commands/ask.py` (via core)
- `core/ingest.py:72-80`

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

**Risk:** If error handling logic changes (e.g., add logging, change error type), 8 places need updating.

### 2. Time Measurement Pattern (7 occurrences)

**Locations:**
- `commands/list_cmd.py:172,193-196`
- `commands/show.py:116,130-133`
- `commands/refs.py:98,112-115`
- `commands/search.py:235,276-279`
- `commands/lean.py:198,202-205` (init)
- `commands/lean.py:245,248-251` (check)
- `commands/ask.py:166,179-180`

**Pattern:**
```python
start_time = time.perf_counter()
# ... do work ...
duration_ms = int((time.perf_counter() - start_time) * 1000)
result.duration_ms = duration_ms
```

**Risk:** If timing precision changes or we add more metadata, 7 places need updating.

### 3. JSON Output Setup Pattern (7 occurrences)

**Locations:**
- `commands/list_cmd.py:168-170`
- `commands/show.py:112-114`
- `commands/refs.py:94-96`
- `commands/search.py:228-230`
- `commands/lean.py:194-196` (init)
- `commands/lean.py:241-243` (check)
- `commands/ask.py:139-141`

**Pattern:**
```python
ctx.ensure_object(dict)
if json_output:
    ctx.obj["json"] = True
```

### 4. arXiv Download Logic (CRITICAL - 2 near-identical blocks)

**Locations:**
- `core/ingest.py:380-422` (DOI+arXiv case)
- `core/ingest.py:445-487` (arXiv-only case)

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
- `core/ingest.py:335-341` - `_get_stable_key(ref: ReferenceEntry)`
- `core/ingest.py:344-350` - `_get_stable_key_from_record(record: ReferenceRecord)`

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

Create a decorator that handles loader, timing, and JSON setup:

```python
# commands/common.py
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
# core/ingest.py
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
# core/ingest.py
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
- [ ] Time measurement consolidated (decorator or context manager)
- [ ] JSON setup consolidated
- [ ] arXiv download logic exists in exactly ONE place
- [ ] Stable key function exists in exactly ONE place
- [ ] All tests pass
- [ ] No functionality changes (pure refactor)

## Effort Estimate

Medium - the decorator approach requires careful testing to ensure all command signatures still work.

## References

- Robert C. Martin, "Clean Code" Chapter 17: Smells and Heuristics - "Duplication"
- DRY Principle: "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system"
