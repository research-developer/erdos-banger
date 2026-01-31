/-
Problem 074 - Novel Experimental Approach

Status: EXPERIMENTAL (2026-01-31)
Prize: $500

MISSION: Find a NOVEL graph construction that solves Erdős Problem #74.

All known triangle-free high-χ families have been REFUTED:
- Burling graphs: FAIL at B₃ (n=27, ebip=8 > √27)
- Twincut graphs: FAIL at G₄ (n=23, ebip=7 > √23)
- Mycielski graphs: FAIL at M₄ (n=11, ebip=4 > √11)

THE PROBLEM:
Find a graph G with χ(G) = ∞ such that every n-vertex subgraph H satisfies:
  ebip(H) = |E(H)| - MaxCut(H) ≤ √n

KEY INSIGHT:
The failure mode of all known constructions is that they allow packing
too many vertex-disjoint odd cycles. Any successful construction must
have odd cycles that SHARE EDGES in a structured way.

APPROACHES TO TRY:
1. Probabilistic construction (Lovász Local Lemma?)
2. Algebraic construction (Cayley graphs of specific groups?)
3. Hierarchical/fractal construction with controlled odd cycle overlap
4. Graphs from incidence geometry (projective planes, etc.)
5. Shift graphs / Borel combinatorics constructions
6. PROVE IT'S IMPOSSIBLE - maybe no such graph exists

RESOURCES:
- `Problem074_RESOURCES.md` - Master tracking
- `literature/extracts/pdf/erdos-gyori-1991-edges-bipartite/fulltext.md` - Pentagonlike graphs
- Web search for novel constructions

INSTRUCTIONS FOR OVERNIGHT AGENT:
1. Research novel graph constructions with high χ and controlled odd cycle structure
2. Define promising constructions in this file
3. State key properties as theorems (or as axioms when currently unproved)
4. If possible, prove the main theorem!
5. Document your reasoning in comments

Compile with:
  cd formal/lean && lake build Erdos.Problem074_novel_experimental
-/

import Erdos.Problem074_experimental
import Mathlib.Data.Nat.Sqrt
import Mathlib.Order.Filter.AtTopBot.Basic

open SimpleGraph Filter

namespace Erdos.Problem074.Novel

universe u

/-!
## Core definitions

This file is meant to be a scratchpad. For the *canonical* definitions / conjecture
statement, see `Erdos/Problem074.lean`.
-/

noncomputable abbrev ebip {V : Type*} {G : SimpleGraph V} (A : G.Subgraph) : ℕ :=
  SimpleGraph.minEdgeDistToBipartite A

noncomputable abbrev maxEbip {V : Type*} (G : SimpleGraph V) (n : ℕ) : ℕ :=
  SimpleGraph.maxSubgraphEdgeDistToBipartite G n

/-!
## The Prize Theorem

The √n case is open (as of 2026). We record the target statement as a `Prop`
from `Erdos/Problem074_experimental.lean` so this file remains warning-free.
-/

/-- The $500 question (square-root bound), stated as a `Prop`. -/
abbrev erdos_74_sqrt : Prop :=
  Erdos.Problem074.erdos_74_sqrt.{u}

/-!
## Experimental Constructions

Try defining novel graph families below. Even if you can't prove the main
theorem, defining the construction and stating its properties is valuable.
-/

/-!
## Computation notes (exact MaxCut on small graphs)

For each candidate family below we computed, for a finite graph `H`:

`ebip(H) = |E(H)| - MaxCut(H)`

using exact MaxCut (brute force / Gray-code). See the Python scripts in `scripts/`.

### New families tried (2026-01-31) — all refuted

1. **Shift graphs** `Sh(n)` (`scripts/shift_graph_sqrt_test.py`)
   - Smallest violation found: `Sh(7)` has `|V|=21`, `ebip=5`, but `⌊√21⌋=4`.

2. **Kneser graphs** `K(n,2)` (`scripts/kneser_graph_sqrt_test.py`)
   - Smallest violation found: `K(6,2)` has `|V|=15`, `ebip=15`, but `⌊√15⌋=3`.
   - (Also `K(7,2)` has `|V|=21`, `ebip=35`, `⌊√21⌋=4`.)

3. **Paley graphs** `P(q)` (`scripts/paley_graph_sqrt_test.py`)
   - Smallest violation found: `P(13)` has `|V|=13`, `ebip=13`, but `⌊√13⌋=3`.

These are *not* proofs about the infinite variants, but they are strong evidence
that the most obvious algebraic / Borel-combinatorics families do not satisfy the
`√n` target.

### Hasse diagrams / Suk–Tomon rank-parity defects (ACTIVE, 2026-01-31)

See:
- `formal/lean/Erdos/Problem074_HASSE_STRATEGY.md`
- `scripts/hasse_poset_test.py`

Computational note (prototype, exact MaxCut on sampled induced subgraphs with `|S| ≤ 25`):
- In a naive modeled "standard example" approximant with parameter `t=4` (`|V|=220, |E|=380`),
  the script finds a **connected** induced subgraph on `n=25` vertices with `ebip=6 > √25=5`
  (so the strict constant-1 `√n` bound fails for this naive model).
- The same subset had a rank-parity defect upper bound `|D(S)|=15`, which is valid but loose.

This does **not** refute the broader Hasse-diagram strategy: the paper enforces distinctness
conditions via a projective transformation, and constants may matter. It *does* strongly suggest
we must implement the actual Suk–Tomon setup carefully before attempting Lean proofs.
-/

/-!
## Refuted finite families (Lean stubs)

These definitions are included so we can refer to the usual families inside Lean.
The refutations are recorded as theorems with `sorry`, backed by the exact-MaxCut Python scripts.
-/

abbrev ShiftV (n : ℕ) : Type :=
  { p : Fin n × Fin n // p.1 < p.2 }

def ShiftGraph (n : ℕ) : SimpleGraph (ShiftV n) where
  Adj p q :=
    (p.1.2 = q.1.1 ∧ p.1.1 < q.1.2) ∨ (q.1.2 = p.1.1 ∧ q.1.1 < p.1.2)
  symm := by
    intro p q h
    rcases h with ⟨h1, h2⟩ | ⟨h1, h2⟩
    · exact Or.inr ⟨h1, h2⟩
    · exact Or.inl ⟨h1, h2⟩
  loopless := by
    intro p h
    rcases h with ⟨hEq, hlt⟩ | ⟨hEq, hlt⟩
    · exact lt_irrefl _ (hEq ▸ hlt)
    · exact lt_irrefl _ (hEq ▸ hlt)

abbrev KneserV (n k : ℕ) : Type :=
  { S : Finset (Fin n) // S.card = k }

def KneserGraph (n k : ℕ) : SimpleGraph (KneserV n k) where
  Adj S T := Disjoint S.1 T.1 ∧ S ≠ T
  symm := by
    intro S T h
    exact ⟨h.1.symm, h.2.symm⟩
  loopless := by
    intro S h
    exact h.2 rfl

/-! Concrete refutation statements (backed by computation). -/

/-- Exact MaxCut computation; see `scripts/shift_graph_sqrt_test.py`. -/
theorem shiftGraph_refuted_sqrt :
    maxEbip (ShiftGraph 7) 21 > Nat.sqrt 21 := by
  -- TODO: port the finite MaxCut computation into Lean, or formalize an analytic bound.
  -- For now this is backed by the exact computation in `scripts/shift_graph_sqrt_test.py`.
  sorry

/-- Exact MaxCut computation; see `scripts/kneser_graph_sqrt_test.py`. -/
theorem kneserGraph_refuted_sqrt :
    maxEbip (KneserGraph 6 2) 15 > Nat.sqrt 15 := by
  -- TODO: port the finite MaxCut computation into Lean, or formalize an analytic bound.
  -- For now this is backed by the exact computation in `scripts/kneser_graph_sqrt_test.py`.
  sorry

/-!
## Key Lemmas

Useful lemmas that might help prove the main theorem.
-/

/-!
### A very crude (but useful) χ vs ebip upper bound

If deleting `k` edges makes a finite graph bipartite, then coloring the `≤ 2k` endpoints of those
edges with fresh colors and 2-coloring the rest gives:

`χ(G) ≤ 2k + 2`.

This does *not* rule out `maxEbip(G,n) ≤ √n` (since `2√n + 2` still grows), but it is a sanity
check: truly tiny `ebip` cannot support large chromatic number.
-/

/--
Crude but useful bound: if deleting `k` edges makes a finite graph bipartite, then `χ ≤ 2k + 2`.

This is a standalone graph-theoretic lemma, and should be provable in Mathlib. We keep it as an
`sorry` in this file for now.
-/
theorem chromaticNumber_le_two_mul_ebip {V : Type*} [Fintype V] (G : SimpleGraph V) :
    G.chromaticNumber ≤ (2 * ebip (G := G) (⊤ : G.Subgraph) + 2 : ℕ∞) := by
  -- TODO: prove this by extracting a min-edge-deletion witness `E` and coloring:
  -- - 2-color the bipartite graph `G.deleteEdges E`
  -- - recolor the ≤ 2|E| endpoints of deleted edges with fresh colors.
  sorry

/-!
### The "hard constraint" heuristic: χ ≤ 2 + 2√(ebip)

Let `(A,B)` be a maximum cut, so the monochromatic edges are exactly `ebip(G)`.
Then `χ(G) ≤ χ(G[A]) + χ(G[B])`, and a graph with `m` edges satisfies `χ ≤ 1 + √(2m)`.

This gives the useful (and plausibly close-to-sharp in this regime) bound:

`χ(G) ≤ 2 + 2√(ebip(G))`.

If true, it implies that any finite witness with `ebip ≤ √n` must have
`χ ≲ n^{1/4}` (matching the Suk–Tomon cover-graph exponent).
-/

/--
Sharper “hard constraint” heuristic: `χ ≤ 2 + 2 * √(ebip)`.

This is discussed in `Problem074_HASSE_STRATEGY.md`. We keep it as a `sorry` here for now.
-/
theorem chromaticNumber_le_two_add_two_sqrt_ebip {V : Type*} [Fintype V] (G : SimpleGraph V) :
    G.chromaticNumber ≤ (2 + 2 * Nat.sqrt (ebip (G := G) (⊤ : G.Subgraph)) : ℕ∞) := by
  -- TODO: prove the standard inequality `χ ≤ 1 + √(2m)` for finite graphs with `m` edges,
  -- and combine it with a maximum-cut witness for `ebip`.
  sorry

/-!
## Notes for Overnight Agent

1. The key mathematical insight is that odd cycles must SHARE EDGES.
   All failed constructions (Burling, Twincut, Mycielski) allow packing
   many DISJOINT odd cycles.

2. A successful construction needs:
   - χ = ∞ (global complexity)
   - Triangle-free or sparse odd cycles
   - Odd cycles forced to overlap on a small edge set

3. Consider the Erdős-Győri 1991 paper on pentagonlike graphs.
   They study graphs close to C₅[n/5,...,n/5]. Maybe there's a hint there.

4. The problem specifies χ = ℵ₀ (countable). It FAILS for χ = ℵ₁.
   This suggests the construction must be "essentially countable" in nature.

5. Don't be afraid to prove impossibility! If √n doesn't work, that's
   also a $500 answer.

Good luck! 🎯
-/

end Erdos.Problem074.Novel
