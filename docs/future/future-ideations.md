# Future Ideations: Erdős-Banger Roadmap & Tool Integration

> **Document Status:** Living document for tracking future enhancements, tool integrations, and architectural decisions.
>
> **Last Updated:** 2026-01-19

---

## Executive Summary

This document outlines potential integrations and architectural enhancements for erdős-banger based on the 2026 AI/ML landscape. The core insight: **the tooling now exists to make autonomous Erdős problem solving viable**. Harmonic's Aristotle system has already solved multiple Erdős problems using the exact approach we're building toward.

---

## Table of Contents

1. [The 2026 Landscape](#the-2026-landscape)
2. [Lean Copilot Integration](#lean-copilot-integration)
3. [Frontier LLMs for Mathematical Reasoning](#frontier-llms-for-mathematical-reasoning)
4. [Harmonic Aristotle: Proof of Concept](#harmonic-aristotle-proof-of-concept)
5. [Research APIs](#research-apis)
6. [Recommended Architecture](#recommended-architecture)
7. [Implementation Priority](#implementation-priority)
8. [Open Questions](#open-questions)

---

## The 2026 Landscape

### What's Changed

The AI theorem proving landscape has fundamentally shifted:

| Development | Impact |
|-------------|--------|
| Harmonic's Aristotle solves Erdős #124 | Proves autonomous Erdős solving is possible |
| DeepSeek-Prover-V2 open-sourced | Purpose-built Lean 4 prover available |
| Lean Copilot supports external APIs | Can use GPT-5.2/Claude/Gemini directly in Lean |
| Exa Research API launched | Agentic literature research with structured output |
| GPT-5.2 achieves 100% on AIME 2025 | Frontier LLMs now competitive with math olympiad gold medalists |

### Key Validation

Harmonic's Aristotle system has:
- Solved Erdős Problem #124 in 6 hours with 100% autonomy
- Written the majority of public formalized solutions on erdosproblems.com
- Achieved gold-medal level on IMO 2025 (5 of 6 problems)
- Been verified by Terence Tao personally

**This is not vaporware territory. The approach works.**

---

## Lean Copilot Integration

### Overview

[Lean Copilot](https://github.com/lean-dojo/LeanCopilot) is a framework for running LLM inference natively in Lean 4. It provides:

- `suggest_tactics` - LLM suggests next proof steps
- `search_proof` - LLM + aesop searches for multi-tactic proofs
- `select_premises` - Retrieves relevant lemmas/theorems

### External API Support (Critical Feature)

**Lean Copilot supports external models through `ExternalGenerator` and `ExternalEncoder`.**

This means you can use ANY LLM (GPT-5.2, Claude Opus 4.5, Gemini 3 Pro) as the backend:

```
┌─────────────────────────────────────────────────────────────┐
│                    Lean 4 Proof Environment                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   theorem erdos_42 : ... := by                              │
│     suggest_tactics  -- Calls external API                  │
│                      -- GPT-5.2 suggests: "apply Nat.le"    │
│     search_proof     -- Orchestrates multi-step search      │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              External Model API Server                      │
│           (implements external_model_api.yaml)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   class ExternalGenerator:                                  │
│       def generate(self, prompt: str) -> list[str]:         │
│           # Call GPT-5.2, Claude, or Gemini API             │
│           response = openai.chat.completions.create(...)    │
│           return [tactic for tactic in response]            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Integration Steps

1. **Add Lean Copilot to lakefile.lean:**
   ```lean
   require LeanCopilot from git "https://github.com/lean-dojo/LeanCopilot.git" @ "v4.23.0"
   ```

2. **Implement external_model_api.yaml wrapper:**
   Create a Python server that:
   - Receives tactic generation requests from Lean
   - Forwards to frontier LLM API (OpenAI, Anthropic, Google)
   - Returns structured tactic suggestions

3. **Configure Lean Copilot to use external endpoint:**
   Point `ExternalGenerator` to your API server

### Why This Matters

- **No local GPU required** - Inference happens on cloud APIs
- **Use the best model** - GPT-5.2 for math, Claude for code generation
- **Seamless workflow** - Tactics appear in Lean editor like native suggestions
- **Verifiable** - Every suggestion is checked by Lean compiler

### References

- [Lean Copilot GitHub](https://github.com/lean-dojo/LeanCopilot)
- [Lean Copilot Paper (arXiv)](https://arxiv.org/abs/2404.12534)
- [LeanDojo Project](https://leandojo.org/)

---

## Frontier LLMs for Mathematical Reasoning

### 2026 Benchmark Comparison

| Model | AIME 2025 | ARC-AGI-2 | SWE-bench | Best For |
|-------|-----------|-----------|-----------|----------|
| **GPT-5.2** | 100% | 52.9% | 72.1% | Mathematical reasoning |
| **Claude Opus 4.5** | 92.8% | 37.6% | 80.9% | Coding, agentic workflows |
| **Gemini 3 Pro** | 95% | 31.1% | 71.4% | Complex reasoning, multimodal |

### Recommendation: GPT-5.2 for Math, Claude for Code

**For theorem proving (tactic generation):** GPT-5.2
- 100% on AIME 2025 without tools
- Best abstract reasoning (ARC-AGI-2)
- Explicitly optimized for multi-step mathematical reasoning

**For code generation (skeleton writing, tooling):** Claude Opus 4.5
- 80.9% on SWE-bench Verified (best in class)
- Excellent at agentic, multi-step workflows
- Better at following complex instructions

**For research synthesis:** Either works, consider Exa Research API

### API Configuration

```bash
# .env file
OPENAI_API_KEY=sk-...          # For GPT-5.2 (math reasoning)
ANTHROPIC_API_KEY=sk-ant-...   # For Claude (code generation)
GOOGLE_API_KEY=...             # For Gemini (optional)
EXA_API_KEY=...                # For literature research
```

### Model Selection Strategy

```python
# Pseudocode for model routing
def select_model(task_type: str) -> str:
    match task_type:
        case "tactic_generation":
            return "gpt-5.2"  # Best for math
        case "proof_search":
            return "gpt-5.2"  # Best for math
        case "code_generation":
            return "claude-opus-4.5"  # Best for code
        case "literature_research":
            return "exa-research"  # Purpose-built
        case "general_reasoning":
            return "gpt-5.2"  # Default to math-optimized
```

### References

- [AI Model Benchmarks Jan 2026 | LM Council](https://lmcouncil.ai/benchmarks)
- [Flagship Model Report: GPT-5.1 vs Gemini 3 Pro vs Claude Opus 4.5](https://www.vellum.ai/blog/flagship-model-report)
- [2025 LLM Review | Atoms.dev](https://atoms.dev/blog/2025-llm-review-gpt-5-2-gemini-3-pro-claude-4-5)

---

## Harmonic Aristotle: Proof of Concept

### What Is Aristotle?

Aristotle is Harmonic's automated theorem proving system that combines:
- Reinforcement learning
- Monte Carlo tree search
- Lean 4 formal verification
- Informal-to-formal reasoning bridge

### Erdős Problem Achievements

| Achievement | Details |
|-------------|---------|
| Erdős Problem #124 | Solved in 6 hours, 100% autonomous |
| Multiple Erdős problems | Solved and formally verified |
| IMO 2025 | Gold medal level (5 of 6 problems) |
| erdosproblems.com | Wrote majority of public formalized solutions |

### Architecture Insights

Aristotle's approach validates our architecture:

```
1. Problem Selection
   └── Identify tractable problems from corpus

2. Informal Reasoning
   └── LLM generates candidate proof strategies
   └── Explore multiple approaches in parallel

3. Auto-Formalization
   └── Convert informal proofs to Lean statements
   └── This is the bottleneck - requires careful prompt engineering

4. Formal Verification
   └── Lean compiler validates or rejects
   └── 100% correctness guarantee

5. Iteration
   └── Failed proofs inform next attempt
   └── Log everything for learning
```

### Key Lesson: The Long Tail

Terence Tao's observation (verified by Aristotle's success):

> "There are a large number of problems that are actually relatively easy to prove or disprove, but due to the limited number of expert mathematicians who can actually invest in research, these problems have received little attention."

**Implication:** Target the "long tail" of easier Erdős problems first. AI can harvest these while humans focus on the harder ones.

### Collaboration Model

Reports indicate GPT-5.2 + Aristotle collaboration:
- GPT-5.2: Generates initial solution and informal proof
- Aristotle: Auto-formalizes to Lean, verifies correctness

This suggests a multi-model approach may be optimal.

### References

- [Harmonic News](https://harmonic.fun/news)
- [GPT-5.2 and Harmonic Solve Erdős Problem | OfficeChai](https://officechai.com/ai/gpt-5-2-and-harmonic-appear-to-have-autonomously-solved-an-erdos-problem-that-had-been-unsolved-by-humans-thus-far/)
- [Three Erdős Problems Fell in Seven Days | Medium](https://medium.com/@cognidownunder/three-erd%C5%91s-problems-fell-in-seven-days-and-terence-tao-verified-every-proof-himself-1a1ff4399bc6)
- [Aristotle IMO Paper (arXiv)](https://arxiv.org/abs/2510.01346)

---

## Research APIs: Good Redundancy Strategy

### Principles: Good vs Bad Redundancy

**Bad redundancy (avoid):**
- Calling multiple APIs for the SAME data
- Example: Crossref + OpenAlex for DOI metadata → redundant, OpenAlex includes Crossref

**Good redundancy (pursue):**
- Calling APIs for DIFFERENT, complementary data
- Each source adds NEW information not available elsewhere

### API Orchestration Architecture

**Status:** Target architecture. Current metadata fetching is still wired via concrete clients in `src/erdos/core/ingest/fetch.py` and tracked as `docs/debt/debt-038-metadata-provider-abstraction.md`.

```
┌─────────────────────────────────────────────────────────────┐
│                    erdos ingest <id>                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
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
        │
        │ Future: "Good Redundancy" Sources
        │ (each adds NEW information)
        │
        ├──► Semantic Scholar: Citation context (who cites what and WHY)
        ├──► Exa Research: Natural language synthesis, agentic queries
        └──► zbMATH Open: Math-specific metadata not in general databases
```

### Good Redundancy Sources (Future v1.3+)

| Source | Unique Value | Not Available Elsewhere |
|--------|--------------|------------------------|
| **Semantic Scholar** | Citation context extraction | "This paper cites X to refute claim Y" |
| **Exa Research** | Agentic research synthesis | Natural language queries with structured output |
| **zbMATH Open** | Math-specific classification | MSC codes, math reviews, equation search |
| **CORE** | Institutional repositories | Grey literature, theses, working papers |

### Exa Research API

[Exa](https://exa.ai/) provides agentic research capabilities that could replace or augment our Spec 010-011 pipeline.

**Key Features:**
- Natural language research queries
- Structured JSON output with citations
- 94.9% accuracy on SimpleQA
- Automatic source clustering and summarization

**Example Integration:**

```python
import exa

response = exa.research(
    query="What approaches have been tried for Erdős conjecture on sum-free sets?",
    output_schema={
        "approaches": [{"name": str, "paper": str, "year": int, "outcome": str}],
        "key_papers": [{"title": str, "authors": list, "arxiv_id": str}],
        "open_questions": [str],
        "related_problems": [int]  # Erdős problem numbers
    }
)
```

**Potential Use Cases:**
- Literature review for specific problems
- Finding related work before formalizing
- Identifying which problems have partial progress
- Building the knowledge base for RAG

### OpenAlex API

[OpenAlex](https://docs.openalex.org/) remains valuable for bulk metadata:
- Free, 100k requests/day
- No authentication required
- Good for systematic corpus building

**Use OpenAlex for:** Bulk ingestion, citation graphs, author disambiguation
**Use Exa for:** Targeted research queries, synthesis, structured extraction

### Semantic Scholar API (Good Redundancy)

[Semantic Scholar](https://www.semanticscholar.org/product/api) offers:
- **Citation context extraction** - WHY a paper cites another (unique value)
- Paper recommendations
- Author impact metrics

**Unique value not in OpenAlex:**
```python
# Semantic Scholar provides citation intent
{
    "citingPaper": {"title": "New Approaches to Sum-Free Sets"},
    "citedPaper": {"title": "Erdős 1965 Conjecture"},
    "intents": ["background", "methodology"],
    "contexts": [
        "Building on the foundational work of [Erdős 1965], we propose..."
    ]
}
```

**Use case:** Finding which papers BUILD ON vs REFUTE an Erdős-related result.

### zbMATH Open API (Good Redundancy)

[zbMATH Open](https://zbmath.org/) is the Zentralblatt MATH database - the gold standard for pure mathematics:

- **MSC codes** (Mathematics Subject Classification) - precise topic hierarchy
- **Math reviews** - expert summaries not available elsewhere
- **Equation search** - find papers by mathematical formula
- **100+ years of coverage** - historical math literature

**API:** `https://api.zbmath.org/`

**Unique value not in OpenAlex:**
```python
# zbMATH provides math-specific classification
{
    "de": "1234567",  # zbMATH identifier
    "msc": ["11B05", "05D10"],  # MSC codes
    "review": "The author proves a variant of Szemerédi's theorem...",
    "keywords": ["arithmetic progressions", "density", "combinatorics"]
}
```

**Use case:** Finding ALL papers in a specific mathematical subfield (e.g., "additive combinatorics" = MSC 11B30).

### References

- [Exa Research API](https://exa.ai/blog/introducing-exa-research)
- [Exa API 2.0](https://exa.ai/blog/exa-api-2-0)
- [OpenAlex Documentation](https://docs.openalex.org/)
- [Semantic Scholar API](https://www.semanticscholar.org/product/api)

---

## Recommended Architecture

### Updated System Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ERDŐS-BANGER v2.0                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│  │  Problems   │   │    Exa      │   │  OpenAlex   │   │  Semantic   │  │
│  │   (YAML)    │   │  Research   │   │     API     │   │   Scholar   │  │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘  │
│         │                 │                 │                 │         │
│         └─────────────────┼─────────────────┼─────────────────┘         │
│                           ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    SQLite FTS5 + Literature Cache               │    │
│  │              (problems, papers, abstracts, chunks)              │    │
│  └──────────────────────────────┬──────────────────────────────────┘    │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                         erdos CLI                               │    │
│  │        list | show | search | ask | ingest | lean | loop        │    │
│  └──────────────────────────────┬──────────────────────────────────┘    │
│                                 │                                       │
│         ┌───────────────────────┼───────────────────────┐               │
│         ▼                       ▼                       ▼               │
│  ┌─────────────┐   ┌───────────────────────┐   ┌─────────────────┐      │
│  │   GPT-5.2   │   │      Lean 4 +         │   │  Claude Opus    │      │
│  │   (Math)    │◄─►│    Lean Copilot       │◄─►│  4.5 (Code)     │      │
│  └─────────────┘   │  (External API Mode)  │   └─────────────────┘      │
│                    └───────────┬───────────┘                            │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                  Proof Attempts + Logs                          │    │
│  │                 formal/lean/Erdos/*.lean                        │    │
│  │                 logs/attempts/*.json                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. RESEARCH PHASE
   erdos ask 42 "What's known about this problem?"
   └── Exa Research API → structured literature review
   └── Cache results in literature/manifests/

2. FORMALIZATION PHASE
   erdos lean formalize 42
   └── Claude Opus 4.5 generates skeleton (best at code)
   └── Output: formal/lean/Erdos/Problem0042.lean

3. PROVING PHASE
   erdos lean check 42 --with-copilot
   └── Lean Copilot (backed by GPT-5.2) suggests tactics
   └── User/agent applies suggestions
   └── Lean compiler validates

4. ITERATION PHASE
   erdos loop 42 --max-attempts 100
   └── Automated loop: generate → check → log → retry
   └── GPT-5.2 for tactic generation
   └── All attempts logged for analysis

5. ANALYSIS PHASE
   erdos logs analyze 42
   └── What tactics were tried?
   └── Where did proofs get stuck?
   └── What knowledge gaps exist?
```

### Configuration

```yaml
# config/models.yaml
models:
  math_reasoning:
    provider: openai
    model: gpt-5.2
    temperature: 0.2
    max_tokens: 4096

  code_generation:
    provider: anthropic
    model: claude-opus-4.5
    temperature: 0.1
    max_tokens: 8192

  research:
    provider: exa
    endpoint: research
    model: exa-research-pro

lean_copilot:
  external_api:
    url: http://localhost:8000
    model: gpt-5.2
```

---

## Implementation Priority

### Phase 1: Foundation (Current - v1.1)

| Task | Spec | Status | Notes |
|------|------|--------|-------|
| Literature ingestion | 010 | Pending | Use OpenAlex first, add Exa later |
| Ask command | 011 | Pending | Start with simple prompt, evolve |
| API key management | - | Pending | Add .env support |

### Phase 2: Lean Integration (v1.2)

| Task | Spec | Status | Notes |
|------|------|--------|-------|
| Lean Copilot setup | - | Not started | Add to lakefile.lean |
| External API server | - | Not started | Wrap GPT-5.2 for Lean Copilot |
| Loop command | 012 | Designed | Automated iteration |

### Phase 3: Advanced Research (v1.3)

| Task | Spec | Status | Notes |
|------|------|--------|-------|
| Exa Research integration | - | Not started | Replace/augment ingest |
| Multi-model routing | - | Not started | GPT for math, Claude for code |
| Vector embeddings | 014 | Deferred | Only if FTS5 insufficient |

### Phase 4: Scale & Polish (v1.4+)

| Task | Spec | Status | Notes |
|------|------|--------|-------|
| MCP Server | 017 | Designed | Enable external agent access |
| Batch operations | 015 | Designed | Process multiple problems |
| Progress dashboard | - | Not started | Visualize attempt logs |

---

## Open Questions

### Technical

1. **Lean Copilot version compatibility**
   - Which Lean 4 version does our project use?
   - Is it compatible with current Lean Copilot?

2. **External API latency**
   - How fast do we need tactic suggestions?
   - Is GPT-5.2 API latency acceptable for interactive use?

3. **Token costs**
   - GPT-5.2 pricing for math-heavy prompts?
   - Budget considerations for automated loops?

### Strategic

1. **Harmonic partnership?**
   - Could we integrate with Aristotle directly?
   - Is there an API or are they closed?

2. **Problem selection**
   - Which Erdős problems are in the "long tail"?
   - How do we identify tractable targets?

3. **Verification standards**
   - When is a proof "solved"?
   - Do we need human mathematician review?

### Research

1. **Auto-formalization quality**
   - How often does informal → formal translation fail?
   - What's the bottleneck?

2. **Tactic search efficiency**
   - Beam search vs. MCTS vs. simple sampling?
   - What works best for Erdős-style combinatorics?

---

## Appendix: API Quick Reference

### OpenAI (GPT-5.2)

```python
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-5.2",
    messages=[
        {"role": "system", "content": "You are a mathematical theorem prover..."},
        {"role": "user", "content": f"Suggest a tactic for: {goal}"}
    ],
    temperature=0.2
)
```

### Anthropic (Claude Opus 4.5)

```python
import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-opus-4-5-20251101",
    max_tokens=4096,
    messages=[
        {"role": "user", "content": f"Generate Lean 4 skeleton for: {problem}"}
    ]
)
```

### Exa Research

```python
from exa_py import Exa

exa = Exa(api_key="...")
result = exa.research(
    query="Approaches to Erdős problem on arithmetic progressions",
    output_schema={"approaches": [...], "papers": [...]}
)
```

---

## References

### Lean & Theorem Proving
- [Lean Copilot - GitHub](https://github.com/lean-dojo/LeanCopilot)
- [LeanDojo Project](https://leandojo.org/)
- [Lean Copilot Paper](https://arxiv.org/abs/2404.12534)

### Frontier Models
- [AI Model Benchmarks 2026 | LM Council](https://lmcouncil.ai/benchmarks)
- [Flagship Model Report | Vellum](https://www.vellum.ai/blog/flagship-model-report)
- [2025 LLM Review | Atoms.dev](https://atoms.dev/blog/2025-llm-review-gpt-5-2-gemini-3-pro-claude-4-5)

### Harmonic & Aristotle
- [Harmonic News](https://harmonic.fun/news)
- [Aristotle IMO Paper](https://arxiv.org/abs/2510.01346)
- [Erdős Problem #124 Discussion](https://www.erdosproblems.com/forum/thread/124)
- [SPEC-021: Aristotle Integration](../specs/spec-021-aristotle-integration.md)
- [Vendor Notes: Harmonic Aristotle](../_vendor-docs/harmonic-aristotle/README.md)

### Research APIs
- [Exa Research API](https://exa.ai/blog/introducing-exa-research)
- [OpenAlex Documentation](https://docs.openalex.org/)
- [Semantic Scholar API](https://www.semanticscholar.org/product/api)

### Math Reasoning
- [DeepSeek-Prover-V2](https://www.infoq.com/news/2025/05/deepseek-prover-v2-formal-proof/)
- [Benchmarking LLMs on Advanced Mathematical Reasoning](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2025/EECS-2025-121.pdf)

---

*This document will be updated as the project evolves and new tools become available.*
