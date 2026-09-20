# Dags

**Path:** `workflows/dags` | **Tier:** discovered

## Purpose

Workflow Graphs — Discovery Boundary



## Components

### `InspectState`

State flowing through inspect graph.

- File: `workflows/dags/inspect_dag.py` (L67–126)
- Methods: _none_

### `NovelCommit`

No description

- File: `workflows/dags/pr_train_dag.py` (L74–77)
- Methods: _none_

### `ExtractEmpty`

Slice produced no new commit on the tip. Skip to the next car; do not halt the train.

- File: `workflows/dags/pr_train_dag.py` (L108–109)
- Methods: _none_

### `PrTrainState`

No description

- File: `workflows/dags/pr_train_dag.py` (L439–485)
- Methods: _none_

## Functions

- `def register()` — Register the DAG authoring graph (SESSION_GUIDANCE).
- `def get_gmp_execution_dag() -> SessionDAG` — Get the GMP execution DAG.
- `def get_harvest_deploy_dag() -> SessionDAG` — Get the harvest-deploy DAG.
- `def validators_available() -> bool` — True when the external-code validators are importable in this checkout.
- `async def classify_node(state) -> dict[str, Any]` — Classify target into type and tier. Detect external code.
- `async def orient_node(state) -> dict[str, Any]` — 30-second understanding of what this does.
- `async def structure_node(state) -> dict[str, Any]` — Map structure: parse AST for classes, functions, imports.
- `async def compliance_node(state) -> dict[str, Any]` — Check L9 canon compliance using real validators.
- `async def impact_node(state) -> dict[str, Any]` — Calculate impact score.
- `async def routing_node(state) -> dict[str, Any]` — Decide next command.
- `async def report_node(state) -> dict[str, Any]` — Generate final report.
- `def build_inspect_graph() -> StateGraph` — Build and compile the inspect graph.
- `async def run_inspect(target) -> InspectState` — Execute inspect graph on target.
- `def campaign_halt(branch, override) -> str | None`
- `def generated_prefix(path) -> str | None`
- `def shares_generated_clobber(left, right) -> bool` — Whole-file generated corpora clobber on MERGE_TRAIN if split across PRs.
- `def is_empty_cherry_pick(stdout, stderr) -> bool` — Already-landed patch. ``cherry-pick --skip`` is not conflict resolution.
- `def parse_merge_tree_name_only(stdout, returncode) -> list[str] | None` — Same contract as ``pr_overlap_check.probe_ref_conflicts``: [] / paths / None.
- `def is_git_repo(repo) -> bool`
- `def sha_is_commit(repo, sha) -> bool`

## Exports

`DAG_AUTHORING_DAG`, `GMPLangGraphExecutor`, `GMPPhase`, `GMPState`, `GMP_EXECUTION_DAG`, `HARVEST_DEPLOY_DAG`, `INSPECT_DAG`, `INTELLIGENCE_HARVEST_V1`, `InspectState`, `PLAN_SIMPLE_BUILD_DAG`, `PR_TRAIN_DAG`, `PrTrainState`, `README_PIPELINE_DAG`, `REFACTORING_DAG`, `SLASH_COMMAND_UPDATE_DAG`, `TEST_PIPELINE_DAG`, `WIRE_DAG`, `build_gmp_graph`, `build_inspect_graph`, `build_pr_train_graph` (+17 more)

## Dependencies

`__future__`, `argparse`, `ast`, `collections.abc`, `dataclasses`, `importlib.util`, `json`, `langgraph.graph`, `os`, `pathlib`, `pydantic`, `structlog`, `subprocess`, `sys`, `time`, `typing`, `workflows.dags.dag_authoring_dag`, `workflows.dags.gmp`, `workflows.dags.gmp.nodes`, `workflows.dags.gmp.routing`, `workflows.dags.gmp_execution_dag`, `workflows.dags.harvest_deploy_dag`, `workflows.dags.inspect_dag`, `workflows.dags.intelligence_harvest_dag`

<!-- l9-module-readme: generated-from-ast -->
