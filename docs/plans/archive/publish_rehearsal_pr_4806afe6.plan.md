---
name: Publish rehearsal PR
overview: "Reset Development to current Staging, then commit the Gate 7 rehearsal on a new clean branch off Staging and open a new pull request into Development with make pr-nosmoke. Do not use fix/rehearsal-evidence-20261108. Do not push or merge Staging."
todos:
  - id: reset-development
    content: Force-update only origin/Development to origin/Staging 88ce4370. Do not push, reset, or merge Staging.
    status: pending
  - id: new-branch
    content: Create a clean worktree and branch fix/rehearsal-gate7-development from origin/Staging. Do not commit on fix/rehearsal-evidence-20261108.
    status: pending
  - id: redact-and-commit
    content: On the new branch only, redact the database name, bump plasticos_crm_sync to 19.0.1.9.23, force-add the 173212 evidence except diagnostics, and commit with latest pointed at that run.
    status: pending
  - id: make-pr
    content: Authorize L4 on the new worktree and run make pr-nosmoke base=Development so a new pull request opens into Development. If that base is refused, stop. Do not retarget Staging.
    status: pending
isProject: false
---

# Publish the rehearsal fixes and the ready evidence

Cursor is on `fix/rehearsal-evidence-20261108` at `9b3ec0a5`. Do not commit, push, or publish that branch. Do not update [PR #404](https://github.com/cryptoxdog/IB-Odoo_19/pull/404). `Staging` (`origin/Staging` `88ce4370`) is about to be promoted. Do not push it, reset it, merge into it, or open a pull request against it.

`origin/Development` is the stale superseded tip `3318fa64`. Before the rehearsal commit is published, make `Development` identical to current `Staging` by updating only that ref:

```bash
git fetch origin Staging Development
git push --force origin origin/Staging:Development
```

That force-push names `Development` and leaves `Staging` untouched. After it, `origin/Development` and `origin/Staging` are both `88ce4370`.

Then start a new clean worktree from `origin/Staging` on a new branch, `fix/rehearsal-gate7-development`. The rehearsal commit is created only there.

## What is committed

The uncommitted Gate 7 work:

- [plasticos_crm_sync/scripts/import_vanillasoft_shell.py](plasticos_crm_sync/scripts/import_vanillasoft_shell.py) keeps the original newlines when it reads a history census, and [plasticos_crm_sync/__manifest__.py](plasticos_crm_sync/__manifest__.py) goes from `19.0.1.9.22` to `19.0.1.9.23`.
- [tests/production-rehearsal/run.sh](tests/production-rehearsal/run.sh) no longer opens or hashes the checkout export. Gate 7 passes the rolling floors. The driver still loads `plasticos_crm_sync/data/approved_contact_crosswalk.csv`.
- The matching judge, tests, and kit text in [tests/production-rehearsal/common.py](tests/production-rehearsal/common.py), [test_rehearsal_scripts.py](tests/production-rehearsal/test_rehearsal_scripts.py), [test_erp_census_source.py](tests/production-rehearsal/test_erp_census_source.py), [SPEC.md](tests/production-rehearsal/SPEC.md), [README.md](tests/production-rehearsal/README.md), and [expected/blockers.yaml](tests/production-rehearsal/expected/blockers.yaml).

The ready run `tests/production-rehearsal/evidence/2026-11-08_173212` is gitignored by `evidence/20*/`. Force-add that folder, except `05-erp-diagnostics.json`, and point the tracked `evidence/latest` symlink at it. Before adding it, replace the source database name in the two lines of `05-erp-import.log` with the placeholder already used in `2026-11-08_124519`. The key log only says `key injection exit=0`.

Do not commit `2026-11-08_173212.zip`. It is a second copy of the same run.

## What stays out

[skills/plasticos-branch-promotion-rehearsal/](skills/plasticos-branch-promotion-rehearsal/) and its registrations in `AGENTS.md`, `.claude/README.md`, and `skills/PLASTICOS_SKILLS_MANIFEST.yaml` are a different rehearsal. That skill forbids reading `tests/production-rehearsal`. Publication refuses a dirty or untracked tree, so those paths and the zip are stashed for the publication and restored afterward.

## Publication

On the new worktree only, after the rehearsal commit: L4 `authorize-release`, then a new pull request into `Development`:

```bash
make pr-nosmoke reason="the cutover rehearsal already ran install-smoke and the import gates" base=Development
```

That skips Docker install-smoke and the runtime-test wave that follows it. Ruff, wiring, and the scoped local pytest still run. The reason is posted on the new pull request. No merge.

`make pr base=Development` is not a Staging publication. `scripts/pr_stack_parent.sh prove` still requires exactly one open pull request from `Development` into `Staging`, and the new branch must contain `origin/Development`. If that prove step refuses the base, stop. Do not drop `base=Development`, do not publish into `Staging`, and do not raw-push the feature branch.
