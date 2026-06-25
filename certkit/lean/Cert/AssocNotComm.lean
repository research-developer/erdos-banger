-- decide-and-certify counter-model: 'x◇(y◇z)=(x◇y)◇z' does NOT imply 'x◇y=y◇x'.
-- Re-checked from the finite witness in plain Lean (witness-pure).
def tbl : List (List (Fin 2)) := [[0, 1], [0, 1]]
def op (a b : Fin 2) : Fin 2 := (tbl.getD a.val []).getD b.val 0

theorem certify_cm : (∀ x y z : Fin 2, op x (op y z) = op (op x y) z) ∧ ¬ (∀ x y : Fin 2, op x y = op y x) := by decide

#print axioms certify_cm
