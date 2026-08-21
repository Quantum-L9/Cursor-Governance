<!-- L9_META
l9_schema: 1
artifact_id: context-sensitive-git-guardrails
first_class_artifact: true
schema_family: l9_autonomy_architecture
version: 1.0.0
status: active
updated: 2026-08-20
owner: platform
layer: ops
tags: [l9, autonomy, first_class, git, guardrails]
/L9_META -->

# Context-sensitive git guardrails — metadata

**Contract:** `l9-context-sensitive-git-guardrails` v1.0.0 (mode `strict`,
default `guard_then_allow`)
**Brain:** `ops/autonomy/git_guardrails.py`
**Gate:** `ops/autonomy/local_execution_gate.py` (Claude PreToolUse + Cursor
`beforeShellExecution`)
**Delegating classifier:** `ops/autonomy/worktree_isolation_gate.py` (forced clean)
**Rule:** `rules/54-context-sensitive-git-guardrails.mdc`
**Conformance suite:** `tests/ops/autonomy/test_git_guardrails.py` (T001–T030 +
invariants I001–I017)

## Purpose

Decide git and destructive filesystem commands from the effect they would
actually have — target sensitivity, provable recoverability, blast radius —
rather than from the subcommand name. Three outcomes: `ALLOW`,
`GUARD_THEN_ALLOW` (observe, capture verified recovery, proceed), and
`DENY_REQUIRES_HUMAN` (`L9_GIT_DESTRUCTIVE_AUTHORIZED=<reason>`).

Replaces both halves of the name-based model: the blanket git execution
exemption (which allowed unrecoverable destruction) and the blanket
subcommand denials (which blocked operations that destroyed nothing).

## Not for

- Publish-path enforcement — `make pr` remains the only route to GitHub
  (`l4-local-autonomy`, `rules/48-make-pr-remediation.mdc`)
- Merge authorization — `ops/autonomy/merge_gate.py`
- Foreign-work scoop and sacred-WIP rules — `worktree_isolation_gate`
- Agent self-authorization of a destructive operation
