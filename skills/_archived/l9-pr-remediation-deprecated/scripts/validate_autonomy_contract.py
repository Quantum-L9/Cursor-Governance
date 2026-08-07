#!/usr/bin/env python3
"""Validate bounded codebase autonomy and CI signal-routing regressions."""
from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REQUIRED_FILES = [
    "agents/meta.yaml",
    "references/autonomy-controller.md",
    "references/ci-signal-boundary.md",
    "references/terminal-escalation.md",
    "assets/terminal-blocker-issue-template.md",
    "assets/ci-pipeline-issue-template.md",
    "scripts/render_ci_pipeline_issues.py",
    "scripts/package_run_deliverable.py",
    "tests/fixtures/run-report-converged.json",
    "tests/fixtures/run-report-blocked-github.json",
    "tests/fixtures/run-report-blocked-fallback.json",
    "tests/fixtures/run-report-blocked-ci-signal.json",
    "tests/fixtures/run-report-invalid-no-escalation.json",
    "tests/fixtures/run-report-invalid-ci-repair-attempt.json",
]
REQUIRED_TERMS = [
    "Maximum three cycles",
    "Never start cycle 4",
    "PR-Ready Definition",
    "Repair codebase defects only",
    "CI pipeline is signal-only",
    "One issue file per CI root cause",
]
FORBIDDEN_REGRESSIONS = [
    "Apply fixes for the accepted findings (blocking CI",
    "Max local verify iterations: 5",
    "Resolve threads after replying.",
    "it never blocks the run (fail-open per source)",
    "CI pipeline mutations: 0 or 1",
]
POSITIVE_FIXTURES = (
    "run-report-converged.json",
    "run-report-blocked-github.json",
    "run-report-blocked-fallback.json",
    "run-report-blocked-ci-signal.json",
)
NEGATIVE_FIXTURES = (
    "run-report-invalid-no-escalation.json",
    "run-report-invalid-ci-repair-attempt.json",
)


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def validate_packager(root: Path, fixture_name: str, expect_ci_file: bool) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        work = Path(temp_dir) / "artifacts"
        work.mkdir()
        fixture = root / "tests" / "fixtures" / fixture_name
        (work / "run-report.json").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
        (work / "CONVERGENCE_REPORT.yaml").write_text("convergence_status: fixture\n", encoding="utf-8")
        (work / "PR_READY_EVIDENCE.json").write_text('{"ready": false}\n', encoding="utf-8")
        render = run_command([
            sys.executable,
            str(root / "scripts" / "render_ci_pipeline_issues.py"),
            "--run-report",
            str(work / "run-report.json"),
            "--output-dir",
            str(work),
        ])
        if render.returncode != 0:
            errors.append(f"renderer fixture failed {fixture_name}: {render.stderr or render.stdout}")
            return errors
        output = Path(temp_dir) / "run.tar.gz"
        package = run_command([
            sys.executable,
            str(root / "scripts" / "package_run_deliverable.py"),
            "--artifact-dir",
            str(work),
            "--output",
            str(output),
        ])
        if package.returncode != 0 or not output.is_file():
            errors.append(f"packager fixture failed {fixture_name}: {package.stderr or package.stdout}")
            return errors
        with tarfile.open(output, "r:gz") as archive:
            names = set(archive.getnames())
        required = {
            "l9-pr-remediation-run/MANIFEST.json",
            "l9-pr-remediation-run/run-report.json",
            "l9-pr-remediation-run/CONVERGENCE_REPORT.yaml",
            "l9-pr-remediation-run/PR_READY_EVIDENCE.json",
        }
        for name in required:
            if name not in names:
                errors.append(f"packager missing {name}")
        ci_names = [name for name in names if "/issues/ci-pipeline/" in name]
        if expect_ci_file and len(ci_names) != 1:
            errors.append(f"expected one CI issue file in tarball, found {len(ci_names)}")
        if not expect_ci_file and ci_names:
            errors.append("unexpected CI issue file in converged no-signal fixture")
    return errors


def run(root: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing {rel}")
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    for term in REQUIRED_TERMS:
        if term not in skill_text:
            errors.append(f"SKILL.md missing autonomy term: {term}")
    for term in FORBIDDEN_REGRESSIONS:
        for path in root.rglob("*"):
            if path.resolve() == Path(__file__).resolve():
                continue
            if path.is_file() and path.suffix in {".md", ".yaml", ".py"}:
                if term in path.read_text(encoding="utf-8", errors="ignore"):
                    errors.append(f"forbidden autonomy regression in {path.relative_to(root)}: {term}")

    schema = json.loads((root / "schemas" / "run-report.schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["run"]["properties"]["configured_max_cycles"].get("maximum") != 3:
        errors.append("schema does not cap configured_max_cycles at 3")
    if schema["properties"]["schema_version"].get("const") != "3.0":
        errors.append("schema version is not 3.0")
    signal_def = schema.get("$defs", {}).get("CiPipelineSignal", {})
    if signal_def.get("properties", {}).get("repair_attempted", {}).get("const") is not False:
        errors.append("schema does not prohibit CI repair attempts")
    if signal_def.get("properties", {}).get("repository_files_modified", {}).get("maxItems") != 0:
        errors.append("schema does not prohibit repository modifications for CI signals")

    validator = root / "scripts" / "validate_run_report.py"
    for name in POSITIVE_FIXTURES:
        proc = run_command([sys.executable, str(validator), str(root / "tests" / "fixtures" / name)])
        if proc.returncode != 0:
            errors.append(f"positive fixture failed {name}: {proc.stderr or proc.stdout}")
    for name in NEGATIVE_FIXTURES:
        proc = run_command([sys.executable, str(validator), str(root / "tests" / "fixtures" / name)])
        if proc.returncode == 0:
            errors.append(f"negative fixture unexpectedly passed: {name}")

    errors.extend(validate_packager(root, "run-report-converged.json", expect_ci_file=False))
    errors.extend(validate_packager(root, "run-report-blocked-ci-signal.json", expect_ci_file=True))

    with tempfile.TemporaryDirectory() as temp_dir:
        work = Path(temp_dir) / "artifacts"
        work.mkdir()
        fixture = root / "tests" / "fixtures" / "run-report-blocked-ci-signal.json"
        (work / "run-report.json").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
        (work / "CONVERGENCE_REPORT.yaml").write_text("convergence_status: partial\n", encoding="utf-8")
        (work / "PR_READY_EVIDENCE.json").write_text('{"ready": false}\n', encoding="utf-8")
        output = Path(temp_dir) / "missing-ci-file.tar.gz"
        proc = run_command([
            sys.executable,
            str(root / "scripts" / "package_run_deliverable.py"),
            "--artifact-dir",
            str(work),
            "--output",
            str(output),
        ])
        if proc.returncode == 0:
            errors.append("packager accepted a run missing its required CI issue file")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    errors = run(root)
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print("PASS: bounded codebase autonomy and CI signal routing validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
