# SPEC-028: v3 Research Integration Verification

> **Status:** Pending
>
> **Target:** v3.1
>
> **Resolves:** Post-v3.0 verification gap
>
> **Prerequisites:** SPEC-023, SPEC-024, SPEC-025, SPEC-026, SPEC-027 (all implemented)

---

## Summary

This spec defines acceptance criteria and test suites to verify that the v3.0 Research State Management implementation (SPEC-023 → SPEC-027) is fully integrated both **vertically** (each feature works end-to-end) and **horizontally** (features work together as a system).

---

## Scope

### In Scope

1. **Vertical integration tests** — each research command works end-to-end
2. **Horizontal integration tests** — commands compose correctly
3. **RAG integration verification** — research artifacts appear in `erdos ask` context
4. **Loop integration verification** — `erdos loop` creates attempt records
5. **Index coherence tests** — research artifacts are indexed and retrievable
6. **CLI contract tests** — all `--json` outputs match documented schemas

### Out of Scope

- Performance benchmarks (future spec)
- Multi-user collaboration scenarios
- Cross-problem knowledge graphs

---

## Verification Matrix

### 1. Workspace Commands (SPEC-023)

| Command | Vertical Test | Expected Outcome |
|---------|---------------|------------------|
| `erdos research init 6` | Creates folder structure | `research/problems/0006/` exists with meta.yaml, README.md, SCRATCHPAD.md, SYNTHESIS.md |
| `erdos research open 6` | Returns path | Outputs `research/problems/0006` |
| `erdos research note 6 "test"` | Appends to scratchpad | SCRATCHPAD.md contains timestamped entry |
| `erdos research status 6` | Shows counts | JSON output includes lead/attempt/hypothesis/task counts |

### 2. Record CRUD (SPEC-024)

| Command | Vertical Test | Expected Outcome |
|---------|---------------|------------------|
| `erdos research lead add 6 --title "..."` | Creates lead file | `leads/lead_*.yaml` exists with correct schema |
| `erdos research lead list 6` | Lists leads | JSON array of lead records |
| `erdos research lead update 6 <id> --status investigating` | Updates lead | File updated, updated_at changed |
| `erdos research hypothesis add 6 --statement "..."` | Creates hypothesis | `hypotheses/hyp_*.yaml` exists |
| `erdos research task add 6 --title "..."` | Creates task | `tasks/task_*.yaml` exists |
| `erdos research attempt log 6 --result failed --summary "..."` | Creates attempt | `attempts/att_*.yaml` exists |
| `erdos research fmt 6` | Formats YAML | All YAML files in canonical format |
| `erdos research validate 6` | Validates schemas | Exit 0 if valid, non-zero with errors |

### 3. RAG Integration (SPEC-025)

| Test | Expected Outcome |
|------|------------------|
| Index includes SYNTHESIS.md | `source_type=research_synthesis` chunks exist |
| Index includes leads | `source_type=research_lead` chunks exist |
| Index includes attempts | `source_type=research_attempt` chunks exist |
| Index includes hypotheses | `source_type=research_hypothesis` chunks exist |
| Index includes tasks | `source_type=research_task` chunks exist |
| SCRATCHPAD.md NOT indexed | No `research_scratchpad` source type |

### 4. Synthesis (SPEC-026)

| Test | Expected Outcome |
|------|------------------|
| `erdos research synthesize 6` | SYNTHESIS.md updated deterministically |
| Synthesis includes top tasks | Tasks sorted by priority appear |
| Synthesis includes active hypotheses | Active hypotheses listed |
| Synthesis includes key leads | Leads sorted by priority appear |
| Synthesis includes recent attempts | Most recent attempts listed |
| Synthesis is idempotent | Running twice produces identical output |

### 5. Loop Integration (SPEC-027)

| Test | Expected Outcome |
|------|------------------|
| `erdos loop 6 --max-iterations 1` | Creates attempt record |
| Attempt references loop log | `artifacts.loop_run_log` points to log file |
| Attempt references Lean file | `artifacts.lean_file` points to Lean source |
| Loop includes SYNTHESIS.md in context | Prompt contains synthesis content |

---

## Horizontal Integration Scenarios

### Scenario A: Full Research Workflow

```bash
# 1. Initialize workspace
erdos research init 6
# 2. Add a lead from literature
erdos research lead add 6 --title "Green-Tao theorem" --arxiv-id "math/0404188"
# 3. Form a hypothesis
erdos research hypothesis add 6 --statement "Use density argument from Green-Tao"
# 4. Add a task
erdos research task add 6 --title "Extract lemma statement"
# 5. Generate synthesis
erdos research synthesize 6
# 6. Rebuild index
erdos search --build-index
# 7. Ask with research context
erdos ask 6 "What approaches have we identified?"
# VERIFY: Response includes Green-Tao lead and hypothesis
```

### Scenario B: Loop Creates Navigable State

```bash
# 1. Initialize and populate
erdos research init 6
erdos research lead add 6 --title "Initial approach"
erdos research synthesize 6
# 2. Run loop
erdos loop 6 --max-iterations 2
# 3. Verify attempt records exist
erdos research attempt list 6
# VERIFY: Attempt records created with loop log references
```

### Scenario C: Index Coherence After Updates

```bash
# 1. Create workspace and index
erdos research init 6
erdos research lead add 6 --title "Lead A"
erdos research synthesize 6
erdos search --build-index
# 2. Verify initial state
erdos search "Lead A"  # Should find it
# 3. Update lead
erdos research lead update 6 <id> --status dead_end
erdos research synthesize 6
erdos search --build-index
# 4. Verify updated state
erdos search "dead_end"  # Should find updated lead
```

---

## Implementation

### Test Locations

```
tests/
  integration/
    research/
      test_vertical_integration.py      # Each command works
      test_horizontal_integration.py    # Commands compose
      test_rag_integration.py          # Research in ask context
      test_loop_integration.py         # Loop creates attempts
      test_index_coherence.py          # Index stays in sync
```

### Fixtures Required

- Pre-populated `research/problems/0006/` with sample data
- Sample loop log files for attempt record testing
- Sample Lean files for artifact references

### CI Integration

Add new test marker:

```python
@pytest.mark.integration_v3
```

Run with:

```bash
uv run pytest -m integration_v3
```

---

## Acceptance Criteria

1. [ ] All vertical integration tests pass
2. [ ] All horizontal integration scenarios pass
3. [ ] `erdos ask` includes research context when SYNTHESIS.md exists
4. [ ] `erdos loop` creates attempt records automatically
5. [ ] Index correctly reflects research artifact state
6. [ ] All `--json` outputs validate against documented schemas
7. [ ] No regressions in existing 992+ tests

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
