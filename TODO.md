# GlobalCommands — Tech Debt (cleanup later)

Context: `tests/`, `templates/`, and `startup/` were deleted (superseded by v6 L9 skills, `.cursor/rules/*.mdc`, `AGENTS.md`, and active wiring scripts). `start-session.yaml` kept for realignment.

## Priority — realign session startup

- [ ] **`start-session.yaml`** — Remove/replace references to deleted paths:
  - `templates/.cursorrules`
  - `startup/REASONING_STACK.yaml`
  - `startup/system_capabilities.md`
  - Other dead steps: `startup/probabilistic_governance_activated.md`, `startup/production_speed_pack.md`, `launchctl com.tenx.*`
  - Align to v6 model: governance-wiring gate → skills (`l9-structured-reasoning`, etc.) → `.cursor/rules/*.mdc` → `AGENTS.md`

## Dangling references (broken if invoked)

- [ ] **`ops/scripts/operational-oversight.py`** — imports `startup.session_startup` (ImportError if run)
- [ ] **`ops/scripts/verify-startup-files.sh`** — checks deleted `startup/*` files
- [ ] **`ops/scripts/README_STARTUP_VERIFICATION.md`** — documents deleted startup verification flow
- [ ] **`ops/scripts/deploy_cursorrules_global.sh`** — deploys deleted `.cursorrules` template

## Rules / docs that mention deleted assets

- [ ] **`rules/25-python-dora-header.mdc`** — references deleted `python-header-template.py`
- [ ] **`profiles/session-startup-protocol.md`** — Suite-6 startup protocol; may reference deleted startup stack
- [ ] **`intelligence/workspace/setup-new-workspace.py`** — may reference `init_workspace` / startup paths
- [ ] **`intelligence/workspace/setup-new-workspace.md`** — same
- [ ] **`execution-governance/README.md`** — startup/session references
- [ ] **`README.md`** (GlobalCommands root) — startup/templates references
- [ ] **`C_GOV_FILES/`** duplicates — `session-startup-protocol.md`, `setup-new-workspace.md`, `setup-new-workspace.py`, `cursor-native-reasoning.md`
- [ ] **`workflows/Dags-Harvest/DAG-Harvest-5.md`** — startup references (verify)
- [ ] **`commands/dora-commands/do-README.md`** — template/startup references (verify)
- [ ] **`ops/scripts/_archived/migrate_to_project_rules.py`** — archived; low priority
- [ ] **`intelligence/reasoning/cursor-native-reasoning.md`** — verify overlap with `l9-structured-reasoning` before edit/delete

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
