# Codecov review (2026-11-20)

Source: Codecov's public API (`api.codecov.io/api/v2/github/<owner>/repos/`, anonymous; no Codecov
credential exists in Infisical), the campaign repositories' default branches, and the GitHub Actions
API. All facts below are observed. Plan and billing were not read (`UNKNOWN`).

## Where Codecov is wired

| Repository | Upload in CI | Codecov project state |
|---|---|---|
| Cognitive.Engine.Graphs | `dev-layer-gmp.yml` only: `pull_request` filtered to `dev_layer/**` and `tests/dev_layer/**`, plus manual dispatch. No upload token. `fail_ci_if_error: true` under `continue-on-error: true`; since #515 the outcome is reported by `tools/scanner_outcomes.py`. | Active only under the old owner `cryptoxdog/Cognitive.Engine.Graphs`; last update 2026-03-13. Not listed under `Quantum-L9`. |
| Enrichment.Inference.Engine, Cursor-Governance, l9-ci-core, l9-ci-sdk, .github | none | Listed but not activated (Core, SDK, .github) or not listed |
| cryptoxdog/IB-Odoo_19 (Staging) | none | Active, no coverage total |

The CEG workflow's last 10 runs are all `failure`, the newest on 2026-03-11. It has not run since.
Organization-wide, two `Quantum-L9` projects are active with coverage: `l9-node-template` (70.25%) and
`golden-repo` (3.79%).

## Verdict

`RETIRE_CANDIDATE` for the campaign repositories. No campaign repository sends Codecov a usable
report. The one upload path is path-filtered, has not run for eight months, failed every time it
ran, and posts to a project under an owner the repository has left. Sonar is the coverage sink the
campaign is wiring: Core #289 imports coverage from Core's existing test runs, with no second test
run. A second coverage service would duplicate the upload and the gate without adding a signal.

| Item | Owner | Action |
|---|---|---|
| Remove the CEG Codecov step and keep the coverage threshold in the test step | CEG, cleanup wave (deliverable 8) | after the Cursor-Governance canary; CEG is off-limits for merges until the operator releases it |
| `l9-node-template` uploads to Codecov, so repositories created from it inherit an upload | template owner, fleet wave | decide before fleet rollout: point new repositories at Sonar coverage instead |
| Codecov GitHub App installation and plan | operator | read-only check of the plan; uninstall only on decision |
