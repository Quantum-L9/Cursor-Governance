---
name: l9-claude-coding-contract-compiler
description: compile, revise, and validate scoped Claude Code coding-contract chains from campaign specs. use for coding contracts, PR or execution specs, and cold-resumable multi-contract campaigns; not for other executors.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, contract-compiler, claude-code, campaign, scope-lock]
  owner: igor_beylin
  status: active
  version: "2.7.0"
  updated: "2026-08-28"
  tier: exemplary
  convergence_status: fixed_point
  compiled_by: l9-skill-compiler v3.5.0
  sibling: perplexity-coding-contract-compiler v2.1.0
  executor_profile: claude-code (hardwired)
---


## Purpose
Compile a coding contract that a **Claude Code session** can execute end-to-end within its
real limits: bounded context window, turn-based execution, permission-gated tools, and cold
session resumes. The contract is the authority; Claude is the executor. The contract must fit
what Claude does best and route around what it does poorly.

This is the Claude-native sibling of `perplexity-coding-contract-compiler`. Same 29-section
skeleton, scope-lock kernel, fail-closed rules, and recursive-improvement kernel — but the
FILL POLICY and AUTHORITY MAPPING are hardwired to Claude Code, not a runtime-agnostic agent.

## When To Use / When To Reject
Use when a change will be built by Claude Code and needs a scoped, enforceable contract.
Reject when: no target repo; freeform unbounded refactor with no scope boundary; the user
wants code written directly with no contract; or the executor is not Claude Code (use the
`perplexity-coding-contract-compiler` sibling instead).

## Claude Executor Model (the fixed premises this compiler builds against)
```yaml
strengths:            # lean the contract INTO these
  - reasoning over a repo it reads incrementally
  - bounded, well-justified diffs with clear rationale
  - preserving existing files and explaining preservation
  - writing the validation report as an argument
limits:               # route the contract AROUND these
  - turn-based; sessions end and resume cold
  - bounded context window; degrades as it fills
  - permission-gated tools (direct push/merge/settings blocked; terminal make pr is explicit narrow delivery)
  - weak as a deterministic hash function / long-lived mutable state holder
```

## Authority Order (contract-internal)
```
1. resume-from precondition (session may be cold)   # Claude-specific, highest
2. prerequisite contract state
3. scope lock (context-window-bounded)
4. self-modification protection
5. fail-closed evaluator (one checkpointed local commit per contract)
6. permission-mapped halt boundary
7. git workflow (exactly one local commit per contract; one terminal make pr)
8. validation report
9. definition of done
```

## Mode Selection
| Intent | Mode |
|---|---|
| Author a new Claude-executable contract | `author` |
| Revise / correct an existing contract | `revise` |
| Harden an existing contract (5-pass, DRY_RUN default) | `harden` |
| Validate for completeness + Claude-fit + safety | `validate` |
| Package with MANIFEST | `package` |

## Compact Workflow
0. Read `references/binding-directives.md` — activate directives, report.
1. Parse change request + repo evidence. Resolve the authority anchors AND the target
   repository's authoritative cold-resume and commit-gate validation commands. Resolve every anchor
   required by `references/contract-anatomy.md`, INCLUDING the fixed `executor: claude-code`.
2. Apply the Claude fill policy (`references/claude-fill-policy.md`) — this is what makes
   this compiler different from the Perplexity sibling.
3. Author the canonical **campaign spec** (`campaign-spec.yaml`, schema
   `schemas/campaign-spec.schema.json`), following the seven rules in
   `references/canonical-spec.md`. Then EMIT instances deterministically:
   ```
   scripts/compile_contract.py --spec campaign-spec.yaml --out DIR --validate --emit-artifacts
   ```
   Do NOT hand-fill the 30 sections — `compile_contract.py` derives the sections manifest, IDs,
   handoff seams, one-commit ordinals/commands, terminal delivery, and `chain_digest` from the spec (determinism lives in the
   script, not model judgment). The 29-section semantics are still authoritative
   (`references/section-contract.md`); the spec is how you feed them.
4. Attach schemas from `schemas/` (JSON, Draft 2020-12) + bundle runnable scripts from `scripts/`.
   If `compile_contract.py` fails closed with `DECOMPOSE_REQUIRED` (an item exceeds session
   thresholds), split that item into ordered sub-items in the spec — never group by judgment,
   never compress. `plan_decomposition.py` provides the thresholds and grouping helper.
5. Run 6 validation classes (`references/validation-evidence.md`) + the Claude-fit gate:
   - `scripts/validate_contract.py` on EVERY emitted instance (schema + Claude-fit + DPK), AND
   - `scripts/validate_chain.py` on ALL sub-contract instances IN ORDER whenever the output is a
     chain. A decomposed pack is NOT valid until the chain validator is green (seams match,
     predecessor proof is reachable, exactly one commit per contract, one repo+branch, and exactly
     one terminal `make pr` authority). Do not report "converged" on
     per-contract passes alone — that is the exact gap that ships a broken chain.
6. Emit validation report + definition of done. Optionally emit per-contract Claude Code artifacts
   with `scripts/generate_claude_settings.py` and `scripts/generate_preflight.py`.
7. Package with MANIFEST. Gate G machine_summary.

## Non-Negotiables (Claude-specific)
- Instance emission is **script-produced** (`compile_contract.py`), never hand-typed. The model
  authors the spec (WHAT); the script fixes IDs, seams, `source_commits`, and `chain_digest` (the
  determinism-critical HOW). Hand-emitting sections is the exact drift the script exists to remove.
- Scope MUST be context-window-bounded. If a mandate can't fit one focused session,
  the compiler MUST decompose it into an ordered sub-contract chain (PR-A -> PR-B -> PR-C).
- Every contract MUST open with a `resume-from` precondition block (session may be cold).
- `halt_boundary` MUST map to concrete tool denials, not prose:
  deny `Bash(git push:*)`, `Bash(git merge:*)`, `Bash(gh pr *:*)`, repo-settings tools.
- DRY_RUN default maps to Claude plan mode / permission prompts, NOT a written approval flag.
- Determinism-critical logic (hashing, planning, promotion) MUST live in bundled scripts
  the agent invokes — NEVER in agent judgment. Claude decides WHAT; scripts decide the HASH.
- `campaign.validation` is mandatory canonical input. The compiler MUST NOT infer npm, Python,
  Go, Cargo, Maven, Gradle, Make, a package manager, or a validation command. Missing target
  validation blocks compilation.
- Every item MUST declare `sizing.commits: 1`. Every contract creates exactly one local commit
  with compiler-owned subject = contract ID on the shared campaign `target_branch`.
- `items[].verify_proof` proves the CURRENT item at commit time and is included in that contract's
  `commit_gate.required_before_commit`. Contract N+1 re-runs only that dedicated predecessor
  completion proof together with an exact HEAD-subject assertion. It MUST NOT replay the predecessor's
  repository-wide commit gate. The current contract's proof is never treated as its own future
  cold-start prerequisite.
- Internal Section 28 handoff token is exactly `["<this-contract-id> committed_and_validated"]`,
  byte-identical to the next contract's assumption. External base prerequisites may still use
  merged/present states.
- No contract pushes between items. Direct `git push` and direct PR-creation commands stay denied.
  Exactly the terminal contract receives `terminal_delivery: {authorized: true, command: "make pr"}`
  and runs `make pr` once after its one validated local commit.

## Resource Map
### Read first
- `references/binding-directives.md`
- `references/claude-fill-policy.md`  — the Claude-vs-generic fill differences (read before filling)
- `references/dpk-integration.md`     — DPK-1.0 six-layer control plane bindings (read for DPK repos)
- `references/section-contract.md`    — 29 sections + Claude fill column
- `references/contract-anatomy.md`    — 8 anchors, executor fixed to claude-code
- `references/canonical-spec.md`       — how to shape the campaign spec (read before authoring input)

### Read when relevant
- `references/kernel-fail-closed.md`       — before writing any promotion/evidence rule
- `references/kernel-scope-lock.md`        — before sizing scope
- `references/validation-evidence.md`      — for validate / harden
- `references/kernel-recursive-harden.md`  — for harden mode (DRY_RUN default)

### Schemas (schemas/, JSON Draft 2020-12)
campaign-spec (input), coding-contract, scope-lock, evidence-record, promotion-decision,
validation-report, improvement-report, improvement-log, delta-report, convergence-report

### Input example
- `examples/campaign-spec.example.yaml` — explicit Node/npm campaign example
- `examples/campaign-spec.python.example.yaml` — Python neutrality + two-contract predecessor example
- `examples/campaign-spec.go.example.yaml` — Go neutrality example

### Runnable scripts (scripts/) — bundle ALL of these with every compiled contract
- `scripts/compile_contract.py`       — spec -> emitted, self-validated instances (the emitter; new in v2.2.0)
- `scripts/validate_contract.py`      — per-instance schema + Claude-fit + DPK gate (exit 0 = valid)
- `scripts/validate_chain.py`         — chain-level seam + `chain_digest` + commit + repo/branch gate
- `scripts/plan_decomposition.py`     — deterministic sizing + commit grouping + `chain_digest`
- `scripts/generate_preflight.py`     — emits `preflight.sh` cold-start guard per contract
- `scripts/generate_claude_settings.py` — emits `.claude/settings.json` + `CLAUDE.md` per contract
- `scripts/test_target_validation.py` — executable Node/Python/Go + branch/predecessor + one-commit/single-delivery regression suite

## Validation
Not complete unless: all 30 sections (0–29) present; target validation is explicit; scope fits one
session; every item is one commit; resume-from is executable; direct remote mutation is denied;
internal handoffs are `committed_and_validated`; contract 2+ proves the predecessor; and only the
terminal contract is authorized for `make pr`. Every instance must pass `validate_contract.py`, the
ordered set must pass `validate_chain.py`, and `scripts/test_target_validation.py` must pass. Per-contract
green alone is NOT convergence.

## Exemplary Intelligence Layer
Compiled to `tier: exemplary` by **l9-skill-compiler v3.3.0** via the pipeline
`parse_source → extract_expertise → compress_expertise → design_skill → run exemplary_gate → package`.
The compressed intelligence — expert roles, doctrine, invariants, authority order, activation and
reject signals, adapters, failure modes, and leverage points — is extracted (not summarized) in:

- `expertise_model.yaml` — the compressed judgment model (Gate B artifact).
- `skill_intelligence_report.yaml` — activation model (measured specificity 5 / false-positive
  risk 1), authority model, 7 expert heuristics, adapter map, evidence hierarchy, all 10
  `exemplary_gate` results = pass, and the `tier_decision`.
- `references/enforcement-gates.md` — the per-stage proof-of-compliance gates
  (spec → emit → validate → chain → package).

**How input must be canonicalized** is the highest-leverage doctrine and lives in
`references/canonical-spec.md` + `schemas/campaign-spec.schema.json`: one allowed-file = one
deliverable-with-path; split forbidden into `forbidden_paths` (→ preserved) vs
`forbidden_capabilities` (→ out-of-scope); `verify_proof` must be runnable; size honestly (the
compiler decides fit); never hand-author IDs/seams/digest; DPK owner + rollback + readiness
categories required; DPK prohibited behaviors adopted verbatim.

The exemplary claim is gated deterministically by `scripts/validate_exemplary_skill.py`
(l9-skill-compiler). Any failing or Unknown gate downgrades the tier to `strong` — never a
fabricated pass. Repo-registry wiring (`l9-wire-skill-into-repo`) is `not_applicable` in
environments where that global skill is absent.

### After-use improvement hook
Capture ONLY when the user reports a bad run or requests iteration: `missed_trigger`,
`false_trigger`, `recurring_user_correction`, `output_that_required_manual_rework`. Feed each
back into the activation signals, doctrine, or canonicalization rules — do not expand the skill
speculatively.

## Sibling: pipeline orchestrator (separate pack)
This compiler's scope is **emit + validate contracts** — nothing more. Chain execution (one fresh
session per contract, auto-merge gate, GitHub branch protection) lives in a **separate sibling pack,
`l9-pipeline-orchestrator`**, which consumes this compiler's emitted `out/PR-*/` set. Keeping them
apart keeps the compiler pure and the orchestration independently versioned. Install the orchestrator
pack when you want hands-off chain execution; it is not required to compile or validate contracts.

## Failure Handling
State exact blocker. Label UNKNOWN. Never invent scope, prerequisites, hashes, test counts,
or approvals. If a mandate exceeds one session, decompose — do not compress. Smallest safe next action.
