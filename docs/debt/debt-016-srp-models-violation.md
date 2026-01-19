# Technical Debt 016: Single Responsibility Principle Violation in models.py

**Date:** 2026-01-19
**Status:** Open
**Priority:** P2 (Material quality gap; should be scheduled soon)
**Impact:** Maintainability, testability, cognitive load

## Summary

`src/erdos/core/models.py` contains 12+ unrelated domain models in a single 474-line file. This violates the Single Responsibility Principle - the file has multiple reasons to change and low cohesion.

## Current State

```
src/erdos/core/models.py (474 lines)
├── ProblemStatus (enum)
├── ReferenceEntry (embedded reference)
├── ProblemRecord (main domain object)
├── OpenAccessStatus (enum)
├── ReferenceRecord (enriched reference)
├── ManifestEntry (cache state)
├── ProblemManifest (manifest file)
├── ChunkSource (enum)
├── TextChunk (search chunk)
├── LeanError (compiler error)
├── LeanCheckResult (compilation result)
└── CLIOutput (command output wrapper)
```

## Problems

1. **Low Cohesion**: `LeanError` and `ProblemRecord` have nothing in common
2. **Multiple Reasons to Change**: Changes to search indexing shouldn't touch problem models
3. **Import Bloat**: Importing one model imports all 474 lines
4. **Cognitive Load**: Developers must scroll through unrelated code
5. **Testing**: Can't test Lean models without loading Problem models

## Proposed Fix

Split into domain-focused modules:

```
src/erdos/core/models/
├── __init__.py          # Re-exports for backward compatibility
├── base.py              # ErdosBaseModel, utc_now()
├── problem.py           # ProblemStatus, ReferenceEntry, ProblemRecord
├── reference.py         # OpenAccessStatus, ReferenceRecord, ManifestEntry, ProblemManifest
├── search.py            # ChunkSource, TextChunk
├── lean.py              # LeanError, LeanCheckResult
└── output.py            # CLIOutput
```

The `__init__.py` re-exports all models for backward compatibility:
```python
from erdos.core.models.problem import ProblemStatus, ReferenceEntry, ProblemRecord
from erdos.core.models.reference import ...
# etc.
```

## Acceptance Criteria

- [ ] models.py split into 6 focused modules
- [ ] All existing imports continue to work (backward compatible)
- [ ] Each module < 150 lines
- [ ] All tests pass
- [ ] No circular imports

## Effort Estimate

Medium - requires careful import management to avoid circular dependencies.

## References

- Robert C. Martin, "Clean Code" Chapter 10: Classes
- SOLID Principles: Single Responsibility Principle
