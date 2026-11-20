```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/l9-ci-core
    - https://github.com/Quantum-L9/L9-Ops-MCP
  read_only:
    - https://github.com/Quantum-L9/l9-ci-sdk
    - https://github.com/Quantum-L9/l9-repo-template
  unlisted_repositories: no_access
```

# CTO-mode campaign launch: governance-authority migration

**Campaign:** L9-ORG-AUTHORITY-CUTOVER-2026-11-18-v1
**Executor:** Cursor CTO / LCTO operating mode, under current Cursor-Governance law
**Authorization:** Implement the bounded migration, open reviewable PRs, verify and integrate permitted changes. This handoff is not a new semantic admission, a ruleset permission grant, or human merge authorization for an unseen exact candidate.
**Starting point:** Admit organization policy into `Quantum-L9/.github` before any authoritative consumer cutover.

## Mission

Make `Quantum-L9/.github` the unique canonical owner of all organization-wide `L9-ORG-*` policy, assertion semantics, grammar and immutable policy release records. Keep `Quantum-L9/Cursor-Governance` the autonomous agentic operating plane with local operating law, skills, modes, adapters, orchestrators and one publication ceremony. Bind every identified consequential operating-plane action to current admitted global semantic authority plus applicable organization policy, and prove enforcement at real operating boundaries rather than in prose. Use Core and existing GitHub rulesets for organization CI; preserve their owners.

## Execution order

`09_EXECUTION_BINDING.md` is the resolved launch binding. It outranks any sentence in this pack that assigns `.github` writes to a pool agent, launches an unbounded scout fleet, stacks these pull requests, or treats this chat as policy admission.

1. Read `CAMPAIGN.yaml`, `01_ARCHITECTURE_LOCK.md`, `02_VERIFIED_SOURCE_BASELINE.md`, `03_ADMISSION_AND_RELEASE_CONTRACT.md`, and `09_EXECUTION_BINDING.md`. The 2026-11-18 recheck found the four writable `main` SHAs unchanged. Reconcile open-PR overlap immediately before a lane mutates.
2. Pool lane **S** only. At most four read-only Tasks inside a pool of four. Do not add lane files. Scouts report and do not write.
3. The CTO session executes lane **A** in one dedicated `.github` worktree. Keep existing global semantic invariants untouched. A pool agent does not clone, branch, or push `.github`. A candidate pull request is not admitted policy.
4. As soon as A's pull request head exists, the same CTO session executes lane **B** stacked on that head. This launch chat is not the exact-head admission decision, and B does not wait for A to merge.
5. E, C, and M open as soon as they have a parent head SHA to pin. They stack on an overlapping open pull request and update their own pull requests when the parent head moves. An unmerged parent is not a pause.
6. F stacks on B's head once B, C, M, and E have a recorded disposition, including an open stacked pull request. The CTO does not merge it.
7. Close with the receipt and the acceptance matrix in `06_ACCEPTANCE_AND_PROOF.md`. Each in-scope finding must be resolved, proven invalid, or explicitly blocked. No false green.

## CTO ownership and swarm discipline

- CTO owns integration, decisions inside the frozen architecture, incident/CI remediation inside the named repository and the end-to-end final receipt. Delegate bounded work, not governing authority. Lanes A, B, and F stay in the CTO session because the child system prompt forbids pool agents from writing `.github`.
- Parallelize discovery, analysis, fixtures, and independent repository work inside a pool of four, cap five. **One mutating agent per exact worktree.** No simultaneous writers to the same `.github` policy or release files. Use the dependency DAG in `CAMPAIGN.yaml`. Successor and overlapping work stacks on the open pull request head. The CTO does not merge, and an unmerged pull request does not pause a lane.
- Work autonomously within the authorized scope. Ask the only human only when a genuine owner-only admission/merge decision, credential, or undelegable authority is required. Never invent or relay owner authorization. A human review convention cannot silently add a second-human requirement.
- No code changes in `l9-ci-sdk`, `l9-repo-template`, unrelated org repositories, or unlisted repos. Their observed defects are findings, not permission to modify.
- Keep the single repository-independent publication ceremony `make pr`, launched through the live Cursor-Governance SSOT with `WS` bound to the exact target worktree. Verify current `Makefile -> Repo.mk -> ops/make/publish.mk` and called gates; `OPEN_PR=1`, `PUSH_ONLY!=1`, `PR_BASE`/stacking, L4 authorization, and current base before publication. Do not invoke raw `git push` or `gh pr create` to bypass it. One terminal ceremony per PR, not a redundant gate-only smoke run. Verify PR existence afterward.
- Do not alter branch protection, org rulesets or owner checks before proving the enforcement step can actually pass and fail. Do not claim org-wide cutover from unit tests or a ruleset JSON file.
- Repair the first authoritative owner inside scope. If actual owner is outside scope, stop only that dependent lane and leave the rest running; report the exact missing authorization and smallest proposed scope expansion.

## Locked architectural result

`.github` is the organization governance, semantic authority, control and distribution owner. Cursor-Governance is a **subordinate consumer** and the **authoritative local operating implementation**, not an org-policy author. Core is the organization CI executor; SDK keeps technical gate semantics; GitHub rulesets independently enforce required CI. Canonical policy is not a global semantic invariant; do not copy `L9-ORG-*` bodies into `semantics/invariants.yaml` or every skill.

## Required output

- Merged upstream policy admission and exact immutable release, with owner decision and integrity proof.
- Migrated Cursor-Governance consumer binding and no active competing canonical policy claims.
- Legacy L9-Ops-MCP mirror compatible with its existing owner behavior, or an exact blocked dependency if cryptographic consumption cannot be safely made operative.
- Live required-workflow/ruleset evidence for coverage; negative tests proving an invalid policy/ref/permission fails rather than a passing check from a different job.
- Exhaustive active operating-action coverage matrix and org repository census with explicit exclusions, current evidence timestamps, controls, and unresolved gaps.
- PR URLs, merge SHAs, native validation receipts, platform observations, exceptions and a defensible final `PASS / PARTIAL / BLOCKED` verdict.

**Stop condition:** Finish when all `06_ACCEPTANCE_AND_PROOF.md` mandatory criteria are evidenced. If an owner-only authorization or external platform limitation blocks a mandatory criterion, emit `BLOCKED` and the single exact action needed; do not weaken policy, silently widen scope, or pretend the campaign shipped.
