#!/usr/bin/env python3
"""Deterministic, secret-safe pre-existing-debt baseline auditor (stdlib only).

================================================================================
Module: debt_audit
Purpose: Record a fail-closed, secret-free pre-existing debt baseline for remediation.
================================================================================

Summary:
    Detects a repository's owned toolchain (Python: ruff/mypy/pytest; Node:
    eslint/tsc/tests/build), records preferred invocations, runs runnable gates, and
    writes a secret-free JSON baseline snapshot (`debt-baseline.json` by convention).

Extended Metadata:
    See __footer_meta__ at module footer for full governance, classification,
    and audit metadata. Runtime trace in __l9_trace__ at very end.

================================================================================
# HEADER META - Module Identity (Static)
# component_id: SKILL-PRREM-DEBT-001
# layer: skill
# domain: pr-remediation
# governance_level: standard
# created_at: 2026-08-04
================================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

TRUNCATE = 4000
RUN_TIMEOUT = 300

PY_MARKERS = ("pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "tox.ini")
NODE_MARKERS = ("package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json")
PY_EXTS = (".py",)
NODE_EXTS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".tox",
    "coverage",
    ".next",
}

# Suppression markers whose UNEXPLAINED proliferation is debt, not a fix.
SUPPRESSION_PATTERNS = {
    "noqa": re.compile(r"#\s*noqa"),
    "type_ignore": re.compile(r"#\s*type:\s*ignore"),
    "eslint_disable": re.compile(r"//\s*eslint-disable|/\*\s*eslint-disable"),
    "ts_expect_error": re.compile(r"@ts-(?:expect-error|ignore|nocheck)"),
}

# A gate that exits 0 while its own output says otherwise is a false pass, not a pass.
FALSE_PASS_MARKERS = (
    "traceback (most recent call last)",
    "no files checked",
    "0 files checked",
    "found 0 source files",
    "no such file or directory",
    "command not found",
)

# Redact anything that looks like a token so a misconfigured tool cannot leak one.
_TOKEN_RE = re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[=:]\s*\S+")


def _validated_output(value: str) -> Path:
    """Require --output to stay within the working directory (S8707 / traversal)."""
    base = Path.cwd().resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def _validated_repo(value: str) -> Path:
    repo = Path(value).resolve()
    if not repo.is_dir():
        raise SystemExit(f"BLOCKED: --repo is not a directory: {value}")
    return repo


def _redact(text: str) -> str:
    return _TOKEN_RE.sub(r"\1=REDACTED", text)[:TRUNCATE]


def _has_any(repo: Path, names: tuple[str, ...]) -> bool:
    return any((repo / name).exists() for name in names)


def detect_languages(repo: Path) -> list[str]:
    languages: list[str] = []
    if _has_any(repo, PY_MARKERS):
        languages.append("python")
    node = _has_any(repo, NODE_MARKERS) or any(
        (repo / cfg).exists()
        for cfg in ("tsconfig.json", "eslint.config.js", "eslint.config.mjs", ".eslintrc.json")
    )
    if node:
        languages.append("node")
    return languages


def _run(argv: list[str], cwd: Path) -> dict:
    """Run a fixed-argv command (never a shell string) and capture a bounded result."""
    if shutil.which(argv[0]) is None:
        return {"available": False, "exit_code": None, "output": "", "command": " ".join(argv)}
    try:
        proc = subprocess.run(  # noqa: S603 (fixed argv allowlist, no shell)
            argv, cwd=cwd, capture_output=True, text=True, timeout=RUN_TIMEOUT, check=False
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "available": True,
            "exit_code": None,
            "output": f"RUN_ERROR: {exc}",
            "command": " ".join(argv),
        }
    combined = _redact((proc.stdout or "") + (proc.stderr or ""))
    return {
        "available": True,
        "exit_code": proc.returncode,
        "output": combined,
        "command": " ".join(argv),
    }


def _tool_version(tool: str) -> str | None:
    if shutil.which(tool) is None:
        return None
    try:
        proc = subprocess.run(  # noqa: S603 (fixed argv allowlist, no shell)
            [tool, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return (proc.stdout or proc.stderr or "").strip()[:120] or None


def _false_pass_signals(record: dict) -> list[str]:
    if record["exit_code"] != 0:
        return []
    lowered = record["output"].lower()
    return [marker for marker in FALSE_PASS_MARKERS if marker in lowered]


def _make_targets(repo: Path) -> set[str]:
    makefile = repo / "Makefile"
    if not makefile.exists():
        return set()
    text = makefile.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"^([A-Za-z0-9][\w-]*):", text, re.MULTILINE))


def _package_scripts(repo: Path) -> dict[str, str]:
    package = repo / "package.json"
    if not package.exists():
        return {}
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    scripts = data.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def python_gates(repo: Path) -> list[dict]:
    ruff_configured = (
        (repo / "ruff.toml").exists()
        or (repo / ".ruff.toml").exists()
        or (
            "[tool.ruff]" in (repo / "pyproject.toml").read_text(encoding="utf-8", errors="replace")
            if (repo / "pyproject.toml").exists()
            else False
        )
    )
    gates = [
        {"id": "ruff_check", "argv": ["ruff", "check", "."], "required": True},
        {"id": "mypy", "argv": ["mypy", "."], "required": True},
        {"id": "pytest", "argv": ["pytest", "-q"], "required": True},
    ]
    if ruff_configured:
        gates.insert(
            1,
            {
                "id": "ruff_format_check",
                "argv": ["ruff", "format", "--check", "."],
                "required": True,
            },
        )
    return gates


def node_gates(repo: Path) -> list[dict]:
    scripts = _package_scripts(repo)
    installed = (repo / "node_modules").is_dir()
    gates: list[dict] = []
    if "lint" in scripts:
        gates.append({"id": "eslint", "argv": ["npm", "run", "lint"], "required": True})
    else:
        gates.append(
            {"id": "eslint", "argv": ["npx", "--no-install", "eslint", "."], "required": True}
        )
    if (repo / "tsconfig.json").exists():
        gates.append(
            {"id": "tsc", "argv": ["npx", "--no-install", "tsc", "--noEmit"], "required": True}
        )
    if "test" in scripts:
        gates.append({"id": "tests", "argv": ["npm", "test"], "required": True})
    if "build" in scripts:
        gates.append({"id": "build", "argv": ["npm", "run", "build"], "required": True})
    for gate in gates:
        gate["needs_install"] = not installed
    return gates


def count_suppressions(repo: Path, languages: list[str]) -> dict[str, int]:
    exts = set()
    if "python" in languages:
        exts.update(PY_EXTS)
    if "node" in languages:
        exts.update(NODE_EXTS)
    counts = dict.fromkeys(SUPPRESSION_PATTERNS, 0)
    # Prune SKIP_DIRS during walk so we never descend into node_modules/.git/etc.
    for root, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = Path(root) / filename
            if path.suffix not in exts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for name, pattern in SUPPRESSION_PATTERNS.items():
                counts[name] += len(pattern.findall(text))
    return counts


def _git_head(repo: Path) -> str | None:
    result = _run(["git", "-C", str(repo), "rev-parse", "HEAD"], cwd=repo)
    if result["available"] and result["exit_code"] == 0:
        return result["output"].strip() or None
    return None


def run_gates(repo: Path, gates: list[dict]) -> list[dict]:
    records: list[dict] = []
    for gate in gates:
        if gate.get("needs_install"):
            records.append(
                {
                    "id": gate["id"],
                    "required": gate["required"],
                    "command": " ".join(gate["argv"]),
                    "status": "UNAVAILABLE_NEEDS_INSTALL",
                    "exit_code": None,
                    "false_pass_signals": [],
                    "output": "",
                }
            )
            continue
        result = _run(gate["argv"], cwd=repo)
        if not result["available"]:
            status = "UNAVAILABLE"
        elif result["exit_code"] is None:
            status = "ERROR"
        else:
            status = "PASS" if result["exit_code"] == 0 else "FAIL"
        signals = _false_pass_signals(result) if result["available"] else []
        if signals:
            status = "FALSE_PASS"
        records.append(
            {
                "id": gate["id"],
                "required": gate["required"],
                "command": result["command"],
                "status": status,
                "exit_code": result["exit_code"],
                "false_pass_signals": signals,
                "output": result["output"],
            }
        )
    return records


def _overall_status(languages: list[str], records: list[dict]) -> str:
    if not languages:
        return "BLOCKED"
    ran = [r for r in records if r["status"] in {"PASS", "FAIL", "FALSE_PASS"}]
    if not ran:
        return "PARTIAL"
    return "COMPLETE"


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a secret-free pre-existing-debt baseline.")
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--output", required=True, help="snapshot path (must stay in the tree)")
    parser.add_argument(
        "--language",
        choices=["python", "node", "mixed", "auto"],
        default="auto",
        help="override detection; 'auto' inspects marker files",
    )
    args = parser.parse_args()

    repo = _validated_repo(args.repo)
    output_path = _validated_output(args.output)

    if args.language == "auto":
        languages = detect_languages(repo)
    elif args.language == "mixed":
        languages = ["python", "node"]
    else:
        languages = [args.language]

    gates: list[dict] = []
    if "python" in languages:
        gates.extend(python_gates(repo))
    if "node" in languages:
        gates.extend(node_gates(repo))

    records = run_gates(repo, gates)
    suppressions = count_suppressions(repo, languages) if languages else {}
    status = _overall_status(languages, records)

    versions = {}
    for tool in ("ruff", "mypy", "pytest", "node", "npx", "git"):
        version = _tool_version(tool)
        if version:
            versions[tool] = version

    failing = [r["id"] for r in records if r["status"] in {"FAIL", "FALSE_PASS", "ERROR"}]
    debt_present = bool(failing) or any(v > 0 for v in suppressions.values())

    snapshot = {
        "schema_version": "debt-baseline-1.0",
        "status": status,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "repository": str(repo),
        "head_sha": _git_head(repo),
        "languages": languages,
        "tool_versions": versions,
        "preferred_invocation": {
            "make_targets": sorted(_make_targets(repo)),
            "package_scripts": sorted(_package_scripts(repo)),
        },
        "gates": records,
        "suppression_counts": suppressions,
        "failing_gates": failing,
        "debt_present": debt_present,
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(
        f"baseline: {output_path} status={status} languages={','.join(languages) or 'none'} "
        f"failing={len(failing)} debt_present={debt_present}"
    )
    if status == "BLOCKED":
        print("BLOCKED: no supported toolchain detected (pass --language to override)")
        return 2
    return 0


__footer_meta__ = {
    "component_id": "SKILL-PRREM-DEBT-001",
    "component_name": "debt_audit",
    "module_version": "1.0.0",
    "created_at": "2026-08-04",
    "created_by": "l9-pr-remediation",
    "layer": "skill",
    "domain": "pr-remediation",
    "type": "cli_script",
    "status": "active",
    "governance_level": "standard",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Fail-closed pre-existing debt baseline auditor",
    "summary": "Stdlib-only debt baseline snapshot for l9-pr-remediation",
    "dependencies": [],
}

__all__ = [
    "main",
    "count_suppressions",
    "detect_languages",
    "run_gates",
    "__footer_meta__",
    "__l9_trace__",
]

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# ============================================================================

__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {
        "confidence": "",
        "errors_detected": [],
        "stability_score": "",
    },
}

# ============================================================================
# END L9 DORA BLOCK
# ============================================================================


if __name__ == "__main__":
    raise SystemExit(main())
