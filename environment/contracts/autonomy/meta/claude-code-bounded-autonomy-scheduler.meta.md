<!-- L9_META
l9_schema: 1
artifact_id: claude-code-bounded-autonomy-scheduler
first_class_artifact: true
schema_family: l9_autonomy_architecture
version: 1.0.0
status: active
updated: 2026-08-12
owner: platform
layer: adapter
tags: [l9, autonomy, first_class, claude-code, e14]
/L9_META -->

# Claude Code bounded-autonomy scheduler — metadata

**SSOT path:** `environment/agents/adapters/claude-code/autonomy/`  
**E14 exemption:** true (not a forbidden copy of root `autonomy/`)

## Purpose

Claude-owned bounded-concurrency scheduler (action graph, worktrees, join).
Cursor maps the same invariants via `l9-bounded-autonomy` Tasks — does not
reimplement this Python runtime.

## Not for

- Citing `environment/claude-code/autonomy/` as a live path (symlink extinguished)
- Cursor reimplementation of the scheduler under a second home
