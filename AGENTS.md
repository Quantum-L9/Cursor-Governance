# AGENTS.md — L9 Governance (Cursor-Governance)

Operating rules for any agent working **in** this repository, and the activation
contract for any agent working **in a repo that consumes** this repository.

Read this file before touching activation, hooks, or symlink wiring.

---

## 1. Mission of this repo

`Cursor-Governance` is the single source of truth for L9/Quantum-L9 agent
governance: rules, skills, slash commands, learning corpus, and the automation
that wires all of it into every coding workspace.

This repo owns:

- the governance content itself (`rules/`, `skills/`, `commands/`, `learning/`)
- the symlink/wiring contract (`CANONICAL_LAW.md`)
- the session activation hooks (`ops/hooks/`)
- the Graphiti memory client and activation runbooks (`ops/graphiti/`)

This repo does **not** own:

- repo-specific rules (those live in the consumer repo's `.cursor/rules/`)
- app/product code of any kind

---

## 2. Activation — how a session boots L9 governance

**There is exactly one activation mechanism, and it is automatic.**

### 2.1 Automatic (every session, no action needed)

`ops/hooks/session_start_bootstrap.sh` is installed as a real file at
`~/.cursor/hooks/session-start-bootstrap.sh` and registered in
`~/.cursor/hooks.json` under `sessionStart` (30s timeout). It runs on every
Cursor session start with no manual step:

1. Backgrounds `governance_sync.sh` — **bidirectional** reconcile of this clone
   against `origin/main`: fast-forward-only pull (never destroys local edits,
   never hard-resets), then a push via `backup_to_github.sh` so local work is
   backed up at session start too, not only on a clean session end. Set
   `GOVERNANCE_SYNC_PUSH=0` to make it pull-only.
2. Backgrounds `setup_claude_code_plugins.sh --quiet` — reconciles the
   declared Claude Code plugin set (user-scope under `~/.claude/`) so every
   governed workspace inherits the same plugins
3. Auto-wires `.cursor-commands` + `~/.cursor/{skills,commands,rules}`
   symlinks in the active workspace if any are missing
4. Backgrounds `install_ide_profile.sh --quiet` — reconciles the IDE profile
   declared in `environment/ide/` (extensions machine-wide, managed-key merge
   into the workspace's `.vscode/settings.json`)
5. Loads Graphiti env, scaffolds `memory-bank/` in the active workspace
6. Ensures the Graphiti SSH tunnel, then runs a health check
7. Reads a `memory-bank/activeContext.md` excerpt (T0 resume context)
8. Runs `check_governance_wiring.sh` and reports PASS/FAIL
9. Delegates to `ops/hooks/session_start_memory_orchestrator.sh` for
   code-graph health (PlasticOS repos) + Graphiti `inject "session start"`
   prefetch
10. Emits one combined `additional_context` JSON blob back to Cursor

### 2.2 Manual / on-demand commands

To re-run the **entire** sequence above against the current repo — same script,
synchronously, with output on your terminal instead of in a JSON payload:

```bash
make -C "$HOME/.cursor-governance" start WS="$(pwd)"
```

Consumer repos may add a two-line delegating `start` target so plain `make start`
works from inside the repo.

Run these directly if you need to re-check or repair only one piece mid-session:

```bash
bash "$HOME/.cursor-governance/ops/scripts/governance_sync.sh"
bash "$HOME/.cursor-governance/ops/scripts/check_governance_wiring.sh" "$(pwd)"
bash "$HOME/.cursor-governance/ops/scripts/setup_workspace_symlinks.sh"      # run from inside the consumer workspace, not from ~/.cursor-governance itself
bash "$HOME/.cursor-governance/ops/scripts/validate_governance_symlinks.sh"
bash "$HOME/.cursor-governance/ops/scripts/setup_claude_code_plugins.sh"     # reconcile Claude Code plugins (or --quiet)
bash "$HOME/.cursor-governance/ops/scripts/install_ide_profile.sh" "$(pwd)"  # reconcile IDE profile (--dry-run to preview)
python3 "$HOME/.cursor-governance/ops/graphiti/graphiti_memory_client.py" health
```

**Caution:** `setup_workspace_symlinks.sh` and `validate_governance_symlinks.sh`
resolve the workspace as `$(pwd)` — always `cd` into the consumer repo first.
Running them from inside `~/.cursor-governance` self-wires the SSOT clone as
if it were a consumer (harmless, but pointless; `.cursor-commands` and
`.cursor/` are gitignored here for exactly this reason).

### 2.3 Graphiti caveat

The learning system is designed to feed into Graphiti, but that pipeline is
**not fully built out or connected yet**. Expect the health check to report
`"graphiti: tunnel up (MCP tools degraded ...)"` — that is an accurate,
expected degraded state, not a wiring bug. Everything else in the activation
chain (symlinks, wiring check, memory-bank read) is unaffected and should
report PASS.

### 2.4 Retired: `start-session.yaml`

A 917-line declarative YAML protocol of the same name previously existed at
the repo root. It was **deleted (2026-07-19)** — it was never wired into any
hook (Cursor doesn't execute YAML), and it had drifted from the pre-Graphiti
learning pipeline archived in `ops/scripts/_archived/`. Do not recreate a
YAML "protocol" file; the `.sh` hook above is the canonical activation
mechanism. If you need a human-readable narrative of what activation does,
this section is that narrative — keep it in sync with the hook, not a
separate spec file.

---

## 3. Source-of-truth files

- `CANONICAL_LAW.md` — symlink law, memory layer, anti-patterns (authoritative)
- `README.md` — directory structure and key-file index
- `ops/hooks/session_start_bootstrap.sh` — activation entry point (§2.1)
- `ops/scripts/resolve_governance_paths.sh` — path resolution (GitHub clone only, no Dropbox fallback)
- `ORG_INVARIANTS.yaml` — canonical Quantum-L9 org policy

Agents must keep code and these docs aligned — see `TODO.md` for known drift
not yet reconciled.

---

## 4. Symlink law (summary — `CANONICAL_LAW.md` §1-3 is authoritative)

| Workspace path | Target |
|---|---|
| `.cursor-commands` | `~/.cursor-governance/` (sole entry, every consumer repo) |
| `.cursor/governance/CANONICAL_LAW.md` | file symlink to the law file only |
| `.cursor/governance/` | local directory, **never** a symlink to the governance root |
| `~/.cursor/skills`, `~/.cursor/commands` | `~/.cursor-governance/skills/`, `~/.cursor-governance/commands/` |

Forbidden: a second governance tree in any repo, `.cursor/commands` or
`.cursor/skills` duplicating `.cursor-commands/*`, hard-reset/force-push of
this clone.

---

## 5. Change policy

### 5.1 Allowed
Bug fixes, dangling-reference repair, test/doc additions, new skills via
`l9-skill-compiler` → `l9-wire-skill-into-repo`.

### 5.2 High-risk — extreme care
Changes to `CANONICAL_LAW.md`, `resolve_governance_paths.sh`,
`backup_to_github.sh`, `ops/hooks/session_start_bootstrap.sh`, or anything in
`ops/scripts/_archived/` (archived = intentionally retired, not missing —
verify the archival rationale in git history before restoring anything).

### 5.3 Forbidden
- Reintroducing Dropbox as an SSOT fallback in any resolver script
- Restoring archived pre-Graphiti daemons without confirming they're not
  superseded (check `git log` for the archiving commit's stated rationale
  first)
- A new YAML/manual "protocol" file duplicating the `.sh` hook's job

---

## 6. Validation workflow before merge

```bash
bash ops/scripts/check_governance_wiring.sh "$(pwd)"
bash ops/scripts/validate_governance_symlinks.sh
bash ops/scripts/validate_governance_no_hardcoded_paths.sh
python3 ops/graphiti/graphiti_memory_client.py health   # degraded Graphiti is expected, not a failure
```

---

## 7. Guidance for AI coding agents

- Before restoring anything from `ops/scripts/_archived/`, run
  `git log --oneline -- ops/scripts/_archived/<file>` and read the archiving
  commit's PR description. "Nothing references it" is not sufficient
  justification to restore it, and archival is not sufficient justification
  to assume it's safe to delete permanently either — check intent both ways.
- Prefer fixing the stale artifact over restoring the retired one. When a
  verification script fails because it checks a pre-archive path, the script
  is usually the thing that's stale, not the archive.
- This repo reconciles with `origin/main` in **both directions at session start**
  (`governance_sync.sh`: ff-only pull, then push via `backup_to_github.sh`) and
  pushes again at session end (`backup_to_github.sh` via the `sessionEnd` hook).
  Both directions are commit-preserving: the pull is fast-forward-only, the push
  rebases and aborts rather than committing over a conflict. Never hand-edit
  files in a way that assumes a different sync model.
- The session-end push is gated by `ops/scripts/backup_gate.sh`, because
  `sessionEnd` fires once per composer conversation (aborted chats and window
  closes included) and would otherwise commit a tree an agent is still writing.
  If a backup you expected did not happen, read `backup.log` — every skip is
  logged with its reason. Do not weaken the gate to force a backup through; run
  `make backup` (ungated) or set `GOVERNANCE_BACKUP_FORCE=1`.

---

## 8. Final principle

This repo is the governance boundary for every L9/Quantum-L9 coding workspace.
Activation must stay boring and automatic — one hook, one clone, one symlink
per consumer repo. Optimize for that staying true; do not add a second
activation path, however convenient it seems in the moment.
