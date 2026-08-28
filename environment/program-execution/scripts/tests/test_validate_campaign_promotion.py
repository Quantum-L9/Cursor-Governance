from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PE_ROOT.parents[1]
MODULE_PATH = PE_ROOT / "scripts/validate_campaign_promotion.py"

_spec = importlib.util.spec_from_file_location("validate_campaign_promotion", MODULE_PATH)
assert _spec and _spec.loader
validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validator)


SURFACE_PROFILE = """\
campaign_execution:
  require_make_pr: true
  campaigns:
    alpha-v1:
      integration_branch: campaign/alpha-v1
    beta-v1:
      integration_branch: campaign/beta-v1
"""

EXECUTION_POLICY = """\
schema: l9.program-execution.campaign-execution-policy.v1
campaigns:
  - id: alpha-v1
    integration_branch: campaign/alpha-v1
    pr_base: campaign/alpha-v1
    execute_order: 1
  - id: beta-v1
    integration_branch: campaign/beta-v1
    pr_base: campaign/beta-v1
    execute_order: 2
"""

COMPILE_ALLOWLIST = """\
schema: l9.program-execution.campaign-compile-allowlist.v1
campaign_ids:
  - alpha-v1
  - beta-v1
"""

STATUS_LEDGER = """\
schema: l9.program-execution.campaign-status-ledger.v1
campaigns:
  - id: alpha-v1
    lifecycle: complete
    verdict: CONVERGED
    evidence:
      pull_request: "https://github.com/Quantum-L9/Cursor-Governance/pull/149"
      merge_sha: 63efde4fdb6f99b0e7e7834211a803b564673351
  - id: beta-v1
    lifecycle: in_progress
    launched_by: make campaign
"""


def build_repo(root: Path) -> None:
    """Materialize a minimal, fully valid promotion surface."""
    write(root / validator.SURFACE_PROFILE, SURFACE_PROFILE)
    write(root / validator.EXECUTION_POLICY, EXECUTION_POLICY)
    write(root / validator.COMPILE_ALLOWLIST, COMPILE_ALLOWLIST)
    write(root / validator.STATUS_LEDGER, STATUS_LEDGER)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class PromotionValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        build_repo(self.root)

    def assertFailsWith(self, report: dict, needle: str) -> None:
        self.assertEqual(report["status"], "FAIL")
        joined = "\n".join(report["errors"])
        self.assertIn(needle, joined)

    # -- baseline ---------------------------------------------------------

    def test_valid_promotion_passes(self) -> None:
        report = validator.validate(self.root)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(
            report["summary"],
            {
                "SURFACE_PROFILE_VALID": "PASS",
                "CAMPAIGN_REGISTRATION_VALID": "PASS",
                "MACHINE_LOCAL_PATHS_IN_SHARED_LEDGER": 0,
            },
        )

    # -- condition 1: surface profile parses -------------------------------

    def test_unparseable_surface_profile_fails(self) -> None:
        # Exactly the PR #224 corruption: the next campaign key was appended
        # onto the previous entry's value line.
        write(
            self.root / validator.SURFACE_PROFILE,
            SURFACE_PROFILE.replace(
                "      integration_branch: campaign/alpha-v1\n",
                "      integration_branch: campaign/alpha-v1    beta-v1:\n",
            ),
        )
        report = validator.validate(self.root)
        self.assertFailsWith(report, "does not parse")
        self.assertEqual(report["summary"]["SURFACE_PROFILE_VALID"], "FAIL")

    def test_missing_surface_profile_fails(self) -> None:
        (self.root / validator.SURFACE_PROFILE).unlink()
        self.assertFailsWith(validator.validate(self.root), "missing")

    # -- condition 2: registrations are well formed ------------------------

    def test_registration_without_integration_branch_fails(self) -> None:
        write(
            self.root / validator.SURFACE_PROFILE,
            "campaign_execution:\n  campaigns:\n    alpha-v1:\n      lane: pe_host\n",
        )
        self.assertFailsWith(
            validator.validate(self.root), "integration_branch must be a non-empty string"
        )

    def test_scalar_registration_fails(self) -> None:
        write(
            self.root / validator.SURFACE_PROFILE,
            "campaign_execution:\n  campaigns:\n    alpha-v1: campaign/alpha-v1\n",
        )
        self.assertFailsWith(validator.validate(self.root), "registration must be a mapping")

    def test_campaigns_must_be_a_mapping(self) -> None:
        write(
            self.root / validator.SURFACE_PROFILE,
            "campaign_execution:\n  campaigns:\n    - alpha-v1\n",
        )
        self.assertFailsWith(validator.validate(self.root), "campaigns must be a mapping")

    # -- condition 3: id collisions ----------------------------------------

    def test_duplicate_yaml_key_fails(self) -> None:
        # yaml.safe_load silently keeps the last duplicate; the validator must not.
        write(
            self.root / validator.SURFACE_PROFILE,
            SURFACE_PROFILE + "    alpha-v1:\n      integration_branch: campaign/alpha-v1\n",
        )
        self.assertFailsWith(validator.validate(self.root), "duplicate key")

    def test_duplicate_policy_id_fails(self) -> None:
        write(
            self.root / validator.EXECUTION_POLICY,
            EXECUTION_POLICY + "  - id: alpha-v1\n    integration_branch: campaign/alpha-v1\n",
        )
        self.assertFailsWith(validator.validate(self.root), "duplicate campaign id")

    def test_duplicate_allowlist_id_fails(self) -> None:
        write(self.root / validator.COMPILE_ALLOWLIST, COMPILE_ALLOWLIST + "  - alpha-v1\n")
        self.assertFailsWith(validator.validate(self.root), "duplicate campaign id")

    def test_duplicate_ledger_id_fails(self) -> None:
        write(
            self.root / validator.STATUS_LEDGER,
            STATUS_LEDGER + "  - id: alpha-v1\n    lifecycle: planned\n",
        )
        self.assertFailsWith(validator.validate(self.root), "duplicate campaign id")

    # -- condition 4: integration_branch matches the id --------------------

    def test_mismatched_integration_branch_fails(self) -> None:
        write(
            self.root / validator.SURFACE_PROFILE,
            SURFACE_PROFILE.replace("campaign/beta-v1", "campaign/beta-v2"),
        )
        self.assertFailsWith(validator.validate(self.root), "!= 'campaign/beta-v1'")

    def test_mismatched_policy_pr_base_fails(self) -> None:
        write(
            self.root / validator.EXECUTION_POLICY,
            EXECUTION_POLICY.replace("pr_base: campaign/beta-v1", "pr_base: main"),
        )
        self.assertFailsWith(validator.validate(self.root), "pr_base 'main'")

    def test_promoted_campaign_absent_from_policy_fails(self) -> None:
        write(
            self.root / validator.EXECUTION_POLICY,
            EXECUTION_POLICY.split("  - id: beta-v1")[0],
        )
        self.assertFailsWith(validator.validate(self.root), "absent from policy")

    def test_promoted_campaign_absent_from_allowlist_passes(self) -> None:
        """Allowlist membership is not admission, so absence is not a failure.

        The inverted assertion this replaces made every new campaign wait on an
        edit to a shared registry before it could compile.
        """
        write(
            self.root / validator.COMPILE_ALLOWLIST,
            COMPILE_ALLOWLIST.replace("  - beta-v1\n", ""),
        )
        report = validator.validate(self.root)
        self.assertEqual(report["status"], "PASS", msg=json.dumps(report["errors"], indent=2))

    def test_duplicate_allowlist_entry_still_fails(self) -> None:
        """It is still a ledger; a broken ledger is still worth reporting."""
        write(
            self.root / validator.COMPILE_ALLOWLIST,
            COMPILE_ALLOWLIST + "  - beta-v1\n",
        )
        self.assertFailsWith(validator.validate(self.root), "duplicate campaign id")

    # -- condition 5: machine-local paths ----------------------------------

    def test_machine_local_path_in_ledger_fails(self) -> None:
        write(
            self.root / validator.STATUS_LEDGER,
            STATUS_LEDGER + "    worktree: /Users/macm2/.l9/program-worktrees/beta-v1\n",
        )
        report = validator.validate(self.root)
        self.assertFailsWith(report, "machine-local path in shared campaign ledger")
        self.assertEqual(report["summary"]["MACHINE_LOCAL_PATHS_IN_SHARED_LEDGER"], 1)

    def test_tilde_and_windows_paths_are_detected(self) -> None:
        write(
            self.root / validator.STATUS_LEDGER,
            STATUS_LEDGER
            + "    blueprint: ~/.l9/blueprints/beta-v1\n    cache: C:\\Users\\l9\\cache\n",
        )
        report = validator.validate(self.root)
        self.assertEqual(report["summary"]["MACHINE_LOCAL_PATHS_IN_SHARED_LEDGER"], 2)

    def test_https_url_is_not_a_machine_local_path(self) -> None:
        # The baseline ledger carries a github.com pull_request URL; a naive
        # drive-letter pattern would match the "s:" in "https:".
        report = validator.validate(self.root)
        self.assertEqual(report["summary"]["MACHINE_LOCAL_PATHS_IN_SHARED_LEDGER"], 0)

    def test_archive_paths_warn_but_do_not_fail(self) -> None:
        write(
            self.root / validator.CAMPAIGNS_DIR / "alpha-v1/history/v1.0.0/handoff.json",
            json.dumps({"receipt": "/home/user/.l9/programs/alpha-v1/receipt.json"}),
        )
        report = validator.validate(self.root)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("immutable campaign evidence", report["warnings"][0])

    # -- the top-level PE MANIFEST is not this validator's business ---------
    #
    # It is not advisory: sync_generated_artifacts.py --pe-manifest regenerates
    # it on the PR gate, governance-self-check.yml fails on drift, and
    # validate_manifest.py enforces it under make program-execution-conformance.
    # Promotion validity is a separate question, and coupling the two once made
    # every ordinary PE edit fail promotion. These pin the decoupling.

    def test_stale_top_level_pe_manifest_does_not_fail_promotion(self) -> None:
        manifest = self.root / "environment/program-execution/MANIFEST.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"generated": "stale"}\n', encoding="utf-8")
        report = validator.validate(self.root)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertNotIn("GENERATED_ARTIFACTS_CURRENT", report["summary"])

    def test_missing_top_level_pe_manifest_does_not_fail_promotion(self) -> None:
        manifest = self.root / "environment/program-execution/MANIFEST.json"
        if manifest.exists():
            manifest.unlink()
        report = validator.validate(self.root)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertNotIn("GENERATED_ARTIFACTS_CURRENT", report["summary"])


class RealRepositoryTest(unittest.TestCase):
    """The promotion surface actually committed in this repository."""

    def test_repository_promotion_is_valid(self) -> None:
        report = validator.validate(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])

    def test_every_registered_campaign_uses_its_own_branch(self) -> None:
        profile = yaml.safe_load(
            (REPO_ROOT / validator.SURFACE_PROFILE).read_text(encoding="utf-8")
        )
        campaigns = profile["campaign_execution"]["campaigns"]
        self.assertIn("pe-router-capability-safety-v4", campaigns)
        for campaign_id, entry in campaigns.items():
            self.assertEqual(entry["integration_branch"], f"campaign/{campaign_id}")


if __name__ == "__main__":
    unittest.main()
