campaign_id: level3-make-pr-single-path
title: Level-3 Make and Single-Path PR Refactor

objective: |-
  Refactor Quantum-L9/Cursor-Governance into a Level-3 Make capability graph
  with one canonical, efficient, fail-closed PR shipping path.

  The operator will provide the exact replacement Makefile separately.
  Treat that supplied Makefile as authoritative input for Commit 1.
  Do not redesign, partially recreate, stylistically rewrite, or silently
  "improve" that Makefile during campaign execution. Replace the repository
  Makefile with the supplied candidate exactly, then validate it against the
  repository.

  REQUIRED END STATE

  1. `make pr` is the sole canonical agent/operator PR shipping entrypoint.
  2. `pr-check` is deleted. No compatibility alias is retained.
  3. Agents never run `make pr-check` before `make pr`.
  4. Agents never run `OPEN_PR=0 make pr` as a preliminary pass immediately
     before a normal `make pr`.
  5. A repository state is subjected to the canonical PR gate at most once
     unless that state changes.
  6. Changed-file resolution occurs once per `make pr` invocation.
  7. `.pre-commit-config.yaml` is the single execution owner for checks it
     declares.
  8. The outer PR gate does not rerun Ruff, formatting, generated-artifact
     reconciliation, or any other check already owned by pre-commit.
  9. PR-only checks remain outside pre-commit only when they genuinely require
     PR context.
  10. After the four planned implementation commits, `make pr` owns the
      publish -> remediation -> green/mergeable -> authorized merge lifecycle.
  11. Post-PR remediation is allowed to repair, commit, and converge the PR.
  12. Merge is allowed only for the exact authorized PR/head when required
      checks are green, the PR is mergeable, no blocking code review remains,
      and no bypass/admin/force-push path is used.
  13. No active agent instruction, rule, skill, policy, or documentation surface
      teaches an alternate PR shipping path.
  14. Generated projections are regenerated from authoritative sources rather
      than hand-edited.
  15. Final validation proves there is no active residual of the superseded
      PR path.

  SINGLE-PATH DEFINITION

  "Single path to GitHub" means the GitHub PR mutation path:
  publish/create/update/remediate/merge.

  `make pr` is the only public agent/operator entrypoint for that lifecycle.
  Internal implementation scripts may use git/GitHub tooling only when they are
  implementation leaves reachable through the canonical `make pr` or the
  remediation capability it authorizes.

  Existing read-only fetch/inspection and unrelated repository backup/sync
  behavior are not alternate PR shipping paths unless evidence shows that they
  can create, update, remediate, or merge a PR.

  COMMAND DISCIPLINE

  The campaign MUST optimize for one authoritative validation attempt per
  repository state.

  Forbidden as normal fallback behavior:
    - make pr-check
    - make pr-check && make pr
    - OPEN_PR=0 make pr && make pr
    - bare `git push` to publish/refeed the campaign PR
    - bare `gh pr create`
    - bare `gh pr merge`
    - rerunning `pre-commit run` after fixing a `make pr` failure merely to
      prove the same gate before rerunning `make pr`
    - rerunning bare Ruff/pytest/mypy/full validation and then immediately
      running the same overlapping checks through `make pr`
    - bypassing a failed canonical gate with a lower-level command
    - force-push
    - admin merge
    - weakening or skipping a required check to save time

  Allowed diagnostic behavior:
    - inspect the exact failing output
    - inspect files/configuration
    - run a narrowly scoped diagnostic or repository Make target only when it
      answers a specific unresolved root-cause question
    - use local git status/diff/add/commit operations for the four planned
      commits

  After a fix, the next authoritative shipping validation is `make pr`.
  Do not first prove the same corrected state through an overlapping full gate.

  REQUIRED FAILURE LOOP

      make pr
          |
          +-- PASS -> continue canonical publication/remediation lifecycle
          |
          +-- FAIL -> diagnose exact failure
                       |
                       v
                     fix
                       |
                       v
                   repository state changed
                       |
                       v
                    make pr

  Every changed state may receive one new `make pr` attempt.
  An unchanged state must not be repeatedly revalidated through equivalent
  command surfaces.

  FOUR-COMMIT CONTRACT

  Before initial publication, produce exactly these four planned commits in
  this order:

    1. refactor(make): establish level-3 PR capability graph
    2. refactor(pr): remove duplicate validation execution
    3. feat(autonomy): authorize bounded green-and-mergeable PR merge
    4. docs(governance): migrate PR contract and regenerate projections

  Do not push between these commits.

  If a defect is found before publication, repair it in the corresponding
  planned commit while history is still local.

  After publication, remediation commits are permitted only when CI/review
  discovers a real defect. Never force-push merely to preserve an exact
  four-commit count.

  CAMPAIGN-SPECIFIC PIPELINE OVERRIDE

  This campaign intentionally supersedes the current generic PE activation
  publish/merge sequence where that sequence conflicts with the target
  architecture.

  Do NOT publish with:
      PR_REMEDIATE=0 make pr

  Do NOT complete this campaign with the activator's legacy direct:
      authorize_campaign_merge.py
      gh pr merge ...

  The refactor itself must prove that the NEW canonical `make pr` path can
  publish, authorize remediation, converge, and merge the campaign PR under
  its bounded exact-head policy.

  Therefore the final campaign publication must use the newly implemented
  canonical path with remediation and bounded automerge enabled.

  FINAL CONVERGENCE GATE

  Before claiming implementation complete, prove all of the following:

    A. MAKE STRUCTURE
       - replacement Makefile matches the operator-supplied candidate except
         for changes explicitly required by evidence and approved campaign scope
       - default target works
       - `make help` succeeds
       - required public targets exist
       - `pr-check` target does not exist
       - no second public PR gate exists
       - Make graph has no accidental recursive duplicate of the PR pipeline

    B. EXECUTION OWNERSHIP
       - changed-file resolution executes once per `make pr`
       - pre-commit executes once per repository state
       - Ruff has one execution owner
       - Ruff format has one execution owner
       - generated reconciliation has one execution owner
       - every other duplicated PR/pre-commit validator has been resolved to
         one authoritative owner
       - PR-only checks are demonstrably PR-specific

    C. FAILURE SEMANTICS
       - failure of any mandatory check fails `make pr`
       - missing mandatory validator fails closed
       - no earlier command failure can be hidden by a later success
       - pre-commit mutation/new state cannot be silently treated as validation
         of the prior state
       - no required validation was weakened for performance

    D. PR PUBLICATION PATH
       - `make pr` is the only active agent/operator PR shipping command
       - no active instruction teaches `git push`, `gh pr create`,
         `gh pr merge`, `make pr-check`, or another public Make target as a
         substitute PR lifecycle
       - low-level GitHub mutation scripts are internal implementation details
         and are reachable only from the canonical path or its authorized
         remediation continuation

    E. POST-PR AUTHORITY
       - remediation authorization is scoped to the campaign PR
       - authorization is bound to the observed head SHA where required
       - required checks must be green
       - PR must be mergeable
       - draft/conflict/blocking-review conditions prevent merge
       - force-push/admin/bypass remain forbidden
       - successful convergence can actually merge without separate human
         intervention when this campaign authorized automerge

    F. RESIDUAL SCAN
       Perform an exhaustive repository-local search after authoritative edits
       and regeneration.

       Classify every hit before disposition.

       Active source-of-truth occurrences of the following must be ZERO unless
       they are explicitly part of a negative regression test:

         `pr-check`
         `make pr-check`
         `PR_REMEDIATE=0 make pr`
         `autonomous_merge: false`
         `"autonomous_merge": false`
         `never merge`
         human-only merge instructions
         bare `gh pr create` as an operator/agent shipping command
         bare `gh pr merge` as an operator/agent shipping command
         bare `git push` as an operator/agent PR publication fallback

       Historical ADR/law material may remain only when preservation is
       required and the surrounding record clearly marks it as superseded.
       Historical text must not remain machine-active or operator-prescriptive.

       Search generated projections too. If they contain stale active doctrine,
       fix the authoritative source and regenerate; never patch the projection.

    G. GENERATED STATE
       - run the canonical generated-artifact synchronizer once after all
         authoritative source edits
       - rerun its check mode
       - no generated drift remains
       - no generated file was manually edited

    H. CLEAN FINAL STATE
       - all four planned implementation commits exist in order
       - only evidence-backed campaign paths changed
       - no temporary diagnostics, receipts, scratch files, or accidental
         campaign artifacts remain tracked
       - no unrelated repository state changed
       - final worktree is clean before shipping

  FINAL SHIPPING RULE

  Do NOT perform a separate full preflight PR gate immediately before shipping.

  When A-H are satisfied locally, invoke the canonical command directly:

      PR_REMEDIATE=1 PR_AUTOMERGE=1 make pr

  That invocation is the authoritative final validation and publication
  attempt for that exact state.

  If it fails:
    - do not fall back to raw component commands as another full gate
    - diagnose the reported failure
    - fix the root cause
    - commit the remediation appropriately
    - rerun `make pr` once for the new state

  If it opens the PR:
    - allow its authorized remediation path to own convergence
    - do not create a second remediation worker for the same PR
    - do not manually push or manually merge around it
    - require successful merge of the exact converged head before declaring
      the campaign complete

  TERMINAL SUCCESS

  Campaign success requires:
    - Level-3 Make graph installed
    - four planned commits completed
    - one-pass PR validation architecture proven
    - zero active superseded PR-path residuals
    - one canonical agent/operator PR shipping path: `make pr`
    - campaign PR green
    - campaign PR mergeable
    - campaign PR merged through the newly authorized canonical lifecycle
    - campaign ledger closed complete

owner: Igor Beylin

target:
  repository_id: Quantum-L9/Cursor-Governance
  source_of_truth: environment/program-execution
  adapter: git

tasks:
  - title: "Commit 1 — refactor(make): establish level-3 PR capability graph"
    objective: |-
      Replace repository Makefile with the exact operator-supplied Level-3
      Makefile candidate.

      Do not reconstruct it from memory and do not opportunistically redesign
      its recipes.

      Before replacing the file:
        - record the supplied candidate digest
        - record the current repository Makefile digest

      After replacing it:
        - prove the working Makefile digest matches the supplied candidate
        - inspect the complete target graph
        - verify default goal/help behavior
        - verify `pr-check` is absent
        - verify `make pr` is the canonical PR target
        - verify public/internal target metadata and .PHONY coverage
        - verify no public target was accidentally lost except the deliberately
          removed `pr-check`
        - preserve explicitly ordered orchestration where order is semantic

      Finish this task as the local commit:
        refactor(make): establish level-3 PR capability graph

      Do not push.
    paths:
      - Makefile

  - title: "Commit 2 — refactor(pr): remove duplicate validation execution"
    objective: |-
      Refactor the local PR gate into a one-pass execution DAG.

      Required mechanics:
        - resolve the changed-file set exactly once per `make pr`
        - pass/reuse that resolved set downstream
        - execute pre-commit exactly once for the repository state
        - make `.pre-commit-config.yaml` authoritative for hooks it declares
        - remove outer-gate duplicate Ruff and Ruff-format execution
        - remove duplicate generated-artifact reconciliation when pre-commit
          owns it
        - remove any other exact duplicate validation discovered by execution
          tracing
        - retain genuinely PR-specific tests/security/lock/context gates outside
          pre-commit
        - fail closed when mandatory validators are missing
        - fail closed when any mandatory command fails
        - stop when a writer changes repository state; do not pretend the old
          state remains validated
        - do not introduce caching, receipts, or parallelism unless required by
          correctness evidence

      Validation must prove execution count and failure propagation, not merely
      inspect source text.

      Finish this task as the local commit:
        refactor(pr): remove duplicate validation execution

      Do not push.
    paths:
      - ops/scripts/run_pr_gate.sh
      - ops/scripts/run_pr_precommit.sh
      - .pre-commit-config.yaml
      - ops/config/precommit-hook-contract.json

  - title: "Commit 3 — feat(autonomy): authorize bounded green-and-mergeable PR merge"
    objective: |-
      Extend the canonical `make pr` lifecycle through post-PR remediation and
      bounded automatic merge.

      Preserve the existing governance boundary:
        standing/unbounded merge authority remains forbidden.

      Add the narrow authority:
        a `make pr` invocation may authorize remediation and merge of its own
        exact PR when the merge contract is satisfied.

      Required merge predicates:
        - authorization belongs to this PR
        - observed head SHA matches the authorized/current head as required
        - PR is not draft
        - required checks for the exact head are green
        - GitHub reports mergeable/no conflict
        - no blocking CHANGES_REQUESTED state remains
        - no unresolved actionable code-owned review item remains
        - no admin/bypass path is used
        - no force-push is used

      `PR_AUTOMERGE=1` must allow this bounded terminal transition.
      `PR_AUTOMERGE=0` must remain a reliable opt-out.

      Remove unconditional "never merge" behavior from executable policy where
      it conflicts with this scoped authority.

      Do not expose a general-purpose bare merge permission to agents.

      Finish this task as the local commit:
        feat(autonomy): authorize bounded green-and-mergeable PR merge

      Do not push.
    paths:
      - ops/scripts/open_pr_after_gate.sh
      - ops/autonomy/merge_gate.py
      - ops/autonomy/surface_profile.yaml
      - environment/program-execution/peer_execution/autonomy/profiles/pr-convergence.json
      - environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml
      - environment/agents/adapters/claude-code/settings.template.json

  - title: "Commit 4 — docs(governance): migrate PR contract and regenerate projections"
    objective: |-
      Migrate every active repository contract, agent instruction, rule, skill,
      policy, and generated projection to the new PR architecture.

      Perform a repository-wide reference inventory before editing.

      Required migration:
        - delete active `pr-check` instructions/callers
        - replace genuine validation-only usage with the canonical supported
          nonpublishing semantic only where that behavior is still required
        - remove the two-pass `pr-check` then `pr` workflow everywhere
        - remove active `PR_REMEDIATE=0 make pr` shipping instructions
        - replace unconditional "never merge"/human-only merge doctrine with the
          new bounded exact-PR/exact-head authority
        - preserve historical law/ADR evidence by supersession rather than
          rewriting history where repository governance requires preservation
        - create/append the architecture decision required to authorize the new
          merge model
        - make agent instructions explicitly teach:
              failure -> diagnose -> fix -> make pr
          and explicitly forbid:
              failure -> run bare full gate -> make pr
        - ensure no active skill tells an agent to use raw `gh pr create`,
          `gh pr merge`, or `git push` as a PR lifecycle fallback
        - regenerate all derived rule/skill/command/environment projections
          from authoritative sources

      Before committing, execute the FINAL CONVERGENCE GATE defined in the
      campaign objective, including the exhaustive residual scan.

      There must be no unexplained active residual.

      Finish this task as the local commit:
        docs(governance): migrate PR contract and regenerate projections

      Do not push.

      After this fourth commit and only after the working tree is clean, invoke:

        PR_REMEDIATE=1 PR_AUTOMERGE=1 make pr

      Do not run a preliminary full PR gate first.