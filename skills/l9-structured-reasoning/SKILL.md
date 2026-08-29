---
name: l9-structured-reasoning
description: Adaptive evidence-based reasoning for planning, architecture, debugging, and trade-offs. Use when the user needs root-cause reasoning or an evidence-grounded decision. Do not activate for simple facts or when a domain Skill owns the contract.
---

# L9 Structured Reasoning

## Objective

Produce the smallest auditable reasoning structure that improves the decision. Expose evidence, assumptions, options, risks, and rationale. Do not expose or require private chain-of-thought.

## Authority Order

1. Current user instruction and platform safety rules.
2. Verified source material, repository state, and explicit invariants.
3. The most specific active domain Skill.
4. This general reasoning Skill.
5. Model inference, labeled when material.

Higher authority wins. Never let this general Skill override a more specific valid domain contract.

## Activation Gate

Activate on strong signals such as:

- explicit trade-off or multi-option decision analysis;
- architecture choice or blast-radius review;
- plan stress test, dependency analysis, or pre-implementation verification;
- reproducible debugging or root-cause analysis;
- multi-document corpus analysis (gaps, coherence, dependency maps, insights);
- a request for an evidence-backed decision record.

Do not activate when:

- the task is a simple factual answer, translation, rewrite, or direct transformation;
- the operation is deterministic and has no meaningful trade-off;
- the change is trivial, reversible, and already specified;
- a specific domain Skill provides the full reasoning and validation contract;
- the user asks only for execution and the required decision is already settled.

When activation is uncertain, prefer non-activation or a lightweight route.

## Adaptive Router

Classify the task across independent dimensions. Do not map complexity to a mandatory sequence of visible blocks.

```yaml
task_kind: plan | review | architecture | debug | decision | corpus
reasoning_depth: rapid | standard | deep
epistemic_methods: [abductive, deductive, inductive, comparative]
risk_class: reversible | guarded | irreversible
evidence_state: sufficient | partial | conflicting | absent
output_profile: answer | decision_record | implementation_plan | architecture_record | debug_report | corpus_report
```

Use `scripts/route_reasoning.py` when deterministic routing is useful. Load `references/reasoning-router.yaml` for proof obligations.

## Core Workflow

1. **Lock the real objective.** State the decision or outcome in one sentence. Use a bounded assumption when safe instead of reopening settled questions.
2. **Inspect the minimum evidence.** Prefer primary sources and targeted reads. Separate verified facts, inference, and Unknown.
3. **Route proof obligations.** Activate only the obligations required by task kind, risk, and evidence state.
4. **Apply first-order leverage.** Prefer the smallest move that improves future moves. Load `references/first-order-leverage.md` only for prioritization or design choices.
5. **Check capabilities and authority.** Never assume subagents, parallel runners, Git worktrees, write access, or connectors. Load `references/capability-adapters.md` when execution depends on tools. For multi-document corpus work, load `references/document-corpus-reasoning.md` and select only the modes/operations that change the decision.
6. **Reason and act proportionally.** Use one targeted probe at a time, ordered by value of information. Stop probing when the material uncertainty is resolved.
7. **Produce the correct output profile.** Use `references/output-profiles.md`. Include a machine-readable ledger only when traceability, handoff, or comparison materially helps.
8. **Validate the decision.** Test disconfirming evidence, regressions, reversibility, and acceptance criteria. Use `references/risk-and-autonomy-policy.md` for proceed, probe, or block decisions.

## Conditional Proof Obligations

- **Plan:** objective, dependencies, critical path, acceptance criteria, material risks, rollback when needed.
- **Review:** evidence chain, contradictions, missing coverage, priority, and recommended correction.
- **Architecture:** at least two viable options when they exist, trade-offs, blast radius, reversibility, migration and rollback.
- **Debug:** reproduce, isolate, testable hypotheses, disconfirming evidence, minimal fix, regression proof.
- **Decision:** options, decision criteria, evidence, opportunity cost, selected option, and trigger for reconsideration.
- **Corpus:** corpus scope, selected mode(s), dependency or pattern map, gaps with severity, coherence conflicts, actionable insights, readiness.

Do not emit obligations that do not change the decision.

## Evidence and Decision Ledger

Use `references/evidence-decision-contract.yaml` when the work is high stakes, resumable, delegated, or likely to be compared across runs. The ledger records claims and evidence, not hidden reasoning.

Required principles:

- every material claim has evidence or an explicit `Unknown` grade;
- disconfirming evidence is recorded when relevant;
- options remain distinct until selection;
- the selected option names its trade-offs and reversibility;
- unresolved uncertainty maps to a probe, constraint, handoff, or block.

## Risk and Autonomy

Do not use arbitrary confidence percentages unless calibrated by benchmark history.
Machine contract: `references/confidence-policy.yaml` (risk table as `allow_set`; ECE is not a gate).

Use:

```yaml
evidence_quality: high | medium | low | unknown
decision_risk: reversible | guarded | irreversible
action: proceed | proceed_with_validation | bounded_probe | block
calibration_status: none
stated_probability: null
```

Reversible work may proceed with bounded validation. Irreversible work requires direct evidence, an explicit authorization boundary, and a rollback or containment path. Fail closed when a material uncertainty cannot be bounded.

## Tool and Parallelism Rules

- Use tools only when they can resolve a named evidence gap.
- Prefer the smallest authoritative inspection over broad exploration.
- Use true parallel trials only when the environment supports isolation and the comparison value exceeds coordination cost.
- Otherwise use sequential bounded probes and stop after the first decisive result.
- When write authority is absent, produce an exact decision record, implementation plan, or handoff rather than mutating.

## Output Discipline

The user-facing response should show:

- the decision or answer;
- the decisive evidence;
- material assumptions and Unknowns;
- key trade-offs;
- the next action or stop condition.

Do not require ceremonial headings, fixed block counts, or end-to-end private reasoning. Keep output proportional to stakes.

## Failure Handling

- If evidence is absent but the action is reversible, run one bounded probe.
- If evidence conflicts, identify the smallest discriminating test.
- If an irreversible decision remains materially uncertain, block and state the exact missing evidence.
- If a domain Skill conflicts, follow the more specific Skill unless it violates a higher authority.
- If tools are unavailable, downgrade to evidence-limited reasoning and label the limitation.

## Self-Improvement Hook

Capture an after-use observation only when the user reports a bad run or requests iteration:

```yaml
missed_trigger: null
false_trigger: null
recurring_correction: null
manual_rework: null
proposed_behavior_change: null
```

Do not invent telemetry.

## Exemplary Build Evidence

This rebuild used the mandatory `extract_expertise -> compress_expertise -> design_skill -> exemplary_gate` path. See `expertise_model.yaml` and `skill_intelligence_report.yaml`. Run `scripts/validate_exemplary_skill.py .` before claiming exemplary status.

## Resource Map

- `references/reasoning-router.yaml`: routing dimensions and conditional proof obligations.
- `references/evidence-decision-contract.yaml`: auditable ledger contract.
- `references/confidence-policy.yaml`: stated-probability ban and evidence × risk allow-set.
- `references/risk-and-autonomy-policy.md`: evidence-risk-action rules.
- `references/capability-adapters.md`: tool, parallelism, Git, and write-authority fallbacks.
- `references/output-profiles.md`: proportional response and artifact shapes.
- `references/debugging-method.md`: evidence-first debugging loop.
- `references/document-corpus-reasoning.md`: multi-document modes and corpus operations.
- `references/first-order-leverage.md`: compact leverage filter.
- `references/benchmark-contract.md`: live comparison protocol for outcome quality and token efficiency.

## Validation

Run:

```bash
python3 scripts/self_test.py
python3 scripts/validate_exemplary_skill.py .
```

A structural pass proves packaging, routing, contracts, and fixtures. It does not by itself prove a literal 10x improvement in live model outcomes; use the benchmark contract for that empirical claim.
