from certkit.lawlean import law_to_lean


def test_commutativity():
    assert law_to_lean("x◇y=y◇x", 2) == "∀ x y : Fin 2, op x y = op y x"


def test_associativity_nesting():
    assert law_to_lean("x◇(y◇z)=(x◇y)◇z", 2) == \
        "∀ x y z : Fin 2, op x (op y z) = op (op x y) z"


def test_star_operator_and_var_order():
    # variables collected in first-appearance order across lhs then rhs
    assert law_to_lean("a*b=b*c", 3) == "∀ a b c : Fin 3, op a b = op b c"
