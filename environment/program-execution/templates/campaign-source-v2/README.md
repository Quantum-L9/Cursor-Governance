# Canonical Campaign Source v2 Template

This directory contains the **only operator-supplied artifact required for the direct Program Execution campaign route**: [`CAMPAIGN_SOURCE.yaml`](CAMPAIGN_SOURCE.yaml). It is a complete, concrete `l9.program-execution.campaign-source.v2` example rather than a syntactic fragment. It passes the direct input preflight and compiles into a native Blueprint without editing the source during compilation.

> The source is sufficient for compilation, not for acceptance or execution. The campaign runner derives the Blueprint from this source, collects admission evidence, accepts the Blueprint, then bootstraps PEC. A PEC runtime is mutable state and is deliberately not committed beside the immutable source.

## Artifact boundary

| Item | Owner | Supplied or generated | Purpose |
|---|---|---:|---|
| `CAMPAIGN_SOURCE.yaml` | Operator | Supplied | Complete immutable intent, target binding, authority, work graph, task scope, validation, evidence, and gate definitions. |
| `source-integrity-receipt.json` | Campaign runner | Generated in the isolated campaign worktree | SHA-256 receipt binding the emitted source. It is not an authoring input. |
| Blueprint directory | Campaign compiler | Generated | Native Blueprint pair and registers validated in template mode. |
| PEC workspace | PEC | Generated | Mutable controller state and Program Lock created only after Blueprint acceptance. |

The `make campaign` front door supports five representations: a direct `campaign-source.v2`, architecture intent, activate seed, plan, or brief. **Only the direct route preserves the complete source unchanged as the compiler input.** PEC itself bootstraps from a validated Blueprint directory; it does not take three companion operator files. Therefore, the complete campaign source is the canonical reusable authoring template.

The historical three-file pack at `environment/program-execution-campaigns/CG-PES-RUN2-HARDENING/` is not the live campaign ingress: its `CAMPAIGN_CHARTER.yaml`, `CAMPAIGN_AUTHORIZATION.yaml`, and `CAMPAIGN_EXECUTION.yaml` each declare themselves compiled `l9.quantum/campaign-pack/v1` artifacts sourced from the older `l9.quantum/campaign-source/v1`. The current `make campaign` router accepts `l9.program-execution.campaign-source.v2` and compiles this template into the Blueprint that PEC consumes.

## Reuse procedure

Copy this directory outside `environment/program-execution/campaigns/` until the new campaign is ready to register. Replace the example campaign facts with verified facts: campaign and program IDs, owner, target repository, expected revision, scope, authorities, evidence, workstreams, tasks, paths, validation commands, gates, risks, and rollback rules. Keep `metadata.campaign_id` and `program.id` identical. Keep every repository alias equal to `targets[].repository_id`, or remove an alias that is not needed.

Do not leave a `REPLACE_WITH_*` token or `{{TOKEN}}` marker in the source. The Blueprint validator rejects them. Do not encode task order in task-local `dependencies` or `dependency_ids`; use only top-level `dependency_edges`. A `repo_local` task that permits `local_write` must declare every writable path and must have at least one single-operation terminal validation command. Program Execution always narrows push, pull request, merge, release, deployment, destructive-change, and external-message authority to `false`.

## Validation commands

From the repository root, first perform the read-only preflight:

```bash
make campaign-check-input \
  INTENT=environment/program-execution/templates/campaign-source-v2/CAMPAIGN_SOURCE.yaml
```

To exercise the actual `make campaign` route through Blueprint generation only, use a disposable runtime root. `CAMPAIGN_UNTIL=blueprint` is intentionally test-only; the explicit debug environment variable is required because ordinary live campaigns run through their local-commit execution boundary.

```bash
L9_CAMPAIGN_UNTIL_DEBUG=1 \
L9_ROOT="$(mktemp -d)/l9" \
make campaign \
  INTENT=environment/program-execution/templates/campaign-source-v2/CAMPAIGN_SOURCE.yaml \
  CAMPAIGN_UNTIL=blueprint \
  CAMPAIGN_ARGS="--primary $(pwd)"
```

This materializes the source and generated integrity receipt in an isolated campaign worktree, compiles the native Blueprint, runs launchability, and validates the Blueprint in template mode. It does not accept the Blueprint, bootstrap PEC, execute the task, create a PR, push, merge, publish, deploy, or modify the original source.

`CAMPAIGN_ARGS="--primary $(pwd)"` makes the local checkout explicit. It is necessary when the repository is not installed at the runner's default `$HOME/.cursor-governance` location.

For a real campaign, omit the test-only stop flag only after replacing every example fact with campaign-specific, authorized facts and after reviewing the resulting local execution consequences.
