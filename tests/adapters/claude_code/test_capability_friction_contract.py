"""Claude Code capability-friction contract.

The vendor permission layer is not an L9 safety boundary. Safe edits and
read-only inspection should not prompt; L9 PreToolUse gates still decide every
managed effect. Conversely, known GraphQL-backed GitHub commands and raw
publication writes must not be advertised as standing approvals.
"""

from __future__ import annotations

import json
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
    assert "Do not invoke Add Memory" in text
    assert "Do not invoke Send Later" in text
    assert "publication is make pr only" in text
    assert "access=push" in text
    assert "second clone" in text


def test_hosted_surface_short_circuits_graphql_without_executing_gh(tmp_path: Path) -> None:
    log = tmp_path / "gh.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> {log!s}\n"
        "exit 99\n",
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
        "#!/usr/bin/env bash\n"
        "[ \"$1 $2 $3\" = \"api --method GET\" ] || exit 98\n"
        "printf 'ok\\n'\n",
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
