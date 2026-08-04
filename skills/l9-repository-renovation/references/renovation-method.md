<!-- L9_META
layer: reference
role: renovation_method
tags: [synthesis, leverage, implementation]
status: active
-->
# Renovation Method

## Synthesis before repair

Convert findings into authority decisions. For each concern answer:

1. What authority exists today?
2. Which authority actually controls runtime or CI?
3. Which authority should remain canonical?
4. Which mechanisms become delegates, generated mirrors, migrations, or deletions?
5. What executable proof prevents recurrence?

A renovation is not a list of fixes. It is a smaller operating model.

## Leverage order

Prefer changes that eliminate whole classes of drift:

1. one manifest and lock authority;
2. one suite registry and runner;
3. CI delegates to local canonical commands;
4. drift validators enforce parity;
5. documentation reflects the proven model;
6. superseded paths are removed.

## Full-file rule

Implementation artifacts must be complete and internally consistent. Never emit a design brief that asks another coding agent to choose schemas, paths, commands, or behavior. When a file is replaced, provide the final full file or make the edit directly.

## Compatibility shims

Keep a shim only when a verified consumer still invokes the legacy path. The shim may forward arguments and exit codes, but it must not duplicate policy, dependency lists, suite topology, or validation logic.

## Commit anatomy

Each commit should establish one stable layer and pass its scoped validation:

1. declarations and lock state;
2. canonical model and runner;
3. validators and negative tests;
4. CI, docs, and handoff.

Reorder when repository evidence demands it, but never commit a consumer before its authority exists.
