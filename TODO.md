# GlobalCommands — Tech Debt (cleanup later)

Context: `tests/`, `templates/`, and `startup/` were deleted (superseded by v6 L9 skills, `.cursor/rules/*.mdc`, `AGENTS.md`, and active wiring scripts). `start-session.yaml` was deleted (2026-07-19) — it was never wired into any hook and had drifted from the archived pre-Graphiti learning pipeline. `ops/hooks/session_start_bootstrap.sh` is the real, live activation script: installed at `~/.cursor/hooks/session-start-bootstrap.sh`, registered in `~/.cursor/hooks.json` under `sessionStart`, runs automatically every session.

## Dangling references (broken if invoked)

- [x] **`ops/scripts/operational-oversight.py`** — fixed (2026-07-19): dangling refs to
  `startup/REASONING_STACK.yaml` and `verify-startup-files.sh` repaired. **Keep, still needs a
  second pass:** its optional `governance_monitor` import (line 59) now points at an archived
  module (`execution-governance/_archived/monitoring/governance-monitor.py`) — already
  soft-fails via `try/except ImportError` so it's not broken, but the fallback message is stale.
- [ ] **`ops/scripts/verify-startup-files.sh`** — checks deleted `startup/*` files
- [ ] **`ops/scripts/README_STARTUP_VERIFICATION.md`** — documents deleted startup verification flow
- [ ] **`ops/scripts/deploy_cursorrules_global.sh`** — deploys deleted `.cursorrules` template
- [ ] **`intelligence/reasoning/reasoning-snapshot-generator.py`** — **KEEP, needs fix** (per
  explicit decision 2026-07-19, not archived like its `intelligence/learning/*` siblings).
  Writes signatures to `foundation/security/_archived/signatures/` — an already-archived
  location predating this session. Needs investigation: either re-point at a live signature
  store, or confirm archived-signatures-as-read-only-ledger is the intended design.
- [ ] **`ops/feedback_loop_config.yaml`** — `feedback_collector.script` points at
  `.cursor-commands/ops/scripts/feedback_collector.py`, which never existed there (the real
  file, now archived, lived at `intelligence/learning/feedback_collector.py`). Pre-existing
  dangling path, not caused by this session's archiving.

## Rules / docs that mention deleted assets

- [ ] **`rules/25-python-dora-header.mdc`** — references deleted `python-header-template.py`
- [ ] **`profiles/session-startup-protocol.md`** — Suite-6 startup protocol; may reference deleted startup stack
- [x] **`intelligence/workspace/setup-new-workspace.py`** — **archived** (2026-07-19) to
  `intelligence/_archived/workspace/`. Still the only implementation of the workspace-setup
  flow, but called deleted `startup/*` files and the broken `process_learnings.sh` pipeline.
- [x] **`intelligence/workspace/setup-new-workspace.md`** — **archived** (2026-07-19) alongside
  its `.py`; was a 1000+ line Suite-6 doc (`.suite6-config.json`, hardcoded Dropbox paths,
  `verify-startup-files.sh` expectations). `SETUP_QUICK_START.md` rewritten to point at
  `AGENTS.md` + `ops/hooks/session_start_bootstrap.sh` instead.
- [x] **`execution-governance/README.md`** — **archived** (2026-07-19) to
  `execution-governance/_archived/README.md` along with the rest of `execution-governance/`
  (all 5 `.py` implementations were confirmed Suite-6 legacy — see CHANGELOG `[Unreleased]`).
- [ ] **`README.md`** (GlobalCommands root) — startup/templates references
- [ ] **`C_GOV_FILES/`** duplicates — `session-startup-protocol.md`, `setup-new-workspace.md`, `setup-new-workspace.py`, `cursor-native-reasoning.md`
- [ ] **`workflows/Dags-Harvest/DAG-Harvest-5.md`** — startup references (verify)
- [ ] **`commands/dora-commands/do-README.md`** — points at the now-archived
  `commands/_archived/do-templates/` (2026-07-19); still describes the `/do-*` scaffold
  commands (`do-init.md`, `do-status.md`, etc.) which were left untouched — verify whether
  those slash commands are still wired to anything before deciding their fate.
- [ ] **`ops/scripts/_archived/migrate_to_project_rules.py`** — archived; low priority
- [ ] **`intelligence/reasoning/cursor-native-reasoning.md`** — verify overlap with `l9-structured-reasoning` before edit/delete
- [ ] **`integrity/hash-verifier.py`** — investigated 2026-07-19, confirmed **ACTIVE, keep**:
  `manifest-lock.json` is a live present artifact, `system-check.sh` calls it, and git history
  shows deliberate Suite-6→L9 rebrand carry-forward (not left to rot). Distinct standalone
  concern from the deprecated memory/learning stack.

## Ruff debt (77 pre-existing errors, tracked 2026-07-19)

`make push` bypassed with `--no-verify` on 2026-07-19 by explicit user approval — none of
these are new (all pre-date this session's archiving/dependency work). Split by severity:

**Real correctness issues (fix first, ~9 total):**
- [ ] F401 unused import — 4 occurrences
- [ ] F841 unused variable — 1 occurrence
- [ ] E722 bare `except:` — 4 occurrences

**Pure style (~68 total, lower priority):**
- [ ] E501 line too long — 51 occurrences
- [ ] E402 import not at top of file — 13 occurrences
- [ ] E741 ambiguous variable name (`l`) — 2 occurrences (known instance: `workflows/wire_executor.py:445`)
- [ ] P022 — 2 occurrences

Heaviest files: `workflows/gmp_executor.py` (12), `ops/scripts/operational-oversight.py` (11),
`workflows/harvest_executor.py` (6), `workflows/runner.py` (5), `workflows/__init__.py` (5).
Run `ruff check .` from repo root for the full current list.

## Already superseded (do not restore)

| Deleted | Replaced by |
|---------|-------------|
| `startup/REASONING_STACK.yaml` | `skills/l9-structured-reasoning/` |
| `startup/init_workspace.py` symlink logic | `ops/scripts/setup_workspace_symlinks.sh`, `check_governance_wiring.sh`, `wire_governance_workspace.sh` |
| `templates/.cursorrules` | `.cursor/rules/*.mdc` + `AGENTS.md` |
| `templates/python-header-template*.py` | `l9-skill-compiler` `meta-standard.md` (lean frontmatter) |
| `tests/test_imports.py` | `l9-wire-skill-into-repo` validation |

## Publish note

Changes live in the SSOT (`$HOME/.cursor-governance`). Backup via `sessionEnd` hook or `make governance-backup` — not from IB-Odoo_19.
