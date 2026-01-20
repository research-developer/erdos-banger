# Technical Debt 023: Security Lint Suppressions (XML + MD5)

**Date:** 2026-01-20
**Status:** Fixed
**Fixed In:** (commit pending)
**Priority:** P2 (Defense-in-depth)
**Impact:** Harder-to-audit security posture; reviewers must reason about exceptions instead of policy

## Summary

The codebase currently suppresses Ruff/Bandit security rules in a few places. In each case there is a plausible justification (trusted inputs, non-cryptographic hashing), but we should either:

1. Remove the suppression by using safer primitives, or
2. Document the threat model explicitly in code and/or docs.

## Evidence

### XML parsing from network content

- File: `src/erdos/core/arxiv_client.py`
- Line: `src/erdos/core/arxiv_client.py:42`
- Code (via Ruff ignore): `root = ET.fromstring(xml_text)  # noqa: S314`

**Risk:** XML entity expansion / parser hardening concerns when parsing remote XML.

**Possible fixes (choose one):**
- Use `defusedxml` for parsing (preferred defense-in-depth).
- If keeping `xml.etree`, add an explicit comment documenting why arXiv XML is treated as trusted enough for this use and what guardrails exist (timeouts, size limits, etc.).

### MD5 used for cache hash

- File: `src/erdos/core/ingest.py`
- Line: `src/erdos/core/ingest.py:705`
- Code (via Ruff ignore): `hashlib.md5(tarball_bytes).hexdigest()  # noqa: S324`

**Risk:** MD5 is a cryptographic anti-pattern; even if used only as a cache key, it looks suspicious and requires reviewer context.

**Possible fixes (choose one):**
- Replace with `hashlib.sha256(...)` or `hashlib.blake2b(...)` (no need for suppression).
- If keeping MD5 for speed, add an explicit comment explaining it is used as a non-security cache key and why collisions are acceptable (and keep the suppression).

## Acceptance Criteria

- No `# noqa: S314` or `# noqa: S324` remains without an explicit threat-model comment.
- CI still passes (`make ci`).
