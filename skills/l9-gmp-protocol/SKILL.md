---
name: l9-gmp-protocol
description: execute deterministic repo changes through locked gmp phases 0-6 with a modification lock and a signed evidence report. use when a change must be traceable and drift-free — adding/refactoring/fixing modules, gated edits, or any task that needs a locked todo plan, phase-by-phase execution, and an evidence report in reports/.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, gmp, deterministic, phases, evidence, modification_lock, governance]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-08-28
---

# GMP Protocol — Deterministic Phased Execution

## Purpose

Execute any repo change as a locked, traceable, drift-free run: lock a TODO plan, confirm ground truth, implement only the locked scope, validate, verify against the plan, and sign an evidence report. Source of truth: `docs/gmp_protocol/`.

Use this skill when a change must be auditable and reversible, not when a one-line edit needs no ceremony.

## Runtime authority

Slash `/gmp` is authorization. Invocation is the locked-venv wizard at
`workflows/gmp_executor.py` (`--authorized-by slash-gmp`). See `commands/gmp.md`.
The LangGraph package under `workflows/dags/gmp/` remains a TTY/graph runtime;
the slash does not invoke it and this skill does not rewrite it.

```
workflows/gmp_executor.py         # slash start / finalize / full (authorized mode)
workflows/dags/gmp/graph.py       # TTY LangGraph state machine (not the slash)
workflows/dags/gmp/executor.py    # GMPLangGraphExecutor + CLI
```

## Ownership boundary

Owns:

- when GMP is required, and when a change is too small to earn it
- the execution authority boundary and the modification/scope lock semantics
- evidence requirements and the signed report contract
- terminal and failure semantics for a run

Does not own:

- generic DAG construction, registration, or discovery -> `l9-dag-authoring`
- command generation or thin command-to-DAG binding -> `l9-dag-authoring`
- Skill compilation -> `l9-skill-compiler`; Skill wiring -> `l9-wire-skill-into-repo`
- generic component audit / verify / probe -> `l9-component-verification`
- git publication, merge, or release authority -> the publish path rules

GMP uses a DAG. That does not make GMP a DAG-authoring capability, and it does
not make the DAG a second Skill.

## Core Contract

`ROLE → MODIFICATION LOCK → CONSTRAINTS → PHASES 0–6 → FINAL DECLARATION`

Three non-negotiables:

1. **Plan locks scope** — Phase 0 produces a deterministic TODO plan before any file is touched.
2. **Phases control execution** — 0→6 in order; a phase that cannot mark its checks with evidence STOPS the run.
3. **Evidence is mandatory** — every run ends with a signed report in `reports/` carrying the verbatim final declaration.

## Authority Order

Resolve every conflict top-down. Lower sources never override higher ones.

1. Explicit user request and the approved/locked TODO plan.
2. Verified repo ground truth — actual files, classes, signatures, and existing conventions in this repo.
3. Repo invariants and guardrails — CI gates, protected paths, `.cursor/rules/*.mdc`, `AGENTS.md`.
4. Canonical GMP protocol in `docs/gmp_protocol/`.
5. Inferred best practice — only when directly supported by the above.
6. `Unknown` — label it and stop rather than invent.

Because ground truth (2) outranks the canonical docs (4), follow the repo's actual conventions when a doc disagrees with observed repo state.

## Compact Workflow

1. **Phase 0 — Plan lock.** Establish ground truth (verify real paths, classes, signatures from this repo). Read relevant ADRs (`.cursor/rules/*.mdc`, `docs/adr/`). Emit a locked TODO plan: each TODO has `id`, `phase`, `file`, `operation` (Insert|Replace|Delete|Wrap|Create), `anchor` (line or unique string), `description`, `dependencies`. No placeholders, no "maybe". Declare the modification lock (may-modify / must-not-modify). When Graphiti is enabled, run `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py conflicts` and declare `MEMORY_PREFETCH: <episode names>`.
2. **Phase 1 — Baseline.** For each TODO confirm file exists, anchor resolves uniquely, no protected path is targeted, dependency chain is acyclic. Status: READY | PARTIAL | BLOCKED. Proceed only on READY (or explicit human override).
3. **Phase 2 — Implement.** Apply only READY TODOs, line-anchored and minimal. No edits outside the locked plan. Keep imports/standards intact. Record file + line ranges per TODO.
4. **Phase 3 — Enforce.** Add only the guards/tests/ACL/observability the TODO requires. Never weaken existing checks. Skip cleanly if the change needs none.
5. **Phase 4 — Validate.** Run the repo gates that apply: `make pr` (lint, XML, wiring, circular deps, Odoo 19 patterns), `python -m py_compile`, targeted tests. Record pass/fail; failures block.
6. **Phase 5 — Recursive verify.** Diff actual changes against the locked plan: only planned files changed, line ranges match, protected systems untouched, no scope creep. Status: VERIFIED | DISCREPANCY_FOUND.
7. **Phase 6 — Finalize.** Write the evidence report to `reports/GMP-Report-{NNN}-{slug}.md` and end with the verbatim final declaration.

Load `references/phase-contracts.md` for the per-phase input/output contract.

## Behavior Rules

- Fail loudly. No silent partial success. If a checklist item cannot be marked with evidence, STOP and report the exact gap.
- If the request is ambiguous or ground truth is missing, STOP at Phase 0 and ask — do not guess paths, classes, or behavior.
- Production-grade only: no stubs, pseudo-code, or "you'll need to tweak". Drop-in usable.
- Scope discipline: deliver only what was requested; no unsolicited refactors, summaries, or helper files.
- A change that would require violating the modification lock must fail at Phase 0 and request a revised plan with explicit permission.
- Respect repo guardrails (see `references/modification-lock.md`): `pipeline_v2.py` is never activated; new models need ACL; `sudo()` needs inline justification. Skill implement does not publish. `/gmp` finalize publishes via `PR_REMEDIATE=1 make pr`.

## Resource Map

- `references/phase-contracts.md` — compressed per-phase (0–6) input/output/exit contracts.
- `references/modification-lock.md` — constraints, modification-lock semantics, protected paths, and the three evidence-validation categories.
- `references/evidence-report.md` — the signed report contract (sections, numbering, final declaration) with the PlasticOS report shape.
- `references/pipeline-composition.md` — multi-step pipeline YAML, stage failure policy, parallel groups, rollback triggers.
- `references/lifecycle-pipelines.md` — Discover / Build / Ship / Check lifecycle, PlasticOS make mapping, decision tree.
- `references/gmp-autonomy-bounds.md` — GMP packet, L4, remediates=1, host_bridge then serialize; no PE Controller.
- `commands/gmp.md` — slash trigger SSOT (`/gmp` is authorization; last steps Shell the executor then Build).
- `docs/gmp_protocol/` — canonical long-form source: `cursor-gmp-canonical.md` plus `cursor-phase-0..6-*.md` and `gmp-report-template.md`.
- `workflows/dags/gmp/` — TTY LangGraph package; not the `/gmp` slash runtime.

Slash invocation (locked interpreter, no `/usr/bin/python3` fallback):

```bash
GOV_PY="${HOME}/.cursor-governance/.venv/bin/python"
test -x "$GOV_PY" || GOV_PY="$(pwd)/.venv/bin/python"
"$GOV_PY" workflows/gmp_executor.py --authorized-by slash-gmp --plan <plan.md> --mode start --tier RUNTIME "<task>"
```

When `/gmp` invoked the run, do not ask. USER_GATE is skipped. See `commands/gmp.md`.

## Validation Requirements

A GMP run is complete only when:

- Phase 0 plan is locked, fully specified, and unambiguous.
- Baseline reported READY (or documented override) before any implementation.
- Only locked-plan files were modified (Phase 5 VERIFIED, no drift).
- Applicable repo gates passed (`make pr` / py_compile / targeted tests).
- Evidence report exists in `reports/` with all required sections and the verbatim final declaration.

## Failure Handling

When blocked: state the exact blocker, label missing/unverifiable inputs as `Unknown`, do not fabricate paths or results, and give the smallest safe next action. Never present a run as complete if any phase lacks evidence.

Slash trigger SSOT is `commands/gmp.md`. Do not paste that command body here.
