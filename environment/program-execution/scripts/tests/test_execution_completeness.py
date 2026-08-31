"""Regression matrix for PEC Blueprint -> execution-completeness repairs.

These tests pin the ten-item batch only. They do not widen Program Execution
scope, create a second controller, or add an external-adapter runtime.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PE_ROOT / "scripts"
PEC_SCRIPTS = PE_ROOT / "core/program-execution-controller-template/scripts"
SCHEMAS = PE_ROOT / "core/program-execution-controller-template/schemas"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(PEC_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PEC_SCRIPTS))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


launchability = _load("pec_execution_completeness_launchability", SCRIPTS / "launchability.py")
run_campaign = _load("pec_execution_completeness_runner", SCRIPTS / "run_campaign.py")
accept_blueprint = _load("pec_execution_completeness_accept", SCRIPTS / "accept_blueprint.py")

from pec import blueprint as pec_blueprint  # noqa: E402
from pec import contracts as pec_contracts  # noqa: E402
from pec import replan as pec_replan  # noqa: E402
from pec import state as pec_state  # noqa: E402
from pec.common import digest_object  # noqa: E402


def _verification(method: str, text: str = "inspect output") -> dict[str, str]:
    return {
        "id": "VAL-001",
        "method": method,
        "command_or_inspection": text,
        "environment": "repo_local",
        "expected_result": "PASS",
    }


def _task(*, method: str, mutating: bool = True, execution_kind: str = "repo_local") -> dict:
    return {
        "id": "TASK-001",
        "title": "Task",
        "execution_kind": execution_kind,
        "definition_status": "ready",
        "authorization_ceiling": {
            "inspect": True,
            "local_write": mutating,
            "commit": False,
            "push": False,
            "pull_request": False,
            "merge": False,
            "publish_or_release": False,
            "deploy_or_migrate": False,
            "destructive_change": False,
            "external_message": False,
        },
        "validation": [_verification(method)],
        "outputs": [{"location": "docs/result.md"}],
    }


class NativeTaskCardAndTerminalVerifierTest(unittest.TestCase):
    def test_native_task_cards_are_the_launchability_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "TASK_CARDS.yaml").write_text(
                yaml.safe_dump({"tasks": [_task(method="command")]}, sort_keys=False),
                encoding="utf-8",
            )
            (root / "tasks.json").write_text(
                json.dumps({"tasks": [{"id": "LEGACY-ONLY"}]}), encoding="utf-8"
            )
            tasks = launchability.blueprint_tasks(root)
            self.assertEqual([item["id"] for item in tasks], ["TASK-001"])

    def test_mutating_repo_local_inspection_only_is_rejected(self) -> None:
        errors = launchability.terminal_verification_errors([_task(method="inspection")])
        self.assertEqual(len(errors), 1)
        self.assertIn("TASK-001", errors[0])

    def test_read_only_inspection_only_remains_valid(self) -> None:
        task = _task(method="inspection", mutating=False, execution_kind="read_only")
        self.assertEqual(launchability.terminal_verification_errors([task]), [])

    def test_external_adapter_is_terminal_but_not_shell_flattened(self) -> None:
        task = _task(method="external_adapter")
        self.assertEqual(launchability.terminal_verification_errors([task]), [])
        self.assertEqual(launchability.declared_validation_commands(task), [])
        self.assertEqual(
            launchability.declared_verification_mechanisms(task)[0]["method"],
            "external_adapter",
        )


class PreSealEnrichmentTest(unittest.TestCase):
    def _blueprint(self, root: Path, validation: list[dict]) -> Path:
        blueprint = root / "blueprint"
        blueprint.mkdir()
        task = _task(method="inspection")
        task["validation"] = validation
        (blueprint / "TASK_CARDS.yaml").write_text(
            yaml.safe_dump({"tasks": [task]}, sort_keys=False), encoding="utf-8"
        )
        (blueprint / "MANIFEST.yaml").write_text(
            "compiled_from: fixture\nfiles: {}\n", encoding="utf-8"
        )
        return blueprint

    @staticmethod
    def _ops(*, errors: list[str] | None = None):
        def write_manifest(root: Path, compiled_from: str) -> None:
            (root / "MANIFEST.yaml").write_text(
                f"compiled_from: {compiled_from}\nfiles:\n  TASK_CARDS.yaml: refreshed\n",
                encoding="utf-8",
            )

        return types.SimpleNamespace(
            lock_exists_for_blueprint=lambda root: False,
            validate_blueprint=lambda root, mode: list(errors or []),
            write_manifest=write_manifest,
        )

    def test_enrichment_appends_and_validates_without_destroying_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declared = _verification("inspection", "inspect the generated file")
            blueprint = self._blueprint(Path(raw), [declared])
            with patch.dict(sys.modules, {"blueprint_ops": self._ops()}):
                changed = launchability.apply_synthesized_validations(
                    blueprint,
                    {"TASK-001": ["test -s docs/result.md"]},
                    validate=True,
                )
            doc = yaml.safe_load((blueprint / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
            entries = doc["tasks"][0]["validation"]
            self.assertEqual(changed, ["TASK-001"])
            self.assertEqual(entries[0], declared)
            self.assertEqual(entries[1]["method"], "command")
            self.assertEqual(entries[1]["command_or_inspection"], "test -s docs/result.md")
            manifest = yaml.safe_load((blueprint / "MANIFEST.yaml").read_text(encoding="utf-8"))
            self.assertEqual(manifest["compiled_from"], "fixture")

    def test_failed_canonical_validation_rolls_back_cards_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = self._blueprint(Path(raw), [_verification("inspection")])
            cards_before = (blueprint / "TASK_CARDS.yaml").read_bytes()
            manifest_before = (blueprint / "MANIFEST.yaml").read_bytes()
            with patch.dict(sys.modules, {"blueprint_ops": self._ops(errors=["bad Blueprint"])}):
                with self.assertRaises(launchability.LaunchabilityError):
                    launchability.apply_synthesized_validations(
                        blueprint,
                        {"TASK-001": ["test -s docs/result.md"]},
                        validate=True,
                    )
            self.assertEqual((blueprint / "TASK_CARDS.yaml").read_bytes(), cards_before)
            self.assertEqual((blueprint / "MANIFEST.yaml").read_bytes(), manifest_before)

    def test_launchability_report_is_outside_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = Path(raw) / "blueprints" / "campaign-a"
            blueprint.mkdir(parents=True)
            report = launchability.launchability_report_path(blueprint)
            self.assertFalse(report.is_relative_to(blueprint))
            self.assertEqual(report.name, "campaign-a.json")


class AcceptanceBoundaryTest(unittest.TestCase):
    def test_acceptance_rejects_mutating_inspection_only_before_program_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            program = {"program": {"definition_status": "draft"}}
            (root / "PROGRAM.yaml").write_text(
                yaml.safe_dump(program, sort_keys=False), encoding="utf-8"
            )
            (root / "TASK_CARDS.yaml").write_text(
                yaml.safe_dump({"tasks": [_task(method="inspection")]}, sort_keys=False),
                encoding="utf-8",
            )
            before = (root / "PROGRAM.yaml").read_bytes()
            with self.assertRaises(RuntimeError) as ctx:
                accept_blueprint.accept_blueprint(root, actor="test", evidence_ids=["EVID-001"])
            self.assertIn("execution completeness failed before acceptance", str(ctx.exception))
            self.assertEqual((root / "PROGRAM.yaml").read_bytes(), before)


class TypedProjectionPersistenceTest(unittest.TestCase):
    @staticmethod
    def _db_task(mechanisms: list[dict]) -> dict:
        return {
            "id": "TASK-001",
            "title": "Task",
            "wave_id": "WAVE-001",
            "workstream_id": "WS-001",
            "target_id": "TARGET-001",
            "repository_id": "org/repo",
            "execution_kind": "repo_local",
            "objective": "Change one file",
            "dependencies": [],
            "required_decisions": [],
            "blocking_unknowns": [],
            "required_evidence": [],
            "completion_gates": ["GATE-001"],
            "authorization_ceiling": {
                "inspect": True,
                "local_write": True,
                "commit": False,
                "push": False,
                "pull_request": False,
                "merge": False,
                "publish_or_release": False,
                "deploy_or_migrate": False,
                "destructive_change": False,
                "external_message": False,
            },
            "required_acceptance": ["AC-001"],
            "verification_mechanisms": mechanisms,
            "required_validation_commands": [],
            "risk_tier": "T2",
            "definition_status": "ready",
        }

    def test_blueprint_lock_preserves_typed_verification_mechanisms(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            required = [
                "PROGRAM.yaml",
                "EXECUTION_TARGETS.yaml",
                "AUTHORITY_REGISTRY.yaml",
                "DECISION_REGISTER.yaml",
                "UNKNOWN_REGISTER.yaml",
                "RISK_REGISTER.yaml",
                "WAIVER_REGISTER.yaml",
                "EVIDENCE_CATALOG.yaml",
                "DO_NOT_BUILD.yaml",
                "CURRENT_STATE_DELTA.yaml",
                "WORKSTREAMS.yaml",
                "DEPENDENCY_GRAPH.yaml",
                "EXECUTION_WAVES.yaml",
                "TASK_CARDS.yaml",
                "CONVERGENCE_GATES.yaml",
                "OBSERVABILITY_PLAN.yaml",
                "CUTOVER_AND_ROLLBACK.yaml",
                "SOURCE_TRACEABILITY.yaml",
            ]
            docs = {
                "PROGRAM.yaml": {
                    "program": {
                        "contracts": {
                            "blueprint": "program-execution-blueprint.v2",
                            "pair": "program-execution-system.v2",
                        }
                    }
                },
                "EXECUTION_TARGETS.yaml": {
                    "targets": [{"id": "TARGET-001", "repository_id": "org/repo"}]
                },
                "AUTHORITY_REGISTRY.yaml": {},
                "DECISION_REGISTER.yaml": {"decisions": []},
                "UNKNOWN_REGISTER.yaml": {"unknowns": []},
                "RISK_REGISTER.yaml": {"risks": []},
                "WAIVER_REGISTER.yaml": {"waivers": []},
                "EVIDENCE_CATALOG.yaml": {"evidence": []},
                "DO_NOT_BUILD.yaml": {},
                "CURRENT_STATE_DELTA.yaml": {},
                "WORKSTREAMS.yaml": {"workstreams": []},
                "DEPENDENCY_GRAPH.yaml": {"edges": []},
                "EXECUTION_WAVES.yaml": {"waves": []},
                "TASK_CARDS.yaml": {
                    "tasks": [
                        {
                            "id": "TASK-001",
                            "title": "Task",
                            "definition_status": "ready",
                            "wave_id": "WAVE-001",
                            "workstream_id": "WS-001",
                            "target_id": "TARGET-001",
                            "execution_kind": "repo_local",
                            "objective": "Change one file",
                            "required_decision_ids": [],
                            "blocking_unknown_ids": [],
                            "input_evidence_ids": [],
                            "completion_gate_ids": ["GATE-001"],
                            "authorization_ceiling": {"inspect": True, "local_write": True},
                            "acceptance": [{"id": "AC-001"}],
                            "validation": [
                                _verification("external_adapter", "verify with adapter")
                            ],
                            "risk": {"tier": "T2"},
                        }
                    ]
                },
                "CONVERGENCE_GATES.yaml": {"gates": []},
                "OBSERVABILITY_PLAN.yaml": {},
                "CUTOVER_AND_ROLLBACK.yaml": {},
                "SOURCE_TRACEABILITY.yaml": {},
            }
            (root / "EXECUTION_INDEX.yaml").write_text(
                yaml.safe_dump(
                    {
                        "blueprint_contract": "program-execution-blueprint.v2",
                        "required_sources": required,
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            for name in required:
                (root / name).write_text(
                    yaml.safe_dump(docs[name], sort_keys=False), encoding="utf-8"
                )
            lock = pec_blueprint.normalize_blueprint(root)
            self.assertEqual(
                lock["tasks"][0]["verification_mechanisms"],
                [_verification("external_adapter", "verify with adapter")],
            )
            self.assertEqual(lock["tasks"][0]["required_validation_commands"], [])

    def test_state_db_persists_typed_verification_mechanisms(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = pec_state.StateDB(Path(raw) / "state.sqlite3")
            try:
                mechanisms = [_verification("external_adapter", "verify with adapter")]
                db.upsert_task(self._db_task(mechanisms))
                self.assertEqual(db.task("TASK-001")["verification_mechanisms"], mechanisms)
                columns = {
                    row["name"] for row in db.conn.execute("PRAGMA table_info(tasks)").fetchall()
                }
                self.assertIn("verification_mechanisms", columns)
            finally:
                db.close()

    def test_state_db_migrates_an_existing_tasks_table(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "state.sqlite3"
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY)")
            conn.commit()
            conn.close()
            # The real migration must add the column before any task read/write.
            db = pec_state.StateDB(path)
            try:
                columns = {
                    row["name"] for row in db.conn.execute("PRAGMA table_info(tasks)").fetchall()
                }
                self.assertIn("verification_mechanisms", columns)
            finally:
                db.close()

    def test_contract_schemas_require_typed_verification_mechanisms(self) -> None:
        for name in ("source-contract.schema.json", "task-contract.schema.json"):
            schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
            self.assertIn("verification_mechanisms", schema["required"])
            self.assertEqual(
                schema["properties"]["verification_mechanisms"]["items"]["properties"]["method"][
                    "enum"
                ],
                ["command", "inspection", "command_and_inspection", "external_adapter"],
            )

    def test_external_adapter_survives_state_to_source_to_rendered(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            (workspace / "runtime").mkdir(parents=True)
            mechanisms = [_verification("external_adapter", "verify with adapter")]
            task = self._db_task(mechanisms)
            task["authorization_ceiling"]["local_write"] = True
            db = pec_state.StateDB(workspace / "state.sqlite3")
            try:
                db.upsert_task(task)
                lock_task_source = {
                    "id": "TASK-001",
                    "outputs": [
                        {
                            "id": "OUT-001",
                            "type": "file",
                            "location": "docs/result.md",
                            "required": True,
                        }
                    ],
                    "rollback": {
                        "strategy": "restore previous file",
                        "trigger": "validation failure",
                        "validation": "git diff --exit-code",
                    },
                }
                (workspace / "runtime/program-lock.json").write_text(
                    json.dumps({"tasks": [{"id": "TASK-001", "source": lock_task_source}]}),
                    encoding="utf-8",
                )
                source_path = workspace / "source.json"
                pec_contracts.draft_source_contract(
                    db, "TASK-001", source_path, workspace=workspace
                )
                source = json.loads(source_path.read_text(encoding="utf-8"))
                self.assertEqual(source["verification_mechanisms"], mechanisms)
                self.assertEqual(source["validation_commands"], [])

                source_digest = digest_object(source)
                rendered_task = db.task("TASK-001")
                rendered_task.update(
                    {
                        "runtime_state": "PREPARED",
                        "source_contract_path": str(source_path),
                        "source_contract_digest": source_digest,
                    }
                )

                class FakeDB:
                    def __init__(self, task_data):
                        self.task_data = task_data

                    def task(self, task_id):
                        return self.task_data if task_id == "TASK-001" else None

                    def active_lease_for_task(self, task_id):
                        return {
                            "lease_id": "LEASE-001",
                            "base_sha": "a" * 40,
                            "branch": "pec/task-001",
                            "worktree": str(workspace / "worktree"),
                        }

                    def get_meta(self, key):
                        return "b" * 64

                    def next_attempt_number(self, task_id):
                        return 1

                    def update_task(self, task_id, **fields):
                        self.task_data.update(fields)

                    def transition_task(self, task_id, state):
                        self.task_data["runtime_state"] = state

                    def update_lease(self, lease_id, **fields):
                        return None

                class FakeLedger:
                    def append(self, *args, **kwargs):
                        return None

                fake_db = FakeDB(rendered_task)
                with patch.object(
                    pec_replan,
                    "current_plan_revision",
                    return_value={"plan_revision": 1, "active_replan_revision_id": None},
                ):
                    rendered_receipt = pec_contracts.render_contract(
                        fake_db, FakeLedger(), workspace, "TASK-001"
                    )
                rendered = json.loads(
                    Path(rendered_receipt["contract"]).read_text(encoding="utf-8")
                )
                self.assertEqual(rendered["verification_mechanisms"], mechanisms)
                self.assertEqual(rendered["validation_commands"], [])
            finally:
                db.close()


class ScopedRelockTest(unittest.TestCase):
    @staticmethod
    def _lock(root: Path) -> dict:
        t1 = {"id": "TASK-001", "source": {"id": "TASK-001", "objective": "old one"}}
        t2 = {"id": "TASK-002", "source": {"id": "TASK-002", "objective": "stable two"}}
        body = {
            "blueprint_root": str(root),
            "source_digests": {"TASK_CARDS.yaml": "1" * 64, "PROGRAM.yaml": "2" * 64},
            "tasks": [t1, t2],
        }
        body["lock_digest"] = digest_object(body)
        return body

    def test_relock_absorbs_non_task_program_drift(self) -> None:
        """Program-wide sources are compiled artifacts, not authored inputs.

        Any resume that reaches a scoped relock has just recompiled the
        Blueprint, so PROGRAM.yaml and its siblings differ from what the prior
        lock attested on every run. Refusing on that drift would make the
        explicit-task-ids path unreachable on a live campaign. What must still
        hold is that a task nobody named is left exactly as it was.
        """
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "blueprint"
            root.mkdir()
            lock_path = Path(raw) / "program-lock.json"
            lock = self._lock(root)
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            current = {
                "source_digests": {"TASK_CARDS.yaml": "3" * 64, "PROGRAM.yaml": "9" * 64},
                "tasks": [
                    {"id": "TASK-001", "source": {"id": "TASK-001", "objective": "new one"}},
                    lock["tasks"][1],
                ],
            }
            with (
                patch.object(pec_blueprint, "normalize_blueprint", return_value=current),
                patch.object(pec_blueprint, "validate_program_lock_schema", return_value=[]),
            ):
                outcome = pec_blueprint.relock_tasks(lock_path, ["TASK-001"])
            self.assertEqual(outcome["relocked"], ["TASK-001"])
            relocked = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(relocked["source_digests"]["PROGRAM.yaml"], "9" * 64)
            self.assertEqual(relocked["source_digests"]["TASK_CARDS.yaml"], "3" * 64)
            self.assertEqual(relocked["tasks"][1], lock["tasks"][1])

    def test_relock_refuses_non_selected_task_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "blueprint"
            root.mkdir()
            lock_path = Path(raw) / "program-lock.json"
            lock = self._lock(root)
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            current = {
                "source_digests": {"TASK_CARDS.yaml": "3" * 64, "PROGRAM.yaml": "2" * 64},
                "tasks": [
                    {"id": "TASK-001", "source": {"id": "TASK-001", "objective": "new one"}},
                    {"id": "TASK-002", "source": {"id": "TASK-002", "objective": "drifted"}},
                ],
            }
            with patch.object(pec_blueprint, "normalize_blueprint", return_value=current):
                with self.assertRaises(pec_blueprint.BlueprintError) as ctx:
                    pec_blueprint.relock_tasks(lock_path, ["TASK-001"])
            self.assertIn("non-selected task definitions changed", str(ctx.exception))

    def test_relock_refreshes_only_task_cards_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "blueprint"
            root.mkdir()
            lock_path = Path(raw) / "program-lock.json"
            lock = self._lock(root)
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            current = {
                "source_digests": {"TASK_CARDS.yaml": "3" * 64, "PROGRAM.yaml": "2" * 64},
                "tasks": [
                    {"id": "TASK-001", "source": {"id": "TASK-001", "objective": "new one"}},
                    lock["tasks"][1],
                ],
            }
            with (
                patch.object(pec_blueprint, "normalize_blueprint", return_value=current),
                patch.object(pec_blueprint, "validate_program_lock_schema", return_value=[]),
            ):
                pec_blueprint.relock_tasks(lock_path, ["TASK-001"])
            relocked = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(relocked["source_digests"]["TASK_CARDS.yaml"], "3" * 64)
            self.assertEqual(relocked["source_digests"]["PROGRAM.yaml"], "2" * 64)
            self.assertEqual(relocked["tasks"][1], lock["tasks"][1])


class NormalExecutionImmutabilityTest(unittest.TestCase):
    def test_normal_execution_never_relocks_to_repair_missing_validation(self) -> None:
        contract = {
            "task_id": "TASK-001",
            "requested_actions": ["inspect", "local_write"],
            "verification_mechanisms": [_verification("inspection")],
            "validation_commands": [],
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            before = list(root.iterdir())
            with self.assertRaises(run_campaign.CampaignError) as ctx:
                run_campaign.fill_inferred_validation(root / "contract.json", contract, root)
            self.assertEqual(ctx.exception.error_code, "MISSING_TERMINAL_VERIFIER")
            self.assertEqual(list(root.iterdir()), before)

    def test_external_adapter_survives_assertion_only_execution_boundary(self) -> None:
        mechanism = _verification("external_adapter", "verify with canonical adapter")
        contract = {
            "task_id": "TASK-001",
            "requested_actions": ["inspect", "local_write"],
            "verification_mechanisms": [mechanism],
            "validation_commands": [],
        }
        with tempfile.TemporaryDirectory() as raw:
            result = run_campaign.fill_inferred_validation(
                Path(raw) / "contract.json", contract, Path(raw)
            )
        self.assertIs(result, contract)
        self.assertEqual(result["verification_mechanisms"], [mechanism])

    def test_preparation_runs_enrichment_before_final_validation(self) -> None:
        self.assertLess(
            run_campaign.PREPARATION_STAGES.index("launchability"),
            run_campaign.PREPARATION_STAGES.index("validate_blueprint"),
        )

    def test_post_accept_byte_change_is_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "PROGRAM.yaml").write_text("x\n", encoding="utf-8")
            accepted = run_campaign.blueprint_byte_inventory(root)
            (root / "PROGRAM.yaml").write_text("y\n", encoding="utf-8")
            with self.assertRaises(run_campaign.CampaignError) as ctx:
                run_campaign.assert_blueprint_immutable(root, accepted, phase="test")
            self.assertIn("post_accept_blueprint_write_count=1", str(ctx.exception))
            self.assertEqual(ctx.exception.error_code, "POST_ACCEPT_BLUEPRINT_WRITE")


if __name__ == "__main__":
    unittest.main()
