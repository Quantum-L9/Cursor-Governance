"""Declared expect-fail fixtures (ops/ci_parity/fixtures.py).

The four required outcomes run end to end through ``run.mode_gate`` with a
stand-in scanner (the same pattern as test_run.py): a named rule that fires
passes, a named rule that does not fire fails, an unnamed finding on a fixture
path blocks, and a finding outside every declared root blocks. Bandit's path
through the same manifest is exercised with the CLI the security gate calls.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import fixtures  # noqa: E402
import manifest  # noqa: E402
import run  # noqa: E402

SLUG = "Example-Org/Consumer.Repo"
ROOT = "fixtures/canary/"
BAD = f"{ROOT}known_bad.sh"

# Stand-in scanner: every line containing a marker WORD reports rule WORD as an
# error, so a test chooses exactly which rules fire on which lines.
FAKE_SCANNER = """#!/usr/bin/env python3
import json, sys
comments = []
for path in [a for a in sys.argv[1:] if not a.startswith("-")]:
    for n, line in enumerate(open(path), 1):
        for word in line.split():
            if word.startswith("SC"):
                comments.append({"file": path, "line": n, "level": "error",
                                 "code": int(word[2:]), "message": "fixture"})
print(json.dumps({"comments": comments}))
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _manifest(files: dict[str, dict[str, list[str]]], roots: list[str] | None = None) -> dict:
    return {
        "schema": fixtures.SCHEMA,
        "repositories": {SLUG: {"roots": roots or [ROOT], "files": files}},
    }


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    fake = tmp_path / "fake-shellcheck"
    fake.write_text(FAKE_SCANNER)
    fake.chmod(0o755)
    (tmp_path / "inst").mkdir()
    (tmp_path / "inst" / "state.json").write_text(
        json.dumps({"shellcheck": {"version": "1", "path": str(fake)}})
    )
    yml = tmp_path / "tools.yaml"
    yml.write_text(
        "schema: l9.ci-parity.tools.v1\n"
        f"install_root: {tmp_path / 'inst'}\n"
        f"bin_dir: {tmp_path / 'bin'}\n"
        f"cache_root: {tmp_path / 'cache'}\n"
        "tools:\n  shellcheck:\n    version: '1'\n    method: release_binary\n"
        "    url: https://example.invalid/sc\n    sha256: '" + "0" * 64 + "'\n"
        "    binary: shellcheck\n    version_cmd: [--version]\n    expect: '1'\n"
        "lanes:\n  shellcheck:\n    tool: shellcheck\n    tier: fast\n    globs: ['*.sh']\n"
        "    block: [error]\n    weight: 1\n"
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "remote", "add", "origin", f"https://github.com/{SLUG}.git")
    (repo / "README").write_text("base\n")
    _git(repo, "add", "README")
    _git(repo, "commit", "-q", "-m", "base")
    path = tmp_path / "expect_fail_fixtures.json"
    monkeypatch.setattr(fixtures, "MANIFEST", path)
    return {
        "loaded": manifest.load(yml),
        "repo": repo,
        "base": _git(repo, "rev-parse", "HEAD"),
        "manifest": path,
    }


def _commit(world: dict, files: dict[str, str]) -> None:
    repo = world["repo"]
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
        _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", "change")


def _gate(world: dict, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run.mode_gate(world["loaded"], world["repo"], "HEAD", world["base"])
    return code, capsys.readouterr().out


def test_a_named_rule_that_fires_passes_and_is_reported(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    world["manifest"].write_text(json.dumps(_manifest({BAD: {"shellcheck": ["SC2086"]}})))
    _commit(world, {BAD: "echo SC2086\n"})
    code, out = _gate(world, capsys)
    assert code == 0, out
    assert "blocking=0" in out and "expected=1" in out
    assert f"expect {BAD}:1: [error] SC2086" in out


def test_a_named_rule_that_does_not_fire_fails(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    world["manifest"].write_text(json.dumps(_manifest({BAD: {"shellcheck": ["SC2086"]}})))
    _commit(world, {BAD: "echo nothing here\n"})
    code, out = _gate(world, capsys)
    assert code == 2, out
    assert f"BLOCK {BAD}:1: [error] {fixtures.MISSING_RULE}" in out
    assert "SC2086 did not fire" in out


def test_an_unnamed_finding_on_a_fixture_path_blocks(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    world["manifest"].write_text(json.dumps(_manifest({BAD: {"shellcheck": ["SC2086"]}})))
    _commit(world, {BAD: "echo SC2086\necho SC1000\n"})
    code, out = _gate(world, capsys)
    assert code == 2, out
    assert f"BLOCK {BAD}:2: [error] SC1000" in out
    assert f"expect {BAD}:1: [error] SC2086" in out


def test_a_fixture_file_with_no_entry_under_a_root_blocks_any_finding(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    world["manifest"].write_text(json.dumps(_manifest({BAD: {"shellcheck": ["SC2086"]}})))
    _commit(world, {BAD: "echo SC2086\n", f"{ROOT}good.sh": "echo SC2086\n"})
    code, out = _gate(world, capsys)
    assert code == 2, out
    assert f"BLOCK {ROOT}good.sh:1: [error] SC2086" in out


def test_a_path_outside_every_declared_root_blocks_as_before(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    world["manifest"].write_text(json.dumps(_manifest({BAD: {"shellcheck": ["SC2086"]}})))
    _commit(world, {BAD: "echo SC2086\n", "src/real.sh": "echo SC2086\n"})
    code, out = _gate(world, capsys)
    assert code == 2, out
    assert "BLOCK src/real.sh:1: [error] SC2086" in out


def test_another_repository_gets_no_exemption(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    other = _manifest({BAD: {"shellcheck": ["SC2086"]}})
    other["repositories"] = {"Other-Org/Other": other["repositories"][SLUG]}
    world["manifest"].write_text(json.dumps(other))
    _commit(world, {BAD: "echo SC2086\n"})
    code, out = _gate(world, capsys)
    assert code == 2, out
    assert f"BLOCK {BAD}:1: [error] SC2086" in out


def test_a_malformed_manifest_blocks_instead_of_exempting(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    world["manifest"].write_text(json.dumps({"schema": "wrong", "repositories": {}}))
    _commit(world, {BAD: "echo SC2086\n"})
    code, out = _gate(world, capsys)
    assert code == 2, out
    assert "ci-parity/fixture-manifest-invalid" in out


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"schema": "x", "repositories": {}}, "schema"),
        (_manifest({}, roots=["/abs/"]), "repository-relative"),
        (_manifest({}, roots=["no-slash"]), "ending in /"),
        (_manifest({}, roots=["a/../b/"]), "repository-relative"),
        (_manifest({"elsewhere/x.py": {"bandit": ["B602"]}}), "outside every declared root"),
        (_manifest({BAD: {"bandit": []}}), "non-empty list"),
        (_manifest({BAD: {}}), "names no lane"),
    ],
)
def test_manifest_validation_fails_closed(data: dict, message: str) -> None:
    with pytest.raises(fixtures.FixtureManifestError, match=message):
        fixtures.parse(data)


def test_the_committed_manifest_parses() -> None:
    registry = fixtures.load(PKG / "expect_fail_fixtures.json")
    eie = registry.for_repo("quantum-l9/enrichment.inference.engine")
    assert eie is not None
    assert eie.covers("contracts/feature_evidence/fixtures/ci_canary/central_rule_bad.py")
    assert not eie.covers("app/main.py")
    ceg = registry.for_repo("quantum-l9/cognitive.engine.graphs")
    assert ceg is not None
    assert ceg.covers("tests/canary/central_rule_witness.py")
    assert not ceg.covers("engine/handlers.py")


def test_manifest_bytes_change_the_runner_digest(world: dict) -> None:
    world["manifest"].write_text(json.dumps(_manifest({BAD: {"shellcheck": ["SC2086"]}})))
    before = run._runner_digest()
    world["manifest"].write_text(json.dumps(_manifest({BAD: {"shellcheck": ["SC1000"]}})))
    assert run._runner_digest() != before


# --- Bandit, through the CLI ops/scripts/run_pr_security.sh calls ------------


def _bandit_cli(world: dict, report: dict, scanned: list[str]) -> subprocess.CompletedProcess:
    path = world["repo"] / "bandit.json"
    path.write_text(json.dumps(report))
    return subprocess.run(
        [
            sys.executable,
            str(PKG / "fixtures.py"),
            "--manifest",
            str(world["manifest"]),
            "bandit",
            "--repo",
            str(world["repo"]),
            "--report",
            str(path),
            *scanned,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _result(world: dict, rel: str, test_id: str, line: int = 1) -> dict:
    return {
        "filename": str(world["repo"] / rel),
        "test_id": test_id,
        "line_number": line,
        "issue_severity": "HIGH",
    }


def test_bandit_named_rule_fires_passes(world: dict) -> None:
    world["manifest"].write_text(json.dumps(_manifest({f"{ROOT}bad.py": {"bandit": ["B602"]}})))
    proc = _bandit_cli(
        world, {"results": [_result(world, f"{ROOT}bad.py", "B602")]}, [f"{ROOT}bad.py"]
    )
    assert proc.returncode == 0, proc.stdout
    assert f"EXPECTED: {ROOT}bad.py:1: B602" in proc.stdout


def test_bandit_named_rule_missing_fails(world: dict) -> None:
    world["manifest"].write_text(json.dumps(_manifest({f"{ROOT}bad.py": {"bandit": ["B602"]}})))
    proc = _bandit_cli(world, {"results": []}, [f"{ROOT}bad.py"])
    assert proc.returncode == 1
    assert f"{fixtures.MISSING_RULE}: declared B602 did not fire" in proc.stdout


def test_bandit_unnamed_finding_on_fixture_blocks(world: dict) -> None:
    world["manifest"].write_text(json.dumps(_manifest({f"{ROOT}bad.py": {"bandit": ["B602"]}})))
    proc = _bandit_cli(
        world,
        {
            "results": [
                _result(world, f"{ROOT}bad.py", "B602"),
                _result(world, f"{ROOT}bad.py", "B307", 2),
            ]
        },
        [f"{ROOT}bad.py"],
    )
    assert proc.returncode == 1
    assert f"BLOCK: {ROOT}bad.py:2: B307" in proc.stdout


def test_split_returns_only_paths_under_a_declared_root(world: dict) -> None:
    world["manifest"].write_text(json.dumps(_manifest({f"{ROOT}bad.py": {"bandit": ["B602"]}})))
    proc = subprocess.run(
        [
            sys.executable,
            str(PKG / "fixtures.py"),
            "--manifest",
            str(world["manifest"]),
            "split",
            "--repo",
            str(world["repo"]),
            f"{ROOT}bad.py",
            "src/app.py",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.split() == [f"{ROOT}bad.py"]


# --- Bandit, end to end through ops/scripts/run_pr_security.sh ---------------

SECURITY_GATE = REPO_ROOT / "ops" / "scripts" / "run_pr_security.sh"
EIE = "Quantum-L9/Enrichment.Inference.Engine"
EIE_BAD = "contracts/feature_evidence/fixtures/ci_canary/central_rule_bad.py"

# Stand-in for `uvx --from bandit==X bandit FILES... [-f json -o OUT]`: every
# file containing shell=True yields a B602; exit 1 when anything was found.
FAKE_UVX = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
out = args[args.index("-o") + 1] if "-o" in args else None
results = []
for arg in args:
    if os.path.isfile(arg) and arg != out:
        for n, line in enumerate(open(arg), 1):
            if "shell=True" in line:
                results.append({"filename": arg, "test_id": "B602", "line_number": n,
                                "issue_severity": "HIGH"})
if out:
    json.dump({"results": results}, open(out, "w"))
else:
    for r in results:
        print(f">> Issue: [B602] {r['filename']}:{r['line_number']}")
sys.exit(1 if results else 0)
"""


def _security_gate(tmp_path: Path, files: dict[str, str]) -> str:
    stub = tmp_path / "stub-bin"
    stub.mkdir()
    (stub / "uvx").write_text(FAKE_UVX)
    (stub / "uvx").chmod(0o755)
    repo = tmp_path / "consumer"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "remote", "add", "origin", f"https://github.com/{EIE}.git")
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    listed = tmp_path / "changed.txt"
    listed.write_text("".join(f"{rel}\n" for rel in files))
    proc = subprocess.run(
        ["bash", str(SECURITY_GATE), "--mode", "advisory", str(repo)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{stub}:/usr/bin:/bin",
            "HOME": str(tmp_path),
            "WS": str(repo),
            "PR_CHANGED_FILE": str(listed),
            "PR_SECURITY_ADVISORY": "1",
        },
    )
    return proc.stdout + proc.stderr


SHELL_TRUE = 'import subprocess\nsubprocess.run("ls", shell=True, check=False)\n'


def test_security_gate_bandit_passes_a_declared_fixture_without_nosec(tmp_path: Path) -> None:
    out = _security_gate(tmp_path, {EIE_BAD: SHELL_TRUE})
    assert f"EXPECTED: {EIE_BAD}:2: B602" in out, out
    assert "PASS: bandit==" in out and "declared expect-fail fixtures" in out, out
    assert "FAIL: bandit" not in out, out


def test_security_gate_bandit_still_blocks_outside_the_fixture_roots(tmp_path: Path) -> None:
    out = _security_gate(tmp_path, {EIE_BAD: SHELL_TRUE, "app/real.py": SHELL_TRUE})
    assert "FAIL: bandit reported issues in changed Python files" in out, out
    assert f"EXPECTED: {EIE_BAD}:2: B602" in out, out


def test_security_gate_bandit_fails_when_a_declared_rule_does_not_fire(tmp_path: Path) -> None:
    out = _security_gate(tmp_path, {EIE_BAD: "import subprocess\n"})
    assert f"{fixtures.MISSING_RULE}: declared B602 did not fire" in out, out
    assert "FAIL: bandit: declared expect-fail fixtures" in out, out


def test_security_gate_needs_no_bash4_builtin_for_the_fixture_split() -> None:
    """macOS ships Bash 3.2: no mapfile/readarray. Under `set +e` a missing
    builtin would leave the fixture list empty and block declared fixtures."""
    import re

    text = SECURITY_GATE.read_text(encoding="utf-8")
    assert not re.search(r"^\s*[^#\n]*\b(mapfile|readarray)\s+-", text, re.M)
