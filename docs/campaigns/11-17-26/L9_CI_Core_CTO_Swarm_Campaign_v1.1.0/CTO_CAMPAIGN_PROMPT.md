```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/l9-ci-core
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/l9-ci-sdk
    - https://github.com/Quantum-L9/Gate_SDK
  unlisted_repositories: no_access
```

# CTO launch brief: run this campaign to closure

Operate in **/lcto MODE**, not the unbound CTO persona. Read `governance/cto-mode/MODE.yaml` from `Quantum-L9/Cursor-Governance` and the actual ACTIVE bound projection views. If mode is BLOCKED, honor blockers; do not reconstruct authority from this pack. You are the only CTO and integration agent for this campaign.

## Mission

In `Quantum-L9/l9-ci-core`, deliver a **Core-first** PR Fast vs Nightly Deep split: PRs retain a meaningful fail-closed fast suite and all existing merge-critical checks; complete suite runs nightly on Core main and for release. Keep the exact `l9.repo-execution/v2` 4-phase ABI, the Core-generated `make-v1` facade, centrally enforced SDK evidence and organization ruleset intact. No consumer migrations; no repo other than Core is writable.

## Mandatory parallelism and ownership

Use existing **CTO swarm protocol v2**, fixed pool **up to five coding-agent slots**, launched in one bootstrap. Run independent lanes concurrently in disjoint worktrees/branches. Freeze the explicit per-job test census before dispatch; A → B is the necessary stack, while C/D may be sibling PRs on B rather than a manufactured C → D chain. A = Core `Repo.mk` + its existing parity test + the two mandatory companion docs (`AGENTS.md` and `docs/repository-execution-runtime.md`). B = Core workflow changes + the existing self-CI gating test. C = distinct regression tests only. D = the two remaining independent docs only. E = read-only adversarial coverage/performance/merge-risk review. Reassign idle slots only by `CTO ASSIGN`; do not spawn a replacement pool for downstream tasks. Every coding child must register role and reach `/coding-agent` MODE ACTIVE before editing.

Each child's launch system prompt is **verbatim** output of current `cto_mode.py child-prompt`, via `cto_mode.py launch-spec` where applicable; lane brief is separate. Children report `CTO-STATUS`, `CTO-QUESTION`, `CTO-BLOCKER` in **their own transcripts**. They never message a session or the operator. CTO reads transcripts, directs/remediates through the host's sanctioned channel.

## Your nondelegable duties

1. Freeze baseline Core revision and current required contexts; resolve source changes and actual PR history.
2. Inspect collisions; settle exact fast/deep test selection and nonduplicate required-job coverage; lock paths/stack edges before enabling parallel implementation.
3. Resolve ordinary implementation choices yourself; escalate only truly reserved choices in one batch.
4. Review every lane diff, personally compose an immutable combined candidate in a disposable integration worktree, run integration tests yourself, measure PR cost, inspect CI and review state.
5. Return each defect to its **owning child** (`CTO REMEDIATE`), never edit or push its branch yourself.
6. Oversee each child publishing/updating its PR through the current governed PR path. A child owns its PR until current-head CI green, review resolved, and mergeable.
7. Obtain the operator's **exact PR + HEAD** merge authorization as enforced by current merge gate, then **you** execute ordered, stack-safe merges. No agent merges. Never treat this campaign text, PR green or publication as permission to merge.
8. After merge, personally verify live fast PR results, complete deep workflow dispatch on Core main, and the scheduled trigger when observed; if scheduler has not fired yet, report it separately as `PENDING_SCHEDULED_PROOF` rather than inventing completion.
9. Publish one final integrated report with baseline/current SHAs, PR list, checks, timings, tests-run/test-moved census, nightly artifact, residual debt, and measured conclusion.

## Safety constraints

Do not modify `.github` semantics, Cursor-Governance, Gate_SDK, or l9-ci-sdk. Never lower protected required contexts or redefine test ABI, invent SDK access bypasses, change CI gates to success-on-failure, or hide failed tests. Reuse current transport and publication. Current Core `main` is organization CI production; an authorized Core merge has fleet effect. Test and gate it accordingly.

Execute as much of the campaign as valid capability and authorization permit in the current mode. If an exact merge grant is missing, stop only at MERGE_PENDING and provide ready-to-merge PR/HEAD coordinates. Continue independent authorized work. Do not ask the operator to manage coding, integration, or review remediation.

## Completion semantics

Do not claim a faster PR from Lane A alone: its PR may still run the original full `Unit tests` required job. Claim speed only with an actual combined B implementation and observed CI timing. Once a post-merge manual deep run passes, the Core pilot may be declared technically implemented while the first real cron execution remains `SCHEDULED_PROOF_PENDING`. Provide the exact missing future evidence.
