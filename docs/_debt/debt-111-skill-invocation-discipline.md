# DEBT-111: Skill Invocation Discipline

**Created:** 2026-01-26
**Priority:** P3
**Type:** Process/Workflow

## Problem

During the 2026-01-26 session, Claude Code failed to invoke the `/erdos` skill before attempting to use the CLI. This led to:

1. Filing a false positive bug (BUG-041 - "Exa not exposed in CLI")
2. Wasting time searching for features that were documented
3. User frustration ("Jesus Christ, if it does work...")

The skill at `.claude/skills/erdos/SKILL.md` clearly documents:
- Line 51: `erdos research exa search` is listed
- Lines 196-197: Shows exact usage example
- Line 220: Documents the known gap (Issue #34)

## Root Cause

Claude Code didn't follow the recommended workflow:
1. **Should have:** `/erdos` (invoke skill) → read docs → execute correctly
2. **Actually did:** Tried things blindly → filed bug → found it later

## Recommended Workflow

When working with erdos CLI:

```
1. FIRST: Invoke /erdos skill to load full CLI reference
2. Check the skill for the exact command syntax
3. Only then attempt to run the command
4. If still confused, check --help
```

## Not a Code Issue

This is a **process/discipline** issue, not a code bug. The skill documentation is comprehensive and accurate.

## Action Items

- [ ] Add CLAUDE.md reminder about invoking skills first
- [ ] Consider auto-invoking `/erdos` skill when CLI errors occur
- [ ] Add "did you invoke /erdos?" to troubleshooting checklist
