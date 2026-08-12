# WIP — sacred tracked backlog (expanded glorified todo)

This folder is a **first-class, git-tracked design backlog** for Cursor-Governance.
Treat it like an expanded glorified todo list: **tracked, read, and respected**.
It is not disposable scratch, not “ignore me,” and not a second SSOT.

## Purpose

Hold unpromoted design deltas, parked specs, and in-flight packs that agents and
humans must be able to find later. Work here is intentional backlog — keep it
visible in git history until it is promoted or deliberately retired.

## Authority

`WIP/` is **not** live runtime authority. Canonical surfaces remain:

- `environment/`, `skills/`, `ops/`, `kernels/`, `rules/`, `commands/`
- `CANONICAL_LAW.md`, `AGENTS.md`, and related wiring

Do not import or depend on `WIP/` paths from production code, hooks, or CI
entrypoints. Read it for context; promote before execution.

## Git policy

- The **tree is committed**. Do **not** add a blanket `WIP/` entry to `.gitignore`.
- Only credential-shaped filenames under WIP are denylisted (see root `.gitignore`):
  `WIP/*oauth*.json`, `WIP/*credentials*.json`, `WIP/*client_secret*.json`.
- `.DS_Store` and other global ignores still apply.

## CI / scanner policy

WIP is intentionally **never gated** by quality or security scanners. Exclusions
live in each tool’s native config (keep them in sync when adding scanners):

| Surface | How WIP is excluded |
|---|---|
| pre-commit | root `exclude` regex includes `WIP/` |
| ruff / mypy / pytest | `pyproject.toml` exclude / `norecursedirs` |
| gitleaks (`make pr-security`) | `.gitleaks.toml` allowlist + `run_pr_security.sh` prefixes |
| changed-file PR gate | `ops/scripts/resolve_changed_files.sh` scratch prefixes |
| SonarCloud | `sonar.exclusions` + `sonar.cpd.exclusions` |
| CodeQL | `.github/codeql/codeql-config.yml` `paths-ignore` |
| Workflows | `paths-ignore: WIP/**` (skips WIP-*only* events) |
| Conflict-marker tripwire | `l9-lint-test.yml` pathspec `:!**/WIP/**` (needed on **mixed** PRs; `paths-ignore` alone is not enough) |

Draft kernels and duplicate packs here must not fail PR quality gates.

## Agent rules

1. **Read and respect** — open relevant WIP before planning or “cleaning up.”
2. **Do not delete or gitignore** the tree to make status look clean.
2b. **Never park WIP** under `/tmp` or `.l9/scratch-hold/` for `make pr` — WIP is unparkable; the vault is for non-WIP only (`ops/scripts/scratch_hold.py`).
3. **Do not treat paths here as runtime imports** or activation dependencies.
4. **Promote deliberately** — land the live-tree change, then delete the WIP copy
   in the **same** change.
5. **Never commit credential-shaped files** under WIP (oauth / credentials /
   client_secret JSON).

## Layout

```text
WIP/
├── README.md                         ← this file (policy SSOT for the folder)
├── backlog/
│   ├── program-execution/
│   │   └── phase0-autonomy-rail/     ← PE Phase 0 / LL-001–004 (not in live core)
│   ├── plan-schema/
│   │   └── canonical.schema.plan_document.v1.yaml
│   ├── kernels/
│   │   ├── diagnose-first/           ← full kernel; law §11 is distill only
│   │   ├── preflight/                ← not compiled as skills
│   │   └── control-plane-stages/     ← Audit→Release cousins; not Cursor skills
│   └── memory/
│       └── graphiti-memory-integration-waves/
├── Execution Schemas/                ← draft execution contract schemas
├── claude code environment/          ← cloud/mobile Claude pack drafts + receipts
├── out-of-scope-hold/                ← parked items (scripts, schemas, …)
└── quantum_animation_spec_pack_v3/   ← animation system build-spec pack
```

## Deliberately removed (already live or superseded)

| Removed | Why |
|---|---|
| `_program-execution-system-v2.0.0/` (full pack) | Base templates live in `environment/program-execution/core/`; only Phase 0 rail kept |
| `6 Pr Train - CG.md`, `plan.closed_loop_runtime_six_pr.v1.yaml` | Six-PR closed-loop train built |
| `GMP Protocol V1.0 (Full)/` | Superseded by Program Execution; live skill/workflow/rules wiring kept elsewhere |
| `8-4-26/Hydration & Harvesting/` | Superseded by `ops/graphiti/hydration/` |
| Exact `10X Kernels` duplicates | Live under `kernels/` |
| `setup.bootstrap.sh` | Duplicate of `environment/agents/adapters/claude-code/web/setup.bootstrap.sh` |
| `_skills meta script/` | IgorBot `SKILL_META` checker; not CG frontmatter validators |
| `current_work/harvested/` | 2026-03-26 Dropbox archive |
| Disposable prompts / empty stubs | One-shot prompt + empty CLA note |

## Promotion rule

Promote into the live tree with an explicit change; do not treat paths here as
runtime dependencies. When a backlog item lands, delete its WIP copy in the
same change.
