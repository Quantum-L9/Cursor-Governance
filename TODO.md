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

## mypy debt (354 errors / 25 files, tracked 2026-07-19)

`.github/workflows/l9-lint-test.yml` (adopted from `l9-ci-core` v2's consumer
template) runs `mypy .` unscoped, same as it runs `ruff check .` — by explicit
decision, shipped as-is with debt tracked rather than holding the workflow
back or silently dropping the mypy step. **CI will show red on every PR
until this is fixed.**

- [ ] `workflows/gmp_executor.py` — ~40 errors, nearly all `Item "None" of
  "Optional[GMPState]" has no attribute "X"` (`union-attr`). Fix: add a
  `_require_state()` guard (per the established L9 pattern — raise if
  `None`, use the narrowed local) instead of accessing `self.state.X` directly
  everywhere.
- [ ] `workflows/dags/inspect_dag.py`, `workflows/harvest_deploy.py` — langgraph
  `StateGraph`/`CompiledStateGraph` return-type and `.ainvoke` attribute
  mismatches — likely a langgraph version/stub mismatch, investigate
  `langgraph` version pin before treating as app-code bugs.
- [ ] `workflows/nodes/{validate,report}.py` — `Optional[str]` used unguarded
  (`arg-type`/`index`) — real potential `None`-handling bugs, not just
  annotation noise.
- [ ] `workflows/state.py:55` — incompatible redefinition of a reducer
  function's type signature.
- [ ] `ops/scripts/transcript_distiller.py:58` — `datetime.UTC` doesn't exist
  on this mypy's stdlib stubs target; check `requires-python`/mypy
  `python_version` alignment.
- [ ] No `[tool.mypy]` section exists yet in `pyproject.toml` — add one
  (pinning `python_version`, `exclude` matching the ruff archived-dirs list)
  once these are triaged, so local `mypy .` matches CI exactly.

Run `mypy . --show-error-codes --ignore-missing-imports --exclude
'_archived|_archive|archive|archived|C_GOV_FILES|current_work'` from repo
root for the full current list.

## Missing `tools.validation.validate_external_code` (found + fixed-partially 2026-07-19)

While wiring `l9-lint-test.yml`, discovered `import workflows` was completely
broken at runtime (not just a lint nit) — traced to two nonexistent packages:

- [x] **`core.decorators.must_stay_async`** — **fixed**: never existed in git
  history (`git log --all` confirms), and every function it decorated
  (`workflows/nodes/{report,extract,inject,validate,checkpoint,deploy}.py`,
  `workflows/harvest_deploy.py`, `workflows/dags/inspect_dag.py` \u00d77) was
  already correctly declared `async def` \u2014 the decorator was a pure
  no-op-shaped safety wrapper, not load-bearing behavior. Removed the
  import + all 8 `@must_stay_async("callers use await")` decorator lines.
  `import workflows` now succeeds up to the next gap below.
- [ ] **`tools.validation.validate_external_code`** \u2014 **deferred, real gap,
  needs a dedicated pass**: `workflows/dags/inspect_dag.py`'s
  `compliance_node` genuinely calls 5 functions from this nonexistent
  module (`ValidationIssue`, `extract_python_code_blocks`,
  `validate_adr_compliance`, `validate_config_values`, `validate_imports`)
  to power what looks like the actual backing implementation for the
  `/inspect` code-gate slash command (see `02-slash-commands.mdc`:
  "Code gate — validate external code before import"). Unlike
  `must_stay_async`, this is real designed logic (severity buckets,
  issue-type classification), not a no-op \u2014 deleting the import would
  gut actual functionality. `skills/l9-inspect/` only has the protocol
  doc (`SKILL.md` + `references/inspect-protocol.md`), not the executable
  validators, so this can't be resolved by pointing at an existing
  alternative either. `tools/` was never tracked in git history (same as
  `core/` was). Explicit decision 2026-07-19: leave broken, implement
  properly in a dedicated follow-up pass — do not stub or delete.
  `pytest .` will show exactly 1 collection error
  (`workflows/dags/test_pipeline_dag.py`, via the `workflows.dags` import
  chain) until this is implemented.

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
