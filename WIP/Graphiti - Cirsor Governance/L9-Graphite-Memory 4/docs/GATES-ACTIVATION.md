<!-- L9_META
l9_schema: 1
parent: l9-graphite-memory
layer: docs
role: runbook
tags: [gates, activation, hooks, rules]
owner: platform
status: active
version: 2.0.0
updated: 2026-07-05
/L9_META -->

# Gate Activation Guide

This document describes how to activate memory gates in a target repository.

## What Are Gates?

Gates are IDE-level intercept hooks that enforce memory discipline. When active:

- **Pre-tool-use gate**: Checks if the agent has loaded relevant memory before using tools
- **GMP phase-lock gate**: Ensures conflict checks pass before granting phase lock
- **Shell-commit gate**: Validates that decisions are written to memory before committing
- **Subagent gate**: Ensures sub-agents inherit memory context

## Activation

### One-Command Activation

```bash
bash scripts/activate_gate.sh /path/to/target-repo
```

This installs:
1. `graphiti-*.sh` hooks into `.cursor/hooks/`
2. `.mdc` rules into `.cursor/rules/`
3. Registers the repo in `config/group_registry.yaml`
4. Runs autoseed-check to verify graph connectivity

### Hooks-Only Mode

If you only want hooks without registry changes:

```bash
bash scripts/activate_gate.sh /path/to/target-repo --hooks-only
```

### Dry Run

Preview what would be installed:

```bash
bash scripts/activate_gate.sh /path/to/target-repo --dry-run
```

## Enabling Write Gates

Write gates are disabled by default. To enable:

```bash
export GRAPHITI_WRITE_GATES=1
```

When enabled, the gate library (`graphiti_gate_lib.py`) will enforce that:
- Episodes are written before phase transitions
- Decisions are captured before commits
- Bootstrap has run before first memory access

## Verification

After activation, verify the gate is wired:

```bash
# Check hooks are in place
ls /path/to/target-repo/.cursor/hooks/graphiti-*.sh

# Check rules are in place
ls /path/to/target-repo/.cursor/rules/*.mdc

# Run health check from the target repo
cd /path/to/target-repo
l9-memory health
```

## Soak Period

After activation, run with `GRAPHITI_WRITE_GATES=0` (read-only) for 24-48 hours to verify:
1. Health checks pass consistently
2. Search returns relevant results
3. No rate limiting or circuit breaker trips

Then enable write gates: `export GRAPHITI_WRITE_GATES=1`

## Deactivation

To remove gates from a repo:

```bash
rm /path/to/target-repo/.cursor/hooks/graphiti-*.sh
rm /path/to/target-repo/.cursor/rules/graphiti-*.mdc
```
