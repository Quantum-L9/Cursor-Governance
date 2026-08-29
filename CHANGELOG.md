# Changelog

All notable changes to this repo are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Entries before this
file existed (2026-07-19) are not reconstructed — see `git log` for that
history instead of trusting a backfilled entry here.

## [Unreleased]

### Removed
- **`execution-governance/`** (TODO A1): Suite-6 archive shell deleted after
  harvest C3/C1/C4 semantics landed in `ops/scripts/audit_rules_corpus.py`
  (inverted rule-enforcer coverage + named population). C5/C6 were already
  live. `operational-oversight.py` no longer soft-imports the retired
  `governance-monitor`. Do not restore the Flask API, dashboard, or Suite-6
  header validator.

### Changed
- **Suite-6 intelligence archive cut-over (2026-08-28):** live wrappers no longer
  exec missing context extractors. Resume owner is Graphiti hydrate +
  `graphiti_memory_client.py`. Historical: nine Suite-6 files were archived
  2026-07-19 (`268608be`); `graphiti_sink.py` was intended but never wired.
- **Merge authority:** campaigns / `make pr` still end green + merge-ready
  and do not merge. Invoking `/l9-pr-remediation` authorizes ordinary
  `gh pr merge` for all open PRs in the target repo after Converge.
  Receipt SSOT: `ops/autonomy/authorize_merge.py`. Gate:
  `ops/autonomy/merge_gate.py` (force-push / admin-merge never waived).
- **IDE class:** `eslint_owned_repos` is empty. Website-Bot and SEO-Bot
  classify as `biome_default` unless the eslint-without-biome heuristic
  matches. Named-exception tests assert both product names are not
  hard-locked to ESLint.
- **`l9-setting-up-ci` 2.0.0:** consumer CI bootstrap now prefers the
  `Quantum-L9/.github` seeder / `l9-ci-pack`, then `l9-ci-core`
  `presets/typescript/stamp.sh`. Agents must not invent `ci.yml` or
  `biome.json`, and must not add ESLint/Prettier as a second JS/TS/JSON owner.

### Added
- **Rules corpus coverage (harvest C3/C1):** `audit_rules_corpus.py` reports
  every declared rule's named enforcers and stamps `population` on
  `reports/rules-corpus-audit.json`. Advisory only — not a `make pr` gate.
  `make rules-corpus-audit` and `pr-full-corpus` run it. Missing
  `rules/RULES-MANIFEST.yaml` fails closed.
- **L4 Local Autonomy (no mid-execution push):** standing doctrine in
  `ops/autonomy/surface_profile.yaml` (`l4_local_autonomy`), CANONICAL_LAW §6.2,
  AGENTS.md §2.0.2, rule `88-l4-local-autonomy.mdc`. Flow: stacked-branch local
  commits → finish program/contract → `kernels/Recursive Alignment.md` +
  `kernels/Validate & Repair.md` → `ops/autonomy/l4_local.py authorize-release`
  → scoped PR via `PULL_REQUEST_TEMPLATE.md`. Mechanical deny of mid-exec
  `git push` / `gh pr create` / `make pr` via `ops/autonomy/local_execution_gate.py`
  (Claude PreToolUse + Cursor `beforeShellExecution`) and
  `open_pr_after_gate.sh`. Make targets: `l4-status`, `l4-begin`,
  `l4-record-kernels`, `l4-authorize`.
- **Autonomy Surface Parity:** `ops/autonomy/surface_profile.yaml` (standing A4
  doctrine SSOT), `ops/scripts/reconcile_claude_settings.py` + `make claude-settings`,
  `ops/autonomy/merge_gate.py` PreToolUse enforcement, SessionStart Profile inject,
  llm-rules `zz-autonomy-surface-override.md`, CANONICAL_LAW §6.1. Peers cite Profile
  via ADAPTER_CONTRACT autonomy carrier.
- **Executable Peer Contract v1:** an executable agent is now an active registry
  identity with a valid surface→Program-adapter binding, canonical autonomy
  access, and fresh machine-verifiable readiness — not merely shell access.
  `agent_registry.yaml` moves to schema v2 with a per-agent
  `execution: {enabled, bindings:[{surface, adapter_id}]}` block; `enabled` is a
  strong assertion (Wave A: `cursor` + `claude-code` enabled; `codex`/`gemini`/
  `manus` `enabled: false` until their dormant worker adapters are promoted).
  Each registry-bound Program adapter descriptor now carries an
  `identity.agent_ref` foreign key (spec schema requires it when
  `binding == agent_registry`), replacing the hardcoded adapter→agent map in
  `identity_binding.py`. New `executable-peer-readiness.schema.json` +
  `integrations/bootstrap/peer_readiness.py` / `peer_context.py` produce
  binding-level readiness receipts under `$HOME/.l9/programs/_peer-readiness/`.
  New cross-registry validator `validate_executable_peers.py` (rules E1-E15) and
  `scripts/probe_executable_peers.py`, wired as `make peer-execution-validate`,
  `make peer-execution-probe`, and the composed `make peer-execution-conformance`
  (plus the `Peer Execution Conformance` CI workflow). Program Execution stays
  the sole controller and `autonomy/` is referenced, never copied. Contract:
  `environment/agents/PEER_EXECUTION.md`. New dormant program adapters
  `codex-cloud` (worker_host), `gemini-review` (verifier), `manus-cloud`
  (worker_host, manual handoff) remain registered for coverage.

### Fixed
- `environment/program-execution/scripts/apply_repository_alignment.py` could
  never apply its own nested `BLOCKS` key
  (`environment/agents/docs/WORK_CLAIM_PROTOCOL.md`) because `_child_file`
  rejected any path separator; replaced with a confined nested-path join
  (`_child_path`) that still blocks absolute paths and traversal. The
  adapter-layer conformance suite is now fully green (70 tests).

- **Portable UI Operator (GMP-1…3):** `ops/secrets/` AWS Secrets Manager registry
  SSOT (`sync_secrets_registry.py`, `resolve_secret.py`), skills `l9-aws-secrets`
  and `l9-ui-operator`, `ops/ui-operator/` console + cartridges (GitHub Packages
  Actions access + Vercel stub), pyproject optional-extra `ui-operator`
  (`playwright==1.56.0`, boto3). Make targets: `secrets-sync`, `secrets-check`,
  `ui-operator-sync`. No Keychain; secret values never committed.
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

### l9-ci-core v2 integration

- Audited the `Quantum-L9/.github` \u2194 `Quantum-L9/l9-ci-core` integration
  end-to-end (git tags, tree contents, registry). Found the org's
  `workflow-interface-registry.yml` and 8 of 9 `workflow-templates/*.yml`
  starters reference `l9-ci-core@v1`, a tag that does not exist (only
  `v0.1.0` exists) and describe a 9-kernel workflow set (`pr-pipeline.yml`
  etc.) that `l9-ci-core`'s v2 rewrite replaced entirely. Filed
  [`Quantum-L9/.github#7`](https://github.com/Quantum-L9/.github/issues/7).
- Added `.github/workflows/l9-lint-test.yml`, adopted verbatim from
  `l9-ci-core` v2's `docs/templates/l9-lint-test.yml` (the documented
  consumer-side replacement for the retired v1 `pr-pipeline.yml`'s generic
  lint/test half \u2014 Core v2 intentionally does not own this, per
  `docs/consumer-lint-test.md`). `TEST_DIR`/`SOURCE_DIR` set to `.` (no
  `tests/` convention exists yet in this repo).
- Investigated `l9-ci-core`'s governed `profile-normalize-semgrep.yml`
  reusable workflow as a CodeQL companion/replacement candidate.
  **Not adopted** \u2014 its nested `normalize-semgrep-report.yml` does its own
  independent `git checkout` of the caller's exact `github.sha` and reads
  `report-path` from that checkout (no `upload-artifact`/`download-artifact`
  hand-off from a prior job), meaning the raw semgrep report would need to
  already be committed at that revision before the workflow runs \u2014 an
  undocumented consumer contract gap in `l9-ci-core` itself, not something
  to build speculatively. CodeQL remains the security scanner for this repo.
- Added `[tool.pytest.ini_options]` to `pyproject.toml` (`testpaths = ["."]`,
  `norecursedirs` mirroring the ruff archived-dir exclude list) so the new
  workflow's `pytest .` invocation doesn't collect
  `commands/_archived/do-templates/test_example.py`.

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
