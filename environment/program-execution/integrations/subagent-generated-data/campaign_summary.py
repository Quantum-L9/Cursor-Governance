from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

SUMMARY_SCHEMA = "l9.pe.subagent-generated-data-summary.v1"


def _display(value: Any) -> str:
    return "UNKNOWN" if value is None else str(value)


def build_summary(
    *,
    database_path: str | Path,
    campaign_id: str,
    campaign_report: dict[str, Any] | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    report = dict(campaign_report or {})
    path = Path(database_path)
    task_counts = report.get("task_counts") or {}
    summary: dict[str, Any] = {
        "schema_version": "1.0.0",
        "schema": SUMMARY_SCHEMA,
        "campaign_id": campaign_id,
        "terminal_status": ("COMPLETE" if not report.get("program_blockers") else "INCOMPLETE"),
        "task_counts": {
            "completed": task_counts.get("completed"),
            "total": task_counts.get("total"),
            "failed": task_counts.get("failed"),
        },
        "generated_data": {
            "subagent_results_seen": None,
            "packets_ingested": 0,
            "packets_validated": 0,
            "packets_rejected": 0,
            "signals_harvested": 0,
            "distilled_units": 0,
            "route_counts_by_destination": {},
        },
        "memory": {
            "memory_candidates_created": 0,
            "memory_candidates_submitted": 0,
            "memory_candidates_accepted": 0,
            "memory_candidates_deferred": 0,
            "memory_candidates_rejected": 0,
            "memory_candidates_deduplicated": 0,
            "memory_candidates_quarantined": 0,
            "memory_units_persisted": 0,
            "memory_failures": 0,
        },
        "receipt_refs": [],
        "errors": [],
        "unresolved_items": [],
    }
    runtime_root = path.parent.parent
    raw_root = runtime_root / "agents" / "results" / "raw"
    if raw_root.is_dir():
        seen = 0
        for raw_path in sorted(raw_root.glob("*.json")):
            try:
                raw = json.loads(raw_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            result = raw.get("result") if isinstance(raw, dict) else None
            identity = result.get("identity") if isinstance(result, dict) else None
            if isinstance(identity, dict) and identity.get("campaign_id") == campaign_id:
                seen += 1
        summary["generated_data"]["subagent_results_seen"] = seen

    workspace_path = Path(workspace) if workspace is not None else None
    if workspace_path is not None:
        runtime_dir = workspace_path / "runtime"
        if runtime_dir.is_dir():
            for result_path in sorted(runtime_dir.glob("*.generated-data.json")):
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    summary["errors"].append(
                        {
                            "code": "GENERATED_DATA_RESULT_UNREADABLE",
                            "path": str(result_path),
                            "message": str(exc),
                        }
                    )
                    continue
                if result.get("schema") == "l9.pe.generated-data-publication-failure.v1":
                    summary["errors"].append(
                        {
                            "code": "PE_OUTCOME_PUBLISH_FAILED",
                            "task_id": result.get("task_id"),
                            "path": str(result_path),
                            "message": result.get("error"),
                        }
                    )

    if not path.is_file():
        summary["errors"].append({"code": "GENERATED_DATA_DATABASE_MISSING", "path": str(path)})
        return summary

    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    try:
        jobs = connection.execute(
            "SELECT job_id, state, packet_id, error_code, error_message "
            "FROM processing_jobs WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchall()
        job_ids = [row["job_id"] for row in jobs]
        summary["generated_data"]["packets_ingested"] = len(jobs)
        summary["generated_data"]["packets_rejected"] = sum(
            1 for row in jobs if row["state"] == "REJECTED"
        )
        for row in jobs:
            if row["error_code"]:
                summary["errors"].append(
                    {
                        "job_id": row["job_id"],
                        "code": row["error_code"],
                        "message": row["error_message"],
                    }
                )
        if not job_ids:
            return summary
        placeholders = ",".join("?" for _ in job_ids)
        events = connection.execute(
            f"SELECT job_id, to_state FROM job_events WHERE job_id IN ({placeholders})",
            job_ids,
        ).fetchall()
        validated_jobs = {row["job_id"] for row in events if row["to_state"] == "VALIDATED"}
        summary["generated_data"]["packets_validated"] = len(validated_jobs)

        snapshots = connection.execute(
            f"SELECT stage, payload_json FROM stage_snapshots WHERE job_id IN ({placeholders})",
            job_ids,
        ).fetchall()
        routes: Counter[str] = Counter()
        promoted_memory_units: set[str] = set()
        for row in snapshots:
            payload = json.loads(row["payload_json"])
            if row["stage"] == "HARVESTED":
                summary["generated_data"]["signals_harvested"] += 1
            elif row["stage"] == "DELIVERY_PENDING":
                route = str(payload.get("route") or "unknown")
                destination = str(
                    (payload.get("routing_decision") or {}).get("destination") or route
                )
                routes[destination] += 1
                if route == "memory":
                    promoted_memory_units.add(str(payload.get("unit_id") or ""))
        summary["generated_data"]["route_counts_by_destination"] = dict(sorted(routes.items()))
        summary["memory"]["memory_candidates_created"] = len(
            {item for item in promoted_memory_units if item}
        )

        receipts = connection.execute(
            f"SELECT receipt_id, unit_id, route, destination_status, "
            f"destination_reference, payload_json FROM delivery_receipts "
            f"WHERE job_id IN ({placeholders})",
            job_ids,
        ).fetchall()
        for row in receipts:
            if row["route"] != "memory":
                continue
            status = str(row["destination_status"]).lower()
            summary["receipt_refs"].append(
                {
                    "receipt_id": row["receipt_id"],
                    "unit_id": row["unit_id"],
                    "status": status,
                    "reference": row["destination_reference"],
                }
            )
            if status in {"enqueued", "already_enqueued", "submitted"}:
                summary["memory"]["memory_candidates_submitted"] += 1
            elif status in {"accepted", "admitted", "merged"}:
                summary["memory"]["memory_candidates_accepted"] += 1
                summary["memory"]["memory_units_persisted"] += 1
                summary["generated_data"]["distilled_units"] += 1
            elif status in {"duplicate", "deduplicated", "already_exists"}:
                summary["memory"]["memory_candidates_deduplicated"] += 1
                summary["memory"]["memory_units_persisted"] += 1
                summary["generated_data"]["distilled_units"] += 1
            elif status in {"quarantined", "contested", "deferred"}:
                summary["memory"]["memory_candidates_quarantined"] += 1
                summary["memory"]["memory_candidates_deferred"] += 1
                summary["generated_data"]["distilled_units"] += 1
            elif status in {"rejected", "denied"}:
                summary["memory"]["memory_candidates_rejected"] += 1

        failed_attempts = connection.execute(
            f"SELECT COUNT(*) AS n FROM delivery_attempts "
            f"WHERE job_id IN ({placeholders}) AND status = 'FAILED'",
            job_ids,
        ).fetchone()["n"]
        dead_letters = connection.execute(
            f"SELECT COUNT(*) AS n FROM dead_letters "
            f"WHERE job_id IN ({placeholders}) AND status = 'OPEN'",
            job_ids,
        ).fetchone()["n"]
        summary["memory"]["memory_failures"] = max(int(failed_attempts), int(dead_letters))
        return summary
    finally:
        connection.close()


def render_brief(summary: dict[str, Any]) -> str:
    tasks = summary["task_counts"]
    generated = summary["generated_data"]
    memory = summary["memory"]
    lines = [
        f"Campaign {summary['campaign_id']}: {summary['terminal_status']}",
        (
            "Tasks: "
            f"{_display(tasks.get('completed'))}/{_display(tasks.get('total'))} complete, "
            f"{_display(tasks.get('failed'))} failed"
        ),
        (f"Subagents: {_display(generated.get('subagent_results_seen'))} result packets captured"),
        (
            "Generated data: "
            f"{generated['packets_ingested']} ingested, "
            f"{generated['packets_validated']} validated, "
            f"{generated['packets_rejected']} rejected"
        ),
        (
            f"Harvested: {generated['signals_harvested']} signals; "
            f"distilled: {generated['distilled_units']} units"
        ),
        "Routes: "
        + (
            ", ".join(
                f"{name} {count}"
                for name, count in generated["route_counts_by_destination"].items()
            )
            or "none"
        ),
        (
            "Memory: "
            f"{memory['memory_candidates_submitted']} submitted, "
            f"{memory['memory_candidates_accepted']} accepted, "
            f"{memory['memory_candidates_deduplicated']} deduplicated, "
            f"{memory['memory_candidates_deferred']} deferred, "
            f"{memory['memory_candidates_quarantined']} quarantined, "
            f"{memory['memory_candidates_rejected']} rejected"
        ),
        (
            f"Memory persisted: {memory['memory_units_persisted']}; "
            f"failures: {memory['memory_failures']}"
        ),
    ]
    return "\n".join(lines)


def write_summary(
    *,
    workspace: str | Path,
    database_path: str | Path,
    campaign_id: str,
    campaign_report: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    summary = build_summary(
        database_path=database_path,
        campaign_id=campaign_id,
        campaign_report=campaign_report,
        workspace=workspace,
    )
    telemetry = Path(workspace) / "telemetry"
    telemetry.mkdir(parents=True, exist_ok=True)
    json_path = telemetry / "subagent-generated-data-summary.json"
    md_path = telemetry / "subagent-generated-data-summary.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_brief(summary) + "\n", encoding="utf-8")
    return summary, json_path, md_path
