"""Claude Code capability-friction contract.

The vendor permission layer is not an L9 safety boundary. Safe edits, canonical
memory operations, and read-only inspection should not prompt; L9 policy still
decides whether each governed effect may proceed. Known GraphQL-backed GitHub
commands and raw publication writes must not be standing approvals.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "environment/agents/adapters/claude-code/settings.template.json"
PROJECTED = ROOT / ".claude/settings.json"
PREFLIGHT = ROOT / "environment/agents/adapters/claude-code/hooks/bootstrap_capability_preflight.sh"
GRAPHQL = ROOT / "ops/scripts/lib/gh_graphql.sh"


def _settings(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_safe_edit_and_read_envelope_is_no_prompt() -> None:
    allow = set(_settings(TEMPLATE)["permissions"]["allow"])  # type: ignore[index]
    required = {
        "Edit",
        "Write",
        "NotebookEdit",
        "Bash(git status:*)",
        "Bash(git diff:*)",
        "Bash(git log:*)",
        "Bash(git show:*)",
        "Bash(git rev-parse:*)",
        "Bash(git merge-base:*)",
        "Bash(git remote get-url:*)",
        "Bash(git ls-files:*)",
        "Bash(git cat-file:*)",
        "Bash(gh api --method GET:*)",
        "Bash(gh run list:*)",
        "Bash(gh run view:*)",
        "Bash(make pr:*)",
    }
    assert required <= allow


def test_canonical_memory_operations_are_no_prompt() -> None:
    allow = set(_settings(TEMPLATE)["permissions"]["allow"])  # type: ignore[index]
    required = {
        "mcp__l9-graphite-memory__memory.health",
        "mcp__l9-graphite-memory__memory.search",
        "mcp__l9-graphite-memory__memory.hydrate",
        "mcp__l9-graphite-memory__memory.conflicts",
        "mcp__l9-graphite-memory__memory.phase_lock",
        "mcp__l9-graphite-memory__memory.write_governed",
        "mcp__l9-graphite-memory__memory.close",
    }
    assert required <= allow


def test_graphql_and_raw_publish_are_not_standing_approvals() -> None:
    allow = set(_settings(TEMPLATE)["permissions"]["allow"])  # type: ignore[index]
    forbidden = {
        "Bash(git push:*)",
        "Bash(gh pr create:*)",
        "Bash(gh pr view:*)",
        "Bash(gh pr list:*)",
        "Bash(gh pr checks:*)",
        "Bash(gh pr merge:*)",
        "Bash(gh repo view:*)",
        "Bash(gh api --method POST:*)",
        "Bash(gh api -X POST:*)",
    }
    assert allow.isdisjoint(forbidden)


def test_preflight_is_registered_and_projects_without_drift() -> None:
    template = _settings(TEMPLATE)
    projected = _settings(PROJECTED)
    expected = {key: value for key, value in template.items() if not key.startswith("_")}
    assert projected == expected

    groups = template["hooks"]["SessionStart"]  # type: ignore[index]
    commands = [
        hook["command"]
        for group in groups
        for hook in group.get("hooks", [])
        if isinstance(hook, dict)
    ]
    assert any("bootstrap_capability_preflight.sh" in command for command in commands)
    assert PREFLIGHT.is_file()


def test_preflight_routes_platform_helpers_to_l9_owners() -> None:
    text = PREFLIGHT.read_text(encoding="utf-8")
    assert "Do not invoke Register Repo Root" in text
    assert "canonical l9-graphite-memory control plane" in text
    assert "memory.phase_lock then memory.write_governed" in text
    assert "Do not invoke Send Later" in text
    assert "publication is make pr only" in text
    assert "Do not invoke Add Repo for this repository at SessionStart" in text
    assert "genuinely different repository" in text
    assert "access=push" not in text
    assert "graphiti_memory_client.py" not in text


def test_primary_checkout_does_not_probe_or_request_add_repo(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/Quantum-L9/example-repo.git"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh_log = tmp_path / "gh.log"
    gh = bin_dir / "gh"
    gh.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> {gh_log!s}\nexit 99\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)

    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(workspace)
    env["CLAUDE_CODE_REMOTE"] = "true"
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    proc = subprocess.run(
        ["bash", str(PREFLIGHT)],
        cwd=workspace,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "primary workspace GitHub repository: Quantum-L9/example-repo" in context
    assert "Repository scope: PRIMARY_CHECKOUT" in context
    assert "Do not invoke Add Repo for this repository at SessionStart" in context
    assert not gh_log.exists(), "SessionStart must not probe GitHub just to validate primary scope"


def test_hosted_surface_short_circuits_graphql_without_executing_gh(tmp_path: Path) -> None:
    log = tmp_path / "gh.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> {log!s}\nexit 99\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    script = f"""
set -u
export PATH={bin_dir!s}:$PATH
export CLAUDE_CODE_REMOTE=true
source {GRAPHQL!s}
rc1=0
GH_GRAPHQL_NOTED=1
gh_graphql pr view --json number >/dev/null 2>/dev/null || rc1=$?
rc2=0
gh pr create --title x >/dev/null 2>/dev/null || rc2=$?
printf '%s %s %s\\n' "$GH_GRAPHQL_UNSUPPORTED" "$rc1" "$rc2"
"""
    proc = subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    flag, rc1, rc2 = proc.stdout.strip().split()
    assert flag == "1"
    assert int(rc1) != 0
    assert int(rc2) != 0
    assert not log.exists(), "hosted GraphQL guard still executed gh"


def test_rest_get_still_passes_through_graphql_guard(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text(
        '#!/usr/bin/env bash\n[ "$1 $2 $3" = "api --method GET" ] || exit 98\nprintf \'ok\\n\'\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)

    script = f"""
set -e
export PATH={bin_dir!s}:$PATH
export CLAUDE_CODE_REMOTE=true
source {GRAPHQL!s}
gh api --method GET repos/Quantum-L9/Cursor-Governance
"""
    proc = subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"
