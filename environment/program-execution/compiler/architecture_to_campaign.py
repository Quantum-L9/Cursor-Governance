"""Lower architecture semantic IR into a complete campaign-source.v2.

This is the compilation step that turns audited candidate semantics into the
rich lossless execution representation Program Execution already runs on.
Rules encoded here, from the architecture-compilation contract:

- every complete generated task is ``definition_status: ready`` — ordering
  lives in dependency edges and waves, never in a blocked status;
- probeable unknowns become READY discovery tasks that dependents wait on;
- prohibitions survive as enforceable ``prohibited_paths`` plus task
  negative cases; deferrals survive as explicit scope exclusions;
- validations resolve from source-supplied commands first, then repository
  truth, then focused synthesis, then inspection assertions — never TODO;
- the generated source embeds ``intent_provenance`` so the canonical campaign
  compiler can revalidate the semantic mapping end to end.

Coverage failure here is a compile failure before any campaign side effect.
It is never a Blueprint full of BLOCKED tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .architecture_coverage import (
    CoverageResult,
    audit_coverage,
    requires_campaign_mapping,
)
from .architecture_extractor import ExtractionOutcome
from .architecture_intent import SourceDocument, parse_frontmatter
from .architecture_ir import SemanticItem, salient_tokens

CAMPAIGN_SOURCE_SCHEMA = "l9.program-execution.campaign-source.v2"
INTENT_PROVENANCE_SCHEMA = "l9.program-execution.intent-provenance.v1"
CAMPAIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)


class LoweringError(RuntimeError):
    """Architecture lowering failed before any campaign side effect."""


def slugify(value: str, *, max_length: int = 63) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:max_length].strip("-")


def action_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return (slug[:80] or "apply_architecture_requirement").strip("_")


def derive_campaign_id(
    document: SourceDocument,
    *,
    existing_ids: set[str],
    declared: str = "",
    title: str = "",
) -> str:
    """Readable deterministic slug with collision-safe suffixing.

    Never the forbidden ``pe-<hash>`` shape. An id already claimed by real
    campaign state gets a ``-v2``/``-v3`` suffix rather than colliding.
    """
    base = slugify(declared) or slugify(title) or slugify(Path(document.path).stem)
    if len(base) < 3:
        base = f"architecture-{base or 'campaign'}"
    if not CAMPAIGN_ID_RE.match(base):
        base = f"architecture-{slugify(base)[:50]}".strip("-")
    if base not in existing_ids:
        return base
    for index in range(2, 100):
        candidate = f"{base}-v{index}"
        if len(candidate) > 63:
            candidate = f"{base[: 63 - len(f'-v{index}')]}-v{index}"
        if candidate not in existing_ids and CAMPAIGN_ID_RE.match(candidate):
            return candidate
    raise LoweringError(f"could not assign a collision-free campaign id from {base!r}")


# ---------------------------------------------------------------------------
# Repository grounding (read-only)
# ---------------------------------------------------------------------------


@dataclass
class RepositoryGrounding:
    """Read-only microscope over the target checkout, when one is available.

    Grounding refines validations and paths and records evidence provenance.
    It never reverses explicit operator architecture intent, and its absence
    never blocks compilation — resolution degrades to inspection assertions.
    """

    repo_path: Path | None = None
    facts: list[dict[str, Any]] = field(default_factory=list)
    _native_commands: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        root = self.repo_path
        if root is None or not Path(root).is_dir():
            self.repo_path = None
            return
        root = Path(root)
        self.repo_path = root
        package = root / "package.json"
        if package.is_file():
            try:
                import json as _json

                scripts = (_json.loads(package.read_text(encoding="utf-8")) or {}).get(
                    "scripts"
                ) or {}
            except Exception:
                scripts = {}
            for script in ("test", "lint", "build"):
                if script in scripts:
                    self._native_commands.append(f"npm run {script} --silent")
                    self._record(f"package.json declares `{script}` script", "package.json")
        makefile = root / "Makefile"
        if makefile.is_file():
            text = makefile.read_text(encoding="utf-8", errors="replace")
            for target in ("test", "check", "validate"):
                if re.search(rf"^{target}:", text, re.M):
                    self._native_commands.append(f"make {target}")
                    self._record(f"Makefile declares `{target}` target", "Makefile")
        if (root / "pyproject.toml").is_file() or (root / "pytest.ini").is_file():
            if any(root.glob("tests/test_*.py")) or any(root.glob("**/tests/test_*.py")):
                self._native_commands.append("python3 -m pytest -q")
                self._record("pytest test suite present", "tests/")

    def _record(self, fact: str, evidence: str) -> None:
        self.facts.append(
            {
                "fact": fact,
                "evidence": evidence,
                "method": "read_only_inspection",
            }
        )

    def existing_paths(self, candidates: list[str]) -> list[str]:
        if self.repo_path is None:
            return []
        found = []
        for candidate in candidates:
            if (self.repo_path / candidate).exists():
                found.append(candidate)
        return found

    def resolve_validation(
        self,
        *,
        task_id: str,
        statement: str,
        explicit_commands: list[str],
        suggested_tests: list[str],
        paths: list[str],
    ) -> list[dict[str, Any]]:
        """§20 priority: explicit → repo-native focused → repo-native aggregate
        → synthesized focused command → inspection assertion. Never TODO."""
        entries: list[dict[str, Any]] = []

        def add(method: str, command: str) -> None:
            entries.append(
                {
                    "id": f"VAL-{task_id.split('-')[-1]}-{len(entries) + 1:02d}",
                    "method": method,
                    "command_or_inspection": command,
                    "expected_result": "PASS",
                }
            )

        for command in explicit_commands:
            add("command", command)
        if entries:
            return entries
        live_tests = self.existing_paths(suggested_tests)
        if live_tests:
            py_tests = [path for path in live_tests if path.endswith(".py")]
            if py_tests:
                add("command", f"python3 -m pytest {' '.join(py_tests)} -q --no-cov")
                self._record(
                    f"{task_id}: focused tests resolved from repository", "; ".join(py_tests)
                )
            for path in live_tests:
                if path.endswith((".ts", ".js")):
                    add("command", f"npm test --silent -- {path}")
                    self._record(f"{task_id}: focused JS/TS test resolved", path)
                    break
        if entries:
            return entries
        if self._native_commands:
            add("command", self._native_commands[0])
            self._record(
                f"{task_id}: repository-native validation attached", self._native_commands[0]
            )
            return entries
        add("inspection", statement)
        return entries


# ---------------------------------------------------------------------------
# Lowering
# ---------------------------------------------------------------------------


TASK_KINDS = frozenset({"requirement", "constraint", "objective"})
_DEFAULT_NEGATIVE_CASES = ("scope_expansion", "remote_mutation_before_release")


@dataclass
class LoweredCampaign:
    source: dict[str, Any]
    campaign_id: str
    mappings: dict[str, list[dict[str, Any]]]
    coverage: CoverageResult
    repository_evidence: list[dict[str, Any]]


def _first_ref_order(item: SemanticItem) -> tuple[str, str]:
    return (min(item.source_refs) if item.source_refs else "SRC-9999", item.id)


def _statement_title(statement: str, *, max_length: int = 96) -> str:
    text = " ".join(statement.split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _overlap(a: str, b: str) -> float:
    left, right = salient_tokens(a), salient_tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


class _TaskBuilder:
    def __init__(self) -> None:
        self.tasks: list[dict[str, Any]] = []
        self.by_semantic: dict[str, dict[str, Any]] = {}

    def new_task(
        self, item: SemanticItem, *, kernel_profile: str, discovery: bool
    ) -> dict[str, Any]:
        position = len(self.tasks) + 1
        task_id = f"TASK-{position:03d}"
        statement = item.statement
        task = {
            "id": task_id,
            "title": _statement_title(statement),
            "definition_status": "ready",
            "workstream_id": "WS-01",
            "wave_id": "W0",
            "target_id": "TARGET-001",
            "execution_kind": "repo_local",
            "objective": statement,
            "authority_basis_ids": ["AUTH-001"],
            "required_decision_ids": [],
            "blocking_unknown_ids": [],
            "input_evidence_ids": [],
            "paths": list(item.suggested_paths),
            "nugget_id": f"NUG-{position:03d}",
            "kernel_profile": kernel_profile,
            "consumers": [],
            "entrypoints": [],
            "actions": [
                (
                    f"inspect_repository_to_answer_{action_slug(statement)[:60]}"
                    if discovery
                    else action_slug(statement)
                )
            ],
            "acceptance": [],
            "validation": [],
            "negative_cases": list(_DEFAULT_NEGATIVE_CASES),
            "rollback": {
                "strategy": "discard_uncommitted_or_revert_local_commit",
                "trigger": "validation_failure",
                "validation": "worktree_matches_prior_head",
            },
            "risk": {
                "tier": "T0" if discovery else "T1",
                "reversibility": "fully_reversible",
                "blast_radius": "declared_paths",
            },
            "authorization_ceiling": {
                "inspect": True,
                "local_write": not discovery,
                "commit": not discovery,
                "push": False,
                "pull_request": False,
                "merge": False,
                "publish_or_release": False,
                "deploy_or_migrate": False,
                "destructive_change": False,
                "external_message": False,
            },
            "completion_gate_ids": [f"GATE-{position:03d}"],
            "_discovery": discovery,
            "_semantic_id": item.id,
            "_explicit_commands": [],
            "_suggested_tests": list(item.suggested_tests),
        }
        self.tasks.append(task)
        self.by_semantic[item.id] = task
        return task

    def owning_task(
        self, item: SemanticItem, items_by_id: dict[str, SemanticItem]
    ) -> dict[str, Any] | None:
        for related in item.related_semantic_ids:
            if related in self.by_semantic:
                return self.by_semantic[related]
        shared = [
            task
            for task in self.tasks
            if set(items_by_id[task["_semantic_id"]].source_refs) & set(item.source_refs)
        ]
        if len(shared) == 1:
            return shared[0]
        if shared:
            return max(shared, key=lambda task: _overlap(task["objective"], item.statement))
        if not self.tasks:
            return None
        best = max(self.tasks, key=lambda task: _overlap(task["objective"], item.statement))
        if _overlap(best["objective"], item.statement) > 0.0:
            return best
        return None


def lower_to_campaign_source(
    document: SourceDocument,
    outcome: ExtractionOutcome,
    *,
    target_repo: str,
    owner: str = "Igor Beylin",
    existing_ids: set[str] | None = None,
    repo_path: Path | None = None,
    stamp: str,
) -> LoweredCampaign:
    """Lower audited semantic items into a full campaign-source.v2 document."""
    items = list(outcome.items)
    items_by_id = {item.id: item for item in items}
    frontmatter = parse_frontmatter(document.text) or {}
    title = str(frontmatter.get("title") or "").strip()
    if not title:
        heading = _H1_RE.search(document.text)
        title = heading.group(1).strip() if heading else Path(document.path).stem
    owner = str(frontmatter.get("owner") or owner).strip() or "Igor Beylin"
    target_repo = str(frontmatter.get("target") or target_repo or "").strip()
    if not target_repo or "/" not in target_repo:
        raise LoweringError(
            "target repository cannot be identified: pass TARGET=owner/repo or declare "
            "`target:` in the architecture frontmatter"
        )
    campaign_id = derive_campaign_id(
        document,
        existing_ids=set(existing_ids or set()),
        declared=str(frontmatter.get("campaign_id") or ""),
        title=title,
    )
    grounding = RepositoryGrounding(repo_path=repo_path)
    mappings: dict[str, list[dict[str, Any]]] = {}

    def map_item(item_id: str, kind: str, ref_id: str, **extra: str) -> None:
        mappings.setdefault(item_id, []).append({"kind": kind, "id": ref_id, **extra})

    def by_kind(*kinds: str) -> list[SemanticItem]:
        chosen = [item for item in items if item.kind in kinds]
        return sorted(chosen, key=_first_ref_order)

    objectives = by_kind("objective")
    requirements = by_kind("requirement", "constraint")
    unknowns = by_kind("unknown")
    prohibitions = by_kind("prohibition")
    decisions = by_kind("decision")
    risks = by_kind("risk")
    assumptions = by_kind("assumption")
    deferrals = by_kind("deferral", "scope_exclude")
    includes = by_kind("scope_include")
    evidence_items = by_kind("evidence_requirement")
    acceptance_items = by_kind("acceptance")
    validation_items = by_kind("validation")
    negative_items = by_kind("negative_case")
    ordering_items = by_kind("ordering", "dependency")
    seam_items = by_kind("implementation_seam", "file_seam")

    if not requirements and not unknowns and not objectives:
        raise LoweringError(
            "architecture source yields no executable work: no requirement, constraint, "
            "objective, or probeable unknown survived semantic compilation"
        )

    builder = _TaskBuilder()
    # Discovery first: probeable unknowns become READY evidence tasks that
    # dependents wait on. A non-probeable unknown is represented as risk +
    # evidence requirement, never a blocked task.
    probeable = [item for item in unknowns if item.probeable is not False]
    for item in probeable:
        task = builder.new_task(item, kernel_profile="AUDIT", discovery=True)
        map_item(item.id, "task", task["id"], task_id=task["id"])
    for item in requirements:
        task = builder.new_task(item, kernel_profile="BUILD", discovery=False)
        map_item(item.id, "task", task["id"], task_id=task["id"])
    if not builder.tasks and objectives:
        task = builder.new_task(objectives[0], kernel_profile="BUILD", discovery=False)
        map_item(objectives[0].id, "task", task["id"], task_id=task["id"])

    for item in objectives:
        if item.id not in mappings:
            map_item(item.id, "program_objective", "PROGRAM")

    # Attach seams, acceptance, validations, negative cases to owning tasks.
    for item in seam_items:
        task = builder.owning_task(item, items_by_id)
        if task is None:
            continue
        for path in item.suggested_paths:
            if path not in task["paths"]:
                task["paths"].append(path)
                map_item(item.id, "task_path", path, task_id=task["id"])
        hint = item.implementation_hint or item.statement
        slug = action_slug(hint)
        if slug not in task["actions"]:
            task["actions"].append(slug)
            map_item(item.id, "task_action", slug, task_id=task["id"])
        if item.id not in mappings:
            map_item(item.id, "task_action", task["actions"][0], task_id=task["id"])

    for item in acceptance_items:
        task = builder.owning_task(item, items_by_id)
        if task is None:
            task = builder.tasks[0]
        entry_id = f"AC-{task['id'].split('-')[-1]}-{len(task['acceptance']) + 1:02d}"
        task["acceptance"].append(
            {
                "id": entry_id,
                "statement": item.statement,
                "required_evidence_types": ["inspection", "test_result"],
            }
        )
        map_item(item.id, "task_acceptance", entry_id, task_id=task["id"])

    for item in validation_items:
        task = builder.owning_task(item, items_by_id)
        if task is None:
            task = builder.tasks[0]
        if item.command:
            task["_explicit_commands"].append(item.command)
        task["_suggested_tests"].extend(item.suggested_tests)
        map_item(
            item.id,
            "task_validation",
            f"VAL-{task['id'].split('-')[-1]}-01",
            task_id=task["id"],
        )

    for item in negative_items:
        task = builder.owning_task(item, items_by_id)
        if task is None:
            task = builder.tasks[0]
        case = action_slug(item.statement)
        if case not in task["negative_cases"]:
            task["negative_cases"].append(case)
        map_item(item.id, "task_negative_case", case, task_id=task["id"])

    # Prohibitions: enforceable do-not-build entries plus negative cases on
    # the tasks that share their source neighborhood.
    prohibited_paths: list[dict[str, Any]] = []
    for position, item in enumerate(prohibitions, start=1):
        dnb_id = f"DNB-{position:03d}"
        prohibited_paths.append(
            {
                "id": dnb_id,
                "statement": item.statement,
                "rationale": item.rationale
                or "Explicit architecture prohibition; violation is a build refusal.",
            }
        )
        map_item(item.id, "prohibited_path", dnb_id)
        task = builder.owning_task(item, items_by_id)
        if task is not None:
            case = action_slug(item.statement)
            if case not in task["negative_cases"]:
                task["negative_cases"].append(case)
            map_item(item.id, "task_negative_case", case, task_id=task["id"])

    # Decisions require source-side options; synthesize the rejected
    # alternative only when the source names none.
    compiled_decisions: list[dict[str, Any]] = []
    for position, item in enumerate(decisions, start=1):
        decision_id = f"DEC-{position:03d}"
        options = [
            {"id": f"OPT-{index}", "description": option}
            for index, option in enumerate(item.options, start=1)
        ]
        if not options:
            options = [
                {"id": "OPT-1", "description": item.selected_option or item.statement},
                {
                    "id": "OPT-2",
                    "description": "Retain the current implementation unchanged.",
                },
            ]
        selected = "OPT-1"
        if item.selected_option:
            for option in options:
                if option["description"] == item.selected_option:
                    selected = option["id"]
        compiled_decisions.append(
            {
                "id": decision_id,
                "question": item.statement,
                "authority_id": "AUTH-001",
                "status": "accepted",
                "options": options,
                "selected_option_id": selected,
                "blocking_task_ids": [],
                "required_evidence_ids": [],
            }
        )
        map_item(item.id, "decision", decision_id)

    # Risks and testable assumptions (assumption + validation + rollback).
    compiled_risks: list[dict[str, Any]] = []
    for item in risks:
        risk_id = f"RISK-{len(compiled_risks) + 1:03d}"
        compiled_risks.append(
            {
                "id": risk_id,
                "statement": item.statement,
                "tier": "T1",
                "likelihood": "possible",
                "impact": "material",
                "owner": "AUTH-001",
                "mitigations": ["read_only_diagnosis_before_mutation", "bounded_rollback"],
            }
        )
        map_item(item.id, "risk", risk_id)
    for item in assumptions:
        risk_id = f"RISK-{len(compiled_risks) + 1:03d}"
        compiled_risks.append(
            {
                "id": risk_id,
                "statement": f"Assumption: {item.statement}",
                "tier": "T0",
                "likelihood": "possible",
                "impact": "low",
                "owner": "AUTH-001",
                "mitigations": [
                    "validate_assumption_during_task_execution",
                    "rollback_local_commit_if_falsified",
                ],
            }
        )
        map_item(item.id, "risk", risk_id)
        task = builder.owning_task(item, items_by_id)
        if task is not None:
            task["_suggested_tests"].extend(item.suggested_tests)

    # Evidence requirements: admission baseline + explicit + probeable unknowns.
    evidence_requirements: list[dict[str, Any]] = [
        {
            "id": "EVID-001",
            "claim": "exact_target_origin_main_revision_and_worktree_state_are_known",
            "source_type": "repository_inspection",
            "source_location": target_repo,
            "collection_method": "read_only_inspection",
            "freshness": "collect_at_admission",
            "producer": "controller",
            "supports": [builder.tasks[0]["id"]] if builder.tasks else [],
            "contradicts": [],
        }
    ]
    non_probeable = [entry for entry in unknowns if entry.probeable is False]
    for item in evidence_items + probeable + non_probeable:
        evid_id = f"EVID-{len(evidence_requirements) + 1:03d}"
        supports: list[str] = []
        task = builder.by_semantic.get(item.id)
        if task is not None:
            supports.append(task["id"])
        evidence_requirements.append(
            {
                "id": evid_id,
                "claim": action_slug(item.statement),
                "source_type": "repository_inspection",
                "source_location": target_repo,
                "collection_method": "read_only_inspection",
                "freshness": "collect_at_admission",
                "producer": "controller",
                "supports": supports,
                "contradicts": [],
            }
        )
        map_item(item.id, "evidence_requirement", evid_id)
        if task is not None:
            task["input_evidence_ids"] = [evid_id]

    # Dependency edges: explicit semantic edges, then discovery -> dependents.
    edges: list[dict[str, str]] = []
    edge_ids: dict[str, str] = {}

    def add_edge(from_task: str, to_task: str, item_id: str | None = None) -> None:
        if from_task == to_task:
            return
        key = f"{from_task}->{to_task}"
        if key not in edge_ids:
            edge_ids[key] = f"EDGE-{len(edge_ids) + 1:03d}"
            edges.append({"from": from_task, "to": to_task})
        if item_id is not None:
            map_item(item_id, "dependency_edge", edge_ids[key])

    for item in ordering_items:
        predecessors = [
            builder.by_semantic[ref]["id"]
            for ref in item.predecessor_ids
            if ref in builder.by_semantic
        ]
        successors = [
            builder.by_semantic[ref]["id"]
            for ref in item.successor_ids
            if ref in builder.by_semantic
        ]
        if predecessors and successors:
            for pred in predecessors:
                for succ in successors:
                    add_edge(pred, succ, item.id)
            continue
        # Resolve by objective overlap: an ordering sentence usually names both
        # sides in the source's own vocabulary.
        scored = sorted(
            builder.tasks,
            key=lambda task: _overlap(task["objective"], item.statement),
            reverse=True,
        )
        pair = [task for task in scored[:2] if _overlap(task["objective"], item.statement) > 0.0]
        if len(pair) == 2:
            first, second = sorted(pair, key=lambda task: task["id"])
            add_edge(first["id"], second["id"], item.id)
        else:
            # Ordering that resolves to no task pair is carried by the wave
            # plan itself, which is the ordering representation.
            map_item(item.id, "wave", "W0")

    for item in probeable:
        discovery_task = builder.by_semantic[item.id]
        dependents = {
            builder.by_semantic[ref]["id"]
            for ref in item.successor_ids
            if ref in builder.by_semantic
        }
        if not dependents:
            shared_units = set(item.source_refs)
            for task in builder.tasks:
                if task["_discovery"]:
                    continue
                other = items_by_id[task["_semantic_id"]]
                if (
                    set(other.source_refs) & shared_units
                    or _overlap(task["objective"], item.statement) >= 0.5
                ):
                    dependents.add(task["id"])
        for dependent in sorted(dependents):
            add_edge(discovery_task["id"], dependent)

    # Topological waves. Cycles fail compilation loudly.
    task_ids = [task["id"] for task in builder.tasks]
    preds: dict[str, set[str]] = {task_id: set() for task_id in task_ids}
    for edge in edges:
        if edge["to"] in preds and edge["from"] in preds:
            preds[edge["to"]].add(edge["from"])
    level: dict[str, int] = {}
    remaining = set(task_ids)
    depth = 0
    while remaining:
        frontier = {task_id for task_id in remaining if preds[task_id].issubset(level.keys())}
        if not frontier:
            raise LoweringError(f"dependency cycle among tasks: {sorted(remaining)}")
        for task_id in sorted(frontier):
            level[task_id] = depth
        remaining -= frontier
        depth += 1

    waves: list[dict[str, Any]] = []
    for wave_index in range(depth):
        wave_id = f"W{wave_index}"
        wave_tasks = sorted(task_id for task_id, lvl in level.items() if lvl == wave_index)
        for task in builder.tasks:
            if task["id"] in wave_tasks:
                task["wave_id"] = wave_id
        waves.append(
            {
                "id": wave_id,
                "name": f"wave_{wave_index}",
                "task_ids": wave_tasks,
                "predecessor_wave_ids": [f"W{wave_index - 1}"] if wave_index else [],
                "exit_gate_ids": [f"GATE-{task_id.split('-')[-1]}" for task_id in wave_tasks],
            }
        )

    # Finalize tasks: validations, acceptance fallbacks, consumers/entrypoints.
    gates: list[dict[str, Any]] = []
    for task in builder.tasks:
        item = items_by_id[task["_semantic_id"]]
        live_paths = grounding.existing_paths(task["paths"])
        for fact_path in live_paths:
            grounding._record(f"{task['id']}: declared path exists in repository", fact_path)
        if not task["acceptance"]:
            if task["_discovery"]:
                statement = f"Question answered with recorded repository evidence: {item.statement}"
            else:
                statement = (
                    f"Repository behavior satisfies the architecture obligation: {item.statement}"
                )
            task["acceptance"] = [
                {
                    "id": f"AC-{task['id'].split('-')[-1]}",
                    "statement": statement,
                    "required_evidence_types": (
                        ["inspection"] if task["_discovery"] else ["inspection", "test_result"]
                    ),
                }
            ]
        task["validation"] = grounding.resolve_validation(
            task_id=task["id"],
            statement=task["acceptance"][0]["statement"],
            explicit_commands=list(dict.fromkeys(task.pop("_explicit_commands"))),
            suggested_tests=list(dict.fromkeys(task.pop("_suggested_tests"))),
            paths=task["paths"],
        )
        task["consumers"] = list(task["paths"]) or [target_repo]
        task["entrypoints"] = list(task["paths"]) or ["make campaign"]
        gate_id = task["completion_gate_ids"][0]
        gates.append(
            {
                "id": gate_id,
                "name": f"{task['id'].lower()}_complete",
                "gate_type": "entry" if task["id"] == task_ids[0] else "completion",
                "blocking": True,
                "owner_authority_id": "AUTH-001",
                "task_ids": [task["id"]],
                "required_evidence_ids": list(task["input_evidence_ids"]),
                "pass_criteria": [task["acceptance"][0]["statement"]],
                "failure_effect": "block_successor_tasks",
            }
        )
        task.pop("_discovery")
        task.pop("_semantic_id")

    # Program-level scope.
    objective_text = (
        objectives[0].statement
        if objectives
        else (requirements[0].statement if requirements else title)
    )
    scope_include = [f"{target_repo} repository-local work"]
    for item in includes:
        scope_include.append(item.statement)
        map_item(item.id, "scope_include", f"SCOPE-IN-{len(scope_include):02d}")
    scope_exclude = []
    for item in deferrals:
        scope_exclude.append(item.statement)
        map_item(item.id, "scope_exclude", f"SCOPE-EX-{len(scope_exclude):02d}")
    scope_exclude.extend(
        ["new repositories", "force_push", "admin_merge", "deploy", "production migration"]
    )

    source_units_payload = []
    for unit in document.units:
        entry = unit.to_dict()
        entry["materiality"] = (
            "routing_metadata"
            if unit.kind == "frontmatter"
            else (
                "material"
                if any(
                    ref == unit.id
                    for item in items
                    if item.materiality == "material" and item.kind != "informational"
                    for ref in item.source_refs
                )
                else "informational"
            )
        )
        source_units_payload.append(entry)

    campaign_source: dict[str, Any] = {
        "schema": CAMPAIGN_SOURCE_SCHEMA,
        "schema_version": "2.0.0",
        "plan_status": "Ready",
        "metadata": {
            "campaign_id": campaign_id,
            "title": title,
            "version": "1.0.0",
            "created_at": stamp,
            "status": "operator_intake",
            "owner": owner,
            "intended_host": target_repo,
            "intended_drop_path": (
                f"environment/program-execution/campaigns/{campaign_id}/CAMPAIGN_SOURCE.yaml"
            ),
            "runtime_root": f"$HOME/.l9/programs/{campaign_id}",
            "worktree_root": f"$HOME/.l9/program-worktrees/{campaign_id}",
            "source_is_immutable": True,
            "remote_mutation_during_admission": False,
            "compiled_by": "compile_architecture_intent",
        },
        "integrity": {
            "digest_algorithm": "sha256",
            "canonical_encoding": "utf-8",
            "canonical_line_endings": "lf",
            "digest_record_location": "source-integrity-receipt.json",
            "generated_counts_or_digests_may_be_hand_edited": False,
        },
        "pipeline_contract": {
            "pair": "program-execution-system.v2",
            "blueprint": "program-execution-blueprint.v2",
            "controller": "program-execution-controller.v2",
        },
        "operator_directive": {
            "objective": objective_text,
            "mode": "controlled_autonomous_until_material_boundary",
            "policy_profile": "quantum-l9.safe-autonomy.v1",
            "prohibited_actions": [
                "force_push",
                "admin_merge",
                "deploy",
                "weaken_validators",
                "delete_tests_for_pass",
            ],
        },
        "program": {
            "id": campaign_id,
            "name": title,
            "version": "1.0.0",
            "owner": owner,
            "definition_status": "ready",
            "plan_status": "Ready",
            "snapshot_at": stamp[:10],
            "objective": objective_text,
            "problem_statement": (
                f"Compiled from architecture intent {Path(document.path).name} "
                f"(sha256 {document.sha256[:12]}…): {objective_text}"
            ),
            "target_state": objective_text,
            "scope": {"include": scope_include, "exclude": scope_exclude},
            "contracts": {
                "pair": "program-execution-system.v2",
                "blueprint": "program-execution-blueprint.v2",
                "controller_minimum": "program-execution-controller.v2",
            },
            "authority_order": [
                "applicable_safety_legal_security_requirements",
                "cursor_governance_canonical_law",
                "explicit_operator_architecture_source",
                "accepted_program_definition",
                "verified_repository_evidence",
                "deterministic_compiler_derivations",
                "semantic_extractor_candidates",
                "UNKNOWN",
            ],
            "operating_rules": [
                "one_authority_per_responsibility",
                "mutable_runtime_state_remains_outside_git",
                "no_silent_scope_expansion",
                "worker_claim_is_not_verification",
            ],
            "terminal_verdicts": [
                "CONVERGED",
                "CONVERGED_WITH_NON_BLOCKING_RISKS",
                "NOT_CONVERGED",
                "INCONCLUSIVE",
            ],
        },
        "targets": [
            {
                "id": "TARGET-001",
                "name": target_repo,
                "kind": "git_repository",
                "authority_owner": target_repo,
                "execution_mode": "repo_local",
                "repository_id": target_repo,
                "source_of_truth": "repository_origin_main",
                "environments": ["local", "ci"],
                "mutability": "reversible",
                "expected_revision": "UNKNOWN",
                "adapter": "git",
            }
        ],
        "authorities": [{"id": "AUTH-001", "responsibility": "campaign_owner", "owner": owner}],
        "workstreams": [
            {"id": "WS-01", "name": title, "owner": "AUTH-001", "objective": objective_text}
        ],
        "evidence_requirements": evidence_requirements,
        "decisions": compiled_decisions,
        "risks": compiled_risks,
        "prohibited_paths": prohibited_paths,
        "dependency_edges": edges,
        "waves": waves,
        "tasks": builder.tasks,
        "gates": gates,
        "intent_provenance": {
            "schema": INTENT_PROVENANCE_SCHEMA,
            "source": {
                "sha256": document.sha256,
                "media_type": document.media_type,
                "path": Path(document.path).name,
            },
            "source_units": source_units_payload,
            "semantic_items": [
                {**item.to_dict(), "campaign_mappings": mappings.get(item.id, [])} for item in items
            ],
            "coverage": {},  # filled below after the final audit
            "extractor": {
                "identity": outcome.extractor_identity,
                "protocol": "l9.program-execution.architecture-extractor-request.v1",
            },
            "repair_rounds": outcome.repair_rounds,
        },
    }

    final_coverage = audit_coverage(
        document,
        items,
        mappings=mappings,
        requested_unit_ids=outcome.requested_unit_ids,
    )
    campaign_source["intent_provenance"]["coverage"] = {
        "total_units": final_coverage.total_units,
        "classified_units": final_coverage.classified_units,
        "material_units": final_coverage.material_units,
        "mapped_material_units": final_coverage.mapped_material_units,
        "unmapped_material_units": final_coverage.unmapped_material_units,
        "status": final_coverage.status,
    }
    if not final_coverage.passed:
        details = "; ".join(str(problem.get("detail")) for problem in final_coverage.problems[:6])
        raise LoweringError(
            f"semantic coverage did not converge (status {final_coverage.status}): {details}"
        )
    unmapped = [
        item.id for item in items if requires_campaign_mapping(item) and not mappings.get(item.id)
    ]
    if unmapped:
        raise LoweringError(f"material semantic items lost their campaign mapping: {unmapped}")
    return LoweredCampaign(
        source=campaign_source,
        campaign_id=campaign_id,
        mappings=mappings,
        coverage=final_coverage,
        repository_evidence=list(grounding.facts),
    )
