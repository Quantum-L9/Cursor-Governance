from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SOURCE = PE_ROOT / "campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml"
EXPECTED_DIGEST = "9528abeaf8117dd0598036216784593a62e88948800636c2eced9dc6262ae010"
PEC_CLI = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"


def _pass_proof(
    path: Path,
    campaign_id: str = "bounded-replanning-v1",
    tools: list | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "l9.program-execution.stack-proof.v1",
                "campaign_id": campaign_id,
                "status": "pass",
                "tools": tools or [],
                "fetched_at": "2026-08-16T00:00:00Z",
                "validator": {"ok": True, "errors": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


# bounded-replanning-v1 declares six repo_local tasks that permit local_write and
# name no writable path. That shape used to compile, silently receiving a
# fabricated `docs/program-execution/TASK-00N.md` output; it is now refused, so
# these tests declare the scope the fixture omits. The checked-in source is
# digest-pinned and is deliberately left alone.
_FIXTURE_WRITABLE_PATHS = {
    "TASK-001": ["docs/program-execution/notes/task-001.md"],
    "TASK-002": ["docs/program-execution/notes/task-002.md"],
    "TASK-003": ["docs/program-execution/notes/task-003.md"],
    "TASK-004": ["docs/program-execution/notes/task-004.md"],
    "TASK-005": ["docs/program-execution/notes/task-005.md"],
    "TASK-006": ["docs/program-execution/notes/task-006.md"],
}


def _with_declared_scope(source: dict) -> dict:
    """Give every mutating fixture task the explicit writable scope it lacks."""
    for task in source.get("tasks") or []:
        declared = _FIXTURE_WRITABLE_PATHS.get(str(task.get("id")))
        if declared and not task.get("paths") and not task.get("outputs"):
            task["paths"] = list(declared)
    return source


def _scoped_source(directory: Path) -> Path:
    """Materialize the fixture with declared writable scope."""
    source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
    path = directory / "CAMPAIGN_SOURCE.yaml"
    path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    return path


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompileCampaignSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = _load(
            "compile_campaign_source_test",
            PE_ROOT / "scripts/compile_campaign_source.py",
        )
        self.validator = _load(
            "validate_blueprint_test",
            PE_ROOT / "core/program-execution-blueprint-template/scripts/validate_blueprint.py",
        )

    def test_source_digest_is_immutable(self) -> None:
        digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_DIGEST)

    def test_compile_forces_program_control_local_write_false(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "blueprint"
            proof = _pass_proof(Path(raw) / "stack-proof.json")
            scoped = _scoped_source(Path(raw))
            before = hashlib.sha256(scoped.read_bytes()).hexdigest()
            self.compiler.compile_source(scoped, target, stack_proof=proof)
            self.assertEqual(hashlib.sha256(scoped.read_bytes()).hexdigest(), before)
            self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), EXPECTED_DIGEST)
            tasks = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))[
                "tasks"
            ]
            task_007 = next(item for item in tasks if item["id"] == "TASK-007")
            self.assertEqual(task_007["execution_kind"], "program_control")
            self.assertFalse(task_007["authorization_ceiling"]["local_write"])
            errors = self.validator.validate(target, "template")
            self.assertEqual(errors, [], msg="\n".join(errors))

    def test_empty_evidence_requirements_still_template_valid(self) -> None:
        """Activate seeds omit evidence_requirements; GATE-* must not become SRC evidence."""
        synthesized = self.compiler._admission_evidence({"metadata": {"intended_host": "org/repo"}})
        self.assertEqual(synthesized[0]["id"], "EVID-001")
        existing = self.compiler._admission_evidence(
            {"evidence_requirements": [{"id": "EVID-009", "claim": "kept"}]}
        )
        self.assertEqual(existing[0]["id"], "EVID-009")

        activate_source = (
            Path.home()
            / ".l9/gov-worktrees/l9-ci-core-org-runtime-v1"
            / "environment/program-execution/campaigns"
            / "l9-ci-core-org-runtime-v1"
            / "CAMPAIGN_SOURCE.yaml"
        )
        if not activate_source.is_file():
            return
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            data = yaml.safe_load(activate_source.read_text(encoding="utf-8"))
            data["metadata"]["campaign_id"] = "bounded-replanning-v1"
            data["program"]["id"] = "bounded-replanning-v1"
            data["evidence_requirements"] = []
            source.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            target = Path(raw) / "blueprint"
            self.compiler.compile_source(
                source,
                target,
                stack_proof=_pass_proof(
                    Path(raw) / "stack-proof.json",
                    tools=[
                        {
                            "name": "upstream-api",
                            "constraints": ["language_name must be the full English name"],
                            "fetch_evidence": {
                                "http_status": 200,
                                "bytes": 80,
                                "digest": "sha256:abc",
                            },
                        }
                    ],
                ),
            )
            catalog = yaml.safe_load((target / "EVIDENCE_CATALOG.yaml").read_text(encoding="utf-8"))
            self.assertEqual(catalog["evidence"][0]["id"], "EVID-001")
            trace = yaml.safe_load(
                (target / "SOURCE_TRACEABILITY.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(trace["sources"][0]["evidence_id"], "EVID-001")
            errors = self.validator.validate(target, "template")
            self.assertEqual(errors, [], msg="\n".join(errors))

    def test_poison_language_name_refuses_compile(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            proof = Path(raw) / "stack-proof.json"
            proof.write_text(
                json.dumps(
                    {
                        "schema": "l9.program-execution.stack-proof.v1",
                        "campaign_id": "bounded-replanning-v1",
                        "status": "pass",
                        "tools": [
                            {
                                "name": "DataForSEO",
                                "constraints": ["language_name must be the full English name"],
                                "fetch_evidence": {
                                    "http_status": 200,
                                    "bytes": 80,
                                    "digest": "sha256:abc",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
            data["program"]["objective"] += ' language_name: "en"'
            source.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self.compiler.compile_source(source, Path(raw) / "out", stack_proof=proof)
            self.assertIn("language_name", str(ctx.exception))

    def test_new_campaign_id_compiles_without_preregistration(self) -> None:
        """A campaign compiles because it is valid, not because it was listed.

        This test used to assert the opposite: an unlisted id was refused even
        when the source was entirely valid. That made every new campaign wait on
        an edit to a shared registry, and made one campaign's registration a
        compile input of every other campaign.
        """
        with tempfile.TemporaryDirectory() as raw:
            # Through _scoped_source: the legacy fixture declares no writable
            # scope, which is now a source defect in its own right. The identity
            # under test is the campaign id, not the scope.
            scoped = _scoped_source(Path(raw))
            source = Path(raw) / "renamed.yaml"
            source.write_text(
                scoped.read_text(encoding="utf-8").replace(
                    "bounded-replanning-v1",
                    "never-preregistered-v1",
                ),
                encoding="utf-8",
            )
            target = Path(raw) / "out"
            result = self.compiler.compile_source(
                source,
                target,
                stack_proof=_pass_proof(Path(raw) / "stack-proof.json", "never-preregistered-v1"),
            )
            self.assertEqual(result["campaign_id"], "never-preregistered-v1")
            self.assertEqual(self.validator.validate(target, "template"), [])

    def test_compiler_has_no_allowlist_surface(self) -> None:
        """The preregistration path is gone, not merely unused."""
        self.assertFalse(hasattr(self.compiler, "load_allowlist"))
        self.assertFalse(hasattr(self.compiler, "ALLOWLIST_PATH"))
        source = (
            Path(__file__).resolve().parents[2] / "scripts/compile_campaign_source.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("--allowlist", source)

    def test_decisions_without_options_fail_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
            data["decisions"][0].pop("options")
            source.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self.compiler.compile_source(
                    source,
                    Path(raw) / "out",
                    stack_proof=_pass_proof(Path(raw) / "stack-proof.json"),
                )
            self.assertIn("options", str(ctx.exception))

    def test_full_admission_loop_compile_collect_accept_bootstrap(self) -> None:
        """The closed loop: compile → collect → accept → bootstrap → validate."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            target = tmp / "blueprint"
            self.compiler.compile_source(
                _scoped_source(tmp),
                target,
                stack_proof=_pass_proof(tmp / "stack-proof.json"),
            )  # self-validates template mode

            # Execution completeness is solved pre-seal: launchability enriches
            # the Task Cards before acceptance, which is assertion-only. The
            # prepare pipeline runs this between compile and accept, so the
            # closed loop has to as well.
            launch = _load("launchability_loop_test", PE_ROOT / "scripts/launchability.py")
            launch_report = launch.check_tasks(launch.blueprint_tasks(target), tmp, infer=True)
            launch.apply_synthesized_validations(
                target, launch_report.get("synthesized_validations") or {}, validate=False
            )

            collect = _load("collect_evidence_test", PE_ROOT / "scripts/collect_evidence.py")
            # CP-F17: an evidence binding needs the revision it was observed at.
            with self.assertRaises(RuntimeError) as unbound:
                collect.collect_evidence(
                    target,
                    evidence_id="EVID-001",
                    revision=None,
                    digest=None,
                    notes="loop test",
                    producer="test",
                    expires_at=None,
                )
            self.assertIn("revision", str(unbound.exception))
            collected = collect.collect_evidence(
                target,
                evidence_id="EVID-001",
                revision="rev-1",
                digest=None,
                notes="loop test",
                producer="test",
                expires_at=None,
            )
            self.assertEqual(collected["status"], "COLLECTED")

            accept = _load("accept_blueprint_test", PE_ROOT / "scripts/accept_blueprint.py")
            accepted = accept.accept_blueprint(target, actor="test", evidence_ids=["EVID-001"])
            self.assertEqual(accepted["status"], "ACCEPTED")
            self.assertTrue((target / "ACCEPTANCE_RECEIPT.yaml").is_file())

            workspace = tmp / "runtime"
            pec_env = os.environ.copy()
            pec_env.setdefault("L9_ALLOW_PEC_DIRECT", "1")
            subprocess.run(
                [
                    sys.executable,
                    str(PEC_CLI),
                    "bootstrap",
                    "--workspace",
                    str(workspace),
                    "--blueprint",
                    str(target),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=pec_env,
            )
            validated = subprocess.run(
                [sys.executable, str(PEC_CLI), "validate", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertEqual(json.loads(validated.stdout)["status"], "PASS")

    def test_every_declared_path_becomes_an_output(self) -> None:
        """The sealed contract must carry all writable paths, not just the first."""
        self.assertEqual(
            self.compiler._task_output_locations(
                {
                    "id": "TASK-001",
                    "paths": [
                        "environment/contracts/execution/adr/ADR-0023.md",
                        "docs/decisions/ADR-0023.md",
                    ],
                }
            ),
            [
                "environment/contracts/execution/adr/ADR-0023.md",
                "docs/decisions/ADR-0023.md",
            ],
        )
        self.assertEqual(
            self.compiler._task_output_locations(
                {
                    "id": "TASK-002",
                    "outputs": [{"location": "receipts/internal.json"}, {"location": "a.md"}],
                    "paths": ["a.md", "b.md"],
                }
            ),
            ["a.md", "b.md"],
        )
        self.assertEqual(
            self.compiler._task_output_locations({"id": "TASK-009"}),
            ["docs/program-execution/TASK-009.md"],
        )

    def test_compiled_task_cards_keep_multi_path_outputs(self) -> None:
        source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
        task = source["tasks"][0]
        task["paths"] = ["docs/one.md", "docs/two.md"]
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            target = Path(raw) / "blueprint"
            self.compiler.compile_source(
                path, target, stack_proof=_pass_proof(Path(raw) / "stack-proof.json")
            )
            cards = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
            compiled = next(item for item in cards["tasks"] if item["id"] == task["id"])
            self.assertEqual(
                [output["location"] for output in compiled["outputs"]],
                ["docs/one.md", "docs/two.md"],
            )
            self.assertEqual(len({output["id"] for output in compiled["outputs"]}), 2)
            errors = self.validator.validate(target, "template")
            self.assertEqual(errors, [], msg="\n".join(errors))

    def test_declared_validation_commands_reach_the_task_card(self) -> None:
        """Flattening to inspection dropped the command and verify ran nothing."""
        entries = self.compiler._task_validations(
            {
                "id": "TASK-001",
                "acceptance": [{"statement": "unused fallback"}],
                "validation": [
                    {
                        "id": "VAL-001",
                        "method": "command",
                        "command_or_inspection": "python3 -m unittest tests/test_x.py",
                        "expected_result": "PASS",
                    }
                ],
            },
            "001",
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["method"], "command")
        self.assertEqual(entries[0]["command_or_inspection"], "python3 -m unittest tests/test_x.py")
        self.assertEqual(entries[0]["environment"], "local")

    def test_validation_falls_back_to_acceptance_when_undeclared(self) -> None:
        entries = self.compiler._task_validations(
            {"id": "TASK-001", "acceptance": [{"statement": "the deliverable exists"}]}, "001"
        )
        self.assertEqual(entries[0]["method"], "inspection")
        self.assertEqual(entries[0]["command_or_inspection"], "the deliverable exists")

    def test_legacy_blocked_canonicalizes_to_ready_from_dependency_edges_alone(self) -> None:
        """ADR-0023 A1: sequencing-only legacy `blocked` compiles as `ready`.

        The predecessor is expressed only as a top-level `dependency_edges`
        entry and the task carries no ordering alias, so the canonicalization
        is proved to follow the canonical DAG and nothing else.
        """
        source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
        task = next(item for item in source["tasks"] if item["id"] == "TASK-002")
        task["definition_status"] = "blocked"
        self.assertNotIn("dependencies", task)
        self.assertNotIn("dependency_ids", task)
        self.assertIn(
            ("TASK-001", "TASK-002"),
            {(edge["from"], edge["to"]) for edge in source["dependency_edges"]},
        )
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            target = Path(raw) / "blueprint"
            result = self.compiler.compile_source(
                path, target, stack_proof=_pass_proof(Path(raw) / "stack-proof.json")
            )
            cards = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
            compiled = next(item for item in cards["tasks"] if item["id"] == "TASK-002")
            self.assertEqual(compiled["definition_status"], "ready")
            graph = yaml.safe_load((target / "DEPENDENCY_GRAPH.yaml").read_text(encoding="utf-8"))
            self.assertIn(
                ("TASK-001", "TASK-002"),
                {(edge["from"], edge["to"]) for edge in graph["edges"]},
            )
            self.assertTrue(
                any("TASK-002" in note and "canonicalized" in note for note in result["warnings"]),
                result["warnings"],
            )

    def test_task_local_dependency_aliases_are_refused(self) -> None:
        """`dependency_edges` is the sole DAG authority; an alias fails closed.

        The equivalent top-level edge is removed first, so the refusal cannot
        be satisfied by an edge the fixture already carried -- the alias is the
        only remaining statement of the ordering.
        """
        for alias in ("dependencies", "dependency_ids"):
            with self.subTest(alias=alias):
                source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
                source["dependency_edges"] = [
                    edge
                    for edge in source["dependency_edges"]
                    if not (edge["from"] == "TASK-001" and edge["to"] == "TASK-002")
                ]
                self.assertNotIn(
                    ("TASK-001", "TASK-002"),
                    {(edge["from"], edge["to"]) for edge in source["dependency_edges"]},
                )
                task = next(item for item in source["tasks"] if item["id"] == "TASK-002")
                task["definition_status"] = "blocked"
                task[alias] = ["TASK-001"]
                with self.assertRaises(self.compiler.CompileError) as ctx:
                    self.compiler.preflight_campaign_source_document(source)
                message = str(ctx.exception)
                self.assertIn(alias, message)
                self.assertIn("dependency_edges", message)

    def test_dependency_alias_is_refused_on_the_compile_path_too(self) -> None:
        """Preflight is not the only door; compile refuses the same shape."""
        source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
        source["tasks"][1]["dependency_ids"] = ["TASK-001"]
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            target = Path(raw) / "out"
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self.compiler.compile_source(
                    path, target, stack_proof=_pass_proof(Path(raw) / "stack-proof.json")
                )
            self.assertIn("dependency_ids", str(ctx.exception))
            self.assertFalse(target.exists(), "refused before the Blueprint tree was created")

    def test_blocked_without_dependencies_refuses_compilation(self) -> None:
        """ADR-0023 A2: `blocked` with nothing to wait on is a runtime dead-end."""
        source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
        task = next(item for item in source["tasks"] if item["id"] == "TASK-001")
        task["definition_status"] = "blocked"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self.compiler.compile_source(
                    path,
                    Path(raw) / "out",
                    stack_proof=_pass_proof(Path(raw) / "stack-proof.json"),
                )
            message = str(ctx.exception)
            self.assertIn("unclaimable", message)
            self.assertIn("dependencies/waves", message)
            self.assertIn("blocking_unknown_ids", message)

    def test_declared_remote_authority_narrows_to_false_in_the_task_card(self) -> None:
        """A legacy source declaring push/pull_request still compiles -- as false.

        The sealed runner reaches neither, so a Task Card advertising them
        would hand every downstream surface an authority nothing can exercise.
        """
        source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
        declared = source["tasks"][0]["authorization_ceiling"]
        self.assertTrue(declared["push"], "fixture must declare the legacy shape")
        self.assertTrue(declared["pull_request"])
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            target = Path(raw) / "blueprint"
            self.compiler.compile_source(
                path, target, stack_proof=_pass_proof(Path(raw) / "stack-proof.json")
            )
            cards = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
        for card in cards["tasks"]:
            ceiling = card["authorization_ceiling"]
            for action in self.compiler.PE_FORBIDDEN_ACTIONS:
                self.assertFalse(ceiling[action], msg=f"{card['id']}.{action}")

    def test_program_control_loses_commit_as_well_as_local_write(self) -> None:
        ceiling = self.compiler.effective_authorization_ceiling(
            {
                "id": "TASK-007",
                "execution_kind": "program_control",
                "authorization_ceiling": {
                    "inspect": True,
                    "local_write": True,
                    "commit": True,
                },
            }
        )
        self.assertFalse(ceiling["local_write"])
        self.assertFalse(ceiling["commit"])

    def test_kernel_profile_round_trips_into_the_task_card(self) -> None:
        """BUILD / CHANGE / AUDIT survive lowering; omission defaults once."""
        for declared, expected in (
            ("BUILD", "BUILD"),
            ("CHANGE", "CHANGE"),
            ("AUDIT", "AUDIT"),
            (None, "BUILD"),
        ):
            with self.subTest(kernel_profile=declared):
                source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
                if declared is not None:
                    source["tasks"][0]["kernel_profile"] = declared
                with tempfile.TemporaryDirectory() as raw:
                    path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
                    path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
                    target = Path(raw) / "blueprint"
                    self.compiler.compile_source(
                        path, target, stack_proof=_pass_proof(Path(raw) / "stack-proof.json")
                    )
                    cards = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
                    errors = self.validator.validate(target, "template")
                    self.assertEqual(errors, [], msg="\n".join(errors))
                card = next(item for item in cards["tasks"] if item["id"] == "TASK-001")
                self.assertEqual(card["kernel_profile"], expected)

    def test_unknown_kernel_profile_is_refused(self) -> None:
        source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
        source["tasks"][0]["kernel_profile"] = "RELEASE"
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("RELEASE", str(ctx.exception))

    def test_ordering_alias_statuses_cannot_become_task_cards(self) -> None:
        """ADR-0023 A3: approval-shaped statuses are not task-ordering states."""
        for alias in ("pending", "advisory", "awaiting_approval", "not_approved"):
            with self.subTest(alias=alias):
                source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
                source["tasks"][1]["definition_status"] = alias
                with tempfile.TemporaryDirectory() as raw:
                    path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
                    path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
                    with self.assertRaises(self.compiler.CompileError) as ctx:
                        self.compiler.compile_source(
                            path,
                            Path(raw) / "out",
                            stack_proof=_pass_proof(Path(raw) / "stack-proof.json"),
                        )
                    self.assertIn(alias, str(ctx.exception))

    def test_compiled_blueprint_requires_the_declared_command(self) -> None:
        source = _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))
        task = source["tasks"][0]
        task["validation"] = [
            {
                "id": "VAL-001",
                "method": "command",
                "command_or_inspection": "python3 -m unittest discover tests",
                "expected_result": "PASS",
            }
        ]
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            target = Path(raw) / "blueprint"
            self.compiler.compile_source(
                path, target, stack_proof=_pass_proof(Path(raw) / "stack-proof.json")
            )
            cards = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
            compiled = next(item for item in cards["tasks"] if item["id"] == task["id"])
            self.assertEqual(
                [entry["command_or_inspection"] for entry in compiled["validation"]],
                ["python3 -m unittest discover tests"],
            )
            errors = self.validator.validate(target, "template")
            self.assertEqual(errors, [], msg="\n".join(errors))


class SourcePreflightTests(unittest.TestCase):
    """Deterministic source defects, caught before anything is created."""

    def setUp(self) -> None:
        self.compiler = _load(
            "compile_campaign_source_preflight",
            PE_ROOT / "scripts/compile_campaign_source.py",
        )

    def _source(self) -> dict:
        return _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))

    def _mutating_task(self, source: dict) -> dict:
        return next(
            item
            for item in source["tasks"]
            if (item.get("authorization_ceiling") or {}).get("local_write")
            and item.get("execution_kind") != "program_control"
        )

    # --- Repair A: truthful mutation scope -------------------------------

    def test_mutating_task_without_writable_paths_fails_preflight(self) -> None:
        source = self._source()
        task = self._mutating_task(source)
        task["paths"] = []
        task.pop("outputs", None)
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        message = str(ctx.exception)
        self.assertIn(task["id"], message)
        self.assertIn("local_write", message)
        self.assertIn("no outputs[].location or paths[]", message)

    def test_no_docs_path_is_fabricated_for_a_mutating_task(self) -> None:
        with self.assertRaises(self.compiler.CompileError):
            self.compiler._task_output_locations(
                {
                    "id": "TASK-001",
                    "execution_kind": "repo_local",
                    "authorization_ceiling": {"local_write": True},
                }
            )

    def test_explicit_writable_scope_passes_and_is_carried_through(self) -> None:
        source = self._source()
        task = self._mutating_task(source)
        task["paths"] = ["ops/scripts/claude_projection.py"]
        task.pop("outputs", None)
        self.compiler.preflight_campaign_source_document(source)
        self.assertEqual(
            self.compiler._task_output_locations(task),
            ["ops/scripts/claude_projection.py"],
        )

    def test_program_control_keeps_the_receipt_fallback(self) -> None:
        """Non-mutating compatibility: local_write is removed at compile time."""
        self.assertEqual(
            self.compiler._task_output_locations(
                {
                    "id": "TASK-007",
                    "execution_kind": "program_control",
                    "authorization_ceiling": {"local_write": True},
                }
            ),
            ["docs/program-execution/TASK-007.md"],
        )

    def test_inspection_task_keeps_the_receipt_fallback(self) -> None:
        self.assertEqual(
            self.compiler._task_output_locations({"id": "TASK-009"}),
            ["docs/program-execution/TASK-009.md"],
        )

    # --- ID grammar, sourced from the Blueprint schemas -------------------

    def test_task_and_gate_id_patterns_come_from_the_blueprint_schemas(self) -> None:
        self.assertEqual(self.compiler.blueprint_task_id_pattern(), "^TASK-[0-9]{3,}$")
        self.assertEqual(self.compiler.blueprint_gate_id_pattern(), "^GATE-[0-9]{3,}$")

    def test_illegal_task_id_fails_preflight_without_renumbering(self) -> None:
        source = self._source()
        original = source["tasks"][0]["id"]
        source["tasks"][0]["id"] = "TASK-001A"
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("TASK-001A", str(ctx.exception))
        # The offending id is named, never silently rewritten.
        self.assertEqual(source["tasks"][0]["id"], "TASK-001A")
        self.assertNotEqual(source["tasks"][0]["id"], original)

    def _compile_dict(self, raw: Path, source: dict) -> None:
        path = raw / "CAMPAIGN_SOURCE.yaml"
        path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
        proof = _pass_proof(raw / "stack-proof.json")
        self.compiler.compile_source(path, raw / "out", stack_proof=proof)

    def test_failed_compile_leaves_no_partial_target(self) -> None:
        """CP-F15: the target only ever holds a validated tree."""
        source = self._source()
        source["gates"] = []
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "out"
            with self.assertRaises(self.compiler.CompileError):
                self._compile_dict(Path(raw), source)
            self.assertFalse(target.exists(), "a refused compile wrote a partial blueprint")
            self.assertEqual(
                [p.name for p in Path(raw).iterdir() if p.name.startswith(".out.")],
                [],
                "staging directories must not survive a refusal",
            )

    def test_failed_recompile_keeps_the_previous_blueprint(self) -> None:
        good = self._source()
        with tempfile.TemporaryDirectory() as raw:
            self._compile_dict(Path(raw), good)
            target = Path(raw) / "out"
            before = sorted(p.name for p in target.iterdir())
            bad = self._source()
            bad["gates"] = []
            with self.assertRaises(self.compiler.CompileError):
                self._compile_dict(Path(raw), bad)
            self.assertEqual(sorted(p.name for p in target.iterdir()), before)

    def test_decision_without_a_defined_authority_is_refused(self) -> None:
        """`AUTH-005` used to be minted for a decision that named no authority."""
        source = self._source()
        source["decisions"] = [
            {
                "id": "DEC-900",
                "title": "Unowned decision",
                "question": "Which option?",
                "status": "accepted",
                "options": [{"id": "OPT-1", "description": "only option"}],
                "selected_option_id": "OPT-1",
            }
        ]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self._compile_dict(Path(raw), source)
        self.assertIn("DEC-900", str(ctx.exception))
        self.assertIn("authority", str(ctx.exception))

    def test_decision_without_a_status_is_refused_before_any_write(self) -> None:
        """A status-less decision used to reach the register dump and die with KeyError."""
        source = self._source()
        authority = source["authorities"][0]["id"]
        source["decisions"] = [
            {
                "id": "DEC-901",
                "title": "Unstated decision",
                "question": "Which option?",
                "authority_id": authority,
                "options": [{"id": "OPT-1", "description": "only option"}],
                "selected_option_id": "OPT-1",
            }
        ]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self._compile_dict(Path(raw), source)
            self.assertFalse((Path(raw) / "out").exists(), "refusal must precede any write")
        self.assertIn("DEC-901", str(ctx.exception))
        self.assertIn("status", str(ctx.exception))

    def test_decision_status_comes_from_the_decision_register_schema(self) -> None:
        source = self._source()
        authority = source["authorities"][0]["id"]
        source["decisions"] = [
            {
                "id": "DEC-902",
                "title": "Mis-stated decision",
                "question": "Which option?",
                "status": "approved",
                "authority_id": authority,
                "options": [{"id": "OPT-1", "description": "only option"}],
                "selected_option_id": "OPT-1",
            }
        ]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self._compile_dict(Path(raw), source)
        self.assertIn("DEC-902", str(ctx.exception))
        self.assertIn("'approved'", str(ctx.exception))
        self.assertIn("accepted", str(ctx.exception))

    def test_source_without_gates_is_refused_not_given_gate_001(self) -> None:
        source = self._source()
        source["gates"] = []
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self._compile_dict(Path(raw), source)
        self.assertIn("no gates", str(ctx.exception))

    def test_illegal_gate_id_fails_preflight(self) -> None:
        source = self._source()
        gates = source.get("gates") or []
        if not gates:
            self.skipTest("fixture declares no gates")
        gates[0]["id"] = "GATE-001A"
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("GATE-001A", str(ctx.exception))

    def test_numeric_ids_of_three_or_more_digits_pass(self) -> None:
        import re

        pattern = re.compile(self.compiler.blueprint_task_id_pattern())
        for task_id in ("TASK-001", "TASK-008", "TASK-1000"):
            self.assertTrue(pattern.match(task_id), msg=task_id)
        for task_id in ("TASK-001A", "TASK-A01", "TASK-01"):
            self.assertFalse(pattern.match(task_id), msg=task_id)

    # --- Authority intersection ------------------------------------------

    def test_local_write_without_commit_fails_preflight(self) -> None:
        """PE has no terminal dirty-worktree mode, so the shape is unexecutable."""
        source = self._source()
        task = self._mutating_task(source)
        task["authorization_ceiling"]["commit"] = False
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        message = str(ctx.exception)
        self.assertIn(task["id"], message)
        self.assertIn("local_write", message)
        self.assertIn("commit", message)

    def test_local_write_without_commit_is_refused_before_any_side_effect(self) -> None:
        source = self._source()
        self._mutating_task(source)["authorization_ceiling"]["commit"] = False
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            target = Path(raw) / "out"
            with self.assertRaises(self.compiler.CompileError):
                self.compiler.compile_source(
                    path, target, stack_proof=_pass_proof(Path(raw) / "stack-proof.json")
                )
            self.assertFalse(target.exists())

    def test_commit_without_local_write_fails_preflight(self) -> None:
        """The commit boundary stages the task's own work; commit cannot float free."""
        source = self._source()
        task = self._mutating_task(source)
        task["authorization_ceiling"]["local_write"] = False
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("commit", str(ctx.exception))

    def test_program_control_ceiling_is_never_checked_for_consistency(self) -> None:
        """Compatibility: program_control loses both, so it can never conflict."""
        source = self._source()
        control = next(
            item for item in source["tasks"] if item["execution_kind"] == "program_control"
        )
        control["authorization_ceiling"]["local_write"] = True
        control["authorization_ceiling"]["commit"] = False
        self.compiler.preflight_campaign_source_document(source)

    # --- Target identity --------------------------------------------------

    def test_targets_array_owns_the_execution_repository(self) -> None:
        self.assertEqual(
            self.compiler.resolve_campaign_target_repository(self._source()),
            "Quantum-L9/Cursor-Governance",
        )

    def test_zero_declared_targets_is_refused(self) -> None:
        source = self._source()
        source["targets"] = []
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("targets[].repository_id", str(ctx.exception))

    def test_multiple_distinct_repository_targets_are_refused(self) -> None:
        source = self._source()
        second = dict(source["targets"][0])
        second["id"] = "TARGET-002"
        second["repository_id"] = "Quantum-L9/l9-ci-core"
        source["targets"].append(second)
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        message = str(ctx.exception)
        self.assertIn("multiple distinct", message)
        self.assertIn("Quantum-L9/l9-ci-core", message)

    def test_a_contradicting_target_alias_is_refused_naming_both_values(self) -> None:
        for alias, mutate in (
            (
                "program.target_repository_id",
                lambda src: src["program"].update({"target_repository_id": "other/repo"}),
            ),
            (
                "metadata.intended_host",
                lambda src: src["metadata"].update({"intended_host": "other/repo"}),
            ),
            (
                "target.repository_id",
                lambda src: src.update({"target": {"repository_id": "other/repo"}}),
            ),
        ):
            with self.subTest(alias=alias):
                source = self._source()
                mutate(source)
                with self.assertRaises(self.compiler.CompileError) as ctx:
                    self.compiler.preflight_campaign_source_document(source)
                message = str(ctx.exception)
                self.assertIn(alias, message)
                self.assertIn("other/repo", message)
                self.assertIn("Quantum-L9/Cursor-Governance", message)

    def test_an_empty_repository_id_target_is_not_a_second_identity(self) -> None:
        """program_control targets carry no repository and must not collide."""
        source = self._source()
        source["targets"].append(
            {"id": "TARGET-002", "kind": "program_control", "repository_id": None}
        )
        self.assertEqual(
            self.compiler.resolve_campaign_target_repository(source),
            "Quantum-L9/Cursor-Governance",
        )

    # --- Validation-command grammar --------------------------------------

    def test_composed_source_validation_command_fails_preflight(self) -> None:
        source = self._source()
        task = self._mutating_task(source)
        task["validation"] = [
            {
                "id": "VAL-001",
                "method": "command",
                "command_or_inspection": "grep -q x a.py && grep -q x b.py",
            }
        ]
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        message = str(ctx.exception)
        self.assertIn("VAL-001", message)
        self.assertIn("compose multiple shell operations", message)

    def test_command_with_omitted_method_is_grammar_checked_at_preflight(self) -> None:
        """The seam: lowering executes it as shell, so preflight must read it as shell."""
        source = self._source()
        task = self._mutating_task(source)
        task["validation"] = [{"id": "VAL-001", "command": "grep -q x a.py && grep -q x b.py"}]
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        message = str(ctx.exception)
        self.assertIn("VAL-001", message)
        self.assertIn("compose multiple shell operations", message)
        # And the ledger lowering would have carried says the same thing.
        self.assertEqual(
            self.compiler.normalize_task_validation(task, "001")[0]["method"], "command"
        )

    def test_bare_command_or_inspection_without_method_is_also_shell(self) -> None:
        source = self._source()
        task = self._mutating_task(source)
        task["validation"] = [{"id": "VAL-001", "command_or_inspection": "python3 -c 'import os'"}]
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("VAL-001", str(ctx.exception))

    def test_an_unknown_validation_method_is_refused_not_coerced(self) -> None:
        source = self._source()
        task = self._mutating_task(source)
        task["validation"] = [
            {"id": "VAL-001", "method": "shell", "command_or_inspection": "git status --short"}
        ]
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        message = str(ctx.exception)
        self.assertIn("shell", message)
        self.assertIn("never coerced", message)

    def test_preflight_and_lowering_agree_on_every_normalized_entry(self) -> None:
        """One ledger, two readers: the two stages cannot reach different answers."""
        source = self._source()
        for task in source["tasks"]:
            suffix = task["id"].split("-")[-1]
            self.assertEqual(
                self.compiler.normalize_task_validation(task, suffix),
                self.compiler._task_validations(task, suffix),
            )

    def test_inspection_text_is_never_parsed_as_shell(self) -> None:
        """Prose is not a command; it must not reach the shell grammar."""
        source = self._source()
        task = self._mutating_task(source)
        task["validation"] = [
            {
                "id": "VAL-001",
                "method": "inspection",
                "command_or_inspection": "Reviewer confirms A && B, then checks > 3 cases",
            }
        ]
        self.compiler.preflight_campaign_source_document(source)

    def test_clean_source_passes_preflight(self) -> None:
        self.compiler.preflight_campaign_source_document(self._source())

    def test_preflight_does_not_mutate_the_source(self) -> None:
        import copy

        source = self._source()
        before = copy.deepcopy(source)
        self.compiler.preflight_campaign_source_document(source)
        self.assertEqual(source, before)


class DuplicateTaskIdTests(unittest.TestCase):
    """Two tasks with one id have no compiled representation and are refused at preflight."""

    def setUp(self) -> None:
        self.compiler = _load(
            "compile_campaign_source_duplicate_ids",
            PE_ROOT / "scripts/compile_campaign_source.py",
        )

    def _source(self) -> dict:
        return _with_declared_scope(yaml.safe_load(SOURCE.read_text(encoding="utf-8")))

    def test_an_exact_duplicate_task_id_fails_preflight(self) -> None:
        source = self._source()
        source["tasks"].append(dict(source["tasks"][0]))
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("duplicate task id 'TASK-001'", str(ctx.exception))

    def test_a_case_colliding_task_id_fails_preflight(self) -> None:
        source = self._source()
        twin = dict(source["tasks"][0])
        twin["id"] = "task-001"
        source["tasks"].append(twin)
        with self.assertRaises(self.compiler.CompileError) as ctx:
            self.compiler.preflight_campaign_source_document(source)
        self.assertIn("collides with 'TASK-001'", str(ctx.exception))
        self.assertIn("case-insensitively", str(ctx.exception))

    def test_the_compile_path_refuses_the_duplicate_too(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source()
            source["tasks"].append(dict(source["tasks"][-1]))
            path = root / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            proof = _pass_proof(root / "stack-proof.json")
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self.compiler.compile_source(path, root / "blueprint", stack_proof=proof)
            self.assertIn("duplicate task id", str(ctx.exception))
            self.assertFalse((root / "blueprint").exists())

    def test_distinct_ids_still_pass(self) -> None:
        self.compiler.preflight_campaign_source_document(self._source())


if __name__ == "__main__":
    unittest.main()
