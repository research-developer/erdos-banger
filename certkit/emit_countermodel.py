"""Emit a self-contained core-Lean proof that a finite magma (given by its
operation table — a decide-and-certify FALSE counter-model) satisfies eq1 but
not eq2. Witness-pure: the kernel re-checks the finite model via `decide`.
"""
from __future__ import annotations
from certkit.lawlean import law_to_lean


def emit_countermodel(order: int, table: list[list[int]], eq1: str, eq2: str,
                      thm: str = "certify_cm") -> str:
    rows = ", ".join("[" + ", ".join(str(x) for x in row) + "]" for row in table)
    prop1 = law_to_lean(eq1, order)
    prop2 = law_to_lean(eq2, order)
    return (
        f"-- decide-and-certify counter-model: {eq1!r} does NOT imply {eq2!r}.\n"
        f"-- Re-checked from the finite witness in plain Lean (witness-pure).\n"
        f"def tbl : List (List (Fin {order})) := [{rows}]\n"
        f"def op (a b : Fin {order}) : Fin {order} := (tbl.getD a.val []).getD b.val 0\n"
        f"\n"
        f"theorem {thm} : ({prop1}) ∧ ¬ ({prop2}) := by decide\n"
        f"\n"
        f"#print axioms {thm}\n"
    )
