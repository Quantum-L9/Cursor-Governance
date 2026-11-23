"""cto_integrate.py: integration candidate build, check run, receipt, and check gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import cto_integrate  # noqa: E402

SCRIPT = REPO / "ops" / "autonomy" / "cto_integrate.py"
PY = sys.executable


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, files: dict[str, str], msg: str) -> str:
    for rel, text in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        _git(repo, "add", "--", rel)
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture(autouse=True)
def _isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate from the host's git config; tests that need a merge driver add one."""
    cfg = tmp_path / "gitconfig"
    cfg.write_text(
        "[user]\n\tname = test\n\temail = test@example.invalid\n"
        "[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(cfg))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return cfg


class Harness:
    """An origin repository with PR heads published as refs/pull/<n>/head."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.origin = root / "origin"
        self.origin.mkdir()
        _git(self.origin, "init", "-q", "-b", "main")
        self.base = _commit(
            self.origin,
            {
                "a.txt": "a\n",
                "shared.txt": "one\ntwo\nthree\n",
                "mod/__manifest__.py": "{'name': 'mod', 'version': '19.0.1.0.0'}\n",
            },
            "base",
        )
        self.workspace = root / "ws"
        self.workspace.mkdir()
        self.workdir = root / "clones" / "repo"
        self.lock_dir = root / "locks"

    def pr(self, number: int, files: dict[str, str]) -> str:
        _git(self.origin, "checkout", "-q", "-B", f"pr{number}", self.base)
        sha = _commit(self.origin, files, f"pr {number}")
        _git(self.origin, "update-ref", f"refs/pull/{number}/head", sha)
        _git(self.origin, "checkout", "-q", "main")
        return sha

    def train(self, numbers: list[int], **overrides: Any) -> Path:
        doc: dict[str, Any] = {
            "schema": "l9.cto-train/v1",
            "campaign": "camp",
            "repo": "acme/widget",
            "base": "main",
            "prs": [{"number": n, "lane": f"L{n}", "proven_head": None} for n in numbers],
            "order": numbers,
            "pairs": [],
            "integration_receipt": None,
            "runtime": None,
            "static": [[PY, "-c", "pass"]],
            "suite": [[PY, "-c", "print('3 passed, 1 skipped in 0.1s')"]],
        }
        doc.update(overrides)
        path = self.workspace / ".l9" / "cto-mode" / "train.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def build(self, *extra: str, workdir: Path | None = None) -> tuple[int, dict[str, Any]]:
        return self.cli(
            "build",
            "--workspace",
            str(self.workspace),
            "--remote",
            str(self.origin),
            "--workdir",
            str(workdir or self.workdir),
            *extra,
        )

    def run(self, candidate: str, *extra: str) -> tuple[int, dict[str, Any]]:
        return self.cli(
            "run",
            "--candidate",
            candidate,
            "--workspace",
            str(self.workspace),
            "--lock-dir",
            str(self.lock_dir),
            *extra,
        )

    @staticmethod
    def cli(*argv: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run([PY, str(SCRIPT), *argv], capture_output=True, text=True)
        assert proc.stdout, proc.stderr
        return proc.returncode, json.loads(proc.stdout)

    def receipt(self, candidate: str) -> dict[str, Any]:
        path = self.workspace / ".l9/cto-mode/integration" / f"{candidate}.json"
        return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


def test_clean_merge_builds_runs_and_passes(h: Harness) -> None:
    s1 = h.pr(1, {"one.txt": "1\n"})
    s2 = h.pr(2, {"two.txt": "2\n"})
    h.train([1, 2])
    rc, out = h.build("--candidate", "c1")
    assert rc == 0, out
    assert out["status"] == "built"
    assert out["grants_permission"] is False
    assert out["heads"] == {"1": s1, "2": s2}
    assert out["drivers"]["l9-versions"] == "absent"  # lane B not landed: recorded, tolerated
    assert out["resolutions"] == []
    clone = Path(out["clone"])
    assert (clone / "one.txt").is_file() and (clone / "two.txt").is_file()
    assert _git(clone, "rev-parse", "HEAD^{tree}") == out["tree_sha"]

    rc, rep = h.run("c1")
    assert rc == 0, rep
    assert rep["verdict"] == "pass" and rep["grants_permission"] is False
    receipt = h.receipt("c1")
    assert cto_integrate.validate_receipt(receipt) == []
    assert receipt["schema"] == "l9.cto-integration-receipt/v1"
    assert receipt["base_sha"] == h.base
    assert receipt["results"]["suite"] == {"ok": True, "passed": 3, "failed": 0, "skipped": 1}
    assert receipt["results"]["static"]["ok"] is True
    assert receipt["results"]["runtime"] is None

    receipt_path = str(h.workspace / ".l9/cto-mode/integration/c1.json")
    rc, chk = h.cli("check", "--receipt", receipt_path, "--heads", f"1={s1},2={s2}")
    assert rc == 0 and chk["ok"] is True, chk


def test_workdir_inside_workspace_is_refused(h: Harness) -> None:
    h.pr(1, {"one.txt": "1\n"})
    h.train([1])
    rc, out = h.build(workdir=h.workspace / "clone")
    assert rc == 2
    assert "overlaps the workspace" in out["error"]


def test_foreign_directory_is_never_reused(h: Harness) -> None:
    h.pr(1, {"one.txt": "1\n"})
    h.train([1])
    h.workdir.mkdir(parents=True)
    (h.workdir / "precious.txt").write_text("mine\n", encoding="utf-8")
    rc, out = h.build()
    assert rc == 2 and "not created by cto_integrate.py" in out["error"]
    assert (h.workdir / "precious.txt").read_text(encoding="utf-8") == "mine\n"


def test_mechanical_resolution_is_recorded_with_its_kind(
    h: Harness, _isolated_git: Path, tmp_path: Path
) -> None:
    # Stand-in for lane B's driver: take the higher-version side ("theirs" here).
    driver = tmp_path / "fake_driver.py"
    driver.write_text(
        "import shutil, sys\nshutil.copyfile(sys.argv[3], sys.argv[2])\n", encoding="utf-8"
    )
    with _isolated_git.open("a", encoding="utf-8") as fh:
        fh.write(f'[merge "l9-versions"]\n\tdriver = {PY} {driver} %O %A %B %P\n')
    attrs = {".gitattributes": "__manifest__.py merge=l9-versions\n"}
    _git(h.origin, "checkout", "-q", "main")
    h.base = _commit(h.origin, attrs, "attributes")
    h.pr(1, {"mod/__manifest__.py": "{'name': 'mod', 'version': '19.0.1.1.0'}\n"})
    h.pr(2, {"mod/__manifest__.py": "{'name': 'mod', 'version': '19.0.1.2.0'}\n"})
    h.train([1, 2])
    rc, out = h.build("--candidate", "mech")
    assert rc == 0, out
    assert out["drivers"]["l9-versions"] == "registered"
    assert [(r["pr"], r["path"], r["kind"]) for r in out["resolutions"]] == [
        (2, "mod/__manifest__.py", "version")
    ]
    assert "l9-versions" in out["resolutions"][0]["detail"]
    rc, _ = h.run("mech")
    assert rc == 0
    assert h.receipt("mech")["resolutions"][0]["kind"] == "version"


def test_manual_conflict_stops_then_reviewed_resolution_applies(h: Harness, tmp_path: Path) -> None:
    h.pr(1, {"shared.txt": "one\nTWO-A\nthree\n"})
    h.pr(2, {"shared.txt": "one\nTWO-B\nthree\n"})
    h.train([1, 2])
    rc, out = h.build("--candidate", "conf")
    assert rc == 3, out
    assert out["status"] == "stopped" and out["reason"] == "conflict"
    assert out["pr"] == 2
    (conflict,) = out["conflicts"]
    assert conflict["path"] == "shared.txt"
    assert "TWO-A" in conflict["ours"] and "TWO-B" in conflict["theirs"]
    assert "two" in conflict["base"]
    assert "--resolution 2:shared.txt:<file>" in out["next"]
    rc, rep = h.run("conf")
    assert rc == 2 and "stopped" in rep["error"]  # a stopped build never yields a receipt

    resolved = tmp_path / "shared.resolved"
    resolved.write_text("one\nTWO-A+B\nthree\n", encoding="utf-8")
    rc, out = h.build("--candidate", "conf", "--resolution", f"2:shared.txt:{resolved}")
    assert rc == 0, out
    (res,) = out["resolutions"]
    assert (res["pr"], res["path"], res["kind"]) == (2, "shared.txt", "manual")
    assert (Path(out["clone"]) / "shared.txt").read_text(
        encoding="utf-8"
    ) == "one\nTWO-A+B\nthree\n"


def test_failing_suite_gives_verdict_fail(h: Harness) -> None:
    s1 = h.pr(1, {"one.txt": "1\n"})
    h.train(
        [1],
        suite=[[PY, "-c", "import sys; print('2 failed, 5 passed in 1s'); sys.exit(1)"]],
    )
    rc, out = h.build("--candidate", "bad")
    assert rc == 0
    rc, rep = h.run("bad")
    assert rc == 1
    assert rep["verdict"] == "fail" and "suite_failed" in rep["reasons"]
    receipt = h.receipt("bad")
    assert receipt["results"]["suite"] == {"ok": False, "passed": 5, "failed": 2, "skipped": 0}
    path = str(h.workspace / ".l9/cto-mode/integration/bad.json")
    rc, chk = h.cli("check", "--receipt", path, "--heads", f"1={s1}")
    assert rc == 1 and "verdict is fail" in chk["reasons"]


def test_unparseable_suite_counts_stay_unknown(h: Harness) -> None:
    h.pr(1, {"one.txt": "1\n"})
    h.train([1], suite=[[PY, "-c", "print('all good')"]])
    h.build("--candidate", "nocount")
    rc, _ = h.run("nocount")
    assert rc == 0
    suite = h.receipt("nocount")["results"]["suite"]
    assert suite == {"ok": True, "passed": None, "failed": None, "skipped": None}


def test_suite_timeout_fails(h: Harness) -> None:
    h.pr(1, {"one.txt": "1\n"})
    h.train([1], static=[[PY, "-c", "import time; time.sleep(30)"]])
    h.build("--candidate", "slow")
    rc, rep = h.run("slow", "--timeout", "1")
    assert rc == 1
    receipt = h.receipt("slow")
    assert receipt["results"]["static"]["ok"] is False
    assert "timeout" in receipt["results"]["static"]["detail"]


def test_check_rejects_heads_mismatch(h: Harness) -> None:
    s1 = h.pr(1, {"one.txt": "1\n"})
    s2 = h.pr(2, {"two.txt": "2\n"})
    h.train([1, 2])
    h.build("--candidate", "m")
    assert h.run("m")[0] == 0
    path = str(h.workspace / ".l9/cto-mode/integration/m.json")
    other = "f" * 40
    rc, chk = h.cli("check", "--receipt", path, "--heads", f"1={s1},2={other}")
    assert rc == 1 and any("PR 2: receipt head" in r for r in chk["reasons"])
    rc, chk = h.cli("check", "--receipt", path, "--heads", f"1={s1}")
    assert rc == 1 and any("not asked for" in r for r in chk["reasons"])
    rc, chk = h.cli("check", "--receipt", path, "--heads", f"1={s1},2={s2},3={other}")
    assert rc == 1 and any("PR 3 is not in the receipt" in r for r in chk["reasons"])
    rc, chk = h.cli("check", "--receipt", path, "--heads", f"1={s1},2={s2}")
    assert rc == 0, chk


def test_check_rejects_a_receipt_that_fails_its_schema(h: Harness, tmp_path: Path) -> None:
    bogus = tmp_path / "r.json"
    bogus.write_text(json.dumps({"schema": "l9.cto-integration-receipt/v1"}), encoding="utf-8")
    rc, chk = h.cli("check", "--receipt", str(bogus), "--heads", f"1={'a' * 40}")
    assert rc == 1 and chk["reasons"] and chk["reasons"][0].startswith("schema:")


def test_pass_verdict_with_failed_check_is_schema_invalid() -> None:
    doc = {
        "schema": "l9.cto-integration-receipt/v1",
        "campaign": "c",
        "repo": "a/b",
        "base_ref": "main",
        "base_sha": "a" * 40,
        "candidate": "x",
        "heads": {"1": "b" * 40},
        "tree_sha": "c" * 40,
        "resolutions": [],
        "results": {
            "static": {"ok": True, "detail": ""},
            "suite": {"ok": False, "passed": 0, "failed": 1, "skipped": 0},
            "runtime": None,
        },
        "verdict": "pass",
        "created_at": "2026-11-23T00:00:00Z",
    }
    assert cto_integrate.validate_receipt(doc)
    doc["verdict"] = "fail"
    assert cto_integrate.validate_receipt(doc) == []


def test_proven_head_mismatch_stops_the_build(h: Harness) -> None:
    h.pr(1, {"one.txt": "1\n"})
    path = h.train([1])
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["prs"][0]["proven_head"] = "e" * 40
    path.write_text(json.dumps(doc), encoding="utf-8")
    rc, out = h.build("--candidate", "moved")
    assert rc == 3 and out["reason"] == "head_moved"


def _runtime_script(tmp_path: Path, body: str) -> list[str]:
    script = tmp_path / "runtime.py"
    script.write_text(body, encoding="utf-8")
    return [PY, str(script)]


def test_runtime_env_and_odoo_counts(h: Harness, tmp_path: Path) -> None:
    h.pr(1, {"one.txt": "1\n"})
    cmd = _runtime_script(
        tmp_path,
        "import os, sys\n"
        "assert os.environ['ODOO_ENTERPRISE_PATH'] == '/ent'\n"
        "print('0 failed, 1 error(s) of 40 tests when loading database')\n"
        "sys.exit(1)\n",
    )
    h.train([1], runtime={"command": cmd, "env": {"ODOO_ENTERPRISE_PATH": "/ent"}, "timeout_s": 60})
    h.build("--candidate", "rt")
    rc, rep = h.run("rt")
    assert rc == 1
    assert h.receipt("rt")["results"]["runtime"] == {
        "ok": False,
        "run": 40,
        "failed": 0,
        "errors": 1,
    }
    assert "runtime_failed" in rep["reasons"]


def test_fixture_inputs_changed_is_reported_and_rebuild_needs_consent(
    h: Harness, tmp_path: Path
) -> None:
    h.pr(1, {"one.txt": "1\n"})
    marker = tmp_path / "rebuilt"
    cmd = _runtime_script(
        tmp_path,
        "import pathlib, sys\n"
        f"if not pathlib.Path({str(marker)!r}).exists():\n"
        "    print('fixture is incompatible with the current inputs: image changed')\n"
        "    sys.exit(1)\n"
        "print('0 failed, 0 error(s) of 12 tests')\n",
    )
    h.train([1], runtime={"command": cmd, "env": {}, "timeout_s": 60})
    h.build("--candidate", "fx")
    rebuild = f'{PY} -c "import pathlib; pathlib.Path({str(marker)!r}).touch()"'

    rc, rep = h.run("fx", "--rebuild-command", rebuild)
    assert rc == 1
    assert rep["reasons"] == ["fixture_inputs_changed"]
    assert rep["runtime"]["rebuild_command"]
    assert not marker.exists()  # never rebuilt without --allow-rebuild

    rc, rep = h.run("fx")
    assert rc == 1 and rep["runtime"]["rebuild_command"] is None
    assert rep["runtime"]["rebuild_hint"].startswith("UNKNOWN")

    rc, rep = h.run("fx", "--rebuild-command", rebuild, "--allow-rebuild")
    assert rc == 0, rep
    assert marker.exists()
    assert h.receipt("fx")["results"]["runtime"] == {
        "ok": True,
        "run": 12,
        "failed": 0,
        "errors": 0,
    }


def test_fixture_lock_excludes_concurrent_runs(h: Harness, tmp_path: Path) -> None:
    """Two processes on two candidates sharing one fixture never overlap at runtime."""
    h.pr(1, {"one.txt": "1\n"})
    log = tmp_path / "runtime.log"
    cmd = _runtime_script(
        tmp_path,
        "import os, sys, time\n"
        f"log = {str(log)!r}\n"
        "def note(tag):\n"
        "    with open(log, 'a') as fh:\n"
        "        fh.write(f'{tag} {time.monotonic()}\\n')\n"
        "note('start')\n"
        "time.sleep(1.5)\n"
        "note('end')\n"
        "print('0 failed, 0 error(s) of 1 tests')\n",
    )
    h.train([1], runtime={"command": cmd, "env": {}, "timeout_s": 60})
    assert h.build("--candidate", "pa", workdir=tmp_path / "clones" / "a")[0] == 0
    assert h.build("--candidate", "pb", workdir=tmp_path / "clones" / "b")[0] == 0
    procs = [
        subprocess.Popen(
            [
                PY,
                str(SCRIPT),
                "run",
                "--candidate",
                name,
                "--workspace",
                str(h.workspace),
                "--lock-dir",
                str(h.lock_dir),
                "--fixture",
                "shared-fixture",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for name in ("pa", "pb")
    ]
    assert [p.wait(timeout=120) for p in procs] == [0, 0]
    events = [line.split() for line in log.read_text(encoding="utf-8").splitlines()]
    assert [e[0] for e in events] == ["start", "end", "start", "end"]
    assert float(events[1][1]) <= float(events[2][1])


def test_busy_fixture_fails_without_waiting(h: Harness) -> None:
    h.pr(1, {"one.txt": "1\n"})
    h.train([1], runtime={"command": [PY, "-c", "print(1)"], "env": {}, "timeout_s": 60})
    h.build("--candidate", "busy")
    holder = subprocess.Popen(
        [
            PY,
            "-c",
            "import sys, time; sys.path.insert(0, sys.argv[1]); import cto_integrate as c\n"
            "from pathlib import Path\n"
            "with c.exclusive_lock(Path(sys.argv[2]), 0) as got:\n"
            "    print('held' if got else 'missed', flush=True); time.sleep(30)\n",
            str(REPO / "ops" / "autonomy"),
            str(h.lock_dir / "fx-busy.lock"),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None and holder.stdout.readline().strip() == "held"
        rc, rep = h.run("busy", "--fixture", "fx-busy", "--fixture-wait", "0")
        assert rc == 1 and rep["reasons"] == ["fixture_busy"]
    finally:
        holder.kill()
        holder.wait()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "== 3 passed, 1 skipped, 2 warnings in 0.5s ==",
            {"run": 3, "passed": 3, "failed": 0, "errors": 0, "skipped": 1},
        ),
        (
            "== 1 failed, 4 passed, 2 errors in 2s ==",
            {"run": 7, "passed": 4, "failed": 1, "errors": 2, "skipped": 0},
        ),
        (
            "== no tests ran in 0.01s ==",
            {"run": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0},
        ),
        (
            "x 0 failed, 0 error(s) of 9 tests\nlater 2 failed, 1 error(s) of 30 tests\n",
            {"run": 30, "passed": 27, "failed": 2, "errors": 1, "skipped": 0},
        ),
        ("nothing parseable", None),
    ],
)
def test_parse_counts(text: str, expected: dict[str, int] | None) -> None:
    assert cto_integrate.parse_counts(text) == expected


def test_resolution_kind_mapping() -> None:
    assert cto_integrate.resolution_kind("addons/x/__manifest__.py") == "version"
    assert cto_integrate.resolution_kind("addons/x/README.md") == "readme_version"
    assert cto_integrate.resolution_kind("addons/x/tests/__init__.py") == "tests_init"
    assert cto_integrate.resolution_kind("tests/__init__.py") == "tests_init"
    assert cto_integrate.resolution_kind("addons/x/models.py") is None


def test_invalid_train_is_rejected(h: Harness) -> None:
    path = h.train([1], order=[1, 2])
    rc, out = h.build("--train", str(path))
    assert rc == 2 and "order must list every PR" in out["error"]


def test_no_checks_declared_is_not_a_pass(h: Harness) -> None:
    h.pr(1, {"one.txt": "1\n"})
    h.train([1], static=[], suite=[])
    h.build("--candidate", "empty")
    rc, rep = h.run("empty")
    assert rc == 1 and rep["reasons"] == ["no_checks_declared"]


def test_outputs_never_grant_permission(h: Harness) -> None:
    assert os.path.isfile(cto_integrate.RECEIPT_SCHEMA_PATH)
    h.pr(1, {"one.txt": "1\n"})
    h.train([1])
    rc, out = h.build("--candidate", "g")
    assert out["grants_permission"] is False
    rc, rep = h.run("g")
    assert rep["grants_permission"] is False
    assert h.receipt("g")["grants_permission"] is False


def test_lock_file_is_private_to_its_owner(tmp_path: Path) -> None:
    lock = tmp_path / "locks" / "fx.lock"
    with cto_integrate.exclusive_lock(lock, 0) as got:
        assert got
    assert lock.stat().st_mode & 0o077 == 0
