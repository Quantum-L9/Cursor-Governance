<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: stage-contract
version: 1.0.0
status: active
-->

# Topology Scan (`SCAN_SKILL_TOPOLOGY`)

Runs at workflow step 4, before Gate C, whenever a request would create a new
pack. Creation is never the default outcome: the scan reads every live skill
and decides whether the capability already has an owner.

## Invocation

```bash
python scripts/scan_skill_topology.py request.json [skills_dir]
```

`skills_dir` defaults to the `skills/` directory of the repository that holds
this pack. Pass it explicitly when the pack is installed outside a repository.
Directories whose names start with `_` or `.` (archived or hidden packs) are not
live and are never candidates.

## Input

`request.json` is a JSON object with one `subject` mapping:

| Field | Type | Meaning |
|---|---|---|
| `proposed_name` | string | name the new pack would take |
| `domain` | string | capability area in a few words |
| `stated_objective` | string | what the requester wants the pack to do |
| `existing_skill` | string, optional | a live pack this request rebuilds |

Every field is optional, but a subject with no words cannot match an owner, so
supply at least `proposed_name` and `stated_objective`.

```json
{
  "subject": {
    "proposed_name": "l9-release-notes",
    "domain": "release documentation",
    "stated_objective": "draft release notes from merged pull requests"
  }
}
```

## Output

One JSON document on stdout, exit code `0`:

| Field | Meaning |
|---|---|
| `stage` | always `SCAN_SKILL_TOPOLOGY` |
| `decision` | one of the decisions below |
| `decided_by` | `deterministic_rule` or `bounded_llm` |
| `evidence` | the facts the decision rests on |
| `candidates` | up to ten live skills ranked by capability overlap, then specificity, then trigger overlap |

A missing or malformed request exits `2` with the reason on stderr and no
decision.

## Decisions

| Decision | Rule | Required action |
|---|---|---|
| `REPLACE_EXISTING` | `existing_skill` names a live pack | rebuild that pack in place |
| `REJECT_NEW_SKILL` | the subject wraps a DAG without claiming DAG lifecycle work, and a live `dag_lifecycle_owner` exists (`policies/topology-ownership.yaml`) | do not create; the owning capability references the DAG |
| `EXTEND_EXISTING` | the top candidate shares at least two capability tokens | extend that skill instead |
| `CREATE_NEW` | no candidate overlaps, or the overlap is trigger words only | a new pack is permitted |
| `ESCALATE_TO_BOUNDED_LLM` | several partial owners, weak overlap, or a DAG-shaped subject with no live owner | record a judgment over `candidates` before Gate C; do not default to creation |

Tokens every live skill shares (such as the `l9` prefix) are removed before
scoring, because they prove no ownership.
