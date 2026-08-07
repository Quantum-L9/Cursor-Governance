# Convergence Loop

## Contract

Repeat codebase remediation no more than three cycles and stop immediately when the exact PR-ready evaluator passes. Route CI-pipeline root causes without repairing them.

```text
for cycle in 1..3:
  resume_and_ingest_current_head()
  classify_ownership_first()
  render_one_issue_file_per_ci_root_cause()
  validate_and_apply_codebase_batch()
  verify_codebase_up_to_3_iterations()
  commit_and_push_at_most_once()
  reply_and_resolve_by_ownership()
  wait_for_required_checks()
  evaluate_pr_ready_on_final_head()
  if ready: converge and package
  if only_ci_pipeline_blockers_remain: package_signal_bundle_and_stop
terminal_codebase_escalation_if_needed()
package()
```

## Remote Confirmation

Poll required checks for the evaluated head only. If the head changes, re-ingest. A remote failure after local verification must be classified:

- source or test defect -> next codebase cycle;
- workflow, action, runner, permission, secret, environment, policy, service, shared CI, or check wiring -> CI signal file;
- unknown ownership -> no edit; preserve evidence and block truthfully.

Do not consume another cycle trying to repair a proven CI-pipeline root cause.

## Re-Ingestion

Fetch only new or changed signals:

- failed checks on the latest head;
- unresolved threads lacking a remediation marker;
- comments created after the last observed mutation;
- changed review decision, draft state, mergeability, branch-protection requirements, or CI signal evidence.

Reuse existing CI signal files when the fingerprint is unchanged. Update evidence in place rather than duplicating the file.

## Stop Conditions

- `pr_readiness.ready == true` -> `converged`;
- only CI-pipeline blockers remain -> `partial` or `blocked`, `ci_signal_bundle`, package immediately;
- cycle 3 completed with codebase or human blockers -> terminal codebase escalation;
- unrecoverable permission, evidence, scope, or human-decision blocker -> ownership-aware escalation;
- user stop -> `partial`, checkpoint and package.

Never start cycle 4. Never recommend another PR-remediation cycle for a proven CI-pipeline blocker.

## Convergence Evidence

The final report includes cycle history, final head, required-check state, mergeability, review state, codebase blocker count, CI-pipeline blocker count, one issue-file path per CI root cause, terminal codebase issue URL or fallback when applicable, and tarball path.
