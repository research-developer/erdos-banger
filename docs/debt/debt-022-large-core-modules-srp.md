# Technical Debt 022: Large Core Modules (SRP Pressure)

**Date:** 2026-01-20
**Status:** Open
**Priority:** P2 (Maintainability / change risk)
**Impact:** Harder reviews, higher bug surface area, slower iteration on ingest/ask features

## Summary

Some `src/erdos/core/` modules are “god modules” that mix multiple responsibilities (I/O, parsing, orchestration, domain decisions). This is not a correctness bug, but it increases coupling and makes changes riskier.

## Evidence

### `src/erdos/core/ingest.py`

- Size: ~826 lines
- Mixes concerns:
  - HTTP fetch + error handling
  - caching / filesystem layout
  - reference parsing/mapping
  - orchestration + reporting structures
- Several long functions (50+ lines) remain (non-exhaustive):
  - `ingest_problem_references` (`src/erdos/core/ingest.py:508`)
  - `_fetch_reference_entry` (`src/erdos/core/ingest.py:731`)

### `src/erdos/core/ask.py`

- Size: ~509 lines
- Mixes concerns:
  - prompt construction (string formatting policy)
  - retrieval query construction
  - subprocess LLM execution + shell parsing
  - user-facing formatting decisions
- Several long functions (50+ lines) remain (non-exhaustive):
  - `ask_question` (`src/erdos/core/ask.py:437`)

## Why This Matters (Clean Code / SRP)

- A change in one concern (e.g., retrieval query policy) requires navigating unrelated code (prompt formatting, subprocess execution).
- Tests tend to broaden unintentionally because there’s no narrow seam for a single concern.
- Multiple responsibilities in one module encourage “just add one more helper” growth over time.

## Proposed Direction (Non-breaking)

Keep public APIs stable, but split by responsibility (example sketch):

- `src/erdos/core/ingest/`
  - `clients.py` (Crossref/arXiv calls)
  - `cache.py` (filesystem/cache policy)
  - `service.py` (orchestration)
  - `models.py` (ingest result structures)
- `src/erdos/core/ask/`
  - `prompt.py` (prompt template / policy)
  - `retrieval.py` (query building + retrieval)
  - `llm.py` (subprocess runner + parsing)
  - `service.py` (ask orchestration)

## Acceptance Criteria

- No CLI behavior change (golden tests still pass).
- Unit tests can target prompt/retrieval/llm independently (narrower fixtures, less mocking).
- `src/erdos/core/ingest.py` and `src/erdos/core/ask.py` shrink to small composition modules (or are replaced by packages) without circular imports.
