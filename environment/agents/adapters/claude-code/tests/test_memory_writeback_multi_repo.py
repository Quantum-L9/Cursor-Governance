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
import unittest.mock as mock
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE_DIR / "hooks"
MEM = CLAUDE_DIR / "memory"
for _p in (str(MEM), str(HOOKS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import memory_state as st  # noqa: E402

REPO_ROOT = CLAUDE_DIR.parents[3]


def _handoff_module() -> types.ModuleType:
    """The tree-under-test's ops.memory.session_handoff (never the SSOT's copy)."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "ops.memory.session_handoff", REPO_ROOT / "ops" / "memory" / "session_handoff.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _make_repo(root: Path, name: str) -> Path:
    repo = root / name
    (repo / ".git").mkdir(parents=True)
    return repo


def _publish(root: Path, number: int) -> None:
    """What make pr leaves behind (pr-summary.json) plus the agent's handoff."""
    pr = root / ".l9" / "pr"
    pr.mkdir(parents=True, exist_ok=True)
    (pr / "pr-summary.json").write_text(
        json.dumps({"repo": f"Org/{root.name}", "number": number, "head_sha": "a" * 40}),
        encoding="utf-8",
    )
    mem = root / ".l9" / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "handoff.json").write_text(
        json.dumps(
            {
                "schema": "l9.session_handoff.v1",
                "pr_number": number,
                "objective": f"ship {root.name}",
                "status": "published, awaiting review",
            }
        ),
        encoding="utf-8",
    )


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
        publish_in: list[Path] | None = None,
    ) -> tuple[dict, list[dict]]:
        """Import the hook fresh, stub close_session, run main(), return receipt."""
        calls: list[dict] = []

        def _close(**kwargs):
            calls.append(kwargs)
            return close_impl(**kwargs)

        stub = types.ModuleType("ops.graphiti.hydration.close_session")
        stub.close_session = _close
        stub.memory_client = lambda **_kw: None

        env = {
            "CLAUDE_PROJECT_DIR": str(self.workspace),
            "L9_MEMORY_AGENT_ID": "claude-code",
            **(env_extra or {}),
        }

        with (
            mock.patch.dict(
                sys.modules,
                {
                    "ops.graphiti.hydration.close_session": stub,
                    "ops.memory.session_handoff": _handoff_module(),
                },
            ),
            mock.patch.dict("os.environ", env, clear=False),
        ):
            contract = st.load_contract()
            payload: dict[str, object] = {
                "namespaces": ["cursor-governance"],
                "transport": "memory-control-plane/v1",
                "status": "prefetched",
                "degraded": False,
            }
            if hydrated_roots is not None:
                payload["hydrated_roots"] = [str(r) for r in hydrated_roots]
            # Keyed exactly as memory_prefetch stamps it: the writer-scoped
            # receipt id, never the raw session id (that mismatch hid the bug).
            receipt_id = st.resolve_receipt_id(event={"session_id": self.session_id})
            st.write_receipt(contract, receipt_id, payload)
            for number, root in enumerate(publish_in or [], start=1):
                _publish(root, number)

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

    def test_no_publication_closes_nothing(self) -> None:
        """The close fires only after a publication — never on an ordinary turn."""
        repos = [_make_repo(self.workspace, n) for n in ("alpha", "beta")]
        receipt, calls = self._run_hook(
            hydrated_roots=repos,
            close_impl=lambda **k: {"status": "closed_canonically", "writes": []},
        )
        self.assertEqual(calls, [])
        self.assertEqual(receipt["status"], "no_publication")

    def test_only_the_published_repository_closes_with_its_handoff(self) -> None:
        repos = [_make_repo(self.workspace, n) for n in ("alpha", "beta", "gamma")]
        receipt, calls = self._run_hook(
            hydrated_roots=repos,
            close_impl=lambda **k: {"status": "closed_canonically", "writes": []},
            publish_in=[repos[1]],
        )
        self.assertEqual([Path(c["project_dir"]).name for c in calls], ["beta"])
        call = calls[0]
        self.assertEqual(call["handoff"]["objective"], "ship beta")
        self.assertEqual(call["publication"], "Org/beta#1@" + "a" * 12)
        self.assertNotIn(str(self.workspace), [str(c["project_dir"]) for c in calls])
        self.assertEqual(receipt["status"], "ran")

    def test_fallback_roots_are_repositories_never_the_container(self) -> None:
        """No hydrated_roots recorded → the shared resolver, never the container root."""
        repos = [_make_repo(self.workspace, n) for n in ("one", "two")]
        _, calls = self._run_hook(
            hydrated_roots=None,
            close_impl=lambda **k: {"status": "closed_canonically", "writes": []},
            publish_in=[repos[1]],
        )
        self.assertEqual([Path(c["project_dir"]).name for c in calls], ["two"])

    def test_one_failing_publication_root_does_not_lose_the_others(self) -> None:
        repos = [_make_repo(self.workspace, n) for n in ("ok1", "boom")]

        def flaky(**kwargs):
            if Path(kwargs["project_dir"]).name == "boom":
                raise RuntimeError("transport exploded")
            return {"status": "closed_canonically", "writes": []}

        receipt, calls = self._run_hook(hydrated_roots=repos, close_impl=flaky, publish_in=repos)
        self.assertEqual(len(calls), 2, "a raising root must not abort the loop")
        self.assertIn("boom=error", receipt["close_status"])
        self.assertIn("ok1=closed_canonically", receipt["close_status"])


class WritebackPolicySkipTest(unittest.TestCase):
    """A session that never hydrated still records WHY it did nothing."""

    def test_subagent_stop_closes_nothing_and_says_so(self) -> None:
        """Authority narrowing (stage C8): a subagent never owns the parent's close."""
        with __import__("tempfile").TemporaryDirectory() as tmp:
            with mock.patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": tmp}, clear=False):
                contract = st.load_contract()
                st.write_receipt(
                    contract,
                    "parent-session",
                    {"namespaces": ["cursor-governance"], "status": "prefetched"},
                )
                sys.modules.pop("memory_writeback", None)
                import memory_writeback as wb  # noqa: PLC0415

                event = json.dumps({"session_id": "parent-session", "is_background_agent": True})
                with mock.patch.object(sys, "stdin", io.StringIO(event)):
                    self.assertEqual(wb.main(), 0)
                path = st.receipt_path(contract, f"parent-session{wb.WRITEBACK_RECEIPT_SUFFIX}")
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["status"], "skipped_subagent")

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
