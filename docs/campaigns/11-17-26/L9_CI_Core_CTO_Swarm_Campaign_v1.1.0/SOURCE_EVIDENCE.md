# Source observations and revision boundaries (2026-11-17)

GitHub connector read current default-branch files below. `main` URLs denote **observed source**, not immutable proof of the SHA that will run during the campaign. CTO records new exact repository heads and repeats affected comparisons at bootstrap.

## Canonical owners and current files

- Core org CI runtime: https://github.com/Quantum-L9/l9-ci-core/blob/main/.github/workflows/org-ci.yml — PR maps to `pr_fast`, merge-group and default push map to `merge`; `repository_verify` calls Core's pinned composite action; nightly is a manual event class, not a fleet cron. File blob SHA observed `70572c083910c495ef4df303d47aba07f2d1ec03`.
- Core repository execution action: https://github.com/Quantum-L9/l9-ci-core/blob/main/.github/actions/run-repository-verification/run.py — V2 `run_v2` loops `V2_REQUIRED_PHASES` and runs `make setup`, `validate`, `check`, `test` regardless of PR profile. Blob SHA `b489be81346db17280a73fc646ae3abe060023ae`.
- Core change-policy companion requirement: https://github.com/Quantum-L9/l9-ci-core/blob/main/.l9/core-repo-policy.json and https://github.com/Quantum-L9/l9-ci-core/blob/main/tests/repo_execution/test_core_policy.py — `Repo.mk` changes require `tests/repo_execution/`, `AGENTS.md`, and `docs/repository-execution-runtime.md` in **one PR**; workflow changes require `tests/workflows/` in **one PR**. This dictates lanes A and B.
- Retired digest ledger: https://github.com/Quantum-L9/l9-ci-core/blob/main/tools/l9_repo/__main__.py (`manifest_check_enabled` opt-in since 2026-10-20). `MANIFEST.sha256` absent on main; older AGENTS §10 text is stale. Do not reintroduce it just to satisfy historical text.
- Core ABI/contract: https://github.com/Quantum-L9/l9-ci-core/blob/main/tools/l9_repo/contract.py and https://github.com/Quantum-L9/l9-ci-core/blob/main/.l9/repo-workflow.json — exact fixed four-phase declaration, no extra metadata.
- Core local execution leaves: https://github.com/Quantum-L9/l9-ci-core/blob/main/Repo.mk — `repo-test` currently complete `unittest discover` over tests. Blob SHA `cc4dc3c28e4ff1fc75052c3e264368fb290dd952`.
- Core own PR workflow: https://github.com/Quantum-L9/l9-ci-core/blob/main/.github/workflows/self-ci.yml — `Unit tests` currently full discovery and `Repository contract` separately calls full `make test`. Blob SHA `9dd3cbb1af6eb3f7754492275845ebeecf7d39a3`.
- Preserved regression: https://github.com/Quantum-L9/l9-ci-core/blob/main/tests/workflows/test_self_ci_gating.py — currently explicitly expects full discovery and fixed required contexts; must be revised with workflow in B. Blob SHA `827c7c64bfa20de856e51fec2e309984ef41d32c`.
- Preserved parity regression: https://github.com/Quantum-L9/l9-ci-core/blob/main/tests/repo_execution/test_core_self_hosting.py — currently expects `repo-test` to equal legacy full discovery; must be revised with A, while keeping non-test parity.
- Core ruleset payload: https://github.com/Quantum-L9/l9-ci-core/blob/main/docs/release/rulesets/core-main-protection.json — current check names; no mutation in campaign. Blob SHA `caeec4abbf232dd840465e65afcecb7aeaa291f3`.
- Canonical org CI required ruleset source: https://github.com/Quantum-L9/.github/blob/main/rulesets/l9-canonical-ci-required.json — existing `Analyze (central Core)` context and source binding. **This file is not the live GitHub ruleset attestation.**
- Core actual daily governance attestation (not a test runner): https://github.com/Quantum-L9/l9-ci-core/blob/main/.github/workflows/control-plane-attestation.yml — already at 04:17 UTC. Nightly Deep should be separately owned; not mixed with admin-token attestation.
- Core release verification: https://github.com/Quantum-L9/l9-ci-core/blob/main/.github/workflows/release-validation.yml — exact annotated tag checks; preserve.

## CTO swarm and merge rules

- https://github.com/Quantum-L9/Cursor-Governance/blob/main/governance/cto-mode/MODE.yaml — operating protocol v2: fixed pool ≤5, Claude session source `.github`, child role registration and coding-agent mode ACTIVE, child transcript reporting, child PR ownership, CTO-only integration, human grant on merges.
- https://github.com/Quantum-L9/Cursor-Governance/blob/main/commands/lcto.md — activation and `cto_mode.py launch-spec`/`child-prompt` procedure. Do not replace these with pack-generated system prompts.
- https://github.com/Quantum-L9/Cursor-Governance/blob/main/ops/autonomy/merge_gate.py — exact head-scoped merge grant, no child merge, stack-safe ancestry constraints.
- https://github.com/Quantum-L9/Cursor-Governance/blob/main/ops/make/publish.mk — one `make pr` ceremony, route depends on live SSOT; CTO validates full publication prerequisites before issuing command.

## Public access verified through repository metadata

- `https://github.com/Quantum-L9/Gate_SDK` = **public**; runtime Constellation transport SDK, not the central CI analyzer.
- `https://github.com/Quantum-L9/l9-ci-sdk` = **public**; analysis/evidence SDK provisioned by Core.
- `https://github.com/Quantum-L9/.github` = **public**; governed semantic authority/bootstrap source.
- `https://github.com/Quantum-L9/Cursor-Governance` = **private**, still requires host account attachment/authorization.

Public visibility removes anonymous-read barriers but does **not** establish CI ability to access every repo at every SHA, remove historical token config, or permit mutations. The Core org workflow still declares an optional read token; do not change it unless an observed fault demands it.

## Unproven before CTO execution

Current live ruleset settings and merge grants; actual PR workflow timing and test counts; GitHub runner results at current HEAD; native cloud session attachment permissions; future real scheduled run. CTO must distinguish these from observed source code and return explicit UNKNOWN when necessary.

## Recursive-alignment inspection refresh

The following blobs were re-fetched through the GitHub connector while preparing v1.1.0: Core `Repo.mk` `cc4dc3c28e4ff1fc75052c3e264368fb290dd952`; Core `tests/workflows/test_self_ci_gating.py` `827c7c64bfa20de856e51fec2e309984ef41d32c`; Core `tests/repo_execution/test_core_self_hosting.py` `c36acb96a1acb008c5f478d64a13c0309d48f89c`; Core `.l9/core-repo-policy.json` `1b4743a0feb23ae544ecf797bac71149bfc68d7a`; Cursor-Governance `governance/cto-mode/MODE.yaml` `b28cdf36e8b07545eb147ef9b527746b9e85661d`; `.github` `rulesets/l9-canonical-ci-required.json` `96af1beb1ff40617b05072c2a59b9e28df73baaf`. These are **file blob hashes**, not a complete repository `main` commit snapshot.

The relevant CTO operating protocol still contains historic wording calling `.github` private. Current repository metadata recorded it public. Treat the older prose as time-bound operational explanation, not a reason to mutate governance in this pilot. The source-url requirement stays per current executable mode until its owner changes it.

Unverified: complete current repository HEADs, installed live organization rulesets, real Actions runner timings, invocation permissions, and scheduled-run behavior. CTO collects those at execution.
