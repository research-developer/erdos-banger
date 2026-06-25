---
description: One-time setup — create ~/.erdos, install the erdos CLI, clone the Lean project, write ~/.erdos/.env
argument-hint: ""
allowed-tools: Bash(bash:*), Bash(erdos:*)
---

Bootstrap the Erdős data home and CLI. Run the setup script (idempotent — safe to re-run), then report what it did and any next steps it prints (e.g. shell-profile lines to add).

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/erdos_home_setup.sh"
```

After it completes, verify with `erdos --version` and `erdos list --limit 1`.
