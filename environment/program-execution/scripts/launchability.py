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
D. inadmissible validation command — a declared command the peer permission
   ceiling will refuse. Reported here rather than at provider dispatch, which
   is the other side of isolation, compile, bootstrap and arm.

Explicit configuration always wins over inference.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

# Sibling import safety: this module is also loaded via importlib (tests) and
# run directly, so the PE root may not be on sys.path.
_PE_ROOT = Path(__file__).resolve().parents[1]
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(_PE_ROOT) not in sys.path:
    sys.path.append(str(_PE_ROOT))

from peer_execution.validation_command import validation_command_error  # noqa: E402

SEVERITY_ORDER = {"blocker": 0, "warning": 1, "info": 2}
_PY_MODULE = re.compile(r"^(?P<pkg>[\w./-]+)\.py$")
_INSPECTION_KINDS = {"analysis", "inspection", "decision", "program_control", "review", "read_only"}
_COMMAND_METHODS = {"command", "command_and_inspection"}
_TERMINAL_METHODS = {"command", "command_and_inspection", "external_adapter"}
_MUTATING_ACTIONS = {"local_write", "commit", "destructive_change"}


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


def declared_verification_mechanisms(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the Blueprint's typed verification mechanisms without flattening them."""
    mechanisms: list[dict[str, Any]] = []
    for entry in task.get("validation") or task.get("verification_mechanisms") or []:
        if not isinstance(entry, dict):
            continue
        method = str(entry.get("method") or "").strip()
        instruction = str(
            entry.get("command_or_inspection")
            or entry.get("instruction")
            or entry.get("command")
            or ""
        ).strip()
        if method and instruction:
            mechanisms.append(
                {
                    "id": str(entry.get("id") or f"VAL-{len(mechanisms) + 1:03d}"),
                    "method": method,
                    "command_or_inspection": instruction,
                    "environment": str(entry.get("environment") or "repo_local"),
                    "expected_result": str(entry.get("expected_result") or "PASS"),
                }
            )
    return mechanisms


def declared_validation_commands(task: dict[str, Any]) -> list[str]:
    """Executable shell commands derived from typed verification mechanisms."""
    commands = [
        item["command_or_inspection"]
        for item in declared_verification_mechanisms(task)
        if item["method"] in _COMMAND_METHODS
    ]
    for command in task.get("required_validation_commands") or []:
        text = str(command).strip()
        if text and text not in commands:
            commands.append(text)
    return commands


def task_requires_terminal_verifier(task: dict[str, Any]) -> bool:
    """Only mutating repo-local work must carry a terminal verifier before seal."""
    if str(task.get("execution_kind") or "").strip() != "repo_local":
        return False
    ceiling = task.get("authorization_ceiling") or {}
    return any(bool(ceiling.get(action)) for action in _MUTATING_ACTIONS)


def has_terminal_verifier(task: dict[str, Any]) -> bool:
    return any(
        item["method"] in _TERMINAL_METHODS for item in declared_verification_mechanisms(task)
    )


def terminal_verification_errors(tasks: list[dict[str, Any]]) -> list[str]:
    return [
        f"{task.get('id') or 'UNKNOWN'}: mutating repo_local task has no terminal "
        "verification mechanism"
        for task in tasks
        if task_requires_terminal_verifier(task) and not has_terminal_verifier(task)
    ]


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
    collect under pytest; the reverse is not true. ``--no-cov`` prevents a
    repo-wide ``--cov-fail-under`` addopts from failing a targeted subset.
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
        joined = " ".join(shlex.quote(path) for path in tests)
        return _admissible([f"{python} -m pytest {joined} --tb=short -q --no-cov"])
    shells = [path for path in paths if path.endswith((".sh", ".bash"))]
    if shells:
        joined = " ".join(shlex.quote(path) for path in shells)
        return _admissible([f"bash -n {joined}"])
    if paths:
        # One command per path. The old multi-path form was
        # `ls -1 'a' 'b' >/dev/null`, whose redirect composes two shell
        # operations and is refused by the peer permission ceiling — after
        # isolation, compile, bootstrap and arm.
        return _admissible([f"test -s {shlex.quote(path)}" for path in paths])
    return []


def _admissible(commands: list[str]) -> list[str]:
    """Synthesis may never emit a command the peer permission ceiling refuses.

    This is an internal invariant, not operator input validation: reaching it
    means launchability itself produced inadmissible shell, which is a defect
    here rather than a defect in the campaign source.
    """
    for command in commands:
        reason = validation_command_error(command)
        if reason is not None:
            raise LaunchabilityError(
                f"launchability synthesized an inadmissible validation command "
                f"{command!r}: {reason}"
            )
    return commands


def _requires_controller_verification(task: dict[str, Any]) -> bool:
    kind = str(task.get("execution_kind") or "").strip().lower()
    if kind in _INSPECTION_KINDS or kind in {"external_adapter"}:
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

        for command in declared_validation_commands(task):
            reason = validation_command_error(command)
            if reason is not None:
                findings.append(
                    _finding(
                        "invalid_validation_command",
                        "blocker",
                        task_id,
                        f"declared validation command {command!r} is not admissible: {reason}",
                        "declare one shell operation per validation entry; the peer permission "
                        "ceiling refuses composed commands, redirects, command substitution and "
                        "inline interpreter code",
                    )
                )

        if (
            _requires_controller_verification(task)
            and not has_terminal_verifier(task)
            and not declared_validation_commands(task)
        ):
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
    blueprint_dir: Path, synthesized: dict[str, list[str]], *, validate: bool = True
) -> list[str]:
    """Atomically enrich native Task Cards before seal, then manifest + validate.

    The campaign runner passes ``validate=False`` because canonical Blueprint
    validation is its immediately following stage. Direct callers default to
    validation so no mutation can escape schema checking.
    """
    import yaml
    from blueprint_ops import lock_exists_for_blueprint, validate_blueprint, write_manifest

    cards = blueprint_dir / "TASK_CARDS.yaml"
    manifest = blueprint_dir / "MANIFEST.yaml"
    if not synthesized or not cards.is_file():
        return []
    if lock_exists_for_blueprint(blueprint_dir):
        raise LaunchabilityError("refuse post-seal Blueprint validation enrichment")

    cards_before = cards.read_bytes()
    manifest_before = manifest.read_bytes() if manifest.is_file() else None
    manifest_doc = (
        yaml.safe_load(manifest_before.decode("utf-8")) if manifest_before is not None else {}
    ) or {}
    compiled_from = str(manifest_doc.get("compiled_from") or "launchability-preseal-enrichment")
    doc = yaml.safe_load(cards_before.decode("utf-8")) or {}
    changed: list[str] = []
    for task in doc.get("tasks") or []:
        commands = synthesized.get(str(task.get("id")))
        if not commands or has_terminal_verifier(task):
            continue
        entries = list(task.get("validation") or [])
        existing = {
            str(item.get("command_or_inspection") or "")
            for item in entries
            if isinstance(item, dict)
        }
        for index, command in enumerate(commands, start=1):
            if command in existing:
                continue
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
        if has_terminal_verifier(task):
            changed.append(str(task.get("id")))

    if not changed:
        return []
    try:
        cards.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
        )
        write_manifest(blueprint_dir, compiled_from)
        if validate:
            errors = validate_blueprint(blueprint_dir, "template")
            if errors:
                raise LaunchabilityError(
                    "pre-seal validation enrichment broke canonical Blueprint schema: "
                    + "; ".join(errors[:5])
                )
    except Exception:
        cards.write_bytes(cards_before)
        if manifest_before is None:
            manifest.unlink(missing_ok=True)
        else:
            manifest.write_bytes(manifest_before)
        raise
    return sorted(changed)


def launchability_report_path(blueprint_dir: Path) -> Path:
    """Runtime/admission report path outside the sealed Blueprint tree."""
    root = blueprint_dir.resolve()
    return root.parent / "launchability-reports" / f"{root.name}.json"


def blueprint_tasks(blueprint_dir: Path) -> list[dict[str, Any]]:
    """Read the canonical native TASK_CARDS.yaml projection used by the Controller."""
    import yaml

    cards = blueprint_dir / "TASK_CARDS.yaml"
    if not cards.is_file():
        return []
    payload = yaml.safe_load(cards.read_text(encoding="utf-8")) or {}
    tasks = payload.get("tasks") or []
    if not isinstance(tasks, list):
        raise LaunchabilityError("TASK_CARDS.yaml tasks must be a list")
    return [item for item in tasks if isinstance(item, dict)]


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
