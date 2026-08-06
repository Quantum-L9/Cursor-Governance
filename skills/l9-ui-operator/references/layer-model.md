<!-- L9_META
l9_schema: 1
parent: l9-ui-operator
layer: reference
role: layer_model
tags: [ui-operator, cartridge, playbook]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-06
/L9_META -->

# Layer model

| Layer | Name | Role |
|---|---|---|
| Primitive skill | `l9-aws-secrets` | Resolve refs; registry; fail-closed |
| Orchestrator skill | `l9-ui-operator` | Control plane; loads secrets; drives console |
| Operating playbook | `saas-dashboard-when-api-insufficient` | Triggers, sequence, stop rules |
| Cartridge | e.g. `github-packages-actions-access` | URLs, selectors, allowlist — not a skill |
