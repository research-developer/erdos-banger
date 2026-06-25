-- Erdős #647 (bounded): for 24 < n ≤ 1000, max_{m<n}(m+τ(m)) > n+2.
-- τ(m) = number of divisors, defined here (no mathlib).
def tau (m : Nat) : Nat :=
  ((List.range (m+1)).filter (fun d => d != 0 && m % d == 0)).length

def witnessExists (n : Nat) : Bool :=
  (List.range n).any (fun m => decide (n + 3 ≤ m + tau m))

theorem p647_bounded_native : ∀ n, n < 1001 → 24 < n → witnessExists n = true := by native_decide

#print axioms p647_bounded_native
