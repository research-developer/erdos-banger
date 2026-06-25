# Erdős Certify+Lean Workbench — Runbook

A self-contained, mathlib-free pipeline that turns decide-and-certify verdicts and
exact zero-float searches into Lean files the kernel checks. The agent is the
**router**; the Lean kernel is the **sole judge**. Nothing is "proved" until
`erdos lean check` exits 0.

Per problem (or sub-goal):

1. **recognize/route** — call decide-and-certify `recognize`/`certify_or_abstain`.
   - magma equational law / `decide`/`omega` goal → **certify path** (step 2)
   - dataset status `falsifiable`/`verifiable`/`decidable`, finite → **sieve path** (step 3)
   - else → existing `erdos loop` (LLM fallback, unchanged)

2. **certify path** — call `decide_implication(eq1, eq2)`.
   - verdict FALSE → take `witness {order, table}` → `certkit.emit_countermodel(...)`
     → write to `certkit/lean/Cert/<Name>.lean` → kernel-check (step 4). (v1 self-contained.)
   - verdict TRUE → the MCP Lean cert uses the solver's Judge* env; checking it there is v2.

3. **sieve path** — run the exact zero-float search (`certkit.sieve647` pattern: NumPy
   integer sieve / `Fraction`) to get the witness or bounded fact →
   `certkit.emit_bounded_decide(...)` → write Lean → kernel-check (step 4).

4. **kernel-check (sole anchor)** — there are TWO distinct checks here, and they read
   two different things. **Use the right tool for the right question.**

   - **Gate — does it kernel-check at all? (pass/fail)**

     ```bash
     uv run erdos lean check certkit/lean/Cert/<Name>.lean --path certkit/lean
     ```

     Exit 0 ⇒ the file compiles and the theorem holds. This is the verdict that
     counts. **But this command DROPS the `#print axioms` output** — it runs
     `lake build <module>` and parses only error/warning diagnostics into a
     pass/fail result, so the axiom list never appears in its stdout/stderr (and a
     cached build re-emits nothing). Do **not** grep this output for axioms; it is
     a gate, not an axioms reader.

   - **Axioms reader — what is the trust base? (`Lean.ofReduceBool` or not)**

     ```bash
     cd certkit/lean && lake env lean Cert/<Name>.lean
     ```

     This elaborates the file fresh and prints the `#print axioms` line to stdout.
     Read it here:
     - pure `decide` ⇒ **no `Lean.ofReduceBool`** (e.g. `[propext]`, or "does not
       depend on any axioms"). The witness-pure baseline.
     - `native_decide` ⇒ **`Lean.ofReduceBool`** present (with `Lean.trustCompiler`).
       Record it — that is the trust delta.

**Trust rule:** a proposer only proposes; nothing counts until `erdos lean check`
exits 0 (the gate). Prefer `decide`; use `native_decide` only when `decide` is too
slow, and always keep the `#print axioms` line in the file and confirm it with
`lake env lean` so the trusted base is visible.

## The two golden certs (verified examples)

| cert | tactic | gate (`erdos lean check`) | axioms (`lake env lean`) | `Lean.ofReduceBool`? |
|------|--------|---------------------------|---------------------------|----------------------|
| `Cert/AssocNotComm.lean` (W1 counter-model) | `decide` | exit 0 | `'certify_cm' depends on axioms: [propext]` | NO |
| `Cert/P647Bounded.lean` (W2 sieve, B=50) | `decide` | exit 0 | `'p647_bounded' does not depend on any axioms` | NO |
| `Cert/P647BoundedNative.lean` (W2 sieve SCALE, B=1000) | `native_decide` | exit 0 | `'p647_bounded_native' depends on axioms: [Lean.ofReduceBool, Lean.trustCompiler]` | YES |

The W2 pair is the whole point: identical statement shape, larger bound, paid for in
compiled-evaluator trust. The `decide` cert anchors to the kernel with no extra
axioms; the `native_decide` cert scales 20× (B=50 → B=1000) but adds
`Lean.ofReduceBool` — and that delta is explicit, in the file and in
`lake env lean` output.

## Reproduce the golden certs

```bash
uv run pytest tests/certkit/ -v
```

The acceptance suite `tests/certkit/test_golden_certs.py` enforces exactly the table
above against the real kernel: for each cert it runs the `erdos lean check` gate
(asserts exit 0) **and** runs `lake env lean` to assert `Lean.ofReduceBool`
presence/absence. It uses two helpers — `_gate(relpath)` (the pass/fail gate) and
`_axioms(cert_subpath)` (the axioms reader) — precisely because `erdos lean check`
cannot answer the axioms question. No mocks: both helpers shell out to the real
toolchain, and the kernel is the sole judge.
