# Resolved execution binding (2026-11-18)

This file is the launch binding for `L9-ORG-AUTHORITY-CUTOVER-2026-11-18-v1`. It resolves contradictions inside the pack and between the pack and the live host. It does not admit organization policy, merge a pull request, or launch the swarm.

Checked from Cursor CTO mode `ACTIVE` for session `07fb2746-2160-41cf-8536-0146803f560f`, authority pin `00500268eb24de29a5e647a447d6f992d609f6f5`. Cited compositions: technical-coordination `sha256:9c159475edeb9a71b50242f51169675a8badd8a897ea9bf83fdda3eb236c6df4`, architecture `sha256:ac3b440f654543fc8c3d547b1910041835e86277da636ac9b0d8d36739d4df28`, governance `sha256:c5d80dbdb7d99eccebdaac663c5f1db8a24252db89b8135205e841d5468d1794`, evidence-provenance `sha256:3eec77f93453af484e53504a7119938aa34d854f61822e77ed6f09730c2ca1d0`, contracts-conformance `sha256:e499a076e3f406506a6bbe38208805aa9fea9f92dc22995331f34cc0a49a9ab1`, capabilities-dependencies `sha256:a42f2987ac439d21b151db242b4bd782c3e591c2786f3a83a35f287e06b7f830`, identity-attribution `sha256:665c6d8e38d4246842d52042286fc9e53ab3773023a174b88b63f80e567e18f5`, strategic-value `sha256:cc362f794d51799fa223b3924f50be8aa116ffd8281beae2d697615cd231277b`.

`technical_coordination_role` coordinates bounded work inside existing authorization. It does not grant execution, admission, publication, or merge. `integration_responsibility` requires evidence of the combined revision. Governance admission rules forbid self-admission, and a human approval binds the exact candidate digest. A changed candidate needs a new decision.

## What this chat authorizes

The operator asked for an execution-ready pack and a clone/push proof before any swarm launch. That request authorizes this binding and the publication of the pack. It is not the exact-head owner decision for a later `.github` policy candidate. Do not treat it as admission, a ruleset change, or merge consent.

## Clone and push proof

GitHub identity `cryptoxdog` (id `31744795`) has `admin` on `Quantum-L9/.github`, including `push: true`. A fresh `git clone --depth 1` of `https://github.com/Quantum-L9/.github.git` checked out `00500268eb24de29a5e647a447d6f992d609f6f5`. `git push --dry-run origin HEAD:refs/heads/l9-cto-push-probe-do-not-create` exited 0. A following `ls-remote` for that ref returned empty, so the probe branch was not created.

The repository API reports `private: false`. The child system prompt still describes the repository as private. Children still must not clone, branch, or push it. The managed pin `$HOME/.l9/authority/.github` is non-shallow and its `HEAD` equals `origin/main` at the same SHA. It has untracked `.l9/agent-tasks/` only. Use it as the coding-agent authority pin. Do not mutate it and do not start a worktree from it.

## Writer split

`governance/cto-mode/MODE.yaml` `child_system_prompt` ends the repository rule with “Quantum-L9/.github is still never cloned, branched, or pushed.” A lane header cannot override that launch system prompt. This pack does not edit that contract.

| Lane | Executor | Why |
| --- | --- | --- |
| S, E, C, M | Fixed pool of four coding agents, cap five | Their writable repositories are not `.github`. |
| A, B, F | Activating CTO session, one `.github` worktree, serialized | Pool agents are forbidden to clone, branch, or push `.github`. |

The same session authors and coordinates A, B, and F. That is a consequence of the host rule, not a new permission. The operator's merge review is the independent check. Do not claim a second swarm review of those diffs. The CTO still does not merge.

On Cursor, a pool slot is a Task. Launch four Tasks in the bootstrap sitting and reuse them. Do not launch a fifth except as one reported replacement for a dead slot. Lane S may split across those four Tasks. Each task prompt narrows the repository list. Do not add lane files. The S header remains the maximum read set.

## Publication and stacking

The CTO has no merge authority. An unmerged pull request is not a hold, a queue, or a reason to pause any lane. The operator merges when they choose. Lanes keep opening and updating stacked pull requests until then.

Every lane publishes with the governance ceremony against that lane's worktree:

```bash
PR_REMEDIATE=0 OPEN_PR=1 \
  make -C "$HOME/.cursor-governance" pr WS="$WT"
```

Set the base as follows. `OPEN_PR=1` and `PR_REMEDIATE=0` stay explicit. One ceremony per pull request. Do not run `OPEN_PR=0 make pr` as a rehearsal. Do not use raw `git push` or `gh pr create`.

- A branch that already has an open pull request is updated in place. Its base stays the base GitHub already records.
- A lane that continues another open pull request, or edits a path that pull request already changes, stacks on that pull request's head. Pass `PR_BASE=origin/<parent head branch>` and `L9_TASK_BASE_AUTHORIZED="operator 2026-11-18: stack on open PRs; unmerged PRs do not block"`.
- `PR_STACK=auto` is used only when the resolver reports one chain. Cursor-Governance currently has several sibling pull requests against `main`, and `auto` fail-closes on that board. Name the predecessor head instead of stopping.
- An unrelated open pull request, including Dependabot, is not a parent and not a wait. Parallel non-overlapping lanes publish together.

Create the worktree from the stacked base, not from a merge:

```bash
cd "$CLONE"
L9_TASK_BASE_AUTHORIZED="operator 2026-11-18: stack on open PRs; unmerged PRs do not block" \
  bash "$HOME/.cursor-governance/ops/scripts/agent_worktree_start.sh" \
  --agent-id <id> --task-id <lane> --base "origin/<parent head branch>" --json
```

A first pull request in a repository with no predecessor uses `--base origin/main` and omits the authorization variable.

Before that command, in the lane worktree: scoped commits, then `l4_local.py begin`, then `l4_local.py authorize-release`, using `"$HOME/.cursor-governance/.venv/bin/python"`. Cursor-Governance `59c0b3e0fae7418c67b7e3be76c4e3f412ad49dd` has no `ops/autonomy/kernel_gate.py`. Do not invent that command. The live remote predicate is `l4_local.py check-remote`.

Create that worktree from inside a dedicated clone of the lane repository, not from the managed authority pin and not with raw `git worktree add`. Then publish with `WS` set to the printed worktree. Do not run a bare `make pr` inside `.github`, `l9-ci-core`, or `L9-Ops-MCP`. Those trees are consumers. The governance gate skips its own pytest registry for a consumer and does not run that repository's tests. The lane runs the repository's own relevant tests before `make pr`. That repository's CI remains the required-check authority.

Fetched `origin/main` for Cursor-Governance is `59c0b3e0fae7418c67b7e3be76c4e3f412ad49dd`. That tip already contains merged #1037, #1038, and #1039. Local `main` commit `39fd2492b314a2b6b132f393af61a27b47764dd1` is outside this campaign. A lane with no predecessor and no overlapping open pull request branches from that fetched tip.

## Live recheck

The launch base is fetched `origin/main`, not the earlier observation SHA `48c9e134`. Cursor-Governance `main` is `59c0b3e0fae7418c67b7e3be76c4e3f412ad49dd` and already contains #1037, #1038, and #1039. `.github`, `l9-ci-core`, and L9-Ops-MCP `main` SHAs are unchanged. `.github` and `l9-ci-core` have no open pull requests.

Cursor-Governance still has [#1040](https://github.com/Quantum-L9/Cursor-Governance/pull/1040), [#1036](https://github.com/Quantum-L9/Cursor-Governance/pull/1036), [#1014](https://github.com/Quantum-L9/Cursor-Governance/pull/1014), [#1013](https://github.com/Quantum-L9/Cursor-Governance/pull/1013), and [#1012](https://github.com/Quantum-L9/Cursor-Governance/pull/1012). None of them is the integration base. #1036 changes only `.github/CODEOWNERS`, `.github/dependabot.yml`, and `.github/workflows/governance.yml`. Lane C stacks on `chore/governance-sync` only if it edits one of those three files.

L9-Ops-MCP still has [#44](https://github.com/Quantum-L9/L9-Ops-MCP/pull/44), #43, #42, #40, and #38. #44 changes only `.github/CODEOWNERS`, `.github/dependabot.yml`, and `.github/pull_request_template.md`. Lane M stacks on that head only when it edits one of those three files. `ORG_INVARIANTS.yaml` and `scripts/validate_org_invariants.py` are outside that list, so M branches from `origin/main`.

## Stack edges, not merge gates

A opens its pull request. B branches from A's head as soon as that head exists and publishes with `PR_BASE` set to A's branch. F branches from B's head the same way. One `.github` worktree writes a given path at a time. When the parent branch moves, the child git-merges that branch into its own branch. Nobody waits for a GitHub merge.

E opens against `l9-ci-core` `main` as soon as it has A's or B's head SHA to pin. C and M pin that same open head. When the parent head moves, they push the new pin to their own open pull requests. A missing signature is recorded on B and does not close C, M, E, or F.

Lane F's `depends_on` means each of B, C, M, and E has a recorded disposition, including a stacked open pull request. A `BLOCKED` predecessor with an owner and one next action still lets F publish its census. It does not let F mark that predecessor `PASS`. The CTO does not merge F.

If no deterministic mirror renderer exists, record `L9-CTRL-004` as `BLOCKED` and name the smallest existing owner path. Do not create a new release product.

Signing and in-toto tooling are still `UNKNOWN` until B reads `.github` source. If the signer or attestor is unavailable, B records `BLOCKED` and the other lanes keep publishing against the stacked heads. The CTO does not merge those pull requests and does not wait for the operator to merge them.

## Ruleset read

`gh` scopes on this token are `gist`, `read:org`, `repo`, and `workflow`. `admin:org` is absent, and the org ruleset URL returns 404. The repository ruleset URL works.

Live `repos/Quantum-L9/.github/rulesets/21895545` on 2026-11-18: enforcement `active`, name `L9 canonical CI required`, target `branch`, included on `~DEFAULT_BRANCH`, exclude list empty. Required check `Analyze (central Core)`. Workflow `.github/workflows/org-ci.yml` at `refs/heads/main`, `repository_id` `1285564308`. `strict_required_status_checks_policy` is false. Bypass actor `OrganizationAdmin` with mode `always`. The ruleset is returned for the `.github` repository itself. The committed JSON that excludes `.github` remains a drift item for F. This read does not prove a bad pull request cannot merge.

Live `repos/Quantum-L9/Cursor-Governance/rulesets/20855699`: enforcement `active`, name `main-protection`. Required checks `Lint and Type Check`, `Test Suite`, `Root-file append-only gate`, `governance-self-check`, and `repo-hygiene`, with strict policy true. Required approving reviews `0`. `require_code_owner_review` false. `required_review_thread_resolution` true. Bypass actor `EnterpriseOwner` with mode `always`.

## Acceptance wording

D07's "smoke" means a behavioral probe of a changed operating path. It is not `OPEN_PR=0 make pr`.

Campaign closure may be `PASS`, `PARTIAL`, or `BLOCKED`. A row is `PASS`, `BLOCKED`, or `NOT_PROVEN`. `PARTIAL` is only a campaign verdict, and only when some mandatory row is not `PASS`.

## Swarm

Do not launch the pool from this binding. The operator has not authorized launch. When launch is authorized, child system prompts are the verbatim output of `cto_mode.py child-prompt --cto-session 07fb2746-2160-41cf-8536-0146803f560f`. Lane scope goes in the task prompt only. Children report in their own transcript and do not message the operator.
