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

| Campaign | Integration branch | Execute order |
|---|---|---|
| `bounded-replanning-v1` | `campaign/bounded-replanning-v1` | 1 (PE host; this repo) |
| `l9-devpack-program-execution-hardening` | `campaign/l9-devpack-program-execution-hardening` | 2 (after attaching `l9-devpack-compiler`) |
| `cc-pe-intent-compiler-v1` | `campaign/cc-pe-intent-compiler-v1` | 3 (same compiler repo, after hardening) |
| `l9-ecosystem-fix-plan` | `campaign/l9-ecosystem-fix-plan` | 4 (parallel; after attaching `IB-Odoo_19`) |

Stacked work inside a campaign:

```bash
PR_BASE=origin/campaign/<campaign_id> PR_REMEDIATE=0 make pr
```
