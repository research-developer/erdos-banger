-- Erdős #647 (bounded): for 24 < n ≤ 50, max_{m<n}(m+τ(m)) > n+2.
-- τ(m) = number of divisors, defined here (no mathlib).
def tau (m : Nat) : Nat :=
  ((List.range (m+1)).filter (fun d => d != 0 && m % d == 0)).length

def witnessExists (n : Nat) : Bool :=
  (List.range n).any (fun m => decide (n + 3 ≤ m + tau m))

theorem p647_bounded : ∀ n, n < 51 → 24 < n → witnessExists n = true := by decide

#print axioms p647_bounded
