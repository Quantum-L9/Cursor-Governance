"""Session locator: one receipt identity per conversation (VSP phase 7)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.skill_routing import session_locator as loc  # noqa: E402

LOCATOR = ROOT / "ops" / "skill_routing" / "session_locator.py"


def test_conversation_key_is_truncated_sha256():
    key = loc.conversation_key("conv-1")
    assert key == hashlib.sha256(b"conv-1").hexdigest()[:32]
    assert key.isalnum()


def test_session_start_and_before_submit_share_identity(tmp_path: Path):
    """Both Cursor events carry conversation_id; session_id is never the key."""
    start = {
        "hook_event_name": "sessionStart",
        "conversation_id": "conv-1",
        "session_id": "sess-9",
        "workspace_roots": [str(tmp_path)],
    }
    submit = {
        "hook_event_name": "beforeSubmitPrompt",
        "conversation_id": "conv-1",
        "generation_id": "gen-2",
        "workspace_roots": [str(tmp_path)],
        "prompt": "x",
    }
    a = loc.locator_from_payload(start, tmp_path / "routes")
    b = loc.locator_from_payload(submit, tmp_path / "routes")
    assert a is not None and b is not None
    assert a.receipt_path == b.receipt_path
    assert a.workspace_key == b.workspace_key
    assert "sess-9" not in a.receipt_path


def test_missing_conversation_id_is_unresolved(monkeypatch):
    monkeypatch.delenv(loc.CONVERSATION_ENV, raising=False)
    assert loc.locator_from_payload({"session_id": "only-session"}) is None
    # sessionStart-exported env is the fallback correlation for later hooks.
    monkeypatch.setenv(loc.CONVERSATION_ENV, "conv-env")
    built = loc.locator_from_payload({})
    assert built is not None and built.conversation_id == "conv-env"


def test_workspace_roots_normalized_and_order_independent(tmp_path: Path):
    a = loc.locator_from_payload(
        {"conversation_id": "c", "workspace_roots": [str(tmp_path / "b"), str(tmp_path / "a")]}
    )
    b = loc.locator_from_payload(
        {"conversation_id": "c", "workspace_roots": [str(tmp_path / "a"), str(tmp_path / "b")]}
    )
    assert a is not None and b is not None
    assert a.workspace_key == b.workspace_key
    single = loc.locator_from_payload({"conversation_id": "c", "workspace_roots": str(tmp_path)})
    assert single is not None and single.workspace_roots == [str(tmp_path.resolve())]


def test_cli_banner_env_json(tmp_path: Path):
    payload = json.dumps({"conversation_id": "conv-cli", "workspace_roots": [str(tmp_path)]})
    base = [sys.executable, str(LOCATOR), "--payload-json", payload, "--state-root", str(tmp_path)]
    banner = subprocess.run([*base, "--banner"], capture_output=True, text=True, check=True).stdout
    assert banner.startswith("### Route locator")
    assert loc.conversation_key("conv-cli") in banner
    env = json.loads(
        subprocess.run([*base, "--env"], capture_output=True, text=True, check=True).stdout
    )
    assert env[loc.CONVERSATION_ENV] == "conv-cli"
    assert env[loc.LOCATOR_ENV].endswith("current.json")
    full = json.loads(subprocess.run(base, capture_output=True, text=True, check=True).stdout)
    assert full["resolved"] is True and full["conversation_key"] == loc.conversation_key("conv-cli")


def test_session_start_bootstrap_owns_the_locator_wiring():
    """The Cursor sessionStart hook reads the payload once and delegates to Python."""
    hook = (ROOT / "ops" / "hooks" / "session_start_bootstrap.sh").read_text(encoding="utf-8")
    assert "read -r -t 3 -d '' L9_HOOK_PAYLOAD" in hook
    assert "session_locator.py" in hook
    assert "--banner" in hook and "--env" in hook
    assert "${ROUTE_LOCATOR_MD}" in hook
    assert "ROUTE_LOCATOR_ENV" in hook
    # No shell-side JSON parsing of the payload.
    assert "conversation_id" not in hook.replace(
        "# Cursor hands the sessionStart payload (conversation_id", ""
    )


def test_cli_unresolved_payload(tmp_path: Path):
    proc = subprocess.run(
        [sys.executable, str(LOCATOR), "--payload-json", "not json", "--banner"],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert "unresolved" in proc.stdout
