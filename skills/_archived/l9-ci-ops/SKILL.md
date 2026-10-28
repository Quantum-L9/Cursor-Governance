---
name: l9-ci-ops
description: "deprecated — do not activate. archived out of live skills/ discovery. CI status and repair follow make pr and l9-pr-remediation."
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

# l9-ci-ops (deprecated)

Do not activate. `/ci` and `/ci-policy` are already retired. This pack still
treated `.github/workflows/ci.yml` and a PlasticOS `make push` into Staging as
ground truth. This repository has no `ci.yml`. Publication is `make pr`.

Live owners:

- Required `main` contexts are declared in `ops/scripts/test_required_contexts_report.py`.
- Local diagnosis is `OPEN_PR=0 make pr`.
- A red required check on an open PR is `l9-pr-remediation`.

The reference files under this directory are historical. Do not load them.
There is no successor skill.
