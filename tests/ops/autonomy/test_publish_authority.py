"""Per-repository publish route — ops/config/publish-authority.json.

The governance ``pr`` target is the publish verb everywhere. A repository that
owns its own publication ceremony (IB-Odoo_19: ``make pr`` → base ``Staging``)
is declared Governance-side and delegated to exactly once. These tests pin:

* one origin normalizer shared with ``local_execution_gate._origin_identity``;
* parse-time routing in ``publish.mk`` (native vs byte-identical governance);
* run-time fail-closed (drift, base mismatch, invalid registry);
* the native runner's receipt, gate-only mapping and env scrub;
* doctrine surfaces naming the registry.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from ops.autonomy import local_execution_gate as gate  # noqa: E402
from ops.autonomy import publish_authority as pa  # noqa: E402

RESOLVER = REPO_ROOT / "ops" / "autonomy" / "publish_authority.py"
RUNNER = REPO_ROOT / "ops" / "scripts" / "run_native_publish.sh"
PREFLIGHT = REPO_ROOT / "ops" / "scripts" / "pr_preflight.sh"
REGISTRY = REPO_ROOT / "ops" / "config" / "publish-authority.json"
ODOO_KEY = "github.com/cryptoxdog/ib-odoo_19"
GOV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PY = str(GOV_PY if GOV_PY.is_file() else sys.executable)

SPELLINGS = (
    "git@github.com:cryptoxdog/IB-Odoo_19.git",
    "https://github.com/cryptoxdog/IB-Odoo_19",
    "https://github.com/cryptoxdog/IB-Odoo_19.git",
    "ssh://git@github.com/cryptoxdog/ib-odoo_19.git",
    "git://github.com/Cryptoxdog/IB-Odoo_19",
    "ssh://git@github.com:22/cryptoxdog/IB-Odoo_19.git",
    "https://github.com:443/cryptoxdog/IB-Odoo_19",
)


def _repo(tmp_path: Path, name: str, origin: str | None) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    if origin:
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", origin], check=True)
    return repo.resolve()


def _resolver(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PY, str(RESOLVER), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env or os.environ.copy(),
    )


def _make_dry_run(ws: Path, *goals: str, extra: tuple[str, ...] = ()) -> str:
    env = os.environ.copy()
    env.pop("MAKEFLAGS", None)
    env.pop("PR_BASE", None)
    proc = subprocess.run(
        ["make", "--no-print-directory", "-n", "-C", str(REPO_ROOT), *goals, f"WS={ws}", *extra],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return proc.stdout + proc.stderr


# --- one normalizer -----------------------------------------------------------------


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_normalize_origin_matches_gate_identity(tmp_path: Path, spelling: str) -> None:
    repo = _repo(tmp_path, "r", spelling)
    assert pa.normalize_origin(spelling) == ODOO_KEY
    assert pa.origin_of(repo) == ODOO_KEY
    assert gate._origin_identity(repo) == ODOO_KEY


def test_normalize_origin_empty_is_none() -> None:
    assert pa.normalize_origin("") is None
    assert pa.normalize_origin(None) is None


def test_normalize_origin_keeps_path_colons_and_rejects_bad_port() -> None:
    # scp form converts only the host/path separator
    assert pa.normalize_origin("git@github.com:owner/na:me.git") == "github.com/owner/na:me"
    # a non-numeric "port" is not an authority we can key on
    assert pa.normalize_origin("ssh://git@github.com:abc/owner/name") is None


# --- registry + resolve ---------------------------------------------------------------


def test_registry_declares_odoo_native_route() -> None:
    document = pa.load_registry(REGISTRY)
    entry = document["repositories"][ODOO_KEY]
    assert entry["route"] == "native"
    assert entry["native_target"] == "pr"
    assert entry["native_check_target"] == "pr-check"
    assert entry["declared_base"] == "Staging"
    assert "CANONICAL_LAW.md" in entry["authority"]
    assert document["default_route"] == "governance"
    # The origin is never the only basis: the ceremony is pinned Governance-side.
    assert entry["ceremony"]["kernel"] == "scripts/make_push_pipeline.sh"
    assert "git status --porcelain" in entry["ceremony"]["kernel_requires"]


def test_missing_registry_parse_governance_run_invalid(tmp_path: Path) -> None:
    """A clone that lost the registry has no policy, not an empty one."""
    repo = _repo(tmp_path, "odoo", SPELLINGS[1])
    missing = tmp_path / "absent.json"
    parse = _resolver("--workspace", str(repo), "--registry", str(missing), "--format", "make")
    assert parse.returncode == 0 and parse.stdout.strip() == "route=governance"
    for expect in ("native", "governance"):
        run = _resolver(
            "--workspace",
            str(repo),
            "--registry",
            str(missing),
            "--format",
            "json",
            "--expect",
            expect,
        )
        assert run.returncode == 3, expect
        assert "PUBLISH_REGISTRY_INVALID" in run.stderr and "registry missing" in run.stderr


def test_native_route_requires_a_declared_ceremony(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "schema": pa.SCHEMA,
                "default_route": "governance",
                "repositories": {
                    ODOO_KEY: {
                        "route": "native",
                        "native_target": "pr",
                        "declared_base": "Staging",
                        "authority": "x",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(pa.RegistryError, match="ceremony"):
        pa.load_registry(bad)


def test_listed_origin_resolves_native(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    decision = pa.resolve(repo)
    assert decision.route == "native"
    assert decision.make_line() == (
        f"route=native target=pr check_target=pr-check base=Staging origin={ODOO_KEY}"
    )


@pytest.mark.parametrize(
    ("name", "origin"),
    [("unknown", "https://github.com/Example-Org/consumer.git"), ("noorigin", None)],
)
def test_unlisted_or_originless_resolves_governance(
    tmp_path: Path, name: str, origin: str | None
) -> None:
    repo = _repo(tmp_path, name, origin)
    assert pa.resolve(repo).make_line() == "route=governance"


def test_not_a_repo_resolves_governance(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    proc = _resolver("--workspace", str(plain), "--format", "make")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "route=governance"


def test_malformed_registry_parse_governance_run_invalid(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[1])
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    parse = _resolver("--workspace", str(repo), "--registry", str(bad), "--format", "make")
    assert parse.returncode == 0 and parse.stdout.strip() == "route=governance"
    run = _resolver(
        "--workspace", str(repo), "--registry", str(bad), "--format", "json", "--expect", "native"
    )
    assert run.returncode == 3
    assert "PUBLISH_REGISTRY_INVALID" in run.stderr


def test_registry_rejects_non_host_keys(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "schema": pa.SCHEMA,
                "default_route": "governance",
                "repositories": {
                    "cryptoxdog/ib-odoo_19": {
                        "route": "native",
                        "native_target": "pr",
                        "declared_base": "Staging",
                        "authority": "x",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(pa.RegistryError):
        pa.load_registry(bad)


@pytest.mark.parametrize("base", ["origin/main", "main"])
def test_native_repo_refuses_other_base(tmp_path: Path, base: str) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    proc = _resolver(
        "--workspace", str(repo), "--format", "json", "--expect", "native", "--pr-base", base
    )
    assert proc.returncode == 2
    assert "PUBLISH_BASE_MISMATCH" in proc.stderr


@pytest.mark.parametrize("base", ["Staging", "origin/Staging", ""])
def test_native_repo_accepts_declared_base(tmp_path: Path, base: str) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    args = ["--workspace", str(repo), "--format", "json", "--expect", "native"]
    if base:
        args += ["--pr-base", base]
    proc = _resolver(*args)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["verdict"] == "OK"


def test_route_drift_is_exit_2(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    proc = _resolver("--workspace", str(repo), "--format", "json", "--expect", "governance")
    assert proc.returncode == 2
    assert "PUBLISH_ROUTE_DRIFT" in proc.stderr


# --- publish.mk parse-time routing -------------------------------------------------------


def test_make_pr_dry_run_routes_native_for_odoo(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    out = _make_dry_run(repo, "pr")
    assert "run_native_publish.sh" in out, out
    assert "run_pr_gate.sh" not in out
    assert "pr_preflight.sh" not in out
    assert 'PR_BASE=""' in out  # root default is not forwarded


def test_make_pr_dry_run_forwards_explicit_base_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    out = _make_dry_run(repo, "pr", extra=("PR_BASE=origin/main",))
    assert 'PR_BASE="origin/main"' in out, out


def test_make_pr_alias_routes_native(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    assert "run_native_publish.sh" in _make_dry_run(repo, "PR")


def test_make_pr_dry_run_keeps_governance_for_unlisted(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "consumer", "https://github.com/Example-Org/consumer.git")
    out = _make_dry_run(repo, "pr")
    assert "run_native_publish.sh" not in out, out
    assert "run_pr_gate.sh" in out
    assert "pr_preflight.sh" in out


def test_publish_mk_keeps_governance_branch_first() -> None:
    body = (REPO_ROOT / "ops" / "make" / "publish.mk").read_text(encoding="utf-8")
    first_pr = body.index("\npr:")
    assert body[first_pr : first_pr + len("\npr: pr-preflight")] == "\npr: pr-preflight"
    assert "PR Pr pR: pr" in body
    assert "pr: export PR_EARLY_OVERLAP = 1" in body
    assert "pr-check:" not in body
    assert "$(origin PR_BASE)" in body
    assert "$(filter pr PR Pr pR,$(MAKECMDGOALS))" in body


# --- run-time fail-closed --------------------------------------------------------------


def test_preflight_stops_native_repo_with_route_drift(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    env = os.environ.copy()
    env.pop("WS", None)
    proc = subprocess.run(
        ["bash", str(PREFLIGHT), str(repo)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "PUBLISH_ROUTE_DRIFT" in proc.stderr


KERNEL = "scripts/make_push_pipeline.sh"
GOV_RECEIPT = REPO_ROOT / ".l9" / "pr" / "publish-route.json"


def _stub_consumer(
    tmp_path: Path, *, check_target: bool = True, kernel: bool = True, invokes_kernel: bool = True
) -> Path:
    """A repository spelling the Odoo origin, with (by default) its real ceremony shape:
    a `pr` recipe that invokes the pinned kernel, and a kernel carrying the pinned guards."""
    repo = _repo(tmp_path, "odoo", SPELLINGS[0])
    call = f"@bash {KERNEL} '' '' $(base) 1 0\n" if invokes_kernel else ""
    recipe = (
        "pr:\n"
        f"\t{call}"
        "\t@echo NATIVE_PR base=$(base) PYTHON=[$$PYTHON] WS=[$$WS]"
        " MAKEOVERRIDES=[$$MAKEOVERRIDES] EARLY=[$$PR_EARLY_OVERLAP]"
        " OPEN_PR=[$$OPEN_PR] PR_BASE=[$$PR_BASE]\n"
    )
    if check_target:
        recipe += "pr-check:\n\t@echo NATIVE_CHECK base=$(base)\n"
    (repo / "Makefile").write_text(recipe, encoding="utf-8")
    if kernel:
        (repo / KERNEL).parent.mkdir(parents=True)
        (repo / KERNEL).write_text(
            "#!/usr/bin/env bash\n"
            'BASE="${3:-Staging}"\n'
            '[[ "$BASE" == "Staging" ]] || refuse "destination must be Staging (got $BASE)"\n'
            'status="$(git status --porcelain)"\n'
            "exit 0\n",
            encoding="utf-8",
        )
    # The consumer ceremony refuses an unclean tree; the fixture commits so the
    # runner's "untouched worktree" proof is meaningful.
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "f"],
        check=True,
    )
    return repo


def _runner(repo: Path, **env: str) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.pop("PR_BASE", None)  # tests pass PR_BASE explicitly when they mean to
    # publish.mk exports WS/OPEN_PR/PR_BASE into the runner; WS is also what a
    # governance `make` would have exported — the consumer must see none of it.
    merged.update(
        {
            "PYTHON": "/leaked/python",
            "MAKEOVERRIDES": "WS=/leaked",
            "PR_EARLY_OVERLAP": "1",
            "WS": "/leaked/ws",
        }
    )
    merged.update(env)
    return subprocess.run(
        ["bash", str(RUNNER), str(repo)],
        capture_output=True,
        text=True,
        check=False,
        env=merged,
    )


def test_native_runner_runs_consumer_pr_once_scrubbed(tmp_path: Path) -> None:
    repo = _stub_consumer(tmp_path)
    proc = _runner(repo, OPEN_PR="1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.count("NATIVE_PR") == 1
    # base=Staging is the one override governance passes on purpose; the
    # inherited governance state must not reach the consumer recipe.
    assert "NATIVE_PR base=Staging PYTHON=[] WS=[] MAKEOVERRIDES=[" in proc.stdout
    assert "EARLY=[] OPEN_PR=[] PR_BASE=[]" in proc.stdout
    assert "/leaked" not in proc.stdout
    # The receipt is governance evidence and never lands in the consumer worktree,
    # whose own ceremony refuses any untracked file (.l9/pr is not in its .gitignore).
    assert not (repo / ".l9").exists()
    assert (
        subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
        ).stdout
        == ""
    )
    receipt = json.loads(GOV_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["schema"] == "l9.publish_route.v1"
    assert receipt["origin"] == ODOO_KEY
    assert receipt["workspace"] == str(repo)
    assert receipt["target"] == "pr"
    assert receipt["declared_base"] == "Staging"
    assert receipt["open_pr"] is True
    assert receipt["ceremony_verified"] is True


def test_native_runner_open_pr_zero_maps_to_check_target(tmp_path: Path) -> None:
    repo = _stub_consumer(tmp_path)
    proc = _runner(repo, OPEN_PR="0")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "NATIVE_CHECK base=Staging" in proc.stdout
    assert "NATIVE_PR" not in proc.stdout
    receipt = json.loads(GOV_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["target"] == "pr-check" and receipt["open_pr"] is False


def test_native_runner_refuses_missing_consumer_target(tmp_path: Path) -> None:
    repo = _stub_consumer(tmp_path, check_target=False)
    GOV_RECEIPT.unlink(missing_ok=True)
    proc = _runner(repo, OPEN_PR="0")
    assert proc.returncode == 2
    assert "NATIVE_TARGET_MISSING" in proc.stderr
    assert not GOV_RECEIPT.exists()
    assert not (repo / ".l9").exists()


@pytest.mark.parametrize(
    ("kwargs", "problem"),
    [
        ({"kernel": False}, "unreadable"),
        ({"invokes_kernel": False}, "does not invoke"),
    ],
)
def test_a_copied_origin_without_the_ceremony_is_not_the_native_route(
    tmp_path: Path, kwargs: dict, problem: str
) -> None:
    """The origin URL is consumer-editable; a workspace that merely spells it
    does not get to run an arbitrary local `pr` target in governance's name."""
    repo = _stub_consumer(tmp_path, **kwargs)
    proc = _runner(repo, OPEN_PR="1")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "PUBLISH_CEREMONY_UNVERIFIED" in proc.stderr and problem in proc.stderr
    assert "NATIVE_PR" not in proc.stdout


def test_kernel_without_the_pinned_guards_is_not_the_ceremony(tmp_path: Path) -> None:
    repo = _stub_consumer(tmp_path)
    (repo / KERNEL).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "strip"], check=True)
    proc = _runner(repo, OPEN_PR="1")
    assert proc.returncode == 2
    assert "PUBLISH_CEREMONY_UNVERIFIED" in proc.stderr and "lacks guard" in proc.stderr


def test_native_runner_refuses_other_base_before_running_anything(tmp_path: Path) -> None:
    repo = _stub_consumer(tmp_path)
    proc = _runner(repo, OPEN_PR="1", PR_BASE="origin/main")
    assert proc.returncode == 2
    assert "PUBLISH_BASE_MISMATCH" in proc.stderr
    assert "NATIVE_PR" not in proc.stdout


# --- doctrine + consistency -------------------------------------------------------------


DOCTRINE_SURFACES = (
    "ops/autonomy/surface_profile.yaml",
    "rules/48-make-pr-remediation.mdc",
    "rules/88-l4-local-autonomy.mdc",
    "docs/L9_DISPATCHER.md",
    "docs/CLAUDE_SURFACE_PARITY.md",
)


@pytest.mark.parametrize("rel", DOCTRINE_SURFACES)
def test_doctrine_names_the_registry(rel: str) -> None:
    body = (REPO_ROOT / rel).read_text(encoding="utf-8")
    assert "publish-authority.json" in body, rel


def test_manifest_registers_registry() -> None:
    manifest = REPO_ROOT / "environment" / "contracts" / "autonomy" / "MANIFEST.yaml"
    body = manifest.read_text(encoding="utf-8")
    assert "publish_authority_registry: ops/config/publish-authority.json" in body


def test_campaign_default_branch_map_agrees_with_registry() -> None:
    campaign = REPO_ROOT / "environment" / "program-execution" / "scripts" / "run_campaign.py"
    source = campaign.read_text(encoding="utf-8")
    match = re.search(r"KNOWN_REMOTE_DEFAULT_BRANCHES\s*=\s*(\{.*?\})", source, re.S)
    assert match, "campaign map not found"
    known = ast.literal_eval(match.group(1))
    document = pa.load_registry(REGISTRY)
    for key, entry in document["repositories"].items():
        short = key.split("/", 1)[1]
        if short in known:
            assert known[short] == entry["declared_base"], key
