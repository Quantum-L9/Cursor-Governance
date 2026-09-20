"""Cheap structural predicates for the tree-kernel apply report.

These do not prove judgment. They prove the agent produced a real
path-confined apply artifact whose hash and delta paths still hold.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from ops.autonomy.receipt_binding import sha256_file
except ImportError:  # pragma: no cover - script invocation from ops/autonomy
    from receipt_binding import sha256_file

APPLY_SCHEMA_V1 = "l9.kernel_apply.v1"
APPLY_SCHEMA_V2 = "l9.kernel_apply.v2"
# Accept both v1 and v2 during transition; new reports should use v2
APPLY_SCHEMA = APPLY_SCHEMA_V2
ACCEPTED_SCHEMAS = frozenset({APPLY_SCHEMA_V1, APPLY_SCHEMA_V2})
APPLY_DIR_REL = Path(".l9") / "autonomy"
APPLY_REL = APPLY_DIR_REL / "kernel-apply.md"
ALLOWED_KERNELS = frozenset({"recursive_alignment", "validate_repair"})
CONVERGENCE_STATUSES = frozenset({"converged", "partial", "blocked"})

# Finding ledger constraints (Phase 2)
FINDING_SEVERITIES = frozenset({"Critical", "High", "Medium", "Low"})
FINDING_CONFIDENCES = frozenset({"Confirmed", "Probable", "Possible", "Unknown"})
FINDING_STATUSES = frozenset(
    {
        "Open",
        "Resolved",
        "AcceptedRisk",
        "FalsePositive",
        "OutOfScope",
        "Blocked",
        "Unknown",
    }
)
# Statuses that can coexist with converged (no open Critical/High)
CONVERGENCE_BLOCKING_STATUSES = frozenset({"Open"})
CONVERGENCE_BLOCKING_SEVERITIES = frozenset({"Critical", "High"})
# Minimum passes that must be run for a valid report
REQUIRED_PASSES = frozenset(
    {
        "context_and_scope_lock",
        "reconciliation_and_convergence",
    }
)
PREDICATE_IDS: tuple[str, ...] = (
    # Phase 1 (mechanical)
    "report_structure",
    "report_sha",
    "delta_paths_exist",
    "deltas_cover_diff",
    "both_kernels_have_deltas",
    "notes_not_template",
    "headings_are_atx",
    "closed_frontmatter",
    "no_duplicate_delta_paths",
    # Phase 2 (finding ledger - v2 only)
    "findings_nonempty_or_explicit_clean",
    "finding_paths_exist",
    "finding_rules_exist",
    "resolved_has_close_validation",
    "convergence_derived",
    "passes_run_minimum",
    "unknowns_key_required",
    # Phase 3 (seed findings)
    "seed_findings_present",
)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
HEADING_RA = "Recursive Alignment"
HEADING_VR = "Validate & Repair"
HEADING_RA_RE = re.compile(r"^##\s+Recursive Alignment\s*$", re.MULTILINE)
HEADING_VR_RE = re.compile(r"^##\s+Validate & Repair\s*$", re.MULTILINE)

# Prefixes exempt from delta coverage check (corpus + generated artifacts).
# Corpus kernels fire on /ff shelf, not at precommit.
CORPUS_SKIP_PREFIXES: tuple[str, ...] = (
    "WIP/",
    "docs/plans/",
    "environment/program-execution/campaigns/",
)
# Generated artifacts are exempt because they are regenerated, not authored.
GENERATED_PATH_PREFIXES: tuple[str, ...] = (
    "rules/RULES-MANIFEST.",
    "environment/generated/llm-rules/",
    "ops/generated/skill-registry.json",
    "environment/agents/adapters/claude-code/generated/skill-registry.json",
    "environment/agents/adapters/claude-code/settings.template.json",
    ".claude/settings.json",
    "commands/COMMANDS_MANIFEST.yaml",
    "skills/AUTONOMY_MANIFEST.yaml",
    "environment/program-execution/core/MANIFEST.yaml",
    "environment/program-execution/core/program-execution-blueprint-template/MANIFEST.yaml",
    "environment/program-execution/core/program-execution-controller-template/MANIFEST.yaml",
    "environment/program-execution/MANIFEST.json",
)

# Allowed keys in the apply report frontmatter. Extra keys are rejected.
ALLOWED_FRONTMATTER_KEYS: frozenset[str] = frozenset(
    {
        "schema",
        "kernels",
        "convergence_status",
        "deltas",
        "findings",
        "validation",
        "unknowns",
        "passes_run",
        "passes_skipped",
        "audit_scope",
    }
)

# Template note placeholders that should be rejected.
TEMPLATE_NOTE_PATTERNS: tuple[str, ...] = (
    "what the kernel changed and why",
    "narrowed the guard",
    "one entry per file you actually changed",
)

try:
    import yaml
except ImportError:  # pragma: no cover - gov venv has PyYAML
    yaml = None  # type: ignore[assignment]


class ReportError(ValueError):
    """Apply-report contract failure."""


# sha256_file is re-exported from receipt_binding, which owns
# canonicalize-then-digest for every receipt plane. Imported rather than
# reimplemented so this module's binding cannot drift from the others'.
__all__ = [
    "ACCEPTED_SCHEMAS",
    "APPLY_REL",
    "APPLY_SCHEMA",
    "APPLY_SCHEMA_V1",
    "APPLY_SCHEMA_V2",
    "PREDICATE_IDS",
    "ReportError",
    "both_kernels_have_deltas",
    "closed_frontmatter",
    "confine_report_path",
    "convergence_derived",
    "delta_paths_exist",
    "deltas_cover_diff",
    "finding_paths_exist",
    "finding_rules_exist",
    "findings_nonempty_or_explicit_clean",
    "headings_are_atx",
    "load_validated_deltas",
    "no_duplicate_delta_paths",
    "notes_not_template",
    "passes_run_minimum",
    "report_sha",
    "report_structure",
    "resolved_has_close_validation",
    "run_predicates",
    "run_predicates_with_diff",
    "seed_findings",
    "seed_findings_present",
    "sha256_file",
    "unknowns_key_required",
]


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
    schema = data.get("schema")
    if schema not in ACCEPTED_SCHEMAS:
        errors.append(f"apply report schema must be one of {sorted(ACCEPTED_SCHEMAS)}")
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
    # Use ATX heading regex check instead of substring
    errors.extend(headings_are_atx(body))
    # Check for unexpected frontmatter keys
    errors.extend(closed_frontmatter(data))
    delta_errors, deltas = _normalized_deltas(data.get("deltas"))
    errors.extend(delta_errors)
    # Check delta-level predicates
    if deltas:
        errors.extend(both_kernels_have_deltas(deltas))
        errors.extend(notes_not_template(deltas))
        errors.extend(no_duplicate_delta_paths(deltas))
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
    """Check that every delta path exists as a regular file (not directory/symlink)."""
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
        if not candidate.is_file():
            if candidate.is_dir():
                errors.append(f"delta path is a directory, not a file: {rel}")
            elif candidate.is_symlink():
                errors.append(f"delta path is a dangling symlink: {rel}")
            else:
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


def _is_exempt_path(rel: str) -> bool:
    """Check if a path is exempt from delta coverage (corpus or generated)."""
    for prefix in CORPUS_SKIP_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return True
    for prefix in GENERATED_PATH_PREFIXES:
        if rel.startswith(prefix) or rel == prefix.rstrip("."):
            return True
    return False


def deltas_cover_diff(deltas: list[dict[str, str]], changed_paths: list[str]) -> list[str]:
    """Check that deltas cover all changed paths (minus exempt prefixes)."""
    errors: list[str] = []
    delta_paths = {item["path"].strip().lstrip("./") for item in deltas}
    changed_set = {p.strip().lstrip("./") for p in changed_paths if p.strip()}

    # Paths in the change set that are not exempt must appear in deltas
    for path in changed_set:
        if _is_exempt_path(path):
            continue
        if path not in delta_paths:
            errors.append(f"changed path not in deltas: {path}")

    # Paths in deltas that are not in the change set are invented (unless exempt)
    for path in delta_paths:
        if _is_exempt_path(path):
            continue
        # Allow the report itself as a delta when nothing else changed
        if path == APPLY_REL.as_posix():
            continue
        if path not in changed_set:
            errors.append(f"delta path not in changed set (invented?): {path}")

    return errors


def both_kernels_have_deltas(deltas: list[dict[str, str]]) -> list[str]:
    """Check that both kernels have at least one delta each."""
    errors: list[str] = []
    kernels_with_deltas: set[str] = set()
    for item in deltas:
        kernel = item.get("kernel", "").strip()
        if kernel in ALLOWED_KERNELS:
            kernels_with_deltas.add(kernel)

    missing = ALLOWED_KERNELS - kernels_with_deltas
    for kernel in sorted(missing):
        errors.append(f"no deltas for kernel: {kernel}")

    return errors


def notes_not_template(deltas: list[dict[str, str]]) -> list[str]:
    """Check that delta notes are not template boilerplate."""
    errors: list[str] = []
    for idx, item in enumerate(deltas):
        note = item.get("note", "").strip().lower()
        if not note:
            continue
        for pattern in TEMPLATE_NOTE_PATTERNS:
            if pattern.lower() in note or note in pattern.lower():
                errors.append(f"delta[{idx}].note is template boilerplate: {item.get('note')!r}")
                break
    return errors


def headings_are_atx(body: str) -> list[str]:
    """Check that kernel headings are proper ATX format (## Heading)."""
    errors: list[str] = []
    if not HEADING_RA_RE.search(body):
        errors.append(
            "apply report body missing ATX heading '## Recursive Alignment' "
            "(found substring but not proper heading)"
            if HEADING_RA in body
            else f"apply report body missing heading {HEADING_RA!r}"
        )
    if not HEADING_VR_RE.search(body):
        errors.append(
            "apply report body missing ATX heading '## Validate & Repair' "
            "(found substring but not proper heading)"
            if HEADING_VR in body
            else f"apply report body missing heading {HEADING_VR!r}"
        )
    return errors


def closed_frontmatter(data: dict[str, Any]) -> list[str]:
    """Check that frontmatter contains only allowed keys."""
    errors: list[str] = []
    # _body is internal; skip it
    for key in data:
        if key == "_body":
            continue
        if key not in ALLOWED_FRONTMATTER_KEYS:
            errors.append(f"unexpected frontmatter key: {key!r}")
    return errors


def no_duplicate_delta_paths(deltas: list[dict[str, str]]) -> list[str]:
    """Check that no delta path appears more than once."""
    errors: list[str] = []
    seen: set[str] = set()
    for item in deltas:
        path = item.get("path", "").strip().lstrip("./")
        if not path:
            continue
        if path in seen:
            errors.append(f"duplicate delta path: {path}")
        seen.add(path)
    return errors


def run_predicates(
    root: Path, receipt: dict[str, Any], changed_paths: list[str] | None = None
) -> list[str]:
    """Re-run structural predicates against live files."""
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
        # Phase 1 hardening predicates
        errors.extend(both_kernels_have_deltas(deltas))
        errors.extend(notes_not_template(deltas))
        errors.extend(no_duplicate_delta_paths(deltas))
        errors.extend(headings_are_atx(str(data.get("_body") or "")))
        errors.extend(closed_frontmatter(data))
        # Phase 2 predicates (v2 only), plus Phase 3 seeds when a change set is known
        errors.extend(run_v2_predicates(root, data, changed_paths=changed_paths))
        if changed_paths is not None:
            errors.extend(deltas_cover_diff(deltas, changed_paths))
    return errors


def run_predicates_with_diff(
    root: Path, receipt: dict[str, Any], changed_paths: list[str]
) -> list[str]:
    """Re-run predicates including diff coverage and seed checks."""
    return run_predicates(root, receipt, changed_paths=changed_paths)


# -----------------------------------------------------------------------------
# Phase 2: Finding ledger predicates (v2 only)
# -----------------------------------------------------------------------------


def _normalize_finding(idx: int, item: object) -> tuple[list[str], dict[str, Any] | None]:
    """Normalize and validate a single finding entry."""
    errors: list[str] = []
    if not isinstance(item, dict):
        return [f"finding[{idx}] must be a mapping"], None

    finding: dict[str, Any] = {}

    # Required fields
    fid = str(item.get("id") or "").strip()
    if not fid:
        errors.append(f"finding[{idx}].id is empty")
    finding["id"] = fid

    kernel = str(item.get("kernel") or "").strip()
    if kernel not in ALLOWED_KERNELS:
        errors.append(f"finding[{idx}].kernel must be recursive_alignment or validate_repair")
    finding["kernel"] = kernel

    path = str(item.get("path") or "").strip()
    if not path:
        errors.append(f"finding[{idx}].path is empty")
    finding["path"] = path

    severity = str(item.get("severity") or "").strip()
    if severity not in FINDING_SEVERITIES:
        errors.append(f"finding[{idx}].severity must be one of {sorted(FINDING_SEVERITIES)}")
    finding["severity"] = severity

    confidence = str(item.get("confidence") or "").strip()
    if confidence not in FINDING_CONFIDENCES:
        errors.append(f"finding[{idx}].confidence must be one of {sorted(FINDING_CONFIDENCES)}")
    finding["confidence"] = confidence

    rule = str(item.get("rule") or "").strip()
    if not rule:
        errors.append(f"finding[{idx}].rule is empty")
    finding["rule"] = rule

    evidence = str(item.get("evidence") or "").strip()
    if not evidence:
        errors.append(f"finding[{idx}].evidence is empty")
    finding["evidence"] = evidence

    status = str(item.get("status") or "").strip()
    if status not in FINDING_STATUSES:
        errors.append(f"finding[{idx}].status must be one of {sorted(FINDING_STATUSES)}")
    finding["status"] = status

    # Optional: close_validation (required when status is Resolved)
    close_validation = str(item.get("close_validation") or "").strip()
    finding["close_validation"] = close_validation

    return errors, finding if not errors else None


def findings_nonempty_or_explicit_clean(data: dict[str, Any]) -> list[str]:
    """Check that findings exist or audit_scope+passes_run explain a clean state."""
    errors: list[str] = []
    findings = data.get("findings")

    # v1 reports don't need findings
    if data.get("schema") == APPLY_SCHEMA_V1:
        return []

    if findings is None:
        errors.append(
            "v2 report requires 'findings' key (use empty list with audit_scope for clean)"
        )
        return errors

    if not isinstance(findings, list):
        errors.append("findings must be a list")
        return errors

    if not findings:
        # Empty findings requires audit_scope and passes_run to explain why
        audit_scope = data.get("audit_scope")
        passes_run = data.get("passes_run")
        if not audit_scope:
            errors.append(
                "empty findings requires 'audit_scope' explaining why no findings were generated"
            )
        if not isinstance(passes_run, list) or not passes_run:
            errors.append(
                "empty findings requires 'passes_run' listing what passes confirmed no issues"
            )

    return errors


def finding_paths_exist(root: Path, findings: list[dict[str, Any]]) -> list[str]:
    """Check that all finding paths exist as files."""
    errors: list[str] = []
    root_r = root.resolve()
    for finding in findings:
        path = finding.get("path", "").strip().lstrip("./")
        if not path:
            continue
        candidate = root_r / path
        if not candidate.is_file():
            errors.append(f"finding path does not exist: {path}")
    return errors


def finding_rules_exist(root: Path, findings: list[dict[str, Any]]) -> list[str]:
    """Check that finding rules exist as files or are known rule IDs."""
    errors: list[str] = []
    root_r = root.resolve()

    # Known rule ID patterns that don't require file existence
    known_patterns = frozenset(
        {
            "CANONICAL_LAW.md",
            "AGENTS.md",
            "ORG_INVARIANTS.yaml",
        }
    )

    for finding in findings:
        rule = finding.get("rule", "").strip()
        if not rule:
            continue

        # Accept known governance doc references
        if rule in known_patterns:
            continue

        # Accept rule references like "rules/XX-name.mdc"
        if rule.startswith("rules/") and rule.endswith(".mdc"):
            rule_path = root_r / rule
            if not rule_path.is_file():
                errors.append(f"finding rule file does not exist: {rule}")
            continue

        # Accept path-based rules (e.g., kernels/Recursive Alignment.md)
        if "/" in rule:
            rule_path = root_r / rule
            if not rule_path.is_file():
                errors.append(f"finding rule file does not exist: {rule}")
            continue

        # Accept inline rule-ids (e.g., L9-ORG-001)
        if rule.startswith("L9-") or rule.startswith("INV-"):
            continue

        errors.append(f"finding rule not recognized: {rule}")

    return errors


def resolved_has_close_validation(findings: list[dict[str, Any]]) -> list[str]:
    """Check that Resolved findings have close_validation."""
    errors: list[str] = []
    for finding in findings:
        status = finding.get("status", "").strip()
        if status == "Resolved":
            close = finding.get("close_validation", "").strip()
            if not close:
                fid = finding.get("id", "?")
                errors.append(f"finding {fid} is Resolved but has no close_validation")
    return errors


def convergence_derived(data: dict[str, Any], findings: list[dict[str, Any]]) -> list[str]:
    """Check that convergence_status is consistent with finding states."""
    errors: list[str] = []
    status = str(data.get("convergence_status") or "").strip()

    # v1 reports don't have this constraint enforced
    if data.get("schema") == APPLY_SCHEMA_V1:
        return []

    # Can't claim converged if there are Open Critical/High findings
    if status == "converged":
        blocking_findings = []
        for finding in findings:
            f_status = finding.get("status", "").strip()
            f_severity = finding.get("severity", "").strip()
            if (
                f_status in CONVERGENCE_BLOCKING_STATUSES
                and f_severity in CONVERGENCE_BLOCKING_SEVERITIES
            ):
                blocking_findings.append(finding.get("id", "?"))

        if blocking_findings:
            severities = list(CONVERGENCE_BLOCKING_SEVERITIES)
            errors.append(
                f"convergence_status is 'converged' but has Open {severities} "
                f"findings: {blocking_findings}"
            )

    return errors


def passes_run_minimum(data: dict[str, Any]) -> list[str]:
    """Check that required passes were run."""
    errors: list[str] = []

    # v1 reports don't require passes
    if data.get("schema") == APPLY_SCHEMA_V1:
        return []

    passes = data.get("passes_run")
    if passes is None:
        errors.append("v2 report requires 'passes_run' key")
        return errors

    if not isinstance(passes, list):
        errors.append("passes_run must be a list")
        return errors

    passes_set = {str(p).strip() for p in passes}
    missing = REQUIRED_PASSES - passes_set
    for name in sorted(missing):
        errors.append(f"required pass not run: {name}")

    return errors


def unknowns_key_required(data: dict[str, Any]) -> list[str]:
    """Check that unknowns key exists (even if empty list)."""
    errors: list[str] = []

    # v1 reports don't require unknowns
    if data.get("schema") == APPLY_SCHEMA_V1:
        return []

    if "unknowns" not in data:
        errors.append("v2 report requires 'unknowns' key (use empty list if none)")

    return errors


def run_v2_predicates(
    root: Path, data: dict[str, Any], changed_paths: list[str] | None = None
) -> list[str]:
    """Run Phase 2 predicates for v2 reports, and Phase 3 seeds when given."""
    errors: list[str] = []

    # Skip v2 predicates for v1 reports
    if data.get("schema") == APPLY_SCHEMA_V1:
        return []

    # Parse findings
    raw_findings = data.get("findings") or []
    findings: list[dict[str, Any]] = []
    if isinstance(raw_findings, list):
        for idx, item in enumerate(raw_findings):
            f_errors, finding = _normalize_finding(idx, item)
            errors.extend(f_errors)
            if finding:
                findings.append(finding)

    # Run Phase 2 predicates
    errors.extend(findings_nonempty_or_explicit_clean(data))
    errors.extend(finding_paths_exist(root, findings))
    errors.extend(finding_rules_exist(root, findings))
    errors.extend(resolved_has_close_validation(findings))
    errors.extend(convergence_derived(data, findings))
    errors.extend(passes_run_minimum(data))
    errors.extend(unknowns_key_required(data))
    if changed_paths is not None:
        errors.extend(seed_findings_present(findings, seed_findings(changed_paths)))

    return errors


# -----------------------------------------------------------------------------
# Phase 3: Seed findings from git changes
# -----------------------------------------------------------------------------

# Paths that require test coverage when modified
REQUIRES_TEST_COVERAGE_PREFIXES: tuple[str, ...] = (
    "ops/autonomy/",
    "ops/memory/",
    "ops/secrets/",
    "ops/hooks/",
    "skills/",
)

# Test directory mappings
TEST_DIRECTORY_MAPPINGS: dict[str, list[str]] = {
    "ops/": ["tests/ops/"],
    "skills/": ["skills/", "tests/skills/"],
    "environment/": ["tests/environment/"],
}

# Seed ID prefixes
SEED_VR_COVERAGE = "SEED-VR-coverage"
SEED_RA_REVIEW = "SEED-RA-review"

# Allowed seed disposition statuses (agent can only dispose, not delete)
ALLOWED_SEED_DISPOSITIONS = frozenset(
    {
        "Resolved",  # Requires close_validation
        "FalsePositive",  # Requires evidence
        "OutOfScope",  # Requires evidence
        "AcceptedRisk",  # Requires evidence
    }
)


def _has_matching_test(path: str, changed_paths: set[str]) -> bool:
    """Check if a source file has a corresponding test file in the changed set."""
    if not path.endswith(".py"):
        return True  # Non-Python files don't need test coverage

    # Skip test files themselves
    if "/tests/" in path or path.startswith("tests/") or path.startswith("test_"):
        return True

    # Look for test file patterns
    basename = Path(path).stem
    test_patterns = [
        f"test_{basename}.py",
        f"{basename}_test.py",
        f"tests/test_{basename}.py",
    ]

    # Check direct test mappings
    for src_prefix, test_prefixes in TEST_DIRECTORY_MAPPINGS.items():
        if path.startswith(src_prefix):
            rel_path = path[len(src_prefix) :]
            for test_prefix in test_prefixes:
                test_path = f"{test_prefix}test_{Path(rel_path).stem}.py"
                if test_path in changed_paths:
                    return True
                # Also check for tests/ subdirectory within the package
                package_test = path.replace(src_prefix, f"tests/{src_prefix}")
                package_test = package_test.replace(".py", "_test.py")
                if package_test in changed_paths:
                    return True

    # Check if any pattern matches
    for test_path in changed_paths:
        for pattern in test_patterns:
            if test_path.endswith(pattern):
                return True

    return False


def _requires_coverage_audit(path: str) -> bool:
    """Check if a path is in a directory that requires test coverage."""
    for prefix in REQUIRES_TEST_COVERAGE_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def seed_findings(changed_paths: list[str]) -> list[dict[str, Any]]:
    """Generate mandatory seed findings from changed paths.

    Seeds cannot be deleted by the agent. They can only be disposed:
    - Resolved: requires close_validation (the test that proves the fix)
    - FalsePositive: requires evidence explaining why this is not a real issue
    - OutOfScope: requires evidence explaining why this is out of scope
    - AcceptedRisk: requires evidence explaining the risk acceptance

    Args:
        changed_paths: List of paths that were changed (from git diff)

    Returns:
        List of seed finding dictionaries
    """
    seeds: list[dict[str, Any]] = []
    changed_set = {p.strip().lstrip("./") for p in changed_paths if p.strip()}
    seen_paths: set[str] = set()

    for raw_path in changed_paths:
        path = raw_path.strip().lstrip("./")
        if not path:
            continue

        # Skip exempt paths
        if _is_exempt_path(path):
            continue

        # Skip if already processed
        if path in seen_paths:
            continue
        seen_paths.add(path)

        # Only Python files for now
        if not path.endswith(".py"):
            continue

        # Skip test files themselves
        if "/tests/" in path or path.startswith("tests/") or path.startswith("test_"):
            continue

        # Check if this path requires test coverage
        if _requires_coverage_audit(path):
            if not _has_matching_test(path, changed_set):
                seed_id = f"{SEED_VR_COVERAGE}-{Path(path).stem}"
                seeds.append(
                    {
                        "id": seed_id,
                        "kernel": "validate_repair",
                        "path": path,
                        "severity": "Medium",
                        "confidence": "Probable",
                        "rule": "AGENTS.md",
                        "evidence": f"Changed {path} without corresponding test file change",
                        "status": "Open",
                        "close_validation": "",
                        "_seed": True,  # Mark as seed for tracking
                    }
                )

    return seeds


def seed_findings_present(findings: list[dict[str, Any]], seeds: list[dict[str, Any]]) -> list[str]:
    """Check that all seed findings are present and properly disposed.

    Seeds cannot be deleted. They must be disposed with an allowed status.

    Args:
        findings: The findings from the report
        seeds: The seed findings that were generated

    Returns:
        List of error messages
    """
    errors: list[str] = []

    if not seeds:
        return []

    # Build a map of finding IDs to findings
    finding_map: dict[str, dict[str, Any]] = {}
    for finding in findings:
        fid = finding.get("id", "").strip()
        if fid:
            finding_map[fid] = finding

    # Check each seed is present and properly disposed
    for seed in seeds:
        seed_id = seed.get("id", "").strip()
        if not seed_id:
            continue

        if seed_id not in finding_map:
            errors.append(f"seed finding {seed_id} is missing (seeds cannot be deleted)")
            continue

        finding = finding_map[seed_id]
        status = finding.get("status", "").strip()

        # Seed must have an allowed disposition status
        if status not in ALLOWED_SEED_DISPOSITIONS:
            errors.append(
                f"seed finding {seed_id} has status {status!r}; "
                f"seeds must be disposed with {sorted(ALLOWED_SEED_DISPOSITIONS)}"
            )
            continue

        # Resolved requires close_validation
        if status == "Resolved":
            close = finding.get("close_validation", "").strip()
            if not close:
                errors.append(f"seed finding {seed_id} is Resolved but has no close_validation")

        # FalsePositive/OutOfScope/AcceptedRisk requires evidence
        if status in {"FalsePositive", "OutOfScope", "AcceptedRisk"}:
            evidence = finding.get("evidence", "").strip()
            if not evidence or evidence == seed.get("evidence", "").strip():
                errors.append(f"seed finding {seed_id} is {status} but has no updated evidence")

    return errors
