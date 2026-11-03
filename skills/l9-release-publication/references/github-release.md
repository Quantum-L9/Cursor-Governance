<!-- L9_META
schema: 1
parent: l9-release-publication
layer: reference
role: host-release-contract
version: 1.0.0
status: active
-->

# Release job and host Release

## Find the one run

List runs with `gh api repos/<owner>/<name>/actions/runs?event=push&head_sha=<commit>`.
Keep the run whose event is the tag push (TAG_TRIGGERED) or the merge to the default
branch (MAIN_TAGGER) and whose `head_sha` is the release commit. Ignore older
waiting runs. Do not start `workflow_dispatch` while that run exists, and do not
re-run a job that finished: a job's own decision step may have skipped work that
already exists.

If a job waits on an environment, report the run URL, job URL, environment name and
required reviewer, and stop. The operator approves that run; continue on the same run
id. Never approve or cancel on the operator's behalf, even when the API allows it.

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
python3 scripts/verify_github_release.py --remote <owner/name> --tag <tag> \
  --peeled-commit <commit> [--require-asset <name> ...] [--major-tag <vN>]
```

Report `RELEASE_VERIFIED` only on exit 0. `RELEASE_ABSENT` after a successful job
whose `release_creator` is `workflow` means the job skipped the Release: read its
decision log before doing anything else.

## Release evidence back into the repository

Some repositories record a published Release as evidence (a publication decision, a
release plan status). Record it in a follow-up change after `RELEASE_VERIFIED`; a
preparation commit must not claim released state.
