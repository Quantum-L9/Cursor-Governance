from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/context7_stack_proof.py"


def _load():
    spec = importlib.util.spec_from_file_location("context7_stack_proof_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load context7_stack_proof")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context7StackProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load()
        self._key = os.environ.get("CONTEXT7_API_KEY")
        os.environ["CONTEXT7_API_KEY"] = "test-key-not-a-secret"

    def tearDown(self) -> None:
        if self._key is None:
            os.environ.pop("CONTEXT7_API_KEY", None)
        else:
            os.environ["CONTEXT7_API_KEY"] = self._key

    def test_empty_infer_on_api_campaign_refuses(self) -> None:
        seed = {
            "campaign_id": "api-demo",
            "objective": "Call the vendor REST API and set language_name.",
            "tasks": [{"title": "Wire API", "objective": "POST the payload"}],
        }
        inferred = self.mod.infer_tools(seed)
        self.assertTrue(inferred)
        seed_empty = {
            "campaign_id": "mystery",
            "objective": "Do the thing with no signals",
            "tasks": [{"title": "Work", "objective": "work"}],
        }
        primed = Path(tempfile.mkdtemp())
        receipt = self.mod.prove_stack(seed_empty, primed_dir=primed)
        self.assertEqual(receipt["status"], "pass")
        self.assertEqual(receipt.get("skipped"), "no-external-stack")
        self.assertEqual(receipt["tools"], [])

    def test_negated_and_inrepo_mentions_are_not_external_stack(self) -> None:
        seed = {
            "campaign_id": "eie-isolation",
            "objective": (
                "Restore RuleEngine inference and tenant-authoritative persistence. "
                "Greens 30-34 are invariants (no new Neo4j, Redis/NATS bus). "
                "Factor Pydantic validation into load_rules_data. "
                "Transport tenant wins over payload tenant_id. SDK handler tenant is authoritative."
            ),
            "tasks": [
                {
                    "title": "Deterministic RuleEngine inference",
                    "objective": "Wire DomainYamlReader; do not convert PlasticOS to v2.",
                }
            ],
        }
        self.assertEqual(self.mod.infer_tools(seed), [])
        primed = Path(tempfile.mkdtemp())
        os.environ.pop("CONTEXT7_API_KEY", None)
        receipt = self.mod.prove_stack(seed, primed_dir=primed)
        self.assertEqual(receipt.get("skipped"), "no-external-stack")
        self.assertEqual(receipt["status"], "pass")

    def test_positive_neo4j_integration_still_infers(self) -> None:
        seed = {
            "campaign_id": "neo4j-gds",
            "objective": "Add a Neo4j GDS job from the domain YAML gds_jobs section.",
            "tasks": [{"title": "GDS", "objective": "run the driver"}],
        }
        names = [item["name"].lower() for item in self.mod.infer_tools(seed)]
        self.assertIn("neo4j", names)

    def test_forged_receipt_rejected(self) -> None:
        inferred = [{"name": "Context7", "kind": "product"}]
        forged = {
            "schema": self.mod.SCHEMA,
            "status": "pass",
            "tools": [{"name": "Context7", "constraints": ["looks real"]}],
        }
        errors = self.mod.validate_receipt(forged, inferred)
        self.assertTrue(any("fetch evidence" in item for item in errors))

    def test_language_name_contradiction(self) -> None:
        seed = {
            "campaign_id": "seo",
            "objective": 'Set language_name: "en" on the DataForSEO payload',
            "tasks": [],
        }
        receipt = {
            "tools": [
                {
                    "name": "DataForSEO",
                    "constraints": ["language_name must be the full English name"],
                }
            ]
        }
        errors = self.mod.seed_contradicts(seed, receipt)
        self.assertTrue(errors)

    def test_prove_stack_writes_receipt(self) -> None:
        def fetch(url: str, headers=None):
            if "libs/search" in url:
                return 200, json.dumps({"results": [{"id": "/upstash/context7"}]})
            return 200, "language_name must be the full English name. language_code is en."

        with tempfile.TemporaryDirectory() as raw:
            primed = Path(raw)
            seed = {
                "campaign_id": "ctx-demo",
                "objective": "Configure Context7 MCP and the HTTP API",
                "tasks": [{"title": "Docs", "objective": "query-docs"}],
            }
            receipt = self.mod.prove_stack(seed, primed_dir=primed, fetch=fetch)
            self.assertEqual(receipt["status"], "pass")
            path = primed / "ctx-demo" / "stack-proof.json"
            self.assertTrue(path.is_file())
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(loaded["tools"][0]["fetch_evidence"]["digest"])

    def test_an_edited_task_reuses_the_proof_it_did_not_invalidate(self) -> None:
        """An edit elsewhere in the seed must not re-fetch a tool's docs."""

        calls: list[str] = []

        def fetch(url: str, headers=None):
            calls.append(url)
            if "libs/search" in url:
                return 200, json.dumps({"results": [{"id": "/upstash/context7"}]})
            return 200, "language_name must be the full English name. language_code is en."

        class Cache:
            def __init__(self) -> None:
                self.entries: dict[tuple[str, str], Any] = {}

            def get(self, stage: str, key: str) -> Any:
                return self.entries.get((stage, key))

            def put(self, stage: str, key: str, value: Any) -> None:
                self.entries[(stage, key)] = value

        cache = Cache()
        seed = {
            "campaign_id": "ctx-demo",
            "objective": "Configure Context7 MCP and the HTTP API",
            "tasks": [{"title": "Docs", "objective": "query-docs"}],
        }
        with tempfile.TemporaryDirectory() as raw:
            primed = Path(raw)
            self.mod.prove_stack(seed, primed_dir=primed, fetch=fetch, tool_cache=cache)
            first = len(calls)
            self.assertTrue(first, "the first proof fetched nothing")

            edited = {**seed, "tasks": [{"title": "Docs", "objective": "query-docs twice"}]}
            receipt = self.mod.prove_stack(edited, primed_dir=primed, fetch=fetch, tool_cache=cache)

            self.assertEqual(len(calls), first, "an unrelated task edit re-fetched the docs")
            self.assertEqual(receipt["status"], "pass")
            self.assertTrue(receipt["tools"][0]["fetch_evidence"]["digest"])

    def test_missing_key_refuses_on_live_fetch(self) -> None:
        os.environ.pop("CONTEXT7_API_KEY", None)
        seed = {
            "campaign_id": "nokey",
            "objective": "Call the Context7 HTTP API",
            "tasks": [{"title": "API", "objective": "GET docs"}],
        }
        with self.assertRaises(self.mod.StackProofError) as ctx:
            self.mod.prove_stack(seed, primed_dir=Path(tempfile.mkdtemp()))
        self.assertIn("CONTEXT7_API_KEY", str(ctx.exception))

    def test_docs_url_get_failure_refuses(self) -> None:
        def fetch(url: str, headers=None):
            if "libs/search" in url:
                return 404, "{}"
            return 503, "down"

        seed = {
            "campaign_id": "docs-miss",
            "objective": "Call the vendor REST API",
            "docs_url": "https://example.invalid/docs",
            "tasks": [{"title": "API", "objective": "payload"}],
        }
        with self.assertRaises(self.mod.StackProofError):
            self.mod.prove_stack(seed, primed_dir=Path(tempfile.mkdtemp()), fetch=fetch)


if __name__ == "__main__":
    unittest.main()
