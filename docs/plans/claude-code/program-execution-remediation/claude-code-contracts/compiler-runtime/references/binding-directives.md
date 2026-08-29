<!-- L9META
parent: claude-coding-contract-compiler
layer: reference
role: bindingdirectives
version: 1.0.0
updated: 2026-07-12
-->

# Binding Directives

Load at Step 0 of every workflow. Activate applicable directives. Report in delivery.

| Directive | Reference | Activates |
|---|---|---|
| Fail-Closed | kernel-fail-closed.md | always |
| Claude-Fill-Policy | claude-fill-policy.md | always |
| Scope-Lock | kernel-scope-lock.md | always |
| Validation Evidence | validation-evidence.md | validate, harden, package |
| Recursive Harden | kernel-recursive-harden.md | harden mode only |

## Activation Report Contract
```yaml
binding_directives_applied:
  fail_closed: active            # always
  scope_lock: active             # always
  validation_evidence: active | not_applicable
  recursive_harden: active | not_applicable
violations: none | [ ... ]
```

## Non-Negotiables (inherited from source contract)
- Agent may not push, open PR, merge, or change repo settings.
- No LLM in gate registration, planning, hashing, or promotion evaluation.
- Fail closed on any missing/malformed/mismatched/unknown required result.
- Any control relaxation requires a migration record, never a silent edit.
