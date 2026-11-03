---
name: Local PR template
overview: Drop the Cursor-Governance change. This repo already publishes with its
  own body builder, and a pull-request template belongs in this repository.
todos:
- id: template-file
  content: Add .github/pull_request_template.md with Summary, Changes, and the Test
    plan checklist
  status: completed
- id: body-builder
  content: Make scripts/build_pr_body.py fill that file from the commit list and diff
    stat
  status: completed
- id: body-test
  content: Assert the built body keeps the template Test plan and includes the commit
    subject
  status: completed
isProject: false
built: true
status: built
---

# Local pull-request template

The previous plan was a guard in Cursor-Governance [`ops/scripts/open_pr_after_gate.sh`](file:///Users/ib-mac/.cursor-governance/ops/scripts/open_pr_after_gate.sh): if the workspace is native-route, skip `cryptoxdog/.github` and hand off to this repo. That is the wrong repository. That script is the Quantum-L9 publisher. This repo is registered not to use it.

[`ops/make/publish.mk`](file:///Users/ib-mac/.cursor-governance/ops/make/publish.mk) already does the split. A native route calls `run_native_publish.sh`, which runs this repo's `make pr`. Only the governance route calls `open_pr_after_gate.sh`, and that is the script that refuses to push until `<owner>/.github` exists. A file added here cannot make that script succeed, because it never reads this repo's template.

This repo's opener is [`scripts/git_open_pr.sh`](scripts/git_open_pr.sh). It sends the body from [`scripts/build_pr_body.py`](scripts/build_pr_body.py) (`## Summary`, `## Changes`, `## Test plan`). That path does not look up `cryptoxdog/.github`. The 404 happened because the governance script was invoked directly.

## Change

One template, in this repo, used by the body builder that already runs:

- Add [`.github/pull_request_template.md`](.github/pull_request_template.md) with those three sections. The test-plan checklist lives in the file, so it is the checklist people edit.
- [`scripts/build_pr_body.py`](scripts/build_pr_body.py) reads that file, fills Summary from `origin/<base>..HEAD` commit subjects and Changes from the diff stat, and leaves the template's Test plan in place. The hardcoded markdown string goes away.
- [`scripts/git_open_pr.sh`](scripts/git_open_pr.sh) stays the sender. It already passes `--body`, which is what GitHub uses; a template file alone is not applied when a body is passed.

No edit to Cursor-Governance, no `cryptoxdog/.github`, and no change to the install-smoke refusal in [`scripts/git_push_with_pr.sh`](scripts/git_push_with_pr.sh).

## Check

A small test that `build_pr_body.py` output contains the template's Test plan text plus a commit subject. Existing [`tests/test_make_pr_publication.py`](tests/test_make_pr_publication.py) does not assert body text, so it stays as it is.

## Build evidence (auto)

- detected_at: `2026-10-22T02:16:37Z`
- conversation_id: `ef60cedd-b4f4-48c5-910e-919c096ff6b2`
- generation_id: `768cc0ab-29d6-4488-91cb-ef0bf993e9f2`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/ef60cedd-b4f4-48c5-910e-919c096ff6b2/ef60cedd-b4f4-48c5-910e-919c096ff6b2.jsonl`
- todos at build time:
- `template-file`: completed
- `body-builder`: completed
- `body-test`: completed
