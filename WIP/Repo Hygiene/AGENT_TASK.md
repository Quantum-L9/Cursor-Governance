# AGENT_TASK - RB-HK-001 Phases 2 and 3

## PHASE 2 - Path and file hygiene

### 2.1 Rename paths with spaces

```
git mv "Activation Command.md" activation-command.md
git mv "key components" key-components
git mv "commands/harvest copy.md" commands/_harvest-copy-REVIEW.md
```

Do not delete the harvest copy. Human decision.

### 2.2 Update all references

Grep for `Activation Command`, `key components`, `harvest copy` across the
tree excluding `.git`. Update every hit, especially `RULES-MANIFEST.yaml`,
`COMMANDS_MANIFEST.yaml`, `AGENTS.md`, `.cursor-plugin/plugin.json`, and any
`Makefile` target. Report the full list of files changed.

### 2.3 Generated and state files

Append the ignore block from RUNBOOK.md Section 4.5 to `.gitignore`.

`git rm --cached` these:
- `governance-health-report.json`
- `.harvest_executor_state.json`
- `commands/.harvest_executor_state.json`

For `.governance-build-lock`: grep `Makefile`, `.github/workflows/**`, and
`tools/**` for readers first. If any reader exists, leave it tracked and
report. Only untrack if nothing reads it.

Create `.harvest_executor_state.example.json` with the same keys as the real
file and placeholder values. No live state.

### 2.4 Env template collapse

Diff `.env.example` against `.env.template`. Merge unique keys into
`.env.example`. Delete `.env.template`. Update references. Report the merged
key list.

### 2.5 Work-tracking contract

- Add `WIP/` to `.cursorignore` (create the file if the housekeeping pack is
  the first thing to need it).
- Report whether `current_work/` has contents. Do not move or delete them -
  I decide their destination.
- Create `rules/15-work-tracking.mdc` following the rules STANDARD.md shape A:

```
---
description: WIP/ is human-owned and off-limits to agents; TODO.md is the agent task queue.
alwaysApply: true
---
```

Body must state: never read or write `WIP/`; maintain `TODO.md` as the task
queue; one task per line with a status prefix; include the Linear identifier
when work spans sessions; `current_work/` is retired and must not be recreated.

Keep it under 1 KB. It is joining the always-apply budget.

## PHASE 3 - Automation

### 3.1 Install workflow files

Copy from `housekeeping-pack/workflows/`:

- `dependabot.yml` -> `.github/dependabot.yml`
- `repo-hygiene.yml` -> `.github/workflows/repo-hygiene.yml`
- `governance-self-check.yml` -> `.github/workflows/governance-self-check.yml`
- `branch-hygiene.yml` -> `.github/workflows/branch-hygiene.yml`

### 3.2 Install the hygiene checker

Copy `scripts/check_repo_hygiene.py` to `tools/check_repo_hygiene.py`. Make it
executable. Add `Makefile` targets, matching existing style and tab indentation:

```
hygiene:
	python3 tools/check_repo_hygiene.py

hygiene-fix:
	@echo "See housekeeping-pack/RUNBOOK.md Section 4"
```

### 3.3 Wire pre-commit

Add a local hook to `.pre-commit-config.yaml` running
`tools/check_repo_hygiene.py`. Match the existing config structure. Do not
reorder or modify existing hooks.

### 3.4 Verify

Run `python3 tools/check_repo_hygiene.py` and report output verbatim. If it
fails, fix what Phase 2 was supposed to fix, then re-run.

### 3.5 Report

Output:
1. Every file changed, with why.
2. The `jobs:` key name from each new workflow, so they can be added as
   required status checks.
3. Whether `.governance-build-lock` was left tracked, and what reads it.
4. Whether `current_work/` still has contents.
5. The size of `rules/15-work-tracking.mdc` and the new always-apply total.

## Prohibitions

- No branch deletions.
- No pushes. No commits.
- Do not modify existing workflows. Only add new ones.
- Do not enable auto-merge anywhere.
