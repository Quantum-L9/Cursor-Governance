# CTO final evidence template

The CTO must fill this from real tool outputs. Do not copy snapshot values into observed completion fields.

| Topic | Required observed evidence | Status |
|---|---|---|
| Authority | .github/Compiler/Cursor current main SHA, semantic source identity, effective operator authority | UNRUN |
| .github #255 | live latest head, CI/reviews, method, merge commit, confirmed candidate path | UNRUN |
| Cursor #1011 | live latest head, CI/reviews, ancestry-safe merge commit | UNRUN |
| Cursor #1030 | live stacked base transition, generated bundles and receipt verification, merge commit | UNRUN |
| v1 scoped admission | `strategy/` final main commit and five raw hashes vs approved manifest, exact owner decision | UNRUN |
| Compiler | exact producer SHA, source binding method, view artifacts/receipts, negative controls, replay | UNRUN |
| CTO | active `/lcto`, composed verified operator view digest and decision witness | UNRUN |
| Architect | exact mode, source digest and permission proof | UNRUN |
| Planner | approved Plan Keeper identity, merged #1011/#1030, no Plan rewrite | UNRUN |
| Meta Planner | exact advisory consumer binding or explicit BLOCKED reason | UNRUN |
| Coding Agent | six delegated obligations, no upstream leakage, negative credential/ACL evidence | UNRUN |
| Full system | CTO-owned integration test at combined HEAD; no collision or forbidden global changes | UNRUN |

**Final statuses:** separate `MERGED`, `ADOPTED_OPERATOR_SCOPED`, `PRODUCED_VERIFIED`, `CONSUMER_BOUND`, `HOST_ACTIVE`, `BLOCKED` and `UNKNOWN`. Never collapse them into a single "done" boolean. End with one smallest necessary next transition only when incomplete.

## Required closeout state machine (per role)

Report each role separately using these **evidence descriptions**, not a fabricated single readiness field:

- `SOURCE_APPROVED` means exact operator content approved, **not** installed.
- `SOURCE_ADOPTED` means the approved bytes are verified on `.github/main` with scoped decision record.
- `PRODUCER_VERIFIED` requires an actual producer receipt plus independent source/digest/selector validation.
- `CONSUMER_VERIFIED` requires a real host-independent consumer verifier and admissible global bundle.
- `HOST_ACTIVE` additionally requires live opt-in mode, actor authorization, decision behavior and access limitations confirmed at exact current revisions.
- `BLOCKED_PRIVACY` applies to Coding Agent while repository-wide source access remains possible even if its view is projection-minimized.
- `BLOCKED_NO_CONSUMER` applies to Meta Planner if no actual target mode exists.
- `MERGE_PENDING` is per new PR when current merge enforcement lacks applicable authorization.

Record not only `status` but subject IDs, revisions, raw hashes, receipt paths, results and unresolved criteria. No evidence available => `Unknown`; no automated paper PASS.

| .github writer path | Current CTO child prompt prohibition vs observed actually authorized `.github` authoring/publishing actor, branch and gate owner | BLOCKED_UNTIL_PROVEN |

**Important:** #255 candidate merge readiness does not establish an actor permitted to create the new `strategy/` adoption PR. Track separately; no fiction that a read-only child's lane header grants GitHub write.
