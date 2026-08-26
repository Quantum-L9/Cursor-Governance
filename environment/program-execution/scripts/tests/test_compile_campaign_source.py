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
            self.compiler.compile_source(SOURCE, target, stack_proof=proof)
            digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
            self.assertEqual(digest, EXPECTED_DIGEST)
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
            source = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            source.write_text(
                SOURCE.read_text(encoding="utf-8").replace(
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
                SOURCE, target, stack_proof=_pass_proof(tmp / "stack-proof.json")
            )  # self-validates template mode

            collect = _load("collect_evidence_test", PE_ROOT / "scripts/collect_evidence.py")
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
        source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
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

    def test_legacy_blocked_with_dependencies_canonicalizes_to_ready(self) -> None:
        """ADR-0023 A1: sequencing-only legacy `blocked` compiles as `ready`."""
        source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
        task = next(item for item in source["tasks"] if item["id"] == "TASK-002")
        task["definition_status"] = "blocked"
        task["dependencies"] = ["TASK-001"]
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

    def test_blocked_without_dependencies_refuses_compilation(self) -> None:
        """ADR-0023 A2: `blocked` with nothing to wait on is a runtime dead-end."""
        source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
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

    def test_ordering_alias_statuses_cannot_become_task_cards(self) -> None:
        """ADR-0023 A3: approval-shaped statuses are not task-ordering states."""
        for alias in ("pending", "advisory", "awaiting_approval", "not_approved"):
            with self.subTest(alias=alias):
                source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
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
        source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
