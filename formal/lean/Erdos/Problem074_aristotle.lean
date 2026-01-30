/-
Problem 74: Erdős Problem #74 - ARISTOTLE ATTEMPT

This is a copy of Problem074_experimental.lean with the open conjectures
converted to theorems with `sorry` for Aristotle API to attempt.

WARNING: These are genuinely OPEN mathematical problems. The main conjecture
carries a $500 prize. Don't expect miracles!
-/

import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Subgraph
import Mathlib.Combinatorics.SimpleGraph.Coloring
import Mathlib.Combinatorics.SimpleGraph.Bipartite
import Mathlib.Order.Filter.AtTopBot.Basic
import Mathlib.Data.Nat.Sqrt
import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Card

open Filter SimpleGraph

namespace Erdos.Problem074

universe u
variable {V : Type u}

/-! ## Definitions (same as experimental) -/

def SimpleGraph.edgeDistancesToBipartite {G : SimpleGraph V} (A : G.Subgraph) : Set ℕ :=
  { (E.ncard) | (E : Set (Sym2 V)) (_ : E ⊆ A.edgeSet) (_ : IsBipartite (A.deleteEdges E).coe)}

noncomputable def SimpleGraph.minEdgeDistToBipartite {G : SimpleGraph V} (A : G.Subgraph) : ℕ :=
  sInf <| SimpleGraph.edgeDistancesToBipartite A

def SimpleGraph.subgraphEdgeDistsToBipartite (G : SimpleGraph V) (n : ℕ) : Set ℕ :=
  { (SimpleGraph.minEdgeDistToBipartite A) |
    (A : Subgraph G) (_ : A.verts.ncard = n) (_ : A.verts.Finite) }

noncomputable def SimpleGraph.maxSubgraphEdgeDistToBipartite
    (G : SimpleGraph V) (n : ℕ) : ℕ := sSup <| SimpleGraph.subgraphEdgeDistsToBipartite G n

/-! ## Proved lemmas (copied from experimental) -/

theorem SimpleGraph.edgeDistancesToBipartite_nonempty {G : SimpleGraph V} (A : G.Subgraph) :
    SimpleGraph.edgeDistancesToBipartite A |>.Nonempty := by
  dsimp only [edgeDistancesToBipartite, Set.nonempty_def]
  refine ⟨_, A.edgeSet, fun _ a ↦ a, ?_, rfl⟩
  use fun _ => 0
  simp

theorem SimpleGraph.subgraphEdgeDistsToBipartite_le_choose_two (G : SimpleGraph V) (n : ℕ) :
    ∀ m ∈ SimpleGraph.subgraphEdgeDistsToBipartite G n, m ≤ n.choose 2 := by
  intro m h
  replace ⟨A, ⟨hn, h_fin, h⟩⟩ := h
  rw [← h]
  have : A.edgeSet.ncard ≤ n.choose 2 := by
    rw [← hn]
    have := h_fin.fintype
    have := Fintype.ofFinite ↑A.coe.edgeSet
    convert (A.coe).card_edgeFinset_le_card_choose_two
    · rw [← Set.ncard_coe_finset A.coe.edgeFinset, coe_edgeFinset A.coe,
        ← Subgraph.image_coe_edgeSet_coe A]
      exact (Set.ncard_image_iff (Set.toFinite A.coe.edgeSet)).mpr <|
        Function.Injective.injOn <| Sym2.map.injective Subtype.coe_injective
    · rw [Set.ncard_eq_toFinset_card _ h_fin, Set.Finite.card_toFinset]
  refine le_trans ?_ this
  apply Nat.sInf_le
  simp [SimpleGraph.edgeDistancesToBipartite]
  refine ⟨A.edgeSet, ?_, subset_rfl, rfl⟩
  use fun _ => 0
  simp

theorem SimpleGraph.subgraphEdgeDistsToBipartite_bddAbove (G : SimpleGraph V) (n : ℕ) :
    BddAbove (SimpleGraph.subgraphEdgeDistsToBipartite G n) := by
  use n.choose 2
  simp only [upperBounds, Set.mem_setOf_eq]
  intro m hm
  exact SimpleGraph.subgraphEdgeDistsToBipartite_le_choose_two (G := G) n m hm

theorem SimpleGraph.minEdgeDistToBipartite_mem_edgeDistancesToBipartite {G : SimpleGraph V}
    (A : G.Subgraph) :
    SimpleGraph.minEdgeDistToBipartite A ∈ SimpleGraph.edgeDistancesToBipartite A := by
  classical
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  exact Nat.sInf_mem (SimpleGraph.edgeDistancesToBipartite_nonempty (A := A))

theorem SimpleGraph.exists_deleteEdges_bipartite_minEdgeDist {G : SimpleGraph V} (A : G.Subgraph) :
    ∃ (E : Set (Sym2 V)), E ⊆ A.edgeSet ∧ IsBipartite (A.deleteEdges E).coe ∧
      E.ncard = SimpleGraph.minEdgeDistToBipartite A := by
  classical
  rcases (by
    simpa [SimpleGraph.edgeDistancesToBipartite] using
      (SimpleGraph.minEdgeDistToBipartite_mem_edgeDistancesToBipartite (A := A))) with
    ⟨E, hBip, hSub, hCard⟩
  exact ⟨E, hSub, hBip, hCard⟩

theorem SimpleGraph.minEdgeDistToBipartite_le_edgeSet_ncard {G : SimpleGraph V} (A : G.Subgraph) :
    SimpleGraph.minEdgeDistToBipartite A ≤ A.edgeSet.ncard := by
  classical
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  apply Nat.sInf_le
  refine ⟨A.edgeSet, subset_rfl, ?_, rfl⟩
  refine ⟨fun _ => 0, ?_⟩
  simp

theorem SimpleGraph.minEdgeDistToBipartite_eq_zero_of_isBipartite {G : SimpleGraph V}
    (A : G.Subgraph) (hA : IsBipartite A.coe) :
    SimpleGraph.minEdgeDistToBipartite A = 0 := by
  classical
  apply Nat.le_zero.1
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  apply Nat.sInf_le
  refine ⟨(∅ : Set (Sym2 V)), by simp, ?_, by simp⟩
  have hcoe : (A.deleteEdges (∅ : Set (Sym2 V))).coe = A.coe := by
    ext v w
    simp
  simpa [hcoe] using hA

theorem SimpleGraph.maxSubgraphEdgeDistToBipartite_le_choose_two (G : SimpleGraph V) (n : ℕ) :
    SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ n.choose 2 := by
  dsimp [SimpleGraph.maxSubgraphEdgeDistToBipartite]
  refine csSup_le' (a := n.choose 2) (s := SimpleGraph.subgraphEdgeDistsToBipartite G n) ?_
  intro m hm
  exact SimpleGraph.subgraphEdgeDistsToBipartite_le_choose_two (G := G) n m hm

theorem tendsto_nat_sqrt_atTop : Tendsto Nat.sqrt atTop atTop := by
  rw [tendsto_atTop_atTop]
  intro b
  refine ⟨b * b, ?_⟩
  intro a ha
  exact (Nat.le_sqrt).2 ha

/-!
## OPEN CONJECTURES - FOR ARISTOTLE TO ATTEMPT

These are the actual open problems. Converting from `def : Prop` to `theorem := by sorry`.
-/

/--
**Main Conjecture (Problem 74)** - $500 PRIZE

Let `f(n) → ∞` (possibly very slowly).
Is there a graph of infinite chromatic number such that every finite subgraph on `n` vertices
can be made bipartite by deleting at most `f(n)` edges?

STATUS: OPEN
-/
theorem erdos_74 :
    ∀ f : ℕ → ℕ, Tendsto f atTop atTop →
      (∃ (W : Type u) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
        ∀ n, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ f n) := by
  sorry

/--
**Known positive result (linear bound).**

There exist graphs of infinite chromatic number such that every finite `n`-vertex subgraph
can be made bipartite by deleting at most `ε * n` edges (for any fixed `ε > 0`).

This is proved by Rödl (1982) using modified Kneser graphs K*(n,k).
Formalizing this requires constructing the Kneser graph and proving its properties.

STATUS: KNOWN TRUE (Rödl 1982) - needs formalization
-/
theorem erdos_74_linear :
    ∀ ε : ℝ, 0 < ε →
      ∃ (W : Type u) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
        ∀ n : ℕ, (SimpleGraph.maxSubgraphEdgeDistToBipartite G n : ℝ) ≤ ε * (n : ℝ) := by
  sorry

/--
**Variant: Square Root Bound**.

Is there a graph of infinite chromatic number such that every finite subgraph on `n` vertices
can be made bipartite by deleting at most `√n` edges?

STATUS: OPEN
-/
theorem erdos_74_sqrt :
    ∃ (W : Type u) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
      ∀ n, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ Nat.sqrt n := by
  sorry

/-- Implication: main conjecture implies sqrt variant.
    This is already proved - just demonstrating the logical relationship. -/
theorem erdos_74_implies_sqrt :
    (∀ f : ℕ → ℕ, Tendsto f atTop atTop →
      ∃ (W : Type u) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
        ∀ n, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ f n) →
    (∃ (W : Type u) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
      ∀ n, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ Nat.sqrt n) := by
  intro h
  have hs : Tendsto Nat.sqrt atTop atTop := tendsto_nat_sqrt_atTop
  rcases h Nat.sqrt hs with ⟨W, G, hχ, hbound⟩
  exact ⟨W, G, hχ, hbound⟩

end Erdos.Problem074
