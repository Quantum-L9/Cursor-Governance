"""End-to-end architecture compilation: golden fixture, forward repair, tamper.

Everything runs on the deterministic extractor — no model, no network.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
if str(PE_ROOT) not in sys.path:
    sys.path.insert(0, str(PE_ROOT))

FIXTURE = Path(__file__).resolve().parent / "fixtures/architecture-intent-llm-router.md"
GOLDEN_TARGET = "Quantum-L9/LLM-Router"

from compiler.architecture_extractor import DeterministicExtractor  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pass_proof(path: Path, campaign_id: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "l9.program-execution.stack-proof.v1",
                "campaign_id": campaign_id,
                "status": "pass",
                "tools": [],
                "fetched_at": "2026-08-26T00:00:00Z",
                "validator": {"ok": True, "errors": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


class _Compiled:
    """Compile the golden fixture once; every golden test reads the result."""

    result: dict | None = None
    tmp: tempfile.TemporaryDirectory | None = None

    @classmethod
    def get(cls, module) -> dict:
        if cls.result is None:
            cls.tmp = tempfile.TemporaryDirectory()
            cls.result = module.compile_architecture(
                FIXTURE,
                target=GOLDEN_TARGET,
                primed_dir=Path(cls.tmp.name),
                extractor=DeterministicExtractor(),
                stamp="2026-08-26T00:00:00Z",
            )
        return cls.result


class GoldenFixtureTests(unittest.TestCase):
    """§ golden dogfood: obligations survive, everything is ready, coverage PASS."""

    def setUp(self) -> None:
        self.module = _load(
            "compile_architecture_intent_test",
            PE_ROOT / "scripts/compile_architecture_intent.py",
        )
        self.result = _Compiled.get(self.module)
        self.source = self.result["campaign_source"]

    def _all_text(self) -> str:
        return yaml.safe_dump(self.source, sort_keys=False)

    def _obligation_present(self, *needles: str) -> bool:
        haystacks = []
        for task in self.source["tasks"]:
            haystacks.append(task["objective"])
            haystacks.extend(str(entry.get("statement")) for entry in task["acceptance"])
        for entry in self.source.get("prohibited_paths") or []:
            haystacks.append(str(entry.get("statement")))
        for entry in self.source["program"]["scope"]["exclude"]:
            haystacks.append(str(entry))
        lowered = "\n".join(haystacks).lower()
        return all(needle.lower() in lowered for needle in needles)

    def test_coverage_is_pass_and_machine_verified(self) -> None:
        coverage = self.result["coverage"]
        self.assertEqual(coverage["status"], "PASS")
        self.assertEqual(coverage["unmapped_material_units"], 0)
        self.assertEqual(coverage["mapped_material_units"], coverage["material_units"])
        self.assertGreater(coverage["material_units"], 10)

    def test_every_generated_task_is_ready(self) -> None:
        statuses = {task["definition_status"] for task in self.source["tasks"]}
        self.assertEqual(statuses, {"ready"})
        self.assertEqual(self.result["blocked_task_count"], 0)
        self.assertGreaterEqual(self.result["task_count"], 8)

    def test_no_approval_shaped_statuses_exist(self) -> None:
        text = self._all_text().lower()
        for forbidden in (
            "advisory",
            "pending",
            "awaiting_review",
            "requires_approval",
            "not_approved",
            "conditionally_blocked",
        ):
            self.assertNotIn(forbidden, text)

    def test_semantic_obligations_survive(self) -> None:
        self.assertTrue(self._obligation_present("deepseek", "primary governed reasoning"))
        self.assertTrue(self._obligation_present("perplexity", "research-only"))
        self.assertTrue(self._obligation_present("requiresreasoning", "canonical capability"))
        self.assertTrue(self._obligation_present("perplexity reasoning models", "not"))
        self.assertTrue(self._obligation_present("capability", "family"))
        self.assertTrue(self._obligation_present("search and reasoning", "fail closed"))
        self.assertTrue(self._obligation_present("vision and reasoning", "fail closed"))
        self.assertTrue(self._obligation_present("route decision", "actual provider dispatch"))
        self.assertTrue(self._obligation_present("reasoning_content"))
        self.assertTrue(self._obligation_present("reasoning-depth", "vocabulary"))
        self.assertTrue(
            self._obligation_present("circuit-breaker", "budget-enforcement", "audit-trail")
        )

    def test_privacy_prohibition_is_enforceable(self) -> None:
        prohibitions = "\n".join(
            str(entry["statement"]) for entry in self.source["prohibited_paths"]
        ).lower()
        self.assertIn("reasoning_content", prohibitions)
        self.assertIn("research-only", prohibitions)
        self.assertGreaterEqual(self.result["prohibition_count"], 3)

    def test_deferred_composite_stays_deferred_not_blocked(self) -> None:
        excludes = "\n".join(self.source["program"]["scope"]["exclude"]).lower()
        self.assertIn("later phase", excludes)
        titles = "\n".join(task["title"] for task in self.source["tasks"]).lower()
        self.assertNotIn("research-then-reasoning composite pipeline", titles)

    def test_probeable_unknown_becomes_ready_discovery_with_dependents(self) -> None:
        discovery = [
            task
            for task in self.source["tasks"]
            if task["kernel_profile"] == "AUDIT" and "cache-hit" in task["objective"].lower()
        ]
        self.assertEqual(len(discovery), 1)
        self.assertEqual(discovery[0]["definition_status"], "ready")
        dependents = [
            edge["to"]
            for edge in self.source["dependency_edges"]
            if edge["from"] == discovery[0]["id"]
        ]
        self.assertTrue(dependents, "budget work must wait on the discovery task")

    def test_ordering_is_graph_based(self) -> None:
        self.assertTrue(self.source["dependency_edges"])
        self.assertGreaterEqual(len(self.source["waves"]), 2)
        wave_ids = {wave["id"] for wave in self.source["waves"]}
        for task in self.source["tasks"]:
            self.assertIn(task["wave_id"], wave_ids)

    def test_validation_commands_resolved_from_source(self) -> None:
        commands = [
            entry["command_or_inspection"]
            for task in self.source["tasks"]
            for entry in task["validation"]
        ]
        joined = "\n".join(commands)
        self.assertIn("npm test --silent -- test/routing.test.ts", joined)
        for command in commands:
            self.assertNotIn("TODO", command)
            self.assertNotIn("TBD", command)

    def test_intent_provenance_embedded_and_bound(self) -> None:
        provenance = self.source["intent_provenance"]
        self.assertEqual(provenance["schema"], "l9.program-execution.intent-provenance.v1")
        self.assertEqual(provenance["coverage"]["status"], "PASS")
        unit_ids = {unit["id"] for unit in provenance["source_units"]}
        for item in provenance["semantic_items"]:
            self.assertTrue(item["source_refs"])
            for ref in item["source_refs"]:
                self.assertIn(ref, unit_ids)
        self.assertEqual(
            provenance["source"]["sha256"],
            __import__("hashlib").sha256(FIXTURE.read_text(encoding="utf-8").encode()).hexdigest(),
        )


class GoldenBlueprintTests(unittest.TestCase):
    """§ golden output: the generated source compiles to a validator-clean
    Blueprint whose artifacts carry the obligations."""

    def setUp(self) -> None:
        self.arch = _load(
            "compile_architecture_intent_test",
            PE_ROOT / "scripts/compile_architecture_intent.py",
        )
        self.compiler = _load(
            "compile_campaign_source_arch_test",
            PE_ROOT / "scripts/compile_campaign_source.py",
        )
        self.validator = _load(
            "validate_blueprint_arch_test",
            PE_ROOT / "core/program-execution-blueprint-template/scripts/validate_blueprint.py",
        )
        self.result = _Compiled.get(self.arch)

    def test_blueprint_compiles_and_carries_obligations(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            source = tmp / "CAMPAIGN_SOURCE.yaml"
            source.write_text(
                yaml.safe_dump(self.result["campaign_source"], sort_keys=False),
                encoding="utf-8",
            )
            target = tmp / "blueprint"
            compiled = self.compiler.compile_source(
                source,
                target,
                stack_proof=_pass_proof(tmp / "stack-proof.json", self.result["campaign_id"]),
            )
            self.assertEqual(compiled["campaign_id"], self.result["campaign_id"])
            errors = self.validator.validate(target, "template")
            self.assertEqual(errors, [], msg="\n".join(errors))

            expected_artifacts = [
                "PROGRAM.yaml",
                "TASK_CARDS.yaml",
                "DEPENDENCY_GRAPH.yaml",
                "EXECUTION_WAVES.yaml",
                "DO_NOT_BUILD.yaml",
                "DECISION_REGISTER.yaml",
                "RISK_REGISTER.yaml",
                "EVIDENCE_CATALOG.yaml",
                "CONVERGENCE_GATES.yaml",
                "SOURCE_TRACEABILITY.yaml",
            ]
            for name in expected_artifacts:
                self.assertTrue((target / name).is_file(), name)

            cards = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
            self.assertEqual({task["definition_status"] for task in cards["tasks"]}, {"ready"})
            # No approval-shaped state anywhere agents read execution state from:
            # every definition_status and gate status must be a live value.
            forbidden_states = {
                "advisory",
                "pending",
                "awaiting_review",
                "requires_approval",
                "not_approved",
                "conditionally_blocked",
                "blocked",
            }
            for name in expected_artifacts:
                payload = yaml.safe_load((target / name).read_text(encoding="utf-8"))
                for entity in (payload or {}).values():
                    if not isinstance(entity, list):
                        continue
                    for row in entity:
                        if isinstance(row, dict) and "definition_status" in row:
                            self.assertNotIn(row["definition_status"], forbidden_states)

            dnb = yaml.safe_load((target / "DO_NOT_BUILD.yaml").read_text(encoding="utf-8"))
            dnb_text = "\n".join(
                str(item["path_or_pattern"]) for item in dnb["prohibited_primary_paths"]
            ).lower()
            self.assertIn("research-only", dnb_text)
            self.assertIn("reasoning_content", dnb_text)

            graph = yaml.safe_load((target / "DEPENDENCY_GRAPH.yaml").read_text(encoding="utf-8"))
            self.assertTrue(graph["edges"])
            waves = yaml.safe_load((target / "EXECUTION_WAVES.yaml").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(waves["waves"]), 2)

            trace = yaml.safe_load(
                (target / "SOURCE_TRACEABILITY.yaml").read_text(encoding="utf-8")
            )
            arch_sources = [
                entry
                for entry in trace["sources"]
                if isinstance(entry.get("architecture_intent"), dict)
            ]
            self.assertEqual(len(arch_sources), 1)
            lineage = arch_sources[0]["architecture_intent"]
            self.assertEqual(lineage["coverage"]["status"], "PASS")
            self.assertTrue(lineage["semantic_item_ids"])
            self.assertTrue(lineage["campaign_mapping_ids"])


class TamperResistanceTests(unittest.TestCase):
    """§ provenance revalidation: a doctored generated source fails canonical
    compilation instead of bypassing architecture coverage."""

    def setUp(self) -> None:
        self.arch = _load(
            "compile_architecture_intent_test",
            PE_ROOT / "scripts/compile_architecture_intent.py",
        )
        self.compiler = _load(
            "compile_campaign_source_arch_test",
            PE_ROOT / "scripts/compile_campaign_source.py",
        )
        self.source = copy.deepcopy(_Compiled.get(self.arch)["campaign_source"])
        self.campaign_id = self.source["metadata"]["campaign_id"]

    def _expect_compile_error(self, doctored: dict, needle: str) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            path = tmp / "CAMPAIGN_SOURCE.yaml"
            path.write_text(yaml.safe_dump(doctored, sort_keys=False), encoding="utf-8")
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self.compiler.compile_source(
                    path,
                    tmp / "out",
                    stack_proof=_pass_proof(tmp / "stack-proof.json", self.campaign_id),
                )
            self.assertIn(needle, str(ctx.exception))

    def test_deleting_a_mapped_task_fails(self) -> None:
        doctored = copy.deepcopy(self.source)
        removed = doctored["tasks"].pop()
        doctored["gates"] = [
            gate for gate in doctored["gates"] if removed["id"] not in gate["task_ids"]
        ]
        doctored["waves"] = [
            {**wave, "task_ids": [tid for tid in wave["task_ids"] if tid != removed["id"]]}
            for wave in doctored["waves"]
        ]
        self._expect_compile_error(doctored, "intent_provenance")

    def test_deleting_a_semantic_item_fails(self) -> None:
        doctored = copy.deepcopy(self.source)
        items = doctored["intent_provenance"]["semantic_items"]
        victim = next(
            index for index, item in enumerate(items) if item.get("kind") == "prohibition"
        )
        del items[victim]
        self._expect_compile_error(doctored, "intent_provenance")

    def test_doctored_coverage_status_fails(self) -> None:
        doctored = copy.deepcopy(self.source)
        doctored["intent_provenance"]["coverage"]["status"] = "FAIL"
        self._expect_compile_error(doctored, "coverage")

    def test_source_without_provenance_stays_backward_compatible(self) -> None:
        legacy = PE_ROOT / "campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml"
        data = yaml.safe_load(legacy.read_text(encoding="utf-8"))
        self.assertNotIn("intent_provenance", data)
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            result = self.compiler.compile_source(
                legacy,
                tmp / "out",
                stack_proof=_pass_proof(tmp / "stack-proof.json", "bounded-replanning-v1"),
            )
            self.assertEqual(result["campaign_id"], "bounded-replanning-v1")


class ForwardRepairTests(unittest.TestCase):
    """§ forward repair: ordinary incompleteness compiles; it never blocks."""

    def setUp(self) -> None:
        self.module = _load(
            "compile_architecture_intent_test",
            PE_ROOT / "scripts/compile_architecture_intent.py",
        )

    def _compile(self, text: str, tmp: Path, **kwargs):
        source = tmp / "architecture.md"
        source.write_text(text, encoding="utf-8")
        return self.module.compile_architecture(
            source,
            target=kwargs.pop("target", "Quantum-L9/SEO-Bot"),
            primed_dir=tmp / "primed",
            extractor=DeterministicExtractor(),
            stamp="2026-08-26T00:00:00Z",
            **kwargs,
        )

    def test_prose_with_no_numbered_tasks_compiles(self) -> None:
        text = (
            "# Ranking freshness\n\n"
            "The crawler MUST refresh stale rankings within one day.\n\n"
            "Stale entries MUST NOT be served to API consumers.\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            result = self._compile(text, Path(raw))
            self.assertEqual(result["coverage"]["status"], "PASS")
            self.assertEqual(result["blocked_task_count"], 0)
            self.assertGreaterEqual(result["task_count"], 1)

    def test_missing_validation_commands_resolve_from_repository_truth(self) -> None:
        text = "# Gateway hardening\n\nThe gateway MUST reject unsigned webhook payloads.\n"
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / "Makefile").write_text("test:\n\ttrue\n", encoding="utf-8")
            result = self._compile(text, tmp, repo_path=repo)
            commands = [
                entry["command_or_inspection"]
                for task in result["campaign_source"]["tasks"]
                for entry in task["validation"]
            ]
            self.assertIn("make test", commands)

    def test_probeable_unknown_makes_ready_evidence_task(self) -> None:
        text = (
            "# Sitemap batching\n\n"
            "Determine whether the sitemap exporter already batches URL writes "
            "for the batching flow.\n\n"
            "The exporter MUST batch URL writes in the batching flow once "
            "confirmed by that answer.\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            result = self._compile(text, Path(raw))
            tasks = result["campaign_source"]["tasks"]
            self.assertEqual({task["definition_status"] for task in tasks}, {"ready"})
            discovery = [task for task in tasks if task["kernel_profile"] == "AUDIT"]
            self.assertEqual(len(discovery), 1)
            edges = result["campaign_source"]["dependency_edges"]
            self.assertIn(discovery[0]["id"], [edge["from"] for edge in edges])

    def test_deferred_feature_is_scope_exclusion_not_blocked_task(self) -> None:
        text = (
            "# Exports\n\n"
            "The exporter MUST emit weekly digests.\n\n"
            "Realtime streaming export is deferred to a later phase.\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            result = self._compile(text, Path(raw))
            source = result["campaign_source"]
            excludes = "\n".join(source["program"]["scope"]["exclude"]).lower()
            self.assertIn("realtime streaming export", excludes)
            self.assertEqual(result["blocked_task_count"], 0)

    def test_missing_target_fails_before_side_effects(self) -> None:
        text = "# Doc\n\nThe service MUST do the work.\n"
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            source = tmp / "architecture.md"
            source.write_text(text, encoding="utf-8")
            with self.assertRaises(self.module.ArchitectureCompileError) as ctx:
                self.module.compile_architecture(
                    source,
                    target="",
                    primed_dir=tmp / "primed",
                    extractor=DeterministicExtractor(),
                )
            self.assertIn("target repository", str(ctx.exception))
            self.assertFalse((tmp / "primed").exists())

    def test_frontmatter_target_needs_no_cli_target(self) -> None:
        text = (
            "---\n"
            "schema: l9.program-execution.architecture-intent.v1\n"
            "target: Quantum-L9/Website-Bot\n"
            "---\n\n"
            "# Doc\n\nThe bot MUST publish sitemaps nightly.\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            result = self._compile(text, Path(raw), target="")
            self.assertEqual(result["target"], "Quantum-L9/Website-Bot")


class CampaignIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load(
            "compile_architecture_intent_test",
            PE_ROOT / "scripts/compile_architecture_intent.py",
        )

    def test_readable_slug_with_collision_suffix_and_same_source_reuse(self) -> None:
        text = "# Widget Plan\n\nThe widget MUST spin quietly during operation.\n"
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            source = tmp / "widget-plan.md"
            source.write_text(text, encoding="utf-8")
            first = self.module.compile_architecture(
                source,
                target="Quantum-L9/SEO-Bot",
                primed_dir=tmp / "primed",
                existing_ids={"widget-plan"},
                extractor=DeterministicExtractor(),
            )
            self.assertEqual(first["campaign_id"], "widget-plan-v2")
            self.assertNotRegex(first["campaign_id"], r"^pe-[0-9a-f]{8,}$")
            # Same source again: the primed resolution binds the digest, so the
            # id is reused instead of suffixing a third variant.
            second = self.module.compile_architecture(
                source,
                target="Quantum-L9/SEO-Bot",
                primed_dir=tmp / "primed",
                existing_ids={"widget-plan", "widget-plan-v2"},
                extractor=DeterministicExtractor(),
            )
            self.assertEqual(second["campaign_id"], "widget-plan-v2")


if __name__ == "__main__":
    unittest.main()
