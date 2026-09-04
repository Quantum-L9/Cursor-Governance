"""Direct coverage for the runner-side seam repairs.

The smoke campaign exercises these paths end to end; this file pins each
repaired invariant at its owner so a regression names the function, not the
campaign:

* the coverage baseline is persisted at first dispatch and reloaded, bound to
  contract digest / base SHA / worktree, on a resume;
* a resumed SUBMITTED/VERIFYING attempt retires the root lease its window ran
  under, by the Controller's verdict;
* the commit boundary stages exactly the verified files;
* gate evaluation supplies the gate's own declared evidence and never decides;
* close reads the Controller's recommendation instead of asserting CONVERGED;
* a resume reconciles the authored source with the prepared shape.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )
    return completed.stdout.strip()


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_repairs_under_test", SCRIPT)

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pe-repairs-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))


class EffectBaselineTests(_Base):
    CONTRACT = {"contract_digest": "sha256:abc", "base_sha": "0" * 40}

    def test_persisted_baseline_round_trips_under_the_same_binding(self) -> None:
        workspace = self.tmp / "ws"
        worktree = self.tmp / "wt"
        worktree.mkdir()
        baseline = {"src/a.py": "sha256:1", "docs/b.md": "sha256:2"}
        path = self.mod.persist_effect_baseline(
            workspace, "TASK-001", contract=self.CONTRACT, worktree=worktree, baseline=baseline
        )
        self.assertEqual(path, self.mod.effect_baseline_path(workspace, "TASK-001"))
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema"], self.mod.EFFECT_BASELINE_SCHEMA)
        self.assertEqual(
            self.mod.load_effect_baseline(
                workspace, "TASK-001", contract=self.CONTRACT, worktree=worktree
            ),
            baseline,
        )

    def test_missing_baseline_fails_closed(self) -> None:
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.load_effect_baseline(
                self.tmp / "ws", "TASK-001", contract=self.CONTRACT, worktree=self.tmp
            )
        self.assertEqual(ctx.exception.error_code, "EFFECT_BASELINE_MISSING")

    def test_baseline_recorded_for_another_binding_is_refused(self) -> None:
        workspace = self.tmp / "ws"
        worktree = self.tmp / "wt"
        worktree.mkdir()
        self.mod.persist_effect_baseline(
            workspace, "TASK-001", contract=self.CONTRACT, worktree=worktree, baseline={}
        )
        for drift in (
            {"contract_digest": "sha256:other"},
            {"base_sha": "1" * 40},
        ):
            with self.subTest(drift=drift), self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.load_effect_baseline(
                    workspace,
                    "TASK-001",
                    contract={**self.CONTRACT, **drift},
                    worktree=worktree,
                )
            self.assertEqual(ctx.exception.error_code, "EFFECT_BASELINE_MISMATCH")
        other = self.tmp / "other-wt"
        other.mkdir()
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.load_effect_baseline(
                workspace, "TASK-001", contract=self.CONTRACT, worktree=other
            )
        self.assertEqual(ctx.exception.error_code, "EFFECT_BASELINE_MISMATCH")

    def test_corrupted_baseline_is_missing_not_guessed(self) -> None:
        workspace = self.tmp / "ws"
        path = self.mod.effect_baseline_path(workspace, "TASK-001")
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.load_effect_baseline(
                workspace, "TASK-001", contract=self.CONTRACT, worktree=self.tmp
            )
        self.assertEqual(ctx.exception.error_code, "EFFECT_BASELINE_MISSING")
        path.write_text(
            json.dumps(
                {
                    "schema": self.mod.EFFECT_BASELINE_SCHEMA,
                    "task_id": "TASK-001",
                    "contract_digest": self.CONTRACT["contract_digest"],
                    "base_sha": self.CONTRACT["base_sha"],
                    "worktree": str(self.tmp.resolve()),
                    "baseline": ["not", "a", "mapping"],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.load_effect_baseline(
                workspace, "TASK-001", contract=self.CONTRACT, worktree=self.tmp
            )
        self.assertEqual(ctx.exception.error_code, "EFFECT_BASELINE_MISMATCH")


class ResumedGrantRetirementTests(_Base):
    def _grants(self) -> unittest.mock.Mock:
        grants = unittest.mock.Mock()
        grants.release_task_grant = unittest.mock.Mock()
        grants.revoke_task_grant = unittest.mock.Mock()
        return grants

    def test_verified_resume_releases_and_rejected_resume_revokes(self) -> None:
        grant = {"lease_id": "lease-1"}
        for verdict, released, revoked in (
            ("PASSED_LOCAL", 1, 0),
            ("FAILED", 0, 1),
            ("INCONCLUSIVE", 0, 1),
        ):
            grants = self._grants()
            with (
                self.subTest(verdict=verdict),
                unittest.mock.patch.object(self.mod, "_grant_module", return_value=grants),
            ):
                self.mod._retire_resumed_grant(
                    {"task_id": "TASK-001", "grant": grant}, {"verdict": verdict}
                )
            self.assertEqual(grants.release_task_grant.call_count, released)
            self.assertEqual(grants.revoke_task_grant.call_count, revoked)

    def test_no_grant_means_nothing_to_retire(self) -> None:
        grants = self._grants()
        with unittest.mock.patch.object(self.mod, "_grant_module", return_value=grants):
            self.mod._retire_resumed_grant({"task_id": "TASK-001", "grant": None}, {"verdict": "X"})
        grants.release_task_grant.assert_not_called()
        grants.revoke_task_grant.assert_not_called()

    def test_retirement_failure_never_masks_the_verdict(self) -> None:
        grants = self._grants()
        grants.revoke_task_grant.side_effect = RuntimeError("root store down")
        with unittest.mock.patch.object(self.mod, "_grant_module", return_value=grants):
            self.mod._retire_resumed_grant(
                {"task_id": "TASK-001", "grant": {"lease_id": "l"}}, {"verdict": "FAILED"}
            )
        grants.revoke_task_grant.assert_called_once()

    def test_persisted_grant_is_read_from_the_latest_generation(self) -> None:
        grants = self._grants()
        grants.latest_grant_receipt = unittest.mock.Mock(
            return_value=(2, {"lease_id": "lease-2", "generation": 2})
        )
        with unittest.mock.patch.object(self.mod, "_grant_module", return_value=grants):
            found = self.mod._persisted_task_grant(self.tmp, {"task_id": "TASK-001"})
            grants.latest_grant_receipt.return_value = (0, None)
            absent = self.mod._persisted_task_grant(self.tmp, {"task_id": "TASK-001"})
        self.assertEqual(found, {"lease_id": "lease-2", "generation": 2})
        self.assertIsNone(absent)


class ExactObservedCommitTests(_Base):
    def _worktree(self) -> Path:
        repo = self.tmp / "wt"
        repo.mkdir()
        _git(repo, "init", "-q")
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-q", "-m", "base")
        return repo

    def test_only_the_verified_files_are_staged(self) -> None:
        repo = self._worktree()
        (repo / "out").mkdir()
        (repo / "out" / "result.md").write_text(
            "# Result\n\nThe task produced a real deliverable with enough prose to be "
            "unmistakably not the rendered stub.\n",
            encoding="utf-8",
        )
        (repo / "out" / "extra.md").write_text("declared but never verified\n", encoding="utf-8")
        (repo / "notes.txt").write_text("under a directory scope\n", encoding="utf-8")
        sha = self.mod.write_and_commit_output(
            repo,
            "out/result.md",
            "Result",
            ["out/result.md", "out/extra.md"],
            commit_authorized=True,
            observed=["out/result.md", "notes.txt"],
        )
        committed = _git(repo, "show", "--name-only", "--format=", sha).splitlines()
        self.assertEqual(sorted(committed), ["notes.txt", "out/result.md"])
        self.assertIn("out/extra.md", _git(repo, "status", "--porcelain"))

    def test_an_empty_observation_refuses_to_commit(self) -> None:
        repo = self._worktree()
        with self.assertRaises(self.mod.CampaignError):
            self.mod.write_and_commit_output(
                repo, "out/result.md", "Result", [], commit_authorized=True, observed=[]
            )

    def test_a_verified_stub_primary_output_still_refuses(self) -> None:
        repo = self._worktree()
        (repo / "out").mkdir()
        (repo / "out" / "result.md").write_text("result complete: Result\n", encoding="utf-8")
        with self.assertRaises(self.mod.CampaignError):
            self.mod.write_and_commit_output(
                repo,
                "out/result.md",
                "Result",
                ["out/result.md"],
                commit_authorized=True,
                observed=["out/result.md"],
            )

    def test_commit_authority_is_still_required(self) -> None:
        repo = self._worktree()
        with self.assertRaises(self.mod.CampaignError):
            self.mod.write_and_commit_output(
                repo, "x.md", "X", [], commit_authorized=False, observed=["x.md"]
            )


class GateEvidenceTests(_Base):
    def test_gate_evaluation_supplies_the_declared_evidence(self) -> None:
        workspace = self.tmp / "ws"
        (workspace / "runtime").mkdir(parents=True)
        (workspace / "runtime" / "program-lock.json").write_text(
            json.dumps(
                {
                    "gates": [
                        {"id": "GATE-001", "required_evidence_ids": ["EVID-001", "EVID-002"]},
                        {"id": "GATE-002"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        calls: list[tuple[str, ...]] = []

        def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
            calls.append((command, *rest))
            return {}

        with unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=fake_pec):
            self.mod.evaluate_completion_gates(
                workspace,
                {"id": "TASK-001", "completion_gates": ["GATE-001", "GATE-002"]},
                "EVID-VERIFY",
            )
        self.assertEqual(len(calls), 2)
        first, second = calls
        self.assertEqual(first[:3], ("evaluate-gate", "GATE-001", "PASS"))
        evidence = [first[i + 1] for i, tok in enumerate(first) if tok == "--evidence-id"]
        self.assertEqual(evidence, ["EVID-VERIFY", "EVID-001", "EVID-002"])
        evidence = [second[i + 1] for i, tok in enumerate(second) if tok == "--evidence-id"]
        self.assertEqual(evidence, ["EVID-VERIFY"])
        self.assertIn("inspection", first)

    def test_no_lock_means_only_the_verification_evidence(self) -> None:
        calls: list[tuple[str, ...]] = []
        with unittest.mock.patch.object(
            self.mod, "pec_cmd", side_effect=lambda ws, c, *r: calls.append((c, *r)) or {}
        ):
            self.mod.evaluate_completion_gates(
                self.tmp, {"id": "TASK-001", "completion_gate_ids": ["GATE-009"]}, "EVID-V"
            )
        self.assertEqual(calls[0][:3], ("evaluate-gate", "GATE-009", "PASS"))
        self.assertEqual(calls[0].count("--evidence-id"), 1)


class TruthfulCloseTests(_Base):
    def _run_close(self, handoff: dict[str, Any]) -> list[tuple[str, ...]]:
        calls: list[tuple[str, ...]] = []

        def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
            calls.append((command, *rest))
            return handoff if command == "export-handoff" else {}

        closer = unittest.mock.Mock()
        closer.close_campaign = unittest.mock.Mock()
        closer.archive_completed = unittest.mock.Mock(return_value=self.tmp / "archived")
        real_load = self.mod._load_script

        def fake_load(name: str, path: Path) -> Any:
            return closer if name == "close_campaign" else real_load(name, path)

        with (
            unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=fake_pec),
            unittest.mock.patch.object(self.mod, "_load_script", side_effect=fake_load),
        ):
            self.mod.default_close(
                self.tmp / "ws",
                "CAMP-1",
                write_root=self.tmp,
                host_repo="owner/repo",
                hooks=self.mod.Hooks(),
                merge_recorded=False,
            )
        self.closer = closer
        return calls

    def test_close_carries_the_controller_recommendation_and_handoff(self) -> None:
        calls = self._run_close(
            {"handoff_id": "HANDOFF-7", "recommended_program_verdict": "CONVERGED"}
        )
        self.assertEqual(calls[0][0], "export-handoff")
        close = next(call for call in calls if call[0] == "close")
        self.assertIn("CONVERGED", close)
        self.assertIn("handoff_id=HANDOFF-7", close)
        args = self.closer.close_campaign.call_args.args
        self.assertEqual(args[2], "CONVERGED")
        self.assertEqual(args[3]["handoff_id"], "HANDOFF-7")

    def test_close_refuses_when_the_controller_does_not_recommend_success(self) -> None:
        for verdict in ("HALTED", "INCONCLUSIVE", None):
            with self.subTest(verdict=verdict), self.assertRaises(self.mod.CampaignError):
                self._run_close({"handoff_id": "H", "recommended_program_verdict": verdict})


class ResumeSourceReconciliationTests(_Base):
    SOURCE = {
        "schema": "campaign-source.v2",
        "campaign_id": "CAMP-1",
        "title": "one",
        "tasks": [
            {"id": "TASK-001", "title": "a", "objective": "first"},
            {"id": "TASK-002", "title": "b", "objective": "second"},
        ],
    }

    def _prepare(self, source_doc: dict[str, Any]) -> tuple[Path, Path, Path]:
        write_root = self.tmp / "root"
        source = self.mod.campaign_source_path(write_root, "CAMP-1")
        source.parent.mkdir(parents=True)
        import yaml

        source.write_text(yaml.safe_dump(source_doc, sort_keys=False), encoding="utf-8")
        shape = self.mod.campaign_source_shape(source)
        l9_home = self.tmp / "l9"
        primed = l9_home / "primed" / "CAMP-1"
        timing = self.mod._load_script("pe_timing", PE_ROOT / "scripts/pe_timing.py")
        prepare = self.mod._load_script("pe_prepare_state", PE_ROOT / "scripts/pe_prepare_state.py")
        state = prepare.PrepareState.load(primed / "PREPARE_STATE.json", campaign_id="CAMP-1")
        state.stages["compile"] = {"key": "compile-key"}
        state.save()
        timing.StageCache(primed, enabled=True).put(
            "compile", "compile-key", {"blueprint": "x", "source": shape}
        )
        return write_root, source, l9_home

    def _reconcile(self, write_root: Path, source: Path, l9_home: Path) -> dict[str, Any]:
        return self.mod.reconcile_resumed_source(
            campaign_id="CAMP-1",
            source=source,
            pec_workspace=self.tmp / "ws",
            l9_home=l9_home,
        )

    def test_unchanged_source_is_current(self) -> None:
        write_root, source, l9_home = self._prepare(self.SOURCE)
        self.assertEqual(self._reconcile(write_root, source, l9_home)["status"], "CURRENT")

    def test_a_task_edit_is_relocked_and_the_recorded_shape_advances(self) -> None:
        write_root, source, l9_home = self._prepare(self.SOURCE)
        import yaml

        edited = json.loads(json.dumps(self.SOURCE))
        edited["tasks"][1]["objective"] = "second, edited after prepare"
        source.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
        with unittest.mock.patch.object(
            self.mod, "adopt_changed_definitions", return_value={"relocked": ["TASK-002"]}
        ) as adopt:
            outcome = self._reconcile(write_root, source, l9_home)
        adopt.assert_called_once_with(self.tmp / "ws", ["TASK-002"])
        self.assertEqual(outcome["status"], "RELOCKED")
        self.assertEqual(outcome["relocked"], ["TASK-002"])
        # A second resume against the same edited source has nothing to absorb.
        self.assertEqual(self._reconcile(write_root, source, l9_home)["status"], "CURRENT")

    def test_a_body_edit_cannot_be_absorbed(self) -> None:
        write_root, source, l9_home = self._prepare(self.SOURCE)
        import yaml

        edited = {**self.SOURCE, "title": "a different program"}
        source.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self._reconcile(write_root, source, l9_home)
        self.assertEqual(ctx.exception.error_code, "SOURCE_DRIFT_ON_RESUME")

    def test_a_changed_task_set_cannot_be_absorbed(self) -> None:
        write_root, source, l9_home = self._prepare(self.SOURCE)
        import yaml

        edited = json.loads(json.dumps(self.SOURCE))
        edited["tasks"].append({"id": "TASK-003", "title": "c", "objective": "third"})
        source.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self._reconcile(write_root, source, l9_home)
        self.assertEqual(ctx.exception.error_code, "SOURCE_DRIFT_ON_RESUME")

    def test_a_refused_relock_stops_the_resume(self) -> None:
        write_root, source, l9_home = self._prepare(self.SOURCE)
        import yaml

        edited = json.loads(json.dumps(self.SOURCE))
        edited["tasks"][0]["objective"] = "first, edited"
        source.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
        with (
            unittest.mock.patch.object(self.mod, "adopt_changed_definitions", return_value=None),
            self.assertRaises(self.mod.CampaignError) as ctx,
        ):
            self._reconcile(write_root, source, l9_home)
        self.assertEqual(ctx.exception.error_code, "SOURCE_DRIFT_ON_RESUME")

    def test_no_recorded_shape_or_source_is_not_drift(self) -> None:
        self.assertEqual(
            self.mod.reconcile_resumed_source(
                campaign_id="CAMP-1",
                source=self.tmp / "absent.yaml",
                pec_workspace=self.tmp / "ws",
                l9_home=self.tmp / "l9",
            )["status"],
            "NO_SOURCE",
        )
        write_root = self.tmp / "root"
        source = self.mod.campaign_source_path(write_root, "CAMP-1")
        source.parent.mkdir(parents=True)
        import yaml

        source.write_text(yaml.safe_dump(self.SOURCE, sort_keys=False), encoding="utf-8")
        self.assertEqual(
            self.mod.reconcile_resumed_source(
                campaign_id="CAMP-1",
                source=source,
                pec_workspace=self.tmp / "ws",
                l9_home=self.tmp / "l9-empty",
            )["status"],
            "NO_RECORDED_SHAPE",
        )


if __name__ == "__main__":
    unittest.main()
