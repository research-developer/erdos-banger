# DEBT-010: No Smoke Test Script

**Priority:** P2
**Status:** Open
**Found:** 2026-01-18
**Affects:** Developer onboarding, installation verification, quick validation

## Problem

There's no single command to verify "does this installation work?"

A professional project would have:
```bash
make smoke  # or ./scripts/smoke-test.sh

# Expected behavior:
# 1. Load problems from fixture
# 2. Build search index
# 3. Search for "prime"
# 4. Generate Lean skeleton for problem 6
# 5. (If lean installed) Compile the skeleton
# 6. Print "All systems operational"
```

Currently, verifying the system works requires:
1. Knowing which pytest commands to run
2. Understanding which markers to use/skip
3. Manual CLI testing
4. Tribal knowledge about what "working" means

## Evidence

**No smoke test exists:**
```bash
$ ls scripts/
# (directory doesn't exist or empty)

$ make smoke
make: *** No rule to make target 'smoke'.  Stop.

$ cat Makefile | grep smoke
# (no matches)
```

**Current verification requires multiple steps:**
```bash
# A contributor would need to know:
uv sync                           # Install deps
uv run pytest                     # Run tests
uv run erdos list                 # Manual CLI check
uv run erdos search prime         # Manual search check
uv run erdos lean skeleton 6      # Manual Lean check
```

**No documented "it works" criteria:**
- README doesn't define what success looks like
- No "getting started" smoke test
- New contributors don't know if their setup is correct

## Risk

1. **Onboarding friction:** New contributors waste time debugging setup
2. **Silent breakage:** Integration could break without anyone noticing
3. **No quick validation:** Can't quickly verify after changes
4. **Missing "definition of done":** What does "it works" mean?

## Proposed Resolution

1. **Create `scripts/smoke-test.sh`:**
   ```bash
   #!/bin/bash
   set -e

   echo "=== Erdos Smoke Test ==="

   echo "[1/5] Loading problems..."
   erdos list > /dev/null

   echo "[2/5] Building search index..."
   erdos index > /dev/null

   echo "[3/5] Searching..."
   erdos search prime > /dev/null

   echo "[4/5] Generating Lean skeleton..."
   erdos lean skeleton 6 --dry-run > /dev/null

   echo "[5/5] Checking Lean (optional)..."
   if command -v lean &> /dev/null; then
       # Lean-specific checks
       echo "      Lean found, running compilation check..."
   else
       echo "      Lean not installed, skipping"
   fi

   echo ""
   echo "✓ All systems operational"
   ```

2. **Add Makefile target:**
   ```makefile
   smoke:
       ./scripts/smoke-test.sh
   ```

3. **Add to CI as final step:**
   ```yaml
   - name: Smoke test
     run: make smoke
   ```

4. **Document in README:**
   ```markdown
   ## Quick Start

   After installation, verify everything works:
   \`\`\`bash
   make smoke
   \`\`\`
   ```

## Acceptance Criteria

- [ ] `make smoke` (or equivalent) exists and works
- [ ] Smoke test covers: data loading, indexing, search, Lean generation
- [ ] Smoke test is documented in README
- [ ] CI runs smoke test after unit/integration tests
- [ ] Smoke test clearly indicates success/failure
- [ ] Smoke test completes in < 30 seconds
