# Dags

**Path:** `workflows/dags` | **Kind:** subsystem

## Modules

### `__init__.py`

Workflow Graphs — Discovery Boundary

Exports: `DAG_AUTHORING_DAG`, `GMP_EXECUTION_DAG`, `HARVEST_DEPLOY_DAG`, `INSPECT_DAG`, `INTELLIGENCE_HARVEST_V1`, `InspectState`, `PLAN_SIMPLE_BUILD_DAG`, `PR_TRAIN_DAG`, `PrTrainState`, `README_PIPELINE_DAG`, `REFACTORING_DAG`, `SLASH_COMMAND_UPDATE_DAG` (+6 more)

### `dag_authoring_dag.py`

DAG Authoring Graph — the graph lifecycle, encoded

- `def register()` — Register the DAG authoring graph (SESSION_GUIDANCE).

### `gmp_execution_dag.py`

GMP Execution DAG — Enforced Step Ordering

- `def get_gmp_execution_dag() -> SessionDAG` — Get the GMP execution DAG.

### `gmp_langgraph_executor.py`

GMP LangGraph Executor — Backwards Compatibility Shim

Exports: `GMPLangGraphExecutor`, `GMPPhase`, `GMPState`, `build_gmp_graph`, `main`, `node_aborted`, `node_baseline`, `node_end`, `node_finalize`, `node_implement`, `node_memory_read`, `node_memory_write` (+7 more)

### `harvest_deploy_dag.py`

Harvest-Deploy Session DAG

- `def get_harvest_deploy_dag() -> SessionDAG` — Get the harvest-deploy DAG.

### `inspect_dag.py`

Inspect DAG — Real LangGraph Implementation

- `InspectState` — State flowing through inspect graph.
- `def validators_available() -> bool` — True when the external-code validators are importable in this checkout.
- `async def classify_node(state) -> dict[str, Any]` — Classify target into type and tier. Detect external code.
- `async def orient_node(state) -> dict[str, Any]` — 30-second understanding of what this does.
- `async def structure_node(state) -> dict[str, Any]` — Map structure: parse AST for classes, functions, imports.
- `async def compliance_node(state) -> dict[str, Any]` — Check L9 canon compliance using real validators.
- `async def impact_node(state) -> dict[str, Any]` — Calculate impact score.
- `async def routing_node(state) -> dict[str, Any]` — Decide next command.
- _+3 more public symbol(s)_

### `intelligence_harvest_dag.py`

Intelligence Harvest DAG - donor-to-beneficiary semantic mining (Enforced)

### `plan_simple_build_dag.py`

Plan-Simple → Improve → Validate & Repair → Build/GMP

### `pr_train_dag.py`

PR-train LangGraph — open stacked PRs, halt for remediator, then /ff.

- `NovelCommit`
- `ExtractEmpty` — Slice produced no new commit on the tip. Skip to the next car; do not halt the train.
- `PrTrainState`
- `def campaign_halt(branch, override) -> str | None`
- `def generated_prefix(path) -> str | None`
- `def shares_generated_clobber(left, right) -> bool` — Whole-file generated corpora clobber on MERGE_TRAIN if split across PRs.
- `def is_empty_cherry_pick(stdout, stderr) -> bool` — Already-landed patch. ``cherry-pick --skip`` is not conflict resolution.
- `def parse_merge_tree_name_only(stdout, returncode) -> list[str] | None` — Same contract as ``pr_overlap_check.probe_ref_conflicts``: [] / paths / None.
- _+44 more public symbol(s)_

### `readme_pipeline_dag.py`

README Pipeline Session DAG

- `def register()` — Register the README pipeline DAG.

### `refactoring_dag.py`

Refactoring Session DAG

- `def get_refactoring_dag() -> SessionDAG` — Get the refactoring DAG.

### `slash_command_update_dag.py`

Slash Command Update DAG — Update Commands as Minimal Triggers

- `def register()` — Register the slash command update DAG.

_+1 further module(s) in this directory._

## Dependencies

**External:** `langgraph`, `pydantic`, `structlog`, `workflows`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
