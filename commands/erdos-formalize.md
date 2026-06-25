---
description: Generate a Lean skeleton
argument-hint: "<id>"
allowed-tools: Bash(erdos:*)
---

Run the Erdős CLI and summarize the result for the user.

If `erdos` is not on PATH, tell the user to run `/erdos-setup` first, then stop.

```bash
erdos lean formalize $ARGUMENTS
```
