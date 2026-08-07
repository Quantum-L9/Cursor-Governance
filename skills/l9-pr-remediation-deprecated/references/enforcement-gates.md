# Enforcement Gates

Each gate must produce a section in the canonical run report before transition.

| Gate | Proof artifact | Blocks transition when |
|---|---|---|
| P: Preflight | `preflight` | target, authorization, or capability truth is unresolved |
| A: Scope and gates | `gates.gate_registry` | required checks or trustworthy local commands are unknown |
| B: Ownership and classification | `gates.classified_findings` | ownership was not decided before disposition |
| C1: CI signal routing | `ci_pipeline_signals` | a pipeline cause lacks a unique issue file or repair was attempted |
| C2: Codebase batch | cycle change count and diff summary | edits are non-codebase, unrelated, or out of scope |
| D: Local verification | `gates.local_verify_log` | a locally reproducible codebase gate fails before push |
| E: Commit and push | `gates.push_record` | more than one commit/push, push without Gate D, or CI issue files enter the commit |
| F: Review handling | `gates.reply_record` | a thread lacks reply/state or ownership-aware routing |
| G: PR readiness | `pr_readiness` | any readiness condition is false |
| H: Terminal and package | `terminal_escalation` + `deliverable` | required codebase escalation or CI issue files are missing |

## Gate B

Every finding has a stable ID, ownership, source, current evidence, severity, disposition, confidence, scope decision, and reason. `CI_PIPELINE_SIGNAL` is never eligible for code mutation.

## Gate C1

For every distinct CI root-cause fingerprint:

- exactly one `issues/ci-pipeline/*.md` file exists;
- `repair_attempted` is false;
- `repository_files_modified` is empty;
- affected checks and evidence are recorded;
- the file is excluded from PR commits and included in the final tar.gz.

## Gate C2

The codebase batch contains only accepted `CODEBASE_REPAIR` findings. A zero-change batch is valid.

## Gate D

Run all reproducible codebase gates. Up to three local iterations are allowed. A push requires `all_green: true` and exact gate-count equality. Pipeline-owned failures are routed, not hidden.

## Gate E

`push_count_this_cycle` is 0 or 1. A non-empty commit contains only codebase changes and the cycle trailer. No force push.

## Gate F

Every thread receives one reply. Resolved plus human-decision plus CI-routed threads equal total threads. Human-decision and CI-routed threads remain open while blocking.

## Gate G

Readiness is evaluated against the final remote head. Ready requires zero codebase blockers and zero CI-pipeline blockers.

## Gate H

- codebase/human residual blockers use a GitHub terminal issue or fallback artifact;
- CI-pipeline blockers always have separate issue files;
- CI-only blocked runs use `ci_signal_bundle`, not an automatic issue in the consumer repository;
- every run has a deterministic tar.gz and manifest.

## Protocol Violations

Record at least:

- cycle-overrun;
- push-before-verify;
- multi-push;
- blind-fixing;
- ownership-not-classified;
- ci-pipeline-mutation-attempted;
- ci-signal-missing-issue-file;
- ci-root-causes-merged;
- ci-issue-file-committed;
- required-gate-weakened;
- false-positive-applied;
- silent-thread;
- readiness-overclaim;
- missing-terminal-escalation;
- duplicate-terminal-issue.

Validation is performed by `scripts/validate_run_report.py` and `scripts/validate_autonomy_contract.py`.
