"""Python-project observation versus repository policy.

The two were fused: an analyzer calling itself `python-project-contract-v1`
regex-searched for `>=X.Y`, substring-searched a stringified conftest, and
read `[tool.uv]` as a universal law about lockfiles. These tests pin the
separation and the UNKNOWN states that replace the silent passes.
"""

from __future__ import annotations

import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

from surface_analyzers.pyproject import (  # noqa: E402
    analyze,
    load_python_repo_policy,
)
from surface_analyzers.python_project import (  # noqa: E402
    normalize_pytest_addopts,
    parse_collection_guards,
    pytest_ignored_paths,
    python_floor,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- T-PY-001 .. T-PY-005: PEP 440 floor derivation ---


def test_simple_floor():
    assert python_floor(">=3.12").value == "3.12"


def test_bounded_floor():
    assert python_floor(">=3.12,<4").value == "3.12"


def test_compatible_release_floor():
    assert python_floor("~=3.12").value == "3.12"


def test_wildcard_equality_floor():
    assert python_floor("==3.12.*").value == "3.12"
    assert python_floor("==3.12.4").value == "3.12"


def test_highest_lower_bound_wins():
    assert python_floor(">=3.9,>=3.12").value == "3.12"


def test_upper_bound_alone_is_unknown():
    floor = python_floor("<4")
    assert floor.value is None
    assert floor.status == "unknown"


def test_wildcard_exclusion_of_the_floor_series_is_unknown():
    """`>=3.12,!=3.12.*` supports nothing in 3.12; a 3.12 target would lie."""
    floor = python_floor(">=3.12,!=3.12.*")
    assert floor.value is None
    assert floor.status == "unknown"


def test_a_point_exclusion_does_not_invalidate_the_series():
    """`!=3.12.1` rules out one patch; 3.12 is still the supported floor."""
    for raw in (">=3.12,!=3.12.1", ">=3.12,!=3.12.4,<4", ">=3.12,!=3.13.0"):
        floor = python_floor(raw)
        assert floor.status == "resolved", raw
        assert floor.value == "3.12", raw


def test_major_only_bound_names_no_minor():
    floor = python_floor(">=3")
    assert floor.value is None
    assert floor.status == "unknown"


def test_strictly_greater_than_is_not_guessed():
    assert python_floor(">3.12").status == "unknown"


def test_invalid_specifier_is_invalid_not_unknown():
    for raw in ("3.12", ">= 3.12 or 3.13", ">=3.12,", "=>3.12"):
        assert python_floor(raw).status == "invalid", raw


def test_absent_specifier_is_unknown():
    assert python_floor(None).status == "unknown"
    assert python_floor("").status == "unknown"


# --- T-PY-006 .. T-PY-009: tool alignment ---


def _project(requires: str, **tools: str) -> str:
    text = f"[project]\nrequires-python = {requires!r}\n"
    for section, (key, value) in tools.items():  # type: ignore[misc]
        text += f"\n[tool.{section}]\n{key} = {value!r}\n"
    return text


def test_ruff_mismatch_is_a_finding(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project(">=3.12", ruff=("target-version", "py311")))
    ids = [row["rule_id"] for row in analyze(tmp_path, tmp_path / "pyproject.toml")["findings"]]
    assert ids == ["python.interpreter.version_alignment"]


def test_mypy_and_pyright_mismatch_are_findings(tmp_path: Path):
    write(
        tmp_path / "pyproject.toml",
        _project(">=3.12", mypy=("python_version", "3.11"), pyright=("pythonVersion", "3.10")),
    )
    ids = [row["rule_id"] for row in analyze(tmp_path, tmp_path / "pyproject.toml")["findings"]]
    assert ids.count("python.interpreter.version_alignment") == 2


def test_absent_optional_tool_config_is_not_a_finding(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project(">=3.12"))
    assert analyze(tmp_path, tmp_path / "pyproject.toml")["findings"] == []


def test_aligned_tools_produce_no_findings(tmp_path: Path):
    write(
        tmp_path / "pyproject.toml",
        _project(
            ">=3.12",
            ruff=("target-version", "py312"),
            mypy=("python_version", "3.12"),
            pyright=("pythonVersion", "3.12"),
        ),
    )
    result = analyze(tmp_path, tmp_path / "pyproject.toml")
    assert result["status"] == "PASS"


def test_undecidable_floor_with_pinned_tools_is_reported_not_passed(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project("<4", ruff=("target-version", "py312")))
    ids = [row["rule_id"] for row in analyze(tmp_path, tmp_path / "pyproject.toml")["findings"]]
    assert ids == ["python.interpreter.floor_unknown"]


def test_invalid_specifier_blocks(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project("=>3.12", ruff=("target-version", "py312")))
    findings = analyze(tmp_path, tmp_path / "pyproject.toml")["findings"]
    assert [row["rule_id"] for row in findings] == ["python.interpreter.requires_python_invalid"]
    assert findings[0]["severity"] == "blocking"


# --- T-PY-010 / T-PY-011: addopts parsing ---


def test_addopts_equals_form():
    tokens, resolved = normalize_pytest_addopts("--import-mode=importlib --ignore=foo/bar.py")
    assert resolved
    assert pytest_ignored_paths(tokens) == {"foo/bar.py"}


def test_addopts_split_form():
    tokens, resolved = normalize_pytest_addopts("--ignore foo/bar.py")
    assert resolved
    assert pytest_ignored_paths(tokens) == {"foo/bar.py"}


def test_addopts_list_form():
    tokens, resolved = normalize_pytest_addopts(["--ignore", "a.py", "--ignore=b.py"])
    assert resolved
    assert pytest_ignored_paths(tokens) == {"a.py", "b.py"}


def test_addopts_unsupported_shape_is_unresolved():
    tokens, resolved = normalize_pytest_addopts({"ignore": "a.py"})
    assert tokens == ()
    assert resolved is False


def test_addopts_substring_is_not_an_exclusion():
    """`--ignore=other.py` must not excuse `foo/other.py`."""
    tokens, _ = normalize_pytest_addopts("--ignore=other.py")
    assert pytest_ignored_paths(tokens) == {"other.py"}


# --- T-PY-012 .. T-PY-014: conftest guards ---


def test_conftest_literal_collect_ignore():
    ignore, glob, resolved = parse_collection_guards(
        'collect_ignore = [\n    "skills/foo/scripts/self_test.py",\n]\n'
    )
    assert ignore == ("skills/foo/scripts/self_test.py",)
    assert glob == ()
    assert resolved


def test_conftest_literal_collect_ignore_glob():
    _ignore, glob, resolved = parse_collection_guards(
        'collect_ignore_glob = ["skills/*/scripts/self_test.py"]\n'
    )
    assert glob == ("skills/*/scripts/self_test.py",)
    assert resolved


def test_conftest_comment_is_not_a_guard():
    ignore, glob, resolved = parse_collection_guards(
        "# skills/foo/scripts/self_test.py is excluded elsewhere\ncollect_ignore = []\n"
    )
    assert ignore == ()
    assert glob == ()
    assert resolved


def test_dynamic_conftest_is_unresolved():
    ignore, _glob, resolved = parse_collection_guards("collect_ignore = build_ignore_list()\n")
    assert ignore == ()
    assert resolved is False


def test_literal_concatenation_still_resolves():
    ignore, _glob, resolved = parse_collection_guards('collect_ignore = ["a.py"] + ["b.py"]\n')
    assert ignore == ("a.py", "b.py")
    assert resolved


# --- T-PY-015 / T-PY-016: repository policy ---


def test_malformed_python_contract_blocks(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project(">=3.12"))
    write(tmp_path / "ops/config/python-contract.json", "{not json")
    findings = analyze(tmp_path, tmp_path / "pyproject.toml")["findings"]
    assert [row["rule_id"] for row in findings] == ["python.self_test.contract_parse"]
    assert findings[0]["severity"] == "blocking"


def test_policy_reads_the_repository_contract(tmp_path: Path):
    write(
        tmp_path / "ops/config/python-contract.json",
        '{"skill_self_test_roots": ["skills/demo"],'
        ' "non_test_exclusions": [{"path": "a.py", "reason": "x"}]}',
    )
    policy = load_python_repo_policy(tmp_path)
    assert policy.self_test_roots == frozenset({"skills/demo"})
    assert policy.require_uv_lock is None
    assert policy.contract_source == "ops/config/python-contract.json"
    # `non_test_exclusions` is deliberately not carried: a declaration that
    # a path should be excluded is not evidence that it is, and that is the
    # distinction `guard_unknown` exists to keep.
    assert not hasattr(policy, "non_test_exclusions")


def test_unregistered_self_test_is_a_finding(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project(">=3.12"))
    write(
        tmp_path / "ops/config/python-contract.json", '{"skill_self_test_roots": ["skills/demo"]}'
    )
    write(tmp_path / "skills/ghost/scripts/self_test.py", "print('x')\n")
    ids = [row["rule_id"] for row in analyze(tmp_path, tmp_path / "pyproject.toml")["findings"]]
    assert "python.self_test.registry" in ids
    assert "python.self_test.collection_guard" in ids


def test_registered_and_guarded_self_test_is_clean(tmp_path: Path):
    write(
        tmp_path / "pyproject.toml",
        '[project]\nrequires-python = ">=3.12"\n\n'
        "[tool.pytest.ini_options]\n"
        'addopts = "--ignore=skills/demo/scripts/self_test.py"\n',
    )
    write(
        tmp_path / "ops/config/python-contract.json", '{"skill_self_test_roots": ["skills/demo"]}'
    )
    write(tmp_path / "skills/demo/scripts/self_test.py", "print('x')\n")
    assert analyze(tmp_path, tmp_path / "pyproject.toml")["findings"] == []


def test_conftest_glob_guard_satisfies_the_check(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project(">=3.12"))
    write(
        tmp_path / "ops/config/python-contract.json", '{"skill_self_test_roots": ["skills/demo"]}'
    )
    write(tmp_path / "conftest.py", 'collect_ignore_glob = ["skills/*/scripts/self_test.py"]\n')
    write(tmp_path / "skills/demo/scripts/self_test.py", "print('x')\n")
    assert analyze(tmp_path, tmp_path / "pyproject.toml")["findings"] == []


def test_unreadable_guards_are_reported_not_assumed(tmp_path: Path):
    write(tmp_path / "pyproject.toml", _project(">=3.12"))
    write(
        tmp_path / "ops/config/python-contract.json", '{"skill_self_test_roots": ["skills/demo"]}'
    )
    write(tmp_path / "conftest.py", "collect_ignore = build()\n")
    write(tmp_path / "skills/demo/scripts/self_test.py", "print('x')\n")
    ids = [row["rule_id"] for row in analyze(tmp_path, tmp_path / "pyproject.toml")["findings"]]
    assert "python.self_test.guard_unknown" in ids


def test_live_repository_python_surface_is_assessable():
    """The real root must parse and its self-test topology must resolve."""
    root = Path(__file__).resolve().parents[3]
    result = analyze(root, root / "pyproject.toml")
    assert result["blockers"] == []
    ids = [row["rule_id"] for row in result["findings"]]
    assert "python.interpreter.requires_python_invalid" not in ids
    assert "python.self_test.contract_parse" not in ids
    assert "python.self_test.guard_unknown" not in ids
