#!/usr/bin/env bash
# Default LLM wrapper entrypoint for erdos.
# Delegates to a concrete provider script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

load_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    local key="${line%%=*}"
    local value="${line#*=}"

    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    value="${value%%#*}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    if [[ "$value" =~ ^\".*\"$ ]]; then
      value="${value:1:-1}"
    elif [[ "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:-1}"
    fi

    export "${key}=${value}"
  done < "$env_file"
}

load_env_file "${REPO_ROOT}/.env"

provider="${ERDOS_LLM_PROVIDER:-}"
if [[ -z "$provider" ]]; then
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    provider="openai"
  elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    provider="anthropic"
  else
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
