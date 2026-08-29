# Campaign: l9-agent-doc-plane

Registration of the **Continuous Agent Doc Plane** program in the governance
SSOT. Compiles through Program Execution v2 from a minimal intent, a bound
intent-resolution, and this campaign source.

| Artifact | Schema / role |
|---|---|
| `INTENT.yaml` | `program-execution.intent.v1` — goal-level user input |
| `INTENT_RESOLUTION.yaml` | `program-execution.intent-resolution.v1` — derived requirements, decisions, unknowns |
| `CAMPAIGN_SOURCE.yaml` | `l9.program-execution.campaign-source.v2` — immutable operator-intent seed |
| `AGENT_INITIATION.md` | Launch mechanics only (activation prompt) |
| `source-integrity-receipt.json` | sha256 bind of `CAMPAIGN_SOURCE.yaml` |

Human mission card (not immutable PE source):
`~/.cursor/plans/rich_root_agent_docs_557cc65b.plan.md`

## What this campaign builds

1. **Ingress** — `l9-update-agent-docs` creates missing quartet + Core-10 + consumer `CANONICAL_LAW`.
2. **Birth seed** — apply that library on `Quantum-L9/l9-repo-template` and inventory-gate it.
3. **Continuous plane** — deterministic `extract_doc_facts.py` + managed fact blocks healed by `sync_generated_artifacts.py` / `make pr`. Authored prose is never auto-rewritten.

## Status

`operator_intake` / `definition_status: draft`. This registration is the compile
input. No Blueprint pair, Program Lock, or controller runtime is committed here.
Runtime lives under `$HOME/.l9/programs/l9-agent-doc-plane`.

## Location

This campaign is a peer of the other four under
`environment/program-execution/campaigns/`:

```text
environment/program-execution/campaigns/l9-agent-doc-plane/
  CAMPAIGN_SOURCE.yaml
  INTENT.yaml
  INTENT_RESOLUTION.yaml
  AGENT_INITIATION.md
  README.md
  source-integrity-receipt.json
```

Registered in `COMPILE_ALLOWLIST.yaml` and `CAMPAIGN_EXECUTION_POLICY.yaml`.
Integration branch: `campaign/l9-agent-doc-plane`.

## Execute

Paste `AGENT_INITIATION.md` into a new agent session on a **clean** worktree
from `origin/main`. Do not mix with unrelated WIP.

_Terminal verdict is reserved to AUTH-001._
