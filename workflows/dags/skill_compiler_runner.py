"""Reusable programmatic invocation interface for the ``skill-compiler-v2`` DAG.

Before this module existed the compiler graph was declarative only: every
caller had to reproduce the stage order by hand. That is exactly the parallel
orchestration the compiler forbids, so the runner derives *everything* from the
canonical graph in :mod:`workflows.dags.skill_compiler_dag`:

* execution order comes from a topological sort of the declared edges;
* each stage's argv comes from that node's ``args`` token list;
* guard entry comes from the node's machine-evaluable ``guard_when``;
* terminal state comes from the graph's ``TERMINAL_STATES`` table.

The runner holds no per-stage knowledge and no second stage list. Adding,
removing, or reordering a node in the DAG changes this runner's behavior with
no edit here.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import types
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

CANONICAL_DAG_MODULE = "workflows.dags.skill_compiler_dag"
CANONICAL_DAG_PATH = "workflows/dags/skill_compiler_dag.py"

# Tokens whose absence simply truncates a stage's argv, because they name an
# optional *output* path. Every input token is mandatory: a stage script that
# silently falls back to its own defaults would validate the wrong pack, so an
# unresolved input halts the run instead.
OPTIONAL_TOKENS = frozenset({"ir_out", "render_outdir"})


def repo_root() -> Path:
    """Repository root, derived from this file's location inside ``workflows/``."""
    return Path(__file__).resolve().parent.parent.parent


def load_canonical_dag():
    """Return ``(module, source, degradation)`` for the canonical compiler DAG.

    The canonical path is a normal package import. Cursor-Governance's
    ``workflows`` package eagerly imports every sibling DAG, so one unrelated
    broken sibling would otherwise make the compiler uninvocable. When that
    happens the runner loads the *same canonical file* through a stub package
    binding and reports the degradation instead of hiding it. There is still
    exactly one graph.
    """
    try:
        return importlib.import_module(CANONICAL_DAG_MODULE), "package_import", None
    except ImportError as exc:
        root = repo_root()
        for name in ("workflows", "workflows.dags"):
            if name not in sys.modules or not hasattr(sys.modules[name], "__path__"):
                stub = types.ModuleType(name)
                stub.__path__ = [str(root.joinpath(*name.split(".")))]
                sys.modules[name] = stub
        module = importlib.import_module(CANONICAL_DAG_MODULE)
        degradation = {
            "id": "canonical_package_import_unavailable",
            "detail": str(exc),
            "resolution": (
                "loaded the identical canonical file "
                + CANONICAL_DAG_PATH
                + " directly; the graph is unchanged"
            ),
        }
        return module, "canonical_file_direct", degradation


def reachable(nodes, entrypoint):
    """Node ids reachable from ``entrypoint`` along declared edges."""
    index = {node["id"]: node for node in nodes}
    seen, stack = set(), [entrypoint] if entrypoint in index else []
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(index[current].get("next", []))
    return seen


def execution_order(nodes, entrypoint):
    """Topological order of the reachable subgraph, derived from edges alone."""
    live = reachable(nodes, entrypoint)
    index = {node["id"]: node for node in nodes if node["id"] in live}
    indegree = {node_id: 0 for node_id in index}
    for node in index.values():
        for target in node.get("next", []):
            if target in indegree:
                indegree[target] += 1
    queue = deque(sorted(node_id for node_id, count in indegree.items() if count == 0))
    order = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for target in index[current].get("next", []):
            if target not in indegree:
                continue
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
        queue = deque(sorted(queue))
    if len(order) != len(index):
        raise ValueError("skill-compiler-v2 graph is not acyclic over reachable nodes")
    return order


@dataclass
class RunContext:
    """Values a runner resolves the DAG's symbolic ``args`` tokens against."""

    request: str | None = None
    ir: str | None = None
    ir_out: str | None = None
    render_outdir: str | None = None
    pack: str | None = None
    skills_dir: str | None = None
    repo_root: str | None = None
    target_profiles: list[str] = field(default_factory=list)
    dry_run: bool = False
    # Nodes the caller deliberately declined to execute. A declined node is
    # never a passing node: the run can only terminate BLOCKED.
    skip_nodes: list[str] = field(default_factory=list)

    def resolve(self, token, profile=None):
        if token == "profile":
            return profile
        return getattr(self, token, None)


@dataclass
class StageRecord:
    node: str
    kind: str
    status: str
    exec_path: str | None = None
    command: list[str] | None = None
    exit_code: int | None = None
    output: object | None = None
    detail: str | None = None


@dataclass
class RunResult:
    dag_id: str
    dag_version: str
    dag_source: str
    planned_order: list[str]
    stages: list[StageRecord] = field(default_factory=list)
    terminal_state: str = "FAIL"
    status: str = "FAIL"
    build_succeeded: bool = False
    topology_decision: object | None = None
    skill_profile: object | None = None
    artifacts: list[str] = field(default_factory=list)
    pending_bounded_llm: list[dict] = field(default_factory=list)
    unknowns: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def as_dict(self):
        return {
            "dag": {
                "id": self.dag_id,
                "version": self.dag_version,
                "source": self.dag_source,
                "planned_order": self.planned_order,
                "terminal_state": self.terminal_state,
            },
            "status": self.status,
            "build_succeeded": self.build_succeeded,
            "topology_decision": self.topology_decision,
            "skill_profile": self.skill_profile,
            "stages": [vars(record) for record in self.stages],
            "artifacts": self.artifacts,
            "pending_bounded_llm": self.pending_bounded_llm,
            "unknowns": self.unknowns,
            "errors": self.errors,
        }


def _guard_satisfied(node, stage_outputs):
    guard = node.get("guard_when")
    if not guard:
        return True
    output = stage_outputs.get(guard["stage"])
    if not isinstance(output, dict):
        return False
    return output.get(guard["field"]) == guard["equals"]


def _stage_commands(node, context, python):
    """Argv list(s) for a node, built purely from its declared ``args`` tokens."""
    profiles = context.target_profiles if node.get("fan_out") == "profile" else [None]
    commands = []
    for profile in profiles or [None]:
        argv = [python, str(Path(context.repo_root or repo_root()) / node["exec"])]
        for token in node.get("args", []):
            value = context.resolve(token, profile=profile)
            if value is None:
                if token in OPTIONAL_TOKENS:
                    break
                return None, "unresolved required stage input: " + token
            argv.append(str(value))
        commands.append(argv)
    return commands, None


def _parse(stdout):
    try:
        return json.loads(stdout)
    except (ValueError, TypeError):
        return None


def run(context, python=None, dag=None):
    """Execute the canonical DAG over ``context`` and return a :class:`RunResult`."""
    python = python or sys.executable
    if dag is None:
        dag, source, degradation = load_canonical_dag()
    else:
        source, degradation = "injected", None

    spec = dag.SKILL_COMPILER_V2
    index = {node["id"]: node for node in dag.NODES}
    order = execution_order(dag.NODES, spec["entrypoint"])
    result = RunResult(
        dag_id=spec["id"],
        dag_version=spec["version"],
        dag_source=source,
        planned_order=order,
    )
    if degradation:
        result.unknowns.append(degradation)

    graph_errors = dag.validate_graph()
    if graph_errors:
        result.terminal_state = "FAIL"
        result.status = "FAIL"
        result.errors.append({"code": "DAG_EXECUTION_FAILED", "detail": graph_errors})
        return result

    stage_outputs = {}
    terminal_state = None
    caller_skipped = False

    for node_id in order:
        node = index[node_id]
        if not _guard_satisfied(node, stage_outputs):
            result.stages.append(
                StageRecord(node=node_id, kind=node["kind"], status="skipped_guard_not_met")
            )
            continue

        if node_id in context.skip_nodes:
            result.stages.append(
                StageRecord(node=node_id, kind=node["kind"], status="skipped_by_caller")
            )
            caller_skipped = True
            continue

        if node["kind"] == "terminal":
            result.stages.append(StageRecord(node=node_id, kind="terminal", status="reached"))
            continue

        if node["kind"] == "bounded_llm":
            satisfied_by = node.get("satisfied_by")
            if satisfied_by and context.resolve(satisfied_by) is not None:
                result.stages.append(
                    StageRecord(
                        node=node_id,
                        kind="bounded_llm",
                        status="satisfied_by_supplied_artifact",
                        detail=satisfied_by,
                    )
                )
                continue
            pending = {
                "node": node_id,
                "impl": node.get("impl"),
                "contract": node.get("contract"),
                "satisfied_by": satisfied_by,
            }
            result.pending_bounded_llm.append(pending)
            result.stages.append(
                StageRecord(
                    node=node_id,
                    kind="bounded_llm",
                    status="requires_bounded_llm",
                    detail=node.get("contract"),
                )
            )
            terminal_state = "BOUNDED_LLM_REQUIRED"
            break

        if not node.get("exec"):
            result.stages.append(
                StageRecord(node=node_id, kind=node["kind"], status="no_executable_declared")
            )
            continue

        if context.dry_run and node.get("writes"):
            result.stages.append(
                StageRecord(
                    node=node_id,
                    kind=node["kind"],
                    status="skipped_dry_run_would_write",
                    exec_path=node["exec"],
                )
            )
            continue

        commands, problem = _stage_commands(node, context, python)
        if problem:
            result.stages.append(
                StageRecord(
                    node=node_id, kind=node["kind"], status="unresolved_input", detail=problem
                )
            )
            result.errors.append(
                {"code": "DAG_EXECUTION_FAILED", "node": node_id, "detail": problem}
            )
            terminal_state = "FAIL"
            break

        stage_failed = False
        for argv in commands:
            completed = subprocess.run(argv, capture_output=True, text=True, check=False)
            payload = _parse(completed.stdout)
            record = StageRecord(
                node=node_id,
                kind=node["kind"],
                status="pass" if completed.returncode == 0 else "fail",
                exec_path=node["exec"],
                command=argv,
                exit_code=completed.returncode,
                output=payload,
                detail=None
                if completed.returncode == 0
                else (completed.stderr or "").strip() or None,
            )
            result.stages.append(record)
            if payload is not None:
                stage_outputs[node_id] = payload
            if completed.returncode != 0:
                result.errors.append(
                    {
                        "code": "DAG_EXECUTION_FAILED",
                        "node": node_id,
                        "exit_code": completed.returncode,
                        "detail": payload if payload is not None else record.detail,
                    }
                )
                stage_failed = True
                break

        if node_id == "SCAN_SKILL_TOPOLOGY" and node_id in stage_outputs:
            result.topology_decision = stage_outputs[node_id]
        if node_id == "CLASSIFY_SKILL_PROFILE" and node_id in stage_outputs:
            result.skill_profile = stage_outputs[node_id]

        if stage_failed:
            terminal_state = "FAIL"
            break

    if terminal_state is None:
        if context.dry_run:
            terminal_state = "DRY_RUN"
        elif caller_skipped:
            terminal_state = "BLOCKED"
        else:
            terminal_state = "PASS"
    if context.dry_run and terminal_state not in ("FAIL",):
        terminal_state = "DRY_RUN"

    mapping = dag.TERMINAL_STATES[terminal_state]
    result.terminal_state = terminal_state
    result.status = mapping["status"]
    result.build_succeeded = mapping["build_succeeded"]

    if context.ir_out and Path(context.ir_out).exists():
        result.artifacts.append(context.ir_out)
    if context.render_outdir and Path(context.render_outdir).exists():
        result.artifacts.append(context.render_outdir)
    return result
