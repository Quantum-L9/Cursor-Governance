```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/.github
  read_only:
    - https://github.com/Quantum-L9/l9-ci-core
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/L9-Ops-MCP
  unlisted_repositories: no_access
```

# F: reconcile intended policy with active platform controls and prove cutover

**Executor:** the activating CTO session, stacked on B's open head. A pool agent must not clone, branch, or push this repository. **Dependencies mean a recorded disposition for C, M, and E,** including an open stacked pull request or `BLOCKED` with an owner and one next action. A blocked predecessor does not become `PASS`, and it does not pause F. The CTO does not merge F. The 2026-11-18 ruleset read is in `09_EXECUTION_BINDING.md`. Refresh it again before changing ruleset source. Do not treat that read as proof that a bad pull request cannot merge.

## Work contract

- Use the existing `.github` organization policy, repository class/registry, intended ruleset JSON and authorized ruleset application path. This lane may adjust `.github/policies/mandatory-files.yml`, `policies/repo-classes.yml`, `docs/ADVISORY.md`, ruleset definition and tests as needed for correctness, without introducing competing CI scripts or duplicating Core governance defaults.
- Reconcile Cursor “Policy SSOT” exemption and self-governed class distinction: distribution method can differ, normative policy applicability cannot silently disappear. Preserve existing legitimate class-specific forbidden caller paths. Do not generate per-repo workflows wholesale.
- Compare intended `rulesets/l9-canonical-ci-required.json` with live ruleset 21895545 and Cursor ruleset 20855699. Explain any `strict` / bypass / targeting discrepancies; confirm admin bypass, audit and exception evidence. Do not mutate privileged settings without active authority and tested rollback.
- Verify upstream `.github` itself is independently protected. The existing org required ruleset source declares `.github` excluded; don't claim it governs `.github` unless an actually attached live control proves otherwise. Check owner authorization for exact candidate and real required checks.
- Run P0 policy-owner, P1 Cursor, P2 L9-Ops-MCP, P3 self-governed and ordinary-class coverage/pilot as defined in `05_CI_RELATIONSHIP_AND_ROLLOUT.md`. Unlisted repos remain read-only/out of mutation scope. Record exact good/bad refs, job status and blocked merge through applicable live rulesets. Where the permission to read rulesets or see merge results is missing, mark UNKNOWN and report needed permission.
- Classify all registered org repositories, including archived/forked identities, by applicability and attached enforcement. Confirm actual check freshness, absence of cross-job success masking, bypass audit coverage and no silent waiver. Update control assurance only for genuine platform-backed evidence.
- Publish intended rule/doc changes through the SSOT `make pr` and obtain required owner decision on exact head. Apply changes only through observed authorized `.github` ruleset process and re-read live state.

## Done

Live expected controls and applicability actually match admitted policy; good case remains mergeable and bad case blocked without bypass; original `.github` is not falsely called covered by an excluding rule; operator receives complete organization coverage and bypass matrix. **No full PASS** with unverified privileged bypass, missing signed release, an unattested control, or a skipped required job.
