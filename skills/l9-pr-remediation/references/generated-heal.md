<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: generated_heal
tags: [pr, generated, merge, manifest]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-28
/L9_META -->

# Generated-artifact heal

Same remediator publish path as source fixes: `make precommit-repo`, commit, and publish via `PR_STACK=auto PR_REMEDIATE=0 make pr`. Bare `git push` is forbidden across all surfaces (ADR-0052). Not a second protocol.

Never `git merge origin/main` to "fix" a failing required check. After the oldest ready PR merges, remaining heads may catch up only to heal generated companions, then regen. Do not file-audit generated paths.

## Classifier

After `git merge origin/main` (or GitHub `CONFLICTING`), list dirty / unresolved paths.

A path is generated when `ops/scripts/sync_generated_artifacts.py` `is_generated_path` is true.

File-by-file architecture audit is forbidden unless
`git diff --name-only --diff-filter=U` lists a path that is **not** generated.

## Heal

```bash
"$PWD/.venv/bin/python" ops/scripts/sync_generated_artifacts.py --root . --force
```

Then `PR_BASE=origin/main make precommit-repo`, one commit, and publish via `PR_STACK=auto PR_REMEDIATE=0 make pr`. An unexpected Program Execution manifest is not a generated artifact this skill regenerates.

## Fail closed

A non-generated unresolved path is a real conflict. Diagnose that file. Still publish via `PR_STACK=auto PR_REMEDIATE=0 make pr`. Bare `git push` is forbidden.
