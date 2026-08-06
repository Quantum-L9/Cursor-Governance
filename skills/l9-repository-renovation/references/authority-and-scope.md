<!-- L9_META
layer: reference
role: authority_and_scope
tags: [repository, authority, scope, github]
status: active
-->
# Authority and Scope

## Baseline resolution

Pin the exact base commit before diagnosis. Read the default branch, current branch, open related PRs, repository instructions, ownership, invariants, and worktree status. A prior audit against another SHA is historical evidence only.

## Scope lock

Every renovation contract must declare:

- repository and immutable base commit;
- owned package boundaries;
- allowed files and globs;
- forbidden files and capabilities;
- behavior and public contracts that must remain unchanged;
- approved migrations;
- validation commands and rollback;
- unresolved blockers.

Do not use a broad `**/*` allowed scope. New files must have a named role in the target authority model.

## Worktree safety

Never overwrite or stage unrelated changes. Prefer a clean feature branch or isolated worktree. Inspect status and diff before every write checkpoint.

## GitHub authorization ladder

Read operations need no write approval. The following actions are independent and each needs explicit authorization:

1. stage exact paths;
2. create commits;
3. push the branch;
4. create or update a PR;
5. push remediation commits;
6. merge.

A user may authorize several actions in one statement only when each action is named. PR completion never implies merge authority.
