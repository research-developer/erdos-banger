from certkit.emit_countermodel import emit_countermodel

CM = dict(order=2, table=[[0, 1], [0, 1]],
          eq1="x◇(y◇z)=(x◇y)◇z", eq2="x◇y=y◇x")


def test_emits_table_and_op():
    src = emit_countermodel(**CM)
    assert "def tbl : List (List (Fin 2)) := [[0, 1], [0, 1]]" in src
    assert "def op (a b : Fin 2) : Fin 2 := (tbl.getD a.val []).getD b.val 0" in src


def test_emits_theorem_and_axioms_print():
    src = emit_countermodel(**CM)
    assert ("theorem certify_cm : (∀ x y z : Fin 2, op x (op y z) = op (op x y) z) "
            "∧ ¬ (∀ x y : Fin 2, op x y = op y x) := by decide") in src
    assert "#print axioms certify_cm" in src
