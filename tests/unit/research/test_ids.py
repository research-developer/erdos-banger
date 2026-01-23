from __future__ import annotations

import re
from datetime import UTC, datetime

from erdos.core.research.ids import generate_record_id


def test_generate_record_id_matches_spec_regex() -> None:
    now = datetime(2026, 1, 23, 0, 5, 1, tzinfo=UTC)
    rid = generate_record_id("lead", now=now)
    assert re.match(r"^lead_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{6}$", rid)
