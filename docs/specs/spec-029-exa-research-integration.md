# SPEC-029: Exa Research API Integration

> **Status:** Pending
>
> **Target:** v3.2
>
> **Resolves:** Agentic literature synthesis gap
>
> **Prerequisites:** SPEC-028 (v3 verification complete)

---

## Summary

Integrate the [Exa Research API](https://exa.ai/) as a "good redundancy" source for agentic literature synthesis. Exa provides structured research queries with automatic source clustering and summarization — capabilities not available in OpenAlex/Crossref/arXiv.

---

## Motivation

Current literature workflow:
1. Manual discovery of relevant papers
2. `erdos ingest` to fetch metadata + content
3. `erdos ask` for RAG-based Q&A

**Gap:** No automated way to ask "What approaches exist for problem X?" and get structured, cited answers.

**Exa fills this gap:** Natural language research queries with structured JSON output, automatic citation, and 94.9% accuracy on SimpleQA.

---

## Scope

### In Scope

1. **Exa client** — HTTP client for Exa Research API
2. **CLI command** — `erdos research exa <problem_id> "<query>"`
3. **Structured output** — Exa responses stored as research leads
4. **Rate limiting** — Respect Exa API limits
5. **Caching** — Cache responses to avoid redundant API calls

### Out of Scope

- Exa as a replacement for OpenAlex (complementary, not replacing)
- Automatic problem-to-query mapping (user provides query)
- Real-time streaming responses

---

## Environment Configuration

```bash
# .env
EXA_API_KEY=your-exa-api-key-here
```

---

## CLI Interface

### Primary Command

```bash
erdos research exa <problem_id> "<query>" [OPTIONS]

# Examples:
erdos research exa 6 "What approaches have been tried for sum-free sets?"
erdos research exa 42 "Progress on arithmetic progressions in primes" --max-results 10
erdos research exa 124 "Techniques for graph coloring bounds" --save-leads
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--max-results` | 5 | Maximum number of sources to return |
| `--save-leads` | false | Auto-create lead records from results |
| `--output-schema` | default | Custom JSON schema for structured extraction |
| `--json` | false | Machine-readable output |

### Output (Default)

```
Query: "What approaches have been tried for sum-free sets?"

Sources (3):
  1. [Green-Tao 2008] "The primes contain arbitrarily long arithmetic progressions"
     - arXiv: math/0404188
     - Relevance: Density arguments applicable to sum-free sets

  2. [Eberhard 2016] "Sum-free sets in abelian groups"
     - DOI: 10.1007/s00222-016-0678-7
     - Relevance: Direct result on sum-free set density

  3. [Alon 2002] "Sum-free subsets"
     - DOI: 10.1007/BF02787556
     - Relevance: Probabilistic methods for existence

Synthesis:
  - Main approaches: density arguments, probabilistic methods, algebraic structure
  - Open questions: tight bounds for specific group structures
```

### Output (--json)

```json
{
  "query": "What approaches have been tried for sum-free sets?",
  "problem_id": 6,
  "sources": [
    {
      "title": "The primes contain arbitrarily long arithmetic progressions",
      "authors": ["Ben Green", "Terence Tao"],
      "year": 2008,
      "arxiv_id": "math/0404188",
      "doi": null,
      "relevance": "Density arguments applicable to sum-free sets",
      "url": "https://arxiv.org/abs/math/0404188"
    }
  ],
  "synthesis": {
    "approaches": ["density arguments", "probabilistic methods", "algebraic structure"],
    "open_questions": ["tight bounds for specific group structures"]
  },
  "cached": false,
  "timestamp": "2026-01-23T12:00:00Z"
}
```

---

## Architecture

### Module Structure

```
src/erdos/core/
  clients/
    exa.py              # HTTP client for Exa API
  research/
    exa_integration.py  # Exa → research workspace integration
```

### Exa Client

```python
# src/erdos/core/clients/exa.py

from dataclasses import dataclass
from erdos.core.retry import with_retry
from erdos.core.rate_limiter import RateLimiter

@dataclass
class ExaSource:
    title: str
    authors: list[str]
    year: int | None
    arxiv_id: str | None
    doi: str | None
    url: str
    relevance: str

@dataclass
class ExaResearchResult:
    query: str
    sources: list[ExaSource]
    synthesis: dict
    cached: bool

class ExaClient:
    """HTTP client for Exa Research API."""

    BASE_URL = "https://api.exa.ai/research"

    def __init__(self, api_key: str, rate_limiter: RateLimiter | None = None):
        self.api_key = api_key
        self.rate_limiter = rate_limiter or RateLimiter(requests_per_second=1)

    @with_retry(max_attempts=3, backoff_base=2.0)
    def research(
        self,
        query: str,
        max_results: int = 5,
        output_schema: dict | None = None,
    ) -> ExaResearchResult:
        """Execute a research query against Exa API."""
        ...
```

### Integration with Research Workspace

```python
# src/erdos/core/research/exa_integration.py

def exa_to_leads(
    result: ExaResearchResult,
    problem_id: int,
    store: ResearchStore,
) -> list[str]:
    """Convert Exa sources to lead records.

    Returns list of created lead IDs.
    """
    lead_ids = []
    for source in result.sources:
        lead = LeadRecord(
            problem_id=problem_id,
            id=generate_lead_id(),
            title=source.title,
            status=LeadStatus.NEW,
            priority=Priority.MEDIUM,
            source=LeadSource(
                doi=source.doi,
                arxiv_id=source.arxiv_id,
                url=source.url,
            ),
            notes=f"[Exa] {source.relevance}",
            created_at=now(),
            updated_at=now(),
        )
        store.save_lead(lead)
        lead_ids.append(lead.id)
    return lead_ids
```

---

## Caching Strategy

Cache Exa responses to avoid redundant API calls:

```
literature/cache/exa/
  <query_hash>.json    # Cached response
```

Cache key: SHA256 of normalized query string.
Cache TTL: 24 hours (configurable via `ERDOS_EXA_CACHE_TTL`).

---

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing API key | Exit with error: "EXA_API_KEY not set" |
| Rate limited (429) | Retry with exponential backoff |
| Invalid response | Log warning, return partial results |
| Network error | Retry up to 3 times, then fail |

---

## Testing

### Unit Tests

```python
# tests/unit/clients/test_exa.py

def test_exa_client_parses_response():
    """Verify response parsing."""
    ...

def test_exa_client_handles_rate_limit():
    """Verify retry on 429."""
    ...

def test_exa_to_leads_creates_records():
    """Verify lead creation from Exa results."""
    ...
```

### Integration Tests (requires API key)

```python
# tests/integration/test_exa_integration.py

@pytest.mark.requires_network
@pytest.mark.requires_exa_key
def test_exa_research_query():
    """End-to-end Exa query."""
    ...
```

---

## Acceptance Criteria

1. [ ] `EXA_API_KEY` documented in `.env.example`
2. [ ] `ExaClient` implements rate limiting and retry
3. [ ] `erdos research exa` command works end-to-end
4. [ ] `--save-leads` creates valid lead records
5. [ ] `--json` output matches documented schema
6. [ ] Responses are cached for 24 hours
7. [ ] Missing API key produces clear error message
8. [ ] Unit tests cover client and integration logic

---

## Dependencies

```toml
# pyproject.toml (optional extra)
[project.optional-dependencies]
exa = ["exa-py>=1.0"]
```

Or implement direct HTTP client (preferred for minimal dependencies).

---

## References

- [Exa Research API](https://exa.ai/blog/introducing-exa-research)
- [Exa API Docs](https://docs.exa.ai/)
- [Exa Python SDK](https://github.com/exa-labs/exa-py)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
