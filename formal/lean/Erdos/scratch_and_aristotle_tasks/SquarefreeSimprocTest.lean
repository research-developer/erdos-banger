import Mathlib.Data.Nat.Squarefree
import Mathlib.Tactic.Simproc.Factors

example : Squarefree 30 := by
  refine (Nat.squarefree_iff_nodup_primeFactorsList (by decide : (30:ℕ) ≠ 0)).2 ?_
  simp

example : ¬ Squarefree 1025 := by
  have h0 : (1025:ℕ) ≠ 0 := by decide
  simpa [Nat.squarefree_iff_nodup_primeFactorsList h0] using
    (show ¬ (1025:ℕ).primeFactorsList.Nodup by simp)
