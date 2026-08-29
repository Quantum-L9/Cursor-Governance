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

Same remediator publish path as source fixes: `make precommit-repo`, commit, `git push`. Not a second protocol.

After the oldest ready PR merges and remaining heads `git merge origin/main`, regen. Do not file-audit generated paths.

## Classifier

After `git merge origin/main` (or GitHub `CONFLICTING`), list dirty / unresolved paths.

A path is generated when `ops/scripts/sync_generated_artifacts.py` `is_generated_path` is true, or the path is `environment/program-execution/MANIFEST.json`.

File-by-file architecture audit is forbidden unless
`git diff --name-only --diff-filter=U` lists a path that is **not** generated.

## Heal

```bash
"$PWD/.venv/bin/python" ops/scripts/sync_generated_artifacts.py --root . --force
```

When `environment/program-execution/MANIFEST.json` is in the set:

```bash
"$PWD/.venv/bin/python" environment/program-execution/scripts/generate_manifest.py
"$PWD/.venv/bin/python" environment/program-execution/scripts/validate_manifest.py
```

`validate_manifest.py` must print `"status": "PASS"`. Then `PR_BASE=origin/main make precommit-repo`, one commit, `git push` the already-open PR branch.

## Fail closed

A non-generated unresolved path is a real conflict. Diagnose that file. Still publish via `make precommit-repo` plus `git push`. Do not run `make pr`.
