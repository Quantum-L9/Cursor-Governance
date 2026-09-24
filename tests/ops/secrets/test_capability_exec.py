"""capability_exec: a registered child gets the secret; nothing else ever does."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import capability_exec as cx  # noqa: E402

CANARY = "canary-3f9a1c-not-a-real-token"

# The child writes the NAMES of its environment (never values) and, for the
# "echo" entry, deliberately leaks the token to stdout and its output file.
CHILD = """#!/usr/bin/env python3
import json, os, sys
mode, out = sys.argv[1], sys.argv[2]
json.dump(sorted(os.environ), open(out + ".envnames", "w"))
if mode == "echo":
    print("token is " + os.environ.get("SEMGREP_APP_TOKEN", ""))
    open(out, "w").write(os.environ.get("SEMGREP_APP_TOKEN", ""))
else:
    print("scan ok")
    open(out, "w").write("{}")
"""


@pytest.fixture
def registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(cx, "CACHE_ROOT", cache)
    child = tmp_path / "child.py"
    child.write_text(CHILD)
    child.chmod(0o755)

    def entry(mode: str) -> dict:
        return {
            "secret": "SEMGREP_APP_TOKEN",
            "env": "SEMGREP_APP_TOKEN",
            "argv": [str(child), mode, "{output}"],
            "fixed_env": {"SEMGREP_REPO_NAME": "{repo}"},
            "params": {"output": "cache_path", "repo": "repo_slug"},
            "cwd": "cache_dir",
            "outputs": ["output"],
            "timeout_seconds": 30,
        }

    return {"quiet": entry("quiet"), "echo": entry("echo"), "_cache": cache}


def _plan(registry: dict, name: str) -> cx.Plan:
    cache = registry["_cache"]
    return cx.plan(name, {"output": str(cache / "out.sarif"), "repo": "o/r"}, str(cache), registry)


def test_real_registry_has_only_the_dry_run_semgrep_entry() -> None:
    reg = cx.load_registry()
    assert set(reg) == {"semgrep-pro"}
    assert "--dry-run" in reg["semgrep-pro"]["argv"]


def test_child_env_is_built_from_nothing_plus_the_one_secret(
    registry: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNRELATED_SECRET", "should-not-reach-the-child")
    result = cx.execute(_plan(registry, "quiet"), bind=lambda _n: CANARY)
    assert result.status == "ok"
    names = json.loads((registry["_cache"] / "out.sarif.envnames").read_text())
    assert set(names) - {"PWD", "SHLVL", "_", "LC_CTYPE"} == {
        "PATH",
        "HOME",
        "LANG",
        "SEMGREP_APP_TOKEN",
        "SEMGREP_REPO_NAME",
    }
    assert "SEMGREP_APP_TOKEN" not in os.environ
    assert CANARY not in result.stdout + result.stderr


def test_output_that_echoes_the_secret_is_withheld_everywhere(registry: dict) -> None:
    result = cx.execute(_plan(registry, "echo"), bind=lambda _n: CANARY)
    assert result.status == "withheld"
    assert CANARY not in result.stdout + result.stderr
    assert CANARY not in (registry["_cache"] / "out.sarif").read_text()


def test_unbound_secret_runs_nothing(registry: dict) -> None:
    result = cx.execute(_plan(registry, "quiet"), bind=lambda _n: None)
    assert result.status == "unbound"
    assert not (registry["_cache"] / "out.sarif").exists()


@pytest.mark.parametrize(
    "params, message",
    [
        ({"output": "/etc/passwd", "repo": "o/r"}, "under the ci-parity cache"),
        ({"output": "OUT", "repo": "o/r; rm -rf /"}, "owner/name"),
        ({"output": "OUT"}, "exactly"),
        ({"output": "OUT", "repo": "o/r", "extra": "--config=evil"}, "exactly"),
    ],
)
def test_requests_outside_the_entry_are_refused(registry: dict, params: dict, message: str) -> None:
    cache = registry["_cache"]
    params = {k: (str(cache / "o.sarif") if v == "OUT" else v) for k, v in params.items()}
    with pytest.raises(cx.ExecError, match=message):
        cx.plan("quiet", params, str(cache), registry)


def test_unknown_entry_is_refused(registry: dict) -> None:
    with pytest.raises(cx.ExecError):
        cx.plan("bash", {}, str(registry["_cache"]), registry)


def test_git_sha_validator() -> None:
    assert cx._validate("git_sha", "29c767df") == "29c767df"
    with pytest.raises(cx.ExecError):
        cx._validate("git_sha", "HEAD;id")


def test_cli_never_prints_the_secret(
    registry: dict, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cx, "load_registry", lambda: registry)
    monkeypatch.setattr(cx.cb, "bind", lambda _n: CANARY)
    cache = registry["_cache"]
    cx.main(
        [
            "run",
            "echo",
            "--cwd",
            str(cache),
            "--param",
            f"output={cache / 'x.sarif'}",
            "--param",
            "repo=o/r",
        ]
    )
    captured = capsys.readouterr()
    assert CANARY not in captured.out + captured.err
