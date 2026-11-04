---
name: Residual audit repairs
overview: Repair four defects that are still true on origin/main, each inside its
  existing owner. Do not reopen the merged October 20 PRs, and do not apply the pack's
  unsafe Core re-pin, dependency bump, or bundle edits.
todos:
- id: census-unreadable
  content: Treat a missing or invalid user-settings path as incomplete with a named
    reason in reconcile_claude_l9_skills.py, and cover both cases plus the CLI exit.
  status: completed
- id: gmp-remediate-zero
  content: Publish adapter /gmp finalize with PR_REMEDIATE=0 in gmp_executor.py, commands/gmp.md,
    and the two adapter tests.
  status: completed
- id: binding-narrative
  content: Align memory-binding.json ref_note, description, and build, plus the README
    rebuild sentence, with uv build --wheel --build-constraint.
  status: completed
- id: drop-measured-closes
  content: Remove _with_measured_closes and keep the existing Closes regression tests
    green.
  status: completed
isProject: false
built: true
status: built
---

# Residual audit repairs

GAR: architecture is already settled. Each repair stays in the module that owns the behavior today. No new component, no second Closes writer, no second publish path.

This checkout (`da5c9a42`) is diverged from `origin/main` (`e31ea231`) and holds unrelated dirt. Build on a clean branch from fetched `origin/main` (sanctioned `agent_worktree_start.sh` if this folder stays dirty). Commit only the paths below. After the todos: `l4_local.py authorize-release`, then `PR_REMEDIATE=0 make pr`. If one unique open-PR chain exists, publish with `PR_STACK=auto`; sibling chains fail closed. Show the PR URL. Do not merge.

## In scope

Four independent repairs:

- **F-737-F1** — unreadable user settings must not count as a passed tier-override check.
- **F-744-F3** — adapter `/gmp` finalize publishes with `PR_REMEDIATE=0` after `authorize-release`.
- **F-752-F1** — binding narrative names the build constraint the proof already uses.
- **F-751-F2** — one Closes writer, `_fill_closes`.

## Out of scope

Leave the October 20 pack's other units alone: no `l9-ci-core` re-pin to `d3fc1b30`, no pre-commit/playwright/claude-agent-sdk bump, no architecture-intelligence bundle or ADR edit, no shallow-clone verifier change, no edits to merged PR bodies or to `Quantum-L9/.github`. Do not rewrite the historical `v2.3.1` sentences in [ops/memory/README.md](ops/memory/README.md) beyond the one reproduction sentence. Do not edit built GMP plan files that still mention `PR_REMEDIATE=1`.

## F-737-F1 — unreadable settings

Owner: [ops/scripts/reconcile_claude_l9_skills.py](ops/scripts/reconcile_claude_l9_skills.py).

`_read_user_settings` returns `None` for a missing file and for invalid JSON. `coverage_census` then sets `tier_override_missing = []` and can report `status: complete` (lines 391–406). `main()` always passes `~/.claude/settings.json` and exits 1 unless status is `complete` (lines 497–503). SessionStart still prints whatever stdout the census emits; a non-zero exit does not fail the hook ([environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh](environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh) lines 537–545).

Change only the requested-path case. `user_settings is None` (unit tests that omit it) stays "check not in scope" and can still be `complete`. A path that is missing, unreadable, or not a JSON object sets status `incomplete`, leaves `tier_override_missing` empty, and records a named reason the banner prints (path plus missing or invalid). Do not invent a list of every explicit-only skill.

Tests in [environment/agents/adapters/claude-code/tests/test_skill_reconciliation.py](environment/agents/adapters/claude-code/tests/test_skill_reconciliation.py): missing file and invalid JSON both yield `incomplete` and the named reason; a valid override file still reaches `complete` (`test_explicit_only_tier_override_checked_in_user_settings`). Update `test_cli_coverage_mode_needs_no_scope`: a HOME with no settings file exits 1 and the banner names that file.

## F-744-F3 — adapter publish flag

Owner: [workflows/gmp_executor.py](workflows/gmp_executor.py) `_publish_pr` (lines 1294–1301). Cursor finalize already returns before `make pr`. Adapter finalize still exports `PR_REMEDIATE=1` after `_maybe_l4_release()`.

Set that export and the recorded subprocess line to `PR_REMEDIATE=0`. In [commands/gmp.md](commands/gmp.md), state that the in-finalize adapter publish uses `PR_REMEDIATE=0`. Leave the Cursor "do not publish again / `PR_REMEDIATE=0 make pr`" instructions as they are.

Flip the two adapter assertions in [tests/workflows/test_gmp_executor_authorized.py](tests/workflows/test_gmp_executor_authorized.py) (lines 186 and 391) to `PR_REMEDIATE=0`. Keep the Cursor assertion that `PR_REMEDIATE=1` is absent (line 347).

## F-752-F1 — binding narrative

Owner: [ops/config/memory-binding.json](ops/config/memory-binding.json) `ref_note`, `release_evidence.description`, and `release_evidence.build`. The proof already runs `uv build --wheel --build-constraint <file>` with `BUILD_CONSTRAINT` taken from `build_backend_constraint` ([.github/workflows/memory-cross-repo.yml](.github/workflows/memory-cross-repo.yml) lines 190–195). `build_backend_note` already says plain `uv build` does not reproduce the wheel.

Amend those three strings so reproduction is `uv build --wheel --build-constraint` of `build_backend_constraint` (`setuptools==84.0.0`) under `SOURCE_DATE_EPOCH`. One sentence in the Proof section of [ops/memory/README.md](ops/memory/README.md) (the rebuild sentence near line 423) gets the same flag. Do not change the pin, the digest, or the workflow.

## F-751-F2 — one Closes writer

`_fill_closes` already writes measured `Closes #N` at the end of Problem, including when the template has no placeholder ([ops/scripts/compose_pr_body.py](ops/scripts/compose_pr_body.py) lines 1478–1523). `_with_measured_closes` (lines 1559–1573) wraps that result and returns immediately when `Closes #\d` is present. `compose_pr_body` calls the wrapper at line 1594.

Delete `_with_measured_closes` and append `_fill_template(...)` directly. Keep `test_closes_only_for_issues_a_commit_names` and `test_closes_ends_the_problem_text_whatever_was_substituted_before_it` in [ops/scripts/tests/test_compose_pr_body.py](ops/scripts/tests/test_compose_pr_body.py) as the proof that one `Closes` line still lands.

## Validation

- `python3 -m pytest environment/agents/adapters/claude-code/tests/test_skill_reconciliation.py tests/workflows/test_gmp_executor_authorized.py ops/scripts/tests/test_compose_pr_body.py -q`
- Confirm `memory-binding.json` still loads (`tests/ops/memory/test_canonical_epoch.py` if that file is in the changed-file pytest set).
- No new architecture, no edit outside the files named above.

## Build evidence (auto)

- detected_at: `2026-10-27T22:30:03Z`
- conversation_id: `58412f07-4a50-480c-9503-c426e0f5cc60`
- generation_id: `d1cb3673-fd8d-47e2-8b70-e7224598db92`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-l9-graphiti-memory-1/agent-transcripts/58412f07-4a50-480c-9503-c426e0f5cc60/58412f07-4a50-480c-9503-c426e0f5cc60.jsonl`
- todos at build time:
- `census-unreadable`: completed
- `gmp-remediate-zero`: completed
- `binding-narrative`: completed
- `drop-measured-closes`: completed
