#!/usr/bin/env python3
"""Idempotent repair of tests and doctrine after the approved PE source cutover."""
from __future__ import annotations

import re
from pathlib import Path


def update(path: str, fn) -> None:
    p = Path(path)
    before = p.read_text(encoding="utf-8")
    after = fn(before)
    if after != before:
        p.write_text(after, encoding="utf-8")


def clean_promotion_test(text: str) -> str:
    text = text.replace("import hashlib\n", "")
    if (
        "def test_stale_top_level_pe_manifest_is_advisory" in text
        and "def test_missing_top_level_pe_manifest_is_advisory" in text
        and "PE_MANIFEST_ROOT" not in text
        and "regenerate_manifest(" not in text
    ):
        return text
    text = re.sub(
        r"\n\ndef regenerate_manifest\(root: Path\) -> None:\n.*?(?=\n\nclass PromotionValidatorTest)",
        "",
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace("    regenerate_manifest(root)\n", "")
    text = re.sub(r"^\s*regenerate_manifest\(self\.root\)\n", "", text, flags=re.M)
    text = text.replace('                "GENERATED_ARTIFACTS_CURRENT": "PASS",\n', "")
    text = re.sub(
        r"\n    # -- condition 6: generated projections are current.*?(?=\n\nclass RealRepositoryTest)",
        "",
        text,
        count=1,
        flags=re.S,
    )
    advisory = '''\n    # -- top-level PE MANIFEST is advisory by settled policy ----------------\n\n    def test_stale_top_level_pe_manifest_is_advisory(self) -> None:\n        manifest = self.root / "environment/program-execution/MANIFEST.json"\n        manifest.parent.mkdir(parents=True, exist_ok=True)\n        manifest.write_text('{"generated": "stale"}\\n', encoding="utf-8")\n        report = validator.validate(self.root)\n        self.assertEqual(report["status"], "PASS", report["errors"])\n        self.assertNotIn("GENERATED_ARTIFACTS_CURRENT", report["summary"])\n\n    def test_missing_top_level_pe_manifest_is_advisory(self) -> None:\n        manifest = self.root / "environment/program-execution/MANIFEST.json"\n        if manifest.exists():\n            manifest.unlink()\n        report = validator.validate(self.root)\n        self.assertEqual(report["status"], "PASS", report["errors"])\n        self.assertNotIn("GENERATED_ARTIFACTS_CURRENT", report["summary"])\n'''
    marker = "\n\nclass RealRepositoryTest"
    if marker not in text:
        raise SystemExit("post-apply: promotion advisory insertion marker missing")
    text = text.replace(marker, advisory + marker, 1)
    if "PE_MANIFEST_ROOT" in text or "regenerate_manifest(" in text:
        raise SystemExit("post-apply: stale promotion-manifest test references remain")
    return text


def clean_local_only_test(text: str) -> str:
    replacement = '''    # ---- legacy release env cannot widen authority -------------------------\n\n    def test_release_environment_never_reopens_publication(self) -> None:\n        with unittest.mock.patch.dict(\n            "os.environ", {"L9_PE_RELEASE_AUTHORIZED": "operator release"}\n        ):\n            self.assertFalse(self.mod.release_authorized())\n            for call in (\n                lambda: self.mod.refuse_publication("push a branch"),\n                lambda: self.mod.refuse_live_until_shortcut("pr"),\n                lambda: self.mod.refuse_live_until_shortcut("close"),\n                lambda: self.mod.refuse_live_until_shortcut("merge"),\n            ):\n                with self.assertRaises(self.mod.CampaignError) as ctx:\n                    call()\n                self.assertIn("permanently local-commit-only", str(ctx.exception))\n'''
    text, count = re.subn(
        r"    # ---- the release transition still works \(authority preserved\) -----------\n\n    def test_release_transition_reopens_publication\(self\) -> None:\n.*?(?=\n\nclass FastModeDoesNotWidenAuthorityTests)",
        replacement,
        text,
        count=1,
        flags=re.S,
    )
    if count == 0 and "test_release_environment_never_reopens_publication" not in text:
        raise SystemExit("post-apply: local-only release test anchor missing")
    return text


def clean_tunnel_test(text: str) -> str:
    return re.sub(
        r"\n    def test_release_env_cannot_reopen_remote_stages\(self\) -> None:\n.*?(?=\n\nif __name__ == \"__main__\":)",
        "",
        text,
        count=1,
        flags=re.S,
    )


def clean_run_campaign_test(text: str) -> str:
    text = text.replace(
        '"validation": [{"command": "python3 -c \'print(0)\'"}],',
        '"validation": [{"command": "git status --short"}],',
    )
    text = text.replace(
        '["python3 -c \'print(0)\'"]',
        '["git status --short"]',
    )
    text = text.replace(
        'self.assertIn("host-only merge", str(ctx.exception))',
        'self.assertIn("permanently local-commit-only", str(ctx.exception))',
    )
    return text.replace(
        '                "execute",\n                "pr",\n',
        '                "execute",\n',
    )


def clean_smoke_test(text: str) -> str:
    return text.replace(
        'attempts = list((workspace / "attempts").rglob(f"*{task_id}*.json"))',
        'attempts = list((workspace / "attempts" / task_id).glob("*.json"))',
    )


def clean_runner_message(text: str) -> str:
    return text.replace(
        "campaign complete: local commits only; publication is a release transition",
        "campaign complete: local commits only; publish separately with PR_REMEDIATE=0 make pr",
    )


def clean_peer_verdict_gate(text: str) -> str:
    old = '''    decision = dispatch_kernel_change(verification)\n    if decision["action"] != "pass":\n        raise CampaignError(\n            f"Diagnose First: Peer Core attempt for {task_id} did not verify cleanly; "\n            f"action={decision['action']} reason={decision['reason']}"\n        )\n    if verification.get("verdict") != "PASSED_LOCAL":\n        raise CampaignError(\n            f"pec verify {task_id} did not PASS: {verification.get('verdict')}; "\n            f"failed gates={json.dumps(failed_gates(verification), sort_keys=True)}"\n        )\n'''
    new = '''    if verification.get("verdict") != "PASSED_LOCAL":\n        decision = dispatch_kernel_change(verification)\n        reason = str(\n            decision.get("reason")\n            or verification.get("kernel_verdict")\n            or verification.get("verdict")\n            or "UNKNOWN"\n        )\n        raise CampaignError(\n            f"Diagnose First: Peer Core attempt for {task_id} did not verify cleanly; "\n            f"action={decision.get('action', 'unknown')} reason={reason}; "\n            f"failed gates={json.dumps(failed_gates(verification), sort_keys=True)}; "\n            f"incomplete gates={json.dumps(incomplete_gates(verification), sort_keys=True)}"\n        )\n'''
    if old in text:
        return text.replace(old, new, 1)
    if 'if verification.get("verdict") != "PASSED_LOCAL":\n        decision = dispatch_kernel_change(verification)' in text:
        return text
    raise SystemExit("post-apply: Peer verdict gate anchor missing")


update("environment/program-execution/scripts/tests/test_validate_campaign_promotion.py", clean_promotion_test)
update("environment/program-execution/scripts/tests/test_pe_local_commit_only.py", clean_local_only_test)
update("environment/program-execution/scripts/tests/test_campaign_tunnel_airtight.py", clean_tunnel_test)
update("environment/program-execution/scripts/tests/test_run_campaign.py", clean_run_campaign_test)
update("environment/program-execution/scripts/tests/test_pe_smoke_campaign.py", clean_smoke_test)
update("environment/program-execution/scripts/run_campaign.py", clean_runner_message)
update("environment/program-execution/scripts/run_campaign.py", clean_peer_verdict_gate)
Path(".github/pe-executor-failure.txt").unlink(missing_ok=True)
print("post-apply behavioral/test repair complete")
