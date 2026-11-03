<!-- L9_META
schema: 1
parent: l9-release-publication
layer: reference
role: release-model-sequences
version: 1.0.0
status: active
-->

# Release models

`scripts/detect_release_model.py --repo-dir <checkout>` decides the model from the
repository's own `.github/workflows/`. It also reports `tag_creator` and
`release_creator`. Those two fields, not habit from another repository, say which
steps below are yours.

## Shared preconditions (every model)

1. **Current, not stale.** The release commit is the tip of the default branch the
   operator named (or the merge commit of the version PR). Read it with
   `git ls-remote origin refs/heads/<default>`. An existing tag is never re-pointed:
   if `vX.Y.Z` already exists at another commit, the current code needs a new
   version, not a moved tag.
2. **Version is an operator decision.** Read the changelog's unreleased section. If it
   carries breaking changes, present the major and the minor option with their
   effect on the maintained major tag, and ask once. Do not infer the line.
3. **Version authority.** `version_authority` lists the files that carry the version.
   The repository's own preparation script (for example `<consumer-repo>:scripts/prepare-release.js`)
   owns derived files; find and run it instead of hand-editing them.
4. **Derived release evidence.** Anything that embeds the producer version or the
   commit (conformance records, golden packets, validation reports) moves with the
   bump. Run the repository's full gate after the bump and refresh what it names
   before the version change merges.

## TAG_TRIGGERED — a job runs on `push: tags:`

The tag object is the release identity and is admitted by the operator.

1. The operator names the tag, the annotated tag-object sha, and the peeled commit.
   If the tag does not exist yet, create it only on an explicit order:
   `git tag -a <tag> <commit> -m "<tag>"`, then read back both shas.
2. `verify_release_tag.py --repo-dir <checkout> --tag <tag> --tag-object <obj> --peeled-commit <sha>`.
   Exit 1 stops. Never delete, move, or recreate the tag.
3. Add `--remote owner/name --bind-origin`. `MATCH`: already published, go to 6.
   `REMOTE_ABSENT`: continue. Anything else stops.
4. Push exactly `refs/tags/<tag>` (references/publication-plane.md).
5. Re-run with `--remote owner/name --require-remote`; continue only on `MATCH`.
6. Watch the one run that push created (references/github-release.md). An environment
   approval wait is a stop: report run URL, job URL, environment, reviewer.
7. `release_creator: workflow` → only verify. `release_creator: agent` → create the
   Release bound to the peeled commit with the assets the repository's release
   decision names.
8. `verify_github_release.py` must report `RELEASE_VERIFIED`.

## MAIN_TAGGER — a branch-push job creates the tag itself

The release is the version change that job watches. You never create the tag:
doing so races the job for the same name at the same commit.

1. Bump the version authority and run the repository's preparation script on the
   branch name its release-prep job expects (read the workflow's `on.push` branches,
   for example `release/v*.*.*`).
2. Run the repository's full gate; refresh derived release evidence (shared 4).
3. Publish the branch through the governed path (`PR_REMEDIATE=0 make pr`). A
   release-prep job may push its own commit to the branch (for example a validation
   report bind); integrate it with a merge, never a force push, and keep the newer
   evidence.
4. Merge only on the operator's order, at a green head, through
   `skills/l9-pr-remediation` merge tooling (`ops/autonomy/stack_safe_merge.py --run`).
5. Watch the release job the merge started. Its own decision step may skip work that
   already exists; read it rather than re-running it.
6. `verify_release_tag.py --remote owner/name --tag <tag> --kind any --peeled-commit <merge sha> --require-remote`,
   then `verify_github_release.py ... --major-tag <vN>` when the job advances a major tag.

## NO_AUTOMATION — nothing creates or reacts to a tag

1. With the operator's version and commit, create an annotated tag locally:
   `git tag -a <tag> <commit> -m "<tag>"`. Read back the tag-object sha.
2. Run TAG_TRIGGERED steps 2–5 (verify, bind origin, push the one ref, verify remote).
3. Create the Release: `gh release create <tag> --verify-tag --title <tag> --notes-file <notes>`.
   `--verify-tag` refuses to let the host invent a tag at another commit.
4. `verify_github_release.py` must report `RELEASE_VERIFIED`.

## AMBIGUOUS or UNKNOWN

Both a tag-push publisher and a branch-push tagger exist, or the workflows could not
be read. Stop, show the evidence list, and ask which job owns the release. Never
pick one.
