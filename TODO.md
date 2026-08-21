# GlobalCommands — Tech Debt (cleanup later)

Context: `tests/`, `templates/`, and `startup/` were deleted (superseded by v6 L9 skills, `.cursor/rules/*.mdc`, `AGENTS.md`, and active wiring scripts). `start-session.yaml` was deleted (2026-07-19) — it was never wired into any hook and had drifted from the archived pre-Graphiti learning pipeline. `ops/hooks/session_start_bootstrap.sh` is the real, live activation script: installed at `~/.cursor/hooks/session-start-bootstrap.sh`, registered in `~/.cursor/hooks.json` under `sessionStart`, runs automatically every session.

## Portable UI operator follow-ups (2026-08-06)

- [ ] Provision AWS secrets `openclaw-igorbot/ui-session-github` and
  `openclaw-igorbot/ui-session-vercel` (JSON key `storage_state`), then
  `make secrets-sync` so overlays flip to `provisioned: true` for `--mode run`.
- [ ] Promote `ops/ui-operator/cartridges/vercel-project-settings-stub.yaml` to a
  filled v1 cartridge (selectors + mutation_allowlist) after human approve.

## Memory / session writes — blocked this session (2026-07-20)

- [ ] ⚠️ **Graphiti (T1) memory writes** — blocked, not done. Health check:
  `liveness_ok: true` but `mcp.tools.reachable: false` (HTTP 404 on the
  SSH-tunneled tool plane). Per the no-local-fallback rule, no fake success
  was reported — this is a real gap, captured in `activeContext.md` for next
  session.
- [ ] ⚠️ **Redis `cache_set_session_context`** — not called. No cache/session
  MCP server is present in this workspace's current MCP tool set.

## Dangling references (broken if invoked)

- [x] **`ops/scripts/operational-oversight.py`** — fixed (2026-07-19): dangling refs to
  `startup/REASONING_STACK.yaml` and `verify-startup-files.sh` repaired. **Keep, still needs a
  second pass:** its optional `governance_monitor` import (line 59) now points at an archived
  module (`execution-governance/_archived/monitoring/governance-monitor.py`) — already
  soft-fails via `try/except ImportError` so it's not broken, but the fallback message is stale.
- [x] **`ops/scripts/verify-startup-files.sh`** — **already purged** with `ops/scripts/_archived`
  (2026-08-06). Close as stale; see DELETE LIST A9 / B9.
- [x] **`ops/scripts/README_STARTUP_VERIFICATION.md`** — **already purged** (same).
- [x] **`ops/scripts/deploy_cursorrules_global.sh`** — **already purged** (same).
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
- [x] **`profiles/session-startup-protocol.md`** — **confirmed dead** (2026-07-24). Lines 61-225 were
  the Suite-6 "read all profiles at startup" bootstrap, superseded by `commands/start-session.md` +
  `ops/hooks/session_start_bootstrap.sh`. Sections B-E cited a foreign stack (`HARD_RULES.md`,
  Supabase schema/auth, `Configuration/.env`) — all absent from this repo, dropped. Only sections
  F/G/H generalized; condensed into `rules/45-pre-action-verification.mdc`. File pending deletion at
  the `profiles/` retirement gate.
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
  **On DELETE LIST (2026-08-12) as A1** — whole tree is archive-only; awaiting delete PR.
- [ ] **`README.md`** (GlobalCommands root) — startup/templates references
- [x] **`C_GOV_FILES/`** duplicates — **path already deleted** (2026-07-05). Remaining work is
  doc scrub only — see DELETE LIST A8.
- [ ] **`workflows/Dags-Harvest/DAG-Harvest-5.md`** — startup references (verify)
- [ ] **`commands/dora-commands/do-README.md`** — points at the now-archived
  `commands/_archived/do-templates/` (2026-07-19); still describes the `/do-*` scaffold
  commands (`do-init.md`, `do-status.md`, etc.) which were left untouched — verify whether
  those slash commands are still wired to anything before deciding their fate.
- [x] **`ops/scripts/_archived/migrate_to_project_rules.py`** — archive tree purged 2026-08-06;
  see DELETE LIST A9 (doc scrub only).
- [ ] **`intelligence/reasoning/cursor-native-reasoning.md`** — verify overlap with `l9-structured-reasoning` before edit/delete
- [ ] **`integrity/hash-verifier.py`** — investigated 2026-07-19, confirmed **ACTIVE, keep**:
  `manifest-lock.json` is a live present artifact, `system-check.sh` calls it, and git history
  shows deliberate Suite-6→L9 rebrand carry-forward (not left to rot). Distinct standalone
  concern from the deprecated memory/learning stack.

## Ruff debt (RESOLVED 2026-07-28 — `ruff check .` and `ruff format --check .` are green)

Both steps in `.github/workflows/l9-lint-test.yml`'s `Lint and Type Check` job were failing
on every PR (confirmed pre-existing on `main`, unrelated to whatever branch triggered CI).
Fixed:
- [x] `WIP/` added to `[tool.ruff] exclude` — 92 of 126 `ruff check` errors were in the
  vendored `WIP/Graphiti - Cirsor Governance/L9-Graphite-Memory 4/` extraction (scratch
  content the user is separately deleting), not production code.
- [x] 34 real `E501` line-too-long errors hand-wrapped across `ops/scripts/{audit_rules_corpus,
  capture_rules_cleanup_preflight, generate_rules_manifest, inventory_cursor_extensions,
  inventory_mcp_servers, validate_rules_manifest}.py`.
- [x] `ruff format .` applied repo-wide — 17 files needed it (6 of the `ops/scripts/*.py`
  above, plus 11 `.md` files with embedded Python code blocks that modern `ruff format`
  also formats: `commands/dora-commands/{do-init,do-metrics}.md`,
  `intelligence/standards/production-quality-standards.md`,
  `learning/solutions/{authentication-fixes,json-issues}.md`,
  `skills/l9-inspect/{SKILL.md,references/inspect-protocol.md}`,
  `skills/l9-python-tdd-with-uv/SKILL.md`, `workflows/Dags-Harvest/DAG-Harvest-{1,2}.md`,
  `workflows/README.md`).

Original 2026-07-19 tracking (F401/F841/E722/E402/E741/P022 breakdown) is superseded — this
list has drifted meaningfully since (files added/removed, WIP grown); re-derive with
`ruff check .` from repo root if new debt accumulates.

## mypy debt (328 errors / 15 files, tracked 2026-07-19, made advisory 2026-07-28)

`.github/workflows/l9-lint-test.yml` (adopted from `l9-ci-core` v2's consumer
template) runs `mypy .` unscoped, same as it runs `ruff check .`. In practice this
step **never actually ran** on any PR to date — `ruff check` was failing first and
GitHub Actions stops a job at the first failing step, so mypy was silently masked.
Once `ruff check`/`ruff format` were fixed (above), mypy surfaced for the first time
and failed with 328 errors across 15 files. Rather than block merges on a first-time-
surfaced, pre-existing 328-error debt pile unrelated to any given PR's diff, the `mypy`
step now has `continue-on-error: true` — still runs and visible in the Actions UI, but
advisory, not blocking, until this list is worked through.

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
  **Update 2026-07-28:** `workflows/dags/test_pipeline_dag.py` is not actually a
  pytest test (it's a DAG module — a "test pipeline" *workflow* — that only
  matches pytest's `test_*.py` discovery convention by name coincidence). Its
  collection was the CI `Test Suite` job's failure mode for this gap. Added
  `--ignore=workflows/dags/test_pipeline_dag.py` to `[tool.pytest.ini_options]
  addopts` so CI stops tripping over a dormant, currently-unused code path.
  The underlying gap (missing `tools/` module) is untouched — still leave
  broken per the explicit decision above, do not stub or delete.

## Already superseded (do not restore)

| Deleted | Replaced by |
|---------|-------------|
| `startup/REASONING_STACK.yaml` | `skills/l9-structured-reasoning/` |
| `startup/init_workspace.py` symlink logic | `ops/scripts/setup_workspace_symlinks.sh`, `check_governance_wiring.sh`, `wire_governance_workspace.sh` |
| `templates/.cursorrules` | `.cursor/rules/*.mdc` + `AGENTS.md` |
| `templates/python-header-template*.py` | `l9-skill-compiler` `meta-standard.md` (lean frontmatter) |
| `tests/test_imports.py` | `l9-wire-skill-into-repo` validation |

---

## Spring-clean DELETE LIST (2026-08-12) — list only; do not delete yet

Audit of orphaned / archived residue vs live SSOT. **Nothing on this list has been
deleted in this pass.** Before any delete PR: re-grep live callers
(`ops/`, `.github/`, `Makefile`, hooks, non-archived `skills/` / `rules/` /
`environment/`), confirm CHANGELOG/TODO archival rationale, and keep
`ALLOW-ROOT-DELETION` / CODEOWNERS rules if a root-protected path is touched.

**Not on this list (KEEP — live SSOT):**
`environment/program-execution/`, `environment/agents/adapters/claude-code/`,
root `autonomy/`, `ops/autonomy/`, `ops/hooks/`, `ops/scripts/` (active set),
`ops/graphiti/`, `integrity/`, `kernels/`, `skills/` (live packs),
`skills/_archived/` **directory convention** (retirement landing zone — keep the
folder even if individual packs are later purged), `learning/` (non-`_archived`),
`schemas/`, `releases/`, `governance/`, `ORG_INVARIANTS.yaml`, `end-session.yaml`.

### Tier A — safest delete candidates (100% archive shells / already gone)

| # | Path | Status | Notes |
|---|------|--------|-------|
| A1 | **`execution-governance/`** | EXISTS (7 files, only `_archived/`) | Suite-6 api/dashboard/monitor/validator (2026-07-19). No live callers. Soft-fail import note in `ops/scripts/operational-oversight.py` — scrub message when deleting. **Added 2026-08-12.** |
| A2 | **`telemetry/`** | EXISTS (2 files, only `_archived/`) | `calibration_dashboard.py`, `telemetry-collector.py` (2026-07-19). |
| A3 | **`environment/_archived/`** | EXISTS (2 files) | `env-manager.py`, `env_loader.py` (2026-07-19). |
| A4 | **`workflows/_archived/`** | EXISTS (1 file) | Orphan `wire_dag.py` duplicate (2026-07-19). |
| A5 | **`intelligence/_archived/`** | EXISTS (9 files) | learning/workspace/context-memory Suite-6 (2026-07-19). |
| A6 | **`learning/failures/_archived/`** | EXISTS (1 file) | Noise MD. |
| A7 | **`foundation/`** | EXISTS (~351 files, all under `_archived/`) | logic/agents + `security/_archived/signatures/` (~333 JSON sigs). **Signatures may be provenance ledger** — prefer cold-export or keep sigs; do not bulk-delete without owner call. |
| A8 | **`C_GOV_FILES/`** | ABSENT (deleted 2026-07-05) | Scrub README/TODO/pyproject excludes that still teach the path. |
| A9 | **`ops/scripts/_archived/`** | ABSENT (purged 2026-08-06) | Scrub AGENTS/CANONICAL_LAW/CODEOWNERS that still teach the path; do not recreate. |
| A10 | **`memory-bank/`** | ABSENT (retired 2026-08-11) | Policy already WARNs if residual; keep absent. |
| A11 | **`start-session.yaml`** | ABSENT (deleted 2026-07-19) | Docs/reports only. |
| A12 | **`environment/claude-code`** | ABSENT (symlink extinguished 2026-08-12) | Sole home: `environment/agents/adapters/claude-code/`. |

### Tier B — orphan / pending retirement (not under `_archived/`, verify then delete)

| # | Path | Status | Notes |
|---|------|--------|-------|
| B1 | **`profiles/`** | EXISTS (~12 files) | README DEPRECATED; `session-startup-protocol.md` confirmed dead. Content migrated into skills/rules. Update `AUTONOMY_MANIFEST.yaml` `sources` that still cite `profiles/*` before delete. |
| B2 | **`key components/`** | ABSENT (absorbed 2026-08-13) | Unique deltas folded into live skills; stubs deleted. See B2 supersession below. |
| B3 | **`pipeline/`** | EXISTS (3 markdown files) | Doc-only; no hooks/Makefile. |
| B4 | **`security/`** (repo root docs) | EXISTS (2 files) | Mostly cited from deprecated profiles; not `foundation/security`. |
| B5 | **`commands/_archived/`** | EXISTS (17 files) | Skipped by commands manifest generator; candidates for hard-delete after retention window. |
| B6 | **`commands/dora-commands/`** | EXISTS (7 files) | AUTONOMY_MANIFEST: unwired legacy DORA; points at archived do-templates. Verify slash commands unused, then delete or archive. |
| B7 | **`ops/feedback_loop_config.yaml`** | EXISTS | Dangling `feedback_collector.script` path; no live consumers. |
| B8 | **`ops/scripts/session_init.sh`**, **`show_context.sh`**, **`process_context.sh`**, **`tenx_status.sh`** | EXISTS | Not referenced from `ops/hooks/` / Makefile / `.github/`. Pre-Graphiti / LaunchAgent-era. |
| B9 | **`ops/scripts/verify-startup-files.sh`**, **`deploy_cursorrules_global.sh`**, **`README_STARTUP_VERIFICATION.md`** | ABSENT | Already purged with `ops/scripts/_archived` — close the open TODO bullets above as done/stale. |
| B10 | **`activation-command.md`** | EXISTS | One-line pointer; unused by hooks. Renamed from `Activation Command.md` (RB-HK-001). |
| B11 | **`ops/graphiti/memory-bank-template/`** (non-`RETIRED.md` stubs) | check | Policy: archival only; keep `RETIRED.md` or fold into `MEMORY_BANK_POLICY.md`. |

**B2 supersession (2026-08-13)** — `key components/` stubs deleted; unique deltas absorbed (no new skills, no CLIs, no auto-apply):

| Stub | Successor |
|------|-----------|
| 01 pattern-detector | `l9-code-analysis` `references/pattern-alignment.md` + `/extract_align` |
| 03 error-corrector | `l9-pr-remediation` + `l9-issue-remediation` `references/fix-engine.md` lesson recall |
| 04 deployment-orchestrator | skipped — `l9-ci-ops` workflow-governance + `make pr` |
| 05 workflow-explainer | skipped — `/analyze` flow mapping; no `.L9.json` in repo |
| 06 refactor-assistant | `l9-code-maintenance` `references/refactor-sweep-protocol.md` Discovery |
| 06 security-validator | `l9-auditing-security` presence-gated workflow credential lint |
| 07 session-rebuilder | skipped — Graphiti inject / `l9-graphiti-memory` |
| 09 monitor-agent | skipped — `check_governance_wiring.sh` on-demand |
| 10 folder-reorganizer | skipped — CANONICAL_LAW + `l9-repository-renovation` |

### Tier C — judgment required (do not bulk-delete)

| # | Path | Notes |
|---|------|-------|
| C1 | **`skills/_archived/*` pack contents** | Individual packs may purge after retention; **keep** `_archived/` landing zone + `skills/_archived/README.md`. |
| C2 | **`foundation/security/_archived/signatures/`** | Immutable provenance carve-out in migration reports; may need cold storage, not git wipe. Blocks careless whole-`foundation/` delete (A7). |
| C3 | **`intelligence/context-memory/`** (non-archived) | CANONICAL_LAW still lists `graphiti_sink.py` / related; CHANGELOG: sink kept, never wired. Decide keep-lean vs archive. |
| C4 | **`intelligence/reasoning/*`** | Explicit KEEP for `reasoning-snapshot-generator.py` (2026-07-19); `cursor-native-reasoning.md` overlap with `l9-structured-reasoning` TBD. |
| C5 | **`reports/`**, **`WIP/`** | Scratch / evidence — cleanup by human policy. **`current_work/`** deleted (RB-HK-001); `repo-hygiene` fail-closes if it reappears. |
| C6 | **`commands/emma-repo-commands/`** | Manifest omit from GlobalCommands; still has `wire_emma.md` — owner call. |

### Suggested delete PR sequence (when authorized)

1. **Doc scrub first:** A8–A11 path teaching + close stale Tier-B9 TODO bullets (no tree delete).
2. **Empty archive shells:** A1 `execution-governance/`, A2 `telemetry/`, A3–A6 (skip A7 until signatures decision).
3. **Orphan live paths:** B1 `profiles/` (after AUTONOMY_MANIFEST), then B2–B4, B6–B8, B10.
4. **Archive retention purge:** B5 / C1 only with explicit retention decision.
5. **Never in spring-clean:** `environment/program-execution/`, Claude adapter pack, `ops/autonomy/`, root `autonomy/`.

### Audit method (2026-08-12)

- Top-level + `_archived/` inventory; existence counts via `find`.
- Live-ref spot checks with ripgrep excluding `reports/`, `_archived/`, CHANGELOG/TODO.
- Cross-check CHANGELOG 2026-07-19 Suite-6 archive + 2026-08-06 `ops/scripts/_archived` purge.
- Confirmed: no Makefile / `.github/` / `ops/hooks` dependencies on Tier A shells.

## Publish note

Changes live in the SSOT (`$HOME/.cursor-governance`). Backup via `sessionEnd` hook or `make governance-backup` — not from IB-Odoo_19.

## pre-commit vs `make pr-check` — parked (2026-08-17)

Do **not** edit `.pre-commit-config.yaml` and do **not** change the working
`Makefile` / `make pr` lifecycle (PR #209) until this is an explicit follow-up.
Keep shipping through `make improve` → `make pr-check` → `make pr`.

**Findings (microscope, 2026-08-17):**

1. **Git commit hook is not installed.** `core.hooksPath` unset;
   `.git/hooks/pre-commit` absent. Worktrees share
   `/Users/macm2/Cursor-Governance/Cursor-Governance/.git/hooks`.
   `pre-commit install` would write that local untracked file. CI never uses
   the hook.
2. **What actually runs lint today**
   - Local: `make pr-check` → `run_pr_gate.sh` → `run_pr_precommit.sh`
     (catalog in `.pre-commit-config.yaml` on changed files) **then** locked
     `.venv` ruff check/format again.
   - CI Lint: `uv run ruff` in `.github/workflows/l9-lint-test.yml` — not the
     `pre-commit` CLI.
   - CI Test Suite: `uv sync --extra dev` + pytest. Dev extra does **not**
     install the `pre-commit` framework. A unit test that shelled into
     `run_pr_precommit.sh` failed until empty file-lists PASS without the
     binary (PR #209).
3. **Duplication is real, but `pr-check` is not only a ruff clone.**

   | In `.pre-commit-config.yaml` | Re-run after that in `pr-check` | Only in `pr-check` |
   |---|---|---|
   | merge-conflict, path-lint, rules, skills, hygiene, ruff, ruff-format | ruff + format (locked venv) | pytest, gitleaks/bandit/semgrep, uv-lock, wiring, gate receipt |

4. **Intended later owner (not this slice):** yaml owns lint; `make pr`
   stays the publish path; `pr-check` becomes a thin alias (catalog + the
   non-lint extras). Do not delete `pr-check` until pytest/security/receipt
   live in the yaml or stay as named extras. Do not teach
   `pre-commit install` as the shipping gate.
5. **Other leftover surfaces (leave alone for now):**
   - `make precommit` / `precommit-repo` — INTERNAL full-tree / changed-files
     of the same catalog.
   - `make push: precommit backup` — second path toward GitHub.
   - Claude web `setup.sh` still mentions `pre-commit install`.
   - Pin lockstep: catalog ruff `rev` vs locked `.venv` ruff vs CI `uv run ruff`.

- [x] Hygiene secret-grep skips `WIP/` the same way scratch `current_work/`
      was never content-scanned (directory remains fail-closed if recreated).
- [ ] Later: yaml-owns-lint (drop the second ruff block in `run_pr_gate.sh`)
      without rewriting `.pre-commit-config.yaml` until that campaign starts.
- [ ] Later: decide git hook (`pre-commit install`) as optional local
      convenience only — not CI, not `make pr`.
- [ ] Later: retire `make push: precommit backup` and Claude `pre-commit install`
      teaching once the owner is yaml.

## Program Execution MANIFEST.json — advisory by decision (2026-08-21)

Settled. This is no longer open work; it is recorded so the disposition is
findable from the artifact.

`environment/program-execution/MANIFEST.json` is **advisory**. Nothing in the PR
gate and nothing in CI enforces it, and that is the intended design, not a
suspension awaiting reversal.

- **Why.** The manifest hashes 471 files across the Program Execution adapter
  layer. `scripts/` alone changed 38 times in the three days before this
  decision, so ordinary source edits invalidate it by construction — that churn
  is what the artifact measures, not a defect in how it is scoped. Narrowing the
  surface was considered and rejected: `campaigns/` (124 files) holds declarative
  `CAMPAIGN_SOURCE.yaml` inputs rather than run output, so dropping it would
  shed a real contract surface without removing the friction.
- **Where it still runs.** `make program-execution-conformance` invokes
  `validate_manifest.py`. That target is the manifest's home, deliberately
  manual.
- **Generation.** `generate_manifest.py` stays opt-in through
  `sync_generated_artifacts.py --pe-manifest`. Auto-writing it during a gate run
  was the original source of the merge friction (a hook that rewrites the tree
  mid-gate reads as "files were modified by this hook"), so the gate never
  writes it.
- **What replaces CI enforcement.** `tests/environment/program_execution/test_manifest_contract.py`
  pins determinism, the generate/validate round-trip, and the exclusion rules on
  both sides. `git_guardrails.DELIBERATELY_NOT_GENERATED` keeps the manifest off
  the disposable-generated list so the clean gate never destroys a local
  regeneration.

Re-opening this needs a stated consumer with an integrity requirement the
advisory path does not meet — not merely the observation that CI does not check
it.

## Claude Code startup/bootstrap — deferred items (2026-08-19)

The startup/bootstrap forensic audit fixed the wiring and reporting defects
(SB-01 pre-commit git hook, SB-02 workspace misdirection, SB-03/SB-04 stale
receipt projection, SB-06 dependency-cache honesty, SB-07 memory label). Two
findings were deliberately left open:

- [ ] **Memory write-back: sticky idempotency** (`MEM-01`, HIGH). In
      `ops/graphiti/hydration/close_session.py:88`, `already_closed()` returns
      True on `or data.get("status") == "closed"`, so once a session has closed
      successfully even once, every later Stop hook returns `idempotent_skip`
      with 0 writes regardless of new content. Evidence:
      `.l9/memory/closes/<session>.json` shows one close with `write_count: 2`,
      after which every writeback receipt reads `writes: 0`. Consequence
      (`MEM-02`): the store only ever captures the first turn of a session, so
      hydrate returns self-referential PICKUP boilerplate instead of real resume
      state. Needs its own plan — the fix is not a one-line guard removal, since
      the head-hash path must still suppress genuine duplicate Stop events.
- [ ] **Capability broker URL** (`SB-05`). `L9_CAPABILITY_BROKER_URL` is unset in
      cloud sessions, so every MCP server in `.mcp.json` has an unresolvable URL
      and the brokered plane (including the `graphiti-memory` front door) never
      connects. Decide whether cloud sessions must carry it; if it stays
      optional, name the concrete lost capabilities in the startup banner rather
      than reporting a bare `DEGRADED`.
