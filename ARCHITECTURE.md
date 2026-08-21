# Cursor-Governance — architecture index

**Version:** 1.0.0
**Updated:** 2026-08-21
**Role:** this-repo map. Not Program Execution architecture. Not the L9 Coding Control Plane kernel doc.

This file indexes live trees and owners so an agent can find the right SSOT. It does **not** outrank the authority chain. Do not copy CI tables, skill registries, or PE Controller law here — refresh those from the cited files.

## Authority

Highest first. This file is an index, not a rung.

1. [`CANONICAL_LAW.md`](CANONICAL_LAW.md) — constitution
2. [`ops/autonomy/surface_profile.yaml`](ops/autonomy/surface_profile.yaml) — autonomy / L4 / campaign / overlap
3. [`AGENTS.md`](AGENTS.md) — operating instructions
4. `skills/l9-*` — task-scoped procedures

Subsystem architecture stays in its home (cite, do not restated):

- Program Execution — [`environment/program-execution/ARCHITECTURE.md`](environment/program-execution/ARCHITECTURE.md)
- Claude Code gold-standard pack — `environment/agents/adapters/claude-code/`
- Org policy — [`ORG_INVARIANTS.yaml`](ORG_INVARIANTS.yaml) (see also [`INVARIANTS.md`](INVARIANTS.md))

## Module index

Verified on disk 2026-08-21 against the repository root (not recalled from [`README.md`](README.md), which can lag). Supporting/legacy trees exist; treat `CANONICAL_LAW.md` and `skills/*/SKILL.md` as authority over any listing.

| Path | Owns |
|---|---|
| `skills/` | Live `l9-*` skill packs (`SKILL.md` each). Retired packs live in `skills/_archived/`. |
| `commands/` | Slash-command protocols. Map: `commands/COMMANDS_MANIFEST.yaml`. |
| `rules/` | Cursor `.mdc` rules SSOT. Projected peers: `environment/generated/llm-rules/` (do not hand-edit). |
| `ops/hooks/` | `sessionStart` / `sessionEnd` activation. Entry: `ops/hooks/session_start_bootstrap.sh`. |
| `ops/scripts/` | Wiring, backup, validators, publish helpers. Path resolver: `ops/scripts/resolve_governance_paths.sh`. |
| `ops/graphiti/` | Graphiti client + hydration. Policy: `ops/graphiti/MEMORY_BANK_POLICY.md`. |
| `ops/secrets/` | AWS name-inventory + Infisical inventory. Skill: `l9-aws-secrets`. |
| `ops/autonomy/` | Shared autonomy brain (Cursor-primary). Profile: `ops/autonomy/surface_profile.yaml`. |
| `ops/ui-operator/` | SaaS UI console (explicit-only). |
| `ops/config/` | Gate contracts, including [`ops/config/root-file-protection.json`](ops/config/root-file-protection.json). |
| `environment/contracts/` | First-class execution / autonomy contracts and the executable-plan template. |
| `environment/ide/` | Editor profile (`policy.json`). |
| `environment/program-execution/` | Program Execution System. Architecture SSOT is the file linked above. |
| `environment/agents/adapters/` | Thin surface adapters (`claude-code`, `codex`, `gemini`, `manus`). Cursor-primary owns shared capability (`CANONICAL_LAW.md` §2.1). |
| `autonomy/` | Provider-neutral autonomy runtime (subordinate to PE Controller; `owns_program_state: false`). |
| `learning/` | Curated lessons / failures. Resume SSOT is Graphiti, not this tree. |
| `docs/plans/` | Machine-global Cursor plans store (via `~/.cursor/plans`). |
| `kernels/` | Recursive Alignment / Validate & Repair and related kernels. Cite by path; do not land KERNEL packs on an unrelated dirty branch. |
| `WIP/` | Dated scratch corpus on `main`. Pre-commit and CI `paths-ignore` treat it as non-gating. |

Root agent-doc surface (this change): `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `ORG_INVARIANTS.yaml`, this file, [`INVARIANTS.md`](INVARIANTS.md).

## CI/CD architecture

Local publish path (authoritative procedure): [`AGENTS.md`](AGENTS.md) §4–6.

```text
make pr-check          quality only (changed-files pre-commit + locked ruff / security / pytest)
PR_REMEDIATE=0 make pr  sole path to GitHub (gate + open_pr_after_gate.sh)
```

There is no git commit hook. Do not run `pre-commit install`. Live hook list and toolchain pins stay in `AGENTS.md` §4–6 and [`.pre-commit-config.yaml`](.pre-commit-config.yaml).

### Workflow map (14 files under `.github/workflows/`)

Index only. Job tables and pin versions live in the workflow files and `AGENTS.md`.

**PR-triggered workflow callers** (these files run on pull_request; they are not automatically required merge checks — required contexts are branch-protection names, not this index):

- `l9-lint-test.yml` — jobs `scope`, `lint`, `test`
- `governance-self-check.yml` — job `governance-self-check`
- `root-file-protection.yml` — job `append-only`
- `validate-org-policy.yml` — job `validate-org-policy`
- `peer-execution.yml` — job `peer-execution`
- `repo-hygiene.yml` — job `repo-hygiene`
- `governance.yml` — jobs `pr`, `issue`
- `supply-chain.yml` — jobs `license-compliance`, `dependency-review`, `cyclonedx-sbom`
- `codeql.yml` — job `codeql` (calls `codeql-reusable.yml`)

**Not a PR merge gate** (schedule, dispatch, or post-merge janitor):

- `lint-autofix.yml` — `push` to `main` + `workflow_dispatch` only
- `branch-hygiene.yml` — schedule / dispatch
- `memory-distill.yml` — schedule / dispatch
- `on-org-update.yml` — `repository_dispatch` / dispatch
- `codeql-reusable.yml` — `workflow_call` only (not a standalone trigger)

### Verified exclusions (do not treat as silent skips)

- `l9-lint-test.yml` `lint` / `mypy` step: `continue-on-error: true` (advisory; see that file’s comment and `TODO.md` mypy debt).
- Several PR workflows `paths-ignore: WIP/**`. CodeQL PRs also ignore `**/*.md`, `docs/**`, `**/*.mdc`.
- Pre-commit global `exclude` and ruff/mypy excludes: see [`INVARIANTS.md`](INVARIANTS.md) false positives.

Hook count at write time: **15** hooks in `.pre-commit-config.yaml` (5 `pre-commit-hooks` + 8 local + 2 ruff). Recount from that file on refresh.

## Refresh

Use skill `l9-update-agent-docs` with adapter [`.claude/adapters/cursor-governance-update-agent-docs.md`](.claude/adapters/cursor-governance-update-agent-docs.md). Keep this file a pointer index. Bump **Version** when the module list or workflow map changes.
