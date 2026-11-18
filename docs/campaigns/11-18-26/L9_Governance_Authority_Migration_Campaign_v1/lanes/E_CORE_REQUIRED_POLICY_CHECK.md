```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/l9-ci-core
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/l9-ci-sdk
    - https://github.com/Quantum-L9/Cursor-Governance
  unlisted_repositories: no_access
```

# E: enforce released org policy under the already-required Core check

**Executor:** one pool agent in its own `l9-ci-core` worktree. **The pull request may open after A merges.** It must not merge required-job enforcement until B's immutable signed release is on `.github` `main`. A missing release must not become a green skip. An unmerged pull request is the only safe state before B. No SDK writes. See `09_EXECUTION_BINDING.md`.

## Observed current enforcement seam

Org ruleset 21895545 requires `Analyze (central Core)` in `l9-ci-core/.github/workflows/org-ci.yml`. That exact job is non-skippable for relevant PR change events and already orchestrates technical gates. It does **not yet prove** enforcement of the new L9-ORG policy. `l9-ci-core/AGENTS.md` keeps Core orchestration/central defaults distinct from SDK technical evaluation. Do not insert a seventh governance-default config into the six-file registry.

## Work contract

- Read current Core source, event classes, job dependencies, exact revision checkout, output/result reduction, required check names and trust model. Identify minimal Core-owned action/step for immutable canonical policy verification on the exact PR head and target repository identity.
- Bind signed B policy release, SHA, digests and approved signer/attestation as applicable. Declared consumer `.l9/ci.json` or checkout-ed policy cannot grant weaker organization mode. SDK remains authoritative for its own technical gate.
- Policy FAIL or critical UNKNOWN must fail the **actual required job**. No `continue-on-error`, `if: always()` masking, skipped-success path, optional parallel status or advisory-only summary. Retargeted base and updated head must recompute; do not reuse stale green from older subject. Write read-only on `pull_request` and preserve minimum required permissions.
- Integrate with existing event and class semantics without adding unnecessary workflow/registry layers. Verify policy-applicability and dynamic inventory from upstream owner; do not mistake no local caller for exemption. Preserve acceptable performance and valid CIs.
- Prove native Core validation and controlled fixtures: valid policy passes; tampered digest, unknown critical assertion, wrong owner, missing release, bad identity/unauthorized waiver fail. Then demonstrate on actual required run as F controls enable. A unit test does not prove GitHub merge blocking.
- If signatures require a nonexisting external verifier, privileged secrets or SDK-owned semantic change, stop that subproblem and record the exact owner/permission. Do not implement a lookalike signature verifier or mutate SDK without separate authority.
- Publish using verified Cursor SSOT `make pr`, merge under current required checks, bind Core final SHA.

## Done

Core's required context deterministically reflects signed org-policy verdict for applicable targets, valid CI stays valid, bad fixture actually makes required job fail and policy source cannot be replaced by consumer input. F still owns proof of live org ruleset merge denial and scope.
