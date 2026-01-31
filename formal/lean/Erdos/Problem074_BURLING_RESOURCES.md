# Problem 074 - Burling Graph Approach Resources

## ⚠️ STATUS: REFUTED ⚠️

**The Burling approach DOES NOT WORK for the √n bound.**

A concrete counterexample was found in G₄:
- **n = 21 vertices, m = 39 edges**
- **MaxCut = 32**
- **ebip = 39 - 32 = 7 edge deletions needed**
- **√21 ≈ 4.58, so Nat.sqrt 21 = 4**
- **7 > 4 → VIOLATES √n bound**

**Reproducible proof:** `scripts/burling_sqrt_counterexample.py`

**Root cause:** The Burling NEXT-B construction creates **disjoint copies** of previous graphs, allowing many vertex-disjoint odd cycles to be packed. This fundamentally prevents the √n bound.

---

## Overview

This document covers the **Burling graph approach** to Erdős Problem #74 ($500 prize).

**Separate from:** `Problem074_RESOURCES.md` (covers Rödl/Kneser linear case approach)

**Next candidate:** See `Problem074_TWINCUT_RESOURCES.md` for twincut graphs approach

---

## Problem Statement

**Erdős Problem #74** (Open, $500 prize)

Let $f(n) \to \infty$ (possibly very slowly). Is there a graph of infinite chromatic number such that every finite subgraph on $n$ vertices can be made bipartite by deleting at most $f(n)$ edges?

**Source:** https://www.erdosproblems.com/74

---

## Lean Files (Burling Approach)

| File | Purpose | Status |
|------|---------|--------|
| `Problem074_burling.lean` | Clean template | Compiles (1 sorry) |
| `Problem074_burling_experimental.lean` | **ACTIVE** - Experimental work | Compiles (3 sorries) |

---

## What Are Burling Graphs?

Burling (1965) constructed a sequence of graphs $B_1, B_2, B_3, \ldots$ with:

| Property | Value | Why It Matters |
|----------|-------|----------------|
| **Chromatic number** | $\chi(B_k) = k$ | Unbounded - exactly what we need |
| **Triangle-free** | No 3-cycles | Weakest possible odd-cycle obstruction! |
| **Clique number** | $\omega(B_k) = 2$ | No large cliques forcing high χ |
| **Structure** | Intersection graphs of axis-aligned boxes in $\mathbb{R}^3$ | Geometric, recursive |
| **Hereditary** | Induced subgraphs are Burling | Good for induction |
| **Minimal** | Minimal hereditary class with unbounded χ (besides complete graphs) | "Simplest" high-χ construction |

---

## Why Burling Graphs Are Promising

### 1. Triangle-Free = Weak Local Obstruction
- Bipartiteness is blocked only by odd cycles
- No 3-cycles means only 5-cycles, 7-cycles, etc.
- Longer cycles are "easier" to hit with edge deletions

### 2. Hierarchical/Recursive Construction
- Box intersection structure may force odd cycles to share edges
- Tree-decomposition properties (arXiv:1703.07871)

### 3. Minimal Hereditary Class
- Only known minimal hereditary class with unbounded χ besides complete graphs
- "Minimality" might translate to efficient edge-deletion structure

---

## The Key Question

$$\text{For Burling graphs: } \max_{|A|=n} \text{minEdgeDistToBipartite}(B_k[A]) \stackrel{?}{\le} \sqrt{n}$$

**If YES:** We win $500.
**If NO:** We learn something and move to next candidate.

---

## Current Lean Progress (Problem074_burling_experimental.lean)

### ✅ PROVED (8+ theorems)

| Theorem | What it proves |
|---------|----------------|
| `burling_1_subsingleton` | B₁ has exactly one vertex |
| `burling_1_no_edges` | B₁ has no edges |
| `burling_1_bipartite_graph` | B₁ is bipartite |
| `burling_1_bipartite` | √n bound holds for B₁ (trivially, = 0) |
| `minEdgeDistToBipartite_eq_zero_of_isBipartite` | Bipartite graphs need 0 deletions |
| `minEdgeDistToBipartite_le_edgeSet_ncard` | Deletions ≤ edge count |
| `maxSubgraphEdgeDistToBipartite_le_edges` | Deletions ≤ n(n-1)/2 |
| `burling_sublinear` (k=0 case) | B₀ is empty, bound holds trivially |
| `burling_sublinear` (k=1 case) | Uses `burling_1_bipartite` |

### ⚙️ AXIOMATIZED (from literature)

| Axiom | Source |
|-------|--------|
| `BurlingGraphAdj` | Adjacency relation |
| `burling_triangle_free` | Burling 1965 |
| `burling_chromatic_number` | Burling 1965: χ(B_k) = k |

### ❌ REMAINING SORRIES (3)

| Theorem | Difficulty | Notes |
|---------|------------|-------|
| `triangle_free_edge_bound_mantel` | Medium | Mantel's theorem - provable, side quest |
| `burling_sublinear` (k≥2 case) | **$500 QUESTION** | This is where the prize money is! |
| `burling_infinite_graph_exists` | Easy | Follows from `burling_sublinear` |

### Proof Structure for `burling_sublinear`

```
match k with
| 0 => ✅ PROVED (B₀ is empty)
| 1 => ✅ PROVED (uses burling_1_bipartite)
| k + 2 => ❌ SORRY ($500 QUESTION)
```

---

## Key Mathematical Insights

### Known Bounds (Gap Analysis)

| Source | Bound | Graph Family |
|--------|-------|--------------|
| EHS82 Theorem 3.A | $f^{(3)}(n) \le 2n^{3/2}$ | Specker graph $\mathcal{G}_0(\omega, 2)$ |
| Rödl 1982 | $f^{(3)}(n) \le \varepsilon n$ | Modified Kneser $K^*(n,k)$ |
| **Problem 74 Target** | $f^{(3)}(n) = o(n)$ or $\sqrt{n}$ | **UNKNOWN - Burling?** |

### The Gap
- **Best known:** $n^{3/2}$ (EHS82)
- **Target:** $\sqrt{n}$ or slower
- **Burling graphs:** UNTESTED!

### Why Triangle-Free Alone Isn't Enough

**Alon 1996:** For triangle-free graphs with $m$ edges:
- MaxCut $\ge m/2 + c \cdot m^{4/5}$
- Therefore: minEdgeDistToBipartite $\le m/2 - c \cdot m^{4/5} \approx O(m) \approx O(n^2)$

This is still quadratic, NOT $\sqrt{n}$. We need something special about Burling.

---

## Proof Strategy for `burling_sublinear`

### What We Need to Show
For all $k, n$: `maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ Nat.sqrt n`

### Candidate Approaches

1. **Sparse Edge Structure**
   - If Burling n-vertex subgraphs have $O(n)$ edges (not $O(n^2)$)
   - Then even $m/2$ gives $O(n)$, closer to $\sqrt{n}$
   - **Question:** Are Burling graphs sparse (bounded degeneracy)?

2. **Odd Cycle Sharing**
   - If all odd cycles share a common edge set of size $O(\sqrt{n})$
   - Then deleting that set makes H bipartite
   - **Question:** Does tree-decomposition force this?

3. **Induction on k**
   - Base: B₁ case (PROVED! = 0)
   - Step: Show B_k → B_{k+1} construction preserves bound
   - **Question:** How do new vertices/edges affect odd cycles?

4. **Box Intersection Geometry**
   - 3D box structure might constrain odd cycles
   - Cycles must "wind around" in specific ways
   - **Question:** Can we formalize geometric constraints?

---

## Key References (Burling-Specific)

| Source | URL | Content |
|--------|-----|---------|
| Burling 1965 | PhD thesis, U. Colorado | Original construction |
| arXiv:1703.07871 | https://arxiv.org/abs/1703.07871 | Tree-decompositions |
| arXiv:2104.07001 | https://arxiv.org/abs/2104.07001 | Burling revisited I: Characterizations |
| arXiv:2106.16089 | https://arxiv.org/abs/2106.16089 | Burling revisited II: Structure |
| arXiv:2112.11970 | https://arxiv.org/abs/2112.11970 | Burling revisited III: χ-boundedness |
| arXiv:2510.19650 | https://arxiv.org/abs/2510.19650 | Burling in large chromatic (Oct 2025) |

### Key Results from Literature

**Pournajafi-Trotignon (2023):**
- Five equivalent characterizations of Burling graphs
- "Derived from a tree" definition (may be easier to formalize)
- Wheels are NOT Burling graphs
- Structural decomposition theorems

**arXiv:1703.07871:**
- Orthogonal tree-decomposition properties
- "Structural parameters alone cannot guarantee small edge-deletion distance"
- (This is concerning but not definitive for our approach)

---

## Related Bounds (for context)

### Alon 1996 - Bipartite Subgraphs
- Paper: https://link.springer.com/article/10.1007/BF01261315
- Any graph with $2m^2$ edges has bipartite subgraph with $\ge m^2 + m/2$ edges
- Triangle-free with $e$ edges: MaxCut $\ge e/2 + c \cdot e^{4/5}$

### Tuza 1987 - Kneser Graphs
- Maximum bipartite subgraphs of Kneser graphs $K(n,k)$
- Explicit bounds relevant to Rödl approach

---

## Computational Test Plan

Before attempting full formal proof:

```python
# Pseudocode for testing Burling graphs
for k in [3, 4, 5, 6]:
    G = construct_burling_graph(k)
    for n in range(5, min(100, |V(G)|)):
        max_deletion = 0
        for A in all_n_vertex_induced_subgraphs(G, n):
            deletion = |E(A)| - max_cut(A)
            max_deletion = max(max_deletion, deletion)
        print(f"B_{k}, n={n}: max_deletion={max_deletion}, sqrt(n)={sqrt(n):.2f}")
```

**Expected outcomes:**
- `max_deletion ≈ c * sqrt(n)`: VERY PROMISING
- `max_deletion ≈ c * n`: Same as Kneser - not a solution
- `max_deletion` slower than sqrt(n): JACKPOT

---

## Action Items

### Immediate
- [ ] Try to prove `triangle_free_edge_bound_mantel` (Mantel's theorem)
- [ ] Investigate if Burling graphs are sparse
- [ ] Study odd cycle structure in B₂ (first non-trivial case)

### If Approach Looks Viable
- [ ] Formalize tree-decomposition from arXiv:1703.07871
- [ ] Prove induction step: B_k bound → B_{k+1} bound
- [ ] Complete `burling_sublinear` proof

### If Approach Fails
- [ ] Document actual growth rate found
- [ ] Consider other candidates (shift graphs, etc.)
- [ ] Update this document with negative result

---

## Session Log

### 2026-01-30
- Created `Problem074_burling.lean` (clean template)
- Created `Problem074_burling_experimental.lean` (active work)
- Proved B₁ case and 6 supporting lemmas
- Reduced to 3 sorries
- Discovered key gap: best known is n^{3/2} (EHS82), target is √n
- Burling graphs remain UNTESTED for this property

### 2026-01-30 (later)
- **REFUTED**: Found concrete counterexample in G₄
- Counterexample: 21-vertex subgraph needs 7 deletions, but √21 = 4
- Root cause: NEXT-B construction creates disjoint copies → many disjoint odd cycles
- Created `scripts/burling_sqrt_counterexample.py` as reproducible proof
- **Conclusion: Burling approach is DEAD for √n bound**
- **Next step: Try twincut graphs (arXiv:2304.04296)**
