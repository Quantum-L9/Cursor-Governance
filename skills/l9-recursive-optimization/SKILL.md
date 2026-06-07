---
name: l9-recursive-optimization
description: recursively align, improve, and converge artifact groups, packs, prompts, plans, and agent outputs until complete and execution-ready. use when hardening l9 packs, auditing contract compliance, improving prompts or skill packs, or when recursive alignment, recursive improvement, or recursive optimization is requested.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, recursive, alignment, improvement, optimization, convergence, audit, hardening]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-07
sources:
  - Recursive Alignment.md
  - Recursive Improvement.md
---

# Recursive Optimization

## Purpose

Recursively align, improve, and converge artifact groups until they are complete, contract-compliant, enforceable, and directly usable — without inventing requirements or implementing code unless explicitly requested.

## Core Contract

| Mode | Action | Implements | Load |
|------|--------|------------|------|
| **align** | Read-only audit vs active contract | Recursive Alignment | [alignment-protocol.md](references/alignment-protocol.md) |
| **improve** | Transform artifacts in place | Recursive Improvement | [improvement-protocol.md](references/improvement-protocol.md) |
| **optimize** (default) | Align → improve gaps → converge | Both protocols | [mode-routing.md](references/mode-routing.md) + both protocol refs |

**Align** reports violations; it does not rewrite source. **Improve** rewrites artifacts while preserving intent. **Optimize** runs alignment first, improves material gaps, then re-aligns until convergence.

## Inputs

| Field | Required | Notes |
|-------|----------|-------|
| artifact group | yes | Files, folder, pack, or pasted content |
| mode | no | `align` \| `improve` \| `optimize` (default) |
| persist | no | `report` (default) = revised content in response only; `apply` = write changes to disk |

## Authority Order

1. Explicit user instruction (mode, scope, persist-or-report).
2. Provided artifact group as primary source of truth.
3. Active architecture contract — L9 rules when applicable; workspace rules (`AGENTS.md`, `INVARIANTS.md`, module rules) in PlasticOS repos.
4. This skill's references.
5. `Unknown` — label; do not invent.

## Operating Rules

1. **Mode routing** — infer from user language; default `optimize`. Load [mode-routing.md](references/mode-routing.md).
2. **Preserve intent** — scope, required outputs, interfaces, and architecture boundaries MUST NOT drift.
3. **L9 context when relevant** — TransportPacket, Gate-only egress, authority boundaries. Load [l9-context-rules.md](references/l9-context-rules.md).
4. **No silent behavior change** — improvement mode MUST NOT weaken constraints or add unrequested scope.
5. **Persist boundary** — improve/optimize MAY rewrite artifacts in the response; write to disk only when `persist=apply` or user explicitly requests file changes. Audits and deltas default to report-only.
6. **Cycle bound** — max 3 align→improve cycles per invocation; then deliver with `partial` or `blocked` if not converged.
7. **Convergence required** — every delivery ends with a convergence block. Load [convergence-block.md](references/convergence-block.md).
8. **Output shape** — alignment → report; improvement → revised artifact group; optimize → delta report + revised sections when gaps fixed. Load [output-contracts.md](references/output-contracts.md).

## Compact Workflow

```text
Route mode → Lock context (pass 1) → Run alignment and/or improvement passes (1–10)
→ Validation gates → Convergence check → Re-run if material improvement remains (max 3 cycles)
→ Deliver delta + output contract + convergence block
```

### Optimize sequence (default)

```text
Context lock → Alignment passes 1–10 → Violation report
→ Improvement passes 1–10 on gaps → Re-align critical/high
→ Convergence → Deliver (max 3 cycles)
```

When artifact is a skill pack, also align against `l9-skill-compiler` [skill-pack-contract.md](../l9-skill-compiler/references/skill-pack-contract.md).

## Resource Map

Load references only when relevant:

- [references/mode-routing.md](references/mode-routing.md) — align vs improve vs optimize; trigger phrases
- [references/alignment-protocol.md](references/alignment-protocol.md) — 10 alignment passes, violation format, correction roadmap
- [references/improvement-protocol.md](references/improvement-protocol.md) — 10 improvement passes, hard rules, validation gates
- [references/l9-context-rules.md](references/l9-context-rules.md) — L9 non-negotiables when artifact touches nodes/Gate/transport
- [references/convergence-block.md](references/convergence-block.md) — required convergence fields per mode
- [references/output-contracts.md](references/output-contracts.md) — alignment report vs improved pack deliverables
- [references/generic-artifact-passes.md](references/generic-artifact-passes.md) — coverage, provenance, compression (non-L9 artifacts)
- [references/validation-checklist.md](references/validation-checklist.md) — fail-closed gates before delivery

## Validation

Run [validation-checklist.md](references/validation-checklist.md) before delivery. Alignment mode MUST NOT claim convergence if critical violations remain unaddressed. Improvement mode MUST return complete revised artifact group when pack-based.

## Failure Handling

- No artifact group provided → STOP; ask for files, folder, or pasted content.
- Mode ambiguous and stakes high → ask one focused question; else default `optimize`.
- Convergence blocked by missing source → halt with blocker; label `Unknown`.
- User asked align-only but expects rewritten files → clarify mode; do not silently improve.

## Daisy-chain

| Downstream | When |
|------------|------|
| `l9-skill-compiler` | User wants violations fixed by rebuilding a skill pack |
| `l9-gmp-protocol` | Corrections require phased, locked repo execution |
| `l9-ynp` | After report; single highest-leverage next action |
