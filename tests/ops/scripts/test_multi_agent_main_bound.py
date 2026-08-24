"""Conformance suite for the L9 Multi-Agent Main-Bound Execution Contract.

Proves the §21 minimum conformance scenarios against real git repositories and
the real gate scripts. The contract's operative model is:

    Graphiti shares knowledge. Worktrees isolate writers. Branches isolate
    history. Git detects code collisions. PR gates serialize integration.
    main is canonical.

Each test names the invariant (E1..E12) it locks in.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
MAIN_BOUND = SCRIPTS / "main_bound_check.py"
OVERLAP = SCRIPTS / "pr_overlap_check.py"
TASK_START = SCRIPTS / "agent_worktree_start.sh"
CLAUDE = ROOT / "environment" / "agents" / "adapters" / "claude-code"


def git_in(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )


def run_gate(script: Path, repo: Path, base: str, **env: str) -> subprocess.CompletedProcess[str]:
    environ = {**os.environ, "PATH": os.environ.get("PATH", "")}
    environ.update(env)
    return subprocess.run(
        [sys.executable, str(script), "--workspace", str(repo), "--base", base],
        capture_output=True,
        text=True,
        check=False,
        env=environ,
    )


@pytest.fixture
def upstream(tmp_path: Path) -> Path:
    """A bare 'origin' with one commit on main, plus a shared source file."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    seed.mkdir()
    git_in(seed, "init", "-q")
    git_in(seed, "config", "user.email", "t@example.com")
    git_in(seed, "config", "user.name", "t")
    (seed / "shared.py").write_text(
        "\n".join(f"line_{n} = {n}" for n in range(1, 41)) + "\n", encoding="utf-8"
    )
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    git_in(seed, "add", "shared.py", "README.md")
    git_in(seed, "commit", "-q", "-m", "seed")
    git_in(seed, "branch", "-M", "main")
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(seed), str(origin)], check=True, capture_output=True
    )
    return origin


def clone_agent(upstream: Path, tmp_path: Path, name: str) -> Path:
    """An agent's own checkout of origin (stands in for a dedicated worktree)."""
    path = tmp_path / name
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(path)], check=True, capture_output=True
    )
    git_in(path, "config", "user.email", f"{name}@example.com")
    git_in(path, "config", "user.name", name)
    return path


def edit_line(repo: Path, lineno: int, text: str) -> None:
    path = repo / "shared.py"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[lineno - 1] = text
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def start_task(repo: Path, agent: str, task: str, lineno: int, text: str) -> str:
    branch = f"agent/{agent}/{task}"
    git_in(repo, "fetch", "-q", "origin", "main")
    base_sha = git_in(repo, "rev-parse", "origin/main").stdout.strip()
    git_in(repo, "checkout", "-q", "-b", branch, base_sha)
    edit_line(repo, lineno, text)
    git_in(repo, "add", "shared.py")
    git_in(repo, "commit", "-q", "-m", f"{agent} {task}")
    return base_sha


# --- E2/E3/E4: main binding, no direct main push, PRs target main ------------


def test_two_agents_different_files_both_publishable(upstream: Path, tmp_path: Path) -> None:
    """Two agents, different files -> both work concurrently and both may publish.

    No global repository lock exists, and neither agent's progress depends on the
    other's (E1, E2, E12).
    """
    a = clone_agent(upstream, tmp_path, "agent_a")
    b = clone_agent(upstream, tmp_path, "agent_b")

    for repo, agent, filename in ((a, "claude", "a_only.py"), (b, "cursor", "b_only.py")):
        git_in(repo, "fetch", "-q", "origin", "main")
        git_in(repo, "checkout", "-q", "-b", f"agent/{agent}/T1", "origin/main")
        (repo / filename).write_text("x = 1\n", encoding="utf-8")
        git_in(repo, "add", filename)
        git_in(repo, "commit", "-q", "-m", f"{agent} work")

    for repo in (a, b):
        result = run_gate(MAIN_BOUND, repo, "origin/main")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "PASS: main-bound" in result.stdout


def test_task_start_from_non_main_ancestry_is_blocked(upstream: Path, tmp_path: Path) -> None:
    """E2: a branch that does not descend from origin/main cannot publish."""
    repo = clone_agent(upstream, tmp_path, "agent_a")
    git_in(repo, "fetch", "-q", "origin", "main")
    # An orphan branch shares no history with main: ancestry is unprovable.
    git_in(repo, "checkout", "-q", "--orphan", "agent/claude/T9")
    (repo / "rogue.py").write_text("x = 1\n", encoding="utf-8")
    git_in(repo, "add", "rogue.py")
    git_in(repo, "commit", "-q", "-m", "orphan")

    result = run_gate(MAIN_BOUND, repo, "origin/main")
    assert result.returncode == 1
    assert "no merge base" in result.stdout


def test_direct_main_push_is_blocked(upstream: Path, tmp_path: Path) -> None:
    """E3: agents do not publish an integration branch directly."""
    repo = clone_agent(upstream, tmp_path, "agent_a")
    git_in(repo, "checkout", "-q", "main")
    result = run_gate(MAIN_BOUND, repo, "origin/main")
    assert result.returncode == 1
    assert "must not push an integration branch directly" in result.stdout


def test_non_main_base_requires_explicit_authorization(upstream: Path, tmp_path: Path) -> None:
    """E4: ordinary PRs target main; another base is an authorized exception."""
    repo = clone_agent(upstream, tmp_path, "agent_a")
    start_task(repo, "claude", "T1", 3, "line_3 = 'claude'")
    git_in(repo, "branch", "agent/other/T7", "origin/main")

    denied = run_gate(MAIN_BOUND, repo, "agent/other/T7")
    assert denied.returncode == 1
    assert "not origin/main (E4)" in denied.stdout

    allowed = run_gate(
        MAIN_BOUND, repo, "agent/other/T7", L9_TASK_BASE_AUTHORIZED="stacked on sibling"
    )
    assert allowed.returncode == 0, allowed.stdout
    assert "authorized" in allowed.stdout

    stacked = run_gate(MAIN_BOUND, repo, "agent/other/T7", PR_STACK="auto")
    assert stacked.returncode == 0, stacked.stdout


def test_campaign_integration_base_is_self_declaring(upstream: Path, tmp_path: Path) -> None:
    """E4 exception: campaign PRs target campaign/<id> by standing policy.

    Rules 48 and 88 require campaign execution to open against the campaign
    integration branch, and that path sets no extra env. The `campaign/` base
    name is itself the declaration, so campaign publishing keeps working while
    an arbitrary non-main base still needs a stated reason.
    """
    repo = clone_agent(upstream, tmp_path, "agent_a")
    start_task(repo, "claude", "T1", 3, "line_3 = 'claude'")
    git_in(repo, "branch", "campaign/2026-08-alpha", "origin/main")
    git_in(repo, "branch", "feat/unrelated", "origin/main")

    ok = run_gate(MAIN_BOUND, repo, "campaign/2026-08-alpha")
    assert ok.returncode == 0, ok.stdout
    assert "campaign integration branch" in ok.stdout

    # A bare "campaign/" prefix is not a campaign id, and an unrelated branch
    # is still refused without an explicit reason.
    denied = run_gate(MAIN_BOUND, repo, "feat/unrelated")
    assert denied.returncode == 1
    assert "not origin/main (E4)" in denied.stdout


def test_rewritten_branch_base_is_blocked(upstream: Path, tmp_path: Path) -> None:
    """E2: a branch re-pointed away from its recorded task base fails closed."""
    repo = clone_agent(upstream, tmp_path, "agent_a")
    base_sha = start_task(repo, "claude", "T1", 3, "line_3 = 'claude'")

    meta = repo / ".l9" / "agent-tasks"
    meta.mkdir(parents=True)
    (meta / "claude__T1.json").write_text(
        json.dumps({"branch": "agent/claude/T1", "base_sha": base_sha}), encoding="utf-8"
    )
    ok = run_gate(MAIN_BOUND, repo, "origin/main")
    assert ok.returncode == 0, ok.stdout
    assert "recorded task base" in ok.stdout

    # Now claim a base_sha that is not in this branch's history.
    (meta / "claude__T1.json").write_text(
        json.dumps({"branch": "agent/claude/T1", "base_sha": "0" * 40}), encoding="utf-8"
    )
    bad = run_gate(MAIN_BOUND, repo, "origin/main")
    assert bad.returncode == 1
    assert "re-pointed after task start" in bad.stdout


# --- E5/E12: collision decided by Git, not by filename ----------------------


def test_same_file_disjoint_hunks_merge_cleanly(upstream: Path, tmp_path: Path) -> None:
    """Two agents, same file, non-conflicting hunks -> Git says mergeable.

    No global lock is required and no serialization is imposed: the merge probe,
    not the filename, is authoritative (E5, E11).
    """
    a = clone_agent(upstream, tmp_path, "agent_a")
    b = clone_agent(upstream, tmp_path, "agent_b")
    start_task(a, "claude", "T1", 3, "line_3 = 'claude'")
    start_task(b, "cursor", "T2", 37, "line_37 = 'cursor'")

    # Publish agent b's branch to origin, then probe agent a's branch against it.
    git_in(b, "push", "-q", "origin", "agent/cursor/T2")
    git_in(a, "fetch", "-q", "origin", "agent/cursor/T2")
    probe = subprocess.run(
        ["git", "-C", str(a), "merge-tree", "--write-tree", "--name-only", "HEAD", "FETCH_HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 0, f"disjoint hunks must merge cleanly:\n{probe.stdout}"


def test_same_file_conflicting_hunks_are_detected(upstream: Path, tmp_path: Path) -> None:
    """Conflicting hunks -> Git detects the collision; both branches survive.

    Isolated work is preserved on each side; only publication is affected (E5).
    """
    a = clone_agent(upstream, tmp_path, "agent_a")
    b = clone_agent(upstream, tmp_path, "agent_b")
    start_task(a, "claude", "T1", 20, "line_20 = 'claude'")
    start_task(b, "cursor", "T2", 20, "line_20 = 'cursor'")

    git_in(b, "push", "-q", "origin", "agent/cursor/T2")
    git_in(a, "fetch", "-q", "origin", "agent/cursor/T2")
    probe = subprocess.run(
        ["git", "-C", str(a), "merge-tree", "--write-tree", "--name-only", "HEAD", "FETCH_HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 1, "same-hunk edits must be reported as a conflict"
    assert "shared.py" in probe.stdout

    # Both agents still hold their own committed work.
    assert "claude" in (a / "shared.py").read_text(encoding="utf-8")
    assert "cursor" in (b / "shared.py").read_text(encoding="utf-8")


# --- E6: telemetry failure denies autonomous publication --------------------


def test_undeterminable_collision_state_blocks_autonomous_publication(
    upstream: Path, tmp_path: Path
) -> None:
    """E6: no gh -> collision state unknown -> publication denied, work intact."""
    repo = clone_agent(upstream, tmp_path, "agent_a")
    start_task(repo, "claude", "T1", 3, "line_3 = 'claude'")

    empty_path = tmp_path / "emptybin"
    empty_path.mkdir()
    result = run_gate(
        OVERLAP,
        repo,
        "origin/main",
        PATH=f"{empty_path}:/usr/bin:/bin",  # no gh on PATH
        L9_AUTONOMY_ENABLED="true",
    )
    assert result.returncode == 1, result.stdout
    assert "publication is denied" in result.stdout
    assert "Local work is unaffected" in result.stdout
    # The commit is untouched.
    assert git_in(repo, "rev-list", "--count", "origin/main..HEAD").stdout.strip() == "1"


def test_operator_may_override_telemetry_failure(upstream: Path, tmp_path: Path) -> None:
    """The fail-closed default is overridable, but only explicitly."""
    repo = clone_agent(upstream, tmp_path, "agent_a")
    start_task(repo, "claude", "T1", 3, "line_3 = 'claude'")
    empty_path = tmp_path / "emptybin2"
    empty_path.mkdir()
    result = run_gate(
        OVERLAP,
        repo,
        "origin/main",
        PATH=f"{empty_path}:/usr/bin:/bin",
        L9_AUTONOMY_ENABLED="true",
        PR_OVERLAP_TELEMETRY="open",
    )
    assert result.returncode == 0
    assert "PR_OVERLAP_TELEMETRY=open" in result.stdout


# --- E7/E8/E10: memory never gates repository mutation ----------------------


def test_no_agent_facing_force_lock_interface_exists() -> None:
    """E8: the --force memory-lock interface must not exist at all."""
    assert not (CLAUDE / "hooks" / "memory_lock.py").exists()
    for path in (CLAUDE / "hooks").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "--force" not in source, path.name


def test_contract_does_not_gate_repository_writes_on_phase_lock() -> None:
    """E7: no governed write may require a phase-lock."""
    contract = json.loads(
        (CLAUDE / "memory" / "memory-enforcement.contract.json").read_text(encoding="utf-8")
    )
    for rule in contract["governed_writes"]:
        assert rule["requires"] == ["session_prefetch"], rule["id"]
    assert "phase_lock" not in contract["preconditions"]


def test_schema_makes_phase_lock_unrepresentable() -> None:
    """E7: reintroducing the coupling must fail validation, not pass silently."""
    schema = json.loads(
        (CLAUDE / "memory" / "memory-enforcement.schema.json").read_text(encoding="utf-8")
    )
    requires = schema["properties"]["governed_writes"]["items"]["properties"]["requires"]
    assert requires["items"]["enum"] == ["session_prefetch"]
    assert "phase_lock" not in schema["properties"]["preconditions"]["properties"]


def test_gate_rejects_a_reintroduced_phase_lock_precondition() -> None:
    """E7 fail-closed: a non-conformant contract raises rather than enforcing."""
    import sys

    sys.path.insert(0, str(CLAUDE / "memory"))
    import memory_state as st

    with pytest.raises(ValueError, match="non-conformant precondition"):
        st.validate_requires({"id": "x", "requires": ["session_prefetch", "phase_lock"]})
    assert st.validate_requires({"id": "x", "requires": ["session_prefetch"]}) == [
        "session_prefetch"
    ]


def test_memory_write_by_one_agent_does_not_block_another_agent_coding(
    upstream: Path, tmp_path: Path
) -> None:
    """E10: memory activity is not a repository mutex.

    Nothing in the repository-write path reads memory conflict or lock state, so
    an agent writing memory cannot revoke another agent's authority to edit and
    publish. Proven structurally: the gates consult git only.
    """
    repo = clone_agent(upstream, tmp_path, "agent_a")
    start_task(repo, "claude", "T1", 3, "line_3 = 'claude'")

    for gate in (MAIN_BOUND, OVERLAP):
        source = gate.read_text(encoding="utf-8")
        assert "graphiti" not in source.lower(), f"{gate.name} must not consult memory"
        assert "memory_state" not in source, gate.name

    # And the gate still passes while a concurrent memory write would be in flight.
    result = run_gate(MAIN_BOUND, repo, "origin/main")
    assert result.returncode == 0, result.stdout


# --- E9: memory namespace is repository-scoped, not branch-scoped -----------


def test_memory_namespace_is_repository_scoped_not_branch_scoped() -> None:
    """E9: the namespace never derives from branch identity."""
    import sys

    sys.path.insert(0, str(CLAUDE / "memory"))
    import memory_state as st

    contract = st.load_contract()
    namespaces = contract["memory"]["default_namespaces"]
    assert namespaces == ["cursor-governance"]
    forbidden = {"main", "master", "default", "test", ""}
    assert not (set(namespaces) & forbidden)

    previous = os.environ.get("L9_MEMORY_NAMESPACES")
    try:
        os.environ.pop("L9_MEMORY_NAMESPACES", None)
        first = st.resolve_namespaces(contract)
        # Namespace resolution takes no branch input at all.
        assert first == st.resolve_namespaces(contract)
    finally:
        if previous is not None:
            os.environ["L9_MEMORY_NAMESPACES"] = previous


# --- E1: shared writable worktrees are refused ------------------------------


def test_task_start_refuses_an_existing_worktree_path(upstream: Path, tmp_path: Path) -> None:
    """E1: two agents cannot be handed the same writable worktree."""
    repo = clone_agent(upstream, tmp_path, "agent_a")
    occupied = tmp_path / "occupied"
    occupied.mkdir()

    result = subprocess.run(
        [
            "bash",
            str(TASK_START),
            "--agent-id",
            "claude",
            "--task-id",
            "T1",
            "--worktree",
            str(occupied),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "already exists" in (result.stdout + result.stderr)


def test_task_start_requires_identity_and_main_ancestry(upstream: Path, tmp_path: Path) -> None:
    """E1/E2: agent identity, task identity, and main ancestry are mandatory."""
    repo = clone_agent(upstream, tmp_path, "agent_a")

    missing = subprocess.run(
        ["bash", str(TASK_START), "--agent-id", "claude"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "--task-id is required" in (missing.stdout + missing.stderr)

    unauthorized = subprocess.run(
        [
            "bash",
            str(TASK_START),
            "--agent-id",
            "claude",
            "--task-id",
            "T1",
            "--base",
            "origin/other",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_TASK_BASE_AUTHORIZED": ""},
    )
    assert unauthorized.returncode != 0
    # The refusal must be about ancestry authorization, not an incidental fetch
    # error -- the intent check runs before any network round trip.
    assert "is not origin/main" in (unauthorized.stdout + unauthorized.stderr)

    # With the exception stated, the base is accepted (it then fails later, on
    # the missing remote ref -- a different, honest failure).
    authorized = subprocess.run(
        [
            "bash",
            str(TASK_START),
            "--agent-id",
            "claude",
            "--task-id",
            "T1",
            "--base",
            "origin/other",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_TASK_BASE_AUTHORIZED": "stacked campaign"},
    )
    combined = authorized.stdout + authorized.stderr
    assert "non-main ancestry authorized" in combined
    assert "is not origin/main" not in combined


def _write_tip_stub(path: Path, *, tip: str, sha: str, reason: str, exit_code: int = 0) -> None:
    path.write_text(
        "\n".join(
            [
                "import sys",
                f"print('STACK_TIP={tip}')",
                f"print('STACK_TIP_SHA={sha}')",
                f"print('REASON={reason}')",
                f"raise SystemExit({exit_code})",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_task_start_empty_pr_stack_stays_on_origin_main(upstream: Path, tmp_path: Path) -> None:
    """Empty PR_STACK keeps origin/main and does not consult the resolver."""
    repo = clone_agent(upstream, tmp_path, "agent_empty_stack")
    stub = tmp_path / "refuse_if_called.py"
    stub.write_text(
        "raise SystemExit('resolver must not run when PR_STACK is empty')\n",
        encoding="utf-8",
    )
    occupied = tmp_path / "occupied-empty"
    occupied.mkdir()
    result = subprocess.run(
        [
            "bash",
            str(TASK_START),
            "--agent-id",
            "claude",
            "--task-id",
            "T-empty",
            "--worktree",
            str(occupied),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PR_STACK": "", "L9_STACK_TIP_RESOLVER": str(stub)},
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "resolver must not run" not in combined
    assert "already exists" in combined


def test_task_start_unset_pr_stack_defaults_to_auto(upstream: Path, tmp_path: Path) -> None:
    """Unset PR_STACK matches Makefile default auto and consults the resolver."""
    repo = clone_agent(upstream, tmp_path, "agent_unset_stack")
    stub = tmp_path / "unique_tip_unset.py"
    _write_tip_stub(stub, tip="feat/stack-safe-merge", sha="dd" * 20, reason="unique_chain_tip")
    env = {**os.environ, "L9_STACK_TIP_RESOLVER": str(stub)}
    env.pop("PR_STACK", None)
    result = subprocess.run(
        ["bash", str(TASK_START), "--agent-id", "claude", "--task-id", "T-unset"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "PR_STACK=auto resolved stack tip origin/feat/stack-safe-merge" in combined
    assert "is not origin/main" not in combined


def test_task_start_pr_stack_auto_uses_resolver_tip(upstream: Path, tmp_path: Path) -> None:
    """PR_STACK=auto without --base implies auth for the unique resolver tip."""
    repo = clone_agent(upstream, tmp_path, "agent_auto_tip")
    stub = tmp_path / "unique_tip.py"
    _write_tip_stub(stub, tip="feat/stack-safe-merge", sha="cc" * 20, reason="unique_chain_tip")
    result = subprocess.run(
        ["bash", str(TASK_START), "--agent-id", "claude", "--task-id", "T-auto"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PR_STACK": "auto", "L9_STACK_TIP_RESOLVER": str(stub)},
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "PR_STACK=auto resolved stack tip origin/feat/stack-safe-merge" in combined
    assert "resolver stack tip (PR_STACK=auto" in combined
    assert "is not origin/main" not in combined
    assert "cannot fetch origin/feat/stack-safe-merge" in combined or "cannot fetch" in combined


def test_task_start_pr_stack_auto_siblings_exit_closed(upstream: Path, tmp_path: Path) -> None:
    """PR_STACK=auto with sibling chains fails closed and names both heads."""
    repo = clone_agent(upstream, tmp_path, "agent_siblings")
    stub = tmp_path / "siblings.py"
    stub.write_text(
        "import sys\n"
        "print('FAIL: sibling open-PR chains target main: "
        "#10:feat/one, #11:feat/two', file=sys.stderr)\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", str(TASK_START), "--agent-id", "claude", "--task-id", "T-sib"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PR_STACK": "auto", "L9_STACK_TIP_RESOLVER": str(stub)},
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "feat/one" in combined
    assert "feat/two" in combined
    assert "could not resolve a unique stack tip" in combined
