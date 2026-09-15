"""Provider egress firewall: merge-blocking since stage C11 (allowlist mode = enforce)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "validate_memory_egress_boundary.py"

spec = importlib.util.spec_from_file_location("validate_memory_egress_boundary", SCRIPT)
assert spec and spec.loader
scanner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scanner  # dataclasses resolve annotations via sys.modules
spec.loader.exec_module(scanner)

TODAY = datetime(2026, 9, 5, tzinfo=UTC)


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "ops" / "graphiti").mkdir(parents=True)
    (tmp_path / "ops" / "graphiti" / "legacy.py").write_text(
        'call_tool("add_memory", payload)\nsearch_memory_facts\n', encoding="utf-8"
    )
    (tmp_path / "ops" / "memory").mkdir()
    (tmp_path / "ops" / "memory" / "clean.py").write_text("hydrate()\n", encoding="utf-8")
    (tmp_path / "ops" / "new_bypass.py").write_text("GRAPHITI_MCP_TOKEN\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "prose.md").write_text("add_memory is retired\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("add_memory\n", encoding="utf-8")
    return tmp_path


def _allowlist(entries: list[dict[str, str]]) -> tuple[Any, ...]:
    return tuple(scanner.AllowlistEntry(**entry) for entry in entries)


def test_production_scope_excludes_prose_and_tests(tmp_path: Path) -> None:
    findings, expired = scanner.scan(_tree(tmp_path), (), today=TODAY)
    paths = {item.path for item in findings}
    assert paths == {"ops/graphiti/legacy.py", "ops/new_bypass.py"}
    assert expired == []
    assert {item.token for item in findings} == {
        "add_memory",
        "search_memory_facts",
        "GRAPHITI_MCP_TOKEN",
    }


def test_exact_allowlist_entry_covers_only_its_path(tmp_path: Path) -> None:
    allow = _allowlist(
        [
            {
                "path": "ops/graphiti/legacy.py",
                "reason": "r",
                "retire_at_stage": "C11",
                "expires": "2026-12-31",
            }
        ]
    )
    findings, _ = scanner.scan(_tree(tmp_path), allow, today=TODAY)
    by_path = {item.path: item.allowlisted for item in findings}
    assert by_path["ops/graphiti/legacy.py"] is True
    assert by_path["ops/new_bypass.py"] is False


def test_expired_allowlist_entry_no_longer_covers(tmp_path: Path) -> None:
    allow = _allowlist(
        [
            {
                "path": "ops/graphiti/legacy.py",
                "reason": "r",
                "retire_at_stage": "C11",
                "expires": "2026-01-01",
            }
        ]
    )
    findings, expired = scanner.scan(_tree(tmp_path), allow, today=TODAY)
    assert [entry.path for entry in expired] == ["ops/graphiti/legacy.py"]
    assert all(item.allowlisted is False for item in findings)


def test_warning_mode_exits_zero_and_enforce_exits_one(tmp_path: Path, capsys) -> None:
    findings, expired = scanner.scan(_tree(tmp_path), (), today=TODAY)
    assert scanner.report(findings, expired, enforce=False, as_json=False) == 0
    assert "warning mode" in capsys.readouterr().out
    assert scanner.report(findings, expired, enforce=True, as_json=True) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["verdict"] == "FAIL" and summary["findings_unlisted"] == 3


def test_enforce_passes_a_clean_tree(tmp_path: Path) -> None:
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "clean.py").write_text("hydrate()\n", encoding="utf-8")
    findings, expired = scanner.scan(tmp_path, (), today=TODAY)
    assert scanner.report(findings, expired, enforce=True, as_json=True) == 0


def test_real_tree_inventory_is_fully_allowlisted_and_unexpired() -> None:
    """Enforce-mode contract (stage C11): every remaining site is a negative check.

    The inventory shrank stage by stage; since C11 no code path that calls a
    provider survives, so an unlisted finding is a regression and an expired
    entry is a finding.
    """

    mode, allowlist = scanner.load_allowlist()
    assert mode == "enforce"
    findings, expired = scanner.scan(ROOT, allowlist)
    unlisted = sorted({item.path for item in findings if not item.allowlisted})
    assert unlisted == [], f"new provider egress outside the allowlist: {unlisted}"
    assert expired == []
    inventoried = {item.path for item in findings if item.allowlisted}
    # The legacy client is gone (tombstone at C11, deleted at C15) and so is the shadow reader.
    assert "ops/graphiti/graphiti_memory_client.py" not in inventoried
    assert "ops/graphiti/hydration/compile_session_packet.py" not in inventoried
    assert "ops/graphiti/hydration/close_session.py" not in inventoried
    assert "ops/graphiti/hydration/pickup_write.py" not in inventoried
    # Nothing left in the inventory is a code path: only checks, fixtures,
    # the scanner itself, and operator-owned files.
    for entry in allowlist:
        assert entry.retire_at_stage in {"never", "operator"}, entry.path


def test_legacy_provider_modules_are_gone() -> None:
    for rel in (
        "ops/graphiti/group_resolver.py",
        "ops/graphiti/episode_contract.py",
        "ops/graphiti/graphiti_env_loader.py",
        "ops/graphiti/graphiti.env.defaults",
        "ops/graphiti/graphiti.env.example",
        "ops/graphiti/outcome_label.py",
        "ops/graphiti/prune.py",
        "ops/graphiti/mcp.json.example",
        "ops/scripts/transcript_distiller.py",
        "ops/scripts/init_graphiti_machine_env.sh",
    ):
        assert not (ROOT / rel).exists(), f"{rel} must stay deleted (stage C11)"
    for rel in (
        "ops/graphiti/graphiti_memory_client.py",
        "ops/graphiti/distill_queue",
        "ops/scripts/run_distiller.sh",
        ".github/workflows/memory-distill.yml",
        "ops/graphiti/hydration/openai_fixed_host.py",
        "ops/graphiti/hydration/openai_key.py",
        "ops/graphiti/hydration/promotion_rules.yaml",
        "ops/graphiti/hydration/resume_signal_scorer.py",
    ):
        assert not (ROOT / rel).exists(), f"{rel} must stay deleted (stage C15, ADR-0033)"


def test_ops_memory_is_provider_free() -> None:
    _mode, allowlist = scanner.load_allowlist()
    findings, _ = scanner.scan(ROOT, allowlist)
    assert not [item for item in findings if item.path.startswith("ops/memory/")]


def test_cli_entrypoint_runs_in_enforce_mode_and_passes() -> None:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--json"], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["mode"] == "enforce"
    # Listed negative checks keep the scanner's WARN vocabulary; what enforce
    # mode guarantees is that nothing unlisted or expired survives.
    assert summary["verdict"] in {"PASS", "WARN"}
    assert summary["findings_unlisted"] == 0
    assert summary["forbidden_tokens"] == list(scanner.FORBIDDEN_TOKENS)


@pytest.mark.parametrize("token", scanner.FORBIDDEN_TOKENS)
def test_every_forbidden_token_from_the_plan_is_scanned(token: str) -> None:
    assert scanner._TOKEN_RE.search(f"x {token} y")


# --------------------------------------------------------------------------- #
# Lane discipline (ADR-0033 / INV-03b)
# --------------------------------------------------------------------------- #


def _lane_tree(tmp_path: Path, files: dict[str, str]) -> Path:
    for relative, body in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return tmp_path


HOOK_OK = (
    "from ops.memory.control_plane_client import MemoryControlPlaneClient\n"
    "client = MemoryControlPlaneClient(surface='cursor-session-end')\n"
)
HOOK_IMPORTS_PACKAGE = HOOK_OK + "from l9_graphite_memory.service import MemoryService\n"
HOOK_SPAWNS_CONSOLE = HOOK_OK + "subprocess.run(['l9-memory', 'write', fact])\n"
AGENT_OK = (
    "from ops.memory.runtime_binding import resolve_runtime_binding\n"
    "subprocess.run([str(resolve_runtime_binding().memory_cli), 'search', q])\n"
)
AGENT_CONSTRUCTS_CLIENT = "client = MemoryControlPlaneClient(surface='pe-sgd-ingest')\n"
AGENT_SPAWNS_OPERATOR = "subprocess.run([py, '-m', 'ops.memory.cli', 'write', fact])\n"

AGENT_PATH = "environment/program-execution/integrations/graphiti/context_reader.py"


def _lanes(root: Path, agent: frozenset[str] = frozenset({AGENT_PATH})) -> list[tuple[str, str]]:
    return [(f.path, f.rule) for f in scanner.scan_lanes(root, agent)]


def test_lane_scan_passes_when_each_lane_uses_its_own_door(tmp_path: Path) -> None:
    root = _lane_tree(
        tmp_path,
        {
            "ops/graphiti/hydration/close_session.py": HOOK_OK,
            "ops/hooks/pr_publish_memory_write.py": "argv = ['-m', 'ops.memory.cli', 'write']\n",
            AGENT_PATH: AGENT_OK,
            # The binding may do both; it is the door.
            "ops/memory/runtime_binding.py": "from l9_graphite_memory import x\n'l9-memory'\n",
        },
    )
    assert _lanes(root) == []


def test_hook_lane_may_not_import_the_package_or_spawn_the_console_script(
    tmp_path: Path,
) -> None:
    root = _lane_tree(
        tmp_path,
        {
            "ops/graphiti/hydration/a.py": HOOK_IMPORTS_PACKAGE,
            "environment/agents/adapters/claude-code/hooks/b.py": HOOK_SPAWNS_CONSOLE,
        },
    )
    rules = dict(_lanes(root))
    assert rules["ops/graphiti/hydration/a.py"].startswith(
        "hook-lane module imports l9_graphite_memory"
    )
    assert rules["environment/agents/adapters/claude-code/hooks/b.py"].startswith(
        "hook-lane module spawns the l9-memory console script"
    )


def test_agent_lane_may_not_construct_the_hook_client_or_spawn_the_operator_cli(
    tmp_path: Path,
) -> None:
    root = _lane_tree(
        tmp_path, {AGENT_PATH: AGENT_OK + AGENT_CONSTRUCTS_CLIENT + AGENT_SPAWNS_OPERATOR}
    )
    rules = sorted(rule for _, rule in _lanes(root))
    assert rules == [
        "agent-lane module constructs the hook client",
        "agent-lane module spawns the operator CLI (ops.memory.cli)",
    ]


def test_lane_scan_judges_code_not_prose_or_tests(tmp_path: Path) -> None:
    root = _lane_tree(
        tmp_path,
        {
            # Docstring and comment mention the other door: that is documentation.
            "ops/graphiti/hydration/c.py": (
                '"""Never spawn "l9-memory" here; import l9_graphite_memory is the binding."""\n'
                "# from l9_graphite_memory import x\n" + HOOK_OK
            ),
            # Colocated tests fake both doors on purpose.
            "ops/graphiti/hydration/test_c.py": HOOK_SPAWNS_CONSOLE + HOOK_IMPORTS_PACKAGE,
            # Prose and non-lane roots are out of scope.
            "docs/lanes.md": HOOK_SPAWNS_CONSOLE,
            "ops/scripts/tool.py": HOOK_SPAWNS_CONSOLE,
        },
    )
    assert _lanes(root) == []


def test_lane_violation_fails_even_without_enforce(tmp_path: Path, capsys) -> None:
    root = _lane_tree(tmp_path, {"ops/graphiti/hydration/a.py": HOOK_IMPORTS_PACKAGE})
    lanes = scanner.scan_lanes(root, frozenset())
    assert scanner.report([], [], enforce=False, as_json=True, lane_findings=lanes) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["verdict"] == "FAIL"
    assert summary["lane_findings"][0]["lane"] == "hook"
    assert scanner.report([], [], enforce=False, as_json=True) == 0


def test_agent_lane_callers_are_declared_in_the_envelope_registry() -> None:
    declared = scanner.load_agent_lane_callers()
    assert AGENT_PATH in declared
    for relative in declared:
        assert (ROOT / relative).is_file(), relative


def test_real_tree_has_no_lane_violation() -> None:
    assert scanner.scan_lanes(ROOT, scanner.load_agent_lane_callers()) == []
