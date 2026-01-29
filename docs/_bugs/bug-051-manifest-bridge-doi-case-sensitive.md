# BUG-051: ManifestBridge DOI Comparison is Case-Sensitive

**Priority:** P2
**Status:** Open
**Found:** 2026-01-29
**Component:** `src/erdos/core/research/manifest_bridge.py`

## Description

The `ManifestBridge.ingest_lead()` method performs case-sensitive DOI comparison, which can lead to duplicate entries when the same DOI appears with different cases (e.g., `10.1234/TEST` vs `10.1234/test`).

DOIs are case-insensitive by specification (https://www.doi.org/doi_handbook/2_Numbering.html#2.4).

## Steps to Reproduce

```python
from erdos.core.research.manifest_bridge import ManifestBridge
from erdos.core.models import ProblemManifest, ManifestEntry, ReferenceRecord
from erdos.core.research.models import LeadRecord, LeadSource
from datetime import datetime, UTC

now = datetime.now(UTC)

# Manifest has DOI in uppercase
existing_ref = ReferenceRecord(doi='10.1234/TEST', title='Existing Paper')
manifest = ProblemManifest(problem_id=74, entries=[ManifestEntry(reference=existing_ref)])

# Lead has same DOI in lowercase
lead = LeadRecord(
    problem_id=74, id='lead_1', title='Lead 1',
    source=LeadSource(doi='10.1234/test'),  # lowercase
    created_at=now, updated_at=now,
    enriched_at=now, enriched_title='Test Paper'
)

bridge = ManifestBridge()
result = bridge.ingest_lead(lead, manifest)
print(f'Added: {result.added}')  # True - WRONG! Should be duplicate
```

## Expected Behavior

Lead with `10.1234/test` should be detected as duplicate of manifest entry with `10.1234/TEST`.

## Actual Behavior

Lead is added as a new entry, creating a duplicate.

## Root Cause

The duplicate check uses plain set membership without normalization:

```python
# Line 92-98 in manifest_bridge.py
existing_dois = {e.reference.doi for e in manifest.entries if e.reference.doi}
# ...
if doi and (doi in existing_dois or doi in seen_dois):
    return IngestResult(lead_id=lead.id, added=False, reason="duplicate_doi")
```

No `.lower()` normalization is applied.

## Recommended Fix

Normalize DOIs to lowercase during comparison:

```python
existing_dois = {e.reference.doi.lower() for e in manifest.entries if e.reference.doi}
# ...
if doi and (doi.lower() in existing_dois or doi.lower() in seen_dois):
    return IngestResult(lead_id=lead.id, added=False, reason="duplicate_doi")

# Also update seen_dois tracking:
if lead.source.doi:
    seen_dois.add(lead.source.doi.lower())
```

Note: The SPEC-036 spec (section 4.2, lines 368-373) explicitly mentions building a lowercase DOI index, but this was not implemented.

## Impact

- **Data duplication**: Same paper can appear multiple times in manifest
- **Wasted resources**: Duplicate entries lead to redundant PDF downloads/extraction
- **Search pollution**: Duplicate results in literature searches

## Related

- SPEC-036: Lead Enrichment Pipeline
- SPEC-036 Section 4.2: ManifestBridge specification (mentions lowercase index)
- DOI Handbook 2.4: DOI case-insensitivity standard
