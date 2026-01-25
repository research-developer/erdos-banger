# Future Ideations: Erdős-Banger Roadmap & Tool Integration

> **Document Status:** Non-normative roadmap (accurate-by-construction)
>
> **Last Updated:** 2026-01-23
>
> This document intentionally avoids factual claims about external products/benchmarks. For implementable, testable work, the SSOT is `docs/_specs/README.md`.

---

## What This Is

- A map of future integrations and how they fit the current architecture.
- A pointer index to the corresponding specs (ironclad, test-driven).

## Architectural Principles (Stable)

1. **Canonical state is repo-local text artifacts** (mergeable, reviewable):
   - `research/` workspace (v3)
2. **Derived stores are regenerable** (not SSOT):
   - `index/erdos.sqlite` search DB
   - `literature/cache/`, `literature/extracts/` caches
   - `logs/` run and loop logs
3. **Vendor-neutral LLM integration**:
   - LLMs are invoked via external commands (`ERDOS_LLM_COMMAND`)
   - Task-level routing is done by selecting different commands/scripts (SPEC-032)
4. **Good redundancy only**:
   - Add a new research API only if it contributes *new* information not already in OpenAlex/Crossref/arXiv.

## Spec-Backed Roadmap

| Spec | Theme | What It Adds |
|------|-------|--------------|
| SPEC-029 | Exa Research Integration | Agentic literature synthesis → research leads |
| SPEC-030 | Semantic Scholar Integration | Citation intent/context (“why cite”) |
| SPEC-031 | zbMATH Integration | Math-native metadata (MSC, reviews excerpt policy) |
| SPEC-032 | Multi-Model Routing | Task → LLM command routing (no SDK lock-in) |
| SPEC-033 | Lean Copilot Integration | In-editor tactic suggestions via external API server |
| SPEC-034 | Progress Dashboard | Terminal dashboard + JSON snapshot mode |

## Reference Architecture (End-to-End)

```text
Problems dataset + metadata APIs
  - Problems YAML (local)
  - OpenAlex / Crossref / arXiv (existing)
  - (future) Exa / Semantic Scholar / zbMATH
            │
            ▼
Canonical research state (SSOT)
  research/problems/<id>/
    meta.yaml
    SYNTHESIS.md
    leads/*.yaml, attempts/*.yaml, hypotheses/*.yaml, tasks/*.yaml
            │
            ▼
Derived retrieval index
  index/erdos.sqlite (FTS5 + optional embeddings)
            │
            ▼
CLI orchestration
  erdos research | search | ask | loop run | logs | ...
            │
            ├─► LLM via external command(s) (SPEC-032)
            │      ERDOS_LLM_COMMAND=...
            │      ERDOS_LLM_COMMAND_MATH=...
            │      ERDOS_LLM_COMMAND_CODE=...
            │
            └─► (future) Lean Copilot external API (SPEC-033)
                   erdos lean copilot serve  (localhost)
```

## Example Workflows (Aligned With Current CLI)

### Research → Ask

```bash
erdos research init 6
erdos research lead add 6 --title "..." --notes "..."
erdos research synthesize 6
erdos --json ask 6 "What have we tried so far?" --no-llm
```

### Research → Loop

```bash
erdos research init 6
erdos research synthesize 6
ERDOS_LLM_COMMAND=./scripts/llm.sh erdos loop run 6 --max-iter 10
```

### Summarize Activity

```bash
erdos logs --since 7d --summary
```

## Open Questions (Pre-Spec / Needs Design)

1. Should we add a “paper identity” module (DOI/arXiv/S2/zbl normalization) before integrating more APIs?
2. If we add vector search, do we want it for:
   - literature only, or also research artifacts?
3. For Lean Copilot `/encode`, should embeddings be:
   - local (sentence-transformers), or
   - remote (API), or
   - optional with a clear degraded mode?
