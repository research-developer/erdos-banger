# Problem 074 - Hasse Diagram Strategy (BREAKTHROUGH)

## Status: ACTIVE RESEARCH DIRECTION

**Date:** 2026-01-31
**Prize:** $500
**Approach:** Rank-parity defects on Suk-Tomon incidence posets

---

## Executive Summary

This document describes a **novel proof architecture** for Erdős Problem #74 that:
1. Derives the construction from the constraint (not trial-and-error)
2. Provides an explicit canonical deletion set D(S)
3. Hits the EXACT correct exponent (χ ≈ n^{1/4})
4. Transforms the problem into a countable fork-certificate lemma

---

## The Hard Constraint: χ ≤ 2 + 2√(ebip)

**Theorem (Chromatic-Frustration Bound):**
For any graph H: χ(H) ≤ 2 + 2·√(ebip(H))

**Proof:**
Let (A,B) be a maximum cut of H. Then:
- Monochromatic edges = e(H[A]) + e(H[B]) = ebip(H) = t
- For any graph G with m edges: χ(G) ≤ 1 + √(2m)
- Therefore:
  ```
  χ(H) ≤ χ(H[A]) + χ(H[B])
       ≤ (1 + √(2·e(H[A]))) + (1 + √(2·e(H[B])))
       ≤ 2 + 2√(e(H[A]) + e(H[B]))
       = 2 + 2√t
  ```

**Critical Consequence:**
If ebip(H) ≤ √n for an n-vertex graph H, then:
```
χ(H) ≤ 2 + 2·√(√n) = 2 + 2·n^{1/4}
```

**Interpretation:**
Any "yes" construction for Problem 74 (√n case) MUST have finite approximants with χ growing like n^{1/4}. This is the "shape of the universe" for this problem.

---

## The Construction: Suk-Tomon Incidence Posets

### Reference
Andrew Suk and István Tomon construct Hasse diagrams (cover graphs of posets) achieving χ ≈ n^{1/4}.

### Properties of G_N (the N-th approximant)

| Property | Value | Why It Matters |
|----------|-------|----------------|
| Vertices | ≈ N^{4/3} | Based on incidence count |
| Chromatic number | ≈ N^{1/3} ≈ \|V\|^{1/4} | **EXACTLY the right exponent** |
| Triangle-free | Yes | Avoids local density trap |
| Structure | Point-line incidences | Geometric, analyzable |

### Construction Sketch

1. Take a point-line configuration (P, L) with:
   - |P| = |L| = N
   - |Incidences| ≈ N^{4/3} (near Szemerédi-Trotter bound)

2. Define poset Q_N on incidences:
   - Elements = {(p, ℓ) : p ∈ ℓ}
   - Order by some geometric rule (x-coordinate, slope, etc.)

3. Take Hasse diagram G_N = H(Q_N):
   - Vertices = elements of Q_N
   - Edges = cover relations (x ≺ y with no z: x ≺ z ≺ y)

---

## The Deletion Method: Rank-Parity Defects

### Definition

For any poset Q with Hasse diagram H(Q) and any finite subset S ⊆ V(H(Q)):

1. **Induced height function:**
   h_S(x) = max length of chain in Q[S] ending at x

2. **Parity coloring:**
   c(x) = h_S(x) mod 2

3. **Defect set:**
   D(S) = {edges xy ∈ E(H(Q)[S]) : h_S(x) ≡ h_S(y) (mod 2)}

### Key Property

**Lemma:** Deleting D(S) from H(Q)[S] makes it bipartite.

**Proof:** After deletion, every remaining edge xy has h_S(x) ≢ h_S(y) (mod 2), so the parity coloring is proper.

**Corollary:** ebip(H(Q)[S]) ≤ |D(S)|

### Why Defects Occur

In a **ranked poset**, every cover x ≺ y satisfies h(y) = h(x) + 1, so heights alternate and D(S) = ∅.

In a **general poset**, a cover x ≺ y can have h_S(y) ≥ h_S(x) + 2 because y has another predecessor via a longer chain not through x. These are the defect edges.

---

## The Fork Certificate Lemma (KEY CONJECTURE)

### Statement

**Conjecture (Fork Forcing):**
In Suk-Tomon incidence posets, if an induced subgraph on n vertices has t defect edges, then t ≤ C√n for some absolute constant C.

### The Fork Certificate

For each defect edge x ≺ y (with h_S(x) ≡ h_S(y) mod 2):

1. Since h_S(y) ≥ h_S(x) + 2, take a longest chain ending at y:
   z_0 ≺ z_1 ≺ ... ≺ z_{h_S(y)-1} ≺ y

2. Let w = z_{h_S(y)-1}. Then:
   - w ≺ y (w is a predecessor of y)
   - h_S(w) = h_S(y) - 1
   - h_S(w) ≥ h_S(x) + 1

3. **Crucially:** w cannot be below x (or x ≺ y wouldn't be a cover).
   Therefore w ∥ x (w is incomparable with x).

4. **The fork:** (x, w, y) with x ≺ y, w ≺ y, x ∥ w.

### The Counting Argument (To Prove)

**Goal:** Show that t forks force ≥ t² vertices.

**Strategy:**
- Each fork (x, w, y) corresponds to a specific incidence pattern
- In incidence geometry, incomparable pairs behave like "inversions"
- Many inversions force a grid-like structure
- A t × t grid has t² vertices

**Analogy:** Like proving that a permutation with t inversions needs ≥ √t elements.

### Why This Implies the √n Bound

If t defect edges ⟹ n ≥ t², then t ≤ √n.
Therefore |D(S)| ≤ √n.
Therefore ebip(H(Q)[S]) ≤ √n. ∎

---

## Why This Avoids the Disjoint Odd Cycle Trap

### The Failure Mode of Previous Approaches

Burling, Mycielski, Twincut all fail because:
- They allow packing Ω(n) edge-disjoint odd cycles
- Each odd cycle needs ≥1 edge deleted
- Therefore ebip ≥ Ω(n), not O(√n)

### Why Hasse Diagrams Are Different

In the rank-parity method:
- **Every** odd cycle contains at least one defect edge
- If |D(S)| ≤ √n, you can pack at most √n edge-disjoint odd cycles
- The "entanglement" is structural: odd cycles = witnesses of rank jumps

This is EXACTLY the "odd cycles must share edges" requirement, made explicit.

---

## Building the Infinite Graph (Fraïssé Limit)

### The Construction

1. Let K = {all finite induced subgraphs of all G_N}

2. K is hereditary (closed under induced subgraphs)

3. If K has the amalgamation property, there exists a countable **Fraïssé limit** G_∞ whose age is exactly K

4. Properties of G_∞:
   - Every finite induced subgraph is in K
   - Therefore ebip ≤ C√n for all n-vertex induced subgraphs
   - χ(G_∞) = ℵ₀ (because K contains graphs of arbitrarily large χ)

### Why Countable is Special

The problem statement notes that the property FAILS for χ = ℵ₁.
This suggests the "countable limit" construction is the right approach.
Fraïssé limits are exactly designed for this.

---

## Computational Validation Plan

### Phase 1: Implement Suk-Tomon Construction

```python
def build_incidence_poset(N):
    """
    Build the N-th Suk-Tomon incidence poset.

    Returns: (vertices, edges, poset_order)
    """
    # 1. Generate point-line configuration
    # 2. Compute incidences
    # 3. Define poset order
    # 4. Extract cover relations (Hasse edges)
    pass
```

### Phase 2: Compute Defect Sets

```python
def compute_height_function(poset, subset):
    """Compute h_S(x) for all x in subset."""
    pass

def compute_defect_set(poset, subset):
    """Return D(S) = edges with same-parity heights."""
    heights = compute_height_function(poset, subset)
    defects = []
    for (u, v) in edges_in_induced_subgraph(poset, subset):
        if heights[u] % 2 == heights[v] % 2:
            defects.append((u, v))
    return defects
```

### Phase 3: Compare ebip vs |D(S)|

```python
def validate_defect_bound(poset, num_samples=1000):
    """
    For random subsets S, compare:
    - ebip(G[S]) via exact MaxCut
    - |D(S)| via rank-parity

    They should be close (|D(S)| ≥ ebip always, hopefully ≈).
    """
    pass
```

### Phase 4: Check √n Scaling

```python
def check_sqrt_scaling(poset, max_n=100):
    """
    For each n, find max ebip over subsets of size n.
    Plot against √n.
    Should see ebip ≤ C√n for some constant C.
    """
    pass
```

---

## Computational Notes (2026-01-31)

Prototype implementation:
- `scripts/hasse_poset_test.py`

What it currently does:
- Implements a small-scale version of Tomon’s **Claim 12** "standard example" graph `G_t` (vertices = incidences).
- Computes exact `ebip(G[S]) = |E(S)| - MaxCut(G[S])` for sampled subsets `S` with `|S| ≤ 25`.
- Computes the **rank-parity defect** upper bound `|D(S)|` via induced poset heights mod 2.

Important caveat (now addressed in code):
- The paper says “by applying a projection” we may assume points have distinct x-coordinates and lines have distinct
  slopes (without changing incidences). The prototype now supports an explicit projective transformation mode
  (`use_projective_transform=True`) that samples random invertible 3×3 projective transforms over rationals and rejects
  degeneracies (points at infinity / vertical lines / collisions).

Observed behavior (Monte Carlo, not exhaustive; exact MaxCut on each sampled subset):
- The strict constant-1 `⌊√n⌋` bound already fails on small induced subgraphs for this family.
  - In both “order-keys” mode and in explicit projective-transform mode we see counterexample subsets at
    `n=20` (`ebip=5 > ⌊√20⌋=4`) and `n=25` (`ebip=6 > ⌊√25⌋=5`) for small parameters (`t=4`/`t=5`).
  - A small projection sweep at `t=4`, `n=20` found violations in multiple random projections (so this is not a
    one-off artifact of a single transform).
- The rank-parity defect count `|D(S)|` is always a valid upper bound on `ebip`, but can be very loose
  (often `|D(S)| ≫ ebip` on the same subset).

Interpretation:
- The “rank-parity defect” deletion set is a compelling *proof architecture*, but the naive hope that the Suk–Tomon /
  Tomon Claim 12 graphs satisfy the **strict constant-1** `√n` bound looks unlikely given the small counterexamples.
- If we keep pursuing this direction, the next computational questions are:
  - Is there a *different* incidence configuration (not the standard example) where the strict `√n` might survive?
  - Does this family at least satisfy `ebip ≤ C√n` for a modest constant `C` (and does `C` stabilize with size)?
  - Are the violating subsets structurally classifiable (via MaxCut witnesses), suggesting a modified construction?

---

## Lean Formalization Plan

### Definitions Needed

```lean
-- Height function in induced poset
def inducedHeight (Q : Poset) (S : Set Q) (x : S) : ℕ := sorry

-- Parity coloring
def parityColor (Q : Poset) (S : Set Q) (x : S) : Fin 2 :=
  ⟨inducedHeight Q S x % 2, Nat.mod_lt _ (by norm_num)⟩

-- Defect set
def defectSet (Q : Poset) (S : Set Q) : Set (S × S) :=
  { (x, y) | isCover Q x y ∧ parityColor Q S x = parityColor Q S y }

-- The key lemma
theorem defect_deletion_bipartite (Q : Poset) (S : Set Q) :
    IsBipartite (HasseGraph Q S \ defectSet Q S) := sorry

-- The fork certificate lemma (the prize)
theorem fork_forcing (Q : SukTomonPoset) (S : Set Q) :
    (defectSet Q S).ncard ≤ C * Nat.sqrt S.ncard := sorry
```

### Theorems to Prove

1. `chromatic_frustration_bound`: χ(G) ≤ 2 + 2√(ebip(G))
2. `defect_deletion_bipartite`: Deleting D(S) makes graph bipartite
3. `ebip_le_defect`: ebip(G[S]) ≤ |D(S)|
4. `fork_forcing`: |D(S)| ≤ C√n (THE KEY LEMMA)
5. `erdos_74_sqrt`: The main theorem

---

## References

1. **Suk-Tomon:** "On the Turán number of ordered graphs" and related papers on Hasse diagrams with high chromatic number

2. **Erdős-Hajnal-Szemerédi 1982:** "On almost bipartite large chromatic graphs" - Definition 3.1 of maxSubgraphEdgeDistToBipartite

3. **Szemerédi-Trotter:** Incidence bounds for point-line configurations

4. **Fraïssé limits:** Standard model theory reference for constructing homogeneous structures

---

## Action Items

- [ ] Find and extract Suk-Tomon paper(s)
- [ ] Implement incidence poset construction in Python
- [ ] Compute defect sets and compare to ebip
- [ ] Test √n scaling conjecture
- [ ] Prove fork certificate lemma (the $500 question)
- [ ] Build Fraïssé limit for infinite graph
- [ ] Formalize in Lean

---

## Files

| File | Purpose |
|------|---------|
| `Problem074_novel_experimental.lean` | Lean workspace |
| `Problem074_HASSE_STRATEGY.md` | This document |
| `scripts/hasse_poset_test.py` | Python implementation (to create) |
| `scripts/ebip_utils.py` | MaxCut utilities |
