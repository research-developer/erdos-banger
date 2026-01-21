# Vendor Docs (Reference Notes)

This directory contains **reference notes** about third-party APIs, CLIs, and services that `erdos-banger` may integrate with.

Guidelines:

- **Do not commit secrets.** Keep API keys in local `.env` (gitignored).
- Prefer **links + summaries** over copying large vendor documentation verbatim.
- If a vendor provides an OpenAPI spec under a compatible license, store a **pinned copy** and record the source URL + retrieval date.

---

## API Source Hierarchy (Target Design)

This diagram describes the intended “ports + adapters” shape. **Current state:** metadata fetching is still wired via concrete clients in `src/erdos/core/ingest/fetch.py` and is tracked as `docs/debt/debt-038-metadata-provider-abstraction.md`.

```
┌─────────────────────────────────────────────────────────────┐
│               MetadataProvider (Protocol/Port)              │
│  get_by_doi(doi) -> ReferenceRecord                         │
│  get_by_arxiv(arxiv_id) -> ReferenceRecord                  │
│  search(query) -> List[ReferenceRecord]                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  OpenAlex    │   │   arXiv      │   │  Crossref    │
│  (PRIMARY)   │   │  (SOURCE)    │   │  (FALLBACK)  │
│              │   │              │   │              │
│ • metadata   │   │ • LaTeX/TeX  │   │ • If OpenAlex│
│ • citations  │   │ • HTML       │   │ • Direct DOI │
│ • topics     │   │ • Abstract   │   │   lookup     │
│ • deduped    │   │              │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Role Assignments (Rob C. Martin SRP)

| API | Role | When to Call |
|-----|------|--------------|
| **OpenAlex** | **Primary metadata source** | Always first for DOI/title/author/abstract/citations |
| **arXiv** | **Source content provider** | When we need LaTeX/TeX for extraction (content, not metadata) |
| **Crossref** | **Fallback only** | If OpenAlex returns nothing (rare edge cases) |

### Why OpenAlex as Primary

1. **Already aggregates Crossref** - calling both is redundant
2. **Built-in deduplication** - matches arXiv preprint ↔ journal version
3. **Richer metadata** - citations, topics, concepts, institutions
4. **More generous anonymous quota** than Crossref’s polite pool
5. **Open data** - CC0 license, no auth required

### Future: "Good Redundancy" Sources

These add NEW information not available in OpenAlex:

| Source | Unique Value |
|--------|--------------|
| **Semantic Scholar** | Citation context (who cites what and WHY) |
| **zbMATH Open** | Math-specific MSC codes, math reviews |
| **Exa Research** | Agentic natural language synthesis |

---

## Vendors

### Metadata Sources

- `openalex/` — OpenAlex (open scholarly metadata API) — **PRIMARY**
- `crossref/` — Crossref REST API (DOI metadata) — **FALLBACK**
- `arxiv/` — arXiv API + e-print tarball download — **SOURCE CONTENT**

### Theorem Proving

- `harmonic-aristotle/` — Harmonic Aristotle (Lean theorem proving service + `aristotlelib` / `aristotle` CLI)

### Content Processing

- `marker/` — Marker PDF → Markdown conversion

### LLM Providers

- `openai/` — OpenAI Responses API (used by local LLM wrapper scripts)
- `anthropic/` — Anthropic Messages API (used by local LLM wrapper scripts)
