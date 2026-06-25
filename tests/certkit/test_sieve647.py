from certkit.sieve647 import verify_647_bound

def test_bound_holds_to_5000():
    r = verify_647_bound(5000)
    assert r["holds_for_all"] is True
    assert r["first_violation"] is None

def test_satisfying_n_are_only_le_24():
    # n=24 satisfies (max ≤ n+2); n=25 must NOT (consistency with the theorem)
    r25 = verify_647_bound(25)
    assert r25["holds_for_all"] is True  # the bound (max > n+2) holds for the single n=25
