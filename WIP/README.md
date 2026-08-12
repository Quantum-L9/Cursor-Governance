# WIP — active backlog only

This folder holds **unpromoted design deltas** for Cursor-Governance.
It is not a second SSOT. Live authority stays under `environment/`, `skills/`,
`ops/`, `kernels/`, and related wiring.

## Layout

```text
WIP/
├── README.md                          ← this file
└── backlog/
    ├── program-execution/
    │   └── phase0-autonomy-rail/      ← PE Phase 0 / LL-001–004 (not in live core)
    ├── plan-schema/
    │   └── canonical.schema.plan_document.v1.yaml
    ├── kernels/
    │   ├── diagnose-first/            ← full kernel; law §11 is distill only
    │   ├── preflight/                 ← not compiled as skills
    │   └── control-plane-stages/      ← Audit→Release cousins; not Cursor skills
    └── memory/
        └── graphiti-memory-integration-waves/  ← cross-repo wave notes
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
