"""Tests for the thin l9 dispatcher.

The dispatcher (environment/agents/adapters/claude-code/bin/l9) is a facade over
`make -C "$GOV" <target> WS="$PWD"`. It holds no build logic: it asks the
Makefile which targets are CONSUMER_SAFE and delegates. These tests shadow
`make` with a recorder so the exact delegated argv is asserted — including that
CURDIR is the Governance clone and WS is the consumer workspace, never confused.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
DISPATCHER = REPO / "environment" / "agents" / "adapters" / "claude-code" / "bin" / "l9"
INSTALLER = REPO / "ops" / "scripts" / "install_l9_dispatcher.sh"

SAFE_LIST = "start pr pr-check improve claude-env l4-status clean"


def _fake_make(bin_dir: Path, argv_out: Path, exit_code: int = 0) -> None:
    """A `make` stand-in: answers the allowlist query, records delegation argv."""
    script = bin_dir / "make"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'for a in "$@"; do\n'
        '  if [ "$a" = "l9-consumer-safe-list" ]; then\n'
        f"    echo {SAFE_LIST!r}\n"
        "    exit 0\n"
        "  fi\n"
        "done\n"
        f'printf "%s\\n" "$@" > "{argv_out}"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def _run(
    args: list[str],
    *,
    cwd: Path,
    gov: Path,
    bin_dir: Path,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "L9_GOV_ROOT": str(gov), "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    return subprocess.run(
        ["bash", str(DISPATCHER), *args],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture
def gov(tmp_path: Path) -> Path:
    g = tmp_path / "gov"
    g.mkdir()
    (g / "Makefile").write_text("# fake\n", encoding="utf-8")
    return g


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    b = tmp_path / "bin"
    b.mkdir()
    return b


def test_delegates_consumer_a_with_ws(tmp_path: Path, gov: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_a.txt"
    _fake_make(bin_dir, argv_out)
    consumer = tmp_path / "consumerA"
    consumer.mkdir()
    proc = _run(["pr"], cwd=consumer, gov=gov, bin_dir=bin_dir)
    assert proc.returncode == 0, proc.stderr
    argv = argv_out.read_text().splitlines()
    assert argv[:2] == ["-C", str(gov)]  # CURDIR is the Governance clone
    assert "pr" in argv
    assert f"WS={consumer}" in argv  # WS is the consumer workspace


def test_delegates_consumer_b_distinct_ws(tmp_path: Path, gov: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_b.txt"
    _fake_make(bin_dir, argv_out)
    consumer = tmp_path / "consumerB"
    consumer.mkdir()
    proc = _run(["claude-env"], cwd=consumer, gov=gov, bin_dir=bin_dir)
    assert proc.returncode == 0, proc.stderr
    argv = argv_out.read_text().splitlines()
    assert f"WS={consumer}" in argv
    assert f"WS={gov}" not in argv  # never confuses consumer WS with Governance


def test_no_path_confusion_ws_never_equals_gov(tmp_path: Path, gov: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_pc.txt"
    _fake_make(bin_dir, argv_out)
    # A consumer dir whose name resembles the governance clone must still be WS.
    consumer = tmp_path / "gov-lookalike"
    consumer.mkdir()
    proc = _run(["clean"], cwd=consumer, gov=gov, bin_dir=bin_dir)
    assert proc.returncode == 0, proc.stderr
    argv = argv_out.read_text().splitlines()
    ws = [a for a in argv if a.startswith("WS=")]
    assert ws == [f"WS={consumer}"]
    assert argv[argv.index("-C") + 1] == str(gov)


def test_forwards_make_vars_with_quoting(tmp_path: Path, gov: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_q.txt"
    _fake_make(bin_dir, argv_out)
    consumer = tmp_path / "c"
    consumer.mkdir()
    proc = _run(["improve", "CONTRACT_ID=a b c"], cwd=consumer, gov=gov, bin_dir=bin_dir)
    assert proc.returncode == 0, proc.stderr
    argv = argv_out.read_text().splitlines()
    assert "CONTRACT_ID=a b c" in argv  # single argv token, quoting preserved


def test_propagates_exit_code(tmp_path: Path, gov: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_e.txt"
    _fake_make(bin_dir, argv_out, exit_code=7)
    consumer = tmp_path / "c"
    consumer.mkdir()
    proc = _run(["pr"], cwd=consumer, gov=gov, bin_dir=bin_dir)
    assert proc.returncode == 7


def test_rejects_governance_only_target(tmp_path: Path, gov: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_r.txt"
    _fake_make(bin_dir, argv_out)
    consumer = tmp_path / "c"
    consumer.mkdir()
    proc = _run(["backup"], cwd=consumer, gov=gov, bin_dir=bin_dir)
    assert proc.returncode == 2
    assert not argv_out.exists()  # never delegated
    assert "not a CONSUMER_SAFE target" in proc.stderr


def test_fail_closed_when_governance_missing(tmp_path: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_m.txt"
    _fake_make(bin_dir, argv_out)
    proc = _run(["pr"], cwd=tmp_path, gov=tmp_path / "nope", bin_dir=bin_dir)
    assert proc.returncode == 3
    assert not argv_out.exists()


def test_list_prints_allowlist(tmp_path: Path, gov: Path, bin_dir: Path) -> None:
    argv_out = tmp_path / "argv_l.txt"
    _fake_make(bin_dir, argv_out)
    proc = _run(["--list"], cwd=tmp_path, gov=gov, bin_dir=bin_dir)
    assert proc.returncode == 0
    assert "pr" in proc.stdout.split()


def test_installer_installs_and_checks(tmp_path: Path) -> None:
    dest = tmp_path / "bin" / "l9"
    env = {**os.environ, "L9_DISPATCHER_DEST": str(dest), "L9_GOV_ROOT": str(REPO)}
    inst = subprocess.run(
        ["bash", str(INSTALLER)], env=env, text=True, capture_output=True, check=False
    )
    assert inst.returncode == 0, inst.stderr
    assert dest.is_file()
    assert os.access(dest, os.X_OK)
    assert dest.read_text() == DISPATCHER.read_text()  # exact source, no second copy drift
    chk = subprocess.run(
        ["bash", str(INSTALLER), "--check"], env=env, text=True, capture_output=True, check=False
    )
    assert chk.returncode == 0, chk.stderr
    assert "OK" in chk.stdout


def test_makefile_owns_classification_no_second_registry() -> None:
    # The allowlist lives in the Makefile (single authority). The dispatcher must
    # not embed its own target list.
    mk = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "L9_CONSUMER_SAFE_TARGETS" in mk
    assert "l9-consumer-safe-list" in mk
    disp = DISPATCHER.read_text(encoding="utf-8")
    assert "l9-consumer-safe-list" in disp  # queries the Makefile
    # Dispatcher must not hardcode the full allowlist as its own registry.
    assert "L9_CONSUMER_SAFE_TARGETS :=" not in disp
