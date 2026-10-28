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
- The commit subject (first line of `pr/COMMIT_MESSAGE.txt`) must describe the diff, use imperative mood, remain one logical commit, and be **at most 72 characters** — `scripts/validate_commit_pack.py` rejects a longer first line.
- The PR body must state problem, solution, behavior, tests, deployment impact, rollback, risks, and unknowns.
- Validation claims must link to commands or inspected artifacts.
- `checksums.sha256` must cover every regular file except itself and generated archives.
- Do not include secrets, credentials, private tokens, `.git/`, caches, virtual environments, or unrelated working-tree changes.

## Enum quick reference (author from this, not by failing the validator)

A smallest valid non-latent template ships at `assets/pack-spec.minimal.json`. The enum-constrained fields authors trip on:

- `optimization.strategy`: `remove_delay`, `bounded_parallelism`, `raise_local_cap`, `batch`, `pipeline_stream`, `async_io`, `process_connection_reuse`, `cache_reuse`, `narrow_lock`, `tune_local_retry`, `activate_latent_capability`, `repair_wiring`, `connect_signal_consumer`, `surface_existing_cli_path`, `other`, `none`.
- `optimization.utilization_gap_class`: the 19-member enum (`artificial_delay` … `lock_contention` for throughput; `inactive_component` … `latent_capability_wiring` for capability; `other_repository_owned`, `external_limit`, `unknown`).
- `revision_synthesis.findings[].kind`: `docs_code_divergence`, `performance_bottleneck`, `latent_capability`, `configuration_misalignment`, `resource_risk`, `external_limit`, `validation_gap`, `deployment_gap`, `other`. Map from `utilization_gap_class` via the table in `references/revision-synthesis-leverage-adapter.md`.
- `divergence_type`: `documented_not_implemented`, `implemented_not_documented`, `behavior_mismatch`, `config_default_mismatch`, `entrypoint_mismatch`, `unknown`.
- `wiring.findings[].defect_class`: `inactive_component`, `miswired_file`, `dormant_capability`, `unused_signal`, `orphaned_config_schema`, `broken_partial_wiring`.

`build_commit_pack.py` reports ALL schema violations in one run, so a single failed build surfaces the full constraint set rather than one error at a time.

## The `wiring` block is latent-capability only

Include the top-level `wiring` object **only** when `optimization.strategy` is a latent-capability strategy (`activate_latent_capability`, `repair_wiring`, `connect_signal_consumer`, `surface_existing_cli_path`) or the gap class is a capability class. For a throughput change, **omit `wiring` entirely** — its sub-schema is strictly required once present, so a copied-but-inapplicable block fails validation. `assets/pack-spec.minimal.json` is the canonical throughput example with no `wiring`; `assets/pack-spec.example.json` is the latent-capability example that carries one.

## Status model

- `PR_READY`: all applicable release gates pass.
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
