# BUG-056: Exa Client Uses Basic Neural Search Instead of Deep Research

**Priority:** P2 (Medium - suboptimal quality, workaround exists)
**Status:** Fixed (Partial - Config added, CLI flag pending)
**Found:** 2026-01-31
**Fixed:** 2026-01-31
**Commit:** `005dc83`
**Component:** `src/erdos/core/clients/exa.py`, `src/erdos/commands/research/exa.py`
**Vendor Docs:** `docs/vendor-docs/exa/exa-api-reference.md`

---

## Summary

The Exa client is hardcoded to use `type: "neural"` (basic embeddings search) when Exa offers **significantly better** search capabilities that we're paying for but not using:

1. **`type: "deep"`** - Multi-pass agentic search with query expansion (3x cost, much better quality)
2. **Research API** (`/research/v1`) - Full async deep research with structured output ($0.10-$0.50/task)

For a **$500 prize problem** like Erdős Problem 74, using the cheapest search tier is a significant oversight that reduces our ability to find novel mathematical approaches.

---

## The Smoking Gun

### Current Implementation (`src/erdos/core/clients/exa.py:240-251`)

```python
payload = {
    "query": query,
    "numResults": max_results,
    "type": "neural",          # <-- HARDCODED to basic search
    "useAutoprompt": True,
    "contents": {"text": {"maxCharacters": 500}},
}
```

### What Vendor Docs Say (`docs/vendor-docs/exa/exa-api-reference.md:83-89`)

```markdown
### Search Types

| Type | Description |
|------|-------------|
| `auto` | **Default.** Intelligently selects the best method |
| `neural` | Embeddings-based semantic search |
| `fast` | Streamlined search optimized for speed |
| `deep` | Multi-pass with query expansion for highest quality |

**When to use `deep`:** Complex research queries where quality matters more
than speed. The endpoint agentically searches, processes, and searches again
until it finds the highest quality information.
```

### Pricing Comparison (`docs/vendor-docs/exa/exa-api-reference.md:606-609`)

| Search Type | 1-25 results | 26-100 results |
|-------------|--------------|----------------|
| Neural | $5/1k requests | $25/1k requests |
| **Deep** | **$15/1k requests** | **$75/1k requests** |

We're using the **cheapest tier** when the **premium tier is 3x better quality** for only 3x cost.

---

## Impact Analysis

### What We're Missing

1. **Query Expansion:** Deep search automatically generates additional query variations
2. **Multi-Pass Search:** Searches, processes results, searches again for better coverage
3. **Higher Quality Ranking:** Agentic refinement of results

### Real-World Impact on Problem 74

When searching for novel mathematical approaches to a $500 prize problem, the difference between finding:
- **Neural:** 10 results from obvious keyword matches
- **Deep:** 10 results from agentic exploration of the mathematical landscape

...could be the difference between spinning wheels on known approaches and finding a breakthrough.

### Evidence from Today's Session

We ran ~10 Exa queries for Problem 74 and found mostly papers we already knew about. With deep search, we might have discovered:
- More obscure structural graph theory papers
- Recent preprints with novel techniques
- Cross-disciplinary approaches (e.g., from coding theory, finite geometry)

---

## Missing Features Inventory

| Feature | Status | Vendor Doc Section | Value |
|---------|--------|-------------------|-------|
| `type: "deep"` | NOT IMPLEMENTED | Search Types (lines 83-89) | High-quality agentic search |
| `type: "auto"` | NOT IMPLEMENTED | Search Types | Let Exa choose best method |
| `category: "research paper"` | NOT IMPLEMENTED | Categories (lines 115-127) | Filter for academic papers |
| `additionalQueries` | NOT IMPLEMENTED | Request Body (line 97) | Extra query variations (deep only) |
| Research API | NOT IMPLEMENTED | Research Endpoints (lines 455-547) | Full async deep research |
| `contents.summary` | NOT IMPLEMENTED | Contents (line 245) | AI-generated summaries |

---

## Root Cause Analysis

1. **Initial implementation optimized for cost over quality** - reasonable for testing, not for production research
2. **No configuration exposure** - the search type is hardcoded, not configurable
3. **No test coverage** - no tests verify we're using optimal search parameters
4. **Vendor docs imported but not fully utilized** - docs say "deep" is better, code uses "neural"

---

## Robsby Martin's TDD Fix Plan

### Phase 1: Add Configuration (Low Risk)

**Test First:**

```python
# tests/unit/clients/test_exa.py

def test_exa_config_supports_search_type():
    """ExaConfig should support configurable search type."""
    config = ExaConfig(api_key="test", search_type="deep")
    assert config.search_type == "deep"

def test_exa_config_defaults_to_neural():
    """ExaConfig should default to neural for backwards compatibility."""
    config = ExaConfig(api_key="test")
    assert config.search_type == "neural"

def test_exa_config_from_env_reads_search_type(monkeypatch):
    """ExaConfig.from_env should read ERDOS_EXA_SEARCH_TYPE."""
    monkeypatch.setenv("ERDOS_EXA_SEARCH_TYPE", "deep")
    config = ExaConfig.from_env()
    assert config.search_type == "deep"
```

**Implementation:**

```python
# src/erdos/core/clients/exa.py

from typing import Literal

SearchType = Literal["neural", "deep", "auto", "fast"]

@dataclass(frozen=True)
class ExaConfig:
    api_key: str | None = None
    search_type: SearchType = "neural"  # Default for backwards compat
    # ... existing fields ...

    @classmethod
    def from_env(cls) -> ExaConfig:
        app_config = AppConfig.from_env()
        return cls(
            api_key=app_config.exa_api_key or None,
            search_type=os.getenv("ERDOS_EXA_SEARCH_TYPE", "neural"),
            # ... existing fields ...
        )
```

### Phase 2: Wire Through to API Call

**Test First:**

```python
@responses.activate
def test_search_uses_configured_search_type():
    """ExaClient.search should use configured search type."""
    responses.add(
        responses.POST,
        "https://api.exa.ai/search",
        json={"results": []},
        status=200,
    )

    config = ExaConfig(api_key="test", search_type="deep")
    client = ExaClient(config)
    client.search("test query", max_results=5, use_cache=False)

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["type"] == "deep"
```

**Implementation:**

```python
# src/erdos/core/clients/exa.py (in search_with_cache_status)

payload = {
    "query": query,
    "numResults": max_results,
    "type": self.config.search_type,  # <-- Use configured type
    "useAutoprompt": True,
    "contents": {"text": {"maxCharacters": 500}},
}
```

### Phase 3: Add CLI Option

**Test First:**

```python
# tests/unit/commands/research/test_exa.py

def test_exa_search_accepts_search_type_flag(runner, mock_exa_client):
    """CLI should accept --search-type flag."""
    result = runner.invoke(
        app,
        ["search", "74", "test query", "--search-type", "deep"]
    )
    assert result.exit_code == 0
```

**Implementation:**

```python
# src/erdos/commands/research/exa.py

@app.command("search")
def exa_search(
    # ... existing params ...
    search_type: Annotated[
        str,
        typer.Option(
            "--search-type",
            help="Search type: neural, deep, auto, fast (default: neural)",
        ),
    ] = "neural",
) -> None:
```

### Phase 4: Add Category Filter (Bonus)

```python
# Add to CLI
category: Annotated[
    str | None,
    typer.Option(
        "--category",
        help="Filter by category: research paper, pdf, news, etc.",
    ),
] = None,
```

---

## Environment Variable Proposal

Add to `.env.example`:

```bash
# Exa Search Configuration
# Search type: neural (default), deep (best quality, 3x cost), auto, fast
ERDOS_EXA_SEARCH_TYPE=neural

# For high-value research (e.g., prize problems), recommend:
# ERDOS_EXA_SEARCH_TYPE=deep
```

---

## Acceptance Criteria

- [x] `ExaConfig` supports `search_type` field with default `"neural"`
- [x] `ERDOS_EXA_SEARCH_TYPE` env var configures search type
- [ ] `erdos research exa search --search-type deep` CLI option works (Phase 3 - pending)
- [x] API calls use configured search type (verified by test)
- [x] `.env.example` documents the option with recommendation for prize problems
- [ ] Vendor docs reference updated in code comments (pending)

## Resolution (Partial)

Implemented Phases 1-2 from the TDD fix plan:

**Phase 1: Configuration** ✅
- Added `exa_search_type: str = "neural"` to `AppConfig`
- Added `search_type: str = "neural"` to `ExaConfig`
- Wired `ERDOS_EXA_SEARCH_TYPE` env var through `AppConfig.from_env()`

**Phase 2: API Wiring** ✅
- Changed `"type": "neural"` to `"type": self.config.search_type` in payload

**Changes:**
- `src/erdos/core/config.py`: Added `exa_search_type` field
- `src/erdos/core/clients/exa.py`: Added `search_type` to config, use in API payload
- `tests/unit/clients/test_exa.py`: Added 3 tests for search_type
- `.env.example`: Documented `ERDOS_EXA_SEARCH_TYPE` option

**Remaining:**
- Phase 3: CLI `--search-type` flag (separate PR)
- Phase 4: Category filter (bonus feature)

---

## Cost/Benefit Analysis

| Scenario | Neural (Current) | Deep (Proposed) |
|----------|------------------|-----------------|
| 100 queries | $0.50 | $1.50 |
| Finding novel approach for $500 problem | Low confidence | Higher confidence |
| Break-even point | N/A | 1 breakthrough = 333x ROI |

**Recommendation:** For prize problems (74, 6, etc.), default to `deep` search. The 3x cost increase is negligible compared to the potential $500+ prize.

---

## Related

- Vendor docs: `docs/vendor-docs/exa/exa-api-reference.md`
- Client code: `src/erdos/core/clients/exa.py:240-251`
- CLI code: `src/erdos/commands/research/exa.py`
- SPEC-029: Exa Research Integration (archived)

---

## Notes

This bug was discovered during Problem 74 research when we realized our Exa queries were returning mostly known papers despite explicitly searching for novel approaches. A review of vendor docs confirmed we're using the lowest-quality search tier.

The fix is surgical (4 lines of code + config) with high ROI for research quality.
