#!/usr/bin/env python3
"""Human stream + interactive unpack for a PR digest. Same semantics as the JSON."""

from __future__ import annotations

from typing import Any


def emit_line(kind: str, payload: dict[str, Any]) -> str:
    if kind == "identity":
        return (
            f"[digest] identity {payload.get('repository')}#{payload.get('pr_number')} "
            f"base={_short(payload.get('base_sha'))} head={_short(payload.get('head_sha'))}"
        )
    if kind == "intent":
        outcome = payload.get("outcome") or "UNKNOWN"
        return f"[digest] intent source={payload.get('source')} outcome={outcome}"
    if kind == "files":
        return (
            f"[digest] files changed={payload.get('changed')} "
            f"added={payload.get('added')} deleted={payload.get('deleted')} "
            f"+{payload.get('lines_added')}/-{payload.get('lines_deleted')}"
        )
    if kind == "finding":
        path = payload.get("path") or "PR"
        return (
            f"[digest] finding {payload.get('severity')} {payload.get('code')} "
            f"{path} — {payload.get('detail')}"
        )
    if kind == "expansion":
        return f"[digest] expansion {payload.get('kind')} {payload.get('path')}"
    if kind == "question":
        return f"[digest] question {payload.get('code')} — {payload.get('question')}"
    if kind == "unknown":
        return f"[digest] unknown {payload.get('code')}"
    if kind == "decision":
        return f"[digest] decision {payload.get('decision')}"
    return f"[digest] {kind} {payload}"


def interactive_report(doc: dict[str, Any]) -> str:
    ident = doc.get("PR_identity") or {}
    intent = doc.get("intent_identity") or {}
    evidence = doc.get("evidence") or {}
    summary = evidence.get("diff_summary") or {}
    checks = evidence.get("CI_checks") or []
    findings = doc.get("deterministic_findings") or []
    judgements = doc.get("judgement_findings") or []
    expansion = doc.get("expansion_items") or []
    narrowing = doc.get("required_narrowing") or []
    questions = doc.get("LLM_judgement_questions") or []
    unknowns = doc.get("unknowns") or []
    packet = doc.get("remediation_packet") or {}
    repo = ident.get("repository") or "UNKNOWN"
    number = ident.get("pr_number") or "UNKNOWN"
    title = intent.get("pr_title") or intent.get("requested_outcome") or "UNKNOWN"
    outcome = intent.get("requested_outcome") or "UNKNOWN"
    changed = summary.get("changed_files") or 0
    added = summary.get("lines_added") or 0
    deleted = summary.get("lines_deleted") or 0
    paragraph = (
        f"{repo}#{number} ({title}) changes {changed} files (+{added}/-{deleted}) "
        f"from `{_short(ident.get('base_sha'))}` to `{_short(ident.get('head_sha'))}`."
    )
    production = summary.get("production_files") or []
    tests = summary.get("test_files") or []
    actually = _bullets([*production[:12], *tests[:8]]) or "- UNKNOWN"
    expansion_lines = (
        _bullets(
            [
                f"{item.get('kind')} `{item.get('path')}` ({item.get('classification')})"
                for item in expansion
            ]
        )
        or "- none"
    )
    arch = _bullets([q.get("question") for q in questions]) or (
        "- no architecture question emitted"
    )
    accepted = {"success", "skipped", "neutral"}
    rejected = {"failure", "failed", "cancelled", "timed_out"}
    ok = [c for c in checks if str(c.get("conclusion") or "").lower() in accepted]
    fail = [c for c in checks if str(c.get("conclusion") or "").lower() in rejected]
    ci_proves = _bullets([f"{c.get('name')}: {c.get('conclusion')}" for c in ok]) or (
        "- no accepted CI evidence"
    )
    ci_not = (
        _bullets([f"{c.get('name')}: {c.get('conclusion')}" for c in fail] + list(unknowns))
        or "- none named"
    )
    finding_lines = (
        _bullets(
            [
                f"{item.get('severity')} `{item.get('code')}` "
                f"{item.get('path') or 'PR'} — {item.get('detail')}"
                for item in findings
            ]
            + [f"judgement — {item}" for item in judgements]
        )
        or "- none"
    )
    narrow_lines = (
        _bullets(
            [
                f"{item.get('reason')} `{item.get('path')}` → {item.get('action')}"
                for item in narrowing
            ]
        )
        or "- none (keep current scope unless a later judgement classifies expansion)"
    )
    packet_lines = _bullets(
        [
            f"accepted: {packet.get('accepted_change_scope') or []}",
            f"attend: {packet.get('files_or_symbols_requiring_attention') or []}",
            f"fix: {len(packet.get('findings_to_fix') or [])} findings",
            f"non-goals: {packet.get('explicit_non_goals') or []}",
            f"UNKNOWN: {packet.get('UNKNOWNs') or []}",
        ]
    )
    return "\n".join(
        [
            f"## PR digest {repo}#{number}",
            "",
            "### 1. PR in one paragraph",
            paragraph,
            "",
            "### 2. Intended change",
            f"- source: `{intent.get('source') or 'UNKNOWN'}`",
            f"- outcome: {outcome}",
            "",
            "### 3. What actually changed",
            actually,
            "",
            "### 4. Expansion map",
            expansion_lines,
            "",
            "### 5. Architecture impact",
            arch,
            "",
            "### 6. What CI proves",
            ci_proves,
            "",
            "### 7. What CI does not prove",
            ci_not,
            "",
            "### 8. Findings",
            finding_lines,
            "",
            "### 9. Narrow-or-keep decisions",
            narrow_lines,
            "",
            "### 10. Remediation packet",
            packet_lines,
            "",
            "### 11. Readiness",
            f"**{doc.get('decision') or 'UNKNOWN'}** · "
            f"confidence `{doc.get('confidence') or 'UNKNOWN'}` · "
            f"LLM_judgement_used={doc.get('LLM_judgement_used')}",
            "",
        ]
    )


def _short(value: Any) -> str:
    text = str(value or "UNKNOWN")
    return text[:12] if len(text) > 12 else text


def _bullets(values: list[Any]) -> str:
    lines = [f"- {value}" for value in values if value not in (None, "", [], {})]
    return "\n".join(lines)
