# BUG-052: ManifestBridge Does Not Normalize arXiv Version Suffixes

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-29
**Fixed:** 2026-01-29
**Component:** `src/erdos/core/research/manifest_bridge.py`

## Description

The `ManifestBridge` does not normalize arXiv version suffixes when checking for duplicates. This means `2305.15585` and `2305.15585v2` are treated as different papers, even though they refer to the same work.

## Steps to Reproduce

```python
from erdos.core.research.manifest_bridge import ManifestBridge
from erdos.core.models import ProblemManifest, ManifestEntry, ReferenceRecord
from erdos.core.research.models import LeadRecord, LeadSource
from datetime import datetime, UTC

now = datetime.now(UTC)

# Manifest has arXiv ID without version
existing_ref = ReferenceRecord(arxiv_id='2305.15585', title='Existing Paper')
manifest = ProblemManifest(problem_id=74, entries=[ManifestEntry(reference=existing_ref)])

# Lead has same arXiv ID with version suffix
lead = LeadRecord(
    problem_id=74, id='lead_1', title='Lead 1',
    source=LeadSource(arxiv_id='2305.15585v2'),  # With version
    created_at=now, updated_at=now,
    enriched_at=now, enriched_title='Test Paper'
)

bridge = ManifestBridge()
result = bridge.ingest_lead(lead, manifest)
print(f'Added: {result.added}')  # True - Potentially wrong
```

## Expected Behavior

Debatable. Two reasonable interpretations:

1. **Strict**: `2305.15585` and `2305.15585v2` are different entries (v2 may have significant changes)
2. **Lenient**: Same base ID = same paper (dedup by stripping version suffix)

For literature tracking purposes, the **lenient** approach is usually better - we care about the paper, not the specific version.

## Actual Behavior

Entries are treated as different, leading to potential duplicates of the same paper.

## Root Cause

No version suffix normalization in duplicate check:

```python
# Line 93-95 in manifest_bridge.py
existing_arxiv_ids = {
    e.reference.arxiv_id for e in manifest.entries if e.reference.arxiv_id
}
```

## Recommended Fix

Strip version suffix when comparing:

```python
import re

def _normalize_arxiv_id(arxiv_id: str) -> str:
    """Strip version suffix from arXiv ID for deduplication."""
    return re.sub(r'v\d+$', '', arxiv_id)

# Then use in duplicate check:
existing_arxiv_bases = {
    _normalize_arxiv_id(e.reference.arxiv_id)
    for e in manifest.entries if e.reference.arxiv_id
}

if arxiv_id and (_normalize_arxiv_id(arxiv_id) in existing_arxiv_bases
                  or _normalize_arxiv_id(arxiv_id) in seen_arxiv_bases):
    return IngestResult(lead_id=lead.id, added=False, reason="duplicate_arxiv")
```

## Impact

- **Data duplication**: Same paper (different versions) appears multiple times
- **Wasted resources**: Redundant PDF downloads
- **Medium severity**: Version differences are sometimes meaningful

## Design Decision Needed

Should we:
1. Strip version suffixes for dedup (lenient - recommended)
2. Treat versions as different entries (strict - current behavior)
3. Store both: normalized base for dedup, original for reference

## Related

- SPEC-036: Lead Enrichment Pipeline
- arXiv ID format: https://info.arxiv.org/help/arxiv_identifier_for_services.html
