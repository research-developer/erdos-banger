import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Tactic.Simproc.Factors
import Mathlib.Tactic.IntervalCases

open Finset

namespace Test

def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

lemma diag_cand_5 : DiagonalCandidates 5 = (∅ : Finset ℕ) := by
  classical
  ext n
  by_cases hn : n < 5
  · interval_cases n <;>
      simp [DiagonalCandidates, Nat.squarefree_iff_nodup_primeFactorsList]
  · simp [DiagonalCandidates, hn]

end Test
