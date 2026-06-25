# Erdős Certify+Lean Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic core of an agent-orchestrated Erdős workbench — two proposer fast-paths (decide-and-certify counter-models, exact-sieve→Lean facts) whose every output is re-checked by the Lean kernel — validated by two passing golden certificates.

**Architecture:** `recognize/route → {certify-MCP | sieve→Lean} → erdos lean check (sole trust anchor) → record cert + #print axioms`. The agent drives routing and the MCP; thin pure-Python helpers in `certkit/` turn a finite witness/counter-model into self-contained core-Lean `decide` proofs. Nothing is trusted until the kernel accepts.

**Tech Stack:** Python 3.11 + uv (erdos-banger CLI), NumPy (exact integer sieve), Lean 4 v4.27.0 (core only — **no mathlib** in v1), `erdos lean check` as kernel runner, decide-and-certify MCP.

## Global Constraints

- **Zero-float discipline:** all arithmetic is exact `int` / `fractions.Fraction` / NumPy integer dtypes. No `float`, no `math.*` in any computation path.
- **Witness-pure trust:** prefer pure-kernel `decide`; use `native_decide` only when `decide` is too slow, and **always** emit `#print axioms <thm>` so the added `Lean.ofReduceBool` (native) vs. its absence (pure) is visible in the cert output.
- **Kernel is sole judge:** a proposer (MCP / sieve) only *proposes*; acceptance = `erdos lean check` exit 0. Never record a cert as valid without a kernel pass.
- **Lean:** core Lean 4 `v4.27.0` only for v1 certs (defines its own `tau`); no mathlib dependency.
- **Repo / branch:** `~/git/erdos-banger`, branch `feat/erdos-certify-workbench`. Python lives under `certkit/`; Lean certs under `certkit/lean/Cert/`.
- **Worktree split (execution):** W1 (certify path) = Tasks 2–3 in worktree `wt-certify`; W2 (sieve path) = Tasks 4–5 in worktree `wt-sieve`; Tasks 1 and 6 on the base branch. W1/W2 share only Task 1's Lean project scaffold.

---

### Task 1: Minimal mathlib-free Lean cert project + toolchain check

**Files:**
- Create: `certkit/lean/lakefile.toml`
- Create: `certkit/lean/lean-toolchain`
- Create: `certkit/lean/Cert.lean`
- Create: `certkit/lean/Cert/Smoke.lean`

**Interfaces:**
- Produces: a Lean project at `certkit/lean/` checkable via `erdos lean check <file> --path certkit/lean`. No mathlib → builds in seconds.

- [ ] **Step 1: Create the toolchain pin**

`certkit/lean/lean-toolchain`:
```
leanprover/lean4:v4.27.0
```

- [ ] **Step 2: Create a mathlib-free lakefile**

`certkit/lean/lakefile.toml`:
```toml
name = "cert"
defaultTargets = ["Cert"]

[[lean_lib]]
name = "Cert"
```

- [ ] **Step 3: Create the library root + a smoke file**

`certkit/lean/Cert.lean`:
```lean
import Cert.Smoke
```

`certkit/lean/Cert/Smoke.lean`:
```lean
theorem smoke : 2 + 2 = 4 := by decide
#print axioms smoke
```

- [ ] **Step 4: Verify the kernel runner works**

Run: `cd ~/git/erdos-banger && uv run erdos lean check certkit/lean/Cert/Smoke.lean --path certkit/lean`
Expected: exit 0, no errors; output shows `'smoke' depends on axioms: [propext, ...]` with **no** `Lean.ofReduceBool`.
(If elan must install `v4.27.0`, that one-time download is expected. If `erdos lean check` cannot target a bare project, fall back to `cd certkit/lean && lake env lean Cert/Smoke.lean` and record that command for later tasks.)

- [ ] **Step 5: Commit**

```bash
git add certkit/lean
git commit -m "feat(certkit): mathlib-free Lean cert project + smoke check"
```

---

### Task 2: Magma-law → Lean translator (`certkit/lawlean.py`)

**Files:**
- Create: `certkit/__init__.py` (empty)
- Create: `certkit/lawlean.py`
- Test: `tests/certkit/test_lawlean.py`

**Interfaces:**
- Produces: `law_to_lean(law: str, n: int) -> str` rendering a flat equational law over op `◇`/`*`/`·` as `∀ <vars> : Fin n, <lhs> = <rhs>` using the Lean operator name `op`. Helpers `parse_term`, `vars_in`, `render`.

- [ ] **Step 1: Write the failing test**

`tests/certkit/test_lawlean.py`:
```python
from certkit.lawlean import law_to_lean

def test_commutativity():
    assert law_to_lean("x◇y=y◇x", 2) == "∀ x y : Fin 2, op x y = op y x"

def test_associativity_nesting():
    assert law_to_lean("x◇(y◇z)=(x◇y)◇z", 2) == \
        "∀ x y z : Fin 2, op x (op y z) = op (op x y) z"

def test_star_operator_and_var_order():
    # variables collected in first-appearance order across lhs then rhs
    assert law_to_lean("a*b=b*c", 3) == "∀ a b c : Fin 3, op a b = op b c"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_lawlean.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'certkit.lawlean'`

- [ ] **Step 3: Write the implementation**

`certkit/lawlean.py`:
```python
"""Translate a flat magma equational law (term = term over one binary op) into a
Lean ∀-quantified Prop over `Fin n`, using the Lean operator name `op`.

Grammar: TERM := VAR | '(' TERM ')' | TERM OP TERM   (OP ∈ {◇,*,·}; VAR ∈ [a-z]).
Fully-parenthesized inputs (the ETP catalogue form) parse unambiguously; bare
chains parse left-associatively.
"""
from __future__ import annotations
from dataclasses import dataclass

OPS = {"◇", "*", "·"}


@dataclass
class Var:
    name: str


@dataclass
class App:
    left: object
    right: object


def _tokenize(s: str) -> list[str]:
    toks: list[str] = []
    for ch in s:
        if ch.isspace():
            continue
        if ch in OPS or ch in "()":
            toks.append(ch)
        elif ch.isalpha() and len(ch) == 1:
            toks.append(ch)
        else:
            raise ValueError(f"bad char {ch!r} in {s!r}")
    return toks


class _Parser:
    def __init__(self, toks: list[str]) -> None:
        self.t = toks
        self.i = 0

    def _peek(self) -> str | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def _next(self) -> str:
        tok = self.t[self.i]
        self.i += 1
        return tok

    def factor(self) -> object:
        tok = self._next()
        if tok == "(":
            inner = self.term()
            assert self._next() == ")", "unbalanced parenthesis"
            return inner
        if tok.isalpha():
            return Var(tok)
        raise ValueError(f"unexpected token {tok!r}")

    def term(self) -> object:
        node = self.factor()
        while self._peek() in OPS:
            self._next()  # consume the operator
            node = App(node, self.factor())  # left-associative
        return node


def parse_term(s: str) -> object:
    p = _Parser(_tokenize(s))
    node = p.term()
    assert p._peek() is None, "trailing tokens"
    return node


def vars_in(t: object, acc: list[str] | None = None) -> list[str]:
    acc = [] if acc is None else acc
    if isinstance(t, Var):
        if t.name not in acc:
            acc.append(t.name)
    else:
        vars_in(t.left, acc)
        vars_in(t.right, acc)
    return acc


def _atom(t: object) -> str:
    return t.name if isinstance(t, Var) else f"({render(t)})"


def render(t: object) -> str:
    if isinstance(t, Var):
        return t.name
    return f"op {_atom(t.left)} {_atom(t.right)}"


def law_to_lean(law: str, n: int) -> str:
    lhs_s, rhs_s = law.split("=")
    lhs, rhs = parse_term(lhs_s), parse_term(rhs_s)
    vs = vars_in(lhs)
    for v in vars_in(rhs):
        if v not in vs:
            vs.append(v)
    binder = " ".join(vs)
    return f"∀ {binder} : Fin {n}, {render(lhs)} = {render(rhs)}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_lawlean.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add certkit/__init__.py certkit/lawlean.py tests/certkit/test_lawlean.py
git commit -m "feat(certkit): flat magma-law → Lean Fin n translator"
```

---

### Task 3: Counter-model emitter + W1 golden cert (`certkit/emit_countermodel.py`)

**Files:**
- Create: `certkit/emit_countermodel.py`
- Test: `tests/certkit/test_emit_countermodel.py`
- Create (generated, committed as the golden artifact): `certkit/lean/Cert/AssocNotComm.lean`

**Interfaces:**
- Consumes: `law_to_lean` (Task 2).
- Produces: `emit_countermodel(order: int, table: list[list[int]], eq1: str, eq2: str, thm: str = "certify_cm") -> str` returning self-contained core-Lean that defines the magma from `table` and proves `(<eq1>) ∧ ¬(<eq2>)` by `decide`, ending with `#print axioms`.

- [ ] **Step 1: Write the failing test**

`tests/certkit/test_emit_countermodel.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_emit_countermodel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'certkit.emit_countermodel'`

- [ ] **Step 3: Write the implementation**

`certkit/emit_countermodel.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_emit_countermodel.py -v`
Expected: 2 passed.

- [ ] **Step 5: Generate the golden W1 cert from the live MCP witness**

The decide-and-certify MCP returns, for `decide_implication(eq1="(x*y)*z = x*(y*z)", eq2="x*y = y*x")`, verdict `false` with witness `{order: 2, table: [[0,1],[0,1]]}`. Generate the Lean file:
```bash
cd ~/git/erdos-banger && uv run python -c "
from certkit.emit_countermodel import emit_countermodel
src = emit_countermodel(2, [[0,1],[0,1]], 'x◇(y◇z)=(x◇y)◇z', 'x◇y=y◇x')
open('certkit/lean/Cert/AssocNotComm.lean','w').write(src)
print(src)"
```

- [ ] **Step 6: Kernel-check the golden cert**

Run: `cd ~/git/erdos-banger && uv run erdos lean check certkit/lean/Cert/AssocNotComm.lean --path certkit/lean`
Expected: exit 0; `#print axioms certify_cm` lists axioms **without** `Lean.ofReduceBool` (pure-kernel). If `decide` errors on Fin pattern/`getD` reduction, debug with `mcp__lean-lsp__lean_run_code` on the file body and adjust the `op` definition, then re-run.

- [ ] **Step 7: Commit**

```bash
git add certkit/emit_countermodel.py tests/certkit/test_emit_countermodel.py certkit/lean/Cert/AssocNotComm.lean
git commit -m "feat(certkit): counter-model emitter + W1 golden cert (assoc ⊭ comm)"
```

---

### Task 4: Bounded-decide emitter + W2 golden cert (`certkit/emit_bounded_decide.py`)

**Files:**
- Create: `certkit/emit_bounded_decide.py`
- Test: `tests/certkit/test_emit_bounded_decide.py`
- Create (generated, committed): `certkit/lean/Cert/P647Bounded.lean`, `certkit/lean/Cert/P647BoundedNative.lean`

**Interfaces:**
- Produces: `emit_p647_bounded(B: int, tactic: str = "decide", thm: str = "p647_bounded") -> str` — core-Lean defining `tau`, `witnessExists`, and proving `∀ n, n < B+1 → 24 < n → witnessExists n = true` by `tactic`, ending with `#print axioms`.

- [ ] **Step 1: Write the failing test**

`tests/certkit/test_emit_bounded_decide.py`:
```python
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
    src = emit_p647_bounded(5000, tactic="native_decide")
    assert "n < 5001" in src and "by native_decide" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_emit_bounded_decide.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

`certkit/emit_bounded_decide.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_emit_bounded_decide.py -v`
Expected: 3 passed.

- [ ] **Step 5: Generate + kernel-check the pure-`decide` golden cert (tune B)**

```bash
cd ~/git/erdos-banger && uv run python -c "
from certkit.emit_bounded_decide import emit_p647_bounded
open('certkit/lean/Cert/P647Bounded.lean','w').write(emit_p647_bounded(50,'decide'))"
uv run erdos lean check certkit/lean/Cert/P647Bounded.lean --path certkit/lean
```
Expected: exit 0; axioms list **without** `Lean.ofReduceBool`. If `decide` is too slow/times out (kernel-reducing `List.range`/`tau`), lower B (try 40, then 30) until it passes; record the largest B that pure `decide` clears in a comment at the top of the file.

- [ ] **Step 6: Generate + kernel-check the `native_decide` scale cert**

```bash
cd ~/git/erdos-banger && uv run python -c "
from certkit.emit_bounded_decide import emit_p647_bounded
open('certkit/lean/Cert/P647BoundedNative.lean','w').write(emit_p647_bounded(5000,'native_decide','p647_bounded_native'))"
uv run erdos lean check certkit/lean/Cert/P647BoundedNative.lean --path certkit/lean
```
Expected: exit 0; axioms list **includes** `Lean.ofReduceBool` — the explicit trust delta vs. the pure cert.

- [ ] **Step 7: Commit**

```bash
git add certkit/emit_bounded_decide.py tests/certkit/test_emit_bounded_decide.py certkit/lean/Cert/P647Bounded.lean certkit/lean/Cert/P647BoundedNative.lean
git commit -m "feat(certkit): bounded-decide emitter + W2 golden cert (Erdős #647)"
```

---

### Task 5: Exact-sieve consistency oracle (`certkit/sieve647.py`)

**Files:**
- Create: `certkit/sieve647.py`
- Test: `tests/certkit/test_sieve647.py`

**Interfaces:**
- Produces: `verify_647_bound(B: int) -> dict` with keys `B`, `holds_for_all` (bool: every 24<n≤B has max_{m<n}(m+τ(m)) > n+2), `first_violation` (int|None). Ties the Lean bound to an independent exact computation (the divisor sieve run live this session).

- [ ] **Step 1: Write the failing test**

`tests/certkit/test_sieve647.py`:
```python
from certkit.sieve647 import verify_647_bound

def test_bound_holds_to_5000():
    r = verify_647_bound(5000)
    assert r["holds_for_all"] is True
    assert r["first_violation"] is None

def test_satisfying_n_are_only_le_24():
    # n=24 satisfies (max ≤ n+2); n=25 must NOT (consistency with the theorem)
    r25 = verify_647_bound(25)
    assert r25["holds_for_all"] is True  # the bound (max > n+2) holds for the single n=25
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_sieve647.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

`certkit/sieve647.py`:
```python
"""Independent exact-integer oracle for the bounded Erdős #647 fact, reusing the
divisor-count sieve. Confirms max_{m<n}(m+τ(m)) > n+2 for all 24 < n ≤ B, so the
Lean `decide` cert's content is matched by a separate code path. Zero float.
"""
from __future__ import annotations
import numpy as np


def verify_647_bound(B: int) -> dict:
    tau = np.zeros(B + 1, dtype=np.int64)
    for i in range(1, B + 1):
        tau[i::i] += 1  # exact divisor-count sieve
    m = np.arange(B + 1, dtype=np.int64)
    prefix_max = np.maximum.accumulate(m + tau)  # prefix_max[k] = max_{j<=k}(j+τ(j))
    n = np.arange(25, B + 1, dtype=np.int64)     # the n with 24 < n ≤ B
    over = prefix_max[n - 1] > (n + 2)           # condition max_{m<n}(...) > n+2
    holds = bool(np.all(over))
    first = None if holds else int(n[np.argmin(over)])
    return {"B": B, "holds_for_all": holds, "first_violation": first}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_sieve647.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add certkit/sieve647.py tests/certkit/test_sieve647.py
git commit -m "feat(certkit): exact-sieve oracle confirming bounded #647 (zero float)"
```

---

### Task 6: Runbook + final both-certs acceptance

**Files:**
- Create: `docs/superpowers/runbooks/erdos-certify-workbench.md`
- Create: `tests/certkit/test_golden_certs.py`

**Interfaces:**
- Consumes: all `certkit/` modules and the four committed Lean files.
- Produces: the runbook (routing + trust rules + reproduce-the-certs recipe) and an acceptance test asserting both golden Lean files kernel-check.

- [ ] **Step 1: Write the acceptance test**

`tests/certkit/test_golden_certs.py`:
```python
import subprocess, pathlib
REPO = pathlib.Path(__file__).resolve().parents[2]

def _check(rel: str) -> str:
    out = subprocess.run(
        ["uv", "run", "erdos", "lean", "check", rel, "--path", "certkit/lean"],
        cwd=REPO, capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, f"{rel} failed:\n{out.stdout}\n{out.stderr}"
    return out.stdout + out.stderr

def test_w1_certify_pure_kernel():
    log = _check("certkit/lean/Cert/AssocNotComm.lean")
    assert "Lean.ofReduceBool" not in log  # pure-kernel certify path

def test_w2_sieve_pure_kernel():
    log = _check("certkit/lean/Cert/P647Bounded.lean")
    assert "Lean.ofReduceBool" not in log  # pure-kernel sieve path

def test_w2_native_scale_declares_trust():
    log = _check("certkit/lean/Cert/P647BoundedNative.lean")
    assert "Lean.ofReduceBool" in log  # native_decide trust delta is explicit
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/test_golden_certs.py -v`
Expected: 3 passed (both fast-paths chain to the kernel; trust deltas as designed). Fix any cert that fails before proceeding.

- [ ] **Step 3: Write the runbook**

`docs/superpowers/runbooks/erdos-certify-workbench.md` — document, in prose + commands:
```markdown
# Erdős Certify+Lean Workbench — Runbook

The agent is the router. Per problem (or sub-goal):

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
4. **kernel-check (sole anchor)** —
   `uv run erdos lean check certkit/lean/Cert/<Name>.lean --path certkit/lean`.
   Read `#print axioms`: pure `decide` ⇒ no `Lean.ofReduceBool`; `native_decide`
   ⇒ `Lean.ofReduceBool` present (record it — that is the trust delta).

**Trust rule:** a proposer only proposes; nothing counts until `erdos lean check` exits 0.
Prefer `decide`; use `native_decide` only when `decide` is too slow, and always keep the
`#print axioms` line so the trusted base is visible.

**Reproduce the golden certs:** `uv run pytest tests/certkit/ -v`.
```

- [ ] **Step 4: Run the whole certkit suite**

Run: `cd ~/git/erdos-banger && uv run pytest tests/certkit/ -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/runbooks/erdos-certify-workbench.md tests/certkit/test_golden_certs.py
git commit -m "docs(certkit): workbench runbook + golden-cert acceptance suite"
```

---

## Self-Review

**Spec coverage:** router (Task 6 runbook), certify fast-path (Tasks 2–3), sieve→Lean fast-path (Tasks 4–5), kernel anchor (Task 1 + every check step), witness-pure trust + `#print axioms` (Tasks 3/4/6), two golden certs (Tasks 3 & 4, asserted in Task 6), `certkit/` helpers (all tasks), worktree split (Global Constraints). LLM-loop fallback is referenced as existing/unchanged (correct — out of scope). Covered.

**Placeholder scan:** every code/Lean/command step contains literal content; B-tuning and the TRUE-path are explicit decisions, not TODOs. None found.

**Type consistency:** `law_to_lean`/`parse_term`/`vars_in`/`render` (Task 2) used by `emit_countermodel` (Task 3); `emit_p647_bounded` signature consistent Tasks 4↔6; `verify_647_bound` keys consistent Task 5↔tests; Lean names (`op`, `tbl`, `tau`, `witnessExists`, `certify_cm`, `p647_bounded`) consistent across emitters, files, and acceptance asserts. Consistent.
