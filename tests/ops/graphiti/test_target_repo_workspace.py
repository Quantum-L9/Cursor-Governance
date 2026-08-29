"""CI-014 / IMP-06: the Graphiti client takes its target repository explicitly.

A `group_id` IS repository identity. Resolving it from the process cwd made every
command's correctness depend on which directory a shell happened to be in — and
a hook, a subshell, or a `cd` inside a compound command all change that without
the caller noticing. These tests pin the contract: `--workspace` names the
target, cwd remains the default, and the flag reaches every subcommand that
resolves a group.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "ops" / "graphiti" / "graphiti_memory_client.py"


def _load():
    sys.path.insert(0, str(CLIENT.parent))
    spec = importlib.util.spec_from_file_location("graphiti_memory_client", CLIENT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


client = _load()


def test_workspace_flag_overrides_cwd(tmp_path: Path) -> None:
    args = argparse.Namespace(workspace=str(tmp_path))
    assert client.target_repo(args) == tmp_path.resolve()


def test_absent_workspace_falls_back_to_cwd() -> None:
    """Default behaviour is unchanged — this is additive, not a migration."""
    assert client.target_repo(argparse.Namespace()) == Path.cwd()
    assert client.target_repo(argparse.Namespace(workspace=None)) == Path.cwd()


def test_workspace_expands_user_and_resolves(tmp_path: Path) -> None:
    nested = tmp_path / "a" / ".." / "a"
    (tmp_path / "a").mkdir()
    assert client.target_repo(argparse.Namespace(workspace=str(nested))) == (tmp_path / "a")


@pytest.mark.parametrize(
    "cmd",
    ["health", "resolve", "search", "write", "inject", "bootstrap", "stats", "conflicts"],
)
def test_every_subcommand_accepts_workspace(cmd: str) -> None:
    """The flag is useless if it reaches only the commands someone remembered."""
    proc = subprocess.run(
        [sys.executable, str(CLIENT), cmd, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--workspace" in proc.stdout, f"{cmd} cannot be retargeted"


def test_no_command_body_resolves_identity_from_cwd() -> None:
    """The regression guard: a new command must not reintroduce a cwd read.

    `target_repo` itself and the `root or Path.cwd()` default are the only two
    legitimate uses; anything else is a command deciding repository identity
    from wherever the shell happened to be.
    """
    text = CLIENT.read_text(encoding="utf-8")
    offenders = [
        line.strip()
        for line in text.splitlines()
        if "Path.cwd()" in line
        and "return Path.cwd()" not in line
        and "root or Path.cwd()" not in line
    ]
    assert not offenders, f"resolve these through target_repo(args): {offenders}"
