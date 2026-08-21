#!/usr/bin/env python3
"""Registry host validation, and the content corrections (B-13, B-15, B-17).

Covers acceptance tests T-27, T-28, T-29, T-30.

`upstream_host` is the only host the broker will contact for a capability, which
makes a wrong value unfixable at call time and invisible at rest. The registry
shipped `api.context7.io` — a domain with no DNS record — so `context7.mcp`
could not have succeeded under any broker or credential.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

from validate_capability_hosts import load_registry, validate  # noqa: E402


def resolver_for(*resolvable: str):
    known = set(resolvable)
    return lambda host: host in known


class CapabilityHostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry()

    # -- T-28 ---------------------------------------------------------------

    def test_context7_points_at_the_host_that_exists(self) -> None:
        entry = next(c for c in self.registry["capabilities"] if c["id"] == "context7.mcp")
        self.assertEqual(entry["upstream_host"], "context7.com")
        self.assertNotEqual(entry["upstream_host"], "api.context7.io")

    def test_shipped_registry_is_syntactically_sound(self) -> None:
        self.assertEqual(validate(self.registry), [])

    def test_shipped_registry_resolves_every_host(self) -> None:
        hosts = {c["upstream_host"] for c in self.registry["capabilities"]}
        self.assertEqual(validate(self.registry, resolve=True, resolver=resolver_for(*hosts)), [])

    # -- T-27 ---------------------------------------------------------------

    def test_unresolvable_host_fails_validation(self) -> None:
        """The exact defect: a syntactically fine hostname that does not exist."""
        registry = {"capabilities": [{"id": "context7.mcp", "upstream_host": "api.context7.io"}]}
        violations = validate(registry, resolve=True, resolver=resolver_for("context7.com"))
        self.assertEqual(len(violations), 1)
        self.assertIn("does not resolve", violations[0])
        self.assertIn("can never succeed", violations[0])

    def test_resolution_is_opt_in_so_offline_ci_is_not_flaky(self) -> None:
        registry = {"capabilities": [{"id": "x", "upstream_host": "api.context7.io"}]}
        self.assertEqual(validate(registry, resolve=False), [])

    def test_a_url_is_rejected(self) -> None:
        registry = {"capabilities": [{"id": "x", "upstream_host": "https://context7.com/v1"}]}
        self.assertIn("want a bare hostname", validate(registry)[0])

    def test_a_host_with_a_port_is_rejected(self) -> None:
        registry = {"capabilities": [{"id": "x", "upstream_host": "context7.com:443"}]}
        self.assertIn("port", validate(registry)[0])

    def test_a_missing_host_is_rejected(self) -> None:
        registry = {"capabilities": [{"id": "x"}]}
        self.assertIn("no upstream_host", validate(registry)[0])

    def test_duplicate_ids_are_rejected(self) -> None:
        registry = {
            "capabilities": [
                {"id": "dup", "upstream_host": "context7.com"},
                {"id": "dup", "upstream_host": "context7.com"},
            ]
        }
        self.assertIn("duplicate capability id", validate(registry)[0])


class SkillReconciliationTests(unittest.TestCase):
    """T-29: the SSOT's skill set, not the 8-skill account-sync copy."""

    def test_ssot_carries_the_full_skill_set(self) -> None:
        skills = sorted(p.parent.name for p in (REPO / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(
            len(skills), 50, "the SSOT should carry the full l9-* skill set, not a subset"
        )
        for expected in ("l9-pr-remediation", "l9-bounded-autonomy", "l9-inspect"):
            self.assertIn(expected, skills)

    def test_installer_reconciles_skills_into_user_scope(self) -> None:
        """Project scope alone is invisible when the project dir is not this repo."""
        install = (REPO / "environment/agents/adapters/claude-code/install.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--scope user", install)
        self.assertIn("--scope project", install)


class AuthorityPointerTests(unittest.TestCase):
    """T-30: doctrine must be reachable from a file that always loads."""

    def test_claude_md_exists_and_is_small_enough_to_always_load(self) -> None:
        path = REPO / "CLAUDE.md"
        self.assertTrue(path.is_file(), "repo root CLAUDE.md must exist")
        size = path.stat().st_size
        self.assertLess(size, 8192, f"CLAUDE.md must stay small enough to always load ({size}B)")

    def test_claude_md_points_at_doctrine_without_duplicating_it(self) -> None:
        body = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        for reference in ("CANONICAL_LAW.md", "AGENTS.md", "surface_profile.yaml"):
            self.assertIn(reference, body)
        canonical = (REPO / "CANONICAL_LAW.md").stat().st_size
        self.assertLess(
            (REPO / "CLAUDE.md").stat().st_size,
            canonical // 4,
            "CLAUDE.md must reference doctrine, not restate it",
        )


if __name__ == "__main__":
    unittest.main()
