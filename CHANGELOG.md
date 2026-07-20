# Changelog

All notable changes to this repo are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Entries before this
file existed (2026-07-19) are not reconstructed — see `git log` for that
history instead of trusting a backfilled entry here.

## [Unreleased]

### Added
- `AGENTS.md` — activation contract for future agent sessions (§2 documents
  the real `.sh`-hook activation mechanism)
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`,
  `PULL_REQUEST_TEMPLATE.md` — imported verbatim from `Quantum-L9/.github`.
  GitHub's org-default fallback is a UI/API-only pointer, not a file copy;
  these now exist locally for anyone who clones this repo offline.
- `.editorconfig`, `.gitattributes`, `pyproject.toml`, `.python-version`,
  `Makefile`, `.env.example`, `CODEOWNERS`
- `structlog>=24.0` and `langgraph>=0.2` added to `pyproject.toml` deps —
  re-derived the import scan per that file's own instruction
  (`grep -rhoE "^(import|from) [a-zA-Z0-9_]+"`) and found both were
  actively imported (10 files for structlog, 4 for langgraph under
  `workflows/`) but missing from the declared dependency list.
- `LICENSE` (MIT) — closes the `license: null` gap in the community profile
  that has no org-wide fallback (see `Quantum-L9/.github#6`)
- `.pre-commit-config.yaml` — wraps `validate_governance_no_hardcoded_paths.sh`
  and `validate_governance_symlinks.sh` as local hooks, plus ruff, so path-lint
  violations are caught pre-commit instead of only in CI

### Removed
- `start-session.yaml` (917 lines) — declarative YAML protocol that was never
  wired into any Cursor hook and had drifted from the pre-Graphiti learning
  pipeline archived in `ops/scripts/_archived/`.
  `ops/hooks/session_start_bootstrap.sh` is, and always was, the actual
  activation mechanism.

### Archived (Suite-6 → L9 cleanup, moved not deleted)

Cross-validated by 6 independent research passes against `CANONICAL_LAW.md`,
git history, and live-wiring references (skills, hooks, Makefile, `AGENTS.md`).
All moves used `git mv` to preserve history; nothing was hard-deleted. Every
`_archived/` directory involved is git-tracked (never gitignored) and now
excluded from pre-commit/ruff via the new `exclude` regex/glob added this
session (see below).

- `commands/workflow executors/` → `commands/_archived/workflow-executors/`
  (`gmp_executor.py`, `harvest_deploy.py`, `harvest_executor.py`,
  `use_harvest_executor.py`, `wire_executor.py`) — obsolete duplicate of the
  canonical `workflows/` tree (confirmed in `skills/AUTONOMY_MANIFEST.yaml`).
  **Exception:** `wire_executor.py`'s ~800-line implementation was the only
  complete one (the "canonical" `workflows/wire_executor.py` was a 17-line
  shim pointing at a nonexistent `core.codegen.wire_executor`) — migrated
  into `workflows/wire_executor.py` first, verified with `py_compile`, then
  the legacy copy was archived. `REPO_ROOT` computation is now correct as a
  side effect (previously resolved to `commands/`, now resolves to the actual
  repo root).
- `commands/dora-commands/do-templates/` → `commands/_archived/do-templates/`
  — orphaned `/do-init` scaffold (config templates + 3 stub `.py` files), no
  active codegen/skill references.
- `environment/{env-manager.py,env_loader.py}` → `environment/_archived/`
- `execution-governance/` (whole tree: `README.md`, `dashboard/`, `api/`,
  `monitoring/`, `testing/`, `validation/`) → `execution-governance/_archived/`
  — all 5 `.py` implementations confirmed Suite-6, docs described the same
  retired system.
- `foundation/{logic/,agents/}` → `foundation/_archived/{logic,agents}/`;
  `foundation/security/governance-integrity.py` →
  `foundation/security/_archived/` (existing archive folder)
- `telemetry/{calibration_dashboard.py,telemetry-collector.py}` →
  `telemetry/_archived/`
- `intelligence/learning/{auto_calibrator.py,chat-learning-extractor.py,
  feedback_collector.py}` → `intelligence/_archived/learning/`
- `intelligence/context-memory/context-extractor.py` →
  `intelligence/_archived/context-memory/` — pre-Graphiti extractor;
  `graphiti_sink.py` (kept, active) is its intended-but-never-wired
  replacement.
- `intelligence/workspace/{setup-new-workspace.py,setup-new-workspace.md}` →
  `intelligence/_archived/workspace/` — `setup-new-workspace.md` was a
  1000+ line Suite-6 doc (`.suite6-config.json`, hardcoded Dropbox paths).
  `SETUP_QUICK_START.md` rewritten to point at `AGENTS.md` instead.
- `workflows/session/dags/wire_dag.py` →
  `workflows/_archived/session/dags/wire_dag.py` — orphaned duplicate of the
  canonical `workflows/dags/wire_dag.py` (the one `dags/__init__.py` actually
  imports). Nothing referenced the `session/dags` path; the orphan also
  lacked the required DORA header/footer meta blocks.

### Investigated and kept (not archived, despite initial LEGACY flags)
- `integrity/hash-verifier.py` — confirmed ACTIVE: `manifest-lock.json` is a
  live artifact, `system-check.sh` calls it, git history shows deliberate
  Suite-6→L9 rebrand carry-forward. Standalone integrity concern, unrelated
  to the deprecated memory/learning stack.
- `intelligence/reasoning/reasoning-snapshot-generator.py` — kept per
  explicit decision; needs a follow-up fix (see `TODO.md`).

### Pre-commit / ruff hardening
- `.pre-commit-config.yaml` — added top-level
  `exclude: '(^|/)_?archive(d)?/'` so every hook (present and future) skips
  `_archived`/`_archive`/`archive`/`archived` directories. They remain fully
  git-tracked — this only exempts them from lint/format checks.
- `pyproject.toml` — added `force-exclude = true` plus glob patterns
  (`**/_archived`, `**/_archive`, `**/archive`, `**/archived`) under
  `[tool.ruff]`. `force-exclude` matters because pre-commit passes explicit
  filenames, which bypasses plain `exclude` (directory-discovery-only).

### Fixed
- `ops/scripts/resolve_governance_paths.sh` — removed the Dropbox fallback
  path entirely; `$HOME/.cursor-governance` (the GitHub clone) is now the
  sole resolvable governance root.
- `ops/scripts/backup_to_github.sh` — removed a stale `CANONICAL_LAW.md`
  copy step that, combined with the Dropbox fallback above, was reintroducing
  stale content into `main` on every session end and had caused a real merge
  conflict.
- `ops/scripts/operational-oversight.py` — fixed dangling references to
  `startup/REASONING_STACK.yaml` and `verify-startup-files.sh`, both of which
  no longer exist.
- `end-session.yaml` — `sister_file` now points at
  `ops/hooks/session_start_bootstrap.sh` instead of the deleted
  `start-session.yaml`.

## [2.0.0] - 2026-07-04

Post-Suite-6, Graphiti-native governance rewrite (per `README.md`
frontmatter). Predates this changelog — consult `git log` rather than a
backfilled entry.

## [1.x] - 2025-01-27 and earlier

Predates this changelog.
