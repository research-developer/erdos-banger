#!/usr/bin/env bash
# Default LLM wrapper entrypoint for erdos.
# Delegates to a concrete provider script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=lib/load-env.sh
source "${SCRIPT_DIR}/lib/load-env.sh"
load_env_file "${REPO_ROOT}/.env"

provider="${ERDOS_LLM_PROVIDER:-}"
if [[ -z "$provider" ]]; then
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    provider="openai"
  elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    provider="anthropic"
  else
    echo "Warning: No API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env" >&2
    provider="openai"
  fi
fi

case "$provider" in
  openai)
    exec "${SCRIPT_DIR}/llm-openai.sh"
    ;;
  anthropic)
    exec "${SCRIPT_DIR}/llm-anthropic.sh"
    ;;
  *)
    echo "Unknown ERDOS_LLM_PROVIDER=${provider} (expected: openai|anthropic)" >&2
    exit 2
    ;;
esac
