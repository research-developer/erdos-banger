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
