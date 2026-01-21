# Harmonic Aristotle (Vendor Notes)

This folder captures **implementation-oriented notes** for integrating Harmonic’s Aristotle with `erdos-banger`.

## What It Is

Aristotle is a Lean-focused theorem proving system. The public entrypoint is the Python package/CLI:

- `aristotlelib` (PyPI) — provides a Python API and an `aristotle` CLI wrapper.

## Quickstart (CLI)

Install:

```bash
uv pip install aristotlelib
```

Configure (local only; never commit real keys):

```bash
export ARISTOTLE_API_KEY="arstl-..."
```

Run (example pattern from vendor docs):

```bash
aristotle prove-from-file formal/lean/Erdos/Problem006.lean --output-file /tmp/Problem006.solved.lean
```

Optional flags (vendor docs):
- `--informal`
- `--formal-input-context`

## Toolchain Compatibility (Important)

Vendor docs currently state Aristotle expects:

- `leanprover/lean4:v4.24.0`
- `mathlib: v4.24.0`

`erdos-banger` must either:
1. Upgrade its pinned Lean toolchain to match, **or**
2. Treat Aristotle output as “best-effort” and validate it under our toolchain (likely requiring edits).

SPEC-021 defines the integration contract and the compatibility policy.

## Where This Integrates

- **Primary**: `erdos loop` (SPEC-012) as an optional “solver backend”.
- **Secondary**: a dedicated command like `erdos lean prove` (SPEC-021) to run Aristotle against a Lean file and write an output file without overwriting the original.

## References

See `SOURCES.md` for URLs and retrieval dates.
