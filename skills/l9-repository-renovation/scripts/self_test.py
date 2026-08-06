#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run(command: list[str], cwd: Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode != expect:
        raise AssertionError(
            f"command failed ({completed.returncode}, expected {expect}): {' '.join(command)}\n{completed.stdout}"
        )
    return completed


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _audit_findings(root: Path) -> list[dict]:
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    import audit_repository

    return audit_repository.audit(root)["findings"]


def regression_ast_precision() -> None:
    """Lock the AST-precision behaviors: structural test-content, scope-aware
    first-party imports, and structural conflict markers — in both directions."""
    base = (
        '[project]\nname = "x"\nversion = "0.1.0"\nrequires-python = ">=3.12"\ndependencies = []\n'
    )
    # Negatives: none of these must produce a finding.
    with tempfile.TemporaryDirectory(prefix="l9-reno-neg-") as tmp:
        root = Path(tmp)
        write(
            root / "pyproject.toml",
            base + '\n[tool.pytest.ini_options]\naddopts = "--ignore=dags/test_pipeline.py"\n',
        )
        write(
            root / "dags/test_pipeline.py",
            '"""A DAG, not a test."""\n\nGRAPH = {"a": ["b"]}\n\n\ndef build():\n    return GRAPH\n',
        )
        write(root / "_archived/legacy_api.py", "import flask\n\napp = flask.Flask(__name__)\n")
        write(root / "docs/notes.md", "# Title\n" + ("=" * 40) + "\n\nprose\n")
        findings = _audit_findings(root)
        blob = json.dumps(findings)
        assert not any(f["class"] == "repository_integrity_failure" for f in findings), (
            f"banner misread as conflict: {blob}"
        )
        assert not any(f["class"] == "test_topology_gap" for f in findings), (
            f"DAG misread as ignored test: {blob}"
        )
        assert "flask" not in blob, f"archived third-party import flagged: {blob}"
    # Positives: each must still be detected.
    with tempfile.TemporaryDirectory(prefix="l9-reno-pos-") as tmp:
        root = Path(tmp)
        write(
            root / "pyproject.toml",
            base + '\n[tool.pytest.ini_options]\naddopts = "--ignore=hidden"\n',
        )
        write(
            root / "hidden/test_real.py", "import pytest\n\n\ndef test_real():\n    assert True\n"
        )
        write(
            root / "src/module.py", "x = 1\n<<<<<<< HEAD\ny = 2\n=======\ny = 3\n>>>>>>> feature\n"
        )
        findings = _audit_findings(root)
        classes = {f["class"] for f in findings}
        assert "test_topology_gap" in classes, f"real ignored test not detected: {sorted(classes)}"
        assert "repository_integrity_failure" in classes, (
            f"real conflict not detected: {sorted(classes)}"
        )


def regression_api_surface() -> None:
    """Lock the public-API compatibility gate: a removed parameter is breaking,
    an added optional parameter is compatible."""
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    import api_surface

    with tempfile.TemporaryDirectory(prefix="l9-reno-api-") as tmp:
        before = Path(tmp) / "before"
        after = Path(tmp) / "after"
        write(before / "pkg/service.py", "def render(a, b, c):\n    return 1\n")
        write(after / "pkg/service.py", "def render(a, b, *, verbose=False):\n    return 1\n")
        delta = api_surface.diff_surface(
            api_surface.extract_surface(before),
            api_surface.extract_surface(after),
        )
        kinds = {c["kind"]: c["severity"] for c in delta["changes"]}
        assert delta["verdict"] == "breaking", f"removed param must be breaking: {delta}"
        assert delta["required_semver_bump"] == "major", (
            f"breaking change must require major: {delta}"
        )
        assert kinds.get("param_removed") == "breaking", f"missing param_removed: {kinds}"
        assert kinds.get("optional_param_added") == "compatible", (
            f"added optional must be compatible: {kinds}"
        )


def main() -> int:
    regression_ast_precision()
    regression_api_surface()
    with tempfile.TemporaryDirectory(prefix="l9-renovation-selftest-") as tmp:
        root = Path(tmp) / "messy-repo"
        root.mkdir()
        run(["git", "init", "-b", "main"], root)
        run(["git", "config", "user.name", "L9 Self Test"], root)
        run(["git", "config", "user.email", "selftest@example.invalid"], root)

        write(
            root / "pyproject.toml",
            """[project]
name = "messy-repo"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
package = false

[tool.pytest.ini_options]
addopts = "--ignore=orphan/tests"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
""",
        )
        write(
            root / ".github/workflows/test.yml",
            """name: test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pip install pytest-xdist
      - run: pytest -q
""",
        )
        write(
            root / "scripts/run_tests.py",
            """from __future__ import annotations

print("root tests only")
""",
        )
        write(
            root / "orphan/tests/test_orphan.py",
            """import unittest


class OrphanTest(unittest.TestCase):
    def test_orphan(self) -> None:
        self.assertTrue(True)
""",
        )
        write(root / "README.md", "# Messy Repo\n")
        run(
            [
                "git",
                "add",
                "pyproject.toml",
                ".github/workflows/test.yml",
                "scripts/run_tests.py",
                "orphan/tests/test_orphan.py",
                "README.md",
            ],
            root,
        )
        run(["git", "commit", "-m", "test: create messy baseline"], root)
        base_sha = run(["git", "rev-parse", "HEAD"], root).stdout.strip()

        before = root / "repository-audit.before.json"
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "audit_repository.py"),
                str(root),
                "--output",
                str(before),
            ],
            root,
        )
        before_payload = load(before)
        classes = {item["class"] for item in before_payload["findings"]}
        required_classes = {
            "dependency_authority_drift",
            "package_boundary_ambiguity",
            "test_topology_gap",
        }
        missing_classes = required_classes - classes
        if missing_classes:
            raise AssertionError(
                f"audit failed to detect expected classes: {sorted(missing_classes)}"
            )

        contract_path = root / "renovation-contract.json"
        plan_path = root / "RENOVATION_PLAN.md"
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "compile_contract.py"),
                str(before),
                "--repo",
                str(root),
                "--base-ref",
                base_sha,
                "--branch",
                "renovation/self-test",
                "--output",
                str(contract_path),
                "--plan",
                str(plan_path),
            ],
            root,
        )
        contract = load(contract_path)
        contract["validation_matrix"] = [
            {
                "id": "synthetic-validation",
                "command": [sys.executable, "-c", "print('synthetic validation passed')"],
                "timeout_seconds": 30,
                "required": True,
            }
        ]
        contract_path.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        run([sys.executable, str(SCRIPT_DIR / "validate_contract.py"), str(contract_path)], root)

        write(
            root / "pyproject.toml",
            """[project]
name = "messy-repo"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
package = false
""",
        )
        write(
            root / ".github/workflows/test.yml",
            """name: test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/run_tests.py
""",
        )
        write(
            root / "scripts/run_tests.py",
            """from __future__ import annotations

import subprocess
import sys

raise SystemExit(
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "orphan/tests", "-p", "test_*.py", "-v"],
        check=False,
    ).returncode
)
""",
        )
        run(
            ["git", "add", "pyproject.toml", ".github/workflows/test.yml", "scripts/run_tests.py"],
            root,
        )
        run(["git", "commit", "-m", "feat: renovate repository control plane"], root)

        after = root / "repository-audit.after.json"
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "audit_repository.py"),
                str(root),
                "--output",
                str(after),
            ],
            root,
        )
        after_payload = load(after)
        after_classes = {item["class"] for item in after_payload["findings"]}
        if required_classes & after_classes:
            raise AssertionError(
                f"renovation did not remove expected findings: {sorted(required_classes & after_classes)}"
            )

        delta_json = root / "renovation-delta.json"
        delta_md = root / "RENOVATION_DELTA.md"
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "compare_audits.py"),
                str(before),
                str(after),
                "--json",
                str(delta_json),
                "--markdown",
                str(delta_md),
            ],
            root,
        )
        delta = load(delta_json)
        if not delta["resolved"] or delta["status"] != "passed":
            raise AssertionError("before/after comparison did not prove a safe improvement")

        evidence = root / "validation-evidence.json"
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "run_validation_matrix.py"),
                str(contract_path),
                "--repo",
                str(root),
                "--output",
                str(evidence),
            ],
            root,
        )
        if load(evidence)["status"] != "passed":
            raise AssertionError("synthetic validation evidence failed")

        pr_validation = root / "pr-pack-validation.json"
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "validate_pr_pack.py"),
                "--repo",
                str(root),
                "--contract",
                str(contract_path),
                "--evidence",
                str(evidence),
                "--before",
                str(before),
                "--after",
                str(after),
                "--output",
                str(pr_validation),
            ],
            root,
        )
        if load(pr_validation)["status"] != "passed":
            raise AssertionError("PR pack validation failed")

        pr_body = root / "PR_BODY.md"
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "render_pr_body.py"),
                "--contract",
                str(contract_path),
                "--evidence",
                str(evidence),
                "--delta",
                str(delta_json),
                "--output",
                str(pr_body),
            ],
            root,
        )
        if "## Renovated authority model" not in pr_body.read_text(encoding="utf-8"):
            raise AssertionError("PR body missing authority model")

    print("SELF TEST PASS: audit -> contract -> renovation -> validation -> PR pack")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
