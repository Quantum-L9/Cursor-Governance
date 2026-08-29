# Remediation Runbook

## Package identity
- Package: `cursor_governance_program_execution_remediation_plan_v1_v27`
- Completion: **PLAN_EXECUTABLE**
- Compiler: `claude-coding-contract-compiler v2.7.0`
- Chain digest: `sha256:4d340ed56b2c97664f13126c9716452efbf98cd8a23c76ba400773a94241c2b3`

## Audit inputs
One audit: **Cursor-Governance Program Execution Forensic Audit**. Original audit baseline `f4265dcc58ff8ebee7896a1a89c9f298c9e8e5c8`. Scope remains `environment/program-execution/**`; all memory-related surfaces remain excluded.

## Current-state baseline
Current `main`: `5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d`. It moved after the audit, so all seven findings were re-adjudicated before recompilation. All seven remain confirmed. Execution branch is `claude/program-execution-authority-remediation-v1`, created from the exact current baseline before contract 1.

## Executive brief
The remediation architecture did not change. v2.7 removes the three compiler blockers that made the prior pack non-executable: it requires explicit target-native validation, executes compound preflights correctly, and uses local `committed_and_validated` seams. Contracts 1–5 are local-only. Contract 6 alone may invoke `make pr` once after its validated local commit. Direct push/PR commands and merge remain denied.

## Findings adjudication
| Finding | Severity | Current disposition | Root cause | Contract |
|---|---|---|---|---|
| PE-001 | P0 | CONFIRMED | reset/recovery side door | PR-001 |
| PE-002 | P1 | CONFIRMED | resume before source/lock reconciliation | PR-002 |
| PE-003 | P1 | CONFIRMED | shadow campaign completion authority | PR-003 |
| PE-004 | P2 | CONFIRMED | caller-supplied gate truth | PR-004 |
| PE-005 | P2 | CONFIRMED | failover policy not consumed live | PR-005 |
| PE-006 | P2 | CONFIRMED | no supported-front-door E2E proof | PR-006 |
| PE-007 | P3 | CONFIRMED | refusal facade still hosts active provider helpers | PR-006 |

## Confirmed findings
Every finding remains valid at `5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d`. See `evidence/finding_disposition_ledger.yaml` for exact current-source observations.

## Findings already resolved or superseded
None.

## Root-cause convergence
Six root-cause units remain, exactly as in the validated plan. PE-006 and PE-007 converge in the final supported-path/compatibility unit.

## Remediation architecture
Repair existing canonical owners only. No new Program state machine, router, registry, validator, completion owner, recovery authority, or memory integration is allowed.

## Execution order
1. Create `claude/program-execution-authority-remediation-v1` from exact `5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d`.
2. Run `claude-code-contracts/artifacts/PR-001/.../preflight.sh`, execute PR-001, run its commit gate, commit exactly once with compiler-owned subject.
3. Repeat fresh-session sequence for PR-002 through PR-005. No publication between contracts.
4. Run PR-006. It contains supported-path E2E, compatibility thinning, and final proof. After its one validated local commit, run **exactly one** terminal `make pr`.
5. Merge is outside this contract chain.

## Scope and hard exclusions
Write scope is only the exact files listed in each compiled contract. All memory-related Program Execution content, paths outside `environment/program-execution/**`, root autonomy implementation, ops/autonomy implementation, unrelated CI/skills/agents, secrets, deployment, and repo-settings mutation remain denied.

## Files and canonical owners
`core/` remains Program Lock/task state/Program lease/canonical receipt owner. `run_campaign.py` remains the supported campaign front door. Peer Execution remains provider lifecycle boundary. Repository campaign ledger becomes a projection, not completion authority.

## Success properties
Blocking properties remain SP-01 through SP-10 from the plan. Each contract's `verify_proof` is executable and is carried into the next contract's cold-resume predecessor proof.

## Negative regression proofs
P0/P1 negative cases are mandatory: direct `fresh-workspace`, active/ambiguous reset, source drift on resume, forged close evidence, false gate PASS, provider failure/retry hazards, duplicate result/completion, dependency blocking, and mutation conflicts.

## Validation gates
- Compiler instance validation: **6/6 PASS**
- Chain validation: **PASS**
- Compiler target-validation regression suite: **11/11 PASS**
- Deterministic recompile: **PASS**
- Plan-to-contract scope/traceability: **PASS**
- Target compatibility: **PASS**
- Implementation tests and `make pr-check`: run during contract execution, not fabricated in this planning package.

## Rollback and recovery
One local commit per contract. On a blocking failure, stop. Revert the failing unpushed local contract commit or restore only its scoped paths. Never hard-reset or force-push. Preserve completed green predecessor commits and evidence.

## Risks and blocking unknowns
No planning/compiler blocker remains. Runtime implementation may still expose new evidence; any material current-state drift or scope conflict requires stop/replan.

## Claude Code execution contracts
Compiler v2.7.0 loaded manually from the uploaded ZIP. Canonical input: `claude-code-contracts/campaign-spec.yaml`. Generated instances: `claude-code-contracts/emitted/PR-001.contract.json` through `PR-006.contract.json`.

## Claude Code contract execution order
`PR-001 -> PR-002 -> PR-003 -> PR-004 -> PR-005 -> PR-006`. Internal prerequisite state is exactly `committed_and_validated`.

## Claude Code cold-session handoffs
Each new session must run the generated `preflight.sh`. Contract 2+ verifies the exact predecessor commit subject, target branch, target-native cold-resume checks, and predecessor completion proof. Nothing else may be assumed.

## Operator handoff
- PLAN_DOCUMENT: `plans/program_execution_remediation_plan.json`
- Canonical plan projection: `plans/program_execution_authority_recovery_remediation_d681ee05.plan.md`
- Target: `Quantum-L9/Cursor-Governance`
- Locked baseline: `5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d`
- Execution branch: `claude/program-execution-authority-remediation-v1`
- Contract root: `claude-code-contracts/`
- First contract: `CG-PE-REMEDIATION-PR-001-v2.7.0`
- Compiler: `2.7.0`
- Contract validation: **PASS**
- Chain validation: **PASS**
- RUNBOOK is not execution authority. PLAN_DOCUMENT remains remediation authority; compiled contracts may narrow but not widen it. The only newly adopted executor-delivery rule from the user's v2.7 instruction is terminal `make pr`; merge remains external.

## Artifact map
See `MANIFEST.yaml` for every packaged artifact and SHA-256. Compiler-native runtime, schemas, references, generated CLAUDE.md/settings/preflight artifacts, validation receipts, traceability, plan, finding ledger, and current-state delta are all included.
