# Bug Reports & Adversarial Reviews

This directory contains bug reports, adversarial code reviews, and quality audits for the erdos-banger project.

## Reviews

| Date | Type | Summary | Status |
|------|------|---------|--------|
| 2026-01-17 | Adversarial Review | Full codebase audit covering specs 003-006 | Active |

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

1. Create a new markdown file: `bug-YYYY-MM-DD-short-description.md`
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
