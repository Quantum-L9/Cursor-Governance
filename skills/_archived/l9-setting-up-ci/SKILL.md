---
name: l9-setting-up-ci
description: "deprecated — do not activate. archived out of live skills/ discovery. CI setup is the repo's workflow files and make pr, not this pack."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, ci, deprecated]
  owner: igor_beylin
  status: deprecated
  version: 2.0.0
  updated: 2026-10-27
---

# l9-setting-up-ci (deprecated)

Do not activate. This pack taught the Quantum-L9 `.github` seeder and an
`l9-ci-core` `presets/typescript` stamp, including a hardcoded Biome pin and a
Node workflow that still ran `tsc` and tests. That is not the live CI plane.

Live owners:

- Required `main` contexts are declared in `ops/scripts/test_required_contexts_report.py`.
- Consumer lint and test is `.github/workflows/l9-lint-test.yml`.
- Biome is `.github/workflows/l9-lint-test-node.yml` calling `l9-ci-sdk`.
- Publication is `make pr`.
- A red required check on an open PR is `l9-pr-remediation`.

There is no successor skill. Do not recreate `skills/l9-ci`.
