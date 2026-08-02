# Documentation and Code Capability Divergence

## Purpose

Detect and preserve material disagreement between documented CLI capability and executable repository behavior. A divergence is evidence to reconcile, not permission to silently choose whichever side is more convenient.

## Inspection surfaces

Compare, when present:

- command help, README, operator guides, examples, changelogs, and generated docs;
- actual entrypoints, parser definitions, dispatch, defaults, configuration precedence, feature flags, and runtime behavior;
- packaging metadata, completion definitions, API or plugin registries, deployment instructions, and compatibility promises.

## Divergence classes

- `documented_not_implemented`: docs claim a capability the executable path does not provide;
- `implemented_not_documented`: code exposes material capability absent from operator-facing docs;
- `behavior_mismatch`: docs and code describe different semantics, ordering, outputs, errors, or side effects;
- `config_default_mismatch`: documented defaults or precedence differ from executable values;
- `entrypoint_mismatch`: docs point to a command, flag, plugin, or route that is absent or differently wired;
- `unknown`: evidence is incomplete or conflicting.

## Reconciliation law

1. Cite both the documentation claim and code/runtime observation.
2. Determine which source is authoritative for the current release.
3. Reconcile only when the correction is inside the locked change map and validated behavior is clear.
4. When reconciliation is not easy, safe, or in scope, preserve a `docs_code_divergence` finding in `evidence/CLI_REVISION_SYNTHESIS.json`.
5. Also render the finding in `evidence/DOCS_CODE_DIVERGENCE_FINDINGS.md` and append its ID to the PR body when a PR pack is produced.
6. A release-blocking divergence prevents `PR_READY`; a non-blocking out-of-scope divergence may remain only when its owner, next action, and evidence are explicit.
7. Never erase a divergence by weakening documentation, hiding behavior, or labeling incomplete evidence as resolved.

## Required finding fields

Every divergence finding records: ID, severity, documentation claim, code observation, evidence, divergence class, scope, owner, reconciliation status, recommended action, release impact, and linked revision target.
