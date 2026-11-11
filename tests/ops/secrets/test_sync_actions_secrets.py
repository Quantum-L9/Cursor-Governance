"""sync_actions_secrets: values reach gh on stdin only, never argv or output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import sync_actions_secrets as sas  # noqa: E402

CANARIES = {
    "SONAR_TOKEN": "canary-sonar-7d1e-not-real",
    "PERPLEXITY_API_KEY": "canary-pplx-22ab-not-real",
    "GITGUARDIAN_API_KEY": "canary-gg-90fe-not-real",
    "SEMGREP_APP_TOKEN": "canary-semgrep-41c0-not-real",
    "GITHUB_TOKEN": "canary-pat-5b77-not-real",
}


class FakeRun:
    """Records every subprocess.run call; never runs anything."""

    def __init__(self, *, probe_ok: bool = True, set_rc: int = 0, set_stderr: str = "") -> None:
        self.calls: list[dict[str, Any]] = []
        self.probe_ok = probe_ok
        self.set_rc = set_rc
        self.set_stderr = set_stderr

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": list(argv), **kwargs})
        if argv[:2] == ["gh", "api"]:
            rc = 0 if self.probe_ok else 1
            return subprocess.CompletedProcess(argv, rc, "3\n" if rc == 0 else "", "")
        if argv[:3] == ["gh", "secret", "set"]:
            return subprocess.CompletedProcess(argv, self.set_rc, "", self.set_stderr)
        raise AssertionError(f"unexpected command {argv[:3]}")

    def secret_sets(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["argv"][:3] == ["gh", "secret", "set"]]


@pytest.fixture
def fake_bind(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    values = dict(CANARIES)

    def bind(name: str, **_kwargs: Any) -> str | None:
        value = values.get(name)
        sas.cb._SOURCES[name] = "infisical" if value else "unbound"
        return value

    monkeypatch.setattr(sas.cb, "bind", bind)
    monkeypatch.setattr(sas.cb, "reset_cache", lambda: None)
    return values


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    runner = FakeRun()
    monkeypatch.setattr(sas.subprocess, "run", runner)
    return runner


def _assert_no_leak(text: str) -> None:
    for value in CANARIES.values():
        assert value not in text


def test_committed_plan_loads_and_is_in_inventory() -> None:
    plan = sas.load_plan()
    assert len(plan.entries) == 6
    assert plan.sdk_token is not None
    assert plan.sdk_token.vault_name == "GITHUB_TOKEN"
    assert plan.vault_names <= sas.root_env_keys()


def test_dry_run_makes_no_secret_set(
    fake_bind: dict[str, str], fake_run: FakeRun, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = sas.main(["--dry-run", "--with-sdk-token"])
    assert rc == 0
    assert fake_run.secret_sets() == []
    out = capsys.readouterr()
    assert "would set Quantum-L9/Enrichment.Inference.Engine SDK_TOKEN" in out.out
    _assert_no_leak(out.out + out.err)


def test_value_reaches_gh_only_through_stdin(
    fake_bind: dict[str, str], fake_run: FakeRun, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = sas.main(["--with-sdk-token"])
    assert rc == 0
    sets = fake_run.secret_sets()
    assert len(sets) == 7
    for call in sets:
        assert call["input"] in CANARIES.values()
        argv = " ".join(call["argv"])
        _assert_no_leak(argv)
        env = call.get("env")
        if env is not None:
            _assert_no_leak(json.dumps(env))
    by_target = {(c["argv"][5], c["argv"][3]): c["input"] for c in sets}
    assert by_target[("cryptoxdog/IB-Odoo_19", "SONARCLOUD_API_KEY")] == CANARIES["SONAR_TOKEN"]
    assert (
        by_target[("Quantum-L9/Enrichment.Inference.Engine", "SDK_TOKEN")]
        == (CANARIES["GITHUB_TOKEN"])
    )
    for call in fake_run.calls:
        if call["argv"][:2] == ["gh", "api"]:
            _assert_no_leak(" ".join(call["argv"]))
    out = capsys.readouterr()
    _assert_no_leak(out.out + out.err)


def test_gh_failure_output_is_never_printed(
    fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRun(set_rc=1, set_stderr=f"HTTP 403 echoing {CANARIES['SONAR_TOKEN']}")
    monkeypatch.setattr(sas.subprocess, "run", runner)
    rc = sas.main([])
    assert rc == 1
    out = capsys.readouterr()
    assert "FAIL" in out.out
    assert "HTTP 403 echoing" not in out.out + out.err
    _assert_no_leak(out.out + out.err)


def test_unbound_vault_name_is_nonzero(
    fake_bind: dict[str, str], fake_run: FakeRun, capsys: pytest.CaptureFixture[str]
) -> None:
    del fake_bind["PERPLEXITY_API_KEY"]
    rc = sas.main([])
    assert rc == 1
    out = capsys.readouterr().out
    assert "SKIP Quantum-L9/Enrichment.Inference.Engine PERPLEXITY_API_KEY" in out
    targets = {c["argv"][3] for c in fake_run.secret_sets()}
    assert "PERPLEXITY_API_KEY" not in targets
    assert len(fake_run.secret_sets()) == 5


def _write_plan(tmp_path: Path, vault_name: str, sdk_vault: str = "GITHUB_TOKEN") -> Path:
    plan = {
        "schema": sas.SCHEMA,
        "secrets": [{"repo": "o/r", "secret": "X_TOKEN", "vault_name": vault_name}],
        "sdk_token": {"repos": ["o/r"], "vault_name": sdk_vault, "must_read": "o/s"},
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


def test_plan_entry_outside_root_env_keys_fails_on_load(tmp_path: Path) -> None:
    with pytest.raises(sas.PlanError, match="NOT_A_VAULT_KEY"):
        sas.load_plan(_write_plan(tmp_path, "NOT_A_VAULT_KEY"))
    with pytest.raises(sas.PlanError, match="NOT_A_VAULT_KEY"):
        sas.load_plan(_write_plan(tmp_path, "SONAR_TOKEN", sdk_vault="NOT_A_VAULT_KEY"))


def test_bad_plan_exits_two_before_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_run: FakeRun
) -> None:
    def no_bind(*_a: Any, **_k: Any) -> None:
        raise AssertionError("bind must not run for an invalid plan")

    monkeypatch.setattr(sas.cb, "bind", no_bind)
    rc = sas.main(["--plan", str(_write_plan(tmp_path, "NOT_A_VAULT_KEY"))])
    assert rc == 2
    assert fake_run.calls == []


def test_sdk_token_skipped_when_read_probe_fails(
    fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRun(probe_ok=False)
    monkeypatch.setattr(sas.subprocess, "run", runner)
    rc = sas.main(["--with-sdk-token"])
    assert rc == 1
    assert "SDK_TOKEN" not in {c["argv"][3] for c in runner.secret_sets()}
    assert len(runner.secret_sets()) == 6
    out = capsys.readouterr()
    assert "SKIP SDK_TOKEN" in out.out
    _assert_no_leak(out.out + out.err)


def test_sdk_token_ignores_shell_github_token(
    fake_run: FakeRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "shell-gh-token")
    monkeypatch.setenv("GITHUB_TOKEN", "shell-github-token")
    seen: dict[str, Any] = {}

    def bind(name: str, *, env: dict[str, str] | None = None, **_k: Any) -> str | None:
        seen["env"] = env
        return CANARIES[name]

    monkeypatch.setattr(sas.cb, "bind", bind)
    monkeypatch.setattr(sas.cb, "reset_cache", lambda: None)
    assert sas.vault_pat("GITHUB_TOKEN") == CANARIES["GITHUB_TOKEN"]
    assert seen["env"] is not None
    assert "GH_TOKEN" not in seen["env"]
    assert "GITHUB_TOKEN" not in seen["env"]
    assert sas.pat_can_read(CANARIES["GITHUB_TOKEN"], "o/s")
    probe_env = fake_run.calls[-1]["env"]
    assert probe_env["GH_TOKEN"] == CANARIES["GITHUB_TOKEN"]
    assert "GITHUB_TOKEN" not in probe_env
