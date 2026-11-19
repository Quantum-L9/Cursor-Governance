# Real organization enforcement and rollout contract

## What already exists

The observed active org ruleset 21895545 requires `Analyze (central Core)` from `Quantum-L9/l9-ci-core/.github/workflows/org-ci.yml`. Its API representation has `strict_required_status_checks_policy=false` and an `OrganizationAdmin` always-bypass actor. The committed ruleset JSON says strict true, zero bypass actors and excludes `.github`; determine whether the divergence comes from API shape, targeting, deployed drift, permissions or history. Cursor has additional main-protection ruleset 20855699. Do not infer live restrictions solely from committed JSON.

`l9-ci-core` owns required-workflow orchestration, central governance defaults and GitHub trust boundaries. `l9-ci-sdk` owns capability detection, technical gate evaluation and deterministic technical evidence. Consumer repos may not set organization CI modes/required checks, and the Core-owned `resolve-governance/defaults/` contract has exactly six allowed files; do not add a seventh policy YAML there by convenience. `.github` owns canonical policy and ruleset intent, not a competing copy of `org-ci.yml`.

## Minimal enforcement integration

1. **Source first.** Resolve the exact approved immutable `.github` policy bundle and existing Core target workflow/action composition. Identify the earliest Core-owned read-only policy evaluation point within `Analyze (central Core)` that has the target repository identity, event SHA, control scope and source authenticity.
2. **Prefer the existing required context.** Enforce applicable org-policy predicates in the existing `Analyze (central Core)` job without short-circuiting legitimate SDK technical gates. A policy FAIL or material UNKNOWN requiring block must cause that job to fail; a skipped step, successful downstream job, advisory summary or differently named optional check cannot satisfy this obligation. This is the recommended smallest implementation, not permission to change Core before verification. Lane E opens that pull request as soon as A's or B's head SHA exists and pins that open head. The CTO does not merge it, and E does not wait for a GitHub merge. A missing release must not become a green skip.
3. **Versioned consumption.** Bind to an approved immutable policy release; verify digest, owner authorization and signer/attestation per admitted source policy. Do not allow a PR-controlled local `ORG_INVARIANTS.yaml`, local `.l9/ci.json`, unknown waiver or mutable branch ref to replace the canonical payload or waive its evaluation.
4. **Coverage and classification.** Use `.github` repository registry and actual GitHub ruleset target/application information. Include archived and forks in inventory; apply operational requirements only where applicable and document why not. `self_governed` describes *CI distribution ownership*, not exemption from required organization law. Preserve legitimate class-level exclusions from duplicated workflow seeding.
5. **Avoid new CI architecture.** No extra org workflow, new SDK technical governor, per-repo copied governance jobs, or a global activation script absent a proven minimal necessity. Changes to `l9-ci-sdk` require a separate bounded authorization and are not in this campaign. If Core cannot verify signature or a required predicate without changing SDK's semantic ownership, block that seam and request a separate exact owner resolution, not an in-scope SDK mutation.

## Threat tests that decide enforcement status

| Test | Observable condition for PASS |
| --- | --- |
| Valid allowed PR | Required Core check runs and passes the *same exact PR head and base* after policy evaluation. |
| Wrong canonical owner/policy digest | The actual required Core job fails; GitHub refuses the merge through applicable live ruleset. |
| Unknown critical assertion | Required Core fails rather than silently reporting advisory/skip. |
| Scope/waiver spoof by PR metadata | Consumer cannot assert itself ungoverned or bypass required policy. |
| Invalid personal owner publication route | At the actual governing gate, operation denied and audit trace emitted. |
| Retargeted PR, replayed event or updated head | Old passing check cannot cover changed subject; new subject triggers fresh verification. |
| Class with no locally seeded governance caller | Still subject to the applicable organization required-workflow, proved through live scope. |
| Archived/forked identity | Included in census; enforcement applicability and any exclusion are explicit, never silently absent. |
| Privileged bypass path | Enumerated permitted principals, policies, audit evidence and live state match approved break-glass contract; no bypass marked safe without proof. |
| Infrastructure/identity unavailable | Required failure does not become a green skip; report the exact blocker and restore legitimate operations when recovered. |

## Sequenced pilot and organization expansion

- Pilot P0: `.github` policy owner. If current org ruleset intentionally excludes it, prove protection through a **separate live applicable** ruleset and owner-controlled merge gate; do not falsely assert it inherits an excluded required workflow.
- Pilot P1: `Cursor-Governance` operating plane. Prove its policy source, normal agentic operation, denied invalid PR and owner-authorization condition.
- Pilot P2: `L9-Ops-MCP` compatibility consumer. Verify historical owner/birth prohibition plus new immutable provenance. If a more appropriate ordinary repo is needed as a third CI class sample, obtain read-only evidence first; do not mutate an unlisted repository.
- Pilot P3: observed self-governed and ordinary-class repositories, **read-only coverage or controlled non-mutating scope verification** unless separate write permission is granted. Prove policy applies to their CI even without copied caller. Capture false positives and actual required status names.
- Only after pilots have actual good/failing evidence and all critical dependency checks pass, update `.github` ruleset source as needed and apply through its existing authorized ruleset workflow. Recheck **live** API state, ruleset applicability and bypass actors. Reconcile config-to-live drift with evidence, not blind REST updates.

This campaign does not require editing all org consumer repositories. Universal control is proven, when possible, at the **organization-owned ruleset and Core required workflow**, plus separate owned publish gates. Any control not implemented or incapable of prevention at that boundary must remain unproven and be stated in the final report.

## Recoverability, change control and no false green

Before changing active required checks, prove that a real passing repository remains mergeable and a known-bad head is refused. Record current config, latest last-known-good Core revision, rollback mechanism and permission to restore. Reversal is through the owning `.github` ruleset application and Core release paths, not a hidden manual bypass. No automatic relaxation of `L9-ORG` critical requirements during rollback. Repo admins with platform bypass do not provide independent enforcement proof until bypass is controlled/audited.

Time-sensitive source checks, stale approval, incomplete API pagination, missing permission, unsigned bundle, deleted source, absent required run, or indeterminate job conclusion are `UNKNOWN/BLOCKED` at the affected gate, not `PASS`.
