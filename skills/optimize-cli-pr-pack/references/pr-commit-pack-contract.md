# PR Commit Pack Contract

## Purpose

Create a portable bundle that lets a developer or successor agent inspect, apply, validate, commit, deploy, and roll back the optimize CLI change without reconstructing the conversation.

## Required tree

```text
<pack-name>/
  MANIFEST.json
  README.md
  change/files/...
  change/commit.patch
  change/OPTIMIZATION_PLAN.json
  pr/COMMIT_MESSAGE.txt
  pr/PR_BODY.md
  pr/PR_CHECKLIST.md
  deploy/DEPLOY_PLAYBOOK.md
  deploy/ROLLBACK_PLAYBOOK.md
  deploy/RELEASE_CHECKLIST.md
  handoff/AGENT_HANDOFF.md
  handoff/NEXT_AGENT_TASK.json
  evidence/CLI_REVISION_SYNTHESIS.json
  evidence/CLI_REVISION_PLAN.md
  evidence/DOCS_CODE_DIVERGENCE_FINDINGS.md
  evidence/VALIDATION.md
  evidence/PERFORMANCE.md
  evidence/commands.jsonl
  evidence/checksums.sha256
```

Add `issues/ISSUE-<fingerprint>.md` only for unresolved independent root causes.

## Consistency laws

- Every path in `MANIFEST.json.changed_files` must exist under `change/files/`.
- Every changed path must be represented in the patch and copied under `change/files/`, except declared deletions.
- `CLI_REVISION_SYNTHESIS.json` must contain every material finding, every revision target, every viable option, validated leverage scores, selection rationale, unresolved divergence IDs, and unknowns.
- Every finding must map to a target and every target to an option; selected options must be in scope and score at least 3.5.
- Unresolved docs-code divergence must appear in the synthesis JSON, divergence Markdown, and PR body.
- `OPTIMIZATION_PLAN.json` must record bottleneck ownership, evidence, strategy, preserved constraints, external limits, resource envelope, and rollback trigger.
- `PERFORMANCE.md` must record comparable baseline and candidate measurements or explain why the pack is blocked.
- The commit subject must describe the diff, use imperative mood, and remain one logical commit.
- The PR body must state problem, solution, behavior, tests, deployment impact, rollback, risks, and unknowns.
- Validation claims must link to commands or inspected artifacts.
- `checksums.sha256` must cover every regular file except itself and generated archives.
- Do not include secrets, credentials, private tokens, `.git/`, caches, virtual environments, or unrelated working-tree changes.

## Status model

- `PR_READY`: all applicable release gates pass.
- `READY_WITH_HUMAN_STEP`: code and pack validate, but a named external approval or deployment action remains.
- `BLOCKED`: material implementation, validation, or deployment blocker remains.

A pack may be complete while status is `BLOCKED`, but it must not claim deployability.


## Conditional Reachability Evidence

When the latent-capability adapter is active, add:

- `evidence/WIRING_MAP.md`;
- `evidence/LATENT_CAPABILITY_FINDINGS.json`;
- manifest fields for wiring analysis, selected finding IDs, and unresolved wiring unknowns.

The pack validator must reject `PR_READY` when selected findings lack definition evidence, consumer-edge evidence, dynamic-dispatch review, verdict `activate`, or a named downstream capability.


## Adaptive reasoning agreement

- `EXECUTION_ROUTE.json` records the initial proportional route and active proof obligations.
- `DECISION_LEDGER.json` records final evidence, selected options, unknowns, proof closure, final action, and convergence.
- `DECISION_RECORD.md` is the human-readable projection of the ledger.
- Manifest counts and actions must match the route and ledger.
- `PR_READY` requires every routed proof obligation satisfied and no material unknowns.
