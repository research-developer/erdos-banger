/-
Problem 074 - Mycielski Graphs Approach

Status: REFUTED (2026-01-31)
Prize: $500

This file explored Mycielski graphs as a candidate family for the √n
edge-deletion-to-bipartite bound in Erdős Problem #74.

RESULT: FAILS.

A concrete counterexample already occurs at M₄ (the Grötzsch graph).
Exact MaxCut computation (see `scripts/mycielski_sqrt_test.py`):
  - n = 11, m = 20, MaxCut = 16, ebip = 4, Nat.sqrt 11 = 3, so 4 > 3.

Reference: `Problem074_MYCIELSKI_RESOURCES.md`
-/

import Erdos.Problem074
import Mathlib.Data.Nat.Sqrt

namespace Erdos.Problem074.Mycielski

/-!
## Mycielski Graph Construction

The Mycielski construction M₁, M₂, M₃, ... produces triangle-free graphs
with χ(Mₖ) = k.

Construction:
- M₁ = K₁ (single vertex)
- M₂ = K₂ (single edge)
- Mₖ₊₁ from Mₖ:
  1. Take Mₖ with vertices v₁, ..., vₙ
  2. Add shadow vertices u₁, ..., uₙ
  3. Add apex vertex w
  4. Connect uᵢ to N(vᵢ) in Mₖ
  5. Connect w to all uᵢ
-/

/-- Vertices of the k-th Mycielski graph.
    Inductively: Mₖ₊₁ has |V(Mₖ)| original + |V(Mₖ)| shadow + 1 apex vertices. -/
inductive MycielskiVertex : ℕ → Type
  | base : MycielskiVertex 1  -- M₁ has one vertex
  | orig {k : ℕ} : MycielskiVertex k → MycielskiVertex (k + 1)  -- original vertices from Mₖ
  | shadow {k : ℕ} : MycielskiVertex k → MycielskiVertex (k + 1)  -- shadow copies
  | apex {k : ℕ} : MycielskiVertex (k + 1)  -- the new apex

/-- The k-th Mycielski graph. -/
def MycielskiGraph (k : ℕ) : SimpleGraph (MycielskiVertex k) := by
  cases k with
  | zero => exact ⊥  -- M₀ = empty (not standard, but type-safe)
  | succ k =>
    cases k with
    | zero => exact ⊥  -- M₁ = K₁ (no edges)
    | succ k =>
      -- M_{k+2} construction
      sorry  -- Full adjacency definition

/-!
## Key Properties (to prove if computationally viable)
-/

/-- Mycielski graphs are triangle-free. -/
theorem mycielski_triangle_free (k : ℕ) : (MycielskiGraph k).CliqueFree 3 := by
  sorry

/-- Mycielski graph Mₖ has chromatic number k. -/
theorem mycielski_chromatic (k : ℕ) (hk : k ≥ 1) :
    (MycielskiGraph k).chromaticNumber = k := by
  sorry

/-!
## The Prize Question (REFUTED)
-/

/-- FALSE: Mycielski graphs do not satisfy the √n bound (counterexample at M₄). -/
theorem mycielski_sqrt_bound_HYPOTHESIS (k : ℕ) :
    ∀ n, SimpleGraph.maxSubgraphEdgeDistToBipartite (MycielskiGraph k) n ≤ Nat.sqrt n := by
  sorry  -- DO NOT ATTEMPT without computational evidence

end Erdos.Problem074.Mycielski
