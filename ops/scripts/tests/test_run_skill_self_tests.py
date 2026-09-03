"""Contract tests for the canonical skill self-test adapter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_skill_self_tests import ContractError, run_self_tests, validate_contract  # noqa: E402


def _skill(root: Path, name: str, script_name: str = "self_test.py", body: str = "raise SystemExit(0)\n") -> None:
    skill = root / "skills" / name
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        "description: validate a fixture-backed skill contract deterministically before publication. use when exercising the test adapter in repository contract tests.\n"
        "---\n",
        encoding="utf-8",
    )
    (scripts / script_name).write_text(body, encoding="utf-8")


def _contract(*roots: str) -> dict:
    return {
        "skill_self_test_roots": [f"skills/{root}" for root in roots],
        "suites": [
            {
                "id": "skill-contracts",
                "kind": "command_sequence",
                "owned_paths": ["skills"],
            }
        ],
    }


def test_registered_roots_cover_every_discovered_self_test(tmp_path: Path) -> None:
    _skill(tmp_path, "l9-alpha")
    _skill(tmp_path, "l9-beta", "pack_self_test.py")
    tests = validate_contract(tmp_path, _contract("l9-alpha", "l9-beta"))
    assert [path.name for path in tests] == ["self_test.py", "pack_self_test.py"]


def test_unregistered_skill_self_test_fails_closed(tmp_path: Path) -> None:
    _skill(tmp_path, "l9-alpha")
    _skill(tmp_path, "l9-new")
    with pytest.raises(ContractError, match="unregistered skill self-test roots"):
        validate_contract(tmp_path, _contract("l9-alpha"))


def test_registered_root_without_self_test_fails_closed(tmp_path: Path) -> None:
    _skill(tmp_path, "l9-alpha")
    missing = tmp_path / "skills" / "l9-missing"
    missing.mkdir(parents=True)
    (missing / "SKILL.md").write_text("placeholder\n", encoding="utf-8")
    with pytest.raises(ContractError, match="have no .*self_test.py"):
        validate_contract(tmp_path, _contract("l9-alpha", "l9-missing"))


def test_each_self_test_runs_in_a_fresh_process(tmp_path: Path) -> None:
    pid_file = tmp_path / "pids.txt"
    script = (
        "import os\n"
        "from pathlib import Path\n"
        f"Path({str(pid_file)!r}).open('a', encoding='utf-8').write(str(os.getpid()) + '\\n')\n"
    )
    _skill(tmp_path, "l9-alpha", body=script)
    _skill(tmp_path, "l9-beta", body=script)
    tests = validate_contract(tmp_path, _contract("l9-alpha", "l9-beta"))
    assert run_self_tests(tmp_path, tests) == 0
    pids = pid_file.read_text(encoding="utf-8").splitlines()
    assert len(pids) == 2
    assert len(set(pids)) == 2
