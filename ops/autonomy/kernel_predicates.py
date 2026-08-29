"""Cheap structural predicates for the tree-kernel apply report.

These do not prove judgment. They prove the agent produced a real
path-confined apply artifact whose hash and delta paths still hold.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

APPLY_SCHEMA = "l9.kernel_apply.v1"
APPLY_DIR_REL = Path(".l9") / "autonomy"
APPLY_REL = APPLY_DIR_REL / "kernel-apply.md"
ALLOWED_KERNELS = frozenset({"recursive_alignment", "validate_repair"})
CONVERGENCE_STATUSES = frozenset({"converged", "partial", "blocked"})
PREDICATE_IDS: tuple[str, ...] = (
    "report_structure",
    "report_sha",
    "delta_paths_exist",
)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
HEADING_RA = "Recursive Alignment"
HEADING_VR = "Validate & Repair"

try:
    import yaml
except ImportError:  # pragma: no cover - gov venv has PyYAML
    yaml = None  # type: ignore[assignment]


class ReportError(ValueError):
    """Apply-report contract failure."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confine_report_path(root: Path, report: Path) -> Path:
    """Resolve report and refuse any path that leaves workspace/.l9/autonomy/."""
    root_r = root.resolve()
    allowed = (root_r / APPLY_DIR_REL).resolve()
    candidate = report.expanduser() if report.is_absolute() else (root_r / report)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise ReportError(f"report path escapes {allowed}: {resolved}") from exc
    return resolved


def parse_apply_report(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if match is None:
        raise ReportError("apply report missing YAML frontmatter")
    if yaml is None:
        raise ReportError("PyYAML is required to parse the apply report")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ReportError("apply report frontmatter must be a mapping")
    body = raw[match.end() :]
    data["_body"] = body
    return data


def report_structure(root: Path, report: Path) -> list[str]:
    errors: list[str] = []
    try:
        confined = confine_report_path(root, report)
    except ReportError as exc:
        return [str(exc)]
    if not confined.is_file():
        return [f"apply report missing: {confined}"]
    try:
        data = parse_apply_report(confined)
    except (OSError, ReportError) as exc:
        return [str(exc)]
    if data.get("schema") != APPLY_SCHEMA:
        errors.append(f"apply report schema must be {APPLY_SCHEMA}")
    kernels = data.get("kernels")
    if not isinstance(kernels, list):
        errors.append("apply report kernels must be a list")
        kernel_set: set[str] = set()
    else:
        kernel_set = {str(item).strip() for item in kernels if str(item).strip()}
        if not ALLOWED_KERNELS.issubset(kernel_set):
            errors.append(
                "apply report kernels must include recursive_alignment and validate_repair"
            )
    status = str(data.get("convergence_status") or "").strip()
    if status not in CONVERGENCE_STATUSES:
        errors.append("apply report convergence_status must be converged|partial|blocked")
    body = str(data.get("_body") or "")
    if HEADING_RA not in body:
        errors.append(f"apply report body missing heading {HEADING_RA!r}")
    if HEADING_VR not in body:
        errors.append(f"apply report body missing heading {HEADING_VR!r}")
    delta_errors, _ = _normalized_deltas(data.get("deltas"))
    errors.extend(delta_errors)
    return errors


def _normalized_deltas(raw: object) -> tuple[list[str], list[dict[str, str]]]:
    errors: list[str] = []
    if not isinstance(raw, list) or not raw:
        return ["apply report deltas must be a non-empty list"], []
    out: list[dict[str, str]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"apply report deltas[{idx}] must be a mapping")
            continue
        path = str(item.get("path") or "").strip()
        kernel = str(item.get("kernel") or "").strip()
        note = str(item.get("note") or "").strip()
        if not path:
            errors.append(f"apply report deltas[{idx}].path is empty")
        if kernel not in ALLOWED_KERNELS:
            errors.append(
                f"apply report deltas[{idx}].kernel must be recursive_alignment or validate_repair"
            )
        if not note:
            errors.append(f"apply report deltas[{idx}].note is empty")
        if path and kernel in ALLOWED_KERNELS and note:
            out.append({"path": path, "kernel": kernel, "note": note})
    return errors, out


def delta_paths_exist(root: Path, deltas: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    root_r = root.resolve()
    for item in deltas:
        rel = item["path"].strip()
        if rel.startswith("./"):
            rel = rel[2:]
        parts = Path(rel).parts
        if not rel or rel.startswith("/") or ".." in parts:
            errors.append(f"delta path is not workspace-relative: {item['path']}")
            continue
        candidate = root_r / rel
        if not candidate.exists():
            errors.append(f"delta path does not exist: {rel}")
    return errors


def report_sha(path: Path, expected: str) -> list[str]:
    if not path.is_file():
        return [f"apply report missing for sha check: {path}"]
    live = sha256_file(path)
    claimed = (expected or "").strip()
    if not claimed:
        return ["receipt report_sha256 is unset"]
    if live != claimed:
        return ["apply report sha does not match receipt report_sha256"]
    return []


def load_validated_deltas(root: Path, report: Path) -> list[dict[str, str]]:
    confined = confine_report_path(root, report)
    if not confined.is_file():
        raise ReportError(f"apply report missing: {confined}")
    data = parse_apply_report(confined)
    struct = report_structure(root, confined)
    if struct:
        raise ReportError("; ".join(struct))
    _errs, deltas = _normalized_deltas(data.get("deltas"))
    missing = delta_paths_exist(root, deltas)
    if missing:
        raise ReportError("; ".join(missing))
    return deltas


def run_predicates(root: Path, receipt: dict[str, Any]) -> list[str]:
    """Re-run the three structural predicates against live files."""
    raw_rel = str(receipt.get("report_rel") or "").strip()
    if not raw_rel:
        return ["receipt report_rel is unset"]
    report = Path(raw_rel)
    errors: list[str] = []
    try:
        confined = confine_report_path(root, report)
    except ReportError as exc:
        return [str(exc)]
    errors.extend(report_structure(root, confined))
    errors.extend(report_sha(confined, str(receipt.get("report_sha256") or "")))
    if not errors:
        try:
            data = parse_apply_report(confined)
        except ReportError as exc:
            return [str(exc)]
        _delta_errs, deltas = _normalized_deltas(data.get("deltas"))
        errors.extend(delta_paths_exist(root, deltas))
    return errors
