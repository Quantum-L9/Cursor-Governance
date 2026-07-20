---
component_id: "INT-WS-002"
component_name: "Workspace Setup Quick Start Guide"
layer: "intelligence"
domain: "workspace_management"
type: "documentation"
status: "active"
updated: "2026-07-19"
author: "Igor Beylin"
maintainer: "Igor Beylin"
purpose: "Point at the current L9 Governance activation mechanism"
summary: "One-command workspace wiring via the real sessionStart hook, not the archived Suite-6 setup script"
---

# L9 Governance Workspace Setup — Quick Start

**The full activation contract lives in [`AGENTS.md`](../../AGENTS.md) at the repo root. Read that
first — this file is a short pointer, not a duplicate.**

`setup-new-workspace.py` (Suite-6, v6/v7) is archived at
[`intelligence/_archived/workspace/`](../_archived/workspace/). It described a `.suite6-config.json`
+ hardcoded-Dropbox-path setup flow that predates the GitHub-SSOT, Graphiti-native governance model.
Do not follow its instructions.

## Automatic activation (already wired, nothing to run manually)

Every Cursor session in a workspace with `.cursor/hooks.json` configured runs
`ops/hooks/session_start_bootstrap.sh` automatically at session start. It:

1. Fast-forward syncs this clone from `origin/main` (`ops/scripts/governance_sync.sh`)
2. Wires `.cursor-commands` + `~/.cursor/{skills,commands,rules}` symlinks
3. Checks Graphiti tunnel/MCP health (degraded is expected pre-full-wiring)

## First-time wiring for a NEW consumer workspace

From inside the **consumer** repo (not `~/.cursor-governance` itself):

```bash
cd /path/to/your/workspace
bash ~/.cursor-governance/ops/scripts/setup_workspace_symlinks.sh
```

This creates the `.cursor-commands` symlink to `~/.cursor-governance`. It is intentionally
**not** committed — see `.gitignore`.

## Verify wiring health

```bash
cd ~/.cursor-governance
make wiring-check WS=/path/to/your/workspace   # check a consumer repo
make symlinks-check                             # check this clone's own symlinks
make path-lint                                  # fail if any script hardcodes /Users or /home
make graphiti-health                            # Graphiti tunnel + MCP tool-plane
```

## Troubleshooting

| Issue | Fix |
|---|---|
| `.cursor-commands` missing or points at the wrong place | Re-run `setup_workspace_symlinks.sh` from the consumer repo |
| Graphiti MCP degraded | Expected pre-full-wiring — see `AGENTS.md` §Activation |
| Anything mentions `.suite6-config.json`, `process_learnings.sh`, or a Dropbox path | Stale Suite-6 reference — ignore, file an issue instead of following it |
