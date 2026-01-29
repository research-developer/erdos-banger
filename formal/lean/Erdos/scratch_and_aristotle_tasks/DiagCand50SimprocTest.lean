import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Tactic.Simproc.Factors
import Mathlib.Tactic.IntervalCases

open Finset

namespace Test

def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

lemma diag_cand_5 : DiagonalCandidates 5 = {0, 1, 2, 3, 4} := by
  classical
  ext n
  by_cases hn : n < 5
  · have : n < 5 := hn
    interval_cases n <;>
      simp [DiagonalCandidates,
        Nat.squarefree_iff_nodup_primeFactorsList (by
          simpa using (Nat.succ_ne_zero (n * n)))]
  · have hne0 : n ≠ 0 := by intro h; subst h; exact hn (by decide)
    have hne1 : n ≠ 1 := by intro h; subst h; exact hn (by decide)
    have hne2 : n ≠ 2 := by intro h; subst h; exact hn (by decide)
    have hne3 : n ≠ 3 := by intro h; subst h; exact hn (by decide)
    have hne4 : n ≠ 4 := by intro h; subst h; exact hn (by decide)
    simp [DiagonalCandidates, hn, hne0, hne1, hne2, hne3, hne4]

end Test
