"""Lower architecture semantics into a complete campaign-source.v2.

Deliberately not the activate-seed shape. `campaign-source.v2` is already the
rich lossless execution representation — tasks with actions, acceptance,
validation, negative cases, authority ceilings, dependency edges, waves, gates,
prohibitions, decisions, risks, and evidence — so lowering into anything weaker
would throw away exactly the material this compiler exists to preserve.

Two rules govern every choice below.

Forward progress. Every complete task is emitted `definition_status: ready`
(ADR-0023). Ordering lives in `dependencies`, `dependency_edges`, `waves`, and
gates. A probeable unknown becomes a *ready* evidence task with dependents
edged behind it; it never becomes a blocked task, and neither does anything else.

Repository truth grounds, it does not overrule. Paths, test commands, and Make
targets are resolved against the real target checkout so validations are
runnable. But where the architecture asks for something the repository does not
yet do, the requirement stands and the difference becomes the task — that gap
is the reason the operator wrote the document.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .architecture_coverage import CoverageReport, ExtractionResult, audit
from .architecture_intent import (
    INTENT_PROVENANCE_SCHEMA,
    ArchitectureIntent,
    slugify,
)
from .architecture_ir import SemanticItem

CAMPAIGN_SOURCE_SCHEMA = "l9.program-execution.campaign-source.v2"
DEFAULT_OWNER = "Igor Beylin"
GOVERNANCE_HOST = "Quantum-L9/Cursor-Governance"

TASK_KINDS = frozenset({"requirement", "constraint", "implementation_seam", "objective"})

_SECTION_TITLE_LIMIT = 72
_STATEMENT_LIMIT = 400
_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}|REPLACE_WITH_[A-Z0-9_]+")


class LoweringError(RuntimeError):
    """The architecture cannot be lowered into an executable campaign source."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------
# Repository grounding (read-only, bounded)
# --------------------------------------------------------------------------


@dataclass
class RepositoryFacts:
    """What the target checkout actually is, collected read-only.

    Bounded on purpose: a handful of manifest reads and existence checks, not a
    whole-tree walk. Every fact carries where it came from so the campaign can
    record evidence provenance rather than assert.
    """

    root: Path | None
    repository_id: str
    #: Empty when the remote's default branch could not be observed.
    default_branch: str = ""
    validation_commands: tuple[str, ...] = ()
    package_manager: str = ""
    evidence: tuple[dict[str, str], ...] = ()

    def path_exists(self, candidate: str) -> bool:
        if self.root is None:
            return False
        try:
            return (self.root / candidate).exists()
        except OSError:
            return False


def inspect_repository(root: Path | None, repository_id: str) -> RepositoryFacts:
    if root is None or not Path(root).is_dir():
        return RepositoryFacts(root=None, repository_id=repository_id)
    root = Path(root).resolve()
    commands: list[str] = []
    evidence: list[dict[str, str]] = []
    package_manager = ""
    package_json = root / "package.json"
    if package_json.is_file():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts") or {}
        except (OSError, json.JSONDecodeError):
            scripts = {}
        package_manager = "npm"
        for name in ("verify:types", "lint", "test", "build"):
            if name in scripts:
                commands.append(f"npm run {name}" if name != "test" else "npm test")
                evidence.append({"fact": f"npm script {name}", "source": "package.json"})
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        package_manager = package_manager or ("uv" if "[tool.uv]" in text else "python")
        if "pytest" in text:
            commands.append("pytest -q")
            evidence.append({"fact": "pytest configured", "source": "pyproject.toml"})
        if "[tool.ruff" in text:
            commands.append("ruff check .")
            evidence.append({"fact": "ruff configured", "source": "pyproject.toml"})
    makefile = root / "Makefile"
    if makefile.is_file():
        targets = _make_targets(makefile)
        for name in ("test", "lint", "check", "validate"):
            if name in targets:
                commands.append(f"make {name}")
                evidence.append({"fact": f"make target {name}", "source": "Makefile"})
    if (root / ".pre-commit-config.yaml").is_file() and not commands:
        commands.append("pre-commit run --all-files")
        evidence.append({"fact": "pre-commit configured", "source": ".pre-commit-config.yaml"})
    branch = _default_branch(root)
    if branch:
        evidence.append({"fact": f"default branch {branch}", "source": "git"})
    return RepositoryFacts(
        root=root,
        repository_id=repository_id,
        default_branch=branch,
        validation_commands=tuple(dict.fromkeys(commands)),
        package_manager=package_manager,
        evidence=tuple(evidence),
    )


_MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?!=)", re.M)


def _make_targets(path: Path) -> set[str]:
    try:
        return set(_MAKE_TARGET_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
    except OSError:
        return set()


def _default_branch(root: Path) -> str:
    """The remote's default branch, or "" when it is not observable.

    `rev-parse --abbrev-ref HEAD` reported whatever branch the checkout
    happened to be on, which is not the repository's default branch.
    """
    git = shutil.which("git")
    if git is None:
        return ""
    try:
        result = subprocess.run(  # noqa: S603 - argv list, no shell
            [git, "-C", str(root), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip().removeprefix("origin/")


# --------------------------------------------------------------------------
# Sectioning and task grouping
# --------------------------------------------------------------------------


@dataclass
class Section:
    index: int
    title: str
    unit_ids: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return slugify(self.title) or f"section-{self.index:02d}"


def sections_for(intent: ArchitectureIntent) -> tuple[list[Section], dict[str, int]]:
    """Group units under their nearest preceding heading.

    Sections are the natural task boundary in an architecture document: the
    author already grouped obligations that belong together, and honoring that
    beats any clustering the compiler could invent.
    """
    sections: list[Section] = []
    by_unit: dict[str, int] = {}
    current = Section(index=0, title=intent.title or "Architecture")
    sections.append(current)
    for unit in intent.units:
        if unit.kind == "heading":
            title = unit.text.lstrip("#").strip()[:_SECTION_TITLE_LIMIT]
            current = Section(index=len(sections), title=title or f"Section {len(sections)}")
            sections.append(current)
        current.unit_ids.append(unit.id)
        by_unit[unit.id] = current.index
    return sections, by_unit


def _section_of(item: SemanticItem, by_unit: dict[str, int]) -> int:
    return min((by_unit.get(ref, 0) for ref in item.source_refs), default=0)


# --------------------------------------------------------------------------
# Lowering
# --------------------------------------------------------------------------


@dataclass
class LoweredCampaign:
    source: dict[str, Any]
    coverage: CoverageReport
    mappings: dict[str, list[dict[str, Any]]]
    task_count: int
    prohibition_count: int
    validation_count: int


def lower(
    intent: ArchitectureIntent,
    extraction: ExtractionResult,
    *,
    campaign_id: str,
    owner: str = DEFAULT_OWNER,
    repository: RepositoryFacts | None = None,
    stamp: str | None = None,
    host: str | None = None,
) -> LoweredCampaign:
    now = stamp or utc_now()
    facts = repository or RepositoryFacts(root=None, repository_id=intent.target)
    # `intended_host` names the repository the campaign executes against -- both
    # its consumers read it that way, and EVID-001 binds the campaign source to
    # that repository's origin/main. Defaulting it to the governance repo while
    # `targets[].repository_id` named another emitted a source that contradicted
    # itself, which the compiler now refuses. An explicit host still wins.
    host = str(host or facts.repository_id or GOVERNANCE_HOST).strip()
    items = list(extraction.items)
    sections, by_unit = sections_for(intent)
    mappings: dict[str, list[dict[str, Any]]] = {item.id: [] for item in items}

    def map_item(item_id: str, kind: str, **extra: Any) -> None:
        entry = {"kind": kind}
        entry.update({key: value for key, value in extra.items() if value})
        mappings.setdefault(item_id, []).append(entry)

    by_kind: dict[str, list[SemanticItem]] = {}
    for item in items:
        by_kind.setdefault(item.kind, []).append(item)

    material = [item for item in items if item.material]

    # ---- program frame -------------------------------------------------
    objectives = [item for item in material if item.kind == "objective"]
    requirements = [item for item in material if item.kind in TASK_KINDS]
    if not requirements and not objectives:
        raise LoweringError(
            "architecture source yielded no material requirement, constraint, or objective; "
            "nothing executable to compile"
        )
    objective_text = _objective_text(intent, objectives, requirements)
    for item in objectives:
        map_item(item.id, "program_objective")

    scope_include = [item for item in material if item.kind == "scope_include"]
    scope_exclude = [item for item in material if item.kind in {"scope_exclude", "deferral"}]
    for item in scope_include:
        map_item(item.id, "program_scope_include")
    for item in scope_exclude:
        map_item(item.id, "program_scope_exclude")

    # ---- prohibitions --------------------------------------------------
    prohibitions = [item for item in material if item.kind in {"prohibition", "negative_case"}]
    prohibited_paths: list[dict[str, Any]] = []
    for index, item in enumerate(prohibitions, start=1):
        dnb_id = f"DNB-{index:03d}"
        prohibited_paths.append(
            {
                "id": dnb_id,
                "statement": _clip(item.statement),
                "rationale": _clip(item.rationale)
                or f"Architecture source states this prohibition ({', '.join(item.source_refs)}).",
                "source_refs": list(item.source_refs),
                "semantic_id": item.id,
            }
        )
        map_item(item.id, "prohibited_path", id=dnb_id)
    for index, item in enumerate(scope_exclude, start=len(prohibited_paths) + 1):
        dnb_id = f"DNB-{index:03d}"
        prohibited_paths.append(
            {
                "id": dnb_id,
                "statement": f"Deferred out of this program's scope: {_clip(item.statement)}",
                "rationale": "Explicit deferral in the architecture source; it stays deferred "
                "rather than silently becoming work.",
                "source_refs": list(item.source_refs),
                "semantic_id": item.id,
            }
        )
        map_item(item.id, "prohibited_path", id=dnb_id)

    # ---- decisions -----------------------------------------------------
    decisions: list[dict[str, Any]] = []
    for index, item in enumerate(by_kind.get("decision", []), start=1):
        if not item.material:
            continue
        dec_id = f"DEC-{index:03d}"
        decisions.append(
            {
                "id": dec_id,
                "question": f"Is the architecture decision honored: {_clip(item.statement)}?",
                "status": "accepted",
                "authority_id": "AUTH-002",
                "options": [
                    {
                        "id": f"{dec_id}-A",
                        "description": _clip(item.statement),
                    },
                    {
                        "id": f"{dec_id}-B",
                        "description": "Leave the current implementation unchanged, contradicting "
                        "the architecture source.",
                    },
                ],
                "selected_option_id": f"{dec_id}-A",
                "required_evidence_ids": [],
                "blocking_task_ids": [],
                "source_refs": list(item.source_refs),
                "semantic_id": item.id,
            }
        )
        map_item(item.id, "decision", id=dec_id)

    # ---- risks and assumptions -----------------------------------------
    risks: list[dict[str, Any]] = []
    for index, item in enumerate(
        [entry for entry in material if entry.kind in {"risk", "assumption"}], start=1
    ):
        risk_id = f"RISK-{index:03d}"
        risks.append(
            {
                "id": risk_id,
                "statement": _clip(item.statement),
                "owner": owner,
                "impact": "material",
                "likelihood": "possible",
                "mitigations": [
                    "Validate the affected task before completion.",
                    "Preserve rollback to the Program Lock base.",
                ],
                "source_refs": list(item.source_refs),
                "semantic_id": item.id,
            }
        )
        map_item(item.id, "risk", id=risk_id)

    # ---- unknowns: probeable ones become ready evidence tasks -----------
    unknown_items = [item for item in material if item.kind == "unknown"]
    unknown_sections: dict[int, list[SemanticItem]] = {}
    for item in unknown_items:
        unknown_sections.setdefault(_section_of(item, by_unit), []).append(item)

    # ---- tasks ---------------------------------------------------------
    task_items: dict[int, list[SemanticItem]] = {}
    for item in material:
        if item.kind in TASK_KINDS or item.kind in {"file_seam", "dependency", "ordering"}:
            task_items.setdefault(_section_of(item, by_unit), []).append(item)

    tasks: list[dict[str, Any]] = []
    evidence_requirements: list[dict[str, Any]] = []
    discovery_by_section: dict[int, str] = {}
    # Recorded as each task is actually created. Deriving it positionally
    # instead — zipping ordered sections against the task list — silently
    # shifts by one for every section that produces no task of its own, which
    # edged a discovery task to the wrong dependent.
    impl_by_section: dict[int, dict[str, Any]] = {}
    counter = 0

    def next_task_id() -> str:
        nonlocal counter
        counter += 1
        return f"TASK-{counter:03d}"

    section_lookup = {section.index: section for section in sections}
    for section_index in sorted(unknown_sections):
        section = section_lookup[section_index]
        group = unknown_sections[section_index]
        task_id = next_task_id()
        evid_id = f"EVID-{len(evidence_requirements) + 1:03d}"
        evidence_requirements.append(
            {
                "id": evid_id,
                "claim": f"open_questions_in_{section.slug or 'architecture'}_are_evidence_bound",
                "source_type": "repository_inspection",
                "source_location": facts.repository_id,
                "collection_method": "read_only_inspection",
                "freshness": "collect_at_admission",
                "producer": "controller",
                "supports": [task_id],
                "contradicts": [],
            }
        )
        tasks.append(
            _task(
                task_id=task_id,
                title=f"Resolve open questions: {section.title}"[:_SECTION_TITLE_LIMIT],
                objective=(
                    "Answer the architecture source's open questions for "
                    f"{section.title} by read-only inspection of {facts.repository_id}, and "
                    "record the answer as evidence the dependent implementation task consumes."
                ),
                actions=[
                    f"Inspect the repository to answer: {_clip(item.statement)}" for item in group
                ],
                acceptance=[
                    {
                        "id": f"AC-{task_id.split('-')[-1]}",
                        "statement": (
                            "Every listed open question is answered from repository evidence, "
                            "with the file or command that produced the answer recorded."
                        ),
                        "required_evidence_types": ["inspection"],
                    }
                ],
                validation=[
                    {
                        "check": "evidence recorded for each open question",
                        "method": "inspection",
                        "command_or_inspection": (
                            "Inspect the task receipt: each open question has an answer and a "
                            "cited repository location that produced it."
                        ),
                        "environment": "local",
                        "evidence": "task receipt inspection",
                    }
                ],
                negative_cases=[
                    "assumed_answer_without_repository_evidence",
                    "mutation_before_evidence_is_recorded",
                ],
                paths=[],
                read_only=True,
                input_evidence_ids=[evid_id],
                target_id="TARGET-001",
                workstream_id="WS-02",
            )
        )
        discovery_by_section[section_index] = task_id
        for item in group:
            map_item(item.id, "task", task_id=task_id)
            map_item(item.id, "evidence_requirement", id=evid_id)

    for section_index in sorted(task_items):
        section = section_lookup[section_index]
        group = task_items[section_index]
        drivers = [item for item in group if item.kind in TASK_KINDS]
        if not drivers:
            # A section that only names files is a seam of another section's
            # work, not a task of its own; fold it into the program's paths.
            continue
        task_id = next_task_id()
        seams = [item for item in group if item.kind == "file_seam"]
        section_units = set(section.unit_ids)
        acceptance_items = [
            item
            for item in material
            if item.kind == "acceptance" and section_units & set(item.source_refs)
        ]
        validation_items = [
            item
            for item in material
            if item.kind == "validation" and section_units & set(item.source_refs)
        ]
        prohibition_items = [item for item in prohibitions if section_units & set(item.source_refs)]
        paths = _resolve_paths(drivers + seams, facts)
        validation = _resolve_validation(validation_items, facts, paths)
        tasks.append(
            _task(
                task_id=task_id,
                title=section.title[:_SECTION_TITLE_LIMIT],
                objective=_task_objective(section, drivers),
                actions=[_action(item) for item in drivers] or [f"Implement {section.title}."],
                acceptance=_task_acceptance(task_id, acceptance_items, drivers),
                validation=validation,
                negative_cases=_task_negative_cases(prohibition_items),
                paths=paths,
                read_only=False,
                input_evidence_ids=[],
                target_id="TARGET-001",
                workstream_id="WS-01",
            )
        )
        for item in drivers:
            map_item(item.id, "task", task_id=task_id)
            map_item(item.id, "task_action", task_id=task_id)
        for item in seams:
            map_item(item.id, "task_path", task_id=task_id)
        for item in acceptance_items:
            map_item(item.id, "task_acceptance", task_id=task_id)
        for item in validation_items:
            map_item(item.id, "task_validation", task_id=task_id)
        for item in prohibition_items:
            map_item(item.id, "task_negative_case", task_id=task_id)
        for item in group:
            if item.kind in {"dependency", "ordering"}:
                map_item(item.id, "task", task_id=task_id)
        impl_by_section[section_index] = tasks[-1]

    if not tasks:
        raise LoweringError("architecture source produced no executable tasks")

    _adopt_orphans(items, mappings, tasks, impl_by_section, by_unit, map_item)

    # Any evidence_requirement item the source stated directly.
    for item in [entry for entry in material if entry.kind == "evidence_requirement"]:
        evid_id = f"EVID-{len(evidence_requirements) + 1:03d}"
        evidence_requirements.append(
            {
                "id": evid_id,
                "claim": slugify(item.statement, limit=80).replace("-", "_")
                or "architecture_evidence_requirement",
                "source_type": "repository_inspection",
                "source_location": facts.repository_id,
                "collection_method": "read_only_inspection",
                "freshness": "collect_at_admission",
                "producer": "controller",
                "supports": [tasks[0]["id"]],
                "contradicts": [],
            }
        )
        map_item(item.id, "evidence_requirement", id=evid_id)

    if not evidence_requirements:
        evidence_requirements.append(
            {
                "id": "EVID-001",
                "claim": "architecture_source_and_target_origin_main_are_bound",
                "source_type": "repository_inspection",
                "source_location": facts.repository_id,
                "collection_method": "read_only_inspection",
                "freshness": "collect_at_admission",
                "producer": "controller",
                "supports": [tasks[0]["id"]],
                "contradicts": [],
            }
        )

    # ---- ordering ------------------------------------------------------
    edges = _dependency_edges(discovery_by_section, impl_by_section, tasks)
    for item in [entry for entry in material if entry.kind in {"dependency", "ordering"}]:
        if mappings.get(item.id):
            map_item(item.id, "dependency_edge")
    waves = _waves(tasks, edges)
    for task in tasks:
        task["wave_id"] = next(wave["id"] for wave in waves if task["id"] in wave["task_ids"])
    gates = _gates(waves, tasks)
    for wave in waves:
        wave["exit_gate_ids"] = [
            gate["id"] for gate in gates if set(gate["task_ids"]) & set(wave["task_ids"])
        ]
    for task in tasks:
        task["completion_gate_ids"] = [
            gate["id"] for gate in gates if task["id"] in gate["task_ids"]
        ]

    workstreams = [
        {
            "id": "WS-01",
            "name": "architecture_implementation",
            "objective": "Implement the obligations the architecture source states.",
            "owner": owner,
        }
    ]
    if any(task["workstream_id"] == "WS-02" for task in tasks):
        workstreams.insert(
            0,
            {
                "id": "WS-02",
                "name": "architecture_evidence",
                "objective": (
                    "Answer the architecture source's open questions from repository evidence."
                ),
                "owner": owner,
            },
        )

    validation_count = sum(len(task.get("validation") or []) for task in tasks)
    coverage = audit(
        intent,
        items,
        mappings=mappings,
        chunks_expected=extraction.coverage.chunks_expected,
        chunks_extracted=extraction.coverage.chunks_extracted,
    )
    provenance = build_provenance(
        intent,
        extraction,
        coverage=coverage,
        mappings=mappings,
        campaign_id=campaign_id,
    )
    source = {
        "schema": CAMPAIGN_SOURCE_SCHEMA,
        "schema_version": "2.0.0",
        "metadata": {
            "campaign_id": campaign_id,
            "title": intent.title,
            "version": "1.0.0",
            "created_at": now,
            "status": "operator_intake",
            "owner": owner,
            "intended_host": host,
            "intended_drop_path": (
                f"environment/program-execution/campaigns/{campaign_id}/CAMPAIGN_SOURCE.yaml"
            ),
            "source_is_immutable": True,
            "compiled_from": "l9.program-execution.architecture-intent.v1",
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
            "compilation_sequence": [
                "segment_and_hash_architecture_source",
                "extract_candidate_semantics",
                "admit_only_source_grounded_items",
                "audit_semantic_coverage",
                "lower_into_campaign_source_v2",
                "compile_native_blueprint",
                "validate_blueprint",
                "bootstrap_controller",
                "execute_reversible_local_waves",
            ],
        },
        "operator_directive": {
            "objective": objective_text,
            "mode": "controlled_autonomous_until_material_boundary",
            "auto_continue": [
                "read_only_repository_inspection",
                "reversible_repo_local_work",
                "local_validation",
                "local_commit_creation_after_task_gate_pass",
            ],
            "pause_only_for": [
                "missing_or_conflicting_semantic_authority",
                "material_scope_expansion",
                "failed_blocking_gate",
                "exact_remote_mutation_approval",
            ],
        },
        "plan_status": "Ready",
        "program": {
            "id": campaign_id,
            "name": intent.title,
            "version": "1.0.0",
            "owner": owner,
            "definition_status": "ready",
            "snapshot_at": now,
            "objective": objective_text,
            "problem_statement": _problem_statement(intent, requirements, facts),
            "target_state": _target_state(intent, requirements),
            "scope": {
                "include": _scope_include(scope_include, tasks),
                "exclude": _scope_exclude(scope_exclude, prohibitions),
            },
            "contracts": {
                "pair": "program-execution-system.v2",
                "blueprint": "program-execution-blueprint.v2",
                "controller_minimum": "program-execution-controller.v2",
            },
            "authority_order": [
                "applicable safety and security law",
                "repository canonical governance",
                "explicit operator architecture source",
                "accepted ADRs and contracts",
                "verified current repository evidence",
                "deterministic compiler derivations",
                "semantic extractor candidate interpretation",
            ],
            "operating_rules": [
                "Every obligation carries a source unit citation back to the architecture source.",
                "Ordering is expressed by dependencies, waves, and gates; never by "
                + "definition status.",
                "Local work only: no remote mutation inside campaign execution.",
                "Repository evidence grounds implementation; it does not overrule operator intent.",
            ],
            "terminal_verdicts": [
                "CONVERGED",
                "CONVERGED_WITH_NON_BLOCKING_RISKS",
                "NOT_CONVERGED",
                "INCONCLUSIVE",
            ],
            "target_repository_id": facts.repository_id,
        },
        "targets": [
            {
                "id": "TARGET-001",
                "name": facts.repository_id,
                "kind": "git_repository",
                "authority_owner": facts.repository_id,
                "execution_mode": "repo_local",
                "repository_id": facts.repository_id,
                "source_of_truth": "repository_origin_main",
                "environments": ["local", "ci"],
                "mutability": "reversible",
                "expected_revision": "UNKNOWN",
                "adapter": "git",
            },
            {
                "id": "TARGET-002",
                "name": "program_execution_controller",
                "kind": "program_control",
                "authority_owner": "AUTH-001",
                "execution_mode": "program_control",
                "repository_id": None,
                "source_of_truth": "controller_runtime_state",
                "environments": ["local"],
                "mutability": "controlled",
                "expected_revision": "UNKNOWN",
                "adapter": "controller",
            },
        ],
        "authorities": [
            {
                "id": "AUTH-001",
                "responsibility": "program_definition_and_convergence_verdict",
                "owner": owner,
            },
            {
                "id": "AUTH-002",
                "responsibility": "architecture_source_semantics",
                "owner": owner,
            },
            {
                "id": "AUTH-003",
                "responsibility": "target_repository_implementation",
                "owner": owner,
            },
        ],
        "evidence_requirements": evidence_requirements,
        "decisions": decisions,
        "unknowns": _unknowns(unknown_items, discovery_by_section, by_unit, owner),
        "risks": risks,
        "waivers": [],
        "prohibited_paths": prohibited_paths,
        "workstreams": workstreams,
        "dependency_edges": edges,
        "waves": waves,
        "tasks": tasks,
        "gates": gates,
        "observability": {
            "program_progress_fields": [
                "tasks_completed",
                "gates_passed",
                "validations_run",
                "coverage_status",
            ]
        },
        "cutover_and_rollback": {
            "preconditions": ["accepted_blueprint", "all_blocking_gates_passed"],
            "rollback_rules": [
                "restore_worktree_to_program_lock_base",
                "preserve_task_receipts_and_evidence",
            ],
        },
        "intent_provenance": provenance,
    }
    _refuse_placeholders(source)
    return LoweredCampaign(
        source=source,
        coverage=coverage,
        mappings=mappings,
        task_count=len(tasks),
        prohibition_count=len(prohibited_paths),
        validation_count=validation_count,
    )


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def build_provenance(
    intent: ArchitectureIntent,
    extraction: ExtractionResult,
    *,
    coverage: CoverageReport,
    mappings: dict[str, list[dict[str, Any]]],
    campaign_id: str,
) -> dict[str, Any]:
    """The record that makes the mapping re-checkable after the fact.

    Digest plus the unit ledger, not the document body: a tampered campaign
    source can then be caught by recomputation rather than by trusting a copy of
    the prose that the same edit could have changed.
    """
    return {
        "schema": INTENT_PROVENANCE_SCHEMA,
        "campaign_id": campaign_id,
        "target": intent.target,
        "source": {
            "path": str(intent.path),
            "sha256": intent.sha256,
            "media_type": intent.media_type,
            "title": intent.title,
        },
        "extractor": {
            "id": extraction.extractor_id or "unknown",
            "protocol": "l9.program-execution.architecture-extractor-response.v1",
            "chunks": extraction.chunks,
            "repair_rounds": extraction.repair_rounds,
            "critic_rounds": extraction.critic_rounds,
        },
        "source_units": [entry.to_dict() for entry in coverage.dispositions],
        "semantic_items": [
            {**item.to_dict(), "campaign_mappings": mappings.get(item.id, [])}
            for item in extraction.items
        ],
        "rejected_items": [item.to_dict() for item in extraction.rejected],
        "contradictions": [entry.to_dict() for entry in extraction.contradictions],
        "coverage": coverage.to_dict(),
    }


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _clip(text: str, limit: int = _STATEMENT_LIMIT) -> str:
    flat = re.sub(r"\s+", " ", (text or "").strip())
    flat = _PLACEHOLDER_RE.sub("", flat).strip()
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rsplit(" ", 1)[0] + "…"


def _refuse_placeholders(source: dict[str, Any]) -> None:
    blob = json.dumps(source, ensure_ascii=False)
    match = _PLACEHOLDER_RE.search(blob)
    if match:
        raise LoweringError(
            f"generated campaign source carries an unresolved placeholder {match.group(0)}"
        )


def _action(item: SemanticItem) -> str:
    hint = f" ({_clip(item.implementation_hint, 120)})" if item.implementation_hint else ""
    return _clip(f"{item.statement}{hint}")


def _objective_text(
    intent: ArchitectureIntent,
    objectives: Sequence[SemanticItem],
    requirements: Sequence[SemanticItem],
) -> str:
    if objectives:
        return _clip(" ".join(item.statement for item in objectives), 900)
    lead = "; ".join(_clip(item.statement, 160) for item in requirements[:4])
    return _clip(
        f"Implement the architecture stated in {intent.title}: {lead}",
        900,
    )


def _problem_statement(
    intent: ArchitectureIntent, requirements: Sequence[SemanticItem], facts: RepositoryFacts
) -> str:
    return _clip(
        f"{facts.repository_id} does not yet satisfy the architecture recorded in "
        f"{intent.path.name} (sha256 {intent.sha256[:12]}). The source states "
        f"{len(requirements)} material obligations that current behavior does not fully honor; "
        "the difference between them is this program's work.",
        900,
    )


def _target_state(intent: ArchitectureIntent, requirements: Sequence[SemanticItem]) -> str:
    return _clip(
        "Every material obligation in the architecture source is implemented, validated by a "
        "repository-native command or inspection, and traceable to the source unit that states "
        f"it. {len(requirements)} obligations are in scope.",
        900,
    )


def _scope_include(
    scope_items: Sequence[SemanticItem], tasks: Sequence[dict[str, Any]]
) -> list[str]:
    include = [_clip(item.statement, 160) for item in scope_items]
    include.extend(f"{task['id']}: {task['title']}" for task in tasks)
    return list(dict.fromkeys(include)) or ["Implement the architecture source."]


def _scope_exclude(
    scope_items: Sequence[SemanticItem], prohibitions: Sequence[SemanticItem]
) -> list[str]:
    exclude = [_clip(item.statement, 160) for item in scope_items]
    exclude.extend(_clip(item.statement, 160) for item in prohibitions)
    exclude.extend(["remote mutation", "merge", "deploy"])
    return list(dict.fromkeys(exclude))


def _task_objective(section: Section, drivers: Sequence[SemanticItem]) -> str:
    body = " ".join(_clip(item.statement, 200) for item in drivers[:6])
    return _clip(f"{section.title}. {body}", 900)


def _task_acceptance(
    task_id: str, acceptance_items: Sequence[SemanticItem], drivers: Sequence[SemanticItem]
) -> list[dict[str, Any]]:
    suffix = task_id.split("-")[-1]
    if acceptance_items:
        return [
            {
                "id": f"AC-{suffix}-{index:02d}",
                "statement": _clip(item.statement),
                "required_evidence_types": ["test_result", "inspection"],
            }
            for index, item in enumerate(acceptance_items, start=1)
        ]
    return [
        {
            "id": f"AC-{suffix}",
            "statement": _clip(
                "The implementation satisfies every obligation this task carries: "
                + "; ".join(_clip(item.statement, 160) for item in drivers[:4])
            ),
            "required_evidence_types": ["test_result", "inspection"],
        }
    ]


def _task_negative_cases(prohibitions: Sequence[SemanticItem]) -> list[str]:
    cases = [_clip(f"violates: {item.statement}", 200) for item in prohibitions]
    cases.extend(["scope_expansion", "remote_mutation_before_release"])
    return list(dict.fromkeys(cases))


def _resolve_paths(items: Sequence[SemanticItem], facts: RepositoryFacts) -> list[str]:
    """Prefer paths the repository actually has; keep new ones the source names."""
    existing: list[str] = []
    proposed: list[str] = []
    for item in items:
        for candidate in item.suggested_paths:
            cleaned = candidate.strip().lstrip("./")
            if not cleaned or cleaned in existing or cleaned in proposed:
                continue
            (existing if facts.path_exists(cleaned) else proposed).append(cleaned)
    return (existing + proposed)[:24]


def _resolve_validation(
    validation_items: Sequence[SemanticItem],
    facts: RepositoryFacts,
    paths: Sequence[str],
) -> list[dict[str, Any]]:
    """Exact source command → repository-native command → focused inspection.

    Never a placeholder. A task whose correctness the source describes without
    giving a command still gets something a verifier can actually run or read.
    """
    resolved: list[dict[str, Any]] = []

    def add(command: str, evidence: str) -> None:
        if any(entry.get("command_or_inspection") == command for entry in resolved):
            return
        resolved.append(
            {
                "check": command,
                "method": "command",
                "command": command,
                # The Task Card carries `command_or_inspection`; emitting only
                # `command` is how a seed's validations silently became
                # inspection stubs with nothing for pec verify to run.
                "command_or_inspection": command,
                "environment": "local",
                "evidence": evidence,
            }
        )

    for item in validation_items:
        for command in item.suggested_tests:
            add(command, f"architecture source {', '.join(item.source_refs)}")
    for command in facts.validation_commands:
        add(command, "repository-native validation command")
    if not resolved:
        subject = ", ".join(paths[:4]) or "the declared task paths"
        statement = (
            f"Inspect {subject} and confirm each stated obligation is implemented as written, "
            "with no obligation left unimplemented."
        )
        resolved.append(
            {
                "check": "implementation inspection",
                "method": "inspection",
                "command_or_inspection": statement,
                "environment": "local",
                "evidence": "inspection of the finished tree",
            }
        )
    return resolved[:6]


def _task(
    *,
    task_id: str,
    title: str,
    objective: str,
    actions: Sequence[str],
    acceptance: Sequence[dict[str, Any]],
    validation: Sequence[dict[str, Any]],
    negative_cases: Sequence[str],
    paths: Sequence[str],
    read_only: bool,
    input_evidence_ids: Sequence[str],
    target_id: str,
    workstream_id: str,
) -> dict[str, Any]:
    declared_paths = list(paths)
    unknown_seam = not read_only and not declared_paths
    # Unknown implementation seam is a discovery dependency, not a fabricated
    # docs/program-execution/<TASK>.md write target.
    inspection_only = read_only or unknown_seam
    return {
        "id": task_id,
        "title": title,
        # ADR-0023 §1: a complete definition is ready. Ordering is the graph's job.
        "definition_status": "ready",
        "workstream_id": workstream_id,
        "wave_id": "W0",
        "target_id": target_id,
        "execution_kind": "read_only" if inspection_only else "repo_local",
        "objective": objective,
        "authority_basis_ids": ["AUTH-002" if inspection_only else "AUTH-003"],
        "required_decision_ids": [],
        # Empty: unknown seam is scheduled as inspection, not a blocked
        # reference the Blueprint validator cannot resolve (ADR-0023 §5).
        "blocking_unknown_ids": [],
        "input_evidence_ids": list(input_evidence_ids),
        "paths": declared_paths,
        "actions": list(actions),
        "acceptance": list(acceptance),
        "validation": list(validation),
        "negative_cases": list(negative_cases),
        "rollback": {
            "strategy": "discard_uncommitted_or_revert_local_commit",
            "trigger": "validation_failure",
            "validation": "worktree_matches_prior_head",
        },
        "risk": {
            "tier": "T0",
            "reversibility": "fully_reversible",
            "blast_radius": "inspection_only" if inspection_only else "declared_paths",
        },
        "authorization_ceiling": {
            "inspect": True,
            "local_write": not inspection_only,
            "commit": not inspection_only,
            "push": False,
            "pull_request": False,
            "merge": False,
            "publish_or_release": False,
            "deploy_or_migrate": False,
            "destructive_change": False,
            "external_message": False,
        },
        "completion_gate_ids": [],
    }


def _adopt_orphans(
    items: Sequence[SemanticItem],
    mappings: dict[str, list[dict[str, Any]]],
    tasks: Sequence[dict[str, Any]],
    impl_by_section: dict[int, dict[str, Any]],
    by_unit: dict[str, int],
    map_item: Any,
) -> None:
    """Attach material items whose section produced no task of its own.

    An architecture states acceptance in one section and the work it accepts in
    another all the time. Dropping those would show up as a coverage failure,
    which is correct but useless: the obligation belongs on the nearest task, so
    that is where it goes.
    """
    if not tasks:
        return
    fallback = next(
        (task for task in tasks if task["workstream_id"] != "WS-02"),
        tasks[0],
    )

    def nearest(item: SemanticItem) -> dict[str, Any]:
        if not impl_by_section:
            return fallback
        target_section = _section_of(item, by_unit)
        best = min(impl_by_section, key=lambda index: (abs(index - target_section), index))
        return impl_by_section[best]

    for item in items:
        if not item.executable or mappings.get(item.id):
            continue
        task = nearest(item)
        suffix = task["id"].split("-")[-1]
        if item.kind == "validation":
            entry: dict[str, Any] = {
                "check": _clip(item.statement, 200),
                "environment": "local",
                "evidence": f"architecture source {', '.join(item.source_refs)}",
            }
            if item.suggested_tests:
                entry["method"] = "command"
                entry["command"] = item.suggested_tests[0]
                entry["command_or_inspection"] = item.suggested_tests[0]
            else:
                entry["method"] = "inspection"
                entry["command_or_inspection"] = _clip(item.statement, 300)
            task.setdefault("validation", []).append(entry)
            map_item(item.id, "task_validation", task_id=task["id"])
        elif item.kind == "acceptance":
            task.setdefault("acceptance", []).append(
                {
                    "id": f"AC-{suffix}-{len(task['acceptance']) + 1:02d}",
                    "statement": _clip(item.statement),
                    "required_evidence_types": ["test_result", "inspection"],
                }
            )
            map_item(item.id, "task_acceptance", task_id=task["id"])
        elif item.kind == "file_seam":
            for candidate in item.suggested_paths:
                cleaned = candidate.strip().lstrip("./")
                if cleaned and cleaned not in task["paths"]:
                    task["paths"].append(cleaned)
            map_item(item.id, "task_path", task_id=task["id"])
        else:
            task.setdefault("actions", []).append(_action(item))
            map_item(item.id, "task_action", task_id=task["id"])


def _dependency_edges(
    discovery_by_section: dict[int, str],
    impl_by_section: dict[int, dict[str, Any]],
    tasks: Sequence[dict[str, Any]],
) -> list[dict[str, str]]:
    """Discovery precedes the work that consumes it; sections stay ordered.

    This is where "we must first determine X" becomes a ready evidence task with
    the implementation edged behind it, instead of a task marked blocked. The
    edge is drawn from the section the question was asked in to the task that
    section produced — never from a positional guess, which pointed the evidence
    at whichever task happened to sit at the same index.
    """
    edges: list[dict[str, str]] = []
    ordered_sections = sorted(impl_by_section)
    first_impl = impl_by_section[ordered_sections[0]]["id"] if ordered_sections else None
    for section_index, discovery_id in sorted(discovery_by_section.items()):
        owner = impl_by_section.get(section_index)
        if owner is None:
            # The question was asked in a section that produced no task of its
            # own; the nearest following section that did is what consumes it.
            following = [index for index in ordered_sections if index > section_index]
            dependent = impl_by_section[following[0]]["id"] if following else first_impl
        else:
            dependent = owner["id"]
        if dependent and dependent != discovery_id:
            edges.append({"from": discovery_id, "to": dependent})
    previous: str | None = None
    for section_index in ordered_sections:
        current = impl_by_section[section_index]["id"]
        if previous is not None:
            edges.append({"from": previous, "to": current})
        previous = current
    known = {task["id"] for task in tasks}
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for edge in edges:
        key = (edge["from"], edge["to"])
        if key in seen or edge["from"] == edge["to"]:
            continue
        if edge["from"] not in known or edge["to"] not in known:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


def _waves(
    tasks: Sequence[dict[str, Any]], edges: Sequence[dict[str, str]]
) -> list[dict[str, Any]]:
    """Topological levels. Waves are ordering; definition status never is."""
    ids = [task["id"] for task in tasks]
    incoming: dict[str, set[str]] = {task_id: set() for task_id in ids}
    for edge in edges:
        if edge["to"] in incoming and edge["from"] in incoming:
            incoming[edge["to"]].add(edge["from"])
    levels: list[list[str]] = []
    placed: set[str] = set()
    remaining = list(ids)
    while remaining:
        layer = [task_id for task_id in remaining if incoming[task_id] <= placed]
        if not layer:
            # A cycle cannot order itself; keep the remainder in one wave rather
            # than dropping tasks or inventing an order the source never stated.
            layer = list(remaining)
        levels.append(layer)
        placed.update(layer)
        remaining = [task_id for task_id in remaining if task_id not in placed]
    waves: list[dict[str, Any]] = []
    for index, layer in enumerate(levels):
        waves.append(
            {
                "id": f"W{index}",
                "name": f"wave_{index}",
                "task_ids": layer,
                "predecessor_wave_ids": [f"W{index - 1}"] if index else [],
                "exit_gate_ids": [],
            }
        )
    return waves


def _gates(
    waves: Sequence[dict[str, Any]], tasks: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {task["id"]: task for task in tasks}
    gates: list[dict[str, Any]] = []
    for index, wave in enumerate(waves, start=1):
        gate_id = f"GATE-{index:03d}"
        criteria = [
            _clip(
                f"{task_id} acceptance is met: {by_id[task_id]['acceptance'][0]['statement']}", 300
            )
            for task_id in wave["task_ids"]
            if task_id in by_id
        ]
        gates.append(
            {
                "id": gate_id,
                "name": f"{wave['name']}_complete",
                "gate_type": "completion",
                "blocking": True,
                "owner_authority_id": "AUTH-001",
                "task_ids": list(wave["task_ids"]),
                "required_evidence_ids": [],
                "pass_criteria": criteria or ["Wave tasks are complete."],
                "failure_effect": "block_successor_tasks",
            }
        )
    return gates


def _unknowns(
    unknown_items: Sequence[SemanticItem],
    discovery_by_section: dict[int, str],
    by_unit: dict[str, int],
    owner: str,
) -> list[dict[str, Any]]:
    """Record the questions, but never as blockers of ordinary work.

    Each one is answered by a ready evidence task, so `blocking_task_ids` stays
    empty: the dependency edge carries the ordering, and ADR-0023 keeps
    `blocked` for genuine inability to proceed.
    """
    unknowns: list[dict[str, Any]] = []
    for index, item in enumerate(unknown_items, start=1):
        section = _section_of(item, by_unit)
        task_id = discovery_by_section.get(section)
        unknowns.append(
            {
                "id": f"UNK-{index:03d}",
                "statement": _clip(item.statement),
                "owner": owner,
                "status": "open",
                "resolution_method": (
                    f"Read-only repository inspection performed by {task_id}."
                    if task_id
                    else "Read-only repository inspection during the first wave."
                ),
                "resolution_evidence_ids": [],
                # Empty on purpose: a probeable question is scheduled work, not
                # a blocker (ADR-0023 §5).
                "blocking_task_ids": [],
                "source_refs": list(item.source_refs),
                "semantic_id": item.id,
            }
        )
    return unknowns


__all__ = [
    "CAMPAIGN_SOURCE_SCHEMA",
    "LoweredCampaign",
    "LoweringError",
    "RepositoryFacts",
    "Section",
    "build_provenance",
    "inspect_repository",
    "lower",
    "sections_for",
    "utc_now",
]
