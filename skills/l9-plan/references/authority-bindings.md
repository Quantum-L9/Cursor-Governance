<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: planning-playbook-v3
tags: [plan, playbook, bindings, fixtures]
status: active
version: 3.0.0
updated: 2026-08-02
/L9_META -->

# Planning playbook — authority bindings

Load map for `/plan` and skill `l9-plan`. **Wrap/call** permanent fixtures. **MUST NOT** paste fixture bodies into plans or into this skill pack.

**Repo doctrine (always-on):** `rules/46-wrap-call-existing-authority.mdc` — never harvest concepts from living fixtures into a distillate fork; Load / Read / apply the SSOT. This file is the canonical Load-map shape for that rule.

Agents **MUST** `Read` each required fixture before filling the bound plan section. Record Reads in the plan’s **Load log**. Fail-closed if a required Read is skipped.

Kernel paths for the five-kernel pipeline remain sole SSOT in [kernel-pass-pipeline.md](kernel-pass-pipeline.md).

---

## A. Always Load (every plan / spec)

| Plan section / stage | Load / Read | Apply |
|----------------------|-------------|-------|
| Doctrine / Gather | Skill Doctrine; `learning/failures/repeated-mistakes.md` (+ `learning/patterns/quick-fixes.md` if present) | Lesson matches or `None matched` |
| Files in/out of scope; Plan DoD; assumptions; critical path; acceptance | `kernels/L9 Coding Control Plane/ai-control-plane/PLAN.md` | Path/glob tables; plan quality gates; no invented paths |
| Post-implementation DoD (named gates) | `kernels/L9 Coding Control Plane/ai-control-plane/DEFINITION_OF_DONE.md` | Name gates for handoff — do not mark Passed at plan time |
| Adaptive depth (Planning Mode) | [ccp-plan-patterns.md](ccp-plan-patterns.md) → points at CCP PLAN | Mode + justification |
| Kernel Pass Log | [kernel-pass-pipeline.md](kernel-pass-pipeline.md) then five kernels | Draft-only hardening |
| MSNA / auto-chain | skill `l9-ynp` / `/ynp` | Exactly one next action |
| Memory (when Graphiti healthy) | skill `l9-graphiti-memory` + [references/authority-bindings.md](../../l9-graphiti-memory/references/authority-bindings.md); timing [read-write-timing.md](../../l9-graphiti-memory/references/read-write-timing.md); `ops/graphiti/graphiti_memory_client.py`; `rules/03-graphiti-memory.mdc` | Prefetch / search before gather explore; conflicts on Gather |
| Authority | `AGENTS.md`; applicable `.cursor/rules/*.mdc` | Conflict resolution |

---

## B. Always Load when handoff = CHANGE / tracked implementation

| Plan section | Load / Read | Apply |
|--------------|-------------|-------|
| Modification Lock; Constraints (lock rules) | `skills/l9-gmp-protocol/references/modification-lock.md` | may-modify / must-not-modify; evidence categories |
| TODO schema; baseline READY; Phase 5 verify-against-lock | `skills/l9-gmp-protocol/references/phase-contracts.md` | Phase-0 fields; implementer preflight; post-impl verify expectations |
| Evidence artifact name | `skills/l9-gmp-protocol/references/evidence-report.md` | Handoff only — implementer writes under GMP |
| Waves / parallel mutate | `skills/l9-gmp-protocol/references/pipeline-composition.md` | No parallel mutating steps unless independent |
| GMP mindset | `skills/l9-gmp-protocol/SKILL.md` | Fail loudly; planning ≠ execution |
| Guardrails awareness | `rules/80-gmp-execution.mdc`, `rules/81-gmp-audit.mdc`, `rules/83-gmp-contracts.mdc` | Do not violate; do not edit rules from `/plan` |

---

## C. Conditional Load (by trigger)

| Trigger | Load | Use |
|---------|------|-----|
| Unclear architecture / options | `skills/l9-structured-reasoning` + `/reasoning` | Depth / Decisions |
| Readiness vs target | `skills/l9-gap-analysis` + `/gap-analysis` | Pre-Validate evidence |
| Unfamiliar codebase | `skills/l9-code-analysis` + `/analyze` | Inventory / hotspots |
| External import | `skills/l9-inspect` + `/inspect` | Out-of-repo gate |
| Security-sensitive | `skills/l9-auditing-security` | Escalate Planning Mode; Constraints |
| Performance-sensitive | `skills/l9-auditing-performance` | Validation matrix |
| Library/API unknowns | `skills/l9-context7-docs`; `rules/22-context7-auto-invoke.mdc` | Gather |
| PlasticOS cross-module | `skills/l9-code-graph-rag-mcp` | CODE_GRAPH_BASELINE or SKIPPED |
| Design decision | `skills/l9-architecture-decision-records` | ADRs consulted / Decision register |
| Multi-artifact harden (optional) | `skills/l9-recursive-optimization` | After kernel pipeline if needed |
| Spec mode | [spec-workflow.md](spec-workflow.md) + `/spec` | Spec shells |
| Fast batch handoff | `skills/l9-forge` + `/forge` | Handoff profile |
| PR already open | `skills/l9-pr-analysis` + `/pr` | Baseline blockers |
| Parallel agents | `skills/l9-bounded-autonomy` + `/autonomy` | Waves / lease awareness only |
| Component ladder | `/probe`, `/audit-component`, `/verify-component` | Validation matrix |
| Repo map | `skills/l9-repo-index` + `/index` | Inspection discovery |
| Skill/command authoring | `l9-skill-compiler`, `/update-command` | When target is skills/commands |
| CI/setup | `l9-setting-up-ci`, `/ci` | Release-mode plans |
| Key-component concepts | `key components/*` (provenance only) | Conditional sections already in workflow — no CLIs |

---

## D. Profiles (Deep / Release only)

| Profile | Path | Use |
|---------|------|-----|
| YNP mode | `profiles/ynp_mode.md` | MSNA quality |
| Reasoning packs | `profiles/reasoning_*.md` | When `/reasoning` chained |
| Workflow governance | `profiles/workflow-governance.md` | Process constraints |
| Session startup | `profiles/session-startup-protocol.md` | Cold session bind |
| Orchestrator | `profiles/orchestrator.md` | Multi-workstream |

Quick/Standard: **MUST NOT** require loading all profiles.

---

## E. Optional Deep GMP wording

| Fixture | Path | Use |
|---------|------|-----|
| GMP Action Prompt | `protocols/GMP-Action-Prompt-Canonical-v1.0.md` | Align language if plan is GMP-bound |

---

## F. Forbid — do not Load into `/plan` (wrong stage)

| Fixture | Why |
|---------|-----|
| GMP Phases 2–6 / `/gmp` DAG executor | Execution |
| `/forge` implementation body | Execution |
| `/end-session`, backup hooks | Session close |
| Release/deploy as executors | After Done |
| `WIP/10X Kernels/**` | Non-SSOT; use CCP `ai-control-plane` |
| Pasting fixture catalogs into `ccp-plan-patterns.md` or the plan draft | Drift |

---

## Anti-patterns

- Skipping a required Read and inventing lock/DoD/Phase-0 rules
- Treating implementation-ready as merge/release-ready
- Editing files under `skills/l9-gmp-protocol/` or `kernels/` from plan mode
- Binding playbook sections to WIP paths
