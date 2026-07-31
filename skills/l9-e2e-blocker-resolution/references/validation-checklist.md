<!-- L9_META
l9_schema: 1
parent: l9-e2e-blocker-resolution
layer: reference
role: validation_contract
tags: [e2e, validation, checklist, zero_stub]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Validation Checklist

## Required before reporting complete

- [ ] Canonical proof command(s) discovered from repo ground truth (or user-supplied).
- [ ] At least one proof command executed (or explicitly blocked before run with reason).
- [ ] Every failure classified: fixable / external / out-of-scope.
- [ ] Fixable items either fixed + re-run, or deferred with explicit reason.
- [ ] No secret values written to docs, TODO, git, or logs intentionally.
- [ ] Brief written or updated at the chosen `docs/…` path.
- [ ] Brief includes commands run, fixed list, remaining blockers table, gap checklist.
- [ ] Root `TODO.md` has a **session reference** section linking the brief.
- [ ] Final report includes Fixed | Remaining | Files | Operator next steps.
- [ ] No unsupported “e2e green / production ready” claim if remaining blockers exist.

## Reject completion if

- Brief missing while external blockers remain
- TODO entry missing or does not link the brief
- Credentials invented or pasted into artifacts
- Disposable remote mutation performed without explicit user confirmation
- Hardcoded another repo’s script names when this repo defines different ones
