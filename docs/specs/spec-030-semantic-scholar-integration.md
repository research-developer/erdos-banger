# SPEC-030: Semantic Scholar API Integration

> **Status:** Pending
>
> **Target:** v3.3
>
> **Resolves:** Citation context gap ("WHY does paper X cite paper Y?")
>
> **Prerequisites:** SPEC-028 (v3 verification), SPEC-029 (Exa integration)

---

## Summary

Integrate the [Semantic Scholar API](https://www.semanticscholar.org/product/api) as a "good redundancy" source for **citation context extraction**. Semantic Scholar uniquely provides the *intent* and *context* of citations — information not available in OpenAlex, Crossref, or Exa.

---

## Motivation

**Current state:** We know paper A cites paper B (via OpenAlex citation counts).

**Gap:** We don't know *why* A cites B:
- Does A build on B's method?
- Does A refute B's claim?
- Is it just background/related work?

**Semantic Scholar fills this gap:** Citation intent classification and in-context snippets.

---

## Unique Value (Not in OpenAlex)

```json
{
  "citingPaper": {"title": "New Approaches to Sum-Free Sets"},
  "citedPaper": {"title": "Erdős 1965 Conjecture"},
  "intents": ["background", "methodology"],
  "contexts": [
    "Building on the foundational work of [Erdős 1965], we propose..."
  ]
}
```

This tells us: the citing paper *uses Erdős 1965 as methodology*, not just that it cites it.

---

## Scope

### In Scope

1. **Semantic Scholar client** — HTTP client for S2 API
2. **Citation context extraction** — Get WHY papers cite each other
3. **CLI commands:**
   - `erdos refs citations <doi|arxiv_id>` — Show citation contexts
   - `erdos refs citing <doi|arxiv_id>` — Papers that cite this work
   - `erdos refs cited-by <doi|arxiv_id>` — Papers this work cites
4. **Integration with leads** — Annotate leads with citation intent

### Out of Scope

- Author impact metrics (available but not priority)
- Paper recommendations (available but not priority)
- Full citation graph visualization (future spec)

---

## Environment Configuration

```bash
# .env (OPTIONAL - works without authentication)
SEMANTIC_SCHOLAR_API_KEY=your-api-key-here
```

**API key is OPTIONAL.** The API works without authentication:

| Tier | Rate Limit | Notes |
|------|------------|-------|
| Unauthenticated | ~100 req / 5 min (shared pool) | Works immediately |
| Authenticated | 1 req / sec (dedicated) | Requires free application |

For light usage (a few queries per session), unauthenticated access is sufficient.
For heavy batch processing, apply for a free API key at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api).

---

## CLI Interface

### Citation Context Command

```bash
erdos refs citations <identifier> [OPTIONS]

# Examples:
erdos refs citations "10.4007/annals.2008.167.481"  # DOI
erdos refs citations "math/0404188"                   # arXiv ID
erdos refs citations --paper-id "649def34f8be52c8b66281af98ae884c09aef38b"  # S2 ID
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--limit` | 10 | Maximum citations to return |
| `--intent` | all | Filter by intent: background, methodology, result |
| `--json` | false | Machine-readable output |

### Output (Default)

```
Paper: "The primes contain arbitrarily long arithmetic progressions"
Authors: Ben Green, Terence Tao
Year: 2008

Citing Papers (10 of 1,234):

  1. "New bounds on sum-free sets" (2015)
     Intent: methodology
     Context: "Using the density increment strategy of Green-Tao [12], we show..."

  2. "Arithmetic progressions in random subsets" (2019)
     Intent: background
     Context: "Since the breakthrough result of [GT08], there has been..."

  3. "A counterexample to conjecture X" (2021)
     Intent: result (contrasting)
     Context: "While Green-Tao established positive density, we show that..."
```

### Output (--json)

```json
{
  "paper": {
    "title": "The primes contain arbitrarily long arithmetic progressions",
    "authors": ["Ben Green", "Terence Tao"],
    "year": 2008,
    "s2_id": "649def34f8be52c8b66281af98ae884c09aef38b",
    "doi": "10.4007/annals.2008.167.481",
    "arxiv_id": "math/0404188"
  },
  "citations": [
    {
      "citing_paper": {
        "title": "New bounds on sum-free sets",
        "year": 2015,
        "s2_id": "abc123..."
      },
      "intents": ["methodology"],
      "contexts": [
        "Using the density increment strategy of Green-Tao [12], we show..."
      ]
    }
  ],
  "total_citations": 1234,
  "returned": 10
}
```

---

## Architecture

### Module Structure

```
src/erdos/core/
  clients/
    semantic_scholar.py   # HTTP client for S2 API
  providers/
    semantic_scholar.py   # MetadataProvider implementation (optional)
```

### Client Implementation

```python
# src/erdos/core/clients/semantic_scholar.py

from dataclasses import dataclass
from erdos.core.retry import with_retry
from erdos.core.rate_limiter import RateLimiter

@dataclass
class CitationIntent:
    """Citation context from Semantic Scholar."""
    citing_paper_id: str
    citing_paper_title: str
    citing_paper_year: int | None
    intents: list[str]  # background, methodology, result
    contexts: list[str]  # Actual text snippets

@dataclass
class S2Paper:
    """Paper metadata from Semantic Scholar."""
    s2_id: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    arxiv_id: str | None
    citation_count: int

class SemanticScholarClient:
    """HTTP client for Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        # Unauthenticated: 100 requests/5 min
        # Authenticated: 1 request/sec
        self.rate_limiter = RateLimiter(
            requests_per_second=0.33 if api_key is None else 1.0
        )

    def get_paper(self, identifier: str) -> S2Paper:
        """Get paper by DOI, arXiv ID, or S2 ID."""
        ...

    def get_citations(
        self,
        paper_id: str,
        limit: int = 10,
        intent_filter: str | None = None,
    ) -> list[CitationIntent]:
        """Get citation contexts for a paper."""
        ...

    def get_references(
        self,
        paper_id: str,
        limit: int = 10,
    ) -> list[S2Paper]:
        """Get papers this work cites."""
        ...
```

---

## Integration with Research Leads

When adding a lead with DOI/arXiv ID, optionally fetch citation context:

```bash
erdos research lead add 6 --arxiv-id "math/0404188" --fetch-citations
```

This annotates the lead notes with citation intent summary.

---

## Rate Limiting

| Tier | Limit | Behavior |
|------|-------|----------|
| Unauthenticated | 100 req / 5 min | Respect, queue requests |
| Authenticated | 1 req / sec | Respect, queue requests |
| Rate limited (429) | — | Exponential backoff, max 3 retries |

---

## Caching Strategy

Cache paper metadata and citations:

```
literature/cache/s2/
  paper_<s2_id>.json       # Paper metadata
  citations_<s2_id>.json   # Citation contexts
```

Cache TTL: 7 days (citation contexts change slowly).

---

## Testing

### Unit Tests

```python
# tests/unit/clients/test_semantic_scholar.py

def test_s2_client_parses_paper():
    """Verify paper parsing."""
    ...

def test_s2_client_parses_citations():
    """Verify citation context parsing."""
    ...

def test_s2_client_handles_missing_intents():
    """Not all citations have intent classification."""
    ...
```

### Integration Tests

```python
# tests/integration/test_semantic_scholar.py

@pytest.mark.requires_network
def test_s2_get_paper_by_arxiv():
    """Fetch paper by arXiv ID."""
    ...

@pytest.mark.requires_network
def test_s2_get_citation_contexts():
    """Fetch citation contexts."""
    ...
```

---

## Acceptance Criteria

1. [ ] `SEMANTIC_SCHOLAR_API_KEY` documented in `.env.example`
2. [ ] `SemanticScholarClient` respects rate limits
3. [ ] `erdos refs citations` works with DOI and arXiv ID
4. [ ] Citation intent (background/methodology/result) extracted
5. [ ] Context snippets included in output
6. [ ] `--json` output matches documented schema
7. [ ] Caching reduces redundant API calls
8. [ ] Graceful degradation without API key (slower, but works)

---

## References

- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [API Documentation](https://api.semanticscholar.org/api-docs/)
- [Citation Intent Dataset](https://github.com/allenai/scicite)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
