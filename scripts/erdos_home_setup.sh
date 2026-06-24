#!/usr/bin/env bash
# Idempotent bootstrap for the Erdős data home + CLI. Safe to re-run.
#
# Creates ~/.erdos (the centralized data home), installs the `erdos` CLI as a
# global uv tool, clones the relocated Lean project + upstream metadata, and
# writes ~/.erdos/.env. Override the home with $ERDOS_HOME.
#
# Note: research-developer/erdos-lean is private; cloning it requires `gh`/git
# credentials with access (the owner's machine has these).
set -euo pipefail

ERDOS_HOME="${ERDOS_HOME:-$HOME/.erdos}"
# Repo root = parent of this script's dir (scripts/ -> repo root)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAN_REPO="https://github.com/research-developer/erdos-lean.git"
ERDOS_FORK="https://github.com/research-developer/erdos-banger.git"
SUBMODULE_REPO="https://github.com/teorth/erdosproblems.git"

echo "==> data home: $ERDOS_HOME"
mkdir -p "$ERDOS_HOME"/{data,literature/manifests,index,logs,formal}

# Lean toolchain on PATH (best-effort)
[ -f "$HOME/.elan/env" ] && . "$HOME/.elan/env"

echo "==> installing erdos CLI (uv tool install --editable)"
uv tool install --editable "$REPO_ROOT" --force

# Lean project (relocated; skip if already cloned)
if [ ! -d "$ERDOS_HOME/formal/lean/.git" ]; then
  echo "==> cloning Lean project -> $ERDOS_HOME/formal/lean"
  git clone "$LEAN_REPO" "$ERDOS_HOME/formal/lean"
  git -C "$ERDOS_HOME/formal/lean" remote add upstream "$ERDOS_FORK" 2>/dev/null || true
else
  echo "==> Lean project already present (skip clone)"
fi

# Upstream metadata (plain clone, not a submodule, since we're outside a checkout)
if [ ! -d "$ERDOS_HOME/data/erdosproblems/.git" ]; then
  echo "==> cloning upstream erdosproblems metadata"
  git clone --depth 1 "$SUBMODULE_REPO" "$ERDOS_HOME/data/erdosproblems"
else
  echo "==> erdosproblems metadata already present (skip clone)"
fi

# Migrate any in-repo literature manifests (copy, never overwrite existing)
if [ -d "$REPO_ROOT/literature/manifests" ]; then
  echo "==> migrating literature manifests"
  cp -an "$REPO_ROOT/literature/manifests/." "$ERDOS_HOME/literature/manifests/" 2>/dev/null || true
fi

# .env (keys / mailto / lean project) — created once, never clobbered
ENV_FILE="$ERDOS_HOME/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "==> writing $ENV_FILE"
  cat > "$ENV_FILE" <<EOF
ERDOS_LEAN_PROJECT=$ERDOS_HOME/formal/lean
ERDOS_SUBMODULE_PATH=$ERDOS_HOME/data/erdosproblems
ERDOS_MAILTO=${ERDOS_MAILTO:-erdos-banger@example.com}
EOF
else
  echo "==> $ENV_FILE already exists (leaving as-is)"
fi

cat <<EOF

✔ erdos home ready at $ERDOS_HOME
  Add to your shell profile (~/.zshrc) so 'erdos' resolves the data home everywhere:
    export ERDOS_HOME="$ERDOS_HOME"
    [ -f "\$HOME/.elan/env" ] && . "\$HOME/.elan/env"
  Then run:  erdos list --limit 1
EOF
