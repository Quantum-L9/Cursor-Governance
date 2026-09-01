"""End-to-end architecture compilation: forward progress, and the golden fixture.

The golden case is a realistic long microscope audit of `Quantum-L9/LLM-Router`:
prose, tables, code fences, current-state observations, migration order, explicit
deferrals, and tests — and no numbered task list anywhere in it. Structural
Blueprint validity is not what these tests check. They check that the
obligations the operator wrote are still there afterwards.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures/architecture-intent-llm-router.md"
TARGET = "Quantum-L9/LLM-Router"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if str(PE_ROOT) not in sys.path:
    sys.path.insert(0, str(PE_ROOT))

ARCH = _load("compile_architecture_intent_test", PE_ROOT / "scripts/compile_architecture_intent.py")
COMPILER = _load(
    "compile_campaign_source_arch_test", PE_ROOT / "scripts/compile_campaign_source.py"
)
VALIDATOR = _load(
    "validate_blueprint_arch_test",
    PE_ROOT / "core/program-execution-blueprint-template/scripts/validate_blueprint.py",
)

BLOCKING_VOCABULARY = ("blocked", "pending", "advisory", "awaiting_review", "requires_approval")


def _compile(
    tmp: Path,
    *,
    intent: Path = FIXTURE,
    target: str | None = TARGET,
    target_checkout: Path | None = None,
    **kwargs,
) -> dict:
    return ARCH.compile_architecture_intent(
        intent,
        target=target,
        repo_root=None,
        target_checkout=target_checkout,
        cache_root=tmp / "primed",
        extractor_name="deterministic",
        stamp="2026-08-26T00:00:00+00:00",
        **kwargs,
    )


def _source(receipt: dict) -> dict:
    return yaml.safe_load(Path(receipt["campaign_source"]).read_text(encoding="utf-8"))


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


class RouteTests(unittest.TestCase):
    def test_raw_markdown_compiles_with_no_frontmatter_edit(self) -> None:
        with TemporaryDirectory() as raw:
            receipt = _compile(Path(raw))
            self.assertEqual(receipt["coverage"]["status"], "PASS")
            self.assertEqual(receipt["target"], TARGET)
            self.assertTrue(Path(receipt["campaign_source"]).is_file())

    def test_the_document_never_had_to_become_a_task_list(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertNotIn("Release 1", text)
        self.assertNotIn("TASK-001", text)
        self.assertNotIn("campaign_id", text)
        with TemporaryDirectory() as raw:
            self.assertGreaterEqual(len(_source(_compile(Path(raw)))["tasks"]), 3)

    def test_campaign_id_is_readable_and_deterministic(self) -> None:
        with TemporaryDirectory() as raw:
            first = _compile(Path(raw))["campaign_id"]
            second = _compile(Path(raw) / "second")["campaign_id"]
        self.assertEqual(first, second)
        self.assertEqual(first, "llm-router-reasoning-capability-microscope-v1")

    def test_compile_writes_only_into_the_compiler_cache(self) -> None:
        """Nothing here may create a worktree, a Blueprint, or PEC state."""
        with TemporaryDirectory() as raw:
            root = Path(raw)
            receipt = _compile(root)
            written = {
                path.relative_to(root).parts[0] for path in root.rglob("*") if path.is_file()
            }
            self.assertEqual(written, {"primed"})
            self.assertIn("primed", Path(receipt["campaign_source"]).parts)

    def test_an_unresolvable_target_fails_before_anything_is_written(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(ARCH.ArchitectureCompileError) as ctx:
                _compile(root, target=None)
            self.assertTrue(ctx.exception.to_dict()["nothing_executed"])
            self.assertFalse(ctx.exception.to_dict()["workspace_created"])
            self.assertEqual(ctx.exception.to_dict()["tasks_started"], 0)
            self.assertEqual([p for p in root.rglob("*") if p.is_file()], [])

    def test_an_unreadable_source_fails_closed(self) -> None:
        with TemporaryDirectory() as raw:
            with self.assertRaises(ARCH.ArchitectureCompileError):
                _compile(Path(raw), intent=Path(raw) / "missing.md")


class ForwardProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.receipt = _compile(Path(self._tmp.name))
        self.source = _source(self.receipt)

    def test_every_generated_task_is_ready(self) -> None:
        statuses = {task["definition_status"] for task in self.source["tasks"]}
        self.assertEqual(statuses, {"ready"})
        self.assertEqual(self.receipt["blocked_task_count"], 0)

    def test_no_approval_shaped_state_is_introduced(self) -> None:
        blob = json.dumps(self.source).lower()
        for word in ("awaiting approval", "not approved", "pending approval", "advisory only"):
            self.assertNotIn(word, blob)
        for task in self.source["tasks"]:
            for field in ("definition_status", "execution_kind"):
                self.assertNotIn(task[field], BLOCKING_VOCABULARY[1:])

    def test_ordering_lives_in_the_graph_not_in_readiness(self) -> None:
        self.assertTrue(self.source["dependency_edges"])
        self.assertGreater(len(self.source["waves"]), 1)
        task_ids = {task["id"] for task in self.source["tasks"]}
        for edge in self.source["dependency_edges"]:
            self.assertIn(edge["from"], task_ids)
            self.assertIn(edge["to"], task_ids)
            self.assertNotEqual(edge["from"], edge["to"])
        waved = [task_id for wave in self.source["waves"] for task_id in wave["task_ids"]]
        self.assertEqual(sorted(waved), sorted(task_ids), "every task belongs to exactly one wave")

    def test_a_probeable_unknown_becomes_a_ready_evidence_task(self) -> None:
        discovery = [task for task in self.source["tasks"] if task["execution_kind"] == "read_only"]
        self.assertTrue(discovery, "the source asks questions a repository read can answer")
        for task in discovery:
            self.assertEqual(task["definition_status"], "ready")
            self.assertFalse(task["authorization_ceiling"]["local_write"])
        dependents = {
            edge["to"]
            for edge in self.source["dependency_edges"]
            if edge["from"] == discovery[0]["id"]
        }
        self.assertTrue(dependents, "dependents wait on the evidence task by edge, not by status")

    def test_unknowns_are_recorded_without_blocking_anything(self) -> None:
        self.assertTrue(self.source["unknowns"])
        for unknown in self.source["unknowns"]:
            self.assertEqual(unknown["blocking_task_ids"], [])
            self.assertTrue(unknown["resolution_method"])

    def test_every_task_carries_runnable_validation(self) -> None:
        for task in self.source["tasks"]:
            self.assertTrue(task["validation"], f"{task['id']} has no validation")
            for entry in task["validation"]:
                body = entry.get("command_or_inspection") or entry.get("command") or ""
                self.assertTrue(body.strip(), f"{task['id']} validation is empty")
                for placeholder in ("TODO", "TBD", "manual review pending", "awaiting validation"):
                    self.assertNotIn(placeholder.lower(), body.lower())

    def test_repository_native_commands_are_resolved_when_a_checkout_is_present(self) -> None:
        with TemporaryDirectory() as raw:
            checkout = Path(raw) / "repo"
            (checkout / "src").mkdir(parents=True)
            (checkout / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest run", "lint": "eslint src/"}}),
                encoding="utf-8",
            )
            source = _source(_compile(Path(raw), target_checkout=checkout))
            commands = {
                entry.get("command")
                for task in source["tasks"]
                for entry in task["validation"]
                if entry.get("command")
            }
            self.assertIn("npm test", commands)
            self.assertIn("npm run lint", commands)


class GoldenSemanticTests(unittest.TestCase):
    """A structurally valid Blueprint missing one of these must fail."""

    OBLIGATIONS = (
        ("DeepSeek is the primary governed reasoning provider", "DeepSeek"),
        ("Perplexity is research only", "Perplexity"),
        ("requiresReasoning is canonical capability authority", "requiresReasoning"),
        ("Perplexity reasoning models are unreachable", "unreachable"),
        ("budget downgrade stays in the capability family", "capability family"),
        ("search plus reasoning fails closed", "Search combined with reasoning"),
        ("vision plus reasoning fails closed", "Vision combined with reasoning"),
        ("route decision equals actual dispatch", "route decision MUST equal"),
        ("reasoning_content is never persisted or exposed", "reasoning_content"),
        ("composite research to reasoning stays deferred", "composite research-then-reasoning"),
        ("control-plane vocabulary is reused", "reuse that existing vocabulary"),
        ("existing circuit/budget/audit invariants remain intact", "circuit-breaker"),
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.receipt = _compile(root)
        cls.source = _source(cls.receipt)
        cls.blueprint = root / "blueprint"
        COMPILER.compile_source(
            Path(cls.receipt["campaign_source"]),
            cls.blueprint,
            stack_proof=_pass_proof(root / "stack-proof.json", cls.receipt["campaign_id"]),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _artifact(self, name: str) -> dict:
        return yaml.safe_load((self.blueprint / name).read_text(encoding="utf-8"))

    def _blueprint_text(self) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(self.blueprint.rglob("*"))
            if path.is_file() and path.suffix in {".yaml", ".yml", ".md"}
        )

    def test_blueprint_validates(self) -> None:
        self.assertEqual(VALIDATOR.validate(self.blueprint, "template"), [])

    def test_every_expected_obligation_survived_into_the_blueprint(self) -> None:
        text = self._blueprint_text()
        missing = [label for label, needle in self.OBLIGATIONS if needle not in text]
        self.assertEqual(missing, [], msg=f"obligations lost in compilation: {missing}")

    def test_all_task_cards_are_ready(self) -> None:
        tasks = self._artifact("TASK_CARDS.yaml")["tasks"]
        self.assertTrue(tasks)
        self.assertEqual({task["definition_status"] for task in tasks}, {"ready"})

    def test_no_fake_pending_or_approval_status_exists(self) -> None:
        tasks = self._artifact("TASK_CARDS.yaml")["tasks"]
        for task in tasks:
            self.assertNotIn(task["definition_status"], BLOCKING_VOCABULARY)
        waves = self._artifact("EXECUTION_WAVES.yaml")["waves"]
        self.assertEqual({wave["definition_status"] for wave in waves}, {"active"})

    def test_dependency_sequencing_exists(self) -> None:
        graph = self._artifact("DEPENDENCY_GRAPH.yaml")
        self.assertTrue(graph["edges"])
        self.assertGreater(len(self._artifact("EXECUTION_WAVES.yaml")["waves"]), 1)

    def test_the_research_only_prohibition_is_enforceable(self) -> None:
        """The law survives compilation, in the channel that can carry it.

        These assertions used to read `path_or_pattern`, because that is where
        the compiler put every prohibition. "MUST NOT serve reasoning" is not a
        glob, and the Controller matching it against changed files enforced
        nothing (W8/S1). The text now lives in `statement`, and the entry
        declares itself semantic so it is never globbed.
        """
        prohibitions = self._artifact("DO_NOT_BUILD.yaml")["prohibited_primary_paths"]
        joined = " ".join(entry["statement"] for entry in prohibitions)
        self.assertIn("Perplexity", joined)
        self.assertIn("MUST NOT serve reasoning", joined)
        carriers = [
            entry for entry in prohibitions if "MUST NOT serve reasoning" in entry["statement"]
        ]
        self.assertTrue(carriers)
        for entry in carriers:
            self.assertEqual(entry["kind"], "semantic")
            self.assertNotIn("path_or_pattern", entry)

    def test_the_reasoning_content_privacy_invariant_is_a_prohibition(self) -> None:
        prohibitions = self._artifact("DO_NOT_BUILD.yaml")["prohibited_primary_paths"]
        self.assertTrue(any("reasoning_content" in entry["statement"] for entry in prohibitions))

    def test_the_deferred_composite_stays_deferred(self) -> None:
        program = self._artifact("PROGRAM.yaml")["program"]
        excluded = " ".join(program["scope"]["exclude"])
        self.assertIn("composite research-then-reasoning", excluded)
        tasks = self._artifact("TASK_CARDS.yaml")["tasks"]
        for task in tasks:
            self.assertNotIn("staged composite executor", " ".join(task["actions"]))

    def test_deepseek_reasoning_requirement_is_task_work(self) -> None:
        tasks = self._artifact("TASK_CARDS.yaml")["tasks"]
        actions = " ".join(action for task in tasks for action in task["actions"])
        self.assertIn("DeepSeek MUST be the primary governed reasoning provider", actions)

    def test_coverage_is_pass_and_recorded_in_traceability(self) -> None:
        self.assertEqual(self.source["intent_provenance"]["coverage"]["status"], "PASS")
        lineage = self._artifact("SOURCE_TRACEABILITY.yaml")["sources"][0]["architecture_intent"]
        self.assertEqual(lineage["coverage"]["status"], "PASS")
        self.assertEqual(lineage["source_sha256"], self.receipt["source"]["sha256"])
        self.assertTrue(lineage["clauses"])
        for clause in lineage["clauses"]:
            self.assertTrue(clause["source_refs"])

    def test_provenance_survives_into_the_campaign_source(self) -> None:
        provenance = self.source["intent_provenance"]
        self.assertEqual(provenance["schema"], "l9.program-execution.intent-provenance.v1")
        self.assertEqual(provenance["source"]["sha256"], self.receipt["source"]["sha256"])
        unit_ids = {unit["id"] for unit in provenance["source_units"]}
        for item in provenance["semantic_items"]:
            self.assertLessEqual(set(item["source_refs"]), unit_ids)

    def test_reported_counts_match_the_artifacts(self) -> None:
        self.assertEqual(self.receipt["task_count"], len(self.source["tasks"]))
        self.assertEqual(self.receipt["prohibition_count"], len(self.source["prohibited_paths"]))
        self.assertEqual(self.receipt["blocked_task_count"], 0)


class LongSourceTests(unittest.TestCase):
    def test_a_source_larger_than_one_request_chunks_instead_of_truncating(self) -> None:
        body = "\n\n".join(
            f"## Section {n}\n\nObligation {n} MUST hold for the router." for n in range(120)
        )
        with TemporaryDirectory() as raw:
            path = Path(raw) / "long.md"
            path.write_text(f"# Long architecture\n\n{body}\n", encoding="utf-8")
            receipt = _compile(Path(raw), intent=path, max_chunk_chars=1500)
            self.assertGreater(receipt["chunks"], 1)
            self.assertEqual(receipt["coverage"]["status"], "PASS")
            source = _source(receipt)
            actions = " ".join(action for task in source["tasks"] for action in task["actions"])
            for index in (0, 60, 119):
                self.assertIn(f"Obligation {index} MUST hold", actions)


class RepairTests(unittest.TestCase):
    def test_missing_paths_and_commands_do_not_block_compilation(self) -> None:
        doc = textwrap.dedent(
            """\
            # Ambient subsystem

            The retry subsystem MUST stop retrying non-idempotent writes.

            The audit log MUST record every retry decision.
            """
        )
        with TemporaryDirectory() as raw:
            path = Path(raw) / "ambient.md"
            path.write_text(doc, encoding="utf-8")
            source = _source(_compile(Path(raw), intent=path))
            self.assertEqual({task["definition_status"] for task in source["tasks"]}, {"ready"})
            for task in source["tasks"]:
                self.assertTrue(task["validation"])

    def test_a_probeable_question_produces_work_not_a_blocker(self) -> None:
        doc = textwrap.dedent(
            """\
            # Schema widening

            We need to determine whether the current schema already exposes the depth enum.

            The policy engine MUST consume whatever depth vocabulary the schema exposes.
            """
        )
        with TemporaryDirectory() as raw:
            path = Path(raw) / "probe.md"
            path.write_text(doc, encoding="utf-8")
            source = _source(_compile(Path(raw), intent=path))
            self.assertEqual({task["definition_status"] for task in source["tasks"]}, {"ready"})
            self.assertTrue(any(task["execution_kind"] == "read_only" for task in source["tasks"]))
            for unknown in source["unknowns"]:
                self.assertEqual(unknown["blocking_task_ids"], [])

    def test_the_evidence_edge_points_at_the_task_that_consumes_it(self) -> None:
        """A driverless section must not shift the section-to-task mapping.

        Alpha states only a prohibition and a seam, so it produces no task of its
        own. Deriving the mapping positionally shifted every later section by
        one, and the Beta question ended up edged to Gamma — the evidence a task
        needs, scheduled after it.
        """
        doc = textwrap.dedent(
            """\
            # Head

            ## Alpha

            The seam is src/alpha.ts and it MUST NOT be renamed.

            ## Beta

            We need to determine whether beta already holds.

            Beta MUST hold.

            ## Gamma

            Gamma MUST hold.
            """
        )
        with TemporaryDirectory() as raw:
            path = Path(raw) / "sections.md"
            path.write_text(doc, encoding="utf-8")
            source = _source(_compile(Path(raw), intent=path))
            by_id = {task["id"]: task for task in source["tasks"]}
            discovery = next(
                task for task in source["tasks"] if task["execution_kind"] == "read_only"
            )
            self.assertIn("Beta", discovery["title"])
            dependents = [
                by_id[edge["to"]]["title"]
                for edge in source["dependency_edges"]
                if edge["from"] == discovery["id"]
            ]
            self.assertEqual(dependents, ["Beta"])

    def test_a_deferred_feature_becomes_an_exclusion_not_a_stalled_task(self) -> None:
        doc = textwrap.dedent(
            """\
            # Staging

            The dispatcher MUST route by capability.

            Composite execution is DEFERRED and OUT OF SCOPE for this release.
            """
        )
        with TemporaryDirectory() as raw:
            path = Path(raw) / "defer.md"
            path.write_text(doc, encoding="utf-8")
            source = _source(_compile(Path(raw), intent=path))
            excluded = " ".join(source["program"]["scope"]["exclude"]).lower()
            self.assertIn("composite execution", excluded)
            titles = " ".join(task["title"] for task in source["tasks"]).lower()
            self.assertNotIn("composite execution is deferred", titles)


class TamperTests(unittest.TestCase):
    """Provenance is re-derived by the canonical compiler, never trusted."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.receipt = _compile(self.root)
        self.source_path = Path(self.receipt["campaign_source"])
        self.source = _source(self.receipt)
        self.proof = _pass_proof(self.root / "stack-proof.json", self.receipt["campaign_id"])

    def _compile_edited(self, edited: dict) -> None:
        path = self.root / "edited.yaml"
        path.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
        COMPILER.compile_source(path, self.root / "tampered", stack_proof=self.proof)

    def test_the_untampered_source_compiles(self) -> None:
        COMPILER.compile_source(self.source_path, self.root / "clean", stack_proof=self.proof)

    def test_deleting_a_mapped_task_is_caught(self) -> None:
        edited = yaml.safe_load(self.source_path.read_text(encoding="utf-8"))
        edited["tasks"] = edited["tasks"][:-1]
        with self.assertRaises(COMPILER.CompileError) as ctx:
            self._compile_edited(edited)
        self.assertIn("the mapped obligation was removed", str(ctx.exception))

    def test_deleting_a_mapped_prohibition_is_caught(self) -> None:
        edited = yaml.safe_load(self.source_path.read_text(encoding="utf-8"))
        edited["prohibited_paths"] = edited["prohibited_paths"][1:]
        with self.assertRaises(COMPILER.CompileError):
            self._compile_edited(edited)

    def test_forging_pass_coverage_over_an_ungoverned_unit_is_caught(self) -> None:
        edited = yaml.safe_load(self.source_path.read_text(encoding="utf-8"))
        for unit in edited["intent_provenance"]["source_units"]:
            if unit.get("signals"):
                unit["disposition"] = "mapped_context"
                break
        with self.assertRaises(COMPILER.CompileError) as ctx:
            self._compile_edited(edited)
        self.assertIn("governed disposition", str(ctx.exception))

    def test_a_fail_coverage_record_cannot_be_compiled(self) -> None:
        edited = yaml.safe_load(self.source_path.read_text(encoding="utf-8"))
        edited["intent_provenance"]["coverage"]["status"] = "FAIL"
        with self.assertRaises(COMPILER.CompileError):
            self._compile_edited(edited)

    def test_dropping_a_source_unit_a_semantic_item_cites_is_caught(self) -> None:
        edited = yaml.safe_load(self.source_path.read_text(encoding="utf-8"))
        cited = edited["intent_provenance"]["semantic_items"][0]["source_refs"][0]
        edited["intent_provenance"]["source_units"] = [
            unit for unit in edited["intent_provenance"]["source_units"] if unit["id"] != cited
        ]
        with self.assertRaises(COMPILER.CompileError) as ctx:
            self._compile_edited(edited)
        self.assertIn("unknown source units", str(ctx.exception))

    def test_a_legacy_source_without_provenance_still_compiles(self) -> None:
        """No intent_provenance is not a defect; missing writable scope is.

        The legacy fixture predates the rule that a mutating task must name what
        it may write, so its tasks are given explicit scope here. What this test
        asserts is that a source carrying no architecture lineage still compiles,
        not that a task may omit its scope.
        """
        legacy = yaml.safe_load(
            (PE_ROOT / "campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml").read_text(
                encoding="utf-8"
            )
        )
        for task in legacy.get("tasks") or []:
            ceiling = task.get("authorization_ceiling") or {}
            mutating = (
                ceiling.get("local_write") and task.get("execution_kind") != "program_control"
            )
            if mutating and not task.get("paths") and not task.get("outputs"):
                task["paths"] = [f"docs/program-execution/{task['id']}.md"]
        source = self.root / "legacy-source.yaml"
        source.write_text(yaml.safe_dump(legacy, sort_keys=False), encoding="utf-8")
        target = self.root / "legacy"
        COMPILER.compile_source(
            source,
            target,
            stack_proof=_pass_proof(self.root / "legacy-proof.json", "bounded-replanning-v1"),
        )
        self.assertEqual(VALIDATOR.validate(target, "template"), [])


class CliTests(unittest.TestCase):
    def test_the_cli_prints_a_receipt_and_exits_zero(self) -> None:
        with TemporaryDirectory() as raw:
            result = subprocess.run(  # noqa: S603 - argv list, no shell
                [
                    sys.executable,
                    str(PE_ROOT / "scripts/compile_architecture_intent.py"),
                    "--intent",
                    str(FIXTURE),
                    "--target",
                    TARGET,
                    "--cache-root",
                    str(Path(raw) / "primed"),
                    "--extractor",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["coverage"]["status"], "PASS")

    def test_a_failure_says_nothing_executed(self) -> None:
        with TemporaryDirectory() as raw:
            result = subprocess.run(  # noqa: S603 - argv list, no shell
                [
                    sys.executable,
                    str(PE_ROOT / "scripts/compile_architecture_intent.py"),
                    "--intent",
                    str(FIXTURE),
                    "--cache-root",
                    str(Path(raw) / "primed"),
                    "--extractor",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("nothing_executed: true", result.stderr)
            self.assertIn("tasks_started: 0", result.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
