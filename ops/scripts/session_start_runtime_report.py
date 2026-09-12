#!/usr/bin/env python3
"""Classify SessionStart runtime probes. Never invent ok from silence.

SessionStart used to dump raw receipt slogans ("no publish-path breakglass",
"itest unavailable", "claude bootstrap: never_ran") as if they were this
session's faults. A missing override is healthy. Local Neo4j :7687 is optional
PlasticOS/code-graph itest, not Graphiti. Cursor does not run the Claude
installer. This reporter names each component, its class, and the evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

# Allow `python ops/scripts/session_start_runtime_report.py` from a checkout.
_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parent.parent
_AUTONOMY = _SCRIPTS.parent / "autonomy"
_SECRETS = _SCRIPTS.parent / "secrets"
for _path in (_REPO, _SCRIPTS, _AUTONOMY, _SECRETS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from breakglass_receipt import evaluate, load_receipt  # noqa: E402
from claude_bootstrap_receipt import read as read_claude_receipt  # noqa: E402

OK = "ok"
NA = "n/a"
DEGRADED = "degraded"
FAILED = "failed"


def _line(
    name: str,
    klass: str,
    summary: str,
    *,
    evidence: str = "",
    this_surface: bool = True,
    include_in_degraded: bool | None = None,
) -> dict[str, Any]:
    if include_in_degraded is None:
        include_in_degraded = klass in {DEGRADED, FAILED} and this_surface
    return {
        "name": name,
        "class": klass,
        "summary": summary,
        "evidence": evidence,
        "this_surface": this_surface,
        "include_in_degraded": include_in_degraded,
    }


def classify_publish_path(verdict: dict[str, Any] | None) -> dict[str, Any]:
    """A missing override is healthy. An in-force grant is a named bypass."""
    if not verdict:
        return _line(
            "publish-path",
            FAILED,
            "probe unread — breakglass_receipt.py produced no verdict",
            evidence="no JSON from --json",
        )
    if verdict.get("in_force"):
        return _line(
            "publish-path",
            DEGRADED,
            (
                "override in force — publish-path enforcement is bypassed "
                f"issuer={verdict.get('issuer') or '?'} "
                f"reason={verdict.get('reason') or '?'} "
                f"expires={verdict.get('expires_at') or '?'}"
            ),
            evidence=str(verdict.get("detail") or ""),
        )
    status = str(verdict.get("status") or "none")
    if status == "none":
        return _line("publish-path", OK, "enforced (no override receipt)")
    if status == "inert_env":
        return _line(
            "publish-path",
            OK,
            "enforced — L9_PUBLISH_PATH_OVERRIDE is set but inert without a receipt",
            evidence=str(verdict.get("detail") or ""),
        )
    if status == "expired":
        return _line(
            "publish-path",
            OK,
            "enforced (override receipt expired)",
            evidence=str(verdict.get("detail") or ""),
        )
    if status == "invalid":
        return _line(
            "publish-path",
            DEGRADED,
            "override receipt present but invalid — enforcement stays on",
            evidence=str(verdict.get("detail") or ""),
        )
    return _line(
        "publish-path",
        FAILED,
        f"unrecognised breakglass status {status!r}",
        evidence=json.dumps(verdict, sort_keys=True)[:400],
    )


def classify_itest(*, error: str, codegraph: str) -> dict[str, Any]:
    """T-CI022: declare runnable vs not. Absence of :7687 is n/a, not a fault."""
    graph = (codegraph or "").strip().splitlines()[0] if codegraph else "unknown"
    if not error:
        return _line(
            "itest/neo4j",
            OK,
            "127.0.0.1:7687 reachable — service-backed integration tests may run",
        )
    return _line(
        "itest/neo4j",
        NA,
        (
            "not required on this workspace — local Neo4j :7687 is PlasticOS/"
            f"code-graph itest, not Graphiti (Graphiti is :8100). Probe: {error}. "
            f"code-graph: {graph[:120]}"
        ),
        evidence=error,
        this_surface=False,
        include_in_degraded=False,
    )


def _receipt_belongs_here(receipt: dict[str, Any], workspace: str) -> tuple[bool, str]:
    """A receipt written for another workspace (or for $HOME) is not this
    session's state. The observed poisoning: a Claude harness SessionStart ran
    install.sh with --workspace $HOME and its receipt was then reported as the
    current session's bootstrap verdict.
    """
    recorded = str(receipt.get("workspace") or "").strip()
    if not recorded:
        return True, ""  # old receipts carry no workspace; do not invent a fault
    try:
        recorded_real = os.path.realpath(recorded)
    except OSError:
        recorded_real = recorded
    home_real = os.path.realpath(str(Path.home()))
    if recorded_real == home_real:
        return False, f"receipt workspace is $HOME ({recorded}) — harness/other-surface run"
    if workspace:
        try:
            ws_real = os.path.realpath(workspace)
        except OSError:
            ws_real = workspace
        if recorded_real != ws_real:
            return False, f"receipt workspace {recorded} is not this session's {workspace}"
    return True, ""


def classify_claude_adapter(
    *,
    surface: str,
    receipt: dict[str, Any],
    repair_log: str,
    repair_text: str,
    workspace: str = "",
) -> list[dict[str, Any]]:
    state = str(receipt.get("state") or "unknown")
    reason = str(receipt.get("reason") or "")

    if surface != "claude-code":
        return [
            _line(
                "claude-adapter",
                NA,
                (
                    "not this surface — Cursor SessionStart does not run "
                    "install.sh (CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1)"
                ),
                this_surface=False,
                include_in_degraded=False,
            )
        ]

    belongs, why = _receipt_belongs_here(receipt, workspace)
    if not belongs:
        return [
            _line(
                "claude-adapter",
                NA,
                f"stale_other_surface — {why}",
                evidence=str(receipt.get("generated_at") or ""),
                this_surface=False,
                include_in_degraded=False,
            )
        ]

    repair_hit = (repair_text or "").strip()
    repair_name = repair_log or str(receipt.get("log_path") or "")
    if state == "ready":
        return [_line("claude-adapter", OK, reason or "all required components READY")]
    klass = FAILED if state in {"never_ran", "failed", "blocked"} else DEGRADED
    how = repair_hit or reason or f"receipt state={state}"
    return [
        _line(
            "claude-adapter",
            klass,
            f"{state} — {how}",
            evidence=f"{repair_name}: {how}" if repair_name else how,
        )
    ]


def classify_cursor_adapter(
    *,
    surface: str,
    receipt: dict[str, Any],
    workspace: str = "",
) -> list[dict[str, Any]]:
    """Cursor's own receipt (~/.l9/cursor/bootstrap-state.json).

    `make cursor-install` is optional wiring, so never_ran is n/a, not a
    fault. A receipt from another workspace is stale_other_surface. Only a
    fresh, this-workspace non-ready receipt reaches ### Degraded.
    """
    if surface != "cursor":
        return []
    state = str(receipt.get("state") or "unknown")
    reason = str(receipt.get("reason") or "")
    if state == "never_ran":
        return [
            _line(
                "cursor-adapter",
                NA,
                "no receipt — make cursor-install never ran (optional wiring)",
                this_surface=False,
                include_in_degraded=False,
            )
        ]
    belongs, why = _receipt_belongs_here(receipt, workspace)
    if not belongs:
        return [
            _line(
                "cursor-adapter",
                NA,
                f"stale_other_surface — {why}",
                evidence=str(receipt.get("generated_at") or ""),
                this_surface=False,
                include_in_degraded=False,
            )
        ]
    if state == "ready":
        return [_line("cursor-adapter", OK, reason or "all required components READY")]
    if state == "unknown":
        # TTL/revision expiry: the file no longer describes an observed state.
        # That is not a this-session install failure (same reader contract as
        # never_ran — n/a until make cursor-install writes a fresh receipt).
        return [
            _line(
                "cursor-adapter",
                NA,
                f"stale_receipt — {reason or 'receipt no longer describes an observed state'}",
                evidence=reason,
                this_surface=False,
                include_in_degraded=False,
            )
        ]
    klass = FAILED if state in {"failed", "blocked"} else DEGRADED
    return [_line("cursor-adapter", klass, f"{state} — {reason or 'receipt state=' + state}")]


def classify_memory(*, detail: str, stderr: str, healthy: bool) -> dict[str, Any]:
    proof = parse_binding_proof(detail)
    if proof_is_live(proof):
        return classify_memory_proof(proof)
    if healthy:
        return _line("memory", OK, detail or "healthy")
    evidence = (stderr or "").strip() or detail or "no stderr captured — probe swallowed"
    return _line(
        "memory",
        FAILED
        if "unreachable" in (detail or "").lower() or "refused" in evidence.lower()
        else DEGRADED,
        detail or "unhealthy",
        evidence=evidence[:500],
    )


def parse_binding_proof(raw: str | None) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def proof_is_live(proof: dict[str, Any] | None) -> bool:
    """A measured RuntimeBinding.as_dict(), not a slogan or fail-closed stub."""
    if not proof:
        return False
    return "binding_status" in proof or "ok" in proof


# Faults a live probe is expected to hit: unreadable manifests, malformed
# bindings, a runtime that refuses to resolve. Anything else is a defect in the
# binding code and must surface, not be reported as "no proof".
_PROBE_FAULTS = (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError)


def probe_memory_binding() -> dict[str, Any] | None:
    try:
        from ops.memory.runtime_binding import resolve_runtime_binding
    except ImportError:
        return None
    try:
        return resolve_runtime_binding().as_dict()
    except _PROBE_FAULTS as exc:
        reason = f"{type(exc).__name__}: {exc}".strip()[:200]
        return {"ok": False, "binding_status": "probe-error", "reasons": [reason]}


def classify_memory_proof(proof: dict[str, Any]) -> dict[str, Any]:
    """Compose the memory line from measured proof fields only."""
    status = str(proof.get("binding_status") or proof.get("status") or "").strip()
    provenance = str(proof.get("artifact_provenance") or "").strip()
    package = str(proof.get("memory_package") or "").strip()
    version = str(proof.get("memory_version") or "").strip()
    raw_reasons = proof.get("reasons") or []
    if isinstance(raw_reasons, str):
        reason_text = raw_reasons.strip()
        reasons: list[str] = [raw_reasons] if raw_reasons.strip() else []
    else:
        reasons = [str(item) for item in raw_reasons if item]
        reason_text = "; ".join(reasons)
    if "ok" in proof:
        usable = bool(proof["ok"])
    else:
        usable = False
    head = status or "unknown"
    if provenance:
        head = f"{head} (provenance {provenance})"
    identity = " ".join(part for part in (package, version) if part)
    summary = " — ".join(part for part in (head, identity, reason_text) if part)
    if not summary:
        summary = "memory proof empty"
    evidence = json.dumps(
        {
            "binding_status": status or None,
            "ok": proof.get("ok"),
            "artifact_provenance": provenance or None,
            "reasons": reasons,
        },
        sort_keys=True,
    )
    lowered = f"{summary} {reason_text}".lower()
    if not usable:
        klass = FAILED if "unreachable" in lowered or "refused" in lowered else DEGRADED
    elif provenance == "unproven":
        klass = DEGRADED
    else:
        klass = OK
    return _line("memory", klass, summary, evidence=evidence[:500])


def resolve_memory_proof(*, raw_proof: str = "", raw_detail: str = "") -> dict[str, Any] | None:
    """Prefer a live proof JSON; otherwise measure. Never trust a slogan."""
    for raw in (raw_proof, raw_detail):
        parsed = parse_binding_proof(raw)
        if proof_is_live(parsed):
            return parsed
    if (raw_detail or "").strip().startswith("disabled"):
        return None
    return probe_memory_binding()


def classify_tunnel(detail: str) -> dict[str, Any]:
    """The provider tunnel is retired. A constant slogan is not a live probe."""
    text = detail or ""
    lowered = text.lower()
    if "retired" in lowered or "no provider tunnel" in lowered:
        return _line(
            "tunnel",
            NA,
            text or "not a plane — memory control plane (no provider tunnel)",
            evidence="not probed",
            this_surface=False,
            include_in_degraded=False,
        )
    return classify_simple("tunnel", text, fail_tokens=("fail", "refused", "error", "closed"))


def classify_simple(name: str, detail: str, *, fail_tokens: tuple[str, ...] = ()) -> dict[str, Any]:
    text = detail or ""
    lowered = text.lower()
    if any(tok in lowered for tok in fail_tokens):
        klass = FAILED if "fail" in lowered or "refused" in lowered else DEGRADED
        return _line(name, klass, text, evidence=text)
    return _line(name, OK, text or "ok")


def classify_venv(detail: str) -> dict[str, Any]:
    """Quote the ensure_uv check UV: line. Nonzero check is DEGRADED, not FAILED."""
    text = (detail or "").strip()
    if not text:
        return _line(
            "venv",
            DEGRADED,
            "probe unread — ensure_uv_environment.sh produced no UV: line",
            evidence="no probe",
        )
    lowered = text.lower()
    if any(
        token in lowered
        for token in (
            "unavailable",
            "synchronization required",
            "missing",
            "without a usable",
        )
    ):
        return _line("venv", DEGRADED, text, evidence=text)
    return _line("venv", OK, text)


def classify_backup(detail: str) -> dict[str, Any]:
    """backup_gate.sh is decision-only. SKIP is n/a, not a this-session fail."""
    text = (detail or "").strip()
    if not text:
        return _line(
            "backup",
            DEGRADED,
            "probe unread — backup_gate.sh produced no PROCEED/SKIP line",
            evidence="no probe",
        )
    if text.startswith("PROCEED"):
        return _line("backup", OK, text)
    if text.startswith("SKIP"):
        return _line(
            "backup",
            NA,
            text,
            evidence=text,
            this_surface=False,
            include_in_degraded=False,
        )
    return _line("backup", OK, text)


#: ``aws.code`` the secrets plane writes when the seeding path was never
#: attempted because the surface may not hold raw secret material
#: (``session_start_secrets.NOT_ATTEMPTED``). The plane owns the string; this is
#: the receipt contract, read here rather than re-derived from the environment.
SECRETS_SEEDING_NOT_APPLICABLE = "SEEDING_NOT_APPLICABLE"


def classify_aws_cli(result: dict[str, Any] | None) -> dict[str, Any]:
    """Derived view of the secrets-plane receipt aws object. Never prints account ids."""
    if not result:
        return _line(
            "aws-cli",
            FAILED,
            "aws-cli receipt unread",
            evidence="no receipt",
        )
    if str(result.get("code") or "") == SECRETS_SEEDING_NOT_APPLICABLE:
        # `aws.ok` is false here because no probe ran — claiming an authorized
        # CLI that was never invoked would be a false READY. But an absence the
        # surface is designed for is not this session's fault, so it is `n/a`,
        # the same call `classify_skill_usage` makes for a log Cursor never
        # writes. Left as FAILED it drove `### FAILED` and exit 1 on every
        # hosted session — the second false-degradation surface for the one
        # by-design condition, after the bootstrap DEGRADED counter.
        return _line(
            "aws-cli",
            NA,
            str(result.get("summary") or "seeding not applicable on this surface"),
            evidence=SECRETS_SEEDING_NOT_APPLICABLE,
        )
    if result.get("ok"):
        return _line("aws-cli", OK, str(result.get("summary") or "authorized"))
    return _line(
        "aws-cli",
        FAILED,
        str(result.get("summary") or result.get("code") or "unauthorized"),
        evidence=str(result.get("code") or ""),
    )


def classify_secrets_bind(statuses: list[dict[str, Any]] | None) -> dict[str, Any]:
    """SessionStart visibility for local bind. Never includes a secret value.

    source=aws is a fault: bind is Infisical only. Unbound is a vault miss,
    not a reason to paste a token.
    """
    if statuses is None:
        return _line(
            "secrets-bind",
            DEGRADED,
            "secrets-plane receipt unread",
            evidence="no receipt",
        )
    parts: list[str] = []
    unbound: list[str] = []
    aws_leftover: list[str] = []
    for raw in statuses:
        name = str(raw.get("name") or "?").strip() or "?"
        source = str(raw.get("source") or "unbound").strip() or "unbound"
        if name.upper() in {"VALUE", "TOKEN", "SECRET"}:
            continue
        parts.append(f"{name}={source}")
        if source == "aws":
            aws_leftover.append(name)
        elif not raw.get("bound"):
            unbound.append(name)
    summary = " ".join(parts) if parts else "no inventory names probed"
    if aws_leftover:
        return _line(
            "secrets-bind",
            FAILED,
            f"{summary} — source=aws is a fault; bind is Infisical only",
            evidence="aws " + ",".join(aws_leftover),
        )
    if unbound:
        return _line(
            "secrets-bind",
            DEGRADED,
            f"{summary} — fetchers will retry; do not paste a token",
            evidence="unbound " + ",".join(unbound),
        )
    return _line("secrets-bind", OK, summary)


def load_secrets_plane_receipt(workspace: str) -> dict[str, Any] | None:
    """Read the plane receipt. Never probe. Invalid/absent is unread."""
    if not workspace:
        return None
    path = Path(workspace) / ".l9" / "session" / "secrets-plane.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def secrets_receipt_parts(
    receipt: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    if not receipt:
        return None, None
    aws = receipt.get("aws")
    binds = receipt.get("binds")
    return (
        aws if isinstance(aws, dict) else None,
        binds if isinstance(binds, list) else None,
    )


def classify_skill_usage(detail: str) -> dict[str, Any]:
    """A missing Claude skill-usage log is n/a on Cursor, not a this-session fault."""
    text = detail or ""
    lowered = text.lower()
    if "absent" in lowered or "never wrote" in lowered:
        return _line(
            "skill-usage",
            NA,
            text or "logger never wrote — not required on this surface",
            evidence=text,
            this_surface=False,
            include_in_degraded=False,
        )
    return _line("skill-usage", OK, text or "ok")


def probe_neo4j(host: str = "127.0.0.1", port: int = 7687, timeout: float = 0.3) -> str:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    except OSError as exc:
        return f"{type(exc).__name__}: {exc}"
    finally:
        sock.close()
    return ""


def latest_repair_log(repair_dir: Path) -> tuple[str, str]:
    if not repair_dir.is_dir():
        return "", ""
    logs = [p for p in repair_dir.glob("bootstrap-repair-*.log") if p.is_file()]
    if not logs:
        return "", ""
    newest = max(logs, key=lambda p: p.stat().st_mtime)
    try:
        text = newest.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        return str(newest), f"unreadable: {exc}"
    return str(newest), text[:400]


def format_markdown(lines: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    failed_aws = [item for item in lines if item["name"] == "aws-cli" and item["class"] == FAILED]
    if failed_aws:
        parts.append("### FAILED")
        for item in failed_aws:
            parts.append(f"- {item['name']}: {item['class']} — {item['summary']}")
        parts.append("")
    runtime = ["### Runtime"]
    for item in lines:
        runtime.append(f"- {item['name']}: {item['class']} — {item['summary']}")
    degraded = [item for item in lines if item.get("include_in_degraded")]
    runtime.append("### Degraded")
    if not degraded:
        runtime.append("- none")
        return "\n".join(parts + runtime)
    for item in degraded:
        ev = item.get("evidence") or ""
        extra = f" Evidence: {ev}" if ev and ev not in item["summary"] else ""
        runtime.append(f"- {item['name']}: {item['class']} — {item['summary']}.{extra}".rstrip("."))
    return "\n".join(parts + runtime)


def collect(
    *,
    surface: str,
    venv: str,
    ide_profile: str,
    tunnel: str,
    memory_detail: str,
    memory_stderr: str,
    memory_healthy: bool,
    memory_proof: dict[str, Any] | None = None,
    wiring: str,
    backup: str,
    skill_note: str,
    codegraph: str,
    hydrate_degraded: bool,
    hydrate_reason: str,
    home: Path | None = None,
    workspace: str = "",
    aws_cli: dict[str, Any] | None = None,
    secrets_bind: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root = home or Path.home()
    lines: list[dict[str, Any]] = [
        classify_venv(venv),
        classify_simple("ide-profile", ide_profile, fail_tokens=("fail", "error")),
        classify_tunnel(tunnel),
        classify_memory_proof(memory_proof)
        if memory_proof is not None
        else classify_memory(detail=memory_detail, stderr=memory_stderr, healthy=memory_healthy),
        classify_publish_path(evaluate(load_receipt())),
        classify_aws_cli(aws_cli),
        classify_secrets_bind(secrets_bind),
        classify_skill_usage(skill_note),
        classify_itest(error=probe_neo4j(), codegraph=codegraph),
    ]
    receipt = read_claude_receipt(path=root / ".l9" / "claude" / "bootstrap-state.json")
    repair_log, repair_text = latest_repair_log(root / ".l9" / "claude")
    lines.extend(
        classify_claude_adapter(
            surface=surface,
            receipt=receipt,
            repair_log=repair_log,
            repair_text=repair_text,
            workspace=workspace,
        )
    )
    lines.extend(
        classify_cursor_adapter(
            surface=surface,
            receipt=read_claude_receipt(
                path=root / ".l9" / "cursor" / "bootstrap-state.json",
                surface="cursor",
            ),
            workspace=workspace,
        )
    )
    lines.append(classify_simple("wiring", wiring, fail_tokens=("fail",)))
    lines.append(classify_backup(backup))
    if hydrate_degraded:
        lines.append(
            _line(
                "memory-hydrate",
                DEGRADED,
                hydrate_reason or "hydrate reported degraded",
                evidence=hydrate_reason,
            )
        )
    return lines


def resolve_reporter_path(
    *,
    override: str | None = None,
    project_dir: str | None = None,
    gc: str | None = None,
) -> Path | None:
    """Load order: L9_SESSION_RUNTIME_REPORT, then worktree, then $GC."""
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    if project_dir:
        candidates.append(Path(project_dir) / "ops" / "scripts" / "session_start_runtime_report.py")
    if gc:
        candidates.append(Path(gc) / "ops" / "scripts" / "session_start_runtime_report.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _truthy(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "degraded"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--surface", default=os.environ.get("L9_GOVERNANCE_SURFACE", "cursor"))
    parser.add_argument("--venv", default="")
    parser.add_argument("--ide-profile", default="")
    parser.add_argument("--tunnel", default="")
    parser.add_argument("--memory-detail", default="")
    parser.add_argument("--memory-stderr", default="")
    parser.add_argument("--memory-healthy", default="false")
    parser.add_argument(
        "--memory-proof",
        default="",
        help="RuntimeBinding.as_dict() JSON; when absent the reporter re-probes",
    )
    parser.add_argument("--wiring", default="")
    parser.add_argument("--backup", default="")
    parser.add_argument("--skill-note", default="")
    parser.add_argument("--codegraph", default="skipped")
    parser.add_argument("--hydrate-degraded", default="false")
    parser.add_argument("--hydrate-reason", default="")
    parser.add_argument(
        "--workspace",
        default=os.environ.get("CURSOR_PROJECT_DIR", os.getcwd()),
        help="session git root; receipts recorded for another workspace are stale_other_surface",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    memory_proof = resolve_memory_proof(
        raw_proof=args.memory_proof,
        raw_detail=args.memory_detail,
    )
    aws_cli, secrets_bind = secrets_receipt_parts(load_secrets_plane_receipt(args.workspace))
    lines = collect(
        surface=args.surface,
        venv=args.venv,
        ide_profile=args.ide_profile,
        tunnel=args.tunnel,
        memory_detail=args.memory_detail,
        memory_stderr=args.memory_stderr,
        memory_healthy=_truthy(args.memory_healthy),
        memory_proof=memory_proof,
        wiring=args.wiring,
        backup=args.backup,
        skill_note=args.skill_note,
        codegraph=args.codegraph,
        hydrate_degraded=_truthy(args.hydrate_degraded),
        hydrate_reason=args.hydrate_reason,
        workspace=args.workspace,
        aws_cli=aws_cli,
        secrets_bind=secrets_bind,
    )
    aws_failed = any(item["name"] == "aws-cli" and item["class"] == FAILED for item in lines)
    if args.json:
        print(json.dumps({"lines": lines}, indent=2, sort_keys=True))
        return 1 if aws_failed else 0
    print(format_markdown(lines))
    return 1 if aws_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
