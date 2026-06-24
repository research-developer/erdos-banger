# Lean formalization (relocated)

The Lean 4 project that used to live at `formal/lean/` has moved to its own
repository: **[research-developer/erdos-lean](https://github.com/research-developer/erdos-lean)**
(split out with full history via `git subtree split`). It is cloned to
`~/.erdos/formal/lean` — the centralized Erdős data home.

## How the CLI finds it

`erdos lean …` resolves the project via `get_default_lean_project_path()`:

1. `$ERDOS_LEAN_PROJECT`, if set
2. otherwise `<data-home>/formal/lean` (default `~/.erdos/formal/lean`)

So the Lean tooling works from any directory once `~/.erdos/formal/lean`
exists (run `/erdos-setup` or `scripts/erdos_home_setup.sh` to set it up).

## Common commands

```bash
# Generate a skeleton (writes into the resolved project)
erdos lean formalize 6

# Check a file (resolved under ~/.erdos/formal/lean)
erdos lean check ~/.erdos/formal/lean/Erdos/Problem006.lean
```

## Pulling upstream Lean changes

`~/.erdos/formal/lean` has `origin` → `erdos-lean` and `upstream` → the
`erdos-banger` fork. To pull `formal/lean` changes that land upstream:

```bash
git -C ~/.erdos/formal/lean fetch upstream
# then cherry-pick / subtree-merge as appropriate
```

## CI note

Lean **build** CI lives with the Lean project (`erdos-lean`), not in this
repo. `erdos-banger`'s `requires_lean` integration tests skip cleanly when
`~/.erdos/formal/lean` is absent, and run locally for developers who have it.
