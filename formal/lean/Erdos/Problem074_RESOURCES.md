# Problem 074 Resources

## Problem Statement

**Erdős Problem #74** (Open, $500 prize)

Let $f(n) \to \infty$ (possibly very slowly). Is there a graph of infinite chromatic number such that every finite subgraph on $n$ vertices can be made bipartite by deleting at most $f(n)$ edges?

**Source:** https://www.erdosproblems.com/74

---

## Lean Files

| File | Purpose |
|------|---------|
| `Problem074.lean` | Main skeleton with `sorry` (produces warnings) |
| `Problem074_experimental.lean` | Same content but warning-free (uses `def : Prop`) |
| `Upstream/FormalConjectures/ErdosProblems/74.lean` | Original upstream formalization |

**Recommendation:** Use `Problem074_experimental.lean` for active work (no warnings), then sync to `Problem074.lean` when finalizing.

---

## Literature (Cleaned Markdown)

All in `literature/extracts/pdf/0074/`:

| File | Paper | Key Content |
|------|-------|-------------|
| `erdos-hajnal-szemeredi-1982-almost-bipartite.md` | **EHS82** - The foundational paper | Definition 3.1 (`maxSubgraphEdgeDistToBipartite`), Theorem 1 (linear bound), Specker graphs |
| `rodl-1982-nearly-bipartite.md` | **Rödl82** - Companion paper | Kneser graph construction, $(\varepsilon, k)$-edge property |
| `erdos-hajnal-1985-chromatic.md` | Survey paper | Problem context, related conjectures |
| `erdos-hajnal-1968-infinite.md` | Earlier foundational work | Partition theorems, universal graphs $\mathcal{G}_{\alpha,\gamma}$ |

---

## Known Results (for Lean statements)

### Proved (can be stated as theorems)

1. **EHS82 Theorem 1 (Linear Bound):** For all $\varepsilon > 0$ and all $\kappa$, there exists $\mathcal{G}$ with $\chi(\mathcal{G}) > \kappa$ such that $f_{\mathcal{G}}^{(3)}(n) \leq \varepsilon n$ for all $n$.
   - Translation: `erdos_74_linear` - answer is YES when $f(n) = \varepsilon n$

2. **Rödl82 Theorem 1.5:** The modified Kneser graphs $K^*(n,k)$ have the $(\varepsilon, k)$-edge property.

3. **Upper bound:** $f_{\mathcal{G}}^{(3)}(n) \leq 2n^{3/2}$ for $\mathcal{G}_0(\omega, 2)$ (EHS82 Theorem 3.A)

### Open (stated as `Prop` or `sorry`)

1. **Main conjecture:** Does such a graph exist for ANY $f(n) \to \infty$?
2. **Square root case:** Does $f(n) = \sqrt{n}$ work?
3. **EHS82 Problem 3:** Can $f_{\mathcal{G}}^{(3)}(n)$ grow as slowly as $\log n$?

### Negative results

- The statement **fails** for graphs with chromatic number $\aleph_1$ (uncountable)

---

## Definitions in Lean

From `Problem074.lean` / `Problem074_experimental.lean`:

```lean
-- The set of k such that A can be made bipartite by deleting k edges
def SimpleGraph.edgeDistancesToBipartite {G : SimpleGraph V} (A : G.Subgraph) : Set ℕ

-- Minimum edges to delete to make A bipartite
noncomputable def SimpleGraph.minEdgeDistToBipartite {G : SimpleGraph V} (A : G.Subgraph) : ℕ

-- Set of minEdgeDistToBipartite for all n-vertex subgraphs
def SimpleGraph.subgraphEdgeDistsToBipartite (G : SimpleGraph V) (n : ℕ) : Set ℕ

-- Maximum over all n-vertex subgraphs (EHS82 Definition 3.1)
noncomputable def SimpleGraph.maxSubgraphEdgeDistToBipartite (G : SimpleGraph V) (n : ℕ) : ℕ
```

---

## arXiv Papers (from manifest)

| arXiv ID | Title | Relevance | Extracted |
|----------|-------|-----------|-----------|
| 1902.08177 | Lambie-Hanson: Growth rate of chromatic numbers | Related but different (chromatic growth, not edge-deletion) | ✅ |
| 1306.5167 | Füredi-Simonovits: Degenerate extremal graph problems | Background/context | ✅ |
| 2012.10409 | Illingworth: Chromatic profile of locally bipartite | Related chromatic problems, minimum degree thresholds | ✅ |
| 2203.13833 | Cambie et al: Removing independent sets for chromatic reduction | Brooks' theorem stability | ✅ |
| **0905.2527** | **Mubayi-Turán: Finding bipartite subgraphs efficiently** | **ALGORITHMIC - polynomial algorithms for bipartite subgraph problems** | ✅ |

---

## DOI Papers (from manifest - via Exa discovery)

| DOI | Paper | Relevance |
|-----|-------|-----------|
| 10.1007/BF01788540 | **Tuza 1987: Maximum bipartite subgraphs of Kneser graphs** | **DIRECTLY RELEVANT - bounds on bipartite subgraphs of K(n,k)** |
| 10.1007/BF01261315 | **Alon 1996: Bipartite subgraphs** | **DIRECTLY RELEVANT - edge bounds for bipartization** |
| 10.1016/0012-365x(85)90148-7 | Erdős-Hajnal 1985: Chromatic number survey | Survey paper (PDF in `literature/extracts/pdf/0074/`) |

---

## Notation Mapping

| Paper Notation | Lean Definition |
|----------------|-----------------|
| $f_{\mathcal{G}}^{(3)}(n)$ (EHS82) | `maxSubgraphEdgeDistToBipartite G n` |
| $\chi(\mathcal{G})$ | `G.chromaticNumber` |
| $\chi(\mathcal{G}) = \omega$ | `G.chromaticNumber = ⊤` (infinite) |

---

## Exa Research Leads (2026-01-30)

75+ leads discovered via Exa search. Most promising for Problem 74:

| Paper | Why It's Gold |
|-------|---------------|
| Alex Scott 2023 "Graphs of large chromatic number" (EMS) | Recent comprehensive survey |
| Thomassen 2016 "Infinitely connected subgraphs" | Uncountable chromatic number |
| Jane Tan 2023 "Induced subgraphs of large chromatic" | Recent Combinatorica |
| arXiv 2512.04993 "Edge density thresholds for unbounded χ" | Dec 2024 - NEW |
| arXiv 2510.19650 "Burling graphs in large chromatic" | Oct 2025 - NEW |

**Full leads:** Run `uv run erdos research lead list 74` to see all leads.

---

## Suggested Approach

1. **Start with `Problem074_experimental.lean`** (warning-free)
2. **Add `erdos_74_linear`** - state EHS82 Theorem 1 (known positive result)
3. **Keep `erdos_74` and `erdos_74_sqrt`** as open `Prop` definitions
4. **The main difficulty:** Constructing the Specker graphs or edge graphs $\mathcal{G}_0(\alpha, k)$ in Lean with proper cardinality arguments
5. **Key insight from Tuza 1987:** Maximum bipartite subgraph of $K(n,k)$ gives explicit bounds
6. **Key insight from Alon 1996:** Every graph with $2m^2$ edges has bipartite subgraph with $≥ m^2 + m/2$ edges
