<!-- L9_META
schema: 1
parent: l9-release-publication
layer: adapter
role: transport-without-publication-gate
version: 1.0.0
status: active
-->

# Ungoverned git

Load only when the push runs where `ops/autonomy/first_publication_gate.py` is not
installed (no governance checkout, no PreToolUse publication hook).

## Decision change

- Do not write a publish-path receipt and do not set `L9_LOCAL_PUSH_AUTHORIZED`.
- Push the verified tag ref once: `git push origin refs/tags/<tag>`.
- MAIN_TAGGER branches still go through a pull request; without `make pr`, open it
  with the host's normal PR flow and leave the merge to the operator.

## Unchanged

Tag identity checks (`scripts/verify_release_tag.py`), the one-run rule, environment
approval stops, digest checks, and `scripts/verify_github_release.py` all still apply.
`--force`, `--tags`, deleting a tag, and API-created tag objects stay forbidden.

If the gate's presence cannot be determined, do not use this adapter: stop with
transport `Unknown`.
