<!-- L9_META
schema: 1
parent: l9-pr-integration-testing
layer: reference
role: repository-adapter-selection
version: 0.1.0
status: active
-->

# Repository adapters, selected from observed files

This skill's core only knows Git, Docker, immutable source evidence and argv-based validation. `detect_adapters()` suggests categories; it never invents test commands or declares a runtime ready. Adapter selection requires a frozen source-tree census and positive evidence of applicable tests.

## Python applications

Detect via `pyproject.toml`, Python source, packaging or test configuration. Verify actual tox/nox/pytest/unittest invocation and lock dependencies at the **baseline**. For example, a confirmed `Makefile` comment or CI command may justify `python -m unittest discover -s tests -v` in a pre-provisioned image. Verify that the command actually exercises intended behavior. `pytest` failure identity parsing is available only if supplied as `failure_parser=pytest`; `unittest` supports `failure_parser=unittest`. No unconditional Python test default.

**Fixture witness:** a Python `unittest` history demonstrates single/multiple Git merges, cross-PR semantic failures, red baselines, a new regression and surviving/killed negative mutations on the local fixture host. It does not prove a Docker image works.

## Node / TypeScript

Detect via a parsed `package.json`, JS/TS source, lockfile, CI and actual tests. Confirm whether the project uses Node built-in tests, Jest, Vitest or another framework and resolve the verified command. Do not run `npm install` from unpinned live dependencies by default. `node --test` and an actual `node:test` fixture have been executed locally. `failure_parser=node-test` is applicable to compatible TAP-style output, not arbitrary JS test runners. Static TypeScript compilation is a separate verified check if required.

**Fixture witness:** a committed Node repository passes `node --test` in a disposable local fixture checkout. Docker behavior remains unproven.

## Containerized and multi-service systems

A Dockerfile or Compose file does not authorize using its runtime environment. Require a reviewed, locally present pinned image containing Git and the required test runtime. Docker runs with no network, no privileged mode, no host mounts beyond the disposable worktree, read-only root filesystem and explicit UID. Stateful dependencies and inter-container networking are **unsupported by the basic safe runner**. If required, record `BLOCKED`/`INCOMPLETE_EVIDENCE` and extend the adapter with reviewed, isolated provisioning plus executable witnesses. Do not point tests at production databases or accounts.

## Odoo addons and PostgreSQL

Detect active Odoo addon manifests from source, distinguish comments from actual `depends`, observe `auto_install`, installed addons and actual runtime model field overrides. Bind Odoo version, edition and target fixtures. Only a verified target-provided command may be executed, and a real disposable PostgreSQL DB with installed addons is required to prove ORM, ACL, migrations, cron, transactional behavior, XML views and cross-addon integration. Enterprise claims require a real available Enterprise fixture with matching license/edition, not a Community pass or fake stub. No Odoo runtime adapter is claimed in this release; manifest category detection alone is not conformance.

## Database-backed repositories

Verify migrations, isolation, DB version, schema state and fixture lifecycles from target repo evidence. The basic runner disallows external networks; a DB-dependent test cannot be replaced by mocks and marked integration-proven. Develop a separate adapter only when its service isolation and cleanup have real positive/adversarial Docker witnesses.

## Common executable procedure contract

The pinned manifest declares each test as:

```json
{
  "id": "unit-and-integration",
  "argv": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
  "timeout_seconds": 300,
  "failure_parser": "unittest",
  "source": {
    "path": "Makefile",
    "sha256": "exact file sha256 at the frozen base",
    "anchor": "python -m unittest discover -s tests -v"
  }
}
```

The example is a shape illustration, not proof that any target Makefile contains that command. All commands use argv, not shell interpolation; prove their target-specific origin and expected property. If the CI/test declaration itself changes in a PR, inspect its impact separately. Docker images must be pinned by manifest digest or local image ID and locally available; fetching unknown images or installing dependencies during testing is not a safe implicit default.
