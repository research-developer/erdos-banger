# Ralph Wiggum Launch Checklist (Pre-Flight)

Use this checklist before starting an overnight autonomous run.

---

## 0) One-Time Machine Setup

- [ ] `git` installed and configured
- [ ] `gh` installed and authenticated (`gh auth status`)
- [ ] `uv` installed (`uv --version`)
- [ ] Claude Code CLI installed (`claude --version`)
- [ ] `tmux` installed (recommended for overnight runs)

---

## 1) Repo Pre-Flight (Required Every Run)

From repo root:

```bash
pwd
git status
git branch --show-current
```

- [ ] Working tree is clean (no uncommitted changes)
- [ ] You are **not** on `main` or `dev`
- [ ] `PROMPT.md` and `PROGRESS.md` exist
- [ ] Specs exist: `docs/specs/spec-010-ingest-command.md` and `docs/specs/spec-011-ask-command.md`

Sync and sanity:

```bash
git fetch origin
git rebase origin/dev
make sync-frozen
make lock-check
make ci
make smoke
```

- [ ] `make ci` passes
- [ ] `make smoke` passes

---

## 2) Safety Checks

- [ ] You understand the file boundaries in `docs/_ralphwiggum/protocol.md` (“Forbidden to change”)
- [ ] You are comfortable with the iteration cap (`MAX=50`)
- [ ] You have disk space (Lean + caches can grow)

---

## 3) Recommended Launch Command

Start a tmux session:

```bash
tmux new-session -s ralph
```

Run the loop:

```bash
MAX=50
for i in $(seq 1 $MAX); do
  echo "=== Iteration $i/$MAX ==="
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  if ! grep -q "^\\- \\[ \\]" PROGRESS.md; then
    echo "All tasks complete"
    break
  fi
  sleep 2
done
```

---

## 4) Monitoring Instructions

In another pane:

```bash
watch -n 10 'git log --oneline -10'
watch -n 10 'head -80 PROGRESS.md'
```

If the loop appears stuck:

```bash
make ci
git status
```

---

## 5) Abort Instructions

- Stop the loop: Ctrl+C (inside the tmux pane running it)
- If needed, kill tmux session: `tmux kill-session -t ralph`

Rollback options:

```bash
git status
git log --oneline -10

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Revert a specific commit (safe on shared branches)
git revert <sha>
```
