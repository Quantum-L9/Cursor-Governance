<!-- L9_META
layer: reference
role: stack_adapters
tags: [python, node, monorepo]
status: active
-->
# Stack Adapters

Load only the verified adapter. These rules modify the generic workflow rather than replacing it.

## Python and uv

Trigger: `pyproject.toml` with `uv.lock` or documented uv bootstrap.

- Distinguish runtime dependencies, development tools, optional features, and dependency groups.
- Treat `[tool.uv] package = false` as a virtual-project decision. Prove install behavior before changing `[build-system]`.
- Require `uv lock --check` and locked synchronization in local and CI paths.
- Map Python import roots to distributions carefully. Do not assume import name equals package name.
- Audit pytest `testpaths`, `addopts`, ignores, `norecursedirs`, import modes, and duplicate top-level packages.
- Put CI-only pytest plugins in the locked development contract when CI requires them.

## Node and TypeScript

Trigger: `package.json` with a recognized lockfile.

- Establish one package manager and frozen-lockfile install command.
- Reconcile root and workspace scripts, package exports, build outputs, typecheck, lint, and test commands.
- Detect CI commands that bypass package scripts or install undeclared global tools.
- Preserve published exports and semver behavior unless a migration is explicitly authorized.
- Isolate unit, integration, browser, and generated-code suites through one documented runner or task graph.

## Polyglot and monorepo

Trigger: multiple package boundaries, languages, or release units.

- Audit each package independently before reconciling root orchestration.
- Do not force one global manifest to own package-local dependencies.
- Make root automation dependency-aware and changed-path-aware without skipping required cross-package contracts.
- Map upstream/downstream release and compatibility effects before editing shared schemas or generated clients.
- Split PRs only when package ownership or release independence is real. Keep tightly coupled authority repair together.
