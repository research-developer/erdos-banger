# SPEC-034: Progress Dashboard

> **Status:** Pending
>
> **Target:** v4.1
>
> **Resolves:** No visualization of proof attempts and research state
>
> **Prerequisites:** SPEC-028 (v3 verification)

---

## Summary

Provide a **terminal-based dashboard** for visualizing:
- Proof attempt history and outcomes
- Research state across problems
- Loop iteration progress
- Lead/hypothesis/task status

---

## Motivation

**Current state:**
- `erdos logs` shows raw run entries
- `erdos research status` shows counts for one problem
- No aggregate view across problems or over time

**Gap:** Hard to answer:
- "Which problems have I worked on recently?"
- "What's the success rate of my loop attempts?"
- "Where did my last proof attempt get stuck?"

---

## Scope

### In Scope

1. **CLI dashboard** — Rich-based terminal UI
2. **Problem overview** — All problems with research state
3. **Attempt timeline** — History of proof attempts
4. **Research summary** — Leads/hypotheses/tasks across problems

### Out of Scope

- Web UI (terminal only for v4.1)
- Real-time streaming (static snapshots)
- Export to HTML/PDF

---

## CLI Interface

### Main Dashboard

```bash
erdos dashboard [OPTIONS]

# Examples:
erdos dashboard                    # Interactive dashboard
erdos dashboard --problems 6,42    # Filter to specific problems
erdos dashboard --recent 7d        # Last 7 days only
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--problems` | all | Comma-separated problem IDs |
| `--recent` | 30d | Time window (7d, 30d, 90d, all) |
| `--refresh` | 5 | Auto-refresh interval (seconds, 0 to disable) |

**JSON mode (`erdos --json dashboard ...`):**

- Must **not** enter an interactive UI loop.
- Must output a single `CLIOutput` envelope whose `data` is a deterministic snapshot of aggregated dashboard data (suitable for tests and tooling).

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ERDŐS-BANGER DASHBOARD                               │
│                         Last updated: 2026-01-23 12:00                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROBLEM OVERVIEW (5 active)                                                │
│  ┌────────┬──────────┬───────┬─────────┬──────────┬───────────────────────┐ │
│  │ ID     │ Status   │ Leads │ Attempts│ Success  │ Last Activity         │ │
│  ├────────┼──────────┼───────┼─────────┼──────────┼───────────────────────┤ │
│  │ 6      │ active   │ 3     │ 12      │ 0%       │ 2026-01-23 11:45      │ │
│  │ 42     │ active   │ 5     │ 8       │ 12.5%    │ 2026-01-22 16:30      │ │
│  │ 124    │ active   │ 2     │ 3       │ 33%      │ 2026-01-21 09:00      │ │
│  │ 256    │ stale    │ 1     │ 0       │ —        │ 2026-01-15 14:20      │ │
│  │ 512    │ new      │ 0     │ 0       │ —        │ 2026-01-23 10:00      │ │
│  └────────┴──────────┴───────┴─────────┴──────────┴───────────────────────┘ │
│                                                                             │
│  RECENT ATTEMPTS (last 7 days)                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ▓▓▓▓░░▓▓░░▓▓▓░░░▓▓▓▓░░░░▓▓░░▓                                       │   │
│  │ Mon   Tue   Wed   Thu   Fri   Sat   Sun                              │   │
│  │ ▓ = attempt (green=success, red=failed, yellow=partial)              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGGREGATE STATS                                                            │
│  ├── Total attempts: 23                                                     │
│  ├── Success rate: 8.7% (2/23)                                              │
│  ├── Active leads: 11                                                       │
│  ├── Active hypotheses: 4                                                   │
│  └── Open tasks: 7                                                          │
│                                                                             │
│  [q] Quit  [r] Refresh  [p] Problem detail  [a] Attempt detail              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Problem Detail View

```bash
erdos dashboard --problem 6
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROBLEM 6: Sum-Free Sets                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SYNTHESIS (last updated: 2026-01-23)                                       │
│  ├── Summary: Investigating density bounds via Green-Tao methods            │
│  ├── Key insight: Reduction to abelian group structure                      │
│  └── Blocker: Lemma X induction hypothesis too weak                         │
│                                                                             │
│  LEADS (3)                                     HYPOTHESES (2)               │
│  ├── [HIGH] Green-Tao theorem (investigating)  ├── [ACTIVE] Use density     │
│  ├── [MED]  Eberhard 2016 (new)                │   argument from Green-Tao  │
│  └── [LOW]  Alon 2002 (dead_end)               └── [ACTIVE] Reduce to       │
│                                                    abelian group            │
│  TASKS (3)                                                                  │
│  ├── [TODO] Extract exact lemma statement                                   │
│  ├── [DOING] Review Mathlib Finset lemmas                                   │
│  └── [BLOCKED] Formalize main theorem (blocked on lemma)                    │
│                                                                             │
│  ATTEMPT HISTORY (12 total)                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ #12 [FAILED]  2026-01-23 11:45  "Stuck on lemma X induction"        │    │
│  │ #11 [FAILED]  2026-01-23 10:30  "Type mismatch in step 3"           │    │
│  │ #10 [PARTIAL] 2026-01-22 16:00  "Proved lemma Y, main stuck"        │    │
│  │ ...                                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  [b] Back  [s] Show synthesis  [l] Show leads  [a] Show attempt #           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

### Module Structure

```
src/erdos/
  commands/
    dashboard.py        # CLI entry point
  core/
    dashboard/
      __init__.py
      data.py           # Data aggregation
      render.py         # Rich rendering
      widgets.py        # Reusable UI components
```

### Data Aggregation

```python
# src/erdos/core/dashboard/data.py

from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ProblemStats:
    problem_id: int
    status: str  # new, active, stale
    lead_count: int
    hypothesis_count: int
    task_count: int
    attempt_count: int
    success_count: int
    last_activity: datetime | None

@dataclass
class DashboardData:
    problems: list[ProblemStats]
    total_attempts: int
    total_successes: int
    active_leads: int
    active_hypotheses: int
    open_tasks: int
    attempt_timeline: dict[str, list[str]]  # date -> list of results

def aggregate_dashboard_data(
    research_path: Path,
    logs_path: Path,
    recent: timedelta = timedelta(days=30),
) -> DashboardData:
    """Aggregate data for dashboard display."""
    ...
```

**Primary data sources (SSOT):**

- Research workspace (canonical): `research/problems/<id>/`
  - `attempts/att_*.yaml` for attempt timeline + success rate
  - `leads/*.yaml`, `hypotheses/*.yaml`, `tasks/*.yaml` for counts
- Run logs (derived): `logs/runs.jsonl` (optional)
  - used only for “recent activity” views when present; dashboard must still work without it

### Rich Rendering

```python
# src/erdos/core/dashboard/render.py

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

def render_dashboard(data: DashboardData, console: Console) -> None:
    """Render full dashboard to console."""
    ...

def render_problem_detail(
    problem_id: int,
    data: DashboardData,
    console: Console,
) -> None:
    """Render problem detail view."""
    ...
```

---

## Acceptance Criteria

1. [ ] `erdos dashboard` displays problem overview table
2. [ ] Attempt timeline shows activity heatmap
3. [ ] Aggregate stats calculated correctly
4. [ ] `--problem` shows detailed view
5. [ ] `--recent` filters by time window
6. [ ] Auto-refresh works (--refresh)
7. [ ] Keyboard navigation (q, r, p, a)
8. [ ] Works without research workspace (shows empty state)
9. [ ] `erdos --json dashboard` emits a single snapshot (no interactive loop)
10. [ ] Unit tests for data aggregation

---

## References

- [Rich Live Display](https://rich.readthedocs.io/en/latest/live.html)
- [Rich Tables](https://rich.readthedocs.io/en/latest/tables.html)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
