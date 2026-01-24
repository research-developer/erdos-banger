# SPEC-030: Semantic Scholar API Integration

> **Status:** Complete
>
> **Target:** v3.3
>
> **Resolves:** Citation context gap ("WHY does paper X cite paper Y?")
>
> **Prerequisites:** SPEC-028 (v3 verification)

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
3. **CLI commands (new `s2` namespace under `erdos refs`):**
   - `erdos refs s2 citations <doi|arxiv_id|s2_id>` — Citation contexts + intents (incoming)
   - `erdos refs s2 cited-by <doi|arxiv_id|s2_id>` — List citing papers (incoming, no contexts)
   - `erdos refs s2 references <doi|arxiv_id|s2_id>` — List referenced papers (outgoing)
4. **CLI compatibility** — Preserve existing `erdos refs <problem_id>` behavior while adding `erdos refs s2 ...` subcommands
5. **Integration with leads** — Annotate leads with citation intent (opt-in)

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
erdos refs s2 citations <identifier> [OPTIONS]

# Examples:
erdos refs s2 citations "10.4007/annals.2008.167.481"   # DOI
erdos refs s2 citations "math/0404188"                  # arXiv ID
erdos refs s2 citations "649def34f8be52c8b66281af98ae884c09aef38b"  # S2 Paper ID
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--limit` | 10 | Maximum citations to return |
| `--intent` | all | Filter by intent: background, methodology, result |

**JSON mode:** use the global flag: `erdos --json refs s2 citations ...`

### Output (Default)

```text
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

### Output (JSON mode)

```json
{
  "schema_version": 1,
  "command": "erdos refs s2 citations",
  "success": true,
  "data": {
    "identifier": "10.4007/annals.2008.167.481",
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
  },
  "error": null,
  "timestamp": "2026-01-23T12:00:00Z",
  "duration_ms": 0
}
```

### Cited-By Command (No Context)

List papers that cite the given paper, without fetching context snippets (faster, less data).

```bash
erdos refs s2 cited-by <identifier> [OPTIONS]
```

Options:

| Option | Default | Description |
|--------|---------|-------------|
| `--limit` | 10 | Maximum citing papers to return |

**JSON mode:** use the global flag: `erdos --json refs s2 cited-by ...`

### References Command

List papers referenced by the given paper (outgoing citations).

```bash
erdos refs s2 references <identifier> [OPTIONS]
```

Options:

| Option | Default | Description |
|--------|---------|-------------|
| `--limit` | 10 | Maximum references to return |

**JSON mode:** use the global flag: `erdos --json refs s2 references ...`

---

## Architecture

### Module Structure

```text
src/erdos/core/
  clients/
    semantic_scholar.py   # HTTP client for S2 API
src/erdos/commands/
  refs.py                 # `erdos refs <problem_id>` (existing) + `s2` subcommands (new)
  refs_s2.py              # Registers the `refs s2 ...` subcommands into refs.app
```

### CLI Compatibility Notes

`erdos refs` is currently implemented as `erdos refs <problem_id>` with a required argument. To add `erdos refs s2 ...` subcommands without breaking the existing behavior, implementation MUST:

1. Make the callback `problem_id` argument optional, and only require it when no subcommand is invoked.
2. Check `ctx.invoked_subcommand` in the callback and return early when a subcommand is present.
3. Keep `erdos refs <problem_id>` working as-is (compat alias), even if a future refactor introduces `erdos refs problem <problem_id>`.

### Client Implementation

```python
# src/erdos/core/clients/semantic_scholar.py

from dataclasses import dataclass
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
        # Repo RateLimiter is delay-based, not QPS-based.
        # Conservative defaults:
        # - unauthenticated: sleep ~3s between calls
        # - authenticated: sleep ~1s between calls
        self.rate_limiter = RateLimiter(delay_seconds=3.0 if api_key is None else 1.0)

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

```text
literature/cache/s2/
  paper_<s2_id>.json       # Paper metadata
  citations_<s2_id>.json   # Citation contexts
  cited_by_<s2_id>.json    # Citing papers (no contexts)
  references_<s2_id>.json  # Outgoing references
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
3. [ ] Existing `erdos refs <problem_id>` remains functional
4. [ ] `erdos refs s2 citations` works with DOI and arXiv ID
5. [ ] `erdos refs s2 cited-by` works with DOI and arXiv ID
6. [ ] `erdos refs s2 references` works with DOI and arXiv ID
7. [ ] Citation intent (background/methodology/result) extracted when present
8. [ ] Context snippets included in `citations` output
9. [ ] `--json` output matches documented schema (all 3 subcommands)
10. [ ] Caching reduces redundant API calls
11. [ ] `erdos research lead add ... --fetch-citations` annotates lead notes (opt-in; best-effort)
12. [ ] Graceful degradation without API key (slower, but works)

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
