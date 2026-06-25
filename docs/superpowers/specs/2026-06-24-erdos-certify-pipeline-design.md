# Erdős Certify+Lean Workbench — Design

- **Date:** 2026-06-24
- **Status:** Approved (brainstorming) → ready for implementation plan
- **Author:** Preston + Claude (agent-orchestrated)
- **Lane:** "Build the certify/Lean pipeline first" so every later proof auto-certifies.

## Goal & Context

Stand up an **agent-orchestrated workbench** that routes an Erdős problem (or sub-goal)
to the fastest *deterministic* prover that can settle it, and certifies the result with
the Lean kernel. `erdos-banger` already provides the Lean half (`lean init/check/
formalize/import/prove`, `core/loop/` LLM↔`lean check` iteration, `core/formal_conjectures/`
upstream import). **Neither decide-and-certify nor an exact-search oracle is wired in.**
This workbench adds the two missing deterministic fast-paths and a router, with
`erdos lean check` as the single trust anchor.

Not in scope (v1): CLI-native autonomous batch backend; changes to the existing LLM loop
(reused untouched as fallback); a full router harness over all 53 decidable/falsifiable/
verifiable problems.

## Locked Decisions

1. **Integration model:** agent-orchestrated workbench — the agent is the router; the
   pipeline is a runbook + thin helper scripts, not new autonomous CLI plumbing.
2. **v1 scope:** both deterministic fast-paths (certify-MCP + exact-sieve→Lean) + kernel
   anchor; existing LLM loop reused as fallback.
3. **Cert trust model:** witness-pure — verifiable (∃) → witness + `decide`/`norm_num`
   (kernel re-runs, zero extra trust); bounded-universal sweeps too big for pure `decide`
   → `native_decide`, but **always emit `#print axioms`** so `Lean.ofReduceBool`/compiler
   trust is explicit.
4. **Validation:** two golden end-to-end certs (below), each passing `erdos lean check`.

## Architecture — one trust spine, three proposers

```
problem id ─► recognize / route ─► { certify-MCP | sieve→Lean | (existing LLM loop) }
                                          └────────► erdos lean check  ◄── SOLE trust anchor
                                                            └─► record cert + #print axioms
```

Nothing is believed until the Lean kernel accepts. Certify / sieve / LLM are *proposers*;
`erdos lean check` is judge. A proposer may **abstain/fail** → fall through to the next;
a kernel **reject** is recorded with its reason and never trusted.

## Components (each independently testable)

- **Router (agent-driven):** classify the goal via decide-and-certify `recognize` /
  `certify_or_abstain` (equational-law or `decide`/`omega` fragment?) and via the
  problem's dataset status (`falsifiable`/`verifiable`/`decidable` → exact-sieve test).
- **Certify fast-path:** MCP `decide_implication` → returns a kernel-checkable Lean cert
  (TRUE) or finite counter-model (FALSE) → `splice_cert.py` inserts it into a Lean file →
  `erdos lean check`.
- **Sieve→Lean fast-path:** zero-error exact search (NumPy divisor/prime sieve, exact
  `Fraction`/bignum — no floats) produces a witness or bounded fact → emit a Lean
  `decide`/`norm_num` theorem (`native_decide` only when forced) → `erdos lean check`.
- **`certkit/` helpers (in erdos-banger):** `emit_lean_witness.py`,
  `emit_lean_bounded_decide.py`, `splice_cert.py`. Small, single-purpose, kernel-anchored.
- **Runbook:** documents the routing decision + the witness-pure trust rules; promoted to
  a reusable skill once the two golden certs pass.

## Two Golden Certs (acceptance tests)

- **W1 — certify path:** `(x◇y)◇z = x◇(y◇z) ⊭ x◇y = y◇x`. MCP returns the right-projection
  counter-model on `Fin 2` + Lean cert → `erdos lean check` PASS → `#print axioms`.
- **W2 — sieve→Lean path:** the bounded form of **Erdős #647**, reusing today's divisor
  sieve: `∀ n, 24 < n → n ≤ B → ∃ m < n, m + τ(m) ≥ n+3` (equivalently
  `max_{m<n}(m+τ(m)) > n+2`). Pure-kernel `decide` at small B (e.g. 200), then push B with
  `native_decide`; `#print axioms` shown each time. Ties the cert to the live computation
  that found "24 is the last satisfying n ≤ 3×10⁷".

## Worktrees (parallel)

Two git worktrees off `erdos-banger`, one per golden cert, worked sequentially-in-parallel.
They share only the one-time `erdos lean init` scaffold; otherwise independent → no merge
conflicts.

- **W1** `wt-certify`: certify path + `splice_cert.py` + W1 cert.
- **W2** `wt-sieve`: `emit_lean_witness.py` / `emit_lean_bounded_decide.py` + W2 #647 cert.

`certkit/` + runbook land on whichever finishes first; the other rebases onto it.

## Error Handling & Testing

- Proposer abstain/fail → fall through; never trust an unchecked proposer claim.
- Kernel reject → record file + error + which proposer produced it.
- The two golden certs are the acceptance tests, gated on `erdos lean check` exit code.
  Each helper script gets a focused unit test (emit → parse → `lean check` PASS).

## Success Criteria

Both golden certs pass `erdos lean check` with `#print axioms` captured, produced through
the router + helper scripts, with the runbook documenting the path. That proves both
deterministic fast-paths chain to the Lean kernel and the workbench is ready to point at
real targets.
