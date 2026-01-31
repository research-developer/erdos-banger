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
| `erdos-hajnal-szemeredi-1982-almost-bipartite.md` | **EHS82** - The foundational paper | Definition 3.1 (`maxSubgraphEdgeDistToBipartite`), Theorem 3.A (subquadratic bound), Problem 3 (slow growth), Specker/edge graphs |
| `rodl-1982-nearly-bipartite.md` | **Rödl82** - Companion paper | Kneser graph construction, $(\varepsilon, k)$-edge property |
| `erdos-hajnal-1985-chromatic.md` | Survey paper | Problem context, related conjectures |
| `erdos-hajnal-1968-infinite.md` | Earlier foundational work | Partition theorems, universal graphs $\mathcal{G}_{\alpha,\gamma}$ |

---

## Known Results (for Lean statements)

### Proved (can be stated as theorems)

1. **Linear edge-deletion bound (Rödl82 / Lovász):** For all $\varepsilon > 0$ and all $k < \omega$, there exist (finite) graphs with $\chi(\mathcal{G}) \ge k$ such that every subgraph $H$ can be made bipartite by deleting at most $\varepsilon |V(H)|$ edges (the $(\varepsilon,k)$-*edge* property).
   - By taking a disjoint union over $k \to \infty$, this yields an infinite-chromatic graph satisfying a linear bound, matching `erdos_74_linear`.

2. **Rödl82 Theorem 1.5:** The modified Kneser graphs $K^*(n,k)$ have the $(\varepsilon, k)$-edge property.

3. **Upper bound:** $f_{\mathcal{G}}^{(3)}(n) \leq 2n^{3/2}$ for $\mathcal{G}_0(\omega, 2)$ (EHS82 Theorem 3.A)

> Note: **EHS82 Theorem 1** is a *different* “linear” result about omitting **vertices** to obtain a large bipartite induced subgraph (their function $f^2$), not about omitting **edges** (their function $f^3$ / Problem 74’s formulation).

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

## Current Status (2026-01-30)

### Completed in `Problem074_experimental.lean`

| Component | Status | Notes |
|-----------|--------|-------|
| `SimpleGraph.sigma` | ✅ DONE | Disjoint union over sigma types |
| `chromaticNumber_sigma_eq_top_of_unbounded` | ✅ DONE | Key chromatic number theorem |
| `rodl_modified_kneser_exists` | ✅ AXIOM | Rödl's finite theorem (axiomatized) |
| `maxSubgraphEdgeDistToBipartite_sigma_le_linear` | ✅ AXIOM | Linear bound preservation |
| **`erdos_74_linear_holds`** | ✅ **PROVED** | The linear case is complete! |

### Remaining Open

| Statement | Status | Difficulty |
|-----------|--------|------------|
| `erdos_74` (main conjecture) | OPEN | **$500 prize** |
| `erdos_74_sqrt` | OPEN | Would follow from main |

---

## Key Mathematical Insights

### MAX-CUT Reformulation (Critical!)

The edge-deletion-to-bipartite problem has an exact equivalence:

$$\text{minEdgeDistToBipartite}(H) = |E(H)| - \text{MaxCut}(H)$$

**Why this matters:** Bounding edge deletions by $f(n)$ means every $n$-vertex subgraph has a cut capturing all but $f(n)$ edges.

### Why Linear is Natural, Sublinear is Hard

| Regime | What it means | Rödl's mechanism |
|--------|---------------|------------------|
| $f(n) = \varepsilon n$ (linear) | Allow $O(n)$ "bad edges" | "Charge per vertex" - pay constant per vertex to hit obstructions |
| $f(n) = o(n)$ (sublinear) | "Almost bipartite in absolute edge error" | **No known mechanism** - would need odd cycles to share a tiny edge set |

**Key insight:** You can't cheat with disjoint unions. The worst-case is over ALL $n$-vertex subgraphs, so any component with only $\varepsilon n$ guarantee fails the $\sqrt{n}$ target for large $n$.

### Countability is Essential

- If $\chi(W) > \omega$ (uncountable chromatic), then $f_W^{(3)}(n) \ge \varepsilon n$ for some $\varepsilon > 0$
- Sublinear is **intrinsically** "countable chromatic" territory
- **Lean tip:** Add `Countable W` to the existential to force the intended case

### What a Sublinear Construction Would Need

A plausible (hypothetical) construction would be:
- **Hierarchical/fractal graph** - globally complex enough for $\chi = \omega$
- **Locally "bipartite + tiny structured defect set"**
- Defect set property: on any $n$-vertex set, it intersects edges in only $o(n)$ edges

---

## Suggested Approach

### For Formalizing (DONE for linear case)

1. ~~**Start with `Problem074_experimental.lean`**~~ ✅
2. ~~**Add `erdos_74_linear`**~~ ✅ (Proved!)
3. **Keep `erdos_74` and `erdos_74_sqrt`** as open `Prop` definitions

### Lemmas Worth Proving in Lean (Future Work)

| Lemma | Purpose | Difficulty |
|-------|---------|------------|
| **Monotonicity** | If $A \le B$ (subgraph inclusion), then `minEdgeDistToBipartite A ≤ minEdgeDistToBipartite B` | Low |
| **Induced-subgraph reduction** | `maxSubgraphEdgeDistToBipartite` equals same quantity over induced subgraphs | Medium |
| **Cut reformulation API** | Bridge between "delete edges" and "2-coloring with ≤k monochromatic edges" | Medium |
| **Replace axiom** | Prove `maxSubgraphEdgeDistToBipartite_sigma_le_linear` for real | High (bookkeeping) |

### For Attacking the Open Problem

1. **Study Tuza 1987:** Maximum bipartite subgraph of $K(n,k)$ gives explicit bounds
2. **Study Alon 1996:** Every graph with $2m^2$ edges has bipartite subgraph with $\ge m^2 + m/2$ edges
3. **Look for hierarchical constructions** with local "bipartite + small defect" structure
4. **Computational exploration:** Brute-force max-cut on small graphs to find candidate families
