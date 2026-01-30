# BUG-053: Lead Ingest Partial Failure Creates Inconsistent State

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-29
**Fixed:** 2026-01-29
**Component:** `src/erdos/commands/research/lead.py`

## Description

When `lead ingest` successfully writes the manifest but fails to update some leads' `ingested_at` field, it creates an inconsistent state where:
- Manifest has new entries with `lead_id` references
- Some leads are not marked as ingested (`ingested_at` is None)

This breaks the provenance tracking that SPEC-036 requires.

## Steps to Reproduce

```python
# Scenario: Manifest write succeeds, but lead update fails (e.g., disk full for lead file)
# 1. Ingest leads - manifest updated with 5 new entries
# 2. Lead 3's update fails (exception caught)
# 3. Result: manifest has lead_3's entry, but lead_3.ingested_at is None
```

## Expected Behavior

Either:
1. **Atomic**: All-or-nothing - if any lead update fails, rollback manifest
2. **Idempotent**: Re-running ingest handles the inconsistent state gracefully

## Actual Behavior

Partial success: manifest is updated, some leads are not marked. No way to detect or recover from this state automatically.

## Root Cause

The ingest command catches and logs exceptions during lead updates without rolling back:

```python
# Line 495-505 in lead.py
for result in results:
    if result.added and result.entry is not None:
        try:
            store.lead_update(
                problem_id,
                result.lead_id,
                ingested_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Failed to update lead %s: %s", result.lead_id, e)
            # <-- No rollback, no failure propagation!
```

## Impact

- **Data inconsistency**: Provenance tracking is broken
- **Audit difficulty**: Cannot reliably trace which leads are in manifest
- **Silent failure**: User sees success even though state is inconsistent

## Recommended Fix

Option 1: **Report partial failure in exit code and output**
```python
failed_updates = 0
for result in results:
    if result.added and result.entry is not None:
        try:
            store.lead_update(...)
        except Exception as e:
            logger.warning("Failed to update lead %s: %s", result.lead_id, e)
            failed_updates += 1

if failed_updates > 0:
    # Include in output
    exit_with_result(ctx, CLIOutput.ok(
        command="erdos research lead ingest",
        data={
            ...
            "failed_lead_updates": failed_updates,
            "warning": f"{failed_updates} leads could not be marked as ingested",
        },
    ))
```

Option 2: **Two-phase commit with rollback**
1. Update all leads first (in-memory)
2. Write manifest only if all lead updates succeed
3. On failure, don't write manifest

## Related

- SPEC-036: Lead Enrichment Pipeline
- SPEC-036 Section 9: Error Handling (mentions rollback for manifest write fails)
