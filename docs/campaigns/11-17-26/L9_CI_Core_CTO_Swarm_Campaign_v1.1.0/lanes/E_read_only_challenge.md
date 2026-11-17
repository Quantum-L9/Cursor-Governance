```yaml
repository_access:
  writable: []
  read_only:
    - https://github.com/Quantum-L9/l9-ci-core
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/l9-ci-sdk
    - https://github.com/Quantum-L9/Gate_SDK
  unlisted_repositories: no_access
```
# Lane E — Independent read-only CI witness

## Role and constraint

You are one of the fixed pool coding agents, not the CTO. Register role and activate coding-agent mode before your work. **Read-only evidence assignment:** no files, branches, commits, PRs, rulesets or comments may be created or modified. No integration testing: CTO alone integrates. All reporting goes in your own transcript to CTO, not through cross-session tools.

## Investigate concurrently

1. Inventory current Core tests involved in false-green prevention, the existing full-suite parity rule, and unique release/security/SDK checks that should *not* move nightly.
2. Audit the CTO-frozen **combined** A+ B PR required-job test census for missing critical modules and repeated expensive test work; identify high-impact test modules absent from that selection and adversarial counterexamples with real file coordinates. Don't demand exhaustive Core tests on every PR merely because they exist.
3. Collect representative PR run timing/cost evidence if visible. Never estimate exact savings without actual run data.
4. Verify that Gate_SDK is an application transport SDK and not directly provisioned in Core org-ci, and that l9-ci-sdk and `.github` public-read access actually works. Read-only checks only.
5. Inspect current Core ruleset payload, source SHA and open PR conflicts; flag drift to CTO, not directly to children.

## Delivery

Report `CTO-STATUS:` with top findings ranked by concrete merge risk and source links. Report UNKNOWNs. Then `CTO-STATUS: idle` so CTO can reuse your pool slot under `CTO ASSIGN`. Do not publish a PR.
