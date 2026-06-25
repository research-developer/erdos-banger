"""Emit a self-contained core-Lean proof of the bounded Erdős #647 fact:
for 24 < n ≤ B, max_{m<n}(m+τ(m)) > n+2, i.e. some m<n has m+τ(m) ≥ n+3.
τ(m) is defined here (divisor count) so no mathlib is needed. Witness-pure:
`decide` re-runs the finite search in-kernel; `native_decide` only when forced.
"""
from __future__ import annotations


def emit_p647_bounded(B: int, tactic: str = "decide", thm: str = "p647_bounded") -> str:
    return (
        f"-- Erdős #647 (bounded): for 24 < n ≤ {B}, max_{{m<n}}(m+τ(m)) > n+2.\n"
        f"-- τ(m) = number of divisors, defined here (no mathlib).\n"
        f"def tau (m : Nat) : Nat :=\n"
        f"  ((List.range (m+1)).filter (fun d => d != 0 && m % d == 0)).length\n"
        f"\n"
        f"def witnessExists (n : Nat) : Bool :=\n"
        f"  (List.range n).any (fun m => decide (n + 3 ≤ m + tau m))\n"
        f"\n"
        f"theorem {thm} : ∀ n, n < {B + 1} → 24 < n → witnessExists n = true := by {tactic}\n"
        f"\n"
        f"#print axioms {thm}\n"
    )
