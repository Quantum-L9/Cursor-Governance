"""Program Execution's connection to the Autonomy Surface Profile.

The pipeline runs only at the stage the profile names, only on the operator's
explicit statement, inside the profile's lanes, and bound to the admitted
coding-agent execution projection. Each of those is a refusal here before it
is anything else.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
import unittest.mock
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
GOV_ROOT = PE_ROOT.parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_run_campaign import (  # type: ignore[import-not-found]  # noqa: E402
    OPERATOR_INVOCATION_ENV,
    SCRIPT,
    _load,
)


def _module():
    spec = importlib.util.spec_from_file_location(
        "campaign_authority_under_test", PE_ROOT / "scripts/campaign_authority.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


authority = _module()
LIVE = authority.load_campaign_authority(GOV_ROOT)


def _profile(tmp: Path, block: object) -> Path:
    path = tmp / authority.SURFACE_PROFILE
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"authority_order": ["CANONICAL_LAW"]}
    if block is not None:
        document["campaign_execution"] = block
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return tmp


class ProfileBlockTests(unittest.TestCase):
    def test_the_live_profile_connects_program_execution_at_the_manual_stage(self) -> None:
        self.assertEqual(LIVE["stage"], "manual")
        self.assertEqual(LIVE["invocation"], "explicit_operator_only")
        self.assertEqual(LIVE["ambient_routing"], "forbidden")
        self.assertEqual(LIVE["make_target"], "not_registered")
        self.assertEqual(LIVE["autonomy"]["provider"], "root-autonomy-control-plane")
        self.assertIs(LIVE["autonomy"]["owns_program_state"], False)
        self.assertEqual(
            LIVE["projection_binding"]["profile_ref"], "l9.projection/coding-agent-execution@1"
        )
        for relative in (
            LIVE["runner"],
            LIVE["autonomy"]["effect_enforcement"],
            LIVE["autonomy"]["concurrency_policy"],
            LIVE["projection_binding"]["binding"],
        ):
            self.assertTrue((GOV_ROOT / relative).is_file(), relative)

    def test_the_pipeline_binds_what_the_coding_agent_mode_selects(self) -> None:
        """One selection, two consumers: a session (/coding-agent) and a campaign."""
        declared = LIVE["projection_binding"]
        mode = yaml.safe_load((GOV_ROOT / declared["mode_contract"]).read_text("utf-8"))
        selected = {item["ref"]: item for item in mode["selection"]["projections"]}
        self.assertIn(declared["profile_ref"], selected)
        self.assertEqual(selected[declared["profile_ref"]]["binding"], declared["binding"])
        self.assertIs(selected[declared["profile_ref"]]["required"], True)

    def test_the_session_start_block_does_not_advertise_program_execution(self) -> None:
        """Connected is not ambient: no session is told the pipeline exists."""
        profile = yaml.safe_load((GOV_ROOT / authority.SURFACE_PROFILE).read_text("utf-8"))
        for key in ("session_start_block", "llm_rules_override"):
            self.assertNotIn("program-execution", profile[key])
            self.assertNotIn("run_campaign", profile[key])

    def test_the_root_make_graph_still_does_not_compose_program_execution(self) -> None:
        for name in ("Makefile", "Repo.mk"):
            self.assertNotIn(
                "ops/make/program-execution.mk", (GOV_ROOT / name).read_text("utf-8"), name
            )

    def _refused(self, block: object, code: str) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = _profile(Path(raw), block)
            with self.assertRaises(authority.CampaignAuthorityError) as caught:
                authority.load_campaign_authority(root)
        self.assertEqual(caught.exception.code, code)

    def test_an_absent_block_is_retirement(self) -> None:
        self._refused(None, "CAMPAIGN_AUTHORITY_ABSENT")

    def test_an_unknown_stage_executes_nothing(self) -> None:
        for stage in ("retired", "registered", "", "autonomous"):
            self._refused({**LIVE, "stage": stage}, "CAMPAIGN_STAGE_NOT_EXECUTABLE")

    def test_a_block_that_widens_publication_authority_is_refused(self) -> None:
        for action in ("push", "pull_request", "merge"):
            self._refused({**LIVE, action: "allowed"}, "CAMPAIGN_AUTHORITY_WIDENED")
        # Merge is never a campaign act, even through the make pr route.
        self._refused({**LIVE, "merge": "via_make_pr_only"}, "CAMPAIGN_AUTHORITY_WIDENED")
        # The only publication route is the governance SSOT make pr.
        publication = LIVE["publication"]
        self._refused({**LIVE, "publication": None}, "CAMPAIGN_AUTHORITY_WIDENED")
        self._refused(
            {**LIVE, "publication": {**publication, "route": "raw_push"}},
            "CAMPAIGN_AUTHORITY_WIDENED",
        )
        for raw in ("raw_push", "raw_pull_request"):
            self._refused(
                {**LIVE, "publication": {**publication, raw: "allowed"}},
                "CAMPAIGN_AUTHORITY_WIDENED",
            )

    def test_the_live_block_publishes_only_through_the_ssot_make_pr(self) -> None:
        self.assertEqual(LIVE["push"], "via_make_pr_only")
        self.assertEqual(LIVE["pull_request"], "via_make_pr_only")
        self.assertEqual(LIVE["merge"], "forbidden")
        self.assertEqual(LIVE["completion_boundary"], "pr")
        self.assertEqual(LIVE["publication"]["route"], "make_pr_ssot")
        self.assertEqual(LIVE["publication"]["remediate"], "0")

    def test_a_block_naming_another_autonomy_provider_is_refused(self) -> None:
        self._refused(
            {**LIVE, "autonomy": {**LIVE["autonomy"], "provider": "someone-else"}},
            "CAMPAIGN_AUTONOMY_PROVIDER_INVALID",
        )
        self._refused(
            {**LIVE, "autonomy": {**LIVE["autonomy"], "owns_program_state": True}},
            "CAMPAIGN_AUTONOMY_PROVIDER_INVALID",
        )


class OperatorInvocationTests(unittest.TestCase):
    def test_no_statement_no_run(self) -> None:
        with self.assertRaises(authority.CampaignAuthorityError) as caught:
            authority.operator_invocation(LIVE, {})
        self.assertEqual(caught.exception.code, "OPERATOR_INVOCATION_REQUIRED")

    def test_a_flag_is_not_a_statement(self) -> None:
        for value in ("1", "true", "YES", "ok", "go", "   "):
            with self.assertRaises(authority.CampaignAuthorityError, msg=value):
                authority.operator_invocation(LIVE, {OPERATOR_INVOCATION_ENV: value})

    def test_the_operators_words_are_recorded_verbatim(self) -> None:
        statement = "run the pec-live-proof-v1 campaign through Program Execution"
        record = authority.operator_invocation(
            LIVE,
            {
                OPERATOR_INVOCATION_ENV: statement,
                "L9_GOVERNANCE_SURFACE": "claude-code",
                "CLAUDE_CODE_SESSION_ID": "session-x",
            },
        )
        self.assertEqual(record["statement"], statement)
        self.assertEqual(record["stage"], "manual")
        self.assertEqual(record["host_session_id"], "session-x")
        self.assertTrue(record["statement_digest"].startswith("sha256:"))

    def test_each_run_appends_and_none_is_rewritten(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            first = authority.operator_invocation(
                LIVE, {OPERATOR_INVOCATION_ENV: "start the demo campaign"}
            )
            second = authority.operator_invocation(
                LIVE, {OPERATOR_INVOCATION_ENV: "resume the demo campaign"}
            )
            authority.record_invocation(workspace, first)
            path = authority.record_invocation(workspace, second)
            log = json.loads(path.read_text("utf-8"))["invocations"]
        self.assertEqual(
            [item["statement"] for item in log],
            ["start the demo campaign", "resume the demo campaign"],
        )

    def test_the_runner_refuses_before_it_reads_its_input(self) -> None:
        """The public entry, with no statement: nothing is compiled or written."""
        import tempfile

        runner = _load("run_campaign_authority_guard", SCRIPT)
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            env = {k: v for k, v in os.environ.items() if k != OPERATOR_INVOCATION_ENV}
            with unittest.mock.patch.dict("os.environ", env, clear=True):
                with self.assertRaises(runner.CampaignError) as caught:
                    runner.run_campaign(
                        tmp / "does-not-exist.yaml",
                        until="execute",
                        primary=tmp / "primary",
                        repo_root=tmp / "host",
                        l9_root=tmp / "l9",
                    )
            self.assertEqual(caught.exception.error_code, "OPERATOR_INVOCATION_REQUIRED")
            self.assertEqual(list(tmp.iterdir()), [])


class LaneCeilingTests(unittest.TestCase):
    def test_the_ceiling_is_the_autonomy_profiles(self) -> None:
        ceiling = authority.lane_ceiling(GOV_ROOT, {"L9_GOVERNANCE_SURFACE": "claude-code"})
        policy = json.loads(
            (GOV_ROOT / "ops/autonomy/claude-execution-profiles.json").read_text("utf-8")
        )
        granted = policy["profiles"][ceiling["profile"]]
        self.assertEqual(ceiling["total_lanes"], granted["max_parallel"])
        self.assertEqual(ceiling["mutation_lanes"], granted["max_mutation_lanes"])

    def test_resolving_the_ceiling_leaves_sys_path_as_it_found_it(self) -> None:
        before = list(sys.path)
        authority.lane_ceiling(GOV_ROOT, {})
        self.assertEqual(sys.path, before)

    def test_program_execution_may_narrow_the_lanes(self) -> None:
        ceiling = {"profile": "p", "total_lanes": 8, "mutation_lanes": 4}
        self.assertEqual(authority.narrowed_lanes(ceiling, total_lanes=4, mutation_lanes=2), (4, 2))
        self.assertEqual(authority.narrowed_lanes(ceiling, total_lanes=8, mutation_lanes=4), (8, 4))

    def test_program_execution_may_not_exceed_them(self) -> None:
        ceiling = {"profile": "p", "total_lanes": 8, "mutation_lanes": 4}
        for total, mutation in ((9, 1), (1, 5)):
            with self.assertRaises(authority.CampaignAuthorityError) as caught:
                authority.narrowed_lanes(ceiling, total_lanes=total, mutation_lanes=mutation)
            self.assertEqual(caught.exception.code, "LANE_POLICY_EXCEEDS_AUTONOMY_PROFILE")

    def test_the_live_concurrency_policy_fits_the_live_profile(self) -> None:
        runner = _load("run_campaign_authority_lanes", SCRIPT)
        budget = runner._peer_concurrency_budget()
        ceiling = authority.lane_ceiling(GOV_ROOT)
        self.assertLessEqual(budget.total_lanes, ceiling["total_lanes"])
        self.assertLessEqual(budget.mutation_lanes, ceiling["mutation_lanes"])


def _reader(tmp: Path, report: object) -> Path:
    """A governance root whose status reader prints `report`."""
    root = tmp / "gov"
    binding = yaml.safe_load((GOV_ROOT / LIVE["projection_binding"]["binding"]).read_text("utf-8"))
    target = root / LIVE["projection_binding"]["binding"]
    target.parent.mkdir(parents=True)
    target.write_text(yaml.safe_dump(binding), encoding="utf-8")
    reader = root / binding["verification"]["status_reader"]
    reader.parent.mkdir(parents=True)
    reader.write_text(f"print({json.dumps(json.dumps(report))})\n", encoding="utf-8")
    bundle = root / binding["bundle"]["path"]
    (bundle / "projections").mkdir(parents=True)
    (bundle / binding["bundle"]["lock"]).write_text("{}\n", encoding="utf-8")
    (bundle / "projections" / "invariants.projection.json").write_text("{}\n", encoding="utf-8")
    return root


class ProjectionBindingTests(unittest.TestCase):
    def _bind(self, report: object):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            return authority.bind_coding_projection(_reader(Path(raw), report), LIVE)

    def test_a_verified_admitted_bundle_binds(self) -> None:
        for status in ("CURRENT", "BOUND"):
            record = self._bind(
                {
                    "status": status,
                    "admission": {"status": "ADMITTED_AND_CURRENT"},
                    "bundle_revision": "a" * 40,
                    "components": ["invariants"],
                }
            )
            self.assertEqual(record["status"], status)
            self.assertEqual(record["profile_ref"], "l9.projection/coding-agent-execution@1")
            self.assertEqual(
                [view["path"].rsplit("/", 1)[-1] for view in record["views"]],
                ["invariants.projection.json"],
            )

    def test_anything_short_of_bound_binds_nothing(self) -> None:
        for status in ("STALE", "UNVERIFIED", "BLOCKED", "REJECTED"):
            with self.assertRaises(authority.CampaignAuthorityError) as caught:
                self._bind({"status": status, "admission": {"status": "ADMITTED_AND_CURRENT"}})
            self.assertEqual(caught.exception.code, "PROJECTION_NOT_BOUND", status)

    def test_a_bound_bundle_without_proved_admission_binds_nothing(self) -> None:
        with self.assertRaises(authority.CampaignAuthorityError) as caught:
            self._bind({"status": "CURRENT", "admission": {"status": "UNRESOLVED"}})
        self.assertEqual(caught.exception.code, "PROJECTION_ADMISSION_NOT_PROVED")

    def test_an_unreadable_verifier_binds_nothing(self) -> None:
        with self.assertRaises(authority.CampaignAuthorityError) as caught:
            self._bind("not a report")
        self.assertEqual(caught.exception.code, "PROJECTION_VERIFIER_UNREADABLE")

    def test_a_campaign_is_not_resumed_across_a_rebind(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            first = {"bundle_lock_digest": "sha256:1", "bundle_revision": "one"}
            authority.record_projection_binding(workspace, first)
            path = authority.record_projection_binding(workspace, dict(first))
            record = json.loads(path.read_text("utf-8"))
            self.assertEqual(record["bootstrap"], first)
            self.assertEqual(len(record["verified"]), 1)
            with self.assertRaises(authority.CampaignAuthorityError) as caught:
                authority.record_projection_binding(
                    workspace, {"bundle_lock_digest": "sha256:2", "bundle_revision": "two"}
                )
            self.assertEqual(caught.exception.code, "PROJECTION_BINDING_DRIFT")

    def test_the_live_runner_has_no_environment_skip(self) -> None:
        source = SCRIPT.read_text("utf-8")
        start = source.index("def default_bind_projection(")
        body = source[start : source.index("\ndef ", start + 1)]
        self.assertNotIn("os.environ", body)


if __name__ == "__main__":
    unittest.main()
