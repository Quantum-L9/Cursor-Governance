# Archived Program Execution campaigns

Completed or cancelled campaign seeds live here. They are history, not live
discovery.

| Rule | Value |
|---|---|
| Live tree | `environment/program-execution/campaigns/<id>/` |
| Archive tree | `environment/program-execution/campaigns/_archived/<id>/` |
| When | after `CAMPAIGN_STATUS.yaml` lifecycle is `complete` or `cancelled` |
| Command | `python3 environment/program-execution/campaigns/scripts/close_campaign.py archive --completed` |
| Immutable seeds | do not rewrite `CAMPAIGN_SOURCE.yaml` bytes |
| Compiler | archived ids are not live allowlist entries; compile is fixture-only from this path |

Do not activate, compile-as-live, or open new PRs from an archived seed.
