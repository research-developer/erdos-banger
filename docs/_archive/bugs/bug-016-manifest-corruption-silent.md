# Bug: Manifest corruption silently returns None

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-21
**Fixed:** 2026-01-21
**Commit:** 1d5bd51

## Description

When loading a manifest file, if the file is corrupted (invalid YAML, validation failure, etc.), the code catches the exception and returns `None` without any logging. This masks data integrity issues from operators.

## Location

`src/erdos/core/ingest/service.py` (`_load_existing_manifest`)

This now logs a warning and proceeds with fresh ingestion.

## Steps to Reproduce

1. Create a manifest file with invalid YAML:
   ```bash
   echo "invalid: yaml: content: [" > literature/manifests/problem_001.yaml
   ```
2. Run `erdos ingest 1`
3. Observe that ingestion proceeds with no indication that the existing manifest was corrupted

## Expected Behavior

- Corruption should be logged at WARNING level
- The log should include the file path and exception details
- Operators should be able to audit manifest health

## Actual Behavior

- Corruption is silently ignored
- No indication of data integrity issues
- Fresh ingestion overwrites potentially valuable partial data

## Root Cause

The comment "If manifest is corrupted, return None to proceed with fresh ingestion" documents the intent, but the implementation lacks observability.

## Fix

Add logging before returning None:

```python
except (OSError, yaml.YAMLError, ValidationError, TypeError, ValueError) as e:
    logger.warning(
        "Manifest corrupted at %s, will proceed with fresh ingestion: %s",
        manifest_path,
        e,
    )
    return None
```

## Related

- BUG-014: Silent exception swallowing masks errors (fixed)
