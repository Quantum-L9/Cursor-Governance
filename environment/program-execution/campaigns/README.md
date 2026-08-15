# Program Execution campaigns

Immutable operator seeds live in each `*/CAMPAIGN_SOURCE.yaml`. Mutable
controller runtime stays under `$HOME/.l9/programs/<campaign_id>`.

## Landing policy

SSOT: `CAMPAIGN_EXECUTION_POLICY.yaml` + `ops/autonomy/surface_profile.yaml`
(`campaign_execution`).

| Rule | Value |
|---|---|
| Publish path | `PR_REMEDIATE=0 make pr` (Makefile checkers, then push + PR) |
| Remediation | forbidden |
| Merge | forbidden (human `L9_MERGE_AUTHORIZED` only) |
| PR base | the campaign integration branch — **not** `main` |
| Mixing | do not land campaign commits on unrelated feature branches |
| PR title | `[{campaign_id}] {metadata.title}` via `scripts/campaign_pr_copy.py` |
| PR body | campaign id, title, objective, integration branch, execute order |
| Runtime status | pec writes `$HOME/.l9/programs/<id>/runtime/campaign-status.json`; running flips `runtime_status` to `active`. Source `metadata.status` stays `operator_intake`. |
| Live closeout | **Required last step.** `pec close` (or a CONVERGED/NOT_CONVERGED `export-handoff`) sets `runtime_status=completed`. Mirror that in `CAMPAIGN_STATUS.yaml` via `campaigns/scripts/close_campaign.py`. Next campaign is the first execute_order that is not `complete`. Leaving a finished campaign `active` / `in_progress` is a defect. |

| Campaign | Integration branch | Execute order | Lifecycle |
|---|---|---|---|
| `bounded-replanning-v1` | `campaign/bounded-replanning-v1` | 1 (PE host; this repo) | **complete** (PR #149) |
| `cc-pe-intent-compiler-v1` | `campaign/cc-pe-intent-compiler-v1` | 2 (build PE compiler module) | **complete** (PR #151) |
| `l9-devpack-program-execution-hardening` | `campaign/l9-devpack-program-execution-hardening` | 3 (harden same module) | **complete** (PR #150) |
| `l9-ecosystem-fix-plan` | `campaign/l9-ecosystem-fix-plan` | 4 (`IB-Odoo_19`) | planned — **next** (Odoo host [PR #153](https://github.com/cryptoxdog/IB-Odoo_19/pull/153)) |

Owner (AUTH-001) terminal verdict on 2026-08-14: **CONVERGED**. Locked campaign
YAML ceilings are `commit/push/pull_request: true` and `merge: false`. This
verdict expands authorization; it does not claim engineering waves completed.

Stacked work inside a campaign:

```bash
PR_BASE=origin/campaign/<campaign_id> PR_REMEDIATE=0 make pr
```
