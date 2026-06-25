"""Both-certs acceptance: the two deterministic fast-paths chain to the Lean kernel.

This suite is the capstone of the Erdős certify+Lean workbench. It proves, against
the *real* Lean kernel (no mocks), that:

  * W1 — the decide-and-certify counter-model re-checks witness-pure
    (`Cert/AssocNotComm.lean`, `decide`, axioms `[propext]`).
  * W2-pure — the exact-sieve bounded fact re-checks witness-pure
    (`Cert/P647Bounded.lean`, `decide`, depends on NO axioms).
  * W2-native — the native_decide SCALE variant kernel-checks but declares its
    trust delta explicitly (`Cert/P647BoundedNative.lean`, `native_decide`,
    axioms include `Lean.ofReduceBool`).

WHY TWO HELPERS (deviation from the task brief's literal `_check()` code):
`erdos lean check` is a *pass/fail gate only* — `LeanRunner.check()` runs
`lake build <module>` and parses stderr for error/warning diagnostics into a
`LeanCheckResult`; it DROPS the `#print axioms` output entirely (and on an
already-built module `lake build` is cached, so nothing is re-emitted at all).
Grepping its stdout/stderr for `Lean.ofReduceBool` therefore can NEVER see the
axioms: the W2-native assertion would FALSE-FAIL and the witness-pure assertions
would pass *vacuously*. So we split the concern:

  * ``_gate(relpath)``  — runs the real ``erdos lean check`` and asserts exit 0.
    This is the kernel's pass/fail verdict (the sole-judge anchor).
  * ``_axioms(cert_subpath)`` — runs ``lake env lean <cert_subpath>`` with
    ``cwd=certkit/lean`` and returns its stdout, which is where Lean actually
    prints the ``#print axioms`` line. We assert ``Lean.ofReduceBool``
    presence/absence on THAT output.

Both helpers invoke real toolchains; the kernel is the sole judge.
"""

from __future__ import annotations

import pathlib
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]
LEAN_PROJECT = REPO / "certkit" / "lean"

# native_decide recompiles + runs the compiled evaluator (~15s); leave generous slack.
TIMEOUT_S = 600


def _gate(relpath: str) -> None:
    """Kernel pass/fail gate: assert ``erdos lean check`` exits 0 for *relpath*.

    *relpath* is given relative to the repo root (matching how a user invokes the
    CLI), e.g. ``certkit/lean/Cert/AssocNotComm.lean``. This is ONLY a gate — it
    does not surface ``#print axioms`` (see module docstring); use ``_axioms`` for
    the trust delta.
    """
    out = subprocess.run(
        ["uv", "run", "erdos", "lean", "check", relpath, "--path", "certkit/lean"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        check=False,
    )
    assert out.returncode == 0, (
        f"erdos lean check failed for {relpath} (exit {out.returncode}):\n"
        f"--- stdout ---\n{out.stdout}\n--- stderr ---\n{out.stderr}"
    )


def _axioms(cert_subpath: str) -> str:
    """Axioms reader: run ``lake env lean <cert_subpath>`` in certkit/lean, return stdout.

    *cert_subpath* is relative to the Lean project root (``certkit/lean``), e.g.
    ``Cert/AssocNotComm.lean``. Lean prints the ``#print axioms`` result to stdout
    during a fresh elaboration here — this is the correct source for the trust
    delta, unlike ``erdos lean check`` which drops it.
    """
    out = subprocess.run(
        ["lake", "env", "lean", cert_subpath],
        cwd=LEAN_PROJECT,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        check=False,
    )
    assert out.returncode == 0, (
        f"lake env lean failed for {cert_subpath} (exit {out.returncode}):\n"
        f"--- stdout ---\n{out.stdout}\n--- stderr ---\n{out.stderr}"
    )
    return out.stdout


def test_w1_certify_pure_kernel() -> None:
    """W1 counter-model: gate passes and the re-check is witness-pure (no ofReduceBool)."""
    _gate("certkit/lean/Cert/AssocNotComm.lean")
    axioms = _axioms("Cert/AssocNotComm.lean")
    assert "depends on axioms: [propext]" in axioms  # witness-pure baseline
    assert "Lean.ofReduceBool" not in axioms  # pure-kernel certify path


def test_w2_sieve_pure_kernel() -> None:
    """W2-pure sieve fact: gate passes and the re-check depends on NO axioms (no ofReduceBool)."""
    _gate("certkit/lean/Cert/P647Bounded.lean")
    axioms = _axioms("Cert/P647Bounded.lean")
    assert "does not depend on any axioms" in axioms  # strongest witness-pure baseline
    assert "Lean.ofReduceBool" not in axioms  # pure-kernel sieve path


def test_w2_native_scale_declares_trust() -> None:
    """W2-native scale variant: gate passes and the trust delta (ofReduceBool) is explicit."""
    _gate("certkit/lean/Cert/P647BoundedNative.lean")
    axioms = _axioms("Cert/P647BoundedNative.lean")
    assert "Lean.ofReduceBool" in axioms  # native_decide trust delta is explicit
