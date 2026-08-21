#!/usr/bin/env python3
"""Cheap pre-bootstrap check that a campaign can actually be executed.

This is deliberately not a proof of campaign correctness. It catches the small
set of conditions that make execution *impossible* — the ones that used to
survive compile, validation, admission, bootstrap and arm, and only surfaced as
an `INCOMPLETE` verdict or a post-bootstrap restart cycle half an hour later.

Three findings, each cheap to compute from the compiled blueprint:

A. verification deadlock — a task the controller must verify, with nothing
   executable to verify it by. Synthesized from repository convention where the
   answer is obvious, reported immediately where it is not.
B. unreachable definition state — `definition_status: blocked` on a task whose
   readiness is already decided by runtime dependency edges, which the
   controller has no transition out of.
C. admission evidence ordering — mechanical evidence the first execution
   frontier needs, which cannot be collected once bootstrap has frozen the
   blueprint.

Explicit configuration always wins over inference.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"blocker": 0, "warning": 1, "info": 2}
_PY_MODULE = re.compile(r"^(?P<pkg>[\w./-]+)\.py$")
_INSPECTION_KINDS = {"analysis", "inspection", "decision", "program_control", "review"}


class LaunchabilityError(RuntimeError):
    """Raised when a campaign cannot be launched and inference cannot save it."""


def _finding(
    code: str, severity: str, task_id: str | None, message: str, remedy: str
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "task_id": task_id,
        "message": message,
        "remedy": remedy,
    }


def declared_validation_commands(task: dict[str, Any]) -> list[str]:
    """Executable commands the task itself declares. Explicit beats inferred."""
    commands: list[str] = []
    for entry in task.get("validation") or []:
        if not isinstance(entry, dict):
            continue
        command = str(entry.get("command_or_inspection") or entry.get("command") or "").strip()
        method = str(entry.get("method") or "").strip()
        if command and method in {"command", "command_and_inspection", "external_adapter"}:
            commands.append(command)
    for command in task.get("required_validation_commands") or []:
        text = str(command).strip()
        if text and text not in commands:
            commands.append(text)
    return commands


def _writable_paths(task: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for entry in task.get("outputs") or []:
        if isinstance(entry, dict) and entry.get("location"):
            paths.append(str(entry["location"]).strip())
    for entry in task.get("writable_paths") or []:
        text = str(entry).strip()
        if text and text not in paths:
            paths.append(text)
    return [path for path in paths if path]


def _nearest_tests(repo_root: Path, module_path: str) -> list[str]:
    """Find tests a repository's own convention associates with a module."""
    candidate = Path(module_path)
    stem = candidate.stem
    if not stem:
        return []
    found: list[str] = []
    for parent in [candidate.parent, *candidate.parents]:
        for name in (f"tests/test_{stem}.py", f"test_{stem}.py"):
            probe = repo_root / parent / name
            if probe.is_file():
                rel = probe.relative_to(repo_root).as_posix()
                if rel not in found:
                    found.append(rel)
        if found:
            break
    return found


def infer_validation_commands(
    task: dict[str, Any], repo_root: Path, *, python: str = "python3"
) -> list[str]:
    """Derive a runnable validation from repository convention.

    Ordered by how much the repository already tells us: an existing test file
    next to a changed module, then the task's own declared test outputs, then a
    presence check on what the task promises to write. Returns an empty list
    when nothing mechanical is derivable — the caller reports that.

    Python test files are run with pytest. Unittest TestCase classes still
    collect under pytest; the reverse is not true. ``-o addopts=`` clears a
    repo-wide ``--cov-fail-under`` addopts without requiring the optional
    pytest-cov plugin (core pytest rejects ``--no-cov`` when the plugin is
    absent).
    """
    paths = _writable_paths(task)
    tests: list[str] = []
    for path in paths:
        if path.startswith("tests/") or Path(path).name.startswith("test_"):
            if path.endswith(".py") and path not in tests:
                tests.append(path)
    if not tests:
        for path in paths:
            if _PY_MODULE.match(path):
                for probe in _nearest_tests(repo_root, path):
                    if probe not in tests:
                        tests.append(probe)
    if tests:
        return [f"{python} -m pytest {' '.join(tests)} --tb=short -q -o addopts="]
    shells = [path for path in paths if path.endswith((".sh", ".bash"))]
    if shells:
        return [f"bash -n {' '.join(shells)}"]
    if paths:
        quoted = " ".join(f"'{path}'" for path in paths)
        return [f"test -s {quoted}"] if len(paths) == 1 else [f"ls -1 {quoted} >/dev/null"]
    return []


def _requires_controller_verification(task: dict[str, Any]) -> bool:
    kind = str(task.get("execution_kind") or "").strip().lower()
    if kind in _INSPECTION_KINDS:
        return False
    return str(task.get("definition_status") or "") != "cancelled"


def check_tasks(
    tasks: list[dict[str, Any]],
    repo_root: Path,
    *,
    infer: bool = True,
    python: str = "python3",
) -> dict[str, Any]:
    """Report launchability findings and any validations that were synthesized."""
    findings: list[dict[str, Any]] = []
    synthesized: dict[str, list[str]] = {}
    ids = {str(task.get("id")) for task in tasks}

    for task in tasks:
        task_id = str(task.get("id") or "UNKNOWN")
        status = str(task.get("definition_status") or "")

        if _requires_controller_verification(task) and not declared_validation_commands(task):
            inferred = infer_validation_commands(task, repo_root, python=python) if infer else []
            if inferred:
                synthesized[task_id] = inferred
                findings.append(
                    _finding(
                        "validation_synthesized",
                        "info",
                        task_id,
                        f"no executable validation declared; inferred {inferred!r} "
                        "from repository convention",
                        "declare validation_commands on the task to override the inference",
                    )
                )
            else:
                findings.append(
                    _finding(
                        "verification_deadlock",
                        "blocker",
                        task_id,
                        "task is controller-verified but declares no executable validation, "
                        "and none is derivable from its outputs; pec verify would return "
                        "INCOMPLETE after bootstrap",
                        "declare a validation entry with method: command, or set "
                        "execution_kind to an inspection kind",
                    )
                )

        if status == "blocked":
            findings.append(
                _finding(
                    "unreachable_definition_state",
                    "blocker",
                    task_id,
                    "definition_status 'blocked' has no controller transition to 'ready'; "
                    "runtime dependency edges already decide eligibility",
                    "compile the task as 'ready' and express ordering through dependencies",
                )
            )

        for dependency in task.get("dependencies") or task.get("dependency_ids") or []:
            if str(dependency) not in ids:
                findings.append(
                    _finding(
                        "dangling_dependency",
                        "blocker",
                        task_id,
                        f"depends on {dependency!r}, which is not a task in this campaign",
                        "remove the dependency or add the missing task",
                    )
                )

    findings.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["task_id"] or ""))
    blockers = [item for item in findings if item["severity"] == "blocker"]
    return {
        "schema": "program-execution.launchability-report.v1",
        "launchable": not blockers,
        "task_count": len(tasks),
        "findings": findings,
        "blockers": blockers,
        "synthesized_validations": synthesized,
    }


def apply_synthesized_validations(
    blueprint_dir: Path, synthesized: dict[str, list[str]]
) -> list[str]:
    """Write inferred validations into the Task Cards they were inferred for.

    Inference used to stop at the report: `--fast` said it would infer a
    validation, the finding recorded what it inferred, and then the contract was
    rendered from a task card that still declared none. The controller then
    returned INCOMPLETE on a campaign whose own preparation had told the operator
    it was handled -- the gap between the message and the artifact.

    The entry is written as an ordinary `method: command` validation, because
    that is what the lock and the rendered contract read. Its `VAL-INFERRED-*`
    id is the only provenance the Task Card schema has room for
    (`additionalProperties: false`), and it is enough to tell an operator
    reading the card that they did not write this line.

    Returns the task ids that were changed, so a caller can re-validate.
    """
    import yaml

    cards = blueprint_dir / "TASK_CARDS.yaml"
    if not synthesized or not cards.is_file():
        return []
    doc = yaml.safe_load(cards.read_text(encoding="utf-8")) or {}
    changed: list[str] = []
    for task in doc.get("tasks") or []:
        commands = synthesized.get(str(task.get("id")))
        if not commands or declared_validation_commands(task):
            continue
        entries = list(task.get("validation") or [])
        for index, command in enumerate(commands, start=1):
            entries.append(
                {
                    "id": f"VAL-INFERRED-{index:03d}",
                    "method": "command",
                    "command_or_inspection": command,
                    "environment": "repo_local",
                    "expected_result": "PASS",
                }
            )
        task["validation"] = entries
        changed.append(str(task.get("id")))
    if changed:
        cards.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
        )
    return sorted(changed)


def blueprint_tasks(blueprint_dir: Path) -> list[dict[str, Any]]:
    """Read compiled Task Cards without importing the blueprint toolchain."""
    tasks_path = blueprint_dir / "tasks.json"
    if tasks_path.is_file():
        payload = json.loads(tasks_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("tasks") or []
        return [item for item in payload if isinstance(item, dict)]
    tasks: list[dict[str, Any]] = []
    for path in sorted((blueprint_dir / "tasks").glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(item, dict):
            tasks.append(item)
    return tasks


def format_report(report: dict[str, Any]) -> str:
    lines = [
        f"launchability: {'OK' if report['launchable'] else 'BLOCKED'} "
        f"({report['task_count']} tasks, {len(report['blockers'])} blockers)"
    ]
    for item in report["findings"]:
        lines.append(
            f"  [{item['severity']}] {item['task_id'] or '-'} {item['code']}: {item['message']}"
        )
        if item["severity"] == "blocker":
            lines.append(f"      remedy: {item['remedy']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="launchability", description=__doc__)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--no-infer", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = check_tasks(blueprint_tasks(args.blueprint), args.repo_root, infer=not args.no_infer)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else format_report(report))
    return 0 if report["launchable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
