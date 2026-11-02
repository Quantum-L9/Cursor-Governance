<!-- L9_META
schema: 1
parent: l9-pr-integration-testing
layer: reference
role: repository-adapter-selection
version: 0.3.0
status: active
-->

# Repository adapters, selected from observed files

This skill's core only knows Git, Docker, immutable source evidence and argv-based validation. `detect_adapters()` suggests categories; it never invents test commands or declares a runtime ready. Adapter selection requires a frozen source-tree census and positive evidence of applicable tests.

## Hosted session environment (owned by governance, not by this skill)

The sandbox is `ops/scripts/docker_sandbox.py` in Cursor-Governance. Cloud SessionStart
warms it in the background; `scripts/quick.py` runs the same idempotent `ensure` when no
READY receipt exists. Do not reimplement any of it here. It provides, with a receipt at
`~/.l9/docker-sandbox/receipt.json`:

| Need | Why the runner needs it | Provided by |
|---|---|---|
| A running Docker daemon | hosted containers ship the CLI but no daemon | `ensure` starts `dockerd` when the session is root |
| A non-root runner in the `docker` group | `DockerSandbox` refuses UID 0 | user `l9sandbox` (`L9_DOCKER_SANDBOX_USER`) |
| The session TLS trust bundle, readable by that user | host-side `git fetch` goes through a TLS-intercepting proxy; the original bundle is root-only | copied from `PIP_CERT` / `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE` |
| A pinned image with Git, `make` and the test runtime | merges, checkouts and tests all run inside a no-network container | `l9-ci-toolchain:core-<sha12>`, built from Quantum-L9/l9-ci-core `toolchain-lock.json` and `requirements-consumer-ci.txt` at an exact Core commit and verified tool-by-tool; `--with-semgrep` adds Core's hash-locked semgrep; Biome is excluded |
| The official python base, despite Docker Hub rate limits | hosted sessions share outbound IPs, so anonymous Docker Hub pulls return HTTP 429 | a local copy first, then Docker Hub, then `mirror.gcr.io` (`L9_DOCKER_SANDBOX_MIRRORS`); `ensure` also starts `dockerd` with those mirrors. The base is pinned by content digest either way, which the mirror serves unchanged; the receipt records it as `base_image` |

Repository dependencies cannot be installed during a no-network test, so the quick path
layers the repository's own `make setup` output, run at the **base** SHA, onto that image.
Isolated PEP 517 builds (`python -m build`, `pip install .`) resolve their build backend at
test time, which a no-network container cannot do. The layer therefore pre-downloads the
repository's `[build-system].requires` (or `setuptools>=40.8.0`, pip's fallback for a
setuptools project without that table) into `/opt/l9-wheelhouse` after `make setup`, and
sets `PIP_FIND_LINKS` to it and `PIP_NO_INDEX=1` for the test run. A test that needs any
other package at run time still fails offline, and that failure is correct: declare the
package in the repository's own setup. For a hand-written manifest, `quick.py --image-only`
builds this layer and prints its pinned image id.

A PR that changes a dependency input (manifests, lockfiles, `requirements*.txt`, `Makefile`,
`Repo.mk`) is BLOCKED by the quick path, because that layer would test it against stale
dependencies; build such a manifest by hand with an image provisioned from the combined revision.

## Repository Execution V2 (`make-v1` facade)

A repository whose `.l9/repo-workflow.json` declares `l9.repo-execution/v2` with facade
`make-v1` names its own phases (`setup`, `validate`, `check`, `test`). `scripts/quick.py`
turns only declared phases into argv `["make", "<phase>"]`, sourced from that file at the
base SHA with its sha256 and the phase literal as anchor. A repository without that
contract is BLOCKED by the quick path; build the manifest by hand from its verified CI
instead.

**Docker witness:** Quantum-L9/l9-ci-core#220 on base `89c9bc4e` — `make test` 821/821 on
the baseline and 822/822 for the PR and the combined candidate in the Core-locked image,
and the yaml-suffix revert probe KILLED. The first attempt failed 22 tests on the baseline
too: `/tmp` was `noexec` and the runner's `GIT_CONFIG_GLOBAL=/dev/null` hid the suite's own
`~/.gitconfig`. A red baseline is a profile defect to diagnose first, not a property of the
target.

## Python applications

Detect via `pyproject.toml`, Python source, packaging or test configuration. Verify actual tox/nox/pytest/unittest invocation and lock dependencies at the **baseline**. For example, a confirmed `Makefile` comment or CI command may justify `python -m unittest discover -s tests -v` in a pre-provisioned image. Verify that the command actually exercises intended behavior. `pytest` failure identity parsing is available only if supplied as `failure_parser=pytest`; `unittest` supports `failure_parser=unittest`. No unconditional Python test default.

**Fixture witness:** a Python `unittest` history demonstrates single/multiple Git merges, cross-PR semantic failures, red baselines, a new regression and surviving/killed negative mutations on the local fixture host. It does not prove a Docker image works.

## Node / TypeScript

Detect via a parsed `package.json`, JS/TS source, lockfile, CI and actual tests. Confirm whether the project uses Node built-in tests, Jest, Vitest or another framework and resolve the verified command. Do not run `npm install` from unpinned live dependencies by default. `node --test` and an actual `node:test` fixture have been executed locally. `failure_parser=node-test` is applicable to compatible TAP-style output, not arbitrary JS test runners. Static TypeScript compilation is a separate verified check if required.

**Fixture witness:** a committed Node repository passes `node --test` in a disposable local fixture checkout. Node inside the Docker profile remains unproven: the toolchain image carries no Node runtime.

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
