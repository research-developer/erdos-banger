# Bug Reports & Adversarial Reviews

This directory contains bug reports, adversarial code reviews, and quality audits for the erdos-banger project.

## Reviews

| Date | Type | Summary | Status |
|------|------|---------|--------|
| 2026-01-17 | Adversarial Review | Full codebase audit covering specs 003-006 | Active |

## Active Bugs

| ID | Title | Priority | Status |
|----|-------|----------|--------|
| BUG-006 | [Ruff lints submodule (CI failure)](bug-006-ruff-lints-submodule.md) | P1 | Open |

## Archived Bugs

All bugs below have been fixed and archived to `docs/_archive/bugs/`.

| ID | Title | Priority | Status | Commit |
|----|-------|----------|--------|--------|
| BUG-001 | Typer `CliRunner` unsupported `mix_stderr` arg | P1 | Fixed | e862a35 |
| BUG-002 | `erdos search --build-index --json` contaminates stdout | P2 | Fixed | e862a35 |
| BUG-003 | `erdos search` crashes when index exists but dataset missing | P2 | Fixed | e862a35 |
| BUG-004 | `iter_problems()` allows duplicate IDs (index overwrite risk) | P2 | Fixed | e862a35 |
| BUG-005 | Dead global flags: `--config`, `--no-network` | P2 | Fixed | a26d149 |

**Next Bug ID:** BUG-007

### Archived Bug Decks

- `docs/_archive/bugs/bug-001-typer-clirunner-mix-stderr.md`
- `docs/_archive/bugs/bug-002-search-build-index-json-stdout.md`
- `docs/_archive/bugs/bug-003-search-fts-loader-missing.md`
- `docs/_archive/bugs/bug-004-iter-problems-duplicate-ids.md`
- `docs/_archive/bugs/bug-005-dead-global-flags.md`

## Bug Priority Definitions

| Priority | Definition | Response Time |
|----------|------------|---------------|
| **P0** | Critical - Data loss, security vulnerability, crashes | Immediate |
| **P1** | High - Major functionality broken, blocks users | Next release |
| **P2** | Medium - Feature partially broken, workaround exists | Soon |
| **P3** | Low - Minor issues, cosmetic, edge cases | When convenient |
| **P4** | Enhancement - Nice to have, quality of life | Backlog |

## Quick Links

- [Adversarial Review 2026-01-17](./adversarial-review-2026-01-17.md)
  - 3 spec drift issues
  - 9 missing test scenarios
  - 2 inappropriate mock patterns
  - 5 bugs (3 P2, 2 P3)

## How to Add Bug Reports

1. Create a new markdown file: `bug-XXX-short-description.md` (preferred) or `bug-YYYY-MM-DD-short-description.md`
2. Use the template below
3. Link from this README

### Bug Report Template

```markdown
# Bug: [Short Title]

**Priority:** P0/P1/P2/P3/P4
**Status:** Open/In Progress/Fixed/Won't Fix
**Found:** YYYY-MM-DD
**Fixed:** YYYY-MM-DD (if applicable)
**Commit:** (fix commit hash)

## Description

Clear description of the bug.

## Steps to Reproduce

1. Step one
2. Step two
3. ...

## Expected Behavior

What should happen.

## Actual Behavior

What actually happens.

## Root Cause

Technical explanation.

## Fix

Description of the fix or link to PR.

## Related

- Related issues
- Related specs
```
