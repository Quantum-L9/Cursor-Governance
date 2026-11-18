```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/L9-Ops-MCP
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/Cursor-Governance
  unlisted_repositories: no_access
```

# M: legacy L9-Ops-MCP mirror compatibility

**Executor:** one pool agent. **Activation dependency:** B release verified. Independent of C, so both may execute concurrently. One writer in this repo. While #44 is open, do not edit `.github/CODEOWNERS`, `.github/dependabot.yml`, or `.github/pull_request_template.md`. Recheck #43, #42, #40, and #38 before editing. `PR_STACK` stays empty. See `09_EXECUTION_BINDING.md`.

## Observed input

`ORG_INVARIANTS.yaml` is a small v1-style `org_invariants` block, not a complete v4 mirror. Its source points to `Cursor-Governance/blob/main/ORG_INVARIANTS.yaml`. Current `scripts/validate_org_invariants.py` matches text `owner: Quantum-L9` or `allowed_owner: Quantum-L9` and forbidden owner patterns. It is not a cryptographic release verifier.

## Work contract

- Inspect all actual consumers and CI callers at current repo SHA; preserve the schema and owner prohibition those callers need.
- Change provenance to actual `.github` immutable B release and add a deterministic, minimal compatibility verifier or verified projection as supported by the repo. Do not claim byte-identical canonical policy if only reduced owner block retained; certify reduction only against a verified full source.
- Preserve owner `Quantum-L9`, forbidden personal repository destinations, fail-closed birth/publish and present native script entrypoints. Add valid/invalid owner and tampered digest/mutable ref negative fixtures.
- Document dual compatibility and block if secure release verification cannot be implemented without source-owner changes. Do not downgrade an existing guard to get a green test.
- Publish/merge through real `make pr` and actual authorizations. No changes to unlisted consumers.

## Done

The original owner-denial still works, the canonical pointer is immutable `.github`, and direct release provenance is verified rather than merely text-matched. Record accepted legacy view and its exact derivation. Otherwise preserve existing protections and report **M blocked**, not fake cutover.
