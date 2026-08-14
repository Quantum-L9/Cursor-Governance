from __future__ import annotations

import ast
import hashlib
import io
import json
import sys
import tokenize
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

EXPECTED_ADAPTERS = {
    "cursor-foreground",
    "cursor-background",
    "claude-code-direct",
    "chatgpt-manual-handoff",
    "ci-generic-shell",
    "ci-github-actions",
    "github-remote-actions",
    "github-checks",
    "github-deployments",
    "target-deployment-factory",
    "codex-cloud",
    "gemini-review",
    "manus-cloud",
}
DEBRIS_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
DEBRIS_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3"}
FORBIDDEN_SOURCE_TERMS = {
    "merge_pull_request(",
    "enable_auto_merge(",
    "git push --force",
    "--dangerously-skip-permissions",
}
REQUIRED_SECURITY = {
    "default_deny": True,
    "may_narrow_authority": True,
    "may_widen_authority": False,
    "autonomous_merge": False,
    "force_push": False,
    "direct_graphiti_write": False,
}
REQUIRED_CORE = {
    "MANIFEST.yaml",
    "shared/AUTHORIZATION_MODEL.yaml",
    "program-execution-controller-template/schemas/task-contract.schema.json",
    "program-execution-controller-template/schemas/attempt-receipt.schema.json",
    "program-execution-controller-template/schemas/verification-receipt.schema.json",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _track_token_depth(
    token: tokenize.TokenInfo,
    depth: int,
    errors: list[tuple[str, int]],
) -> int:
    if token.type == tokenize.OP and token.string in "([{":
        return depth + 1
    if token.type == tokenize.OP and token.string in ")]}":
        return max(0, depth - 1)
    if token.type == tokenize.OP and token.string == ";":
        errors.append(("E702", token.start[0]))
    return depth


def _compound_body_errors(
    physical_lines: dict[int, list[tuple[tokenize.TokenInfo, int]]],
) -> list[tuple[str, int]]:
    compound_keywords = {
        "if",
        "elif",
        "else",
        "for",
        "while",
        "try",
        "except",
        "finally",
        "with",
        "def",
        "class",
    }
    ignored = {
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.COMMENT,
    }
    errors: list[tuple[str, int]] = []
    for line_number, line_tokens in physical_lines.items():
        significant = [item for item in line_tokens if item[0].type not in ignored]
        if not significant or significant[0][0].string not in compound_keywords:
            continue
        colon_positions = [
            index
            for index, (token, token_depth) in enumerate(significant)
            if token.type == tokenize.OP and token.string == ":" and token_depth == 0
        ]
        if colon_positions and colon_positions[-1] < len(significant) - 1:
            errors.append(("E701", line_number))
    return errors


def _compressed_statement_errors(source: str) -> list[tuple[str, int]]:
    errors: list[tuple[str, int]] = []
    physical_lines: dict[int, list[tuple[tokenize.TokenInfo, int]]] = {}
    depth = 0
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in {tokenize.ENCODING, tokenize.ENDMARKER}:
            continue
        physical_lines.setdefault(token.start[0], []).append((token, depth))
        depth = _track_token_depth(token, depth, errors)
    errors.extend(_compound_body_errors(physical_lines))
    return errors


def _check_adapter_entry(
    *,
    subsystem: Path,
    entry: Any,
    validator: Draft202012Validator,
    errors: list[str],
) -> tuple[str, str] | None:
    adapter_id = str(entry.get("adapter_id"))
    descriptor_path = subsystem / str(entry.get("descriptor"))
    provider_path = subsystem / str(entry.get("provider_module"))
    if not descriptor_path.is_file():
        errors.append(f"{adapter_id}: descriptor missing")
        return None
    if not provider_path.is_file():
        errors.append(f"{adapter_id}: provider module missing")
    descriptor = _load_yaml(descriptor_path)
    for exc in sorted(validator.iter_errors(descriptor), key=lambda item: list(item.path)):
        location = ".".join(str(item) for item in exc.path) or "<root>"
        errors.append(f"{adapter_id}: descriptor {location}: {exc.message}")
    if descriptor.get("adapter_id") != adapter_id:
        errors.append(f"{adapter_id}: descriptor identity mismatch")
    if descriptor.get("adapter_kind") != entry.get("adapter_kind"):
        errors.append(f"{adapter_id}: registry kind mismatch")
    security = descriptor.get("security") or {}
    if any(security.get(key) != value for key, value in REQUIRED_SECURITY.items()):
        errors.append(f"{adapter_id}: security invariants are not locked")
    return adapter_id, _digest(descriptor_path)


def _validate_registry_entries(
    *,
    subsystem: Path,
    entries: list[Any],
    validator: Draft202012Validator,
    errors: list[str],
) -> dict[str, str]:
    ids = [str(item.get("adapter_id")) for item in entries]
    if set(ids) != EXPECTED_ADAPTERS:
        errors.append(
            "registry adapter IDs mismatch: "
            f"missing={sorted(EXPECTED_ADAPTERS - set(ids))}, "
            f"extra={sorted(set(ids) - EXPECTED_ADAPTERS)}"
        )
    if len(ids) != len(set(ids)):
        errors.append("registry contains duplicate adapter IDs")
    digests: dict[str, str] = {}
    for entry in entries:
        checked = _check_adapter_entry(
            subsystem=subsystem,
            entry=entry,
            validator=validator,
            errors=errors,
        )
        if checked is not None:
            digests[checked[0]] = checked[1]
    return digests


def _validate_debris(subsystem: Path, errors: list[str]) -> None:
    for path in subsystem.rglob("*"):
        if path.name in DEBRIS_NAMES:
            errors.append(f"compiled or cache debris: {_relative(path, subsystem)}")
        elif path.is_file() and path.suffix in DEBRIS_SUFFIXES:
            errors.append(f"runtime debris: {_relative(path, subsystem)}")
        elif path.is_symlink():
            errors.append(f"symlink forbidden in subsystem: {_relative(path, subsystem)}")


def _validate_python_file(path: Path, subsystem: Path, errors: list[str]) -> None:
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        errors.append(f"syntax error: {_relative(path, subsystem)}:{exc.lineno}")
    relative = path.relative_to(subsystem)
    if relative.parts[0] == "adapters" and "tests" not in relative.parts:
        for term in FORBIDDEN_SOURCE_TERMS:
            if term in source:
                errors.append(f"forbidden operation {term!r}: {_relative(path, subsystem)}")
    for number, line in enumerate(source.splitlines(), 1):
        if len(line) > 100 and "# noqa: E501" not in line:
            errors.append(
                f"line exceeds 100 characters: {_relative(path, subsystem)}:{number}:{len(line)}"
            )
    for rule, number in _compressed_statement_errors(source):
        errors.append(f"compressed statement {rule}: {_relative(path, subsystem)}:{number}")


def _validate_source_hygiene(*, subsystem: Path, core: Path, errors: list[str]) -> None:
    _validate_debris(subsystem, errors)
    for path in subsystem.rglob("*.py"):
        if core in path.parents:
            continue
        _validate_python_file(path, subsystem, errors)


def _validate_status_locks(entries: list[Any], errors: list[str]) -> None:
    chatgpt = next(
        (item for item in entries if item.get("adapter_id") == "chatgpt-manual-handoff"),
        {},
    )
    if chatgpt.get("status") != "dormant":
        errors.append("ChatGPT manual handoff must remain dormant")
    factory = next(
        (item for item in entries if item.get("adapter_id") == "target-deployment-factory"),
        {},
    )
    if factory.get("status") != "non_routable":
        errors.append("target deployment factory must remain non_routable")


def _validate_integrations(subsystem: Path, errors: list[str]) -> None:
    graphiti = subsystem / "integrations/graphiti/context_reader.py"
    if graphiti.is_file():
        source = graphiti.read_text(encoding="utf-8")
        for forbidden in ("add_memory", "write_memory", "cmd_write"):
            if forbidden in source:
                errors.append(f"Graphiti integration contains write path: {forbidden}")
    if (subsystem / "environment/agents/agent_registry.yaml").exists():
        errors.append("adapter layer must not carry a second agent registry")


def validate(root: str | Path) -> dict[str, Any]:
    subsystem = Path(root).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    evidence: list[dict[str, Any]] = []
    core = subsystem / "core"
    for relative in sorted(REQUIRED_CORE):
        if not (core / relative).is_file():
            errors.append(f"core file missing: {relative}")

    registry_path = subsystem / "registry/EXECUTION_ADAPTER_REGISTRY.yaml"
    schema_path = subsystem / "conformance/schemas/execution-adapter-spec.schema.json"
    if not registry_path.is_file() or not schema_path.is_file():
        errors.append("registry or adapter specification schema is missing")
        return _report(errors, warnings, evidence)

    registry = _load_yaml(registry_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    entries = registry.get("adapters") or []
    descriptor_digests = _validate_registry_entries(
        subsystem=subsystem,
        entries=entries,
        validator=validator,
        errors=errors,
    )
    if registry.get("schema") != "program-execution-adapter.registry.v1":
        errors.append("registry schema identifier mismatch")
    _validate_status_locks(entries, errors)

    core_schema_names = {
        path.name
        for path in (core / "program-execution-controller-template/schemas").glob("*.json")
    }
    adapter_schema_names = {
        path.name for path in (subsystem / "conformance/schemas").glob("*.json")
    }
    duplicates = sorted(core_schema_names & adapter_schema_names)
    if duplicates:
        errors.append(f"canonical core schemas duplicated: {duplicates}")

    _validate_source_hygiene(subsystem=subsystem, core=core, errors=errors)
    _validate_integrations(subsystem, errors)
    evidence.append({"type": "descriptor_digests", "values": descriptor_digests})
    return _report(errors, warnings, evidence)


def _report(
    errors: list[str],
    warnings: list[str],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "program-execution-adapter.validation-report.v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    report = validate(root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
