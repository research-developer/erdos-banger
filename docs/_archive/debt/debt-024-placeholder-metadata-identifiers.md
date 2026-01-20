# Technical Debt 024: Placeholder Metadata (Authors / Contact Email)

**Date:** 2026-01-20
**Status:** Fixed
**Fixed In:** (pending commit)
**Priority:** P3 (Polish / OSS hygiene)
**Impact:** Unprofessional packaging metadata; unclear contact identity for polite API usage

## Summary

Some repository/package metadata still contains placeholders (likely from early scaffolding). This is low-risk but should be corrected before broader contributor onboarding or publishing.

## Evidence

### Package metadata placeholders

- File: `pyproject.toml`
- Current:
  - `authors = [{ name = "Your Name", email = "you@example.com" }]` (`pyproject.toml:9`)

### API contact placeholder

- File: `docs/specs/spec-020-openalex-integration.md`
- Current:
  - Polite pool example uses `?mailto=you@example.com` (`docs/specs/spec-020-openalex-integration.md:50`)

## Proposed Fix

- Replace placeholders with real project contact info (or remove the author block entirely until it’s known).
- Prefer a stable project contact email (e.g., `maintainers@…`) over a personal address if this will be long-lived.

## Acceptance Criteria

- `pyproject.toml` contains no placeholder author identity.
- Specs contain no placeholder emails.
