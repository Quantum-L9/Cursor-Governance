"""One resolver for every local_execution_gate consumer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
AUTONOMY = REPO / "ops" / "autonomy"
if str(AUTONOMY) not in sys.path:
    sys.path.insert(0, str(AUTONOMY))

import resolve_execution_gate as resolver  # noqa: E402

HOOK = REPO / "ops" / "hooks" / "l4-local-execution-gate-shell.sh"
WRAP = (
    REPO
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "local_execution_gate_wrap.py"
)
GATE = AUTONOMY / "local_execution_gate.py"


def _identity_tree(root: Path) -> Path:
    (root / "skills").mkdir(parents=True)
    (root / "rules").mkdir(parents=True)
    (root / "ops" / "scripts").mkdir(parents=True)
    (root / "ops" / "autonomy").mkdir(parents=True)
    (root / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
    (root / "skills" / "AUTONOMY_MANIFEST.yaml").write_text("x: 1\n", encoding="utf-8")
    (root / "rules" / "RULES-MANIFEST.yaml").write_text("rules: []\n", encoding="utf-8")
    (root / "ops" / "scripts" / "check_governance_wiring.sh").write_text(
        "#!/bin/sh\n", encoding="utf-8"
    )
    gate = root / "ops" / "autonomy" / "local_execution_gate.py"
    gate.write_text("# checkout gate\n", encoding="utf-8")
    return gate


def test_override_wins(tmp_path: Path) -> None:
    other = tmp_path / "custom_gate.py"
    other.write_text("# override\n", encoding="utf-8")
    found = resolver.resolve_gate(
        workspace=tmp_path / "consumer",
        home=tmp_path / "home",
        env={resolver.OVERRIDE_ENV: str(other)},
    )
    assert found == other.resolve()


def test_identity_checkout_beats_ssot(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ssot = _identity_tree(home / ".cursor-governance")
    checkout = _identity_tree(tmp_path / "worktree")
    found = resolver.resolve_gate(workspace=tmp_path / "worktree", home=home, env={})
    assert found == checkout.resolve()
    assert found != ssot.resolve()


def test_consumer_workspace_does_not_win(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ssot_gate = _identity_tree(home / ".cursor-governance")
    consumer = tmp_path / "app"
    consumer.mkdir()
    (consumer / "ops" / "autonomy").mkdir(parents=True)
    fake = consumer / "ops" / "autonomy" / "local_execution_gate.py"
    fake.write_text("# planted copy\n", encoding="utf-8")
    found = resolver.resolve_gate(workspace=consumer, home=home, env={})
    assert found == ssot_gate.resolve()


def test_hook_adjacent_when_no_workspace(tmp_path: Path) -> None:
    gov = tmp_path / "gov"
    hooks = gov / "ops" / "hooks"
    hooks.mkdir(parents=True)
    gate = _identity_tree(gov)
    hook = hooks / "l4-local-execution-gate-shell.sh"
    hook.write_text("#!/bin/sh\n", encoding="utf-8")
    found = resolver.resolve_gate(hook_file=hook, home=tmp_path / "empty-home", env={})
    assert found == gate.resolve()


def test_missing_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolver.resolve_gate(workspace=tmp_path / "nope", home=tmp_path / "home", env={})


def test_cli_reads_cwd_from_event(tmp_path: Path) -> None:
    checkout_gate = _identity_tree(tmp_path / "wt")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"cwd": str(tmp_path / "wt")}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(AUTONOMY / "resolve_execution_gate.py"), "--event-json", str(event)],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != resolver.OVERRIDE_ENV},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == checkout_gate.resolve()


def test_hook_and_wrap_name_the_resolver() -> None:
    hook = HOOK.read_text(encoding="utf-8")
    wrap = WRAP.read_text(encoding="utf-8")
    assert "resolve_execution_gate.py" in hook
    assert "failing closed" in hook
    assert "2>/dev/null" not in hook
    assert '{"permission":"allow"}' not in hook
    assert "resolve_execution_gate" in wrap
    assert "ops gate missing; skip" not in wrap


def test_repo_checkout_resolves_this_gate() -> None:
    found = resolver.resolve_gate(workspace=REPO, hook_file=HOOK, env={})
    assert found == GATE.resolve()


def test_cursor_hook_denies_when_resolver_missing(tmp_path: Path) -> None:
    """A hook that cannot find the resolver must not fail open."""
    hook = tmp_path / "l4-local-execution-gate-shell.sh"
    hook.write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
    hook.chmod(0o755)
    proc = subprocess.run(
        ["bash", str(hook)],
        input='{"command":"make push"}',
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(tmp_path / "empty-home")},
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["permission"] == "deny"
    assert "INTERNAL_EVALUATION_ERROR" in payload["user_message"]
