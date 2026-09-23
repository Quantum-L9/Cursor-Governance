#!/usr/bin/env python3
"""SessionStart runtime lines must name class + evidence, not slogans."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))
sys.path.insert(0, str(REPO / "ops" / "autonomy"))
sys.path.insert(0, str(REPO / "ops" / "secrets"))

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


class TunnelClassificationTests(unittest.TestCase):
    def test_retired_slogan_is_na_not_ok(self) -> None:
        line = report.classify_tunnel("retired (memory control plane; no provider tunnel)")
        self.assertEqual(line["class"], report.NA)
        self.assertFalse(line["include_in_degraded"])


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
        self.assertIn("claude-adapter: n/a", md)
        self.assertNotIn("claude-adapter-repair", md)
        self.assertIn("### Degraded\n- none", md)
        self.assertNotIn("no publish-path breakglass in force", md)

    def test_all_ok_emits_degraded_none(self) -> None:
        md = report.format_markdown(
            [report.classify_publish_path({"status": "none", "in_force": False})]
        )
        self.assertIn("### Degraded\n- none", md)

    def test_aws_cli_failed_leads_markdown(self) -> None:
        md = report.format_markdown(
            [
                report.classify_aws_cli(
                    {
                        "ok": False,
                        "code": "AWS_CLI_NOT_FOUND",
                        "summary": "AWS_CLI_NOT_FOUND — secrets plane cannot start",
                    }
                )
            ]
        )
        self.assertTrue(md.startswith("### FAILED"))
        self.assertIn("aws-cli: failed", md)
        self.assertIn("### Runtime", md)


class SecretsPlaneClassificationTests(unittest.TestCase):
    def test_bind_names_come_from_the_owner(self) -> None:
        from session_start_secrets import BIND_NAMES

        self.assertNotIn("BIND_NAMES", vars(report))
        self.assertIn("GITHUB_TOKEN", BIND_NAMES)

    def test_aws_source_is_a_fault(self) -> None:
        line = report.classify_secrets_bind(
            [{"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "aws"}]
        )
        self.assertEqual(line["class"], report.FAILED)
        self.assertIn("source=aws is a fault", line["summary"])

    def test_unbound_is_degraded_not_a_paste(self) -> None:
        line = report.classify_secrets_bind(
            [{"name": "SONAR_TOKEN", "bound": False, "source": "unbound"}]
        )
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("do not paste a token", line["summary"])

    def test_missing_receipt_is_unread_not_a_live_probe(self) -> None:
        line = report.classify_secrets_bind(None)
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("secrets-plane receipt unread", line["summary"])
        self.assertNotIn("capability_bind", line["summary"])

    def test_aws_missing_receipt_is_unread(self) -> None:
        line = report.classify_aws_cli(None)
        self.assertEqual(line["class"], report.FAILED)
        self.assertIn("aws-cli receipt unread", line["summary"])
        self.assertNotIn("aws_cli_preflight", line["summary"])


class VenvBackupClassificationTests(unittest.TestCase):
    def test_cached_uv_line_is_ok(self) -> None:
        line = report.classify_venv("UV: cached locked environment")
        self.assertEqual(line["class"], report.OK)
        self.assertIn("UV:", line["summary"])

    def test_unavailable_and_sync_required_are_degraded_not_failed(self) -> None:
        missing = report.classify_venv(
            "UV: unavailable; locked governance environment not activated"
        )
        sync = report.classify_venv("UV: environment synchronization required")
        self.assertEqual(missing["class"], report.DEGRADED)
        self.assertEqual(sync["class"], report.DEGRADED)
        self.assertNotEqual(missing["class"], report.FAILED)

    def test_empty_venv_is_unread(self) -> None:
        line = report.classify_venv("")
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("unread", line["summary"])

    def test_proceed_is_ok(self) -> None:
        line = report.classify_backup("PROCEED: reason=- gates clear")
        self.assertEqual(line["class"], report.OK)

    def test_skip_is_na_not_fail(self) -> None:
        line = report.classify_backup("SKIP: sessionEnd reason=error — not a committable boundary")
        self.assertEqual(line["class"], report.NA)
        self.assertFalse(line["include_in_degraded"])

    def test_build_lock_skip_is_na(self) -> None:
        line = report.classify_backup("SKIPPED — .governance-build-lock present")
        self.assertEqual(line["class"], report.NA)

    def test_empty_backup_is_unread(self) -> None:
        line = report.classify_backup("")
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("unread", line["summary"])


class SecretsReceiptLoadTests(unittest.TestCase):
    def test_load_receipt_passes_aws_and_binds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / ".l9" / "session"
            dest.mkdir(parents=True)
            (dest / "secrets-plane.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "login": "present",
                        "aws": {"ok": True, "code": "OK", "summary": "authorized"},
                        "binds": [{"name": "GITHUB_TOKEN", "bound": True, "source": "infisical"}],
                    }
                ),
                encoding="utf-8",
            )
            receipt = report.load_secrets_plane_receipt(tmp)
            aws, binds = report.secrets_receipt_parts(receipt)
            self.assertEqual(aws["code"], "OK")
            self.assertEqual(binds[0]["source"], "infisical")

    def test_absent_receipt_is_unread_parts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aws, binds = report.secrets_receipt_parts(report.load_secrets_plane_receipt(tmp))
        self.assertIsNone(aws)
        self.assertIsNone(binds)

    def test_receipt_carries_the_plane_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / ".l9" / "session"
            dest.mkdir(parents=True)
            (dest / "secrets-plane.json").write_text(
                json.dumps(
                    {
                        "ok": False,
                        "state": "unavailable_by_surface",
                        "surface_class": "model_controlled",
                        "login": "skipped",
                        "aws": {
                            "ok": False,
                            "code": "AWS_CLI_NOT_FOUND",
                            "summary": "AWS_CLI_NOT_FOUND — secrets plane cannot start",
                        },
                        "binds": [
                            {"name": "SONAR_TOKEN", "bound": False, "source": "unbound"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            receipt = report.load_secrets_plane_receipt(tmp)
            self.assertEqual(
                report.secrets_plane_state(receipt),
                report.PLANE_UNAVAILABLE_BY_SURFACE,
            )

    def test_pre_carve_out_receipt_has_no_state(self) -> None:
        """A receipt written before the carve-out reads '' and keeps failing."""
        legacy = {"ok": False, "aws": {"ok": False, "code": "AWS_CLI_NOT_FOUND"}}
        self.assertEqual(report.secrets_plane_state(legacy), "")
        line = report.classify_aws_cli(legacy["aws"], report.secrets_plane_state(legacy))
        self.assertEqual(line["class"], report.FAILED)

    def test_unrecognized_state_is_fail_closed(self) -> None:
        """An unknown state degrades to no-state, never to the carve-out."""
        for raw in ("unavailable", "OK", "ok ", "sudo", "", None, 1, {"a": 1}):
            with self.subTest(state=raw):
                self.assertEqual(report.secrets_plane_state({"state": raw}), "")

    def test_state_returned_is_the_module_literal_not_the_receipt_string(self) -> None:
        """Nothing read from the receipt may leave this reader.

        The report is printed, so a value flowing from the receipt into the
        rendered output is a clear-text-logging path (CodeQL flagged exactly
        that). Returning the allowlisted literal is the barrier: the object
        returned is the module's own constant, never the parsed string.
        """
        parsed = json.loads('{"state": "unavailable_by_surface"}')
        returned = report.secrets_plane_state(parsed)
        self.assertEqual(returned, report.PLANE_UNAVAILABLE_BY_SURFACE)
        self.assertIn(returned, report.PLANE_STATES)
        # Identity, not just equality: the literal, not the receipt's string.
        self.assertIs(returned, report.PLANE_UNAVAILABLE_BY_SURFACE)
        self.assertIsNot(returned, parsed["state"])


class SecretsBindSurfaceClassificationTests(unittest.TestCase):
    """The carve-out reaches the bind classifier too.

    Without this the report contradicted itself: aws-cli named the surface and
    said "not a fault" while secrets-bind degraded on the very same cause.
    """

    UNBOUND = [
        {"name": "SEMGREP_APP_TOKEN", "bound": False, "source": "infisical-machine-absent"},
        {"name": "SONAR_TOKEN", "bound": False, "source": "infisical-machine-absent"},
        {"name": "GITHUB_TOKEN", "bound": True, "source": "env"},
    ]

    def test_unbound_by_surface_is_not_degraded(self) -> None:
        line = report.classify_secrets_bind(self.UNBOUND, report.PLANE_UNAVAILABLE_BY_SURFACE)
        self.assertEqual(line["class"], report.NA)
        self.assertFalse(line["include_in_degraded"])
        self.assertIn("unbound by surface", line["summary"])
        # Still named, so the unbound inventory stays visible in the report.
        self.assertIn("SEMGREP_APP_TOKEN", line["evidence"])

    def test_unbound_without_the_carve_out_still_degrades(self) -> None:
        for state in ("failed", "ok", ""):
            with self.subTest(state=state):
                line = report.classify_secrets_bind(self.UNBOUND, state)
                self.assertEqual(line["class"], report.DEGRADED)
                self.assertTrue(line["include_in_degraded"])

    def test_source_aws_is_a_fault_on_every_surface(self) -> None:
        """A real fault is never carved out — checked before the unbound branch."""
        leftover = [{"name": "SONAR_TOKEN", "bound": True, "source": "aws"}]
        for state in (report.PLANE_UNAVAILABLE_BY_SURFACE, "failed", ""):
            with self.subTest(state=state):
                line = report.classify_secrets_bind(leftover, state)
                self.assertEqual(line["class"], report.FAILED)
                self.assertTrue(line["include_in_degraded"])

    def test_unread_receipt_is_degraded_whatever_the_state(self) -> None:
        line = report.classify_secrets_bind(None, report.PLANE_UNAVAILABLE_BY_SURFACE)
        self.assertEqual(line["class"], report.DEGRADED)

    def test_report_does_not_contradict_itself_on_a_carved_out_surface(self) -> None:
        """The regression Codex caught: both lines, one cause, one verdict."""
        aws = {"ok": False, "code": "AWS_CLI_NOT_FOUND", "summary": "absent"}
        state = report.PLANE_UNAVAILABLE_BY_SURFACE
        lines = [
            report.classify_aws_cli(aws, state),
            report.classify_secrets_bind(self.UNBOUND, state),
        ]
        self.assertEqual([item["class"] for item in lines], [report.NA, report.NA])
        rendered = report.format_markdown(lines)
        self.assertNotIn("### FAILED", rendered)
        degraded_section = rendered.split("### Degraded", 1)[1]
        self.assertIn("none", degraded_section)


class AwsCliSurfaceClassificationTests(unittest.TestCase):
    """The third state renders as neither ok nor FAILED."""

    ABSENT = {
        "ok": False,
        "code": "AWS_CLI_NOT_FOUND",
        "summary": "AWS_CLI_NOT_FOUND — secrets plane cannot start",
    }

    def test_unavailable_by_surface_is_not_failed_and_not_degraded(self) -> None:
        line = report.classify_aws_cli(self.ABSENT, report.PLANE_UNAVAILABLE_BY_SURFACE)
        self.assertEqual(line["class"], report.NA)
        self.assertFalse(line["include_in_degraded"])
        self.assertFalse(line["this_surface"])
        self.assertIn("unavailable by surface", line["summary"])
        # Still named in the report — visible, just not scored as a fault.
        self.assertEqual(line["evidence"], "AWS_CLI_NOT_FOUND")

    def test_failed_plane_state_still_fails(self) -> None:
        for state in ("failed", ""):
            with self.subTest(state=state):
                line = report.classify_aws_cli(self.ABSENT, state)
                self.assertEqual(line["class"], report.FAILED)
                self.assertTrue(line["include_in_degraded"])

    def test_unread_receipt_still_fails_whatever_the_state(self) -> None:
        line = report.classify_aws_cli(None, report.PLANE_UNAVAILABLE_BY_SURFACE)
        self.assertEqual(line["class"], report.FAILED)

    def test_markdown_omits_the_failed_header_for_the_carve_out(self) -> None:
        carved = report.classify_aws_cli(self.ABSENT, report.PLANE_UNAVAILABLE_BY_SURFACE)
        self.assertNotIn("### FAILED", report.format_markdown([carved]))
        failed = report.classify_aws_cli(self.ABSENT, "failed")
        self.assertIn("### FAILED", report.format_markdown([failed]))


class MemoryProofClassificationTests(unittest.TestCase):
    def test_compatible_unproven_is_not_unbound_or_bound(self) -> None:
        line = report.classify_memory_proof(
            {
                "binding_status": "compatible",
                "ok": True,
                "artifact_provenance": "unproven",
                "memory_package": "l9-graphite-memory",
                "memory_version": "2.3.1",
                "reasons": ["the install recorded no PEP 610 archive hash"],
            }
        )
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("compatible", line["summary"])
        self.assertIn("unproven", line["summary"])
        self.assertIn("PEP 610", line["summary"])
        self.assertNotIn("unbound", line["summary"])
        self.assertFalse(line["summary"].startswith("bound "))

    def test_exact_proved_is_ok_from_measured_ok(self) -> None:
        line = report.classify_memory_proof(
            {
                "binding_status": "exact",
                "ok": True,
                "artifact_provenance": "artifact_sha256",
                "memory_package": "l9-graphite-memory",
                "memory_version": "2.3.1",
                "reasons": [],
            }
        )
        self.assertEqual(line["class"], report.OK)
        self.assertIn("exact", line["summary"])
        self.assertNotIn("bound (", line["summary"])

    def test_missing_ok_is_not_invented_usable(self) -> None:
        line = report.classify_memory_proof({"binding_status": "compatible"})
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertFalse(line["summary"].startswith("bound "))

    def test_json_detail_is_classified_as_proof(self) -> None:
        line = report.classify_memory(
            detail=(
                '{"binding_status":"compatible","ok":true,'
                '"artifact_provenance":"unproven","reasons":["digest unproved"]}'
            ),
            stderr="",
            healthy=False,
        )
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("compatible", line["summary"])
        self.assertNotIn("unbound", line["summary"])

    def test_unbound_runtime_is_an_environment_fault_not_degraded(self) -> None:
        """ADR-0032: a drifted governance .venv is a bootstrap fault; memory was not observed."""

        line = report.classify_memory_proof(
            {
                "binding_status": "unbound",
                "ok": False,
                "environment_fault": True,
                "environment_heal": "skipped:repo-write-lock-held",
                "memory_package": "l9-graphite-memory",
                "memory_version": "2.3.1",
                "reasons": ["package version 2.3.1 does not match expected 2.4.0"],
            }
        )
        self.assertEqual(line["class"], report.ENVIRONMENT_FAULT)
        self.assertTrue(line["summary"].startswith("ENVIRONMENT_FAULT unbound"))
        self.assertIn("heal=skipped:repo-write-lock-held", line["summary"])
        self.assertIn("does not match expected", line["summary"])
        self.assertTrue(line["include_in_degraded"])
        rendered = report.format_markdown([line])
        self.assertIn("- memory: environment_fault — ENVIRONMENT_FAULT", rendered)
        self.assertNotIn("memory: degraded", rendered)

    def test_older_proof_shape_still_classifies_unbound_as_environment(self) -> None:
        line = report.classify_memory_proof(
            {"binding_status": "unbound", "ok": False, "reasons": ["not importable"]}
        )
        self.assertEqual(line["class"], report.ENVIRONMENT_FAULT)

    def test_slogan_is_not_a_live_proof(self) -> None:
        self.assertIsNone(report.parse_binding_proof("unbound: the install recorded no PEP 610"))
        self.assertFalse(report.proof_is_live({"status": "unbound"}))
        self.assertTrue(report.proof_is_live({"binding_status": "compatible", "ok": True}))


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
    def test_unhealthy_memory_still_emits_hydrate_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lines = report.collect(
                surface="cursor",
                venv="UV: cached locked environment",
                ide_profile="applied",
                tunnel="open",
                memory_detail="unreachable",
                memory_stderr="Connection reset by peer",
                memory_healthy=False,
                wiring="PASS",
                backup="PROCEED: reason=- gates clear",
                skill_note="/tmp/x.jsonl (1 entries)",
                codegraph="skipped",
                hydrate_degraded=True,
                hydrate_reason="CANONICAL_UNAVAILABLE: store unreachable",
                home=Path(tmp),
                aws_cli={"ok": True, "code": "OK", "summary": "authorized"},
                secrets_bind=[
                    {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "env"},
                    {"name": "SONAR_TOKEN", "bound": True, "source": "infisical"},
                    {"name": "GITHUB_TOKEN", "bound": True, "source": "infisical"},
                ],
            )
        names = [item["name"] for item in lines]
        self.assertIn("memory", names)
        self.assertIn("memory-hydrate", names)
        hydrate = next(item for item in lines if item["name"] == "memory-hydrate")
        self.assertEqual(hydrate["class"], report.DEGRADED)
        self.assertIn("CANONICAL_UNAVAILABLE", hydrate["summary"])

    def _collect_condition(self, condition: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            lines = report.collect(
                surface="cursor",
                venv="locked",
                ide_profile="applied",
                tunnel="open",
                memory_detail="healthy",
                memory_stderr="",
                memory_healthy=True,
                wiring="PASS",
                backup="armed",
                skill_note="/tmp/x.jsonl (1 entries)",
                codegraph="skipped",
                hydrate_degraded=False,
                hydrate_reason="",
                hydrate_condition=condition,
                home=Path(tmp),
                aws_cli={"ok": True, "code": "OK", "summary": "authorized"},
                secrets_bind=[],
            )
        return next(item for item in lines if item["name"] == "memory-hydrate")

    def test_stale_continuation_is_not_a_degraded_row(self) -> None:
        """ADR-0032: the false positive this fix removes — STALE on an OK hydrate."""
        hydrate = self._collect_condition("STALE: continuation_stale=true")
        self.assertEqual(hydrate["class"], report.OK)
        self.assertFalse(hydrate["include_in_degraded"])
        self.assertTrue(hydrate["summary"].startswith("STALE"))
        rendered = report.format_markdown([hydrate])
        self.assertIn("### Degraded\n- none", rendered)

    def test_close_gap_is_an_ok_row_naming_the_repair(self) -> None:
        hydrate = self._collect_condition("CLOSE_GAP: session abc left no receipt")
        self.assertEqual(hydrate["class"], report.OK)
        self.assertFalse(hydrate["include_in_degraded"])
        self.assertIn("session abc left no receipt", hydrate["summary"])
        self.assertIn("REPAIR: /end-session", hydrate["summary"])

    def test_environment_fault_condition_lands_in_degraded_under_its_own_name(self) -> None:
        hydrate = self._collect_condition("ENVIRONMENT_FAULT: BINDING_FAILED: 2.3.1 != 2.4.0")
        self.assertEqual(hydrate["class"], report.ENVIRONMENT_FAULT)
        self.assertTrue(hydrate["include_in_degraded"])
        self.assertIn("2.3.1 != 2.4.0", hydrate["summary"])
        rendered = report.format_markdown([hydrate])
        self.assertIn("- memory-hydrate: environment_fault — ENVIRONMENT_FAULT", rendered)
        self.assertNotIn("memory-hydrate: degraded", rendered)

    def test_no_condition_and_not_degraded_emits_no_hydrate_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lines = report.collect(
                surface="cursor",
                venv="locked",
                ide_profile="applied",
                tunnel="open",
                memory_detail="healthy",
                memory_stderr="",
                memory_healthy=True,
                wiring="PASS",
                backup="armed",
                skill_note="/tmp/x.jsonl (1 entries)",
                codegraph="skipped",
                hydrate_degraded=False,
                hydrate_reason="",
                hydrate_condition="",
                home=Path(tmp),
                aws_cli={"ok": True, "code": "OK", "summary": "authorized"},
                secrets_bind=[],
            )
        self.assertNotIn("memory-hydrate", [item["name"] for item in lines])

    def test_healthy_memory_keeps_hydrate_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lines = report.collect(
                surface="cursor",
                venv="locked",
                ide_profile="applied",
                tunnel="open",
                memory_detail="healthy",
                memory_stderr="",
                memory_healthy=True,
                wiring="PASS",
                backup="armed",
                skill_note="/tmp/x.jsonl (1 entries)",
                codegraph="skipped",
                hydrate_degraded=True,
                hydrate_reason="empty packet",
                home=Path(tmp),
                aws_cli={"ok": True, "code": "OK", "summary": "authorized"},
                secrets_bind=[
                    {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "env"},
                    {"name": "SONAR_TOKEN", "bound": True, "source": "infisical"},
                    {"name": "GITHUB_TOKEN", "bound": True, "source": "infisical"},
                ],
            )
        names = [item["name"] for item in lines]
        self.assertIn("memory-hydrate", names)


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
        self.assertNotIn("ARCHIVE_ARGS=(--archive-spent)", text)
        self.assertNotIn('"${ARCHIVE_ARGS[@]}"', text)
        self.assertNotIn("audit_pipeline.py", text)
        self.assertIn("audit_plans.py", text)
        self.assertIn("UNBUILT_MD", text)
        self.assertIn("--format session-start", text)
        self.assertNotIn("### Plan audit", text)
        self.assertNotIn("PLAN_AUDIT_MD", text)
        self.assertNotIn("TUNNEL_NOTE", text)
        self.assertNotIn("--tunnel ", text)
        bootstrap = (REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("session_start_secrets.py", bootstrap)
        self.assertIn("--receipt-out", bootstrap)
        self.assertIn("$WORKSPACE/ops/secrets/session_start_secrets.py", bootstrap)
        self.assertLess(
            bootstrap.index("$WORKSPACE/ops/secrets/session_start_secrets.py"),
            bootstrap.index("$GOV_DIR/ops/secrets/session_start_secrets.py"),
        )
        self.assertIn('rm -f "$SECRETS_RECEIPT"', bootstrap)
        self.assertNotIn("itest: unavailable — neo4j absent", text)
        self.assertNotIn("publish-path grant: none", text)
        self.assertNotIn("GRANT_NOTE", text)
        self.assertNotIn("ITEST_NOTE", text)
        self.assertNotIn("BOOTSTRAP_NOTE", text)
        self.assertNotIn("plugins, IDE, cold venv", text)
        self.assertNotIn("cold venv", text)
        self.assertNotIn("bound ($BINDING_STATUS)", text)
        self.assertNotIn("exact|compatible|development_checkout", text)
        self.assertNotIn("""echo '{"status":"unbound"}'""", text)
        self.assertNotIn('BACKUP_NOTE="armed"', text)
        self.assertNotIn('VENV_NOTE="locked (uv.lock)"', text)
        self.assertIn("backup_gate.sh", text)
        self.assertIn("ensure_uv_environment.sh", text)
        reporter = (REPO / "ops" / "scripts" / "session_start_runtime_report.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("debug-eb0fc6", reporter)
        self.assertNotIn("def probe_aws_cli", reporter)
        self.assertNotIn("def probe_secrets_bind", reporter)
        self.assertNotIn("else probe_", reporter)
        self.assertNotIn("bind_status", reporter)

    def test_cursor_hook_heals_links_in_non_migrating_plans_mode(self) -> None:
        """F-08: SessionStart wires links without the plans-store migration.

        ensure_workspace_wired.sh unconditionally called the machine
        plans-store helper, which copies, renames aside and replaces a legacy
        real ~/.cursor/plans directory. The hook must call it in a mode where
        that helper never runs against an existing entry, and must not fall
        through to setup_workspace_symlinks.sh / check_governance_wiring.sh
        (both call the helper unconditionally) while such a directory exists.
        """
        text = (REPO / "ops" / "hooks" / "session_start_bootstrap.sh").read_text(encoding="utf-8")
        for line in text.splitlines():
            if 'bash "$ENSURE"' in line:
                self.assertIn("L9_PLANS_STORE_MODE=links-only", line, line)
        self.assertIn("plans_store_is_legacy_real", text)
        ensure = (REPO / "ops" / "scripts" / "ensure_workspace_wired.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("L9_PLANS_STORE_MODE", ensure)
        self.assertIn("links-only", ensure)
        # The helper is still the default for manual callers, never removed.
        self.assertIn("ensure_machine_cursor_plans_store", ensure)

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
        # The ceiling is the CLAMPED one ("$_gen_cap"), not the raw configured
        # default: a fixed 90 s inside a 30 s hook could only ever be killed. The
        # invariant this test owns is unchanged — go through the portable
        # wrapper, never bare `timeout`, never a stub.
        self.assertNotRegex(text, r'(?<!run_with_)timeout "\$_gen_cap"')
        self.assertNotRegex(
            text,
            r'(?<!run_with_)timeout "\$\{L9_BOOTSTRAP_GENERATE_BUDGET:-90\}"',
        )
        self.assertNotIn('run_with_timeout() { shift; "$@"; }', text)
        skipped = text.index("bootstrap receipt: NOT GENERATED — run_with_timeout.sh missing")
        generate = text.index('run_with_timeout "$_gen_cap"', skipped)
        installer = text.index('bash "$installer"', generate)
        self.assertLess(skipped, generate)
        self.assertLess(generate, installer)


class ReceiptSurfaceIsolationTests(unittest.TestCase):
    """A receipt written for another workspace or $HOME is never this session's fault."""

    def test_claude_home_receipt_is_stale_other_surface_not_degraded(self) -> None:
        home = str(Path.home())
        lines = report.classify_claude_adapter(
            surface="claude-code",
            receipt={
                "state": "degraded",
                "reason": "degraded: capabilities",
                "workspace": home,
                "generated_at": "2026-09-02T20:19:36Z",
            },
            repair_log="",
            repair_text="",
            workspace="/Users/someone/Cursor-Governance",
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["class"], report.NA)
        self.assertIn("stale_other_surface", lines[0]["summary"])
        self.assertIn("$HOME", lines[0]["summary"])
        self.assertFalse(lines[0]["include_in_degraded"])

    def test_claude_other_workspace_receipt_is_stale_other_surface(self) -> None:
        lines = report.classify_claude_adapter(
            surface="claude-code",
            receipt={
                "state": "failed",
                "reason": "installer failed",
                "workspace": "/tmp/some-other-clone",
            },
            repair_log="",
            repair_text="",
            workspace="/tmp/this-clone",
        )
        self.assertEqual(lines[0]["class"], report.NA)
        self.assertIn("stale_other_surface", lines[0]["summary"])
        self.assertFalse(lines[0]["include_in_degraded"])

    def test_claude_this_workspace_receipt_still_scores(self) -> None:
        lines = report.classify_claude_adapter(
            surface="claude-code",
            receipt={
                "state": "failed",
                "reason": "installer failed at stage 'settings'",
                "workspace": "/tmp/this-clone",
            },
            repair_log="",
            repair_text="",
            workspace="/tmp/this-clone",
        )
        self.assertEqual(lines[0]["class"], report.FAILED)
        self.assertTrue(lines[0]["include_in_degraded"])

    def test_receipt_without_workspace_is_not_invented_stale(self) -> None:
        lines = report.classify_claude_adapter(
            surface="claude-code",
            receipt={"state": "ready", "reason": "all components READY (10s ago)"},
            repair_log="",
            repair_text="",
            workspace="/tmp/this-clone",
        )
        self.assertEqual(lines[0]["class"], report.OK)


class CursorAdapterClassificationTests(unittest.TestCase):
    def test_not_cursor_surface_emits_nothing(self) -> None:
        self.assertEqual(
            report.classify_cursor_adapter(
                surface="claude-code", receipt={"state": "ready"}, workspace="/tmp/ws"
            ),
            [],
        )

    def test_never_ran_is_ceremony_failure(self) -> None:
        lines = report.classify_cursor_adapter(
            surface="cursor",
            receipt={"state": "never_ran", "reason": "no bootstrap receipt on disk"},
            workspace="/tmp/ws",
        )
        self.assertEqual(lines[0]["class"], report.FAILED)
        self.assertIn("every bootstrap", lines[0]["summary"])
        self.assertTrue(lines[0]["include_in_degraded"])

    def test_ready_this_workspace_is_ok(self) -> None:
        lines = report.classify_cursor_adapter(
            surface="cursor",
            receipt={"state": "ready", "reason": "all READY", "workspace": "/tmp/ws"},
            workspace="/tmp/ws",
        )
        self.assertEqual(lines[0]["class"], report.OK)

    def test_other_workspace_cursor_receipt_is_stale(self) -> None:
        lines = report.classify_cursor_adapter(
            surface="cursor",
            receipt={"state": "degraded", "reason": "x", "workspace": "/tmp/other"},
            workspace="/tmp/ws",
        )
        self.assertEqual(lines[0]["class"], report.NA)
        self.assertIn("stale_other_surface", lines[0]["summary"])

    def test_ttl_unknown_is_ceremony_failure(self) -> None:
        lines = report.classify_cursor_adapter(
            surface="cursor",
            receipt={
                "state": "unknown",
                "reason": "receipt expired (764027s old, ttl 86400s)",
                "workspace": "/tmp/ws",
            },
            workspace="/tmp/ws",
        )
        self.assertEqual(lines[0]["class"], report.FAILED)
        self.assertIn("stale_receipt", lines[0]["summary"])
        self.assertTrue(lines[0]["include_in_degraded"])

    def test_fresh_this_workspace_failed_reaches_degraded(self) -> None:
        lines = report.classify_cursor_adapter(
            surface="cursor",
            receipt={"state": "failed", "reason": "hooks.json missing", "workspace": "/tmp/ws"},
            workspace="/tmp/ws",
        )
        self.assertEqual(lines[0]["class"], report.FAILED)
        self.assertTrue(lines[0]["include_in_degraded"])


class ReceiptReaderSurfaceTests(unittest.TestCase):
    def test_cursor_surface_maps_to_cursor_receipt_path(self) -> None:
        import claude_bootstrap_receipt as cbr

        path = cbr.receipt_path(env={"HOME": "/tmp/h"}, surface="cursor")
        self.assertEqual(str(path), "/tmp/h/.l9/cursor/bootstrap-state.json")
        self.assertEqual(cbr.schema_for("cursor"), "l9.cursor-bootstrap.v2")
        self.assertEqual(cbr.schema_for("claude"), "l9.claude-bootstrap.v1")

    def test_claude_code_alias_maps_to_claude_dir(self) -> None:
        import claude_bootstrap_receipt as cbr

        path = cbr.receipt_path(env={"HOME": "/tmp/h"}, surface="claude-code")
        self.assertEqual(str(path), "/tmp/h/.l9/claude/bootstrap-state.json")

    def test_generic_override_wins(self) -> None:
        import claude_bootstrap_receipt as cbr

        path = cbr.receipt_path(
            env={"HOME": "/tmp/h", "L9_CURSOR_BOOTSTRAP_RECEIPT": "/tmp/x.json"},
            surface="cursor",
        )
        self.assertEqual(str(path), "/tmp/x.json")

    def test_never_ran_remediation_names_session_start(self) -> None:
        import claude_bootstrap_receipt as cbr

        cursor = cbr.evaluate(None, surface="cursor")
        self.assertIn("start WS=", cursor["remediation"])
        claude = cbr.evaluate(None, surface="claude")
        self.assertIn("claude-code/install.sh", claude["remediation"])


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


class MemoryProbeFaultTests(unittest.TestCase):
    """An expected probe fault is evidence with a reason; an unexpected one surfaces."""

    def test_expected_fault_becomes_structured_proof(self) -> None:
        with mock.patch(
            "ops.memory.runtime_binding.resolve_runtime_binding",
            side_effect=RuntimeError("manifest unreadable"),
        ):
            proof = report.probe_memory_binding()
        self.assertIsNotNone(proof)
        assert proof is not None
        self.assertTrue(report.proof_is_live(proof))
        self.assertFalse(proof["ok"])
        self.assertEqual(proof["binding_status"], "probe-error")
        self.assertEqual(proof["reasons"], ["RuntimeError: manifest unreadable"])
        line = report.classify_memory_proof(proof)
        self.assertEqual(line["class"], report.DEGRADED)
        self.assertIn("manifest unreadable", line["summary"])

    def test_unexpected_exception_is_not_swallowed(self) -> None:
        with (
            mock.patch(
                "ops.memory.runtime_binding.resolve_runtime_binding",
                side_effect=ZeroDivisionError("defect in binding code"),
            ),
            self.assertRaises(ZeroDivisionError),
        ):
            report.probe_memory_binding()


class SessionStartCeremonyTests(unittest.TestCase):
    def _collect(self, tmp: Path, **kwargs: object) -> list:
        defaults: dict = {
            "surface": "cursor",
            "venv": "UV: cached locked environment",
            "ide_profile": "applied",
            "memory_detail": "healthy",
            "memory_stderr": "",
            "memory_healthy": True,
            "wiring": "PASS",
            "backup": "PROCEED: reason=- gates clear",
            "skill_note": "/tmp/x.jsonl (1 entries)",
            "hydrate_degraded": False,
            "hydrate_reason": "",
            "home": tmp,
            "workspace": str(tmp),
            "aws_cli": {"ok": True, "code": "OK", "summary": "authorized"},
            "secrets_bind": [
                {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "infisical"},
                {"name": "SONAR_TOKEN", "bound": True, "source": "infisical"},
                {"name": "GITHUB_TOKEN", "bound": True, "source": "infisical"},
            ],
        }
        defaults.update(kwargs)
        return report.collect(**defaults)

    def test_collect_omits_tunnel_and_neo4j(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
            (tmp / "AGENTS.md").write_text("agents\n", encoding="utf-8")
            names = [
                item["name"] for item in self._collect(tmp, tunnel="open", codegraph="skipped")
            ]
        self.assertNotIn("tunnel", names)
        self.assertNotIn("itest/neo4j", names)

    def test_collect_writes_cursor_receipt_every_run(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
            (tmp / "AGENTS.md").write_text("agents\n", encoding="utf-8")
            cursor_dir = tmp / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "hooks.json").write_text(
                '{"sessionStart":[{"command":"session-start-bootstrap.sh"}]}',
                encoding="utf-8",
            )
            plugin = tmp / ".cursor" / "plugins" / "local" / "l9-governance"
            plugin.mkdir(parents=True)
            lines = self._collect(tmp)
            receipt_path = tmp / ".l9" / "cursor" / "bootstrap-state.json"
            self.assertTrue(receipt_path.is_file())
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "l9.cursor-bootstrap.v2")
            self.assertEqual(payload["mode"], "session-start")
            self.assertEqual(payload["workspace"], str(tmp))
            self.assertIn(payload["state"], {"READY", "DEGRADED", "FAILED"})
            self.assertEqual(payload["probes"]["mcp"], "alias:memory")
            self.assertEqual(payload["probes"]["hooks"], "hooks.json")
            names = [item["name"] for item in lines]
            self.assertIn("cursor-adapter", names)
            cursor = next(item for item in lines if item["name"] == "cursor-adapter")
            self.assertNotEqual(cursor["class"], report.NA)


if __name__ == "__main__":
    unittest.main()
