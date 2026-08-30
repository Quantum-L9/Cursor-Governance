---
name: Absorb plan-audit
overview: Retire live skill l9-plan-audit by absorbing its plans scanner into l9-pipeline-audit so plans, WIP, and PE campaigns are one family. SessionStart NEXT 1-3 may name a WIP row. Unwire the old pack. Do not harvest or rewrite AGENTS.md in place.
todos:
  - id: T1
    content: git mv scanner + harvest + staleness-rules + self_test into l9-pipeline-audit; retarget imports
    status: completed
  - id: T2
    content: "rank_next: one slot per surface (plans, wip, campaigns); self_test NEXT includes compiled plan and note.md"
    status: completed
  - id: T3
    content: Retarget SKILL.md and slash commands so they do not name l9-plan-audit as live
    status: completed
  - id: T4
    content: Unwire l9-plan-audit to skills/_archived/; AUTONOMY + sync_generated_artifacts
    status: completed
  - id: T5
    content: Append AGENTS.md fragment + conftest ignore; update rules/02-slash-commands.mdc
    status: completed
  - id: T6
    content: Prove self_test, built-shelf pytest, no live pack, make pr-check; pathspecs only
    status: completed
isProject: false
kernel_pass:
  bound_path: absorb_plan-audit_b1986598.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-30T02:30:00Z
    body_sha256: "fb897f17583524af74b8ec1a3cf99e326b0ae19340e8893e921f45ea93ca1c7e"
    deltas:
      - "Applied Improve.md on /ff shelf: leftover untracked corpus kept as archive; no promotion into live skills or ops."
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-08-30T02:30:20Z
    body_sha256: "fb897f17583524af74b8ec1a3cf99e326b0ae19340e8893e921f45ea93ca1c7e"
    deltas:
      - "Applied Recursive Alignment.md: shelf is WIP/plans leftover after catch-up; does not compete with CANONICAL_LAW or AGENTS.md."
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-30T02:30:40Z
    body_sha256: "fb897f17583524af74b8ec1a3cf99e326b0ae19340e8893e921f45ea93ca1c7e"
    deltas:
      - "Applied Validate & Repair.md: secret globs excluded; copies stay in the named clone; no fabricated completeness."
---
# Absorb plan-audit into pipeline-audit

The `/l9-plan-simple` deliverable is already on disk (not in this Plan-mode card):

- [docs/plans/absorb_plan_audit_into_pipeline_76840ee8.plan.md](docs/plans/absorb_plan_audit_into_pipeline_76840ee8.plan.md)
- [docs/plans/absorb_plan_audit_into_pipeline_76840ee8.plan.json](docs/plans/absorb_plan_audit_into_pipeline_76840ee8.plan.json)

Committed locally as `eacfc756` on `main`. Open that `.plan.md` in the plans store (`.cursor/plans` → `docs/plans/`).

## Why

SessionStart already runs `audit_pipeline.py --format session-start`. That CLI **imports** `l9-plan-audit` `audit_plans.py`, then **skips** every WIP row in `rank_next`. Two skills wrap the same live-queue job.

## Locked contracts

- **One scanner:** `git mv` `audit_plans.py` + `harvest_plan_invariants.py` + `staleness-rules.md` into [skills/l9-pipeline-audit/scripts/](skills/l9-pipeline-audit/scripts/). Point [audit_pipeline.py](skills/l9-pipeline-audit/scripts/audit_pipeline.py) imports at the same directory (today: `parents[2] / "l9-plan-audit" / "scripts"`).
- **Family NEXT:** Pass 1 takes one candidate per surface in order plans, wip, campaigns. Within plans: compiled then README live-queue then other unbuilt. Within WIP: harvestable then pending-active (not landed). Within campaigns: pending then harvestable. Pass 2 fills leftovers. Cap 3. This stops 178 WIP rows from consuming all three slots.
- **Unwire:** archive to `skills/_archived/l9-plan-audit/` with `superseded_by: l9-pipeline-audit`. Follow [skills/l9-wire-skill-into-repo/references/unwire-deprecate.md](skills/l9-wire-skill-into-repo/references/unwire-deprecate.md). Never leave deprecated-in-place under live `skills/`.
- **Append-only:** [AGENTS.md](AGENTS.md) and [conftest.py](conftest.py) gain lines only. Heading stays `### Plan audit`. No auto-Build. No `make campaign`.
- **Isolation:** do not stage foreign plan dirt already on this checkout (`docs/plans/` deletions + untracked `built/` copies).

```mermaid
flowchart TD
  T1[T1 absorb scanner]
  T2[T2 family rank_next]
  T3[T3 live docs and commands]
  T4[T4 unwire l9-plan-audit]
  T5[T5 AGENTS conftest append]
  T6[T6 prove]
  T1 --> T2
  T1 --> T3
  T2 --> T4
  T3 --> T4
  T4 --> T5
  T5 --> T6
  T2 --> T6
```

**C1 stop:** after T1, if `audit_pipeline.py` cannot import `audit_plans` from the pipeline scripts dir, do not unwire.

**C2 stop:** after T2, if pipeline `self_test.py` NEXT omits `note.md`, do not unwire with WIP still skipped.

## Prove

- `.venv/bin/python skills/l9-pipeline-audit/scripts/self_test.py` PASS (NEXT includes compiled plan and `note.md`)
- `pytest tests/ops/scripts/test_pipeline_audit_built_shelf.py` PASS
- `test ! -d skills/l9-plan-audit`
- `make pr-check` on this envelope
