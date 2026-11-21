#!/usr/bin/env python3
"""Tests for deriving the Manus capability manifest from the canonical registry.

The contract under test is "one source, no drift": every capability the adapter
exposes is a projection of a registry entry, every registry entry is either
rendered or excluded with a stated reason, and a stale committed manifest is a
failure rather than a latent surprise.
"""

from __future__ import annotations

import importlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPOSITORY = ADAPTER.parents[3]

for entry in (str(ADAPTER), str(REPOSITORY)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import capability_source  # noqa: E402
import render_infisical_capabilities as renderer  # noqa: E402

from ops.secrets.capability_registry import (  # noqa: E402
    CapabilityRegistry,
    CapabilitySpec,
    load_registry,
)
from ops.secrets.surface_trust import classify  # noqa: E402

server = importlib.import_module("infisical_mcp_server")

REGISTRY_PATH = REPOSITORY / capability_source.REGISTRY_RELATIVE


def _spec(**overrides: object) -> CapabilitySpec:
    """A registry entry that the adapter *can* render, before any overrides."""
    base: dict[str, object] = {
        "id": "github.mcp",
        "summary": "synthetic entry for derivation tests",
        "secret_refs": ("GITHUB_TOKEN",),
        "upstream_host": "api.github.com",
        "base_path": "",
        "methods": frozenset({"GET"}),
        "paths": ("/repos/{owner}/{repo}",),
        "params": {"owner": {"source": "caller"}, "repo": {"source": "caller"}},
        "repository_scope": "none",
        "sanitizer": "github_repository_metadata",
        "audit_class": "read_advisory",
        "failure_semantics": "degrade",
        "surfaces": frozenset({"model-controlled"}),
        "max_response_bytes": 1 << 20,
        "max_requests_per_minute": 30,
    }
    base.update(overrides)
    return CapabilitySpec(**base)  # type: ignore[arg-type]


def _manifest() -> dict:
    return json.loads(renderer.manifest_path(REPOSITORY).read_text(encoding="utf-8"))


def _exclusions(manifest: dict) -> dict[str, dict]:
    return {entry["registry_id"]: entry for entry in manifest["exclusions"]}


class CommittedManifestTests(unittest.TestCase):
    """The committed file must be the render of the committed registry."""

    def test_committed_manifest_is_current_with_the_registry(self) -> None:
        self.assertEqual(renderer.check(REPOSITORY), 0)

    def test_manifest_declares_itself_derived(self) -> None:
        generated = _manifest()["generated"]
        self.assertIs(generated["do_not_edit"], True)
        self.assertEqual(generated["source"], "ops/secrets/capabilities.yaml")
        self.assertEqual(generated["source_sha256"], capability_source.source_digest(REGISTRY_PATH))
        self.assertEqual(generated["surface"], "manus")
        self.assertEqual(generated["trust_class"], "model-controlled")

    def test_stale_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ops/secrets").mkdir(parents=True)
            shutil.copy(REGISTRY_PATH, root / capability_source.REGISTRY_RELATIVE)
            tampered = _manifest()
            tampered["capabilities"]["github.get_repository"]["method"] = "POST"
            path = renderer.manifest_path(root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(renderer.check(root), 1)

    def test_registry_edit_without_render_is_rejected(self) -> None:
        # The real drift this work exists to prevent: the registry changes and
        # nobody re-renders. Simulate by rendering against a grown registry.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ops/secrets").mkdir(parents=True)
            grown = REGISTRY_PATH.read_text(encoding="utf-8") + (
                "\n  - id: github.tags_read\n"
                "    summary: synthetic\n"
                "    secret_refs: [GITHUB_TOKEN]\n"
                "    upstream_host: api.github.com\n"
                '    base_path: ""\n'
                "    methods: [GET]\n"
                '    paths: ["/repos/{owner}/{repo}/tags"]\n'
                "    params:\n"
                "      owner: {source: caller, validate: text}\n"
                "      repo: {source: caller, validate: text}\n"
                "    repository_scope: none\n"
                "    sanitizer: github_repository_metadata\n"
                "    audit_class: read_advisory\n"
            )
            (root / capability_source.REGISTRY_RELATIVE).write_text(grown, encoding="utf-8")
            path = renderer.manifest_path(root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                renderer.manifest_path(REPOSITORY).read_text(encoding="utf-8"), encoding="utf-8"
            )
            self.assertEqual(renderer.check(root), 1)

    def test_rendered_manifest_loads_through_the_server_loader(self) -> None:
        capabilities = server.load_capabilities(renderer.manifest_path(REPOSITORY))
        self.assertEqual(sorted(capabilities), ["github.get_repository"])

    def test_manifest_carries_no_secret_material(self) -> None:
        rendered = renderer.manifest_path(REPOSITORY).read_text(encoding="utf-8")
        self.assertNotIn("secretValue", rendered)
        self.assertNotIn("secret_value", rendered)


class ParityTests(unittest.TestCase):
    """Rendered facts must equal registry facts, and nothing may vanish silently."""

    def setUp(self) -> None:
        self.registry = load_registry(REGISTRY_PATH)
        self.manifest = _manifest()

    def test_every_rendered_capability_matches_the_registry(self) -> None:
        for identifier, item in self.manifest["capabilities"].items():
            with self.subTest(capability=identifier):
                provenance = item["provenance"]
                spec = self.registry.get(provenance["registry_id"])
                self.assertIsNotNone(spec)
                assert spec is not None
                self.assertEqual(item["origin"], f"https://{spec.upstream_host}{spec.base_path}")
                self.assertIn(item["method"], spec.methods)
                self.assertIn(item["path_template"], spec.paths)
                self.assertIn(item["secret_key"], spec.secret_refs)
                self.assertEqual(provenance["registry_method"], item["method"])
                self.assertEqual(provenance["registry_path"], item["path_template"])

    def test_rendered_arguments_are_sanctioned_caller_parameters(self) -> None:
        for identifier, item in self.manifest["capabilities"].items():
            spec = self.registry.get(item["provenance"]["registry_id"])
            assert spec is not None
            with self.subTest(capability=identifier):
                self.assertEqual(
                    sorted(item["arguments"]),
                    sorted(
                        server.load_capabilities(renderer.manifest_path(REPOSITORY))[
                            identifier
                        ].arguments
                    ),
                )
                for name in item["arguments"]:
                    self.assertEqual(spec.params[name]["source"], "caller")

    def test_every_registry_entry_is_rendered_or_excluded_with_a_reason(self) -> None:
        rendered = {
            item["provenance"]["registry_id"] for item in self.manifest["capabilities"].values()
        }
        excluded = _exclusions(self.manifest)
        self.assertEqual(len(excluded), len(self.manifest["exclusions"]))
        self.assertEqual(rendered | set(excluded), set(self.registry.ids()))
        for entry in self.manifest["exclusions"]:
            with self.subTest(entry=entry["registry_id"]):
                self.assertIn(entry["disposition"], {"excluded", "partially_rendered"})
                self.assertTrue(entry["reason"])
                self.assertTrue(entry["reason_code"])

    def test_exclusion_reasons_name_the_actual_blocker(self) -> None:
        entries = _exclusions(self.manifest)
        self.assertEqual(entries["sonar.read_issues"]["reason_code"], "unsupported_upstream_host")
        self.assertIn("sonarcloud.io", entries["sonar.read_issues"]["reason"])
        self.assertEqual(entries["github.pr_read"]["reason_code"], "unsupported_secret_ref")
        self.assertIn("GH_TOKEN", entries["github.pr_read"]["reason"])
        self.assertEqual(
            entries["github.packages_read"]["reason_code"], "unsupported_upstream_host"
        )
        self.assertIn("npm.pkg.github.com", entries["github.packages_read"]["reason"])

    def test_partial_render_accounts_for_every_unrendered_endpoint(self) -> None:
        entry = _exclusions(self.manifest)["github.mcp"]
        spec = self.registry.get("github.mcp")
        assert spec is not None
        self.assertEqual(entry["disposition"], "partially_rendered")
        self.assertEqual(entry["rendered_capability_ids"], ["github.get_repository"])
        self.assertEqual(len(spec.paths), 21)
        self.assertEqual(len(entry["unrendered_paths"]), 20)
        self.assertEqual(
            set(entry["unrendered_paths"]) | {"/repos/{owner}/{repo}"}, set(spec.paths)
        )
        self.assertEqual(entry["unrendered_methods"], ["POST"])
        self.assertNotIn("/repos/{owner}/{repo}", entry["unrendered_paths"])

    def test_narrowings_record_where_the_adapter_is_stricter(self) -> None:
        rows = {(row["capability_id"], row["field"]): row for row in self.manifest["narrowings"]}
        self.assertEqual(rows[("github.get_repository", "method")]["registry"], "GET, POST")
        self.assertEqual(rows[("github.get_repository", "sanitizer")]["registry"], "passthrough")
        self.assertEqual(
            rows[("github.get_repository", "sanitizer")]["adapter"],
            "github_repository_metadata",
        )
        self.assertIn(("github.get_repository", "param.owner"), rows)


class PinnedPostureTests(unittest.TestCase):
    """Constants that mirror hard-coded server checks must not drift apart."""

    def test_adapter_origin_matches_the_server_allowlist(self) -> None:
        self.assertEqual(capability_source.ADAPTER_ORIGIN, server.GITHUB_API_ORIGIN)

    def test_manus_trust_class_matches_surface_trust(self) -> None:
        self.assertEqual(capability_source.MANUS_TRUST_CLASS, classify("manus").trust_class)
        self.assertEqual(capability_source.MANUS_TRUST_CLASS, "model-controlled")

    def test_argument_patterns_reject_separators_and_whitespace(self) -> None:
        capability = server.load_capabilities(renderer.manifest_path(REPOSITORY))[
            "github.get_repository"
        ]
        for bad in ("invalid/owner", "with space", "owner\n", "a" * 40, ""):
            with self.subTest(value=bad):
                with self.assertRaises(server.SafeMcpError):
                    capability.render_path({"owner": bad, "repo": "Cursor-Governance"})
        for bad in ("repo/name", "repo name", "r" * 101):
            with self.subTest(value=bad):
                with self.assertRaises(server.SafeMcpError):
                    capability.render_path({"owner": "Quantum-L9", "repo": bad})


class DerivationFailClosedTests(unittest.TestCase):
    """A projection that no longer matches the registry must fail, not shrink."""

    def test_projection_to_an_undeclared_registry_id_fails(self) -> None:
        with self.assertRaisesRegex(capability_source.DerivationError, "does not declare"):
            capability_source.derive(CapabilityRegistry({}), source_sha256="0")

    def test_projection_to_an_unlisted_path_fails(self) -> None:
        registry = CapabilityRegistry({"github.mcp": _spec(paths=("/elsewhere",))})
        with self.assertRaisesRegex(capability_source.DerivationError, "does not allow-list"):
            capability_source.derive(registry, source_sha256="0")

    def test_projection_using_a_non_caller_parameter_fails(self) -> None:
        registry = CapabilityRegistry(
            {
                "github.mcp": _spec(
                    params={
                        "owner": {"source": "workspace", "from": "git_remote"},
                        "repo": {"source": "caller"},
                    }
                )
            }
        )
        with self.assertRaisesRegex(capability_source.DerivationError, "caller-controlled"):
            capability_source.derive(registry, source_sha256="0")

    def test_projection_to_a_write_method_fails(self) -> None:
        write = capability_source.Projection(
            capability_id="github.write",
            registry_id="github.mcp",
            method="POST",
            path="/repos/{owner}/{repo}",
            sanitizer="github_repository_metadata",
            description="",
            arguments={"owner": "[a-z]+", "repo": "[a-z]+"},
        )
        registry = CapabilityRegistry({"github.mcp": _spec(methods=frozenset({"GET", "POST"}))})
        with self.assertRaisesRegex(capability_source.DerivationError, "read-only"):
            capability_source.derive(registry, source_sha256="0", projections=(write,))

    def test_projection_to_a_foreign_host_fails(self) -> None:
        registry = CapabilityRegistry({"github.mcp": _spec(upstream_host="api.gitguardian.com")})
        with self.assertRaisesRegex(capability_source.DerivationError, "only reaches"):
            capability_source.derive(registry, source_sha256="0")


class RegistryGrowthTests(unittest.TestCase):
    """A registry addition must change the rendered output, one way or another."""

    def test_a_gained_entry_becomes_an_explicit_exclusion(self) -> None:
        base = {"github.mcp": _spec()}
        before = capability_source.derive(CapabilityRegistry(base), source_sha256="a")
        grown = dict(base)
        grown["github.tags_read"] = _spec(
            id="github.tags_read", paths=("/repos/{owner}/{repo}/tags",)
        )
        after = capability_source.derive(CapabilityRegistry(grown), source_sha256="b")
        self.assertNotIn("github.tags_read", [entry["registry_id"] for entry in before.exclusions])
        entry = {item["registry_id"]: item for item in after.exclusions}["github.tags_read"]
        self.assertEqual(entry["reason_code"], "not_projected")
        self.assertIn("no reviewed projection", entry["reason"])
        self.assertNotEqual(before.manifest(), after.manifest())

    def test_a_gained_unrenderable_entry_is_explained(self) -> None:
        base = {"github.mcp": _spec()}
        grown = dict(base)
        grown["sonar.read_issues"] = _spec(
            id="sonar.read_issues",
            upstream_host="sonarcloud.io",
            base_path="/api",
            secret_refs=("SONAR_TOKEN",),
            sanitizer="sonar_issue_snapshot",
            paths=("/issues/search", "/rules/show"),
        )
        derivation = capability_source.derive(CapabilityRegistry(grown), source_sha256="c")
        entry = {item["registry_id"]: item for item in derivation.exclusions}["sonar.read_issues"]
        self.assertEqual(entry["reason_code"], "unsupported_upstream_host")
        self.assertIn("sonarcloud.io", entry["reason"])
        self.assertEqual(len(entry["unrendered_paths"]), 2)

    def test_an_entry_without_the_manus_surface_is_excluded_by_surface(self) -> None:
        # The surface filter is a real gate, not a formality: an entry that is
        # otherwise perfectly renderable still fails if its surfaces do not
        # admit the Manus trust class.
        registry = CapabilityRegistry(
            {
                "github.mcp": _spec(),
                "github.operator_only": _spec(
                    id="github.operator_only",
                    paths=("/repos/{owner}/{repo}/topics",),
                    surfaces=frozenset({"trusted-operator"}),
                ),
            }
        )
        derivation = capability_source.derive(registry, source_sha256="d")
        self.assertEqual(sorted(derivation.capabilities), ["github.get_repository"])
        entry = {item["registry_id"]: item for item in derivation.exclusions}[
            "github.operator_only"
        ]
        self.assertEqual(entry["reason_code"], "surface_not_admissible")
        self.assertIn("model-controlled", entry["reason"])
        self.assertEqual(entry["disposition"], "excluded")

    def test_source_digest_tracks_the_registry_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capabilities.yaml"
            path.write_text("schema_version: '1.0.0'\n", encoding="utf-8")
            first = capability_source.source_digest(path)
            path.write_text("schema_version: '1.0.1'\n", encoding="utf-8")
            self.assertNotEqual(first, capability_source.source_digest(path))


class ServerRefusalTests(unittest.TestCase):
    """Fail closed at the invocation boundary, before any network call."""

    ENV = {
        "L9_MANUS_INFISICAL_CLIENT_ID": "fixture-client-id",
        "L9_MANUS_INFISICAL_CLIENT_SECRET": "fixture-bootstrap-secret",
        "L9_MANUS_INFISICAL_PROJECT_ID": "fixture-project-id",
    }

    def test_unknown_capability_is_refused_before_any_network_call(self) -> None:
        calls: list[tuple] = []

        def requester(*args: object) -> dict:
            calls.append(args)
            raise AssertionError("no network call may precede capability validation")

        mcp = server.ManusInfisicalMcp(env=self.ENV, request_json=requester)
        response = mcp.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "infisical_invoke",
                    "arguments": {"capability": "github.delete_repository", "arguments": {}},
                },
            }
        )
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        self.assertIn("unknown capability", response["result"]["content"][0]["text"])
        self.assertEqual(calls, [])

    def test_status_exposes_exclusions_without_secret_material(self) -> None:
        def requester(*args: object) -> dict:
            raise AssertionError("status must not authenticate")

        mcp = server.ManusInfisicalMcp(env=self.ENV, request_json=requester)
        status = mcp.client.status(mcp.capabilities, mcp.exclusions)
        rendered = json.dumps(status)
        self.assertFalse(status["secret_values_exposed"])
        self.assertEqual(status["capability_exclusion_count"], len(mcp.exclusions))
        self.assertIn(
            "github.pr_read", [entry["registry_id"] for entry in status["capability_exclusions"]]
        )
        self.assertNotIn("fixture-bootstrap-secret", rendered)
        for entry in status["capability_exclusions"]:
            self.assertEqual(set(entry), {"registry_id", "reason_code"})

    def test_status_remains_valid_without_an_exclusion_list(self) -> None:
        mcp = server.ManusInfisicalMcp(env=self.ENV, request_json=lambda *a: {})
        status = mcp.client.status(mcp.capabilities)
        self.assertEqual(status["capability_exclusions"], [])
        self.assertEqual(status["capability_exclusion_count"], 0)


class ImportPurityTests(unittest.TestCase):
    """Derivation is file I/O only; the connector never gains a network import."""

    def test_derivation_modules_import_no_transport(self) -> None:
        for module in (capability_source.__file__, renderer.__file__):
            source = Path(module).read_text(encoding="utf-8")
            for forbidden in ("urllib", "requests", "socket", "http.client", "subprocess"):
                with self.subTest(module=Path(module).name, forbidden=forbidden):
                    self.assertNotIn(forbidden, source)

    def test_server_starts_without_credentials(self) -> None:
        mcp = server.ManusInfisicalMcp(env={}, request_json=lambda *a: {})
        status = mcp.client.status(mcp.capabilities, mcp.exclusions)
        self.assertEqual(status["status"], "missing_configuration")
        self.assertFalse(status["secret_values_exposed"])


if __name__ == "__main__":
    unittest.main()
