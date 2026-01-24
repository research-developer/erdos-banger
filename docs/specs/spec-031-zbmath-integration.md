# SPEC-031: zbMATH Open API Integration

> **Status:** Pending
>
> **Target:** v3.4
>
> **Resolves:** Math-specific metadata gap (MSC codes, math reviews, equation search)
>
> **Prerequisites:** SPEC-028 (v3 verification)

---

## Summary

Integrate the [zbMATH Open API](https://zbmath.org/) as a "good redundancy" source for **math-specific metadata**. zbMATH is the Zentralblatt MATH database — the gold standard for pure mathematics with 100+ years of coverage.

---

## Motivation

**Current state:** OpenAlex provides general academic metadata (titles, authors, citations).

**Gap:** We lack math-specific classification:
- **MSC codes** (Mathematics Subject Classification) — precise topic hierarchy
- **Math reviews** — expert summaries not available elsewhere
- **Equation search** — find papers by mathematical formula
- **Historical coverage** — pre-digital mathematics literature

**zbMATH fills this gap:** Purpose-built for mathematics research.

---

## Unique Value (Not in OpenAlex)

```json
{
  "de": "1234567",
  "title": "On the density of certain sequences of integers",
  "authors": ["Erdős, Paul"],
  "year": 1935,
  "msc": [
    {"code": "11B05", "text": "Density, gaps, topology"},
    {"code": "05D10", "text": "Ramsey theory"}
  ],
  "review": "The author proves that the density of integers representable as sums of two squares is precisely π/4 · 1/√log n. The proof uses...",
  "keywords": ["density", "integers", "squares", "analytic methods"]
}
```

**Key unique data:**
- MSC codes enable precise topic queries (e.g., "all papers in 11B05")
- Expert reviews summarize key results (not auto-generated)
- Keywords are math-specific terminology

---

## Scope

### In Scope

1. **zbMATH client** — HTTP client for zbMATH Open API
2. **MSC-based search** — Find papers by Mathematics Subject Classification
3. **CLI commands:**
   - `erdos refs zbmath <identifier>` — Get zbMATH metadata for a paper
   - `erdos search --msc "11B05"` — Search by MSC code
4. **CLI compatibility** — Preserve existing `erdos refs <problem_id>` behavior while adding `erdos refs zbmath ...`
5. **Lead enrichment** — Annotate leads with MSC codes (opt-in)

### Out of Scope

- Equation/formula search (complex, requires LaTeX parsing)
- Full zbMATH review text in RAG (copyright considerations)
- zbMATH as primary metadata source (complement only)

---

## Environment Configuration

```bash
# No API key required! zbMATH Open is... open.
# But we should identify ourselves for polite access:
ERDOS_MAILTO=your-email@example.com
```

---

## CLI Interface

### zbMATH Lookup Command

```bash
erdos refs zbmath <identifier> [OPTIONS]

# Examples:
erdos refs zbmath "10.4007/annals.2008.167.481"  # DOI
erdos refs zbmath --zbl "1234567"                 # zbMATH ID
erdos refs zbmath --title "primes arithmetic progressions"  # Title search
```

### MSC Search Command

```bash
erdos search --msc "11B05" [OPTIONS]

# Examples:
erdos search --msc "11B05"                    # Density, gaps, topology
erdos search --msc "05D10"                    # Ramsey theory
erdos search --msc "11B05" --year-min 2000    # Recent papers only
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--limit` | 20 | Maximum results |
| `--year-min` | — | Filter by publication year |
| `--year-max` | — | Filter by publication year |

**JSON mode:** use the global flag: `erdos --json refs zbmath ...`

### Output (Default)

```text
zbMATH Entry: Zbl 1234567

Title: The primes contain arbitrarily long arithmetic progressions
Authors: Green, Ben; Tao, Terence
Year: 2008
Journal: Annals of Mathematics
DOI: 10.4007/annals.2008.167.481

MSC Classifications:
  - 11B05: Density, gaps, topology
  - 11N13: Primes in progressions
  - 05D10: Ramsey theory

Keywords: arithmetic progressions, primes, density, ergodic methods

Review (excerpt):
  The authors prove that the prime numbers contain arbitrarily long
  arithmetic progressions. This resolves a long-standing conjecture...
```

### Output (JSON mode)

```json
{
  "schema_version": 1,
  "command": "erdos refs zbmath",
  "success": true,
  "data": {
    "identifier": "10.4007/annals.2008.167.481",
    "entry": {
      "zbl_id": "1234567",
      "title": "The primes contain arbitrarily long arithmetic progressions",
      "authors": ["Green, Ben", "Tao, Terence"],
      "year": 2008,
      "journal": "Annals of Mathematics",
      "doi": "10.4007/annals.2008.167.481",
      "msc": [
        {"code": "11B05", "primary": true, "text": "Density, gaps, topology"},
        {"code": "11N13", "primary": false, "text": "Primes in progressions"},
        {"code": "05D10", "primary": false, "text": "Ramsey theory"}
      ],
      "keywords": ["arithmetic progressions", "primes", "density", "ergodic methods"],
      "review_excerpt": "The authors prove that the prime numbers contain..."
    }
  },
  "error": null,
  "timestamp": "2026-01-23T12:00:00Z",
  "duration_ms": 0
}
```

---

## Architecture

### Module Structure

```text
src/erdos/core/
  clients/
    zbmath.py           # HTTP client for zbMATH Open API
src/erdos/commands/
  refs.py               # Existing: `erdos refs <problem_id>` + new `zbmath` subcommand
  refs_zbmath.py        # Registers the `refs zbmath ...` subcommand into refs.app
```

### CLI Compatibility Notes

`erdos refs` is currently implemented as `erdos refs <problem_id>` with a required argument. To add `erdos refs zbmath ...` without breaking the existing behavior, implementation MUST follow the same approach as SPEC-030:

1. Make the callback `problem_id` argument optional, and only require it when no subcommand is invoked.
2. Check `ctx.invoked_subcommand` in the callback and return early when a subcommand is present.
3. Keep `erdos refs <problem_id>` working as-is (compat alias), even if a future refactor introduces `erdos refs problem <problem_id>`.

### Client Implementation

```python
# src/erdos/core/clients/zbmath.py

from dataclasses import dataclass
from erdos.core.rate_limiter import RateLimiter

@dataclass
class MSCCode:
    """Mathematics Subject Classification code."""
    code: str
    text: str
    primary: bool = False

@dataclass
class ZbMathEntry:
    """Paper metadata from zbMATH."""
    zbl_id: str
    title: str
    authors: list[str]
    year: int | None
    journal: str | None
    doi: str | None
    msc: list[MSCCode]
    keywords: list[str]
    review_excerpt: str | None  # First ~500 chars only

class ZbMathClient:
    """HTTP client for zbMATH Open API."""

    BASE_URL = "https://api.zbmath.org/v1"

    def __init__(self, mailto: str | None = None):
        self.mailto = mailto
        # zbMATH doesn't publish rate limits; be conservative
        self.rate_limiter = RateLimiter(delay_seconds=2.0)

    def get_by_doi(self, doi: str) -> ZbMathEntry | None:
        """Lookup by DOI."""
        ...

    def get_by_zbl(self, zbl_id: str) -> ZbMathEntry | None:
        """Lookup by zbMATH ID."""
        ...

    def search_by_msc(
        self,
        msc_code: str,
        limit: int = 20,
        year_min: int | None = None,
        year_max: int | None = None,
    ) -> list[ZbMathEntry]:
        """Search by MSC code."""
        ...

    def search_by_title(self, title: str, limit: int = 10) -> list[ZbMathEntry]:
        """Search by title keywords."""
        ...
```

---

## MSC Code Reference

Common MSC codes for Erdős problems:

| Code | Area | Erdős Problem Examples |
|------|------|------------------------|
| 05Dxx | Extremal combinatorics | Many |
| 05D10 | Ramsey theory | 6, 42, 124 |
| 11Bxx | Sequences and sets | Sum-free sets, progressions |
| 11B05 | Density, gaps, topology | 6 |
| 11B25 | Arithmetic progressions | 42 |
| 11N05 | Distribution of primes | Many |
| 11N13 | Primes in progressions | 42 |
| 52Cxx | Discrete geometry | Distance problems |

---

## Integration with Leads

Enrich leads with MSC codes:

```bash
erdos research lead add 6 --doi "10.4007/annals.2008.167.481" --fetch-msc
```

This queries zbMATH and adds MSC codes to the lead's tags.

---

## Caching Strategy

Cache zbMATH responses:

```text
literature/cache/zbmath/
  doi_<hash>.json     # DOI lookup cache
  zbl_<id>.json       # Direct zbMATH ID cache
  msc_<code>.json     # MSC search cache (short TTL)
```

Cache TTL:
- Paper metadata: 30 days (rarely changes)
- MSC searches: 7 days (new papers added)

---

## Testing

### Unit Tests

```python
# tests/unit/clients/test_zbmath.py

def test_zbmath_parses_entry():
    """Verify entry parsing."""
    ...

def test_zbmath_parses_msc_codes():
    """Verify MSC code extraction."""
    ...

def test_zbmath_handles_missing_fields():
    """Not all entries have reviews/keywords."""
    ...
```

### Integration Tests

```python
# tests/integration/test_zbmath.py

@pytest.mark.requires_network
def test_zbmath_lookup_by_doi():
    """Fetch entry by DOI."""
    ...

@pytest.mark.requires_network
def test_zbmath_search_by_msc():
    """Search by MSC code."""
    ...
```

---

## Acceptance Criteria

1. [ ] `ZbMathClient` implemented with rate limiting
2. [ ] `erdos refs zbmath` works with DOI and zbMATH ID
3. [ ] Existing `erdos refs <problem_id>` remains functional
4. [ ] `erdos search --msc` returns papers by MSC code
5. [ ] MSC codes included in JSON output
6. [ ] Review excerpts included (first 500 chars)
7. [ ] Caching reduces redundant API calls
8. [ ] `--fetch-msc` enriches leads with MSC tags
9. [ ] No API key required (open API)

---

## References

- [zbMATH Open](https://zbmath.org/)
- [zbMATH API Documentation](https://api.zbmath.org/)
- [Mathematics Subject Classification](https://mathscinet.ams.org/mathscinet/msc/msc2020.html)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
