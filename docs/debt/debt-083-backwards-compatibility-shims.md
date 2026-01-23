# DEBT-083: Remove Backwards-Compatibility Shims

**Priority:** P2
**Status:** Open
**Found:** 2026-01-23
**Tool:** Grep + code review

## Description

Multiple modules contain "backwards compatibility" re-exports and deprecated shims that should be removed. This is a greenfield project with no external consumers requiring backwards compatibility.

These shims:
1. Create confusion about canonical import paths
2. Increase maintenance burden
3. Prevent clean refactoring
4. Violate the project's forward-looking philosophy

## Evidence

### 1. Deprecated `build_metadata_provider` function

`src/erdos/core/context.py:84-109`:
```python
def build_metadata_provider(
    *,
    mailto: str,
    timeout: float,
    openalex_api_key: str | None = None,
) -> MetadataProvider:
    """Create the default metadata provider with capability-specific chains.

    Deprecated in favor of `erdos.core.ingest.fetch.build_provider_from_source()`,
    but kept for backwards compatibility and tests.
    ...
    """
```

**Status:** Only used in tests (`tests/unit/providers/test_fallback.py`). Production code uses `build_provider_from_source()` directly.

### 2. Re-exports in `__init__.py` files

**`src/erdos/core/ask/__init__.py`:**
```python
All public APIs are re-exported for backward compatibility.
# Re-export public APIs for backward compatibility
```

**`src/erdos/core/ingest/__init__.py`:**
```python
All public APIs are re-exported for backward compatibility.
# Re-export public APIs for backward compatibility
```

**`src/erdos/core/search/__init__.py`:**
```python
All public APIs are re-exported for backward compatibility.
```

**`src/erdos/core/loop/__init__.py`:**
```python
# Re-export public API for backward compatibility
```

### 3. Internal compatibility methods

**`src/erdos/core/search/facade.py:293-299`:**
```python
# Internal access (for backward compatibility in tests)
def _connect(self) -> sqlite3.Connection:
    """Get raw database connection.

    NOTE: This is for backward compatibility with existing tests.
    ...
    """
```

### 4. Re-exports in fetch.py

**`src/erdos/core/ingest/fetch.py:54`:**
```python
# Re-export for backward compatibility
```

## Root Cause

During DEBT-061 (Remove core backward-compatibility shims), some shims were preserved in subpackages. The original cleanup focused on core-root modules but left these in place.

## Recommendation

1. **Delete `build_metadata_provider`** from `context.py` - update tests to use `build_provider_from_source()` directly
2. **Remove all "backward compatibility" comments and re-exports** - establish canonical import paths
3. **Remove `_connect` method** from `SearchIndex` - tests should use public API
4. **Update import statements** throughout codebase to use canonical paths

## Acceptance Criteria

- [ ] `build_metadata_provider` removed from `context.py`
- [ ] All `__init__.py` re-exports removed or converted to explicit public API (no "backward compatibility" comments)
- [ ] `_connect` method removed from `SearchIndex`
- [ ] Tests updated to use canonical imports
- [ ] No grep results for "backward.compatibility" in src/erdos/
- [ ] All tests pass
- [ ] Archive this debt deck

## Impact

**Low risk** - This is internal refactoring. No external consumers depend on these paths.

## Related

- DEBT-061: Remove core backward-compatibility shims (previously archived)
- Project philosophy: Forward-looking greenfield with minimal compatibility debt
