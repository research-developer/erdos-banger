# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-23
**Status:** Ready - Research v3 shipped, awaiting senior review
**Branch:** ralph-wiggum-debt-067
**Purpose:** State file for Ralph Wiggum loop (see `docs/_ralphwiggum/protocol.md`)

---

## Operating Rules (SSOT)

1. **One task per iteration** (never batch)
2. **TDD required**: add a failing test before production code for behavior changes
3. **No reward hacks**
   - never delete/disable tests to "make CI green"
   - never mock the unit under test (mock boundaries only: network/subprocess/time)
   - never lower quality gates (coverage/lint/mypy)
4. **Checkpoint discipline**
   - commit after each completed task
   - push after each commit (remote is the backup)
5. **Escalate early** (stop and request human review) if:
   - a spec/deck contradicts SSOT / code reality
   - the change exceeds ~500 LOC or >10 files for a single task (split into subtasks)
   - quality gates fail after 3 fix attempts for the same root cause

---

## Active Queue

Work strictly top-to-bottom unless blocked by dependencies.

*No unchecked items. Add `- [ ]` tasks here to start an overnight run.*

---

## Backlog (Needs Human Approval; not active)

Ideas for SPEC-028+ (do not convert to checkboxes without explicit approval):

- Index literature extracts into the SQLite search DB (chunking + citations)
- Expose `erdos research` operations via MCP server tools
- Expand smoke test to include research workspace commands

---

## Work Log (2026-01-23)

- Research v3 implemented (workspace + records + synthesis + indexing + loop integration) and hardened for SSOT/senior review.
- CI/code-health fixes: split oversized `erdos research` command module into a package; reduced `execute_proof_loop()` below audit threshold.
- Test isolation: loop CLI tests now set `ERDOS_REPO_ROOT` to avoid polluting the repo with generated `research/` artifacts.
