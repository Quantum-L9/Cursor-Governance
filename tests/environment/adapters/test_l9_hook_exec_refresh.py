"""Launcher refresh: SessionStart-scoped, origin-trusted, lease-locked.

The launcher refreshes the ephemeral governance clone before HOOK_PATH resolves
so tip-only SessionStart files exist for every sibling. PR #548 review
(F-548-001/002/003) pinned three properties this suite proves by execution:

- only SessionStart hooks refresh; gates and later-event observers never
  fetch or checkout;
- the fetch goes to the clone's configured origin and only when that origin is
  trusted — L9_GOVERNANCE_REMOTE cannot redirect it, and the test seam
  (L9_GOV_REFRESH_LOCAL_ORIGIN) admits a fixture only when it IS the origin;
- an abandoned lock (owner killed mid-fetch) is reclaimed by the next
  launcher, and a live lock never strands a hook without an explicit outcome.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = (
    REPO_ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
)
# A SessionStart-registered name (settings.template.json) whose body the
# fixture supplies at the origin tip only. The launcher decides scope by name.
TIP_HOOK = "bootstrap_capability_preflight.sh"
HOOKS_REL = Path("environment/agents/adapters/claude-code/hooks")
# Echoed by fixture hooks so a test can read the binding the launcher exported.
ECHO_BINDING = (
    'echo "attempt=${L9_GOV_REFRESH_ATTEMPT_ID-unset} outcome=${L9_GOV_REFRESH_OUTCOME-unset}"\n'
)
TEMPLATE = REPO_ROOT / "environment" / "agents" / "adapters" / "claude-code"
TEMPLATE = TEMPLATE / "settings.template.json"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _origin_with_tip_only_hook(
    tmp: Path, *, name: str = "origin", marker: str = "TIP_ONLY_RAN"
) -> tuple[Path, str]:
    work = tmp / f"{name}-work"
    work.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    _git(work, "config", "user.email", "t@e")
    _git(work, "config", "user.name", "t")
    (work / "CANONICAL_LAW.md").write_text("v1\n", encoding="utf-8")
    hooks = work / HOOKS_REL
    hooks.mkdir(parents=True)
    (hooks / "existing.sh").write_text("#!/usr/bin/env bash\necho existing\n", encoding="utf-8")
    _git(work, "add", "CANONICAL_LAW.md", "environment")
    _git(work, "commit", "-qm", "base")
    old = _git(work, "rev-parse", "HEAD").stdout.strip()
    (hooks / TIP_HOOK).write_text(
        f"#!/usr/bin/env bash\necho {marker}\n" + ECHO_BINDING + "exit 0\n",
        encoding="utf-8",
    )
    _git(work, "add", str(hooks / TIP_HOOK))
    _git(work, "commit", "-qm", "tip-only hook")
    origin = tmp / f"{name}.git"
    subprocess.run(["git", "clone", "--bare", "-q", str(work), str(origin)], check=True)
    return origin, old


def _clone_at(home: Path, origin: Path, sha: str) -> Path:
    gov = home / ".cursor-governance"
    subprocess.run(["git", "clone", "-q", str(origin), str(gov)], check=True)
    _git(gov, "checkout", "-q", sha)
    return gov


def _launcher_env(home: Path, extra: dict[str, str]) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "CURSOR_AGENT",
            "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "L9_GOVERNANCE_SURFACE",
            "L9_GOVERNANCE_DIR",
            "L9_GOVERNANCE_REMOTE",
            "L9_GOV_REFRESH_LOCAL_ORIGIN",
            "L9_GOV_REFRESH_ATTEMPT_ID",
            "L9_GOV_REFRESH_OUTCOME",
        }
    }
    env.update(
        {
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "CLAUDE_CODE_REMOTE": "true",
            "L9_SURFACE_GUARD": "0",
            "L9_GOVERNANCE_BRANCH": "main",
        }
    )
    env.update(extra)
    return env


def _run_launcher(
    home: Path,
    origin: Path | None,
    hook_name: str,
    *,
    hook_class: str = "observer",
    extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env_extra = dict(extra or {})
    if origin is not None:
        env_extra.setdefault("L9_GOV_REFRESH_LOCAL_ORIGIN", str(origin))
    return subprocess.run(
        ["bash", str(LAUNCHER), "--class", hook_class, hook_name],
        cwd=str(home),
        env=_launcher_env(home, env_extra),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _receipt(home: Path) -> dict:
    return json.loads((home / ".l9" / "claude" / "gov-refresh.json").read_text(encoding="utf-8"))


def _tip_present(gov: Path) -> bool:
    return (gov / HOOKS_REL / TIP_HOOK).is_file()


def test_launcher_refresh_precedes_hook_path_resolve() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert text.index("l9_cloud_refresh_gov") < text.index("HOOK_PATH=")
    assert subprocess.run(["bash", "-n", str(LAUNCHER)]).returncode == 0


def test_tip_only_hook_is_found_after_launcher_refresh(tmp_path: Path) -> None:
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    assert not _tip_present(gov)
    result = _run_launcher(home, origin, TIP_HOOK)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "TIP_ONLY_RAN" in result.stdout
    assert "hook file absent" not in result.stderr
    # The attempt that established the tree is bound into the hook's environment
    # and into the receipt it wrote, so the SessionStart hook can tell THIS
    # attempt from any older receipt.
    receipt = _receipt(home)
    assert receipt["outcome"] == "fetched"
    assert receipt["attempt_id"]
    assert f"attempt={receipt['attempt_id']} outcome=fetched" in result.stdout
    assert receipt["local_sha"] == _git(gov, "rev-parse", "HEAD").stdout.strip()
    assert isinstance(receipt["refreshed_epoch"], int)


def test_dirty_tracked_clone_is_not_force_reset(tmp_path: Path) -> None:
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    (gov / "CANONICAL_LAW.md").write_text("in-flight\n", encoding="utf-8")
    result = _run_launcher(home, origin, TIP_HOOK)
    assert result.returncode == 0, result.stderr
    assert (gov / "CANONICAL_LAW.md").read_text(encoding="utf-8") == "in-flight\n"
    assert "hook file absent" in result.stderr
    assert "TIP_ONLY_RAN" not in result.stdout
    assert not _tip_present(gov)
    assert _receipt(home)["outcome"] == "reset-skipped-dirty"


# --- F-548-002: only SessionStart hooks refresh ---------------------------------


def test_non_session_start_hooks_perform_no_refresh(tmp_path: Path) -> None:
    """A gate or later-event observer never fetches, checks out, or writes a receipt."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    # Register the tip-only body under non-SessionStart names in the CLONE so
    # the launcher can find and run them without any refresh.
    hooks = gov / HOOKS_REL
    (hooks / "pr_summary_posttool.sh").write_text(
        "#!/usr/bin/env bash\necho POSTTOOL_RAN\nexit 0\n", encoding="utf-8"
    )
    receipt = home / ".l9" / "claude" / "gov-refresh.json"

    for name, cls in (
        ("pr_summary_posttool.sh", "observer"),  # PostToolUse observer
        ("user_prompt_skill_router.py", "observer"),  # UserPromptSubmit observer
        ("merge_gate_wrap.py", "gate"),  # PreToolUse gate
        ("session_debt_wrap.py", "gate"),  # Stop gate
    ):
        result = _run_launcher(home, origin, name, hook_class=cls)
        assert _git(gov, "rev-parse", "HEAD").stdout.strip() == old, (name, result.stderr)
        assert not _tip_present(gov), name
        assert not receipt.exists(), name
        assert (
            "FETCH_HEAD"
            not in _git(gov, "rev-parse", "--verify", "-q", "FETCH_HEAD", check=False).stdout
        )

    ran = _run_launcher(home, origin, "pr_summary_posttool.sh")
    assert "POSTTOOL_RAN" in ran.stdout
    assert "attempt=unset outcome=unset" not in ran.stdout  # that body does not echo it
    # And the same clone still refreshes for a SessionStart hook afterwards.
    started = _run_launcher(home, origin, TIP_HOOK)
    assert "TIP_ONLY_RAN" in started.stdout
    assert receipt.exists()


def test_every_session_start_registration_is_in_the_launcher_table() -> None:
    """The scope table must name every SessionStart hook the template registers."""
    template = json.loads(
        (
            REPO_ROOT
            / "environment"
            / "agents"
            / "adapters"
            / "claude-code"
            / "settings.template.json"
        ).read_text(encoding="utf-8")
    )
    registered: set[str] = set()
    for group in template["hooks"]["SessionStart"]:
        for hook in group["hooks"]:
            registered.add(hook["command"].split()[-1].rstrip("'"))
    text = LAUNCHER.read_text(encoding="utf-8")
    table = text[
        text.index("l9_is_session_start_hook() {") : text.index("l9_gov_origin_trusted() {")
    ]
    for name in registered:
        assert name in table, f"{name} is registered for SessionStart but absent from the table"


# --- F-548-001: trusted origin only -----------------------------------------------


def test_foreign_governance_remote_cannot_change_executed_hook_bytes(tmp_path: Path) -> None:
    """L9_GOVERNANCE_REMOTE names an attacker repo; the canonical origin still wins."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    foreign, _ = _origin_with_tip_only_hook(tmp_path, name="foreign", marker="FOREIGN_POLICY_RAN")
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    result = _run_launcher(home, origin, TIP_HOOK, extra={"L9_GOVERNANCE_REMOTE": str(foreign)})
    assert result.returncode == 0, result.stderr
    assert "FOREIGN_POLICY_RAN" not in result.stdout
    assert "TIP_ONLY_RAN" in result.stdout, (
        "the canonical (seam-admitted) origin must still refresh"
    )
    assert "L9_GOVERNANCE_REMOTE is not the canonical governance remote" in result.stderr
    assert _git(gov, "remote", "get-url", "origin").stdout.strip() == str(origin)
    assert "FOREIGN_POLICY_RAN" not in (gov / HOOKS_REL / TIP_HOOK).read_text(encoding="utf-8")


def test_untrusted_origin_is_refused_without_the_seam(tmp_path: Path) -> None:
    """A clone whose origin is neither canonical nor the admitted seam never fetches."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    result = _run_launcher(home, None, TIP_HOOK)
    assert result.returncode == 0
    assert "governance refresh refused" in result.stderr
    assert "hook file absent" in result.stderr
    assert not _tip_present(gov)
    assert not (home / ".l9" / "claude" / "gov-refresh.json").exists()


def test_seam_must_equal_the_configured_origin(tmp_path: Path) -> None:
    """The seam admits the origin; it cannot point the fetch at another repo."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    foreign, _ = _origin_with_tip_only_hook(tmp_path, name="foreign", marker="FOREIGN_POLICY_RAN")
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    result = _run_launcher(home, foreign, TIP_HOOK)
    assert "governance refresh refused" in result.stderr
    assert "FOREIGN_POLICY_RAN" not in result.stdout
    assert not _tip_present(gov)
    assert _git(gov, "remote", "get-url", "origin").stdout.strip() == str(origin)


def _origin_trusted(url: str, seam: str = "") -> bool:
    """Run the launcher's own trust predicate on one URL."""
    text = LAUNCHER.read_text(encoding="utf-8")
    fn_start = text.index("l9_gov_origin_trusted() {")
    fn_end = text.index("\n}\n", fn_start) + 3
    script = (
        f"L9_GOV_CANONICAL_REMOTE={json.dumps(_canonical_remote(text))}\n"
        f"L9_GOV_REFRESH_LOCAL_ORIGIN={json.dumps(seam)}\n"
        + text[fn_start:fn_end]
        + f"l9_gov_origin_trusted {json.dumps(url)}\n"
    )
    return subprocess.run(["bash", "-c", script], capture_output=True, check=False).returncode == 0


def _canonical_remote(text: str) -> str:
    line = next(ln for ln in text.splitlines() if ln.startswith("L9_GOV_CANONICAL_REMOTE="))
    return line.split("=", 1)[1].strip().strip('"')


def test_canonical_github_remotes_are_trusted_by_name(tmp_path: Path) -> None:
    trusted = (
        "https://github.com/Quantum-L9/Cursor-Governance",
        "https://github.com/Quantum-L9/Cursor-Governance.git",
        "git@github.com:Quantum-L9/Cursor-Governance.git",
        "ssh://git@github.com/Quantum-L9/Cursor-Governance.git",
    )
    foreign = (
        "https://github.com/Evil-Org/Cursor-Governance.git",
        "https://github.com/Quantum-L9/Cursor-Governance-fork.git",
        "https://github.com/Quantum-L9/Cursor-Governance.git.evil.example",
        str(tmp_path),
        "",
    )
    for url in trusted:
        assert _origin_trusted(url), url
    for url in foreign:
        assert not _origin_trusted(url), url
    # The seam admits exactly the directory it names, and only an existing one.
    assert _origin_trusted(str(tmp_path), seam=str(tmp_path))
    assert not _origin_trusted(str(tmp_path / "other"), seam=str(tmp_path))
    assert not _origin_trusted(str(tmp_path / "missing"), seam=str(tmp_path / "missing"))
    assert "remote set-url" not in LAUNCHER.read_text(encoding="utf-8"), (
        "the launcher must never rewrite origin"
    )


# --- F-548-003: abandoned locks recover ----------------------------------------------


def _lockdir(home: Path) -> Path:
    return home / ".l9" / "claude" / "gov-refresh.lock.d"


def test_lock_left_by_a_killed_owner_is_reclaimed(tmp_path: Path) -> None:
    """Owner PID dead: the next SessionStart launcher reclaims and refreshes."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    # A launcher that was killed mid-fetch: it holds the lock, its pid is gone.
    victim = subprocess.Popen(["sleep", "30"])
    victim.kill()
    victim.wait()
    lock = _lockdir(home)
    lock.mkdir(parents=True)
    (lock / "owner").write_text(f"{victim.pid} {int(time.time())} {TIP_HOOK}\n", encoding="utf-8")

    result = _run_launcher(home, origin, TIP_HOOK, extra={"L9_GOV_REFRESH_WAIT_TICKS": "3"})
    assert result.returncode == 0, result.stderr
    assert "reclaimed an abandoned lock" in result.stderr
    assert "TIP_ONLY_RAN" in result.stdout
    assert _receipt(home)["outcome"] == "fetched"
    assert not lock.exists(), "the reclaimed lease is released after the refresh"
    assert _tip_present(gov)


def test_expired_lease_of_a_live_owner_is_reclaimed(tmp_path: Path) -> None:
    """A holder that is alive but past its lease (a hung fetch) does not strand refresh."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    _clone_at(home, origin, old)
    holder = subprocess.Popen(["sleep", "30"])
    try:
        lock = _lockdir(home)
        lock.mkdir(parents=True)
        (lock / "owner").write_text(
            f"{holder.pid} {int(time.time()) - 600} {TIP_HOOK}\n", encoding="utf-8"
        )
        result = _run_launcher(
            home,
            origin,
            TIP_HOOK,
            extra={"L9_GOV_REFRESH_WAIT_TICKS": "3", "L9_GOV_REFRESH_LEASE": "60"},
        )
    finally:
        holder.kill()
        holder.wait()
    assert "reclaimed an abandoned lock" in result.stderr
    assert "TIP_ONLY_RAN" in result.stdout


def test_lock_directory_without_owner_record_is_aged_and_reclaimed(tmp_path: Path) -> None:
    """A pre-lease lock directory (the shape the old launcher left) still recovers."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    _clone_at(home, origin, old)
    lock = _lockdir(home)
    lock.mkdir(parents=True)
    stale = time.time() - 600
    os.utime(lock, (stale, stale))
    result = _run_launcher(home, origin, TIP_HOOK, extra={"L9_GOV_REFRESH_WAIT_TICKS": "3"})
    assert "reclaimed an abandoned lock" in result.stderr
    assert "TIP_ONLY_RAN" in result.stdout


def test_live_lease_is_waited_on_then_reported_not_silently_skipped(tmp_path: Path) -> None:
    """A genuinely busy lock never blocks the hook and never pretends to have refreshed."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    # The hook must exist in the clone for the launcher to run it without refresh.
    hooks = gov / HOOKS_REL
    (hooks / TIP_HOOK).write_text(
        "#!/usr/bin/env bash\n" + ECHO_BINDING,
        encoding="utf-8",
    )
    holder = subprocess.Popen(["sleep", "30"])
    try:
        lock = _lockdir(home)
        lock.mkdir(parents=True)
        (lock / "owner").write_text(f"{holder.pid} {int(time.time())} other.sh\n", encoding="utf-8")
        result = _run_launcher(home, origin, TIP_HOOK, extra={"L9_GOV_REFRESH_WAIT_TICKS": "3"})
    finally:
        holder.kill()
        holder.wait()
    assert result.returncode == 0, result.stderr
    assert "lock busy" in result.stderr
    assert "attempt=unset outcome=lock-busy" in result.stdout
    assert lock.exists(), "a live lease is not stolen"
    assert not (home / ".l9" / "claude" / "gov-refresh.json").exists()


def test_sibling_receipt_of_this_session_is_adopted_without_a_second_fetch(tmp_path: Path) -> None:
    """Concurrent SessionStart siblings observe one freshly established revision."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    first = _run_launcher(home, origin, TIP_HOOK)
    assert "TIP_ONLY_RAN" in first.stdout
    receipt = _receipt(home)
    # Prove the second launcher did not fetch: move origin ahead; an adopted
    # receipt means HEAD stays at the revision the first sibling established.
    work = tmp_path / "origin-work"
    (work / "AFTER.md").write_text("later\n", encoding="utf-8")
    _git(work, "add", "AFTER.md")
    _git(work, "commit", "-qm", "later")
    _git(work, "push", "-q", str(origin), "main")
    second = _run_launcher(home, origin, TIP_HOOK)
    assert f"attempt={receipt['attempt_id']} outcome=fetched" in second.stdout
    assert _git(gov, "rev-parse", "HEAD").stdout.strip() == receipt["local_sha"]


def test_inherited_attempt_binding_is_never_trusted(tmp_path: Path) -> None:
    """A pre-seeded L9_GOV_REFRESH_ATTEMPT_ID from the environment is discarded."""
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    result = _run_launcher(
        home,
        None,
        TIP_HOOK,
        extra={"L9_GOV_REFRESH_ATTEMPT_ID": "forged", "L9_GOV_REFRESH_OUTCOME": "fetched"},
    )
    # Origin untrusted without the seam → no refresh, and the forged binding is gone.
    assert "hook file absent" in result.stderr
    assert not _tip_present(gov)
    hooks = gov / HOOKS_REL
    (hooks / TIP_HOOK).write_text(
        "#!/usr/bin/env bash\n" + ECHO_BINDING,
        encoding="utf-8",
    )
    result = _run_launcher(
        home,
        None,
        TIP_HOOK,
        extra={"L9_GOV_REFRESH_ATTEMPT_ID": "forged", "L9_GOV_REFRESH_OUTCOME": "fetched"},
    )
    assert "attempt=unset outcome=origin-untrusted" in result.stdout
