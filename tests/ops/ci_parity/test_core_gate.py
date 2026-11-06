"""The semgrep-l9 lane is Analyze (central Core)'s SDK gate, run before the push.

A stand-in `l9-ci` CLI plays the SDK so the verdict mapping is exercised without
the network: `semgrep run` writes (or, on request, omits) a finding bundle and
`gate evaluate` exits with the code the test chooses, as org-ci.yml reads it.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import manifest  # noqa: E402
import run  # noqa: E402

FAKE_SDK = """
import json, os, sys
args = sys.argv[1:]
def value(flag):
    return args[args.index(flag) + 1]
with open(os.environ["FAKE_SDK_LOG"], "a") as fh:
    fh.write(json.dumps(args) + "\\n")
if args[:2] == ["semgrep", "run"]:
    if os.environ.get("FAKE_NO_BUNDLE"):
        print("error[unresolved_strict_contract]: unresolved", file=sys.stderr)
        raise SystemExit(0)
    rule = "l9.baseline.python.hardcoded-credential"
    bundle = {"findings": [{"finding_id": "fn_1", "provider_rule_id": rule,
              "message": "hardcoded credential",
              "locations": [{"normalized_path": "ops/x.py", "start_line": 7}]}],
              "provider_failures": [{"message": "Semgrep did not produce a report"}]}
    open(value("--output"), "w").write(json.dumps(bundle))
    raise SystemExit(0)
if args[:2] == ["gate", "evaluate"]:
    code = int(os.environ.get("FAKE_GATE_EXIT", "0"))
    if code == 1:
        open(value("--output"), "w").write(json.dumps({"blocking_finding_ids": ["fn_1"]}))
    raise SystemExit(code)
raise SystemExit(99)
"""


def _ctx(tmp_path: Path, scan_dir: Path) -> run.Context:
    loaded = manifest.load()
    return run.Context(
        loaded=loaded,
        workspace=scan_dir,
        slug="local/x",
        cache=tmp_path / "cache",
        scan_dir=scan_dir,
        sha="a" * 40,
        base="b" * 40,
        changed=["ops/x.py"],
        ranges={},
        nice=False,
        timeout=60,
    )


@pytest.fixture
def sdk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    fake = tmp_path / "fake_sdk.py"
    fake.write_text(FAKE_SDK)
    log = tmp_path / "sdk.log"
    log.write_text("")
    monkeypatch.setenv("FAKE_SDK_LOG", str(log))
    work = tmp_path / "work"
    work.mkdir()
    scan = tmp_path / "scan"
    scan.mkdir()
    gov = run.CoreGovernance(
        core_sha="c" * 40,
        strict=False,
        required=True,
        policy=Path(".l9/runtime/org-governance/semgrep-policy.yaml"),
        identity_maps=Path(".l9/runtime/org-governance/semgrep-identity-maps"),
    )
    ctx = _ctx(tmp_path, scan)
    (tmp_path / "cache").mkdir()
    return {"cli": [sys.executable, str(fake)], "log": log, "work": work, "ctx": ctx, "gov": gov}


def _gate(sdk: dict, languages: tuple[str, ...] = ("python",)) -> list:
    return run._sdk_gate(
        sdk["ctx"], sdk["cli"], languages, sdk["gov"], sdk["work"], dict(os.environ)
    )


def _calls(sdk: dict) -> list[list[str]]:
    return [json.loads(line) for line in sdk["log"].read_text().splitlines()]


def test_gate_pass_has_no_findings_and_mirrors_core_arguments(
    sdk: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_GATE_EXIT", "0")
    assert _gate(sdk) == []
    semgrep_run, gate = _calls(sdk)
    assert semgrep_run[:4] == ["semgrep", "run", "--language", "python"]
    assert semgrep_run[semgrep_run.index("--policy") + 1] == str(sdk["gov"].policy)
    identity = semgrep_run[semgrep_run.index("--identity-map") + 1]
    assert identity.endswith("semgrep-identity-maps/python.yaml")
    assert "--strict" not in semgrep_run and "--required" in semgrep_run  # pr_fast
    assert gate[-1] == "--no-strict-unresolved"


def test_strict_profile_passes_strict_to_both_calls(
    sdk: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_GATE_EXIT", "0")
    sdk["gov"] = run.CoreGovernance(
        "c" * 40, True, False, sdk["gov"].policy, sdk["gov"].identity_maps
    )
    _gate(sdk)
    semgrep_run, gate = _calls(sdk)
    assert "--strict" in semgrep_run and "--required" not in semgrep_run
    assert gate[-1] == "--strict-unresolved"


def test_gate_fail_reports_core_blocking_findings_with_locations(
    sdk: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_GATE_EXIT", "1")
    found = _gate(sdk)
    assert [(f.path, f.line, f.severity) for f in found] == [("ops/x.py", 7, "error")]
    assert found[0].rule == "l9.baseline.python.hardcoded-credential"


def test_incomplete_gate_is_a_notice_never_a_pass(
    sdk: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_GATE_EXIT", "6")
    assert _gate(sdk) == []
    notice = " ".join(sdk["ctx"].notices)
    assert "gate incomplete" in notice and "did not produce a report" in notice


def test_semgrep_run_exit_zero_without_a_bundle_is_never_a_pass(
    sdk: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_NO_BUNDLE", "1")
    assert _gate(sdk) == []
    assert len(_calls(sdk)) == 1  # gate evaluate never ran on a missing bundle
    assert "wrote no bundle" in sdk["ctx"].notices[0]
    assert "unresolved_strict_contract" in sdk["ctx"].notices[0]


def test_each_changed_language_gets_its_own_run(sdk: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_GATE_EXIT", "0")
    _gate(sdk, ("python", "typescript"))
    languages = [c[3] for c in _calls(sdk) if c[:2] == ["semgrep", "run"]]
    assert languages == ["python", "typescript"]


def test_sdk_languages_cover_only_what_the_sdk_packages() -> None:
    assert run.sdk_languages(["a.py", "b.pyi", "c.ts", "d.jsx", "e.json", "f.sh"]) == [
        "python",
        "typescript",
    ]
    assert run.sdk_languages(["README.md"]) == []


def test_proxy_shim_only_when_proxy_settings_exist(tmp_path: Path) -> None:
    semgrep = tmp_path / "bin" / "semgrep"
    semgrep.parent.mkdir()
    semgrep.write_text("#!/bin/sh\n")
    plain = run.provider_path(tmp_path / "w1", semgrep, {"PATH": "/usr/bin"})
    assert plain == os.pathsep.join([str(semgrep.parent), "/usr/bin"])
    assert not (tmp_path / "w1").exists()
    proxied = run.provider_path(
        tmp_path / "w2", semgrep, {"PATH": "/usr/bin", "HTTPS_PROXY": "http://p:1", "OTHER": "x"}
    )
    shim = tmp_path / "w2" / "semgrep-shim" / "semgrep"
    assert proxied.split(os.pathsep)[0] == str(shim.parent)
    body = shim.read_text()
    assert "export HTTPS_PROXY=http://p:1" in body and "OTHER" not in body
    assert f"exec {semgrep}" in body
    assert stat.S_IMODE(shim.stat().st_mode) == 0o700


def test_core_governance_is_read_from_core_and_staged_like_org_ci(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = run.GOVERNANCE_ROOT
    files = {
        f"{root}/defaults/execution-profiles.yaml": '{"profiles": {"pr_fast": {"strict": false}}}',
        f"{root}/defaults/provider-requiredness.yaml": (
            '{"profiles": {"pr_fast": {"semgrep": true}}}'
        ),
        f"{root}/defaults/quality-thresholds.yaml": (
            '{"profiles": {"pr_fast": {"sdk_policy": "semgrep-policy.yaml"}}}'
        ),
        f"{root}/semgrep-policy.yaml": '{"defaults": {"mode": "blocking"}}',
        f"{root}/identity-maps/python.yaml": "rules: {}\n",
    }
    reads: list[str] = []

    class Reader:
        @staticmethod
        def core_commit(ref: str) -> str:
            assert ref == "main"
            return "d" * 40

        @staticmethod
        def core_file(sha: str, path: str) -> str:
            reads.append(path)
            return files[path]

    monkeypatch.setattr(run, "_core_reader", lambda: Reader)
    scan = tmp_path / "scan"
    scan.mkdir()
    ctx = _ctx(tmp_path, scan)
    ctx = run.replace(ctx, loaded=run.replace(ctx.loaded, cache_root=tmp_path / "cache"))
    gov = run.stage_core_governance(ctx, "pr_fast", ["python"])
    assert (gov.strict, gov.required, gov.core_sha) == (False, True, "d" * 40)
    assert (scan / gov.policy).read_text() == files[f"{root}/semgrep-policy.yaml"]
    assert (scan / gov.identity_maps / "python.yaml").read_text() == "rules: {}\n"
    first = len(reads)
    run.stage_core_governance(ctx, "pr_fast", ["python"])
    assert len(reads) == first  # cached per Core commit
    with pytest.raises(ValueError, match="no 'strict' for profile 'release'"):
        run.stage_core_governance(ctx, "release", ["python"])


def test_lane_without_semgrep_installed_is_a_skip(tmp_path: Path) -> None:
    loaded = run.replace(manifest.load(), install_root=tmp_path / "nothing")
    ctx = run.replace(_ctx(tmp_path, tmp_path), loaded=loaded)
    lane = loaded.lanes["semgrep-l9"]
    assert run._lane_semgrep_l9(ctx, lane, tmp_path / "l9-ci", ["ops/x.py"]) == []
    assert ctx.notices and "SKIP" in ctx.notices[0]


def test_sdk_python_is_the_tool_shebang(tmp_path: Path) -> None:
    binary = tmp_path / "l9-ci"
    binary.write_text(f"#!{sys.executable}\nprint()\n")
    assert run.sdk_python(binary) == sys.executable


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_snapshot_fetches_from_the_workspace_being_scanned(tmp_path: Path) -> None:
    """The clone is cached per repository; a second checkout's commit must still resolve."""
    first = tmp_path / "first"
    first.mkdir()
    _git(first, "init", "-q", "-b", "main")
    (first / "a.txt").write_text("a\n")
    _git(first, "add", "a.txt")
    _git(first, "commit", "-q", "-m", "base")
    cache = tmp_path / "cache"
    cache.mkdir()
    run.ensure_snapshot(first, cache, _git(first, "rev-parse", "HEAD"))
    second = tmp_path / "second"
    _git(tmp_path, "clone", "-q", str(first), str(second))
    (second / "b.txt").write_text("b\n")
    _git(second, "add", "b.txt")
    _git(second, "commit", "-q", "-m", "only in the second checkout")
    sha = _git(second, "rev-parse", "HEAD")
    clone = run.ensure_snapshot(second, cache, sha)
    assert _git(clone, "rev-parse", "HEAD") == sha and (clone / "b.txt").is_file()


def test_scope_keeps_whole_file_and_whole_tree_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    found = [
        run.fnd.Finding("t", "r", "error", "changed.json", 1, "whole-file format"),
        run.fnd.Finding("t", "r", "error", "untouched.py", 3, "tree-wide rule"),
    ]
    monkeypatch.setitem(run.LANES, "biome", lambda ctx, lane, binary, files: list(found))
    loaded = manifest.load()
    binary = tmp_path / "biome"
    binary.write_text("")
    monkeypatch.setattr(manifest.Manifest, "resolve", lambda self, name: binary)
    ctx = run.replace(_ctx(tmp_path, tmp_path), changed=["changed.json"], ranges={})
    sem = run.WeightedSemaphore(2)
    biome = run.run_lane(ctx, loaded.lanes["biome"], sem)
    assert [f["path"] for f in biome["blocking"]] == ["changed.json"]  # changed-files scope
    tree_lane = run.replace(loaded.lanes["biome"], extra={"scope": "whole-tree"})
    tree = run.run_lane(ctx, tree_lane, sem)
    assert sorted(f["path"] for f in tree["blocking"]) == ["changed.json", "untouched.py"]
    line_lane = run.replace(loaded.lanes["biome"], extra={})
    assert run.run_lane(ctx, line_lane, sem)["blocking"] == []  # default: changed lines only


def test_gate_lanes_filter_runs_only_the_named_lanes(tmp_path: Path) -> None:
    ctx = run.replace(_ctx(tmp_path, tmp_path), changed=["a.json", "b.py", "c.sh"])
    names = {lane.name for lane in run.applicable(ctx, ("fast", "heavy"), ["biome", "semgrep-l9"])}
    assert names == {"biome", "semgrep-l9"}
    assert "shellcheck" in {lane.name for lane in run.applicable(ctx, ("fast", "heavy"))}


def test_core_lane_receipt_stands_only_for_the_same_core_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = manifest.load()
    lane = loaded.lanes["semgrep-l9"]
    digest = run._lane_digest(loaded, lane)
    record = {"digest": digest, "status": "pass", "core_sha": "a" * 40}
    monkeypatch.setattr(run, "_CORE_SHAS", {"main": "a" * 40})
    assert run.receipt_reusable(loaded, lane, record)
    monkeypatch.setattr(run, "_CORE_SHAS", {"main": "b" * 40})  # Core moved its governance
    assert not run.receipt_reusable(loaded, lane, record)
    monkeypatch.setattr(run, "_CORE_SHAS", {})

    class Unreachable:
        @staticmethod
        def core_commit(ref: str) -> str:
            raise RuntimeError("git transport also failed")

    monkeypatch.setattr(run, "_core_reader", lambda: Unreachable)
    assert not run.receipt_reusable(loaded, lane, record)  # cannot prove it: re-run


def test_skip_and_error_receipts_are_never_reused() -> None:
    loaded = manifest.load()
    lane = loaded.lanes["biome"]
    digest = run._lane_digest(loaded, lane)
    assert run.receipt_reusable(loaded, lane, {"digest": digest, "status": "pass"})
    for status in ("skip", "error"):
        assert not run.receipt_reusable(loaded, lane, {"digest": digest, "status": status})


def test_core_lane_records_the_core_commit_it_applied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = manifest.load()
    lane = loaded.lanes["semgrep-l9"]
    binary = tmp_path / "tool"
    binary.write_text("")
    monkeypatch.setattr(manifest.Manifest, "resolve", lambda self, name: binary)

    def lane_fn(ctx: run.Context, lane: object, binary: Path, files: list[str]) -> list:
        ctx.facts["core_sha"] = "e" * 40
        return []

    monkeypatch.setitem(run.LANES, "semgrep-l9", lane_fn)
    ctx = run.replace(_ctx(tmp_path, tmp_path), changed=["ops/x.py"])
    record = run.run_lane(ctx, lane, run.WeightedSemaphore(2))
    assert record["core_sha"] == "e" * 40 and record["status"] == "pass"


def test_cli_rejects_an_unknown_lane(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        run.main(["--gate", "HEAD", "--lanes", "biome,no-such-lane"])
    assert "unknown lane(s) no-such-lane" in capsys.readouterr().err
