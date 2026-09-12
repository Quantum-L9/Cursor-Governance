# Cursor-Governance — invariants index

**Version:** 1.4.0
**Updated:** 2026-09-11
**Role:** this-repo operating-invariant index plus a CI enforcement map.

This file does **not** replace [`ORG_INVARIANTS.yaml`](ORG_INVARIANTS.yaml). That YAML is the machine-readable organization policy SSOT. The operator note for org policy is [`docs/governance/ORG_INVARIANTS.md`](docs/governance/ORG_INVARIANTS.md). Do not copy `L9-ORG-*` requirement bodies into this file.

Authority for day-to-day work: `CANONICAL_LAW.md` > `ops/autonomy/surface_profile.yaml` > `AGENTS.md` > skills. This index does not outrank them.

## Invariant list

Named pointers only. One line + path. Bind from live law at refresh time.

| Invariant | Authority |
|---|---|
| One governance root; no Dropbox / cloud-storage fallback | [`CANONICAL_LAW.md`](CANONICAL_LAW.md) §1; [`ops/scripts/resolve_governance_paths.sh`](ops/scripts/resolve_governance_paths.sh) |
| Cursor-primary capability; thin adapters wrap outward | `CANONICAL_LAW.md` §2.1 |
| Symlink law (consumers `.cursor-commands` → clone; SSOT must not self-alias) | [`AGENTS.md`](AGENTS.md) §10; `CANONICAL_LAW.md` §1–3 |
| Sole sanctioned publish path is `make pr` (any capitalization); raw `git push` / `gh pr create` skip the Makefile checkers (not a hook denial in this repo) | `AGENTS.md` §4; `CANONICAL_LAW.md` §6.2.4 |
| L4: local commits only during execution; no mid-execution push | `AGENTS.md` §3.1; `ops/autonomy/surface_profile.yaml` |
| Graphiti is the episodic resume SSOT; do not write `memory-bank/` | `AGENTS.md` §7; `ops/graphiti/MEMORY_BANK_POLICY.md` |
| Memory egress crosses the `l9-graphite-memory` control plane only; no direct provider calls, no provider credentials in Cursor code (INV-03/04/06/07/11). Enforce mode since stage C11 (merge-blocking; ADR-0030); the boundary's shape is enforced on the AST and at runtime since audit closure C14 (no network/provider transport imports on the memory path, process spawn only through the binding modules, the client launches only the bound `l9-memory`), and the binding is proved against the exact memory artifact by a required, non-skippable job | `ops/memory/README.md`; [`ops/config/memory-binding.json`](ops/config/memory-binding.json); [`ops/scripts/validate_memory_egress_boundary.py`](ops/scripts/validate_memory_egress_boundary.py); [`tests/ops/memory/test_transport_boundary.py`](tests/ops/memory/test_transport_boundary.py); `.semgrep/l9-pr.yml` (`l9.memory-boundary-*`); [`.github/workflows/memory-cross-repo.yml`](.github/workflows/memory-cross-repo.yml) |
| Secret values never in git, logs, receipts, or chat | `AGENTS.md` §8; `ops/secrets/` |
| Root files are classified; new root files must be registered; `additive_only` files are append-only | `AGENTS.md` §14; [`ops/config/root-file-protection.json`](ops/config/root-file-protection.json) |
| One mutating agent per worktree; stage explicit pathspecs only | `AGENTS.md` + `rules/49-shared-worktree-isolation.mdc` |
| Org repository birth under `Quantum-L9` | `ORG_INVARIANTS.yaml` `invariants:`; `docs/governance/ORG_INVARIANTS.md` |
| Tests run once locally (same worktree digest + `PR_BASE`); full corpus is `make pr-full` / nightly / push-to-`main` | `AGENTS.md` `TESTS_ONCE_AND_PUBLISH_V1`; `CANONICAL_LAW.md` §6.2.5 |
| Commit finished work when done, then `make pr` (remediates=1; `PR_REMEDIATE=0` opt-out) | `AGENTS.md` `TESTS_ONCE_AND_PUBLISH_V1`; `rules/48-make-pr-remediation.mdc` |
| `pr-check` is the INTERNAL gate leaf of `make pr`; Diagnose is `OPEN_PR=0 make pr`; do not run `pr-check` after `precommit-repo` | `AGENTS.md` `PR_CHECK_FOLDED_V1`; `rules/48-make-pr-remediation.mdc` |
| Repository documentation closure is obligation-based: a receipt may be `PASS` only when every applicable `DocumentationObligation` is terminal and its required validation is evidenced; any required non-terminal obligation remains `PARTIAL`, and a blocked obligation yields `BLOCKED` | `skills/l9-update-agent-docs/contracts/documentation-obligation.schema.json`; `skills/l9-update-agent-docs/scripts/doc_obligations.py` |
| Semantic documentation obligations require admitted, change-bound `l9-intelligence-harvest` evidence; the Harvest input must bind the evaluated repository, required surfaces, and semantic source digest before it may qualify an obligation | `skills/l9-update-agent-docs/scripts/repo_docs.py`; `skills/l9-update-agent-docs/scripts/compile_semantic_obligations.py` |
| Maximum velocity is the committed execution personality on every surface (Cursor and Claude): `maximum_velocity`, `max_parallel>=480`, `max_mutation_lanes>=128`, `native_subagent_limit>=480`. Independent research launches as concurrent Tasks, not one in-session lane | `ops/autonomy/claude-execution-profiles.json`; `ops/autonomy/surface_profile.yaml` `claude_execution_profiles`; `rules/07-max-velocity-research.mdc`; `ops/scripts/validate_max_velocity.py` |
| `/ff` overwrite-untracked scan is two git processes (`ls-files` + `ls-tree` + `comm -13`), never one `ls-files --error-unmatch` per origin path | `skills/l9-repo-sync/scripts/ff.sh`; `skills/l9-repo-sync/scripts/validate_pack_structure.py` |
| Tree kernels latch at precommit (first writers step of `make pr`), never at L4 authorize-release; every local surface latches and unmarked CI is the only skip | `ops/autonomy/kernel_gate.py`; `ops/autonomy/surface_detect.py`; `CANONICAL_LAW.md` `KERNEL_PRECOMMIT_HOOK_V1`; `AGENTS.md` `KERNEL_LATCH_BARE_LOCAL_V1` |

Org-policy invariant IDs and enforcement text live only in the YAML `invariants:` block. Point there; do not duplicate.

## CI enforcement map

Invariant → workflow or script that actually checks it. Local procedure remains `AGENTS.md` §4–6.

| Invariant | Enforcement |
|---|---|
| Root-file classification / append-only | `.github/workflows/root-file-protection.yml` → `ops/scripts/validate_root_file_protection.py` |
| Org policy / Quantum-L9 birth | `.github/workflows/validate-org-policy.yml` → `ops/scripts/validate_org_policy.py` |
| Governance wiring / tip freshness | `.github/workflows/governance-self-check.yml`; `ops/scripts/check_governance_wiring.sh` |
| Repository documentation obligations / evidence-backed closure | `.github/workflows/governance-self-check.yml` → `skills/l9-update-agent-docs/scripts/repo_docs.py` → `l9.repo-docs.receipt.v3` |
| No hardcoded `/Users` / `/home` paths | `.pre-commit-config.yaml` hook `no-hardcoded-paths` → `ops/scripts/validate_governance_no_hardcoded_paths.sh` |
| No Dropbox SSOT / L9_MEMORY_HTTP residue | pre-commit `legacy-doctrine-residue` → `ops/scripts/validate_legacy_doctrine_residue.py` |
| Lint / format / tests | `.github/workflows/l9-lint-test.yml`; local `make pr` |
| Peer Execution / adapter conformance | `.github/workflows/peer-execution.yml` |
| Supply chain | `.github/workflows/supply-chain.yml` |
| CodeQL | `.github/workflows/codeql.yml` (reusable: `codeql-reusable.yml`) |
| Repo hygiene | `.github/workflows/repo-hygiene.yml`; pre-commit `repo-hygiene` |
| Generated artifact heal | pre-commit `sync-generated-artifacts` (make pr may WARN+continue; see hook comment) |
| Maximum-velocity execution profile | pre-commit `max-velocity` → `ops/scripts/validate_max_velocity.py`; `tests/ops/scripts/test_validate_max_velocity.py` |
| `/ff` overwrite-untracked high-velocity | `skills/l9-repo-sync/scripts/validate_pack_structure.py`; `skills/l9-repo-sync/scripts/self_test.py` `ignored_colliding` |

Workflow file count at write time: **14** under `.github/workflows/`. Recount from that directory on refresh. Blocking vs janitor split: [`ARCHITECTURE.md`](ARCHITECTURE.md) CI/CD architecture.

## False positives

Only items with a cited exclude or ignore. No invented flakes.

| Where | What | Why (cited) |
|---|---|---|
| `.pre-commit-config.yaml` `exclude` | `_archive(d)?/`, `WIP/`, `current_work/`, `C_GOV_FILES/`, `reports/`, root `workflows/` | Scratch / reference trees must not block or be reformatted (comment in that file; keep in sync with `ops/scripts/resolve_changed_files.sh` `SCRATCH_PREFIXES` and `ops/scripts/run_pr_security.sh` `EXCLUDE_PREFIXES`) |
| `.pre-commit-config.yaml` `check-yaml` `exclude` | `environment/generated/`, `environment/program-execution/core/` | Generated / sealed PE core YAML |
| `pyproject.toml` `[tool.ruff] exclude` / `force-exclude` | archives, `WIP`, `C_GOV_FILES`, `.cursor-commands`, `.cursor`, `environment/generated/llm-rules`, `ops/generated`, `**/generated` | Same scratch + generated contract; `force-exclude` so pre-commit filename passes honor it |
| `pyproject.toml` `[tool.ruff.lint.per-file-ignores]` | `E501` on named skill script globs; `E402` on `subagent-generated-data/**` and `environment/agents/generated-data/**` | Intentional long evidence strings; sys.path bootstrap before imports (comments in `pyproject.toml`) |
| `pyproject.toml` `[tool.mypy] exclude` and `[tool.pytest.ini_options] norecursedirs` | same scratch trees | Do not type-check or collect WIP / archived / vendored suites |
| `.github/workflows/l9-lint-test.yml` `lint` / `mypy` | `continue-on-error: true` | Advisory only; pre-existing mypy debt (`TODO.md`); does not gate merge |
| Several workflows `paths-ignore: WIP/**` | WIP-only events skip lint/PE/CodeQL | Scratch corpus; mixed PRs still scan non-WIP paths |
| `ops/scripts/sync_generated_artifacts.py` `GENERATED_PATH_PREFIXES` | generated manifests / llm-rules / skill registries | Overlap-gate exempt; merge driver `l9-generated` |
| `AGENTS.md` §6 | `SEMGREP_APP_TOKEN` / `semgrep login`, `SONAR_TOKEN` | **Not required** for `make pr` |

Ruff `line-length = 100` (`pyproject.toml` `[tool.ruff]`). Pins stay in `AGENTS.md` §6 / `requirements.txt`.

## Refresh

Use skill `l9-update-agent-docs` with adapter [`.claude/adapters/cursor-governance-update-agent-docs.md`](.claude/adapters/cursor-governance-update-agent-docs.md). Keep this file an index. Bump **Version** when an invariant pointer or exclusion citation changes.

<!-- MAX_VELOCITY_INVARIANT_V1 -->
## Maximum velocity (2026-09-10)

Additive index row only. Do not fold the table. A committed `constrained`
Cursor profile, `max_parallel` below 480, or `cursor_default` other than
`maximum_velocity` is a fail-closed regression
(`ops/scripts/validate_max_velocity.py`). Agents fan out independent
research as Tasks (`rules/07-max-velocity-research.mdc`).

<!-- FF_OVERWRITE_UNTRACKED_VELOCITY_V1 -->
## `/ff` overwrite-untracked velocity (2026-09-10)

Additive index row only. Do not fold the table. `_park_overwrite_untracked`
must intersect the index with `origin/main` via `comm -13` (`git ls-files`
vs `git ls-tree`). A per-path `git ls-files --error-unmatch` loop is a
fail-closed regression (`validate_pack_structure.py`). Do not restore
`ls-files --others` — excludesfile misses ignored colliding copies.
