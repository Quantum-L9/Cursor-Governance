---
name: l9-structured-reasoning
description: structured multi-modal reasoning for planning, plan analysis, architecture decisions, and debugging. use when decomposing complex tasks, evaluating trade-offs, root cause analysis, pre-implementation verification, reviewing proposed plans, or when the user asks for deep reasoning, strategy, or decision support.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, reasoning, planning, architecture, debugging, analysis, leverage, confidence]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-06-06
sources:
  - 01_reasoning_engine.kernel.yaml
  - 02_intelligence_analysis_engine.kernel.yaml
  - 07_reasoning_engine_extended.kernel.yaml
  - l9_first_order_thinking_enforcement.kernel.yaml
  - reasoning_think_strategy.kernel.yaml
---

# Structured Reasoning

## Purpose

Apply disciplined, visible reasoning before and during non-trivial work: planning, analyzing plans, architecture decisions, and debugging. Surface highest-leverage paths, quantify trade-offs, and state confidence explicitly.

## Core Contract

| Task type | Preflight | Mode | Analysis | Extra ref |
|-----------|-----------|------|----------|-----------|
| Planning | Required | Strategic + ADI | Dependency | B9 plan + ToTh if high-stakes |
| Plan review | Required | Deductive + Comparative | Comprehensive | Effort/coverage ratio |
| Architecture | Required | Strategic + Deep | Dependency + Performance | ≥2 alternatives |
| Debugging | Required | Deep + Abductive | Rapid → Deep | Disconfirming evidence |
| Multi-modal summary | Optional | Abductive/Deductive/Inductive | — | [reasoning-command-workflow.md](references/reasoning-command-workflow.md) |

Skip for trivial one-line fixes with no trade-offs.

## Authority Order

1. Explicit user instruction
2. Workspace invariants (`AGENTS.md`, `INVARIANTS.md`, module rules)
3. This skill's operating rules and references
4. Domain-specific skills loaded after this one

## Operating Rules

1. **First-order preflight first** — run five leverage gates silently; surface failures before artifacts. Load [first-order-gates.md](references/first-order-gates.md).
2. **Verify before asserting** — read workspace state with tools; do not answer from memory when evidence is available.
3. **Visible reasoning** — no black-box conclusions; show logic, assumptions, trade-offs.
4. **Mode routing** — strategic / rapid / deep / creative or ADI per [reasoning-modes.md](references/reasoning-modes.md).
5. **Block protocol** — blocks 0–7 in order; Block 5 gate must pass before irreversible execution. Load [reasoning-protocol.md](references/reasoning-protocol.md).
6. **Analysis depth** — match mode to question per [analysis-modes.md](references/analysis-modes.md).
7. **Confidence required** — state confidence on every non-trivial recommendation. Load [confidence-and-contingency.md](references/confidence-and-contingency.md).
8. **Fail closed** — confidence below threshold or gate failure → halt, surface blocker, request confirmation.

Folded techniques: [systematic-debugging.md](references/systematic-debugging.md), [best-of-n-parallel.md](references/best-of-n-parallel.md).

## Compact Workflow

```text
Preflight (5 gates) → Complexity (Block 0) → Objective → Context → Decompose → Leverage
→ Strategy (5A/5B/5C) → Pre-action gate (moderate+) → Execute (visible) → Synthesize
→ Anticipate-and-Deliver → Confidence → Implementation plan (if coding)
```

## Resource Map

Load references only when relevant:

- [references/first-order-gates.md](references/first-order-gates.md) — cardinal rule, five gates, proceed protocol
- [references/reasoning-protocol.md](references/reasoning-protocol.md) — blocks 0–7 + extensions
- [references/reasoning-modes.md](references/reasoning-modes.md) — depth tiers, ADI, complexity routing
- [references/reasoning-command-workflow.md](references/reasoning-command-workflow.md) — abductive/deductive/inductive synthesis output
- [references/implementation-plan-template.md](references/implementation-plan-template.md) — Block 9 YAML plan skeleton
- [references/success-metrics-template.md](references/success-metrics-template.md) — Block 11 acceptance criteria
- [references/analysis-modes.md](references/analysis-modes.md) — rapid/comprehensive/dependency/performance
- [references/confidence-and-contingency.md](references/confidence-and-contingency.md) — confidence scale, Block 5 gate
- [references/validation-checklist.md](references/validation-checklist.md) — pass/fail gates before delivery
- [references/systematic-debugging.md](references/systematic-debugging.md) — reproduce → isolate → verify
- [references/best-of-n-parallel.md](references/best-of-n-parallel.md) — parallel best-of-n strategies

## Validation

Before delivering a reasoning artifact, validate against [validation-checklist.md](references/validation-checklist.md).

## Failure Handling

- State exact blocker and which gate or block failed
- Label unverifiable items as `Unknown`
- Surface highest-leverage alternative with quantified trade-offs
- Do not proceed on moderate+ complexity when Block 5 gate fails without explicit user override
- Do not present low-confidence output as certain
