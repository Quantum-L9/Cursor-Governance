```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Cursor-Governance
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/l9-ci-core
  unlisted_repositories: no_access
```

# C: Cursor-Governance consumes canonical policy while owning its own operation

**Executor:** one pool agent. **Activation dependency:** B verified immutable policy release. **One Cursor worktree writer** branched from fetched `origin/main` `48c9e134bfbb5520adc18645ded9e68cdcb1056a`, not from local `main` `39fd2492b314a2b6b132f393af61a27b47764dd1`. While #1038 is open, do not edit `AGENTS.md` or `CANONICAL_LAW.md`. While #1036 is open, do not edit `.github/CODEOWNERS`, `.github/dependabot.yml`, or `.github/workflows/governance.yml`. Recheck #1037 before editing. `PR_STACK` stays empty. Do not push onto those branches. Current global operating-plane @2 profile stays separate and never gains policy admission by implication. Holds are in `09_EXECUTION_BINDING.md`.

## Editable surfaces

Existing `ORG_INVARIANTS.yaml`, `governance/ASSERTION_TYPES.yaml`, `governance/authority-bindings/`, `governance/POLICY_MODEL.md`, `governance/TRUST_MODEL.md`, `governance/CHANGE_PROCESS.md`, `schemas/org-invariants.schema.json`, `releases/POLICY_RELEASE.schema.yaml`, `ops/scripts/validate_org_policy.py`, `tests/org_policy/`, `.github/workflows/validate-org-policy.yml`, policy-facing `AGENTS.md`, `CANONICAL_LAW.md`, docs root/index, and only actual action guard paths proven affected by integration. Do not bulk-edit skills/adapters or unrelated local contract families.

## Work contract

- Resolve Cursor baseline exact SHA and open PR changed-file overlap. Preserve true local architecture authority, agent modes, L4, program execution and one `make pr`. Correct only the claims that `Cursor-Governance` owns **organization** normative policy. It remains local canonical for its operating implementation.
- Consume the verified B release at a separate local versioned org-policy binding. Hold immutable upstream source SHA, actual full payload and schema/registry digests, verification mechanism and applicable action classes. Existing `l9.projection/cursor-governance-operating-plane@2` remains admitted semantics and independently checked current. Do not pretend the org-policy release is now a ninth semantic source class.
- Migrate `ORG_INVARIANTS.yaml` into a derived, read-only mirror if genuinely needed by existing callers; preserve valid legacy fields and test them. Strip `canonical:true`, author role and claims of self-versioning global policy. Align sibling normative registry/schema/release artifacts with consumption instead of leaving duplicate editable canon.
- Bind the actual governance-sensitive actions: CTO execution proposals/dispatch, architect/planner delegated decisions, coding agent permissions, adapter activation, L4/publish, repo birth/owner routing and bypass. Map each to earliest owned gate and admitted global semantic vs org-policy selector, with allowed/denied fixtures. An agent's own report is not proof of gating.
- Preserve valid authorized autonomous actions without repeated human approval. Human exact owner authorization remains for actual governance admission/merges, not ordinary agent plans. An adapter may narrow its behavior but never widen global policy authority.
- Retarget existing local org-policy tests/workflow. Demonstrate positive and negative immutability/unknown critical/forbidden repo destination, plus normal `make pr` behavior. Run target's actual documented tests, not a guessed script; publish through live SSOT, capture PR and merge receipts.

## Done

No active Cursor-as-global policy claim, consumer binding is current and authenticated, local operation remains functional, governed action denies correctly, resulting PR is merged under required rules. Report an unproven host hook as UNVERIFIED, not enforced. No mass repo rollout is part of C.
