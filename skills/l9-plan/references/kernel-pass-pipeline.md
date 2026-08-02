<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: plan-kernel-hardening-v2.2.0
tags: [plan, kernels, pipeline, validation]
status: active
version: 2.2.0
updated: 2026-08-02
/L9_META -->

# Kernel Pass Pipeline — orchestration SSOT

Mandatory post-draft hardening for **plan** and **spec** modes. This file owns the **exact kernel paths**, **order**, **plan-as-target rule**, **Kernel Pass Log schema**, and **stop rules**.

Skill and `/plan` MUST cite this file. **MUST NOT** duplicate the five path strings elsewhere as a second authoritative list.

## Purpose

After the draft plan/spec is written from the workflow template, **Read and apply** five recursive kernels to the **draft text only**, then emit a Kernel Pass Log. Fail-closed if the log is missing or incomplete.

## Authorized target

- **Modification scope:** the in-progress plan or spec **draft text only**.
- **MUST NOT** modify product/code files, repo config, or any file under `kernels/` from plan/spec mode.
- **Recursive Alignment:** audit claimed file/repo/architecture targets against ground truth; fold findings into Depth / Risks / TODOs / Checkpoints — do not change code.

## Ordered kernel paths (sole path SSOT)

```text
kernels/Improve.md
kernels/Leverage.md
kernels/Recursive Alignment.md
kernels/Recursive Leverage.md
kernels/Validate & Repair.md
```

**Fixed order (non-negotiable):** Improve → Leverage → Recursive Alignment → Recursive Leverage → Validate & Repair.

## Read-apply rules

1. **MUST** `Read` each kernel file before applying (skip re-read only if already loaded this turn).
2. **MUST NOT** paste kernel bodies into the plan, spec, skill docs, or chat as the deliverable.
3. Apply each kernel’s objectives/gates to **revise the draft**; record material deltas in the log.
4. Ticket mode does **not** run this pipeline — see exception below.

## Kernel Pass Log schema (mandatory)

Every ready plan/spec MUST include:

```markdown
### Kernel Pass Log (mandatory)
| Kernel | Path | Status | Material deltas |
|--------|------|--------|-----------------|
| Improve | kernels/Improve.md | Applied \| Blocked | 1–3 deltas **or** `no material delta` |
| Leverage | kernels/Leverage.md | Applied \| Blocked | … |
| Recursive Alignment | kernels/Recursive Alignment.md | Applied \| Blocked | … |
| Recursive Leverage | kernels/Recursive Leverage.md | Applied \| Blocked | … |
| Validate & Repair | kernels/Validate & Repair.md | Applied \| Blocked | … |
```

### Status vocabulary

| Mode | Allowed row statuses |
|------|----------------------|
| plan / spec | `Applied` \| `Blocked` only — **`N/A` forbidden** |
| ticket | Single line: `N/A — ticket mode` (pipeline not run) |

Each `Applied`/`Blocked` row **MUST** include 1–3 material deltas **or** the exact phrase `no material delta`. Empty deltas are invalid.

If `Blocked`, include earliest blocker text in the Material deltas cell.

## Stop rules

1. Missing Kernel Pass Log, wrong row count (≠5 for plan/spec), or invalid status → plan/spec **incomplete**; do not present as ready.
2. On **Blocked**: halt further kernel passes; emit partial log (completed rows + Blocked row); do not claim readiness.
3. Kernel file missing/unreadable → log `Blocked` with path; halt.
4. Fake `Applied` (no deltas and not `no material delta`) → invalid; treat as incomplete.

## Anti-patterns

- Silent skip of any kernel in plan/spec mode
- Duplicating the five path strings as a second SSOT outside this file
- Editing code or `kernels/*` during the pipeline
- Inlining kernel bodies into skill/command docs
- Marking Applied without material deltas or `no material delta`
- Using `N/A` for a kernel row in plan/spec mode

## Ticket-mode exception

Engineering ticket mode (`references/engineering-ticket-template.md`) does **not** run the five-kernel pipeline. Record:

```markdown
### Kernel Pass Log
N/A — ticket mode
```
