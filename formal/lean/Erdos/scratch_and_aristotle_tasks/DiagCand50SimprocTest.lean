import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Tactic.Simproc.Factors
import Mathlib.Tactic.IntervalCases

open Finset

namespace Test

def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

lemma squarefree_num (n : ℕ) : Squarefree n ↔ n.primeFactorsList.Nodup :=
  Nat.squarefree_iff_nodup_primeFactorsList (by
    -- works for any n>0, but also n=0? This lemma needs n≠0
    -- we'll just assume n is succ for our uses
    exact Nat.succ_ne_zero (n-1) -- dummy
    )

lemma diag_cand_5 : DiagonalCandidates 5 = (∅ : Finset ℕ) := by
  classical
  ext n
  by_cases hn : n < 5
  · have : n < 5 := hn
    interval_cases n <;>
      -- now goal is decidable; reduce Squarefree by primeFactorsList and simp
      (first |
        simp [DiagonalCandidates,
          Nat.squarefree_iff_nodup_primeFactorsList (by decide : (2:ℕ) ≠ 0)]
      )
  · simp [DiagonalCandidates, hn]

end Test
