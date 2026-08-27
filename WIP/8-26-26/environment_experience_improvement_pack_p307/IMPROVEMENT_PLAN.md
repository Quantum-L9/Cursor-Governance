# Improvement Plan — Current Forward Work

Only unresolved/current work appears in the active roadmap. Completed source work is retained below
for provenance but is not scheduled again.

> **Delivery overlay (2026-08-27, `main@498dcaa`).** The `**Status:**` line on each entry is the
> record's *roadmap classification at pack generation*, not its delivery state. Delivery state
> lives in [`PROGRESS.md`](PROGRESS.md) / [`progress.yaml`](progress.yaml) and is authoritative.
> **CI-007** and **CI-026** are `done` and are no longer scheduled, despite the `ACTIVE` line
> below. Fourteen further records are `partial` with named residuals — read the overlay before
> scheduling any entry here.

## Execution order

### CI-002 — Make bootstrap projection ownership-aware and non-destructive to tracked repo content
**Status:** ACTIVE  
**Priority band:** 0  
**Depends on:** none

Detect repository-owned tracked paths before projection. Project machine-local rules/hooks/state only to non-repo-owned locations; ignore only genuinely generated/untracked paths. Never blanket-ignore or replace a repository-owned .claude tree.

**Sources:** P1/improvements/IMP-06, P1/improvements/IMP-07, P3/improvements/B1, P3/improvements/B2, P6/improvements/BOOT-3, P9/improvements/I-BS-01

### CI-004 — Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components
**Status:** ACTIVE  
**Priority band:** 0  
**Depends on:** none

Bind receipts to container/session lifecycle and governance revision; invalidate stale receipts; re-probe DEGRADED components; retain per-component reason, evidence, log path, and retry/remediation state.

**Sources:** P1/improvements/IMP-10, P3/improvements/B5, P4/improvements/IMP-03, P4/improvements/IMP-04, P6/improvements/BOOT-1, P7/improvements/IMP-07, P8/improvements/I-BF-01, P8/improvements/I-BF-02, P8/improvements/I-BF-03, P9/improvements/I-BS-04

### CI-006 — Resolve authority-sensitive environment drift at the actual source
**Status:** OPEN_DECISION  
**Priority band:** 0  
**Depends on:** none

Trace each effective value to its source, separate authority-widening drift from cosmetic drift, make repair reachable or explicitly human-only, and record the governing value. The intended AUTONOMOUS_MERGE value remains an open decision.

**Sources:** P1/improvements/IMP-03, P3/improvements/A1, P4/improvements/IMP-08, P6/improvements/ENV-1, P7/improvements/IMP-03, P8/improvements/I-EL-01, P8/improvements/I-EL-02, P9/improvements/I-EL-03

### CI-007 — Replace standing breakglass environment strings with scoped expiring receipts
**Status:** ACTIVE  
**Priority band:** 0  
**Depends on:** none

✅ **Delivered** (PR#304/#305, and PR#306 for the readiness probe). Not scheduled — see `PROGRESS.md`.

Represent exceptional publish authority with issuer, reason, scope, issuance time, expiry/consumption semantics, and session-start visibility; do not normalize a one-time grant into silent permanent configuration.

**Sources:** P1/improvements/IMP-04, P6/improvements/ENV-2, P9/improvements/I-EL-06

### CI-008 — Reconcile make pr doctrine with consumer-repository command contracts
**Status:** OPEN_DECISION  
**Priority band:** 0  
**Depends on:** none

Choose one canonical contract: ship a functioning pr target into every governed consumer or relax the absolute doctrine to a defined supported fallback. Do not retain contradictory absolutes.

**Sources:** P1/improvements/IMP-13, P3/improvements/C4, P6/improvements/BOOT-6, P9/improvements/I-BS-08

### CI-009 — Establish one project interpreter/toolchain authority and verify importability before READY
**Status:** ACTIVE  
**Priority band:** 0  
**Depends on:** none

Resolve the project interpreter/venv deterministically, pin checker versions to the same authority, export durable PATH/PYTHONPATH only through one loader, and make readiness end with repository import/command smoke tests.

**Sources:** P2/improvements/IMP-E1, P2/improvements/IMP-E2, P2/improvements/IMP-E3, P3/improvements/A2, P3/improvements/A3, P3/improvements/A4, P3/improvements/A5, P5/improvements/IMP-003, P5/improvements/IMP-008, P7/improvements/IMP-04, P9/improvements/I-EL-05

### CI-010 — Make broker authentication and reachability diagnosable
**Status:** ACTIVE_WITH_UNKNOWN  
**Priority band:** 0  
**Depends on:** CI-004

Ensure CLAUDE_SESSION_JWT is issued or its absence is a hard named prerequisite failure; split broker states into DNS/unreachable, proxy-denied, and upstream-error before deciding allowlist remediation.

**Sources:** P1/improvements/IMP-05, P9/improvements/I-EL-01, P9/improvements/I-EL-02

### CI-001 — Publish and enforce the real GitHub REST/GraphQL capability boundary
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** none

Document REST and GraphQL independently; use a REST auth probe; give merge/PR helpers REST-capable probe/execution paths; report probe-blocked separately from stack/auth unknown.

**Sources:** P1/improvements/IMP-01, P1/improvements/IMP-02, P1/improvements/IMP-11, P1/improvements/IMP-12, P2/improvements/IMP-A1, P3/improvements/C1, P3/improvements/A6, P4/improvements/IMP-11, P7/improvements/IMP-02, P8/improvements/I-WT-02, P9/improvements/I-EL-04

### CI-003 — Make the Stop hook ownership-aware instead of residue-blind
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** CI-002

Scope stop-hook checks to authored changes in the active repo and explicitly exclude bootstrap-owned paths without masking tracked authored content.

**Sources:** P1/improvements/IMP-08, P3/improvements/B3, P9/improvements/I-BS-02

### CI-005 — Make memory health transport-specific and continuity task-bearing
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** CI-004

Use one authoritative probe per memory transport, distinguish nothing-to-write from failed writes, write a task-bearing completion PICKUP, prioritize the target repo in hydration, and name skipped repos/empty state explicitly.

**Sources:** P1/improvements/IMP-09, P4/improvements/IMP-05, P6/improvements/BOOT-2, P6/improvements/BOOT-4, P6/improvements/BOOT-7, P7/improvements/IMP-09, P9/improvements/I-BS-05, P9/improvements/I-BS-06

### CI-012 — Gate rules and MCP config on actual surface capabilities
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** CI-004

Validate MCP config schema before session start and annotate projected rules with capability preconditions when their mechanism is unavailable, while preserving the rule intent.

**Sources:** P4/improvements/IMP-07, P9/improvements/I-BS-03, P9/improvements/I-BS-12

### CI-013 — Preserve fail-closed destructive/staging gates while making denials actionable
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** none

Keep unresolved/empty destructive targets fail-closed. Add literal scoped cleanup paths, reachable authorization where policy permits, hook stderr, and per-stage denial reporting for compound commands. Do not weaken the unresolved-expansion invariant.

**Sources:** P3/improvements/B4, P3/improvements/C3, P7/improvements/IMP-10, P9/improvements/I-BS-07, P9/improvements/I-BS-10

### CI-015 — Name and enforce the authoritative governance checkout
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** none

When multiple governance trees exist, print both revisions, name the one from which rules resolve, and remove/relabel non-authoritative clones where possible.

**Sources:** P3/improvements/C2, P8/improvements/I-WT-01, P9/improvements/I-BS-13

### CI-016 — Make L4/release receipts resolve paths, branch, and head dynamically
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** none

Bind receipts to the released repository, current branch/head, and actual template path; make stale SHA/branch bindings visible before they block publication.

**Sources:** P1/improvements/IMP-14, P3/improvements/B6, P9/improvements/I-BS-09

### CI-017 — Validate generated-artifact membership and report all drift in one pass
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** none

Make validation tolerate legitimate index/worktree states, catch missing manifest membership at file creation, and report every generated artifact out of step in one run.

**Sources:** P2/improvements/IMP-B1, P4/improvements/IMP-09, P8/improvements/I-WT-03

### CI-018 — Make local CI parity and hooks first-class provisioning
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** CI-009

Install the actual hooks/gates, define one local CI-parity command, and keep its blocker list aligned with remote CI so local green means something.

**Sources:** P2/improvements/IMP-B2, P2/improvements/IMP-R2, P5/improvements/IMP-001, P7/improvements/IMP-01

### CI-023 — Collapse variable-loading authorities into one reproducible loader contract
**Status:** ACTIVE  
**Priority band:** 1  
**Depends on:** CI-009

Define one loader/precedence contract that works in non-interactive shells, fails fast on missing required configuration, guards source-without-call misuse, and removes inert/documented-but-unused variables.

**Sources:** P4/improvements/IMP-01, P4/improvements/IMP-02, P5/improvements/IMP-002, P5/improvements/IMP-005, P5/improvements/IMP-006, P6/improvements/LOADER-2

### CI-011 — Bound large MCP responses with field projection/pagination
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** none

Add projection, pagination, or bounded summaries to large file/job methods so tool responses remain inside the interaction envelope.

**Sources:** P1/improvements/IMP-15, P2/improvements/IMP-A2

### CI-014 — Make target repository/cwd explicit for governance CLIs
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** none

Pass the target repository explicitly to governance commands and avoid procedures whose correctness depends on persistent shell cwd.

**Sources:** P4/improvements/IMP-06

### CI-019 — Coordinate concurrent writers on shared PR branches
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** none

Detect/serialize or otherwise coordinate cross-machine writers before push so shared head branches do not repeatedly non-fast-forward.

**Sources:** P7/improvements/IMP-06

### CI-021 — Make session-experience and skill-usage logging observable
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** none

Fix logging matchers/paths and emit enough session-start evidence to distinguish inactivity from a broken collector.

**Sources:** P5/improvements/IMP-011, P9/improvements/I-BS-11

### CI-022 — Provision or explicitly declare service-backed integration-test dependencies
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** CI-009

Provision declared services such as Neo4j when integration proof is expected, otherwise surface the unavailable coverage before tests run.

**Sources:** P9/improvements/I-EL-07

### CI-024 — Repair or remove foreign/stale bootstrap and deploy entrypoints
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** none

Choose one documented provisioning path and ensure bootstrap/deploy targets belong to and execute against the actual repository instead of missing or foreign scripts.

**Sources:** P2/improvements/IMP-B3, P5/improvements/IMP-004, P5/improvements/IMP-009

### CI-025 — Provide sanctioned cleanup of generated/cache residue
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** CI-013

Keep generated/cache debris out of gate inputs and provide a permission-safe cleanup path that does not weaken general destructive-command policy.

**Sources:** P5/improvements/IMP-010, P7/improvements/IMP-05, P7/improvements/IMP-08

### CI-028 — Improve dependency provisioning evidence and determinism
**Status:** ACTIVE  
**Priority band:** 2  
**Depends on:** CI-009

Use constraints or equivalent deterministic dependency resolution, timestamp dependency logs, and make the provisioning step emit a real exit status/readiness result.

**Sources:** P6/improvements/BOOT-5, P8/improvements/I-EL-03

### CI-020 — Expose notification age when queued state is delivered
**Status:** ACTIVE  
**Priority band:** 3  
**Depends on:** none

Stamp queued notifications with age at delivery so superseded instructions are recognizable before action.

**Sources:** P9/improvements/I-BS-14

### CI-026 — Support safe on-disk aliases for dot-prefixed repositories
**Status:** ACTIVE  
**Priority band:** 3  
**Depends on:** none

✅ **Delivered** — `Quantum-L9/.github` is attached as a session source. Not scheduled — see `PROGRESS.md`.

Allow repositories such as .github to be attached under an explicit safe alias rather than blocking the entire org-governance class.

**Sources:** P1/improvements/IMP-16

### CI-027 — Correct rule rationale that no longer matches container reality
**Status:** ACTIVE  
**Priority band:** 3  
**Depends on:** none

Preserve the pinned-interpreter requirement but remove or correct stale rationale that system Python lacks PyYAML when that premise is false.

**Sources:** P1/improvements/IMP-17

### CI-029 — Persist repeatable cross-repo E2E fixtures
**Status:** ACTIVE  
**Priority band:** 3  
**Depends on:** none

Move scratchpad-only fixture builders required for repeatable validation into an owned repository surface.

**Sources:** P8/improvements/I-WT-04

### CI-030 — Improve receipt CLI ergonomics without multiplying state owners
**Status:** ACTIVE  
**Priority band:** 3  
**Depends on:** none

Give receipt CLIs a default/status-style read action while retaining one canonical receipt store and schema.

**Sources:** P6/improvements/LOADER-1

### CI-031 — Keep repo documentation and tracked-path hygiene synchronized
**Status:** ACTIVE  
**Priority band:** 3  
**Depends on:** none

Correct stale hook counts and prevent case-only duplicate tracked paths that make documentation/checkout behavior platform-dependent.

**Sources:** P2/improvements/IMP-R1, P2/improvements/IMP-R3

### CI-032 — Give slow validation units explicit headroom without weakening total proof
**Status:** ACTIVE  
**Priority band:** 3  
**Depends on:** none

Adjust per-file RPC/test ceilings for known slow tests while keeping aggregate validation coverage intact.

**Sources:** P4/improvements/IMP-10

### CI-100 — Investigate why PR #70's workflow runs were gated in action_required
**Status:** ACTIVE_CONTEXT_SPECIFIC  
**Priority band:** 4  
**Depends on:** none

Read the repository and org Actions approval settings and determine whether bot-authored branches require manual approval by policy.

**Sources:** P2/improvements/IMP-C1

### CI-101 — Align the branch directive with the repository actually worked in
**Status:** ACTIVE_CONTEXT_SPECIFIC  
**Priority band:** 4  
**Depends on:** none

Align the branch directive with the repository actually worked in

**Sources:** P5/improvements/IMP-007

### CI-102 — Valid GH_TOKEN or formal surface exemption from gh-dependent gates
**Status:** ACTIVE_CONTEXT_SPECIFIC  
**Priority band:** 4  
**Depends on:** none

(a) provision openclaw PAT per rule 62 via secret plane; or (b) amend surface_profile + rules 53/62 to sanction MCP path for claude-cloud

**Sources:** P6/improvements/ENV-3

## Completed / do not repeat

- **CI-033 — Use pipefail in push/retry helpers** — source evidence says already applied. Sources: P2/improvements/IMP-A3
