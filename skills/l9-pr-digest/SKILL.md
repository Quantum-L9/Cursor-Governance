---
name: l9-pr-digest
description: digest an exact pull request into deterministic evidence, intent and expansion analysis, architecture judgement, and a bounded remediation gate without modifying the PR. use when reviewing agent-generated PR scope, checking architecture or proportionality before remediation, manually unpacking a PR in chat, or running a machine pre-remediation quality gate beyond ordinary CI.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pr, digest, scope, architecture, pre-remediation, evidence]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-09-02
---

# L9 PR Digest

## Purpose

Read and judge a PR **before remediation can change its evidence surface**. Bind exact base/head, consume CI rather than cloning it, expose unnecessary expansion, and emit one bounded gate + remediation packet. Never mutate the PR.

This skill owns pre-remediation digestion. `l9-pr-remediation` remains the downstream mutator and merge/convergence owner.

## Activation boundary

Use for PR digestion before remediation, agent-output scope control, architecture-expansion review, proportionality review, or interactive PR unpacking. Do not use for ordinary unit/lint execution, formatting-only checks, dependency installation, generic code generation, or remediation itself.

## Authority order

1. User task/contract and explicit non-goals.
2. Exact PR base/head evidence and current repository source.
3. `AGENTS.md`, canonical law, scoped rules, canonical contracts, and established owners.
4. Existing CI/test evidence.
5. Deterministic digest from `scripts/pr_digest.py`.
6. Targeted semantic judgement, only when the deterministic evidence leaves a material question unresolved.
7. `UNKNOWN`; never invent intent, architecture, CI, or execution evidence.

## Required inputs

- PR reference or current PR
- exact base revision and exact head revision
- repository context
- original task/intent when recoverable
- governing architecture and repository law
- CI/test evidence available for the current stage

If base or head cannot be bound exactly, stop with `BLOCKED`. If original intent cannot be recovered, continue structural/architecture review but use `INTENT_UNKNOWN_REVIEW_REQUIRED` when material scope judgement depends on it.

## Deterministic-first workflow

1. **Bind immutable identity.** Record repo, PR, base SHA, head SHA, merge base, branch, commits.
2. **Collect machine evidence.** Run `scripts/pr_digest.py` in live `gh` mode or normalized fixture mode. It inventories paths, line counts, tests/docs/config/dependencies, CI checks, generated-looking surfaces, structural additions, suppressions, binaries, lockfile churn, and other objective signals.
3. **Load architecture only where touched.** Use repository files first. Compose `l9-code-analysis` for deep structural mapping when useful. Use `l9-code-graph-rag-mcp` only when its index is already healthy and importer/blast-radius evidence changes the decision.
4. **Bind intent.** Priority: explicit task contract → linked task/issue → agent contract → PR body → commit messages → `UNKNOWN`.
5. **Classify growth.** Load [decision-and-expansion.md](references/decision-and-expansion.md). Size alone never proves scope creep.
6. **Escalate only unresolved judgement.** Load [judgement-escalation.md](references/judgement-escalation.md). Compose `l9-structured-reasoning` only for the exact semantic/architecture questions emitted by the digest. Do not rerun deterministic work through a model.
7. **Gate.** A deterministic failure cannot be overridden by model judgement. Apply the shared decision contract.
8. **Emit bounded handoff.** Validate the machine shape against [machine-output.schema.json](references/machine-output.schema.json) and remediation packet against [remediation-packet.schema.json](references/remediation-packet.schema.json). Remediation receives only accepted scope, required fixes/narrowing, invariants, relevant tests/CI, explicit non-goals, and unknowns.

## Modes

### Machine

Prefer maximum automation. Run the deterministic engine first:

```bash
python3 skills/l9-pr-digest/scripts/pr_digest.py \
  --repo owner/repo --pr-number 123 --workspace "$PWD" \
  --output .l9/pr/pr-digest-result.json
```

A connector or orchestration host may instead normalize immutable PR evidence into JSON and run `--fixture evidence.json`. This is the preferred path when the repository is not locally cloned. `--validate-only result.json` validates required fields and exact revision binding.

If `LLM_judgement_questions` is empty, do not invoke a model. If non-empty, answer only those questions from cited PR + repository evidence, append `judgement_findings`, classify the affected `expansion_items`, set `LLM_judgement_used: true`, then recompute the final decision under the rules below.

### Interactive chat

Use the same evidence object and decision semantics. Load [interactive-output-contract.md](references/interactive-output-contract.md) and render a human-readable change story, expansion map, architecture impact, CI boundary, findings, narrowing decisions, bounded remediation packet, and readiness. Do not mutate the PR.

## Decision model

Allowed decisions only:

- `READY_FOR_REMEDIATION`
- `READY_WITH_NON_BLOCKING_NOTES`
- `NARROW_BEFORE_REMEDIATION`
- `ARCHITECTURE_REPAIR_BEFORE_REMEDIATION`
- `CI_OR_EXECUTION_FAILURE`
- `INTENT_UNKNOWN_REVIEW_REQUIRED`
- `BLOCKED`
- `UNKNOWN`

`NARROW_BEFORE_REMEDIATION` blocks remediation until confirmed unjustified expansion is removed. `ARCHITECTURE_REPAIR_BEFORE_REMEDIATION` blocks remediation until duplicate authority/shadow path/boundary bypass is corrected. CI/execution failures remain failures. Only the two READY decisions may pass the bounded packet to `l9-pr-remediation`.

## CI boundary

CI owns cheap deterministic proof such as syntax, format, lint, typecheck, schemas, tests, package build, and known policy checks. This skill consumes those results. It owns intent alignment, proportionality, architecture fit, duplicate authority, unnecessary generalization, semantic contract drift, suspicious scope growth, and the decision whether remediation should narrow before polishing.

Do not rerun expensive CI merely to duplicate an existing result. Missing evidence is `NOT_EXECUTED` or `UNKNOWN`, never `PASS`.

## Composition boundary

- `l9-code-analysis`: structural support when a touched seam needs deeper mapping.
- `l9-structured-reasoning`: judgement-only support for emitted semantic questions.
- `l9-code-graph-rag-mcp`: conditional blast-radius/importer evidence when already healthy.
- `l9-gap-analysis`: conditional explicit target/readiness delta, not a default PR dependency.
- `l9-pr-remediation`: downstream only after a READY decision.

Do not activate GAR, security, performance, CI setup, or GMP merely because they exist. Load them only when a distinct triggered concern requires their owner.

## Pipeline handoff

The canonical bounded-autonomy PR poll worker must run this skill before `l9-pr-remediation`. It must preserve the reviewed base/head. If the head moved, discard the stale digest and run again. On a non-READY decision it must not enter remediation. On READY, pass only `remediation_packet` plus exact PR identity downstream.

## Hard prohibitions

- Never edit, push, comment on, relabel, close, or merge the PR under review.
- Never use PR size alone as a scope-creep verdict.
- Never fabricate original intent.
- Never let a model override deterministic failure.
- Never recreate CI as another green/red layer.
- Never recreate the archived generic `l9-pr-analysis` owner; this skill is specifically the immutable pre-remediation digest/gate.
- Never hardcode Fable behavior. Agent-expansion checks are provider-neutral.
- Never send remediation vague cleanup or optional refactors as mandatory work.

## Validation

```bash
python3 skills/l9-pr-digest/scripts/self_test.py
python3 skills/l9-pr-digest/scripts/pr_digest.py --validate-only <digest.json>
python3 skills/l9-skill-compiler/scripts/validate_skill_pack.py skills/l9-pr-digest
```

A structural pass proves the pack and deterministic engine shape. It does not prove a real PR judgement until exact PR evidence is dogfooded.

## Resources

- [decision-and-expansion.md](references/decision-and-expansion.md)
- [judgement-escalation.md](references/judgement-escalation.md)
- [interactive-output-contract.md](references/interactive-output-contract.md)
- [machine-output.schema.json](references/machine-output.schema.json)
- [remediation-packet.schema.json](references/remediation-packet.schema.json)
- [dogfood-validation.md](references/dogfood-validation.md)
