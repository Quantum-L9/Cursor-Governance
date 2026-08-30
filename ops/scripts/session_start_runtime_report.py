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
_AUTONOMY = _SCRIPTS.parent / "autonomy"
for _path in (_SCRIPTS, _AUTONOMY):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from claude_bootstrap_receipt import read as read_claude_receipt  # noqa: E402
from breakglass_receipt import evaluate, load_receipt  # noqa: E402

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


def classify_claude_adapter(
    *,
    surface: str,
    receipt: dict[str, Any],
    repair_log: str,
    repair_text: str,
) -> list[dict[str, Any]]:
    state = str(receipt.get("state") or "unknown")
    reason = str(receipt.get("reason") or "")
    log_path = str(receipt.get("log_path") or "")
    repair_hit = (repair_text or "").strip()
    repair_name = repair_log or log_path

    if surface != "claude-code":
        lines = [
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
        if state not in {"ready", ""} or repair_hit:
            how = repair_hit or reason or f"receipt state={state}"
            lines.append(
                _line(
                    "claude-adapter-repair",
                    FAILED if "timeout" in how or state == "never_ran" else DEGRADED,
                    (
                        f"Claude Code SessionStart last repair did not write a "
                        f"receipt (state={state}). How: {how}"
                    ),
                    evidence=f"{repair_name}: {how}" if repair_name else how,
                    this_surface=False,
                    include_in_degraded=True,
                )
            )
        return lines

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


def classify_graphiti(*, detail: str, stderr: str, healthy: bool) -> dict[str, Any]:
    if healthy:
        return _line("graphiti", OK, detail or "healthy")
    evidence = (stderr or "").strip() or detail or "no stderr captured — probe swallowed"
    return _line(
        "graphiti",
        FAILED if "unreachable" in (detail or "").lower() or "refused" in evidence.lower() else DEGRADED,
        detail or "unhealthy",
        evidence=evidence[:500],
    )


def classify_simple(name: str, detail: str, *, fail_tokens: tuple[str, ...] = ()) -> dict[str, Any]:
    text = detail or ""
    lowered = text.lower()
    if any(tok in lowered for tok in fail_tokens):
        klass = FAILED if "fail" in lowered or "refused" in lowered else DEGRADED
        return _line(name, klass, text, evidence=text)
    return _line(name, OK, text or "ok")


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
    runtime = ["### Runtime"]
    for item in lines:
        runtime.append(f"- {item['name']}: {item['class']} — {item['summary']}")
    degraded = [item for item in lines if item.get("include_in_degraded")]
    runtime.append("### Degraded")
    if not degraded:
        runtime.append("- none")
        return "\n".join(runtime)
    for item in degraded:
        ev = item.get("evidence") or ""
        extra = f" Evidence: {ev}" if ev and ev not in item["summary"] else ""
        runtime.append(f"- {item['name']}: {item['class']} — {item['summary']}.{extra}".rstrip("."))
    return "\n".join(runtime)


def collect(
    *,
    surface: str,
    venv: str,
    ide_profile: str,
    tunnel: str,
    graphiti_detail: str,
    graphiti_stderr: str,
    graphiti_healthy: bool,
    wiring: str,
    backup: str,
    skill_note: str,
    codegraph: str,
    hydrate_degraded: bool,
    hydrate_reason: str,
    home: Path | None = None,
) -> list[dict[str, Any]]:
    root = home or Path.home()
    lines: list[dict[str, Any]] = [
        classify_simple("venv", venv, fail_tokens=("absent", "missing", "fail")),
        classify_simple("ide-profile", ide_profile, fail_tokens=("fail", "error")),
        classify_simple("tunnel", tunnel, fail_tokens=("fail", "refused", "error", "closed")),
        classify_graphiti(
            detail=graphiti_detail, stderr=graphiti_stderr, healthy=graphiti_healthy
        ),
        classify_publish_path(evaluate(load_receipt())),
        classify_simple("skill-usage", skill_note, fail_tokens=("absent", "never wrote")),
        classify_itest(error=probe_neo4j(), codegraph=codegraph),
    ]
    receipt = read_claude_receipt()
    repair_log, repair_text = latest_repair_log(root / ".l9" / "claude")
    lines.extend(
        classify_claude_adapter(
            surface=surface,
            receipt=receipt,
            repair_log=repair_log,
            repair_text=repair_text,
        )
    )
    lines.append(classify_simple("wiring", wiring, fail_tokens=("fail",)))
    lines.append(classify_simple("backup", backup, fail_tokens=("fail", "error")))
    if hydrate_degraded:
        lines.append(
            _line(
                "graphiti-hydrate",
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
    parser.add_argument("--graphiti-detail", default="")
    parser.add_argument("--graphiti-stderr", default="")
    parser.add_argument("--graphiti-healthy", default="false")
    parser.add_argument("--wiring", default="")
    parser.add_argument("--backup", default="")
    parser.add_argument("--skill-note", default="")
    parser.add_argument("--codegraph", default="skipped")
    parser.add_argument("--hydrate-degraded", default="false")
    parser.add_argument("--hydrate-reason", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    lines = collect(
        surface=args.surface,
        venv=args.venv,
        ide_profile=args.ide_profile,
        tunnel=args.tunnel,
        graphiti_detail=args.graphiti_detail,
        graphiti_stderr=args.graphiti_stderr,
        graphiti_healthy=_truthy(args.graphiti_healthy),
        wiring=args.wiring,
        backup=args.backup,
        skill_note=args.skill_note,
        codegraph=args.codegraph,
        hydrate_degraded=_truthy(args.hydrate_degraded),
        hydrate_reason=args.hydrate_reason,
    )
    if args.json:
        print(json.dumps({"lines": lines}, indent=2, sort_keys=True))
        return 0
    print(format_markdown(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
