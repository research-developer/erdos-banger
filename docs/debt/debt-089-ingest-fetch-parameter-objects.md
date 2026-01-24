# DEBT-089: Ingest/Fetch Long Parameter Lists

**Status:** Identified
**Created:** 2026-01-23
**Priority:** P1
**Tracking:** Functions with 8-14 parameters in `core/ingest/fetch.py`

## Summary

Multiple functions in `core/ingest/fetch.py` have 8-14 parameters (mostly keyword-only). This creates cognitive load at call sites and makes signatures harder to evolve.

## Current State

| Function | Parameters | Severity |
|----------|------------|----------|
| `_fetch_with_provider` | 8 | HIGH |
| `fetch_reference_entry` | 11 | HIGH |
| `process_single_reference` | 13 | CRITICAL |
| `process_all_references` | 14 | CRITICAL |

### Example (process_all_references)

```python
def process_all_references(
    problem: ProblemRecord,
    *,
    existing_manifest: ProblemManifest | None,
    force: bool,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
    delay: float,
    pdf: bool = False,
    pdf_converter: str = "marker",
    pdf_use_llm: bool = False,
    source: MetadataSource = MetadataSource.OPENALEX,
    provider: MetadataProvider | None = None,
) -> ProcessAllReferencesResult:
```

## The Problem

1. **Cognitive Load**: 14 parameters is impossible to remember
2. **Testing Burden**: Tests need to construct complex parameter sets
3. **Evolution Risk**: Adding features means adding more parameters
4. **Call Site Noise**: Every call is a wall of `param=value`

## Recommended Refactor

Note: `core/ingest/app.py` already has an `IngestOptions` dataclass at the application layer. This debt is specifically about the internal `core/ingest/fetch.py` API surface; the refactor should either (a) reuse existing option objects, or (b) introduce smaller, purpose-built config objects for fetch/PDF to reduce signature sprawl.

### Step 1: Create Configuration Dataclasses

```python
@dataclass(frozen=True)
class FetchConfig:
    """Configuration for reference fetching."""
    repo_root: Path
    allow_download: bool = True
    allow_network: bool = True
    timeout: float = 30.0
    mailto: str = ""
    delay: float = 3.0

@dataclass(frozen=True)
class PDFConfig:
    """Configuration for PDF conversion (SPEC-019)."""
    enabled: bool = False
    converter: str = "marker"
    use_llm: bool = False

@dataclass(frozen=True)
class IngestConfig:
    """Combined configuration for ingestion."""
    fetch: FetchConfig
    pdf: PDFConfig
    source: MetadataSource = MetadataSource.OPENALEX
    force: bool = False
```

### Step 2: Refactor Functions

```python
def process_all_references(
    problem: ProblemRecord,
    config: IngestConfig,
    *,
    existing_manifest: ProblemManifest | None = None,
    provider: MetadataProvider | None = None,
) -> ProcessAllReferencesResult:
    """Process all references for a problem.

    Args:
        problem: Problem record with references.
        config: Ingestion configuration.
        existing_manifest: Existing manifest for idempotence.
        provider: Optional MetadataProvider for dependency injection.
    """
```

**Result**: 14 parameters → 4 parameters

### Step 3: Update Call Sites

```python
# Before (14 params)
result = process_all_references(
    problem,
    existing_manifest=manifest,
    force=force,
    repo_root=repo_root,
    allow_download=not no_download,
    allow_network=not no_network,
    timeout=timeout,
    mailto=mailto,
    delay=delay,
    pdf=pdf,
    pdf_converter=pdf_converter,
    pdf_use_llm=pdf_use_llm,
    source=source,
    provider=provider,
)

# After (4 params)
config = IngestConfig(
    fetch=FetchConfig(repo_root=repo_root, mailto=mailto, timeout=timeout),
    pdf=PDFConfig(enabled=pdf, converter=pdf_converter, use_llm=pdf_use_llm),
    source=source,
    force=force,
)
result = process_all_references(problem, config, existing_manifest=manifest)
```

## Acceptance Criteria

- [ ] Create `FetchConfig` dataclass
- [ ] Create `PDFConfig` dataclass
- [ ] Create `IngestConfig` composition
- [ ] Refactor `process_all_references` to use config
- [ ] Refactor `process_single_reference` to use config
- [ ] Refactor `fetch_reference_entry` to use config
- [ ] Refactor `_fetch_with_provider` to use config
- [ ] Update all call sites (CLI, service, tests)
- [ ] Maintain 100% test coverage

## Impact

- **Medium risk**: Changes function signatures (breaking change for direct callers)
- **Medium effort**: ~2-3 hours of refactoring + test updates
- **High clarity gain**: Dramatically cleaner APIs

## Files Affected

1. `src/erdos/core/ingest/fetch.py` - Core changes
2. `src/erdos/core/ingest/service.py` - Call site updates
3. `src/erdos/commands/ingest.py` - CLI adapter
4. `tests/unit/core/ingest/test_fetch.py` - Test updates
5. `tests/unit/core/ingest/test_service.py` - Test updates
