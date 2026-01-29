# BUG-050: Enrichment `with_identifiers` Stat Incorrect When Leads Already Enriched

**Priority:** P1
**Status:** Open
**Found:** 2026-01-29
**Component:** `src/erdos/core/research/enrichment.py`

## Description

The `EnrichmentStats.with_identifiers` counter only counts leads that are processed (not already enriched), not all leads that actually have DOI/arXiv identifiers. This produces misleading statistics that don't match user expectations.

## Steps to Reproduce

```bash
# 1. Add a lead with DOI
uv run erdos research lead add 74 --title "Test" --doi "10.1234/test"

# 2. Enrich it
uv run erdos research lead enrich 74

# 3. Run enrich again without force
uv run erdos research lead enrich 74 --json | jq '.data'
```

## Expected Behavior

```json
{
  "total": 1,
  "with_identifiers": 1,
  "enriched": 0,
  "skipped_no_id": 0,
  "failed": 0
}
```

The `with_identifiers` should count all leads that have a DOI or arXiv ID.

## Actual Behavior

```json
{
  "total": 1,
  "with_identifiers": 0,
  "enriched": 0,
  "skipped_no_id": 0,
  "failed": 0
}
```

The counter is 0 because the already-enriched lead is skipped before the identifier check.

## Root Cause

In `enrich_leads()`, the identifier counting logic runs AFTER the "already enriched" skip:

```python
for lead in leads:
    # Check if already enriched
    if lead.enriched_at is not None and not force:
        logger.debug("Skipping already enriched lead: %s", lead.id)
        results.append(EnrichmentResult(lead=lead))
        continue  # <-- Skips before counting!

    # Check for identifiers
    has_identifier = lead.source.doi or lead.source.arxiv_id
    if has_identifier:
        stats.with_identifiers += 1  # <-- Never reached for enriched leads
```

## Recommended Fix

Move identifier counting before the already-enriched check:

```python
for lead in leads:
    # Count identifiers first (for accurate stats)
    has_identifier = lead.source.doi or lead.source.arxiv_id
    if has_identifier:
        stats.with_identifiers += 1

    # Check if already enriched
    if lead.enriched_at is not None and not force:
        stats.skipped_already_enriched += 1  # Add new counter
        logger.debug("Skipping already enriched lead: %s", lead.id)
        results.append(EnrichmentResult(lead=lead))
        continue

    # Check for identifiers (skip if none)
    if not has_identifier:
        stats.skipped_no_id += 1
        # ...
```

## Impact

- **User confusion**: Stats don't reflect actual state of leads
- **Automation risk**: Scripts relying on `with_identifiers` will get wrong counts
- **Audit difficulty**: Cannot accurately assess how many leads have identifiers

## Evidence

```python
# Test script confirming bug:
from erdos.core.research.enrichment import LeadEnrichmentService
from erdos.core.research.models import LeadRecord, LeadSource
from datetime import datetime, UTC
from unittest.mock import Mock

provider = Mock()
provider.get_by_doi.return_value = None

now = datetime.now(UTC)
leads = [
    LeadRecord(problem_id=74, id='lead_1', title='Lead 1',
               source=LeadSource(doi='10.1234/test'), created_at=now, updated_at=now,
               enriched_at=now),  # Already enriched
    LeadRecord(problem_id=74, id='lead_2', title='Lead 2',
               source=LeadSource(doi='10.5678/test'), created_at=now, updated_at=now),
]

service = LeadEnrichmentService(provider)
_, stats = service.enrich_leads(leads, delay=0, force=False)

print(f'with_identifiers: {stats.with_identifiers}')  # Prints 1, should be 2
```

## Related

- SPEC-036: Lead Enrichment Pipeline
- SPEC-036 Section 11.6: Rate Limiting (partial implementation)
