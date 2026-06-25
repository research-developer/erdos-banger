"""Golden ↔ emitter pin tests (drift detection).

Each committed ``.lean`` golden MUST be byte-for-byte the emitter's output for
its parameters. These pins assert that equality so any future drift — a hand
edit to the golden, or an emitter change that is not reflected in the golden —
fails loudly here, well before the (slow) kernel acceptance suite.

The emitter is the single source of truth for the golden text; provenance/tuning
rationale lives in the runbook and the task report, NOT inside the generated
``.lean`` (which is why these files are pure emitter output).
"""

from __future__ import annotations

import pathlib

from certkit.emit_bounded_decide import emit_p647_bounded
from certkit.emit_countermodel import emit_countermodel

REPO = pathlib.Path(__file__).resolve().parents[2]
LEAN_CERT = REPO / "certkit" / "lean" / "Cert"


def test_pin_assoc_not_comm():
    expected = emit_countermodel(
        2, [[0, 1], [0, 1]], "x◇(y◇z)=(x◇y)◇z", "x◇y=y◇x"
    )
    assert (LEAN_CERT / "AssocNotComm.lean").read_text() == expected


def test_pin_p647_bounded():
    expected = emit_p647_bounded(50, "decide")
    assert (LEAN_CERT / "P647Bounded.lean").read_text() == expected


def test_pin_p647_bounded_native():
    expected = emit_p647_bounded(1000, "native_decide", "p647_bounded_native")
    assert (LEAN_CERT / "P647BoundedNative.lean").read_text() == expected
