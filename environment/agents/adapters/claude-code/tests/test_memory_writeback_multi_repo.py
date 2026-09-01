#!/usr/bin/env python3
"""Write-back closes every repository it hydrated, not the container root.

The defect these tests pin: on a cloud container ``WORKSPACE`` names the parent
of several repositories, ``memory_prefetch.py`` fanned out across them, and
``memory_writeback.py`` called ``close_session`` exactly once — on the container
root, where ``resolve_group_id`` matches every repository and therefore resolves
none. The observed end state was ``status=skipped writes=0`` against a healthy
Graphiti: six repositories read, zero written, so nothing a session learned
survived it.

Network-free. ``close_session`` is stubbed at its module path, so these assert
the hook's fan-out and budget arithmetic, never Graphiti itself.
"""

from __future__ import annotations

import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

CLAUDE_DIR = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE_DIR / "hooks"
MEM = CLAUDE_DIR / "memory"
for _p in (str(MEM), str(HOOKS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import memory_state as st  # noqa: E402


def _make_repo(root: Path, name: str) -> Path:
    repo = root / name
    (repo / ".git").mkdir(parents=True)
    return repo


class WritebackFanOutTest(unittest.TestCase):
    """Every hydrated root gets its own close_session call."""

    def setUp(self) -> None:
        self._tmp = __import__("tempfile").TemporaryDirectory()
        self.workspace = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)
        self.session_id = "sess-multi"

    def _run_hook(
        self,
        *,
        hydrated_roots: list[Path] | None,
        close_impl,
        env_extra: dict[str, str] | None = None,
    ) -> tuple[dict, list[dict]]:
        """Import the hook fresh, stub close_session, run main(), return receipt."""
        calls: list[dict] = []

        def _close(**kwargs):
            calls.append(kwargs)
            return close_impl(**kwargs)

        stub = types.ModuleType("ops.graphiti.hydration.close_session")
        stub.close_session = _close

        env = {
            "CLAUDE_PROJECT_DIR": str(self.workspace),
            "L9_MEMORY_AGENT_ID": "claude-code",
            **(env_extra or {}),
        }

        with (
            mock.patch.dict(sys.modules, {"ops.graphiti.hydration.close_session": stub}),
            mock.patch.dict("os.environ", env, clear=False),
        ):
            contract = st.load_contract()
            payload: dict[str, object] = {
                "namespaces": ["cursor-governance"],
                "transport": "cursor-graphiti-hydrate",
                "status": "prefetched",
                "degraded": False,
            }
            if hydrated_roots is not None:
                payload["hydrated_roots"] = [str(r) for r in hydrated_roots]
            st.write_receipt(contract, self.session_id, payload)

            sys.modules.pop("memory_writeback", None)
            import memory_writeback as wb  # noqa: PLC0415

            event = json.dumps({"session_id": self.session_id, "reason": "completed"})
            with mock.patch.object(sys, "stdin", io.StringIO(event)):
                rc = wb.main()
            self.assertEqual(rc, 0, "Stop hook must stay fail-open")

            receipt_path = st.receipt_path(
                contract, f"{self.session_id}{wb.WRITEBACK_RECEIPT_SUFFIX}"
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        return receipt, calls

    def test_closes_each_hydrated_root_once(self) -> None:
        repos = [_make_repo(self.workspace, n) for n in ("alpha", "beta", "gamma")]
        receipt, calls = self._run_hook(
            hydrated_roots=repos,
            close_impl=lambda **k: {"status": "phase_a", "writes": ["w"], "warnings": []},
        )
        self.assertEqual(len(calls), 3, "one close_session per hydrated repository")
        self.assertEqual(
            [Path(c["project_dir"]).name for c in calls],
            ["alpha", "beta", "gamma"],
            "closes the repositories, never the container root",
        )
        self.assertNotIn(
            str(self.workspace),
            [str(c["project_dir"]) for c in calls],
            "the container root is exactly what must NOT be closed",
        )
        self.assertEqual(receipt["writes"], 3)
        self.assertEqual(receipt["status"], "ran")
        self.assertEqual(receipt["deferred_roots"], [])

    def test_each_call_carries_a_budget(self) -> None:
        """Each call is budgeted; six default-ceiling calls would overrun the hook."""
        repos = [_make_repo(self.workspace, n) for n in ("a", "b")]
        _, calls = self._run_hook(
            hydrated_roots=repos,
            close_impl=lambda **k: {"status": "phase_a", "writes": [], "warnings": []},
            env_extra={"L9_MEMORY_WRITEBACK_BUDGET": "40"},
        )
        self.assertTrue(all("budget" in c for c in calls), "budget must be passed through")
        self.assertTrue(
            all(0 < c["budget"] <= 40 for c in calls),
            f"each budget must fit the hook allowance, got {[c['budget'] for c in calls]}",
        )

    def test_exhausted_budget_defers_and_names_the_remainder(self) -> None:
        """A truncated loop reports what it did NOT close, rather than only wins."""
        repos = [_make_repo(self.workspace, n) for n in ("a", "b", "c", "d")]

        def slow(**kwargs):
            # Burn the whole allowance on the first repository.
            import time as _t

            _t.sleep(1.2)
            return {"status": "phase_a", "writes": [], "warnings": []}

        receipt, calls = self._run_hook(
            hydrated_roots=repos,
            close_impl=slow,
            env_extra={"L9_MEMORY_WRITEBACK_BUDGET": "1"},
        )
        self.assertEqual(len(calls), 1, "stops once the budget cannot cover another root")
        self.assertEqual(
            [Path(p).name for p in receipt["deferred_roots"]],
            ["b", "c", "d"],
            "deferred roots are named in the receipt, not silently dropped",
        )

    def test_falls_back_to_shared_resolver_without_a_receipt_field(self) -> None:
        """No hydrated_roots recorded → the shared workspace_roots answer, not the container."""
        repos = [_make_repo(self.workspace, n) for n in ("one", "two")]
        _, calls = self._run_hook(
            hydrated_roots=None,
            close_impl=lambda **k: {"status": "phase_a", "writes": [], "warnings": []},
        )
        self.assertEqual(
            sorted(Path(c["project_dir"]).name for c in calls),
            [r.name for r in repos],
            "fallback must still enumerate repositories, never the container root",
        )

    def test_single_repository_workspace_is_unchanged(self) -> None:
        """A workspace that IS a checkout closes exactly itself — byte-for-byte prior behaviour."""
        (self.workspace / ".git").mkdir()
        _, calls = self._run_hook(
            hydrated_roots=None,
            close_impl=lambda **k: {"status": "phase_a", "writes": [], "warnings": []},
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(Path(calls[0]["project_dir"]).resolve(), self.workspace)

    def test_one_failing_root_does_not_lose_the_others(self) -> None:
        repos = [_make_repo(self.workspace, n) for n in ("ok1", "boom", "ok2")]
        seen: list[str] = []

        def flaky(**kwargs):
            name = Path(kwargs["project_dir"]).name
            seen.append(name)
            if name == "boom":
                raise RuntimeError("transport exploded")
            return {"status": "phase_a", "writes": ["w"], "warnings": []}

        receipt, calls = self._run_hook(hydrated_roots=repos, close_impl=flaky)
        self.assertEqual(seen, ["ok1", "boom", "ok2"], "every root is still attempted, in order")
        self.assertEqual(len(calls), 3, "a raising root must not abort the loop")
        self.assertIn("boom=error", receipt["close_status"])
        self.assertEqual(receipt["writes"], 2, "the healthy roots still wrote")


class WritebackPolicySkipTest(unittest.TestCase):
    """A session that never hydrated still records WHY it did nothing."""

    def test_no_prefetch_receipt_records_policy_skip(self) -> None:
        with __import__("tempfile").TemporaryDirectory() as tmp:
            with mock.patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": tmp}, clear=False):
                contract = st.load_contract()
                sys.modules.pop("memory_writeback", None)
                import memory_writeback as wb  # noqa: PLC0415

                event = json.dumps({"session_id": "never-hydrated"})
                with mock.patch.object(sys, "stdin", io.StringIO(event)):
                    self.assertEqual(wb.main(), 0)
                path = st.receipt_path(contract, f"never-hydrated{wb.WRITEBACK_RECEIPT_SUFFIX}")
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["status"], "skipped_no_prefetch")


if __name__ == "__main__":
    unittest.main()
