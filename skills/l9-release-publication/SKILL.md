---
name: l9-release-publication
description: Cut and publish a release tag and its GitHub Release for any L9 repository, detecting whether the repo publishes on tag push, tags itself on a version-bump merge, or has no release automation, then verifying tag identity, the release job and the Release. Use when the operator asks to cut, ship or finish a release or advance a major tag. Do not use for release notes, deployment, consumer rebinds, registry publishing, or moving an existing tag.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, release, tag, publication, github, versioning]
  owner: igor_beylin
  status: active
  version: "1.0.0"
  updated: "2026-11-03"
  license: Proprietary
---

# Release publication

## Purpose

Ship the current code of one repository as an immutable, verified release: the right
version, a tag that names the right commit, the repository's own release job allowed to
do its part, and a host Release that matches. Generalized from the l9-graphiti-memory
tag-push procedure to every release model an L9 repository uses.

## Activation boundary

Explicit invocation only: publishing is irreversible. Use when the operator names a
repository and asks to cut, publish, finish or verify a release, or to advance its
maintained major tag. Reject release-note drafting, environment deployment, consumer
rebinds (`skills/l9-memory-consumer-rebind`), registry publication without a recorded
owner approval, and any request to move, delete or recreate a tag that already exists.

## Authority

1. The operator's latest instruction: repository, version (or the choice between lines),
   and, for an admitted tag, the tag-object sha and peeled commit.
2. The repository's release job definitions and release decision documents.
3. The repository's version authority file and preparation script.
4. `scripts/verify_release_tag.py` and `scripts/verify_github_release.py` output against the host.
5. The release job's run log and conclusion.
6. `Unknown`. Inference never supplies a model, version, SHA, digest or publication claim.

## Sequence

1. **Bind the target.** Check out the repository at the current tip of its default
   branch. Read the tip with `git ls-remote origin refs/heads/<default>`; that commit
   (or the version PR's merge commit) is what ships. A stale commit is never released.
2. **Detect the model.** `python3 scripts/detect_release_model.py --repo-dir <checkout>`.
   It reports `model` (TAG_TRIGGERED, MAIN_TAGGER, NO_AUTOMATION, AMBIGUOUS, UNKNOWN),
   `tag_creator`, `release_creator` and `version_authority`. AMBIGUOUS or UNKNOWN: stop
   and show the evidence.
3. **Settle the version.** If the requested tag exists at another commit, stop and offer
   the next version. If the unreleased changelog carries breaking changes, ask once
   which line (major or minor, and what that does to the maintained major tag).
4. **Run the model's sequence** in [release-models.md](references/release-models.md). Tag pushes
   follow [publication-plane.md](references/publication-plane.md); the release job and Release follow
   [github-release.md](references/github-release.md).
5. **Verify.** `scripts/verify_release_tag.py --remote <owner/name> --require-remote`
   (`--kind any` for a tag a job created), then `scripts/verify_github_release.py`, adding
   `--major-tag <vN>` when the release advances one. Report `RELEASE_VERIFIED` only on its exit 0.
6. **Close out.** Record release evidence the repository keeps in a follow-up change, close
   the release issue with the tag, Release URL and commit, and report open items (registry
   publication, dependency PRs that now need rebinding).

## Stops

- AMBIGUOUS or UNKNOWN model, an existing tag at another commit, or a version line the
  operator has not chosen.
- A release job waiting on an environment: report the run URL, job URL, environment and
  reviewer. Never approve on the operator's behalf.
- Merging a version change, pushing a tag, or creating a Release without the operator's order.
- `MISMATCH` or `TRANSPORT_BLOCKED` from a verifier: stop; never force a ref.

## Adapters

The core sequence assumes the governance publication plane evaluates tag pushes. Where
`ops/autonomy/first_publication_gate.py` is not installed, load
[ungoverned-git.md](adapters/ungoverned-git.md). If its presence cannot be determined, stop with
transport `Unknown`.

## Verification commands

```bash
python3 scripts/detect_release_model.py --repo-dir <checkout>
python3 scripts/verify_release_tag.py --repo-dir <checkout> --tag <tag> --tag-object <obj> --peeled-commit <sha> --remote <owner/name> --bind-origin
python3 scripts/verify_release_tag.py --remote <owner/name> --tag <tag> --kind any --peeled-commit <sha> --require-remote
python3 scripts/verify_github_release.py --remote <owner/name> --tag <tag> --peeled-commit <sha> --major-tag <vN>
```

Exit codes: verify_release_tag 0 MATCH, 1 MISMATCH, 2 REMOTE_ABSENT, 3 TRANSPORT_BLOCKED;
verify_github_release 0 RELEASE_VERIFIED, 1 MISMATCH, 2 RELEASE_ABSENT, 3 TRANSPORT_BLOCKED.

## After use

This pack was compiled by `skills/l9-skill-compiler` through `extract_expertise` and the
compiler's `enforcement-gates`; [skill_intelligence_report.yaml](skill_intelligence_report.yaml)
records activation, heuristics and failure controls and is not publication authority.
When a run misclassifies a repository, misses or false-triggers, or the operator corrects
a step, change the smallest pattern or heuristic, add a regression test under
`tests/skills/l9_release_publication/`, and rerun `validate_skill_pack.py` and
`validate_exemplary_skill.py` from `skills/l9-skill-compiler/scripts/`.
