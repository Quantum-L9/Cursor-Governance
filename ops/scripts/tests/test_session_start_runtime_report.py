#!/usr/bin/env python3
"""SessionStart runtime lines must name class + evidence, not slogans."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import session_start_runtime_report as report  # noqa: E402


class PublishPathClassificationTests(unittest.TestCase):
    def test_missing_override_is_ok_not_a_fault(self) -> None:
        line = report.classify_publish_path({"status": "none", "in_force": False})
        self.assertEqual(line["class"], report.OK)
        self.assertIn("enforced", line["summary"])
        self.assertNotIn("no publish-path breakglass in force", line["summary"])
        self.assertFalse(line["include_in_degraded"])

    def test_in_force_grant_is_named_degraded(self) -> None:
        line = report.classify_publish_path(
            {
                "status": "in_force",
                "in_force": True,
                "issuer": "ops",
                "reason": "incident-1234",
                "expires_at": "2026-08-30T20:00:00Z",
                "detail": "publish-path grant in force",
            }
        )
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("incident-1234", line["summary"])
        self.assertTrue(line["include_in_degraded"])

    def test_unread_probe_is_failed(self) -> None:
        line = report.classify_publish_path(None)
        self.assertEqual(line["class"], report.FAILED)
        self.assertTrue(line["include_in_degraded"])


class ItestClassificationTests(unittest.TestCase):
    def test_refused_neo4j_is_na_not_unavailable_slogan(self) -> None:
        line = report.classify_itest(
            error="ConnectionRefusedError: [Errno 61] Connection refused",
            codegraph="skipped",
        )
        self.assertEqual(line["class"], report.NA)
        self.assertIn("Errno 61", line["summary"])
        self.assertIn("Graphiti is :8100", line["summary"])
        self.assertNotIn("itest: unavailable", line["summary"])
        self.assertFalse(line["include_in_degraded"])

    def test_reachable_neo4j_is_ok(self) -> None:
        line = report.classify_itest(error="", codegraph="indexed")
        self.assertEqual(line["class"], report.OK)


class ClaudeAdapterClassificationTests(unittest.TestCase):
    def test_cursor_does_not_score_never_ran_as_this_surface(self) -> None:
        lines = report.classify_claude_adapter(
            surface="cursor",
            receipt={"state": "never_ran", "reason": "no bootstrap receipt on disk"},
            repair_log="/tmp/bootstrap-repair-deadbeef.log",
            repair_text="timeout: command not found",
        )
        by_name = {item["name"]: item for item in lines}
        self.assertEqual(list(by_name), ["claude-adapter"])
        self.assertEqual(by_name["claude-adapter"]["class"], report.NA)
        self.assertFalse(by_name["claude-adapter"]["include_in_degraded"])
        self.assertNotIn("claude-adapter-repair", by_name)

    def test_claude_surface_never_ran_is_this_surface_failed(self) -> None:
        lines = report.classify_claude_adapter(
            surface="claude-code",
            receipt={"state": "never_ran", "reason": "no bootstrap receipt on disk"},
            repair_log="/tmp/x.log",
            repair_text="timeout: command not found",
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["class"], report.FAILED)
        self.assertTrue(lines[0]["this_surface"])
        self.assertIn("timeout: command not found", lines[0]["summary"])


class MarkdownEmitTests(unittest.TestCase):
    def test_degraded_section_lists_only_actionable_failures(self) -> None:
        lines = [
            report.classify_publish_path({"status": "none", "in_force": False}),
            report.classify_itest(error="ConnectionRefusedError: x", codegraph="skipped"),
            *report.classify_claude_adapter(
                surface="cursor",
                receipt={"state": "never_ran", "reason": "absent"},
                repair_log="/tmp/r.log",
                repair_text="timeout: command not found",
            ),
        ]
        md = report.format_markdown(lines)
        self.assertIn("### Runtime", md)
        self.assertIn("### Degraded", md)
        self.assertIn("publish-path: ok", md)
        self.assertIn("itest/neo4j: n/a", md)
        self.assertIn("claude-adapter: n/a", md)
        self.assertNotIn("claude-adapter-repair", md)
        self.assertIn("### Degraded\n- none", md)
        self.assertNotIn("no publish-path breakglass in force", md)
        self.assertNotIn("itest: unavailable", md)

    def test_all_ok_emits_degraded_none(self) -> None:
        md = report.format_markdown(
            [report.classify_publish_path({"status": "none", "in_force": False})]
        )
        self.assertIn("### Degraded\n- none", md)


class SkillUsageClassificationTests(unittest.TestCase):
    def test_absent_log_is_na_not_degraded(self) -> None:
        line = report.classify_skill_usage("/tmp/skill-usage.jsonl (absent — logger never wrote)")
        self.assertEqual(line["class"], report.NA)
        self.assertFalse(line["include_in_degraded"])

    def test_present_log_is_ok(self) -> None:
        line = report.classify_skill_usage("/tmp/skill-usage.jsonl (730 entries)")
        self.assertEqual(line["class"], report.OK)
        self.assertFalse(line["include_in_degraded"])


class HydrateCollapseTests(unittest.TestCase):
    def test_unhealthy_graphiti_does_not_add_hydrate_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lines = report.collect(
                surface="cursor",
                venv="locked",
                ide_profile="applied",
                tunnel="open",
                graphiti_detail="unreachable",
                graphiti_stderr="Connection reset by peer",
                graphiti_healthy=False,
                wiring="PASS",
                backup="armed",
                skill_note="/tmp/x.jsonl (1 entries)",
                codegraph="skipped",
                hydrate_degraded=True,
                hydrate_reason="PICKUP search unreachable",
                home=Path(tmp),
            )
        names = [item["name"] for item in lines]
        self.assertIn("graphiti", names)
        self.assertNotIn("graphiti-hydrate", names)
        graphiti = next(item for item in lines if item["name"] == "graphiti")
        self.assertIn("PICKUP search unreachable", graphiti["evidence"])

    def test_healthy_graphiti_keeps_hydrate_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lines = report.collect(
                surface="cursor",
                venv="locked",
                ide_profile="applied",
                tunnel="open",
                graphiti_detail="healthy",
                graphiti_stderr="",
                graphiti_healthy=True,
                wiring="PASS",
                backup="armed",
                skill_note="/tmp/x.jsonl (1 entries)",
                codegraph="skipped",
                hydrate_degraded=True,
                hydrate_reason="empty packet",
                home=Path(tmp),
            )
        names = [item["name"] for item in lines]
        self.assertIn("graphiti-hydrate", names)


class ReporterResolveTests(unittest.TestCase):
    def test_override_wins_over_worktree_and_gc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            override = root / "override.py"
            override.write_text("# override\n", encoding="utf-8")
            worktree = root / "wt"
            gc = root / "gc"
            for base in (worktree, gc):
                dest = base / "ops" / "scripts"
                dest.mkdir(parents=True)
                (dest / "session_start_runtime_report.py").write_text("# other\n", encoding="utf-8")
            found = report.resolve_reporter_path(
                override=str(override),
                project_dir=str(worktree),
                gc=str(gc),
            )
            self.assertEqual(found, override)

    def test_worktree_wins_over_gc_when_override_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "wt"
            gc = root / "gc"
            for base in (worktree, gc):
                dest = base / "ops" / "scripts"
                dest.mkdir(parents=True)
                (dest / "session_start_runtime_report.py").write_text(
                    f"# {base.name}\n", encoding="utf-8"
                )
            found = report.resolve_reporter_path(
                override=None,
                project_dir=str(worktree),
                gc=str(gc),
            )
            self.assertEqual(
                found,
                worktree / "ops" / "scripts" / "session_start_runtime_report.py",
            )

    def test_missing_everywhere_is_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            found = report.resolve_reporter_path(
                override=str(Path(tmp) / "missing.py"),
                project_dir=str(Path(tmp) / "wt"),
                gc=str(Path(tmp) / "gc"),
            )
            self.assertIsNone(found)


class HookWiringTests(unittest.TestCase):
    def test_cursor_hook_calls_the_reporter_and_drops_slogans(self) -> None:
        text = (REPO / "ops" / "hooks" / "session_start_bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn("session_start_runtime_report.py", text)
        self.assertIn("resolve_runtime_reporter", text)
        self.assertNotIn("itest: unavailable — neo4j absent", text)
        self.assertNotIn("publish-path grant: none", text)
        self.assertNotIn("GRANT_NOTE", text)
        self.assertNotIn("ITEST_NOTE", text)
        self.assertNotIn("BOOTSTRAP_NOTE", text)
        self.assertNotIn("plugins, IDE, cold venv", text)
        self.assertNotIn("cold venv", text)

    def test_claude_hook_uses_portable_timeout(self) -> None:
        text = (
            REPO
            / "environment"
            / "agents"
            / "adapters"
            / "claude-code"
            / "hooks"
            / "session_start_claude_governance.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("run_with_timeout.sh", text)
        self.assertIn("run_with_timeout", text)
        self.assertNotRegex(
            text,
            r'(?<!run_with_)timeout "\$\{L9_BOOTSTRAP_REPAIR_BUDGET:-90\}"',
        )
        self.assertNotIn('run_with_timeout() { shift; "$@"; }', text)
        skipped = text.index("bootstrap repair: SKIPPED — run_with_timeout.sh missing")
        installer = text.index('bash "$installer"', skipped)
        repair = text.index('run_with_timeout "${L9_BOOTSTRAP_REPAIR_BUDGET:-90}"', skipped)
        marker = text.index(': >"$marker"', installer)
        self.assertLess(skipped, installer)
        self.assertLess(repair, installer)
        self.assertLess(installer, marker)


class PortableTimeoutTests(unittest.TestCase):
    def test_python_fallback_runs_without_gnu_timeout(self) -> None:
        lib = REPO / "ops" / "scripts" / "lib" / "run_with_timeout.sh"
        proc = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; PATH=/usr/bin:/bin run_with_timeout 2 echo portable-ok',
                "bash",
                str(lib),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "portable-ok")

    def test_python_fallback_returns_124_on_expiry(self) -> None:
        lib = REPO / "ops" / "scripts" / "lib" / "run_with_timeout.sh"
        proc = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; PATH=/usr/bin:/bin run_with_timeout 1 sleep 5',
                "bash",
                str(lib),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 124, proc.stderr)


if __name__ == "__main__":
    unittest.main()
