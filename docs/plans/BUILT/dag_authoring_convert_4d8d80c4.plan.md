---
name: DAG authoring CONVERT
overview: "Add CONVERT to l9-dag-authoring: classify every SessionDAG, emit a StateGraph only for intelligence-harvest-v1, leave SessionDAG deletion to a follow-on plan."
todos:
  - id: T01
    content: Reverify HEAD; stop if write_allow paths are dirty with foreign bytes
    status: completed
  - id: T02
    content: Add session-deprecation.yaml with the ten catalog rows, each carrying source_path and proof_path
    status: completed
  - id: T03
    content: Add session-to-langgraph-contract.md (classify first; emit only CONVERT_TO_LANGGRAPH; never register; never delete in the same step)
    status: completed
  - id: T04
    content: Extend request and receipt schemas to CONVERT v2.2.0 with disposition fields; allow_session_retire default false
    status: completed
  - id: T05
    content: Add CONVERT to lifecycle and ownership policies; mark SESSION_GUIDANCE deprecated_pending_convert only in graph-kinds.yaml
    status: completed
  - id: T06
    content: Update validate_request.py and render_receipt.py; CONVERT requires dag_id or dag_path; refuse allow_session_retire true
    status: completed
  - id: T07
    content: Add classify_conversion_disposition.py; source must be SESSION_GUIDANCE; unknown id BLOCKED; prove survivor or skill path
    status: completed
  - id: T08
    content: Add convert_session_to_langgraph.py; refuse any disposition other than CONVERT_TO_LANGGRAPH; prose action fails closed
    status: completed
  - id: T09
    content: Add fixtures and pack tests for twin, absorb, convert, unknown id, LangGraph source, and prose-action refuse
    status: completed
  - id: T10
    content: Add CONVERT to SKILL.md and /dag-authoring --convert; keep the command under 80 lines; mention CONVERT on the commands-index dag-authoring row
    status: completed
  - id: T11
    content: Dry-run the classifier on every catalog id; CONVERT_TO_LANGGRAPH count must equal 1 or stop
    status: completed
  - id: T12
    content: Emit workflows/dags/intelligence_harvest/ from the IR node set; add test_intelligence_harvest_langgraph.py
    status: completed
  - id: T13
    content: Point harvest SKILL.md and skill-ir authority.canonical_dag at the new graph.py; keep dag_registry_id and the SessionDAG adapter
    status: completed
  - id: T14
    content: Run pack tests plus OPEN_PR=0 make pr; prove get_session_dag intelligence-harvest-v1 still resolves; do not push
    status: completed
isProject: false
kernel_pass:
  bound_path: dag_authoring_convert_4d8d80c4.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T01:26:00Z
    body_sha256: "2e4718fd1e5410f6f4bf766b7fce52a4a50bcae45f2f09d3d8154a281ba3faba"
    deltas:
      - "Parked this leftover CONVERT plan so unique commits can ride pr-train without a new planning pass"
      - "Kept CONVERT as classify-then-emit; SessionDAG deletion stays a follow-on"
      - "Did not mix this plan onto ssot main; extract cherry-picks only"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T01:26:30Z
    body_sha256: "2e4718fd1e5410f6f4bf766b7fce52a4a50bcae45f2f09d3d8154a281ba3faba"
    deltas:
      - "Todos T01-T14 already completed in the source commits; this file is the receipt not a new Build"
      - "No make campaign and no Program Lock from this parked plan"
      - "kernel_pass stamped so precommit plan-gate can pass the extract"
---

# PLAN: Add CONVERT to l9-dag-authoring

## Execute via Cursor Build

Press **Build**. Work in the **current checkout**.

This pass is the skill pack only: T02 through T10. Do not start T12 until T11 reports convert-count 1.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.

## Objective

`l9-dag-authoring` owns graph lifecycle. Markdown surfaces now list CONVERT. Machine ops still need the catalog, schemas, and scripts. [`policies/graph-kinds.yaml`](skills/l9-dag-authoring/policies/graph-kinds.yaml) treats `SESSION_GUIDANCE` and `LANGGRAPH_RUNTIME` as peers.

Add **CONVERT**: a disposition gate, then one of three exits. It is not a rewrite of every SessionDAG into a `StateGraph`. SessionDAG file deletion is a follow-on plan after receipts exist.

```mermaid
flowchart TD
  request[CONVERT_request]
  kind[classify_graph_kind]
  sessionGate[SESSION_GUIDANCE_only]
  catalog[session-deprecation.yaml]
  twin[DELETE_TWIN]
  absorb[ABSORB_INTO_SKILL]
  convert[CONVERT_TO_LANGGRAPH]
  emit[emit_StateGraph]
  stop[receipt_no_emit]
  blocked[BLOCKED]
  request --> kind
  kind --> sessionGate
  kind --> blocked
  sessionGate --> catalog
  catalog --> twin
  catalog --> absorb
  catalog --> convert
  catalog --> blocked
  twin --> stop
  absorb --> stop
  convert --> emit
```

## Exclusive envelope

write_allow:

- `skills/l9-dag-authoring/policies/session-deprecation.yaml`
- `skills/l9-dag-authoring/policies/dag-lifecycle.yaml`
- `skills/l9-dag-authoring/policies/graph-kinds.yaml`
- `skills/l9-dag-authoring/policies/ownership-boundary.yaml`
- `skills/l9-dag-authoring/references/session-to-langgraph-contract.md`
- `skills/l9-dag-authoring/references/dag-lifecycle-contract.md`
- `skills/l9-dag-authoring/contracts/dag-authoring-request.schema.json`
- `skills/l9-dag-authoring/contracts/dag-authoring-receipt.schema.json`
- `skills/l9-dag-authoring/scripts/validate_request.py`
- `skills/l9-dag-authoring/scripts/render_receipt.py`
- `skills/l9-dag-authoring/scripts/self_test.py`
- `skills/l9-dag-authoring/scripts/classify_conversion_disposition.py`
- `skills/l9-dag-authoring/scripts/convert_session_to_langgraph.py`
- `skills/l9-dag-authoring/fixtures/convert_delete_twin.json`
- `skills/l9-dag-authoring/fixtures/convert_absorb.json`
- `skills/l9-dag-authoring/fixtures/convert_langgraph.json`
- `skills/l9-dag-authoring/fixtures/convert_unknown.json`
- `skills/l9-dag-authoring/fixtures/convert_langgraph_source.py`
- `skills/l9-dag-authoring/fixtures/convert_prose_action.py`
- `skills/l9-dag-authoring/tests/test_skill.py`
- `skills/l9-dag-authoring/SKILL.md`
- `skills/l9-dag-authoring/agents/meta.yaml`
- `commands/dag-authoring.md`
- `commands/commands-index.md`
- `skills/l9-intelligence-harvest/SKILL.md`
- `skills/l9-intelligence-harvest/meta/skill-ir.json`
- `workflows/dags/intelligence_harvest/__init__.py`
- `workflows/dags/intelligence_harvest/state.py`
- `workflows/dags/intelligence_harvest/nodes.py`
- `workflows/dags/intelligence_harvest/routing.py`
- `workflows/dags/intelligence_harvest/graph.py`
- `workflows/dags/intelligence_harvest/executor.py`
- `tests/workflows/test_intelligence_harvest_langgraph.py`

write_deny:

- `workflows/dags/dag_authoring_dag.py`
- `workflows/dags/gmp_execution_dag.py`
- `workflows/dags/harvest_deploy_dag.py`
- `workflows/dags/slash_command_update_dag.py`
- `workflows/dags/readme_pipeline_dag.py`
- `workflows/dags/refactoring_dag.py`
- `workflows/dags/wire_dag.py`
- `workflows/dags/test_pipeline_dag.py`
- `workflows/dags/intelligence_harvest_dag.py`
- `workflows/dags/__init__.py`
- `workflows/__init__.py`
- `workflows/README.md`
- `workflows/session/interface.py`
- `workflows/session/registry.py`
- `tests/workflows/test_dags_discovery_boundary.py`
- `tests/workflows/test_intelligence_harvest_dag.py`
- `Makefile`
- `AGENTS.md`
- `CLAUDE.md`
- `CANONICAL_LAW.md`
- `pyproject.toml`
- `docs/plans/plan_skills_precommit_catalog_9e2b4c71.plan.md`
- `docs/plans/plan_skills_precommit_catalog_9e2b4c71.plan.json`

Overlap policy: `stop_if_dirty_overlaps_may_modify`. Pathspec commits only. Do not push.

## Catalog

Lock these rows in [`session-deprecation.yaml`](skills/l9-dag-authoring/policies/session-deprecation.yaml). Every row needs `dag_id`, `source_path`, `disposition`, `domain_owner`, `proof_path`. Missing `proof_path` on a DELETE_TWIN or ABSORB_INTO_SKILL row is BLOCKED, not convert.

| dag_id | disposition | source_path | proof_path |
|---|---|---|---|
| `gmp-execution-v1` | DELETE_TWIN | `workflows/dags/gmp_execution_dag.py` | `workflows/dags/gmp/graph.py` |
| `harvest-deploy-v1` | DELETE_TWIN | `workflows/dags/harvest_deploy_dag.py` | `workflows/harvest_deploy.py` |
| `slash-command-update-v1` | DELETE_TWIN | `workflows/dags/slash_command_update_dag.py` | `skills/l9-dag-authoring/SKILL.md` COMMAND_BIND |
| `skill-compiler-v2` | DELETE_TWIN | none | `skills/l9-skill-compiler/SKILL.md` supersedes line |
| `readme-pipeline-v1` | ABSORB_INTO_SKILL | `workflows/dags/readme_pipeline_dag.py` | `skills/l9-update-agent-docs/SKILL.md` |
| `refactoring-v1` | ABSORB_INTO_SKILL | `workflows/dags/refactoring_dag.py` | `skills/l9-code-maintenance/SKILL.md` |
| `wire-v1` | ABSORB_INTO_SKILL | `workflows/dags/wire_dag.py` | `skills/l9-governance-wiring/references/wire-executor.md` |
| `test-pipeline-v1` | ABSORB_INTO_SKILL | `workflows/dags/test_pipeline_dag.py` | `skills/l9-code-maintenance/SKILL.md` |
| `dag-authoring-v1` | ABSORB_INTO_SKILL | `workflows/dags/dag_authoring_dag.py` | `skills/l9-dag-authoring/SKILL.md` |
| `intelligence-harvest-v1` | CONVERT_TO_LANGGRAPH | `workflows/dags/intelligence_harvest_dag.py` | `skills/l9-intelligence-harvest/meta/skill-ir.json` |

Unknown id → BLOCKED. A `LANGGRAPH_RUNTIME` source → BLOCKED. Dry-run `CONVERT_TO_LANGGRAPH` count must be **1** before T12.

## CONVERT contracts

Request: `operation: CONVERT` requires `dag_id` or `dag_path`. `allow_session_retire` defaults false and is refused when true.

Classifier: run [`classify_graph_kind.py`](skills/l9-dag-authoring/scripts/classify_graph_kind.py) first. Continue only on `SESSION_GUIDANCE`. Look up the catalog. DELETE_TWIN requires `proof_path` to exist. ABSORB_INTO_SKILL requires the skill `SKILL.md` to exist. CONVERT_TO_LANGGRAPH requires `domain_owner` and fails if a twin `StateGraph` already exists for that id.

Emitter: run only after classifier returns `CONVERT_TO_LANGGRAPH`. Copy the modular shape of [`workflows/dags/gmp/`](workflows/dags/gmp/). Map IR / SessionNode ids to `add_node`. An `action` that is an existing repo script becomes a node callable. A prose `action` fails closed. Conditional edges become `add_conditional_edges`. No `register_session_dag`. Then [`validate_langgraph_source.py`](skills/l9-dag-authoring/scripts/validate_langgraph_source.py) must PASS.

IR node ids that must appear on `build_intelligence_harvest_graph()`: BIND_REQUEST, PROBE_CAPABILITIES, LOCK_SOURCE_IDENTITY, INVENTORY_DONOR, RECONSTRUCT_SYSTEM, TRACE_SURFACES, DETECT_DUPLICATION_DRIFT, EXTRACT_CONCEPT_CANDIDATES, QUALIFY_NUGGETS, COMPARE_BENEFICIARY, DISPOSITION_CONCEPTS, DERIVE_ACCEPTANCE_TESTS, RANK_NUGGETS, SAFETY_PORTABILITY_AUDIT, EVIDENCE_CLOSURE, RENDER_OUTPUT, PASS, PARTIAL, BLOCKED, FAIL.

Bounded-LLM nodes record `UNKNOWN` or terminal `BLOCKED`. They do not fabricate harvest.json fields.

`canonical_dag_registration` stays a SessionDAG-adapter obligation on [`intelligence_harvest_dag.py`](workflows/dags/intelligence_harvest_dag.py). The emitted package must not implement registration. T13 changes `authority.canonical_dag` to `workflows/dags/intelligence_harvest/graph.py` and leaves `dag_registry_id: intelligence-harvest-v1`.

`deprecated_pending_convert` lives only in [`graph-kinds.yaml`](skills/l9-dag-authoring/policies/graph-kinds.yaml). Do not put legacy-generation or fake wording in [`workflows/dags/__init__.py`](workflows/dags/__init__.py), [`workflows/__init__.py`](workflows/__init__.py), or [`workflows/README.md`](workflows/README.md). [`test_dag_authoring_alignment.py`](tests/workflows/test_dag_authoring_alignment.py) pins that wording.

Do not edit [`test_dags_discovery_boundary.py`](tests/workflows/test_dags_discovery_boundary.py). The `skill-compiler-v2` registry assertion stays until the follow-on.

## Hard stops

- Do not emit a StateGraph for absorb or twin rows.
- Do not delete any SessionDAG module.
- Do not add CONVERT nodes to [`dag_authoring_dag.py`](workflows/dags/dag_authoring_dag.py).
- Do not flip `allow_session_retire`.
- T12 is forbidden until T11 reports convert-count 1.

## Proof

```bash
python3 skills/l9-dag-authoring/scripts/self_test.py
python3 -m pytest skills/l9-dag-authoring/tests/test_skill.py \
  tests/workflows/test_dag_authoring_alignment.py \
  tests/workflows/test_intelligence_harvest_dag.py \
  tests/workflows/test_intelligence_harvest_langgraph.py
python3 skills/l9-dag-authoring/scripts/validate_langgraph_source.py \
  workflows/dags/intelligence_harvest/graph.py
OPEN_PR=0 make pr
```

`get_session_dag("intelligence-harvest-v1")` must still resolve. Do not push.

## Follow-on (not this Build)

Delete twin SessionDAGs, fold absorb-row text into the named skills, drop the stale `skill-compiler-v2` registry assertion, then retire `workflows/session/` and `dag_authoring_dag.py`. That unification wave is a separate plan. CONVERT is the machine that makes it legal.

## Rollback

`git restore --staged --worktree --` the write_allow paths. Delete only files this Build created under `workflows/dags/intelligence_harvest/`. Do not revert foreign commits on `feat/pr-check-folded`.
