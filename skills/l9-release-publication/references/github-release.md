<!-- L9_META
schema: 1
parent: l9-release-publication
layer: reference
role: host-release-contract
version: 1.0.0
status: active
-->

# Release job and host Release

## Completion loop

A merge or a tag push starts a release; it does not finish one. A release is three
host facts at the release commit: the exact tag, a published Release, and (when the
repository keeps one) the maintained major tag. Drive them to done:

```bash
"$GOV_PY" "$SKILL_DIR/scripts/complete_release.py" --remote <owner/name> --tag <tag> \
  --commit <release commit> [--major-tag <vN>] [--workflow <release_workflow>] \
  [--dispatchable] [--tag-kind lightweight|annotated] --repo-dir <checkout>
```

Take `--workflow` and `--dispatchable` from `detect_release_model.py`
(`release_workflow`, `release_workflow_dispatchable`) and `--tag-kind` from how the
job creates tags (a plain `git tag <name> <sha>` is lightweight). The script waits for
the run on the release commit (`--wait-seconds`, default 1800), then reads the host.
It never mutates anything.

| Exit | Status | Do |
|---|---|---|
| 0 | `RELEASE_COMPLETE` | Verify (below), then close out with `consumer_refresh`. |
| 4 | `WAITING_APPROVAL` | Stop: report run URL, environment and reviewers. The operator approves; rerun the loop. |
| 5 | `COMPLETION_REQUIRED` | Run `plan` in order, one shell command per step, then rerun the loop. |
| 6 | `RUN_PENDING` | Rerun the loop; the job is still running. |
| 1 | `MISMATCH` | Stop: a tag names another commit, or the major tag is ahead. Never re-point. |
| 3 | `TRANSPORT_BLOCKED` | Stop with the detail. |

`plan` takes one route at a time, preferred first; `fallback` holds the next route:

1. `repository_job` — the job finishes its own work with its own credentials: dispatch
   it when it never ran and accepts `workflow_dispatch`, or rerun its run for this
   commit once (failed jobs only, when it failed). Before a full rerun, read the job:
   rerun only when it decides each side effect from host state, as a job that skips
   an existing tag and moves the major tag with a lease does. A job that would publish
   a package twice is never rerun; use the fallback.
2. `agent` — push the missing exact tag (or a missing major tag) behind the
   publish-path receipt (references/publication-plane.md), and create or publish the
   Release with `gh release create --verify-tag`.
3. `operator` — advance an existing major tag. The lease push onto a shared tag ref
   needs `L9_GIT_DESTRUCTIVE_AUTHORIZED`, which only a human sets. Give the operator
   the exact command from `plan`; after they run it, rerun the loop.

Never approve or cancel a run on the operator's behalf, never start a second dispatch
or a second rerun, and never call a release done while the loop exits non-zero.

## Package evidence

When the job builds artifacts, read its digest output and the registry publish step.
Compare each digest to the admitted checksum. A mismatch stops the Release. A local
rebuild is never publication evidence.

## Creating the Release (`release_creator: agent` only)

1. Read the repository's release decision (an ADR, `docs/release*`, or the release
   checklist) for the required asset set. If it names none, the set is the source
   archive only; if the decision cannot be found and the job builds artifacts, label
   the asset set `Unknown` and stop.
2. `gh release create <tag> --verify-tag --title <tag> --notes-file <notes> <assets...>`.
3. Never create a Release while its job is still running or waiting: there is
   nothing admitted to attach yet.

When `release_creator: workflow`, do not create or edit the Release; verify it.

## Verification

```bash
"$GOV_PY" "$SKILL_DIR/scripts/verify_github_release.py" --remote <owner/name> --tag <tag> \
  --peeled-commit <commit> [--require-asset <name> ...] [--major-tag <vN>]
```

Report `RELEASE_VERIFIED` only on exit 0. `RELEASE_ABSENT` after a successful job
whose `release_creator` is `workflow` means the job skipped the Release: read its
decision log before doing anything else.

## Consumer view

A plain `git fetch` adds a new tag but refuses to move one that exists ("would clobber
existing tag"), so every existing clone keeps the old major tag after a correct
release. Judge release state only from the host (`git ls-remote origin 'refs/tags/*'`
or the loop), and give the operator the loop's `consumer_refresh` command for their
clones.

## Release evidence back into the repository

Some repositories record a published Release as evidence (a publication decision, a
release plan status). Record it in a follow-up change after `RELEASE_VERIFIED`; a
preparation commit must not claim released state.
