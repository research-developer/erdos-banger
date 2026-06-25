from certkit.emit_bounded_decide import emit_p647_bounded

def test_defines_tau_and_witness():
    src = emit_p647_bounded(50)
    assert "def tau (m : Nat) : Nat :=" in src
    assert "(List.range n).any (fun m => decide (n + 3 ≤ m + tau m))" in src

def test_theorem_uses_bound_and_tactic():
    src = emit_p647_bounded(50, tactic="decide")
    assert "theorem p647_bounded : ∀ n, n < 51 → 24 < n → witnessExists n = true := by decide" in src
    assert "#print axioms p647_bounded" in src

def test_native_variant():
    src = emit_p647_bounded(1000, tactic="native_decide")
    assert "n < 1001" in src and "by native_decide" in src
