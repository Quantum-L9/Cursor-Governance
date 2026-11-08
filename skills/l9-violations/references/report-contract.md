# Report contract

Every brief uses these fields. The index row carries the same id, status, severity, type, and date.

| Field | What it holds |
|---|---|
| Type | `skill_bypass`, `unauthorized_deletion`, `unauthorized_merge`, `unauthorized_production_change`, `unauthorized_infrastructure_change`, `falsified_evidence`, `hidden_finding`, `speculate_without_reading`, `unauthorized_move`, `restored_user_deletion`, `invented_capability`, `parallel_implementation`, `rewrite_instead_of_copy`, `unauthorized_push`, `existing_code_overwritten`, `rule_defect` |
| Severity | `critical`, `high`, or `medium` |
| Location | Workspace, branch, file, or command. `unknown` when the source does not name one. |
| Description | What the agent did. |
| Evidence | The command, commit, path, or quoted source. No secrets. |
| Required action | The next concrete action. |
| Prevention | The control that would have stopped it. |
| Provenance | The historical file this brief was taken from. |

Status is `open`, `acknowledged`, or `addressed`.

A new brief is appended under `records/` and indexed in `records/register.yaml`. Nothing else is a store.
