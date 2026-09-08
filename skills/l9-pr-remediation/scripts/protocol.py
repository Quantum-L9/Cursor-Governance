#!/usr/bin/env python3
"""Deterministic remediator protocol tables. Stdlib only.

Owns path edit-axis, reviewer class, plan/gate schemas, and scanner
normalization. Never invents HUMAN / FALSE_POSITIVE / disposition / board.
Those stay model judgment in the reference files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CRA_LOGINS = frozenset(
    {
        "github-code-quality",
        "copilot",
        "copilot-pull-request-reviewer",
    }
)
CI_LOGINS = frozenset({"github-actions"})
OTHER_BOT_LOGINS = frozenset(
    {
        "gemini-code-assist",
        "coderabbitai",
        "github-advanced-security",
        "sonarcloud",
        "codecov",
        "dependabot",
    }
)

#: Path prefixes that are CI_PIPELINE / secret-plane. Match start of a
#: normalized relative path. Keep aligned with pr_fleet.FORBIDDEN_PATHS.
CI_PIPELINE_PREFIXES = (
    ".github/workflows/",
    ".github/actions/",
    ".github/codeowners",
    "ops/secrets/",
)
CI_PIPELINE_NAMES = frozenset(
    {
        ".github/codeowners",
        ".env",
        "codeowners",
    }
)
CI_PIPELINE_SUFFIXES = (".pem", ".key")
CI_PIPELINE_ENV_RE = re.compile(r"^\.env(?:\.|$)")

EDIT_CODEBASE = "CODEBASE"
EDIT_CI_PIPELINE = "CI_PIPELINE"
EDIT_CLASSES = frozenset(
    {
        EDIT_CODEBASE,
        EDIT_CI_PIPELINE,
        "ENVIRONMENT",
        "HUMAN",
        "FALSE_POSITIVE",
    }
)

REVIEWER_CRA = "code_review_agent"
REVIEWER_BOT = "bot"
REVIEWER_HUMAN = "human"
REVIEWER_CI = "ci"

SOURCES = frozenset(
    {
        "ci",
        "review_inline",
        "review_general",
        "github-code-quality",
        "copilot",
        "human",
        "bot",
        "sonar",
        "sonarcloud",
        "codeql",
        "semgrep",
        "debt",
    }
)
DISPOSITIONS = frozenset(
    {
        "fix",
        "reply_ack",
        "reply_disagree",
        "defer",
        "already_fixed",
        "note_pipeline",
        "note_environment",
    }
)
CONFIDENCES = frozenset({"high", "medium", "low", "Unknown"})
BOARD_VALUES = frozenset({"merge", "fix", "wait", "leftover"})
SEVERITIES = frozenset({"blocking", "actionable", "discussion", "deferred"})
HANDOFF_CLASSES = frozenset({"HUMAN", "CI_PIPELINE", "ENVIRONMENT"})

FINDING_REQUIRED = (
    "id",
    "source",
    "ownership",
    "disposition",
    "evidence",
    "root_cause",
)
PLAN_FINDING_REQUIRED = FINDING_REQUIRED
VERIFY_COMMAND = "make precommit-repo"
PUBLISH_COMMAND = "git push"
IMPROVE_COMMAND = "make improve"
FORBIDDEN_VERIFY = (
    "make pr",
    "make pr-check",
    "PR_REMEDIATE=0 make pr",
    "make precommit",
    "make pr-full",
    "pre-commit --all-files",
    "pre-commit run --all-files",
)

GATE_TYPE_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lint", ("ruff", "eslint", "biome", "lint")),
    ("format", ("prettier", "ruff format", "format")),
    ("type-check", ("tsc", "mypy", "pyright", "type")),
    ("test", ("jest", "pytest", "vitest", "test")),
    ("build", ("vite build", "tsc --noemit", "compile", "build")),
    ("security", ("semgrep", "npm audit", "snyk", "trivy", "gitleaks", "bandit")),
)

_BOT_SUFFIX = re.compile(r"\[bot\]$", re.I)


def strip_bot_suffix(login: str) -> str:
    return _BOT_SUFFIX.sub("", (login or "").strip()).lower()


def reviewer_class(login: str) -> str:
    raw = (login or "").strip()
    key = strip_bot_suffix(raw)
    if not key:
        return REVIEWER_HUMAN
    if key in CRA_LOGINS:
        return REVIEWER_CRA
    if key in CI_LOGINS:
        return REVIEWER_CI
    if key in OTHER_BOT_LOGINS or _BOT_SUFFIX.search(raw):
        return REVIEWER_BOT
    return REVIEWER_HUMAN


def ledger_source(*, author: str = "", kind: str = "review") -> str:
    """Map an ingest event onto the remediation-plan source vocabulary."""
    if kind == "ci":
        return "ci"
    if kind in {"sonar", "sonarcloud"}:
        return "sonar"
    if kind in {"semgrep", "codeql", "debt"}:
        return kind
    cls = reviewer_class(author)
    if cls == REVIEWER_CRA:
        key = strip_bot_suffix(author)
        return "github-code-quality" if "code-quality" in key else "copilot"
    if cls == REVIEWER_CI:
        return "ci"
    if cls == REVIEWER_BOT:
        return "bot"
    return "human"


def is_code_review_agent(login: str) -> bool:
    return reviewer_class(login) == REVIEWER_CRA


def _normalize_path(path: str | None) -> str:
    text = (path or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def edit_axis(path: str | None) -> str:
    """Path-only edit axis. Never returns HUMAN or FALSE_POSITIVE."""
    rel = _normalize_path(path)
    if not rel:
        return EDIT_CODEBASE
    lowered = rel.lower()
    name = Path(lowered).name
    if name in CI_PIPELINE_NAMES or CI_PIPELINE_ENV_RE.match(name):
        return EDIT_CI_PIPELINE
    if any(lowered.startswith(prefix) for prefix in CI_PIPELINE_PREFIXES):
        return EDIT_CI_PIPELINE
    if lowered.endswith(CI_PIPELINE_SUFFIXES):
        return EDIT_CI_PIPELINE
    return EDIT_CODEBASE


def gate_type(text: str | None) -> str | None:
    blob = (text or "").lower()
    if not blob:
        return None
    for kind, markers in GATE_TYPE_MARKERS:
        if any(marker in blob for marker in markers):
            return kind
    return None


def ownership_hint(finding: dict[str, Any]) -> str:
    return edit_axis(finding.get("file") or finding.get("path"))


def severity_hint(finding: dict[str, Any], required_checks: set[str] | None = None) -> str | None:
    """Deterministic severity only. Review 'actionable vs discussion' stays prose."""
    required = {item.lower() for item in (required_checks or set())}
    source = str(finding.get("source") or "")
    gate = str(finding.get("gate") or finding.get("check") or "")
    if source == "ci":
        if gate and gate.lower() in required:
            return "blocking"
        return "actionable"
    login = str(finding.get("author") or "")
    if is_code_review_agent(login):
        label = str(finding.get("severity_label") or finding.get("severity") or "").lower()
        if label in {"error", "warning"}:
            return "actionable"
        if label == "note":
            return "discussion"
        return "actionable"
    return None


def discover_gate_registry(cwd: Path | None = None) -> dict[str, Any]:
    root = Path(cwd or Path.cwd())
    makefile = (root / "Makefile").is_file() or (root / "Makefile.am").is_file()
    leftover: list[str] = []
    if not makefile:
        workflows = root / ".github" / "workflows"
        if workflows.is_dir():
            leftover = sorted(
                str(path.relative_to(root))
                for path in (*workflows.glob("*.yml"), *workflows.glob("*.yaml"))
            )
    return {
        "makefile": makefile,
        "public": {
            "verify": VERIFY_COMMAND,
            "publish": PUBLISH_COMMAND,
            "improve": IMPROVE_COMMAND,
        },
        "leftover_workflow_run": leftover if not makefile else [],
    }


def validated_output(value: str, cwd: Path | None = None) -> Path:
    base = (cwd or Path.cwd()).resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def validate_gate_registry(registry: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(registry, dict):
        return ["gate_registry missing"]
    public = registry.get("public") or {}
    if public.get("verify") != VERIFY_COMMAND:
        errors.append(f"verify must be {VERIFY_COMMAND!r}")
    if public.get("publish") != PUBLISH_COMMAND:
        errors.append(f"publish must be {PUBLISH_COMMAND!r}")
    leftover = registry.get("leftover_workflow_run") or []
    if registry.get("makefile") and leftover:
        errors.append("leftover_workflow_run must be empty when Makefile exists")
    return errors


def validate_plan(plan: dict[str, Any], findings: list[dict[str, Any]] | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["plan is not an object"]
    body = plan.get("remediation_plan") if isinstance(plan.get("remediation_plan"), dict) else plan
    board = body.get("board")
    if board not in BOARD_VALUES:
        errors.append(f"board must be one of {sorted(BOARD_VALUES)}")
    if not str(body.get("board_reason") or "").strip():
        errors.append("board_reason missing")
    if board == "leftover" and not str(body.get("board_declaration") or "").strip():
        errors.append("leftover requires board_declaration")
    head = str(body.get("head_sha") or "")
    if head and not re.fullmatch(r"[0-9a-f]{40}", head):
        errors.append("head_sha must be 40-char hex when present")

    planned = body.get("findings")
    if not isinstance(planned, list):
        errors.append("findings must be a list")
        planned = []
    seen: set[str] = set()
    for item in planned:
        if not isinstance(item, dict):
            errors.append("finding is not an object")
            continue
        fid = str(item.get("id") or "")
        if not fid:
            errors.append("finding missing id")
        elif fid in seen:
            errors.append(f"duplicate finding id {fid}")
        seen.add(fid)
        if "board" in item:
            errors.append(f"{fid or '?'} must not carry a board field")
        for field in PLAN_FINDING_REQUIRED:
            if not str(item.get(field) or "").strip():
                errors.append(f"{fid or '?'} missing {field}")
        ownership = item.get("ownership")
        if ownership and ownership not in EDIT_CLASSES:
            errors.append(f"{fid} invalid ownership {ownership!r}")
        disposition = item.get("disposition")
        if disposition and disposition not in DISPOSITIONS:
            errors.append(f"{fid} invalid disposition {disposition!r}")
        if disposition == "fix":
            confidence = item.get("confidence")
            if confidence not in {"high", "medium"}:
                errors.append(f"{fid} disposition=fix requires confidence high|medium")
            if str(item.get("root_cause") or "") in {"", "Unknown"}:
                errors.append(f"{fid} disposition=fix requires a verified root_cause")

    clusters = body.get("clusters") or []
    if not isinstance(clusters, list):
        errors.append("clusters must be a list")
        clusters = []
    clustered: set[str] = set()
    for cluster in clusters:
        if not isinstance(cluster, dict):
            errors.append("cluster is not an object")
            continue
        ids = cluster.get("finding_ids") or []
        clustered.update(str(x) for x in ids)
        if any(str(x) for x in ids) and not (cluster.get("files") and cluster.get("action")):
            errors.append(f"cluster {cluster.get('id')!r} needs files + action")
    for item in planned:
        if isinstance(item, dict) and item.get("disposition") == "fix":
            fid = str(item.get("id") or "")
            if fid and fid not in clustered:
                errors.append(f"{fid} disposition=fix is not in a cluster")

    verify = body.get("verify") or {}
    targets = verify.get("makefile_targets") or []
    if "precommit-repo" not in targets:
        errors.append("verify.makefile_targets must include precommit-repo")
    policy = body.get("commit_policy") or {}
    if policy.get("commits") != 1:
        errors.append("commit_policy.commits must be 1")
    if policy.get("publish") != PUBLISH_COMMAND:
        errors.append(f"commit_policy.publish must be {PUBLISH_COMMAND!r}")
    if policy.get("no_verify") is True:
        errors.append("commit_policy.no_verify must be false")

    if findings is not None:
        ingested = {
            str(item.get("id")) for item in findings if isinstance(item, dict) and item.get("id")
        }
        missing = ingested - seen
        extra = seen - ingested
        if missing:
            errors.append(f"plan missing ingested ids: {sorted(missing)}")
        if extra:
            errors.append(f"plan has ids not in ingest: {sorted(extra)}")
    return errors


def _classified_counts(receipt: dict[str, Any]) -> dict[str, int]:
    classified = receipt.get("classified_findings") or {}
    if all(isinstance(classified.get(key), list) for key in SEVERITIES):
        return {key: len(classified.get(key) or []) for key in SEVERITIES} | {
            "total": sum(len(classified.get(key) or []) for key in SEVERITIES)
        }
    return {key: int(classified.get(key) or 0) for key in (*SEVERITIES, "total")}


def validate_gate(
    gate: str,
    receipt: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
    findings: list[dict[str, Any]] | None = None,
) -> list[str]:
    letter = gate.strip().upper()
    if letter not in {"A", "B", "C", "D", "E", "F"}:
        return [f"unknown gate {gate!r}"]
    if not isinstance(receipt, dict):
        return ["gate receipt is not an object"]
    errors: list[str] = []
    if letter == "A":
        errors.extend(validate_gate_registry(receipt.get("gate_registry")))
        blob = str(receipt.get("cached_verbs") or "")
        for verb in FORBIDDEN_VERIFY:
            if verb in blob:
                errors.append(f"cached ceremony verb {verb!r}")
    elif letter == "B":
        if plan is None:
            errors.append("Gate B requires a plan")
        else:
            errors.extend(validate_plan(plan, findings))
        counts = _classified_counts(receipt)
        if "total" not in (receipt.get("classified_findings") or {}) and counts["total"] == 0:
            if findings:
                errors.append("classified_findings.total missing")
        execution = receipt.get("execution_plan") or {}
        if not isinstance(execution, dict):
            errors.append("execution_plan missing")
        if receipt.get("worktree_dirty") is not False:
            errors.append("Gate B requires worktree_dirty: false")
    elif letter == "C":
        cycle = list((receipt.get("execution_plan") or {}).get("cycle_scope") or [])
        has_fix = bool(receipt.get("has_fix") or cycle)
        diff = str(receipt.get("diff_stat") or "")
        if has_fix and not diff.strip():
            errors.append("Gate C: empty diff while fix items remain")
    elif letter == "D":
        log = receipt.get("local_verify_log") or {}
        if log.get("result") != "Passed":
            errors.append("Gate D result must be Passed")
        command = str(log.get("command") or "")
        if VERIFY_COMMAND not in command:
            errors.append(f"Gate D command must include {VERIFY_COMMAND}")
        if int(log.get("iteration") or 0) > 5:
            errors.append("Gate D iteration exceeds 5")
        if log.get("exit_code") not in {0, "0"}:
            errors.append("Gate D exit_code must be 0")
    elif letter == "E":
        record = receipt.get("push_record") or {}
        sha = str(record.get("commit_sha") or "")
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            errors.append("push_record.commit_sha must be 40-char hex")
        if record.get("publish_count_this_cycle") != 1:
            errors.append("publish_count_this_cycle must be 1")
        if record.get("publish_command") != PUBLISH_COMMAND:
            errors.append(f"publish_command must be {PUBLISH_COMMAND!r}")
    elif letter == "F":
        record = receipt.get("reply_record") or {}
        total = int(record.get("threads_total") or 0)
        if int(record.get("threads_replied") or -1) != total:
            errors.append("threads_replied must equal threads_total")
        if int(record.get("threads_resolved") or -1) != total:
            errors.append("threads_resolved must equal threads_total")
        if record.get("batch_summary_posted") is not True:
            errors.append("batch_summary_posted must be true")
    return errors


def render_issue_body(
    *,
    klass: str,
    repo: str,
    pr: int,
    head: str,
    best_effort: str,
    why: str,
) -> str:
    return (
        "## Handoff from l9-pr-remediation\n\n"
        f"- **class:** {klass}\n"
        f"- **repo:** {repo}\n"
        f"- **pr:** #{pr}\n"
        f"- **head:** {head}\n"
        f"- **best-effort:** {best_effort}\n"
        f"- **why above paygrade:** {why}\n"
        "- **downstream:** l9-issue-remediation\n\n"
        "Do not bounce this back to the PR remediator until `open_issues=0`.\n"
    )


def _scanner_items(source: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    if source in {"sonar", "sonarcloud"}:
        return list(snapshot.get("issues") or [])
    if source == "semgrep":
        return list(snapshot.get("findings") or [])
    if source == "codeql":
        return list(snapshot.get("open_alerts") or snapshot.get("alerts") or [])
    if source == "debt":
        return [
            gate
            for gate in (snapshot.get("gates") or [])
            if isinstance(gate, dict) and gate.get("status") in {"FAIL", "FALSE_PASS", "ERROR"}
        ]
    return []


def normalize_scanner_findings(source: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    items = _scanner_items(source, snapshot)
    out: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        path = (
            item.get("path")
            or item.get("file")
            or item.get("component")
            or (item.get("textRange") or {}).get("path")
        )
        if source in {"sonar", "sonarcloud"} and isinstance(path, str) and ":" in path:
            path = path.split(":", 1)[-1]
        line = (
            item.get("line")
            or item.get("start_line")
            or (item.get("textRange") or {}).get("startLine")
        )
        message = str(item.get("message") or item.get("rule_name") or item.get("id") or source)
        finding = {
            "id": f"{source}-{index}",
            "source": ledger_source(author=str(source), kind=source),
            "author": source,
            "reviewer_class": REVIEWER_BOT,
            "file": path,
            "line": line,
            "message": message,
            "gate": None,
            "surface": "scanner",
            "local_verify_command": VERIFY_COMMAND,
            "raw": message,
            "ownership_hint": edit_axis(path if isinstance(path, str) else None),
            "severity_hint": None,
        }
        out.append(finding)
    return out


def _carry_review_identity(winner: dict[str, Any], loser: dict[str, Any]) -> dict[str, Any]:
    if not winner.get("thread_id") and loser.get("thread_id"):
        winner["thread_id"] = loser["thread_id"]
    extras = list(winner.get("also_authors") or [])
    other = loser.get("author")
    if other and other != winner.get("author") and other not in extras:
        extras.append(other)
    if extras:
        winner["also_authors"] = extras
    return winner


def merge_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same file+line collapses. CI message wins; review text and thread_id stay."""
    merged: list[dict[str, Any]] = []
    index: dict[tuple[str, int], int] = {}
    for finding in findings:
        file_name = finding.get("file")
        line = finding.get("line")
        if not file_name or line in {None, ""}:
            merged.append(finding)
            continue
        try:
            key = (str(file_name), int(line))
        except (TypeError, ValueError):
            merged.append(finding)
            continue
        if key in index:
            existing = merged[index[key]]
            if existing.get("source") != "ci" and finding.get("source") == "ci":
                finding = {
                    **finding,
                    "raw": f"{finding.get('raw')}\n---\n{existing.get('raw')}",
                }
                merged[index[key]] = _carry_review_identity(finding, existing)
            else:
                existing["raw"] = f"{existing.get('raw')}\n---\n{finding.get('raw')}"
                _carry_review_identity(existing, finding)
            continue
        index[key] = len(merged)
        merged.append(finding)
    return merged
