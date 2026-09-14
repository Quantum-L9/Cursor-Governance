# RB-HK-001 Checklist

## Phase 0 - branch protection (manual, admin required)
- [ ] Ruleset `main-protection` created, targeting `main`, Active
- [ ] Restrict deletions
- [ ] Block force pushes
- [ ] Require PR, 1 approval
- [ ] Dismiss stale approvals
- [ ] Require conversation resolution
- [ ] Required checks: `l9-lint-test`, `validate-org-policy`, `root-file-protection`, `codeql`
- [ ] `gh api .../branches/main --jq '.protected'` prints `true`
- [ ] Auto-delete head branches enabled

## Phase 1 - branches (14 to resolve)
- [ ] `cleanup_branches.sh` run in report mode
- [ ] Merged count: ____  Unmerged count: ____
- [ ] SHAs recorded (RUNBOOK Section 4.2)
- [ ] `sessionend-phase-b-gha-distill` vs `-v2` resolved - survivor: ________
- [ ] `pr-23` and `fix-pr23-sonar` deleted
- [ ] All 4 `claude/*` branches deleted
- [ ] Each unmerged branch: PR opened, cherry-picked, or Linear issue filed
- [ ] `--apply` run; remaining branch count: ____

## Phase 2 - paths and files
- [ ] `Activation Command.md` -> `activation-command.md`
- [ ] `key components/` -> `key-components/`
- [ ] `harvest copy.md` -> `_harvest-copy-REVIEW.md`
- [ ] All references updated (manifests, AGENTS.md, plugin.json, Makefile)
- [ ] Ignore block appended to `.gitignore`
- [ ] `governance-health-report.json` untracked
- [ ] Both `.harvest_executor_state.json` copies untracked
- [ ] `.example` state file created
- [ ] `.governance-build-lock` decision: untracked ____ / kept ____ because ________
- [ ] `.env.template` merged into `.env.example` and deleted
- [ ] `WIP/` added to `.cursorignore`
- [ ] `current_work/` contents migrated, directory deleted
- [ ] `rules/15-work-tracking.mdc` created, under 1 KB
- [ ] `TODO.md` seeded from template

## Phase 3 - automation
- [ ] `.github/dependabot.yml`
- [ ] `repo-hygiene.yml`
- [ ] `governance-self-check.yml`
- [ ] `branch-hygiene.yml`
- [ ] `tools/check_repo_hygiene.py` + Makefile `hygiene` target
- [ ] Pre-commit hook wired
- [ ] Each workflow dispatched once and green
- [ ] `repo-hygiene` added as required check
- [ ] `governance-self-check` added as required check

## Validation
- [ ] `main` protected: true
- [ ] `check_repo_hygiene.py` exits 0
- [ ] No tracked path contains a space
- [ ] Test PR blocked until checks pass

## Deferred (Section 8) - confirm still deferred
- [ ] `governance/` vs `execution-governance/` consolidation
- [ ] `workflows/` vs `pipeline/` vs `.wave/` consolidation
- [ ] Command duplicate clusters
- [ ] Unused skill pruning

## Sign-off

| Field | Value |
|---|---|
| Operator | |
| Date | |
| Branches before / after | 15 / |
| Phase 0 completed by | |
| Next quarterly review | |
