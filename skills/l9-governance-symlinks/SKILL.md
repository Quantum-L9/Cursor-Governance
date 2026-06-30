---
name: l9-governance-symlinks
description: Wire and verify a repo's Cursor governance symlinks against the Dropbox governance SSOT. Runs the canonical setup_workspace_symlinks.sh in the current workspace, then runs validate_governance_symlinks.sh and confirms PASS. Use when setting up a new workspace/repo for governance, when .cursor/rules, .cursor/commands, .cursor/skills, or .cursor/governance links are missing/broken, or when the user asks to set up, repair, or validate governance symlinks.
disable-model-invocation: true
---

# L9 Governance Symlinks

Run canonical `setup_workspace_symlinks.sh` in the workspace, then run `validate_governance_symlinks.sh` and confirm PASS.

## What this does

- Wires user-level Cursor links (`~/.cursor/skills`, `~/.cursor/commands`) to the Dropbox governance SSOT.
- Wires repo-level links in the current workspace: `.cursor-commands`, `.cursor/commands`, `.cursor/rules`, `.cursor/governance`.
- Validates every link resolves to the canonical Single Source of Truth and reports `RESULT: PASS` or `RESULT: FAIL`.

The canonical scripts live under the Dropbox governance root resolved exactly like the scripts do (first match wins):

1. `$HOME/.cursor-governance/ops/scripts`
2. `$HOME/.cursor-governance/ops/scripts`

## Workflow

```
- [ ] Step 1: Resolve canonical scripts dir
- [ ] Step 2: Run setup from the workspace root
- [ ] Step 3: Validate and confirm PASS
```

### Step 1 — Resolve the canonical scripts directory

Always invoke the canonical copies from the governance SSOT (never a stale per-repo copy):

```bash
GOV_SCRIPTS=""
for p in "$HOME/Dropbox/cursor governance" "$HOME/Dropbox/Cursor Governance"; do
  if [ -d "$p/GlobalCommands/ops/scripts" ]; then
    GOV_SCRIPTS="$p/GlobalCommands/ops/scripts"
    break
  fi
done
[ -n "$GOV_SCRIPTS" ] || { echo "ERROR: governance SSOT not found under \$HOME/Dropbox"; exit 1; }
echo "Canonical scripts: $GOV_SCRIPTS"
```

### Step 2 — Run setup from the workspace root

`setup_workspace_symlinks.sh` uses `$(pwd)` as the workspace, so you MUST `cd` to the repo root you want to wire before running it. Run it from the canonical path:

```bash
cd "<workspace_root>"          # the repo to wire; default to the current workspace root
bash "$GOV_SCRIPTS/setup_workspace_symlinks.sh"
```

Notes:
- The script is idempotent: existing correct links print `OK:`, others print `LINKED: ... -> ...`.
- A non-symlink file/dir at a target path is moved aside to `<path>.backup.<timestamp>` before linking.
- It already runs validation at the end, but Step 3 below is run explicitly to confirm the final state.

### Step 3 — Validate and confirm PASS

```bash
bash "$GOV_SCRIPTS/validate_governance_symlinks.sh" "$(pwd)"
```

This is the gate. Treat the task as complete ONLY when the final line is:

```
RESULT: PASS — governance symlinks aligned
```

Confirm exit code is `0`. If you see `RESULT: FAIL`, read the `FAIL:` lines, then re-run Step 2 from the correct workspace root and validate again. Common failures:

- `missing: .../GlobalCommands/...` or `CANONICAL_LAW.md` — the Dropbox SSOT is not present/synced; do not patch links, fix the SSOT first.
- `not a symlink` / `expected X got Y` — a stale file or wrong target; re-running Step 2 repairs it.
- `missing .../skills/<l9-skill>/SKILL.md` — a required L9 skill is absent from the SSOT.

## Report

After a PASS, state: which workspace was wired, that setup ran from the canonical scripts dir, and that validation returned `RESULT: PASS`.
