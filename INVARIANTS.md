# Cursor-Governance — invariants index

**Version:** 1.1.0
**Updated:** 2026-09-04
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
| Secret values never in git, logs, receipts, or chat | `AGENTS.md` §8; `ops/secrets/` |
| Root files are classified; new root files must be registered; `additive_only` files are append-only | `AGENTS.md` §14; [`ops/config/root-file-protection.json`](ops/config/root-file-protection.json) |
| One mutating agent per worktree; stage explicit pathspecs only | `AGENTS.md` + `rules/49-shared-worktree-isolation.mdc` |
| Org repository birth under `Quantum-L9` | `ORG_INVARIANTS.yaml` `invariants:`; `docs/governance/ORG_INVARIANTS.md` |
| Tests run once locally (same worktree digest + `PR_BASE`); full corpus is `make pr-full` / nightly / push-to-`main` | `AGENTS.md` `TESTS_ONCE_AND_PUBLISH_V1`; `CANONICAL_LAW.md` §6.2.5 |
| Commit finished work when done, then `make pr` (remediates=1; `PR_REMEDIATE=0` opt-out) | `AGENTS.md` `TESTS_ONCE_AND_PUBLISH_V1`; `rules/48-make-pr-remediation.mdc` |
| `pr-check` is the INTERNAL gate leaf of `make pr`; Diagnose is `OPEN_PR=0 make pr`; do not run `pr-check` after `precommit-repo` | `AGENTS.md` `PR_CHECK_FOLDED_V1`; `rules/48-make-pr-remediation.mdc` |
| Repository documentation closure is obligation-based: a receipt may be `PASS` only when every applicable `DocumentationObligation` is terminal and its required validation is evidenced; any required non-terminal obligation remains `PARTIAL`, and a blocked obligation yields `BLOCKED` | `skills/l9-update-agent-docs/contracts/documentation-obligation.schema.json`; `skills/l9-update-agent-docs/scripts/doc_obligations.py` |
| Semantic documentation obligations require admitted, change-bound `l9-intelligence-harvest` evidence; the Harvest input must bind the evaluated repository, required surfaces, and semantic source digest before it may qualify an obligation | `skills/l9-update-agent-docs/scripts/repo_docs.py`; `skills/l9-update-agent-docs/scripts/compile_semantic_obligations.py` |

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