# Per-repository PR stacking and collision-free concurrency

## The non-negotiable distinction

A PR is stackable onto a branch **in its own repository only**. EIE, CEG and optional Gate therefore each have one linear PR chain; the CTO records a cross-repo compatibility tuple of exact head SHAs. A stack is not a multi-repository merge or release.

## Per-repo branch train

- Plan each write path once per active wave. Agents edit disjoint modules and branches concurrently. A single CTO publisher scheduler assigns each finished branch a specific previous PR branch as `PR_BASE`. The first campaign PR uses an explicitly verified base (normally that repository's current default branch, after checking existing open PRs and collision policy).
- Fetch the parent branch at its exact current SHA. When needed, incorporate the parent's changes with the repository's permitted **merge** process, not unauthorized rebase or force push; if branch is not actually based on the intended parent, publication is blocked. Do not combine unrelated sibling PRs.
- Use the live Cursor-Governance **make pr** route (`make -C "$GOV" pr WS="$WORKSPACE" PR_BASE="$VERIFIED_PARENT"` in a compatible current environment, or the target's verified delegating `make pr` wrapper). The syntax is an illustration of a repository-verified surface, not permission to guess paths. Do not run both entrypoints. `OPEN_PR=1`, current L4 release status and exact artifact/branch authority must be valid.
- Do not depend on `PR_STACK=auto` selecting the correct parent: current `resolve_pr_stack.sh` permits keeping `origin/main` on some telemetry failures. Explicit `PR_BASE` wins and requires confirmation of the GitHub PR's actual base and head after publication. A mismatch blocks the train; correct through existing governance before continuing.
- Do not change `Makefile` or `Repo.mk` to implement stack support. If the target repo has no local `make pr` target, use the existing governance workspace publication route.
- Publish **one PR at a time per repository**, as soon as its branch passes the required local gate. Different repo publication may proceed concurrently. Only the publishing coding agent makes source/PR fixes and updates its own PR through `make pr`.
- If a parent changes after a child's publication, pause that descendant train (not other repos), have each descendant's owner integrate the updated parent through permitted branch operations, republish and restore green current-head CI. Merge decisions are separate and require actual authorization. Never erase a pending child's changes with reset/force push.
- PR creation and clean CI are code-ready milestones, not graph runtime verification. Preserve baseline/cross-repo SHA pins for final Docker after the complete program publishes.

## Agent pool & task ownership

One CTO session; fixed <=5 coding agents according to live host mode. The CTO is the only dispatcher/integrator. Child prompts are rendered by the current LCTO host, agents report in their own transcripts, and each publication owner handles all of its review/CI remediation. No two writers own a path/prefix, generated file, branch or PR simultaneously. Documentation writer owns README/AGENTS/invariant/ADR files throughout its wave; cross-wave writes are serialized in that same repo's stack.

The local AGENT.md/AGENTS.md added human-review protection is waived for declared DOC changes **only**. The root Makefile and Repo.mk are excluded from every lane. Do not edit current global L9 law, unrelated repos or production data.

## Cheap checks versus final Docker

During P0-P4 development: native lint, unit, contract, security and existing mandatory PR CI; no user-initiated multi-container full-rail tests. G_PUBLISH requires every campaign PR published, properly stacked, current-head green and the authored E2E fixture/test PR included. Use the existing secret provider to obtain only scoped test rail material when the rail is ready. Final signed Docker run follows G_PUBLISH. On defects, owners fix their existing PRs and the CTO repeats only required checks and the terminal integration rail.

## Current-state rebind (v1.3.0)

- Every lane worktree branches from fetched `origin/main` at the pinned SHA (EIE `29d4eb5…`, CEG `5d06649…`, Gate `b451b68…`). The local EIE primary clone is diverged (one unpushed docs-pass commit, uncommitted edits, five commits behind) — never branch from it and never scoop its dirty files.
- EIE PR #328 (open) rewrites `app/services/crm/{base,hubspot,odoo,salesforce}_client.py` and `docs/contracts/*`: the P1 CRM lane sequences or stacks against it under CTO scheduling; no concurrent rewrite of those files.
- Open EIE dependabot PRs (#361-363) and governance PRs (#1040-1044, #1036, #1012-1014) are read-only context; no campaign lane writes Cursor-Governance or `.github`.
- Predecessor receipts: record Flywheel merged PRs as already-satisfied evidence per `06_PREDECESSOR_EVIDENCE_AND_CURRENT_STATE.md` before opening any lane PR that overlaps them.
