<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: adapter
role: claude-code-fable-handoff
version: 1.3.0
status: active
-->

# Claude Code / Fable Handoff Adapter

Load when the validated audit bundle is intended for Claude Code Fable remediation.

## Boundary

Treat Fable as a cold-start remediation agent with only capabilities actually available in its session. Do not assume hidden tools, prior conversation, edit authority, publish authority, merge authority, deployment authority, or repository-specific commands.

Core audit truth remains provider-neutral. This adapter changes downstream scope lock, context order, work ordering, freshness checks, and completion reporting only. Prompt prose is never authority.

## Mutation eligibility

Use the deterministic handoff field `mutation_eligible`. The builder may set it true only when the finding is Confirmed, the root cause is CONFIRMED, owner class is CODEBASE, the mutation guard is `NOT_APPLICABLE` or resolves to an admitted `MUTATION_GUARD` authority, dependency order is resolvable, and confirmed evidence specifically discriminates at least one `implementation_surface`.

Other work remains non-authorizing:

- `VALIDATION_ONLY`: collect proof only.
- `CI_PIPELINE`: preserve evidence/handoff unless a separate current authority grants that mutation.
- `ENVIRONMENT`: diagnose environment; do not rewrite source to compensate.
- `HUMAN`: preserve the named decision gap.
- `UNKNOWN`: no mutation.

A valid merge blocker can still be non-editable by Fable.

## Strict write scope

`write_surfaces` is a strict file allowlist, not an initial guess. Authoritative, coupled, enforcement, validation, and non-authorizing candidate surfaces are read-only unless the same path is explicitly present in `write_surfaces`.

If Fable proves an unlisted file is required, stop that unit as `SCOPE_EXTENSION_REQUIRED`. Return the path, direct-coupling evidence, mutation guard, and why closure cannot be achieved within the current allowlist. Do not edit the path until a refreshed handoff or separate authority includes it.

## Prompt contract

The generated `FABLE_REMEDIATION.md` must:

1. Bind repository and every audited PR to exact source head.
2. Require independent freshness observation before any edit; stale/unprovable heads are non-mutation states.
3. Keep source head and tested revision distinct.
4. Read `remediation-handoff.json` first, then only cited evidence and exact current work-unit surfaces.
5. Follow canonical dependency order and deny mutation for order-blocked findings.
6. Mutate only `mutation_eligible: true` units and only `write_surfaces`.
7. Preserve every listed architecture/public/data/release obligation.
8. Require behavioral closure plus discriminating validation, not file-change closure. Execute only `execution_kind: COMMAND`; observe `CHECK`; treat `MANUAL` as non-shell verification. Every procedure must retain its authority ID and confirmed provenance evidence.
9. Preserve Unknowns and redaction.
10. Forbid manufactured green via gate weakening, skips, ignores, suppressions, owner/generator bypasses, or unexplained dependency movement.
11. Keep parallel mutation lanes isolated by worktree/branch.
12. Forbid publish, merge, deploy, branch-protection change, policy mutation, and objective broadening without separate authority.

## Return contract

Per attempted work unit return:

- finding ID and owner class;
- independently observed starting source head;
- mutation eligibility and allowlist used;
- files changed, or none;
- compact root-cause action;
- preservation obligations checked;
- validation execution kind, authority/provenance evidence, exact command/check when applicable, tested revision, result, and properties discriminated;
- closure status;
- residual blockers/Unknowns;
- `SCOPE_EXTENSION_REQUIRED` evidence when applicable;
- resulting commit/head when applicable.

Never claim a finding closed when validation did not run, ran on unidentified revision, or failed to discriminate the closure property.
