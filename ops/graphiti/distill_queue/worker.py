"""GHA / offline worker: pull pending S3 distill jobs → OpenAI → Graphiti."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_GRAPHITI_DIR = _REPO_ROOT / "ops" / "graphiti"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_GRAPHITI_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPHITI_DIR))

from ops.graphiti.distill_queue.enqueue import (  # noqa: E402
    DEFAULT_PREFIX,
    SCHEMA_VERSION,
)
from ops.graphiti.hydration.openai_fixed_host import (  # noqa: E402
    OpenAIFixedHostError,
    chat_completions,
    message_content,
)
from ops.graphiti.hydration.openai_key import resolve_openai_api_key  # noqa: E402

AWS_CALL_TIMEOUT = 60
DONE_PREFIX_DEFAULT = "distill-queue/done/"


_ERR_TOKENS = frozenset(
    {
        "missing_bucket",
        "openai_key",
        "runtime",
        "value",
        "os",
        "timeout",
        "job",
        "main",
        "failed",
    }
)


def _err(kind: str) -> None:
    """Log a closed-set token only. Callers must pass untainted literals/kinds."""
    token = kind if kind in _ERR_TOKENS else "failed"
    print(f"::error::distill_worker_{token}", file=sys.stderr)
    print(f"ERROR: distill_worker_{token}", file=sys.stderr)


def _aws_region() -> str:
    return (
        os.environ.get("AWS_REGION", "").strip()
        or os.environ.get("AWS_DEFAULT_REGION", "").strip()
        or "us-east-1"
    )


def _bucket() -> str:
    bucket = os.environ.get("MEMORY_DISTILL_S3_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("MEMORY_DISTILL_S3_BUCKET unset")
    return bucket


def _pending_prefix() -> str:
    prefix = os.environ.get("MEMORY_DISTILL_S3_PREFIX", DEFAULT_PREFIX).strip()
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def _done_prefix() -> str:
    prefix = os.environ.get("MEMORY_DISTILL_S3_DONE_PREFIX", DONE_PREFIX_DEFAULT).strip()
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def list_pending_keys(*, runner: Any = subprocess.run, max_keys: int = 50) -> list[str]:
    bucket = _bucket()
    prefix = _pending_prefix()
    proc = runner(
        [
            "aws",
            "s3api",
            "list-objects-v2",
            "--bucket",
            bucket,
            "--prefix",
            prefix,
            "--max-keys",
            str(max_keys),
            "--region",
            _aws_region(),
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=AWS_CALL_TIMEOUT,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "list-objects-v2 failed").strip()[:400])
    data = json.loads(proc.stdout or "{}")
    keys: list[str] = []
    for item in data.get("Contents") or []:
        key = str(item.get("Key") or "")
        if key.endswith(".json"):
            keys.append(key)
    return keys


def get_job_to_path(key: str, dest: Path, *, runner: Any = subprocess.run) -> dict[str, Any]:
    bucket = _bucket()
    proc = runner(
        [
            "aws",
            "s3api",
            "get-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--region",
            _aws_region(),
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=AWS_CALL_TIMEOUT,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or f"get-object {key} failed").strip()[:400])
    data = json.loads(dest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"job {key} is not a JSON object")
    return data


def mark_done(key: str, job: dict[str, Any], *, runner: Any = subprocess.run) -> None:
    bucket = _bucket()
    content_hash = str(job.get("content_hash") or Path(key).stem)
    done_key = f"{_done_prefix()}{content_hash}.json"
    # Copy then delete pending (idempotent if already done).
    proc = runner(
        [
            "aws",
            "s3",
            "cp",
            f"s3://{bucket}/{key}",
            f"s3://{bucket}/{done_key}",
            "--region",
            _aws_region(),
        ],
        capture_output=True,
        text=True,
        timeout=AWS_CALL_TIMEOUT,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "s3 cp done failed").strip()[:400])
    runner(
        [
            "aws",
            "s3",
            "rm",
            f"s3://{bucket}/{key}",
            "--region",
            _aws_region(),
        ],
        capture_output=True,
        text=True,
        timeout=AWS_CALL_TIMEOUT,
        check=False,
    )


def already_ingested(content_hash: str, *, runner: Any = subprocess.run) -> bool:
    bucket = _bucket()
    done_key = f"{_done_prefix()}{content_hash}.json"
    proc = runner(
        [
            "aws",
            "s3api",
            "head-object",
            "--bucket",
            bucket,
            "--key",
            done_key,
            "--region",
            _aws_region(),
        ],
        capture_output=True,
        text=True,
        timeout=AWS_CALL_TIMEOUT,
        check=False,
    )
    return proc.returncode == 0


def distill_job(job: dict[str, Any], *, timeout: float = 45.0) -> dict[str, Any]:
    """LLM distill → SessionSignalPacket-shaped dict."""
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError(f"unsupported schema_version: {job.get('schema_version')}")
    key, reason = resolve_openai_api_key()
    if not key:
        raise RuntimeError(reason or "openai_key_absent")
    excerpt = str(job.get("transcript_excerpt") or "")[:12000]
    pickup = job.get("heuristic_pickup") or {}
    session_id = str(job.get("session_id") or "")
    budget_tokens = int(os.environ.get("MEMORY_DISTILL_TOKEN_BUDGET", "300"))
    system = (
        "Extract durable session signals. Output ONLY JSON with keys: "
        "promotion_decisions (list of {kind, body, decision, score}), "
        "pickup ({active_objective, next_action, context_slice, blockers}), "
        "do_not_promote (list of strings). "
        "kind in lesson|insight|decision|preference|constraint; "
        "decision in promote|defer|reject. "
        "Promote only durable facts; never dump the transcript."
    )
    user = json.dumps(
        {
            "session_id": session_id,
            "heuristic_pickup": pickup,
            "transcript_excerpt": excerpt,
        },
        ensure_ascii=False,
    )
    try:
        resp = chat_completions(
            api_key=key,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=budget_tokens,
            timeout=timeout,
        )
        text = message_content(resp)
    except OpenAIFixedHostError as exc:
        raise RuntimeError(str(exc)) from exc
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise RuntimeError("distill returned non-object JSON")
    packet_id = hashlib.sha256(f"{session_id}:{time.time()}".encode()).hexdigest()[:16]
    return {
        "packet_id": packet_id,
        "session_id": session_id,
        "promotion_decisions": data.get("promotion_decisions") or [],
        "pickup": data.get("pickup") or pickup,
        "do_not_promote": data.get("do_not_promote") or [],
        "content_hash": job.get("content_hash"),
    }


def _pickup_payload(
    job: dict[str, Any],
    packet: dict[str, Any],
    *,
    agent_id: str,
    user_id: str,
    group_id: str,
) -> dict[str, Any]:
    from ops.graphiti.hydration.identity import stamp_source_description

    rich = packet.get("pickup") or {}
    objective = str(rich.get("active_objective") or "Resume from distill queue")
    next_action = str(rich.get("next_action") or "Continue from Graphiti PICKUP")
    search_line = (
        f"PICKUP|objective={objective}|next={next_action}|"
        f"agent={agent_id}|session={job.get('session_id')}"
    )
    pickup_body = (
        search_line
        + "\n"
        + json.dumps(
            {
                "type": "PICKUP",
                "active_objective": objective,
                "next_action": next_action,
                "context_slice": rich.get("context_slice") or "",
                "session_id": job.get("session_id"),
                "packet_id": packet.get("packet_id"),
                "content_hash": job.get("content_hash"),
                "agent_id": agent_id,
                "source": "gha_distill_queue",
                "search_line": search_line,
            },
            ensure_ascii=False,
        )
    )
    payload: dict[str, Any] = {
        "name": f"pickup-{job.get('session_id')}-{packet.get('packet_id')}",
        "episode_body": pickup_body,
        "source": "text",
        "source_description": stamp_source_description(agent_id, "pickup_context"),
        "group_id": group_id,
    }
    try:
        from episode_contract import EpisodeContract

        ep = EpisodeContract(
            name=payload["name"],
            episode_body=pickup_body,
            source="text",
            source_description=payload["source_description"],
            group_id=group_id,
            agent_id=agent_id,
            user_id=user_id,
            reference_time=datetime.now(UTC),
        )
        payload = ep.to_mcp_payload()
    except Exception:  # noqa: BLE001
        pass
    return payload


def _eligible_promotions(packet: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in packet.get("promotion_decisions") or []:
        if len(out) >= limit:
            break
        if not isinstance(item, dict) or item.get("decision") != "promote":
            continue
        kind = str(item.get("kind") or "lesson")
        if kind not in {"lesson", "insight", "decision"}:
            continue
        body = str(item.get("body") or "").strip()
        if not body or float(item.get("score") or 0) < 0.65:
            continue
        out.append({"kind": kind, "body": body})
    return out


def ingest_to_graphiti(
    job: dict[str, Any],
    packet: dict[str, Any],
    *,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Write PICKUP + promoted atomics via Graphiti client (no C1)."""
    import graphiti_memory_client as gmc

    from ops.graphiti.hydration.identity import stamp_source_description

    writes: list[dict[str, Any]] = []
    group_id = str(job["group_id"])
    agent_id = str(job.get("agent_id") or "gha-distill")
    user_id = os.environ.get("USER_ID", "gha_distill_agent")
    gmc.load_env()
    # Prefer public HTTPS for GHA when tunnel unavailable
    if not os.environ.get("GRAPHITI_MCP_URL", "").strip():
        os.environ["GRAPHITI_MCP_URL"] = "https://memory.quantumaipartners.com/graphiti/mcp"

    payload = _pickup_payload(job, packet, agent_id=agent_id, user_id=user_id, group_id=group_id)
    if dry_run:
        writes.append({"written": False, "dry_run": True, "kind": "pickup_context"})
    else:
        gmc.call_tool("add_memory", payload)
        writes.append({"written": True, "kind": "pickup_context"})

    for idx, item in enumerate(_eligible_promotions(packet)):
        kind = item["kind"]
        promo_payload = {
            "name": f"{kind}-{packet.get('packet_id')}-{idx}",
            "episode_body": item["body"],
            "source": "text",
            "source_description": stamp_source_description(agent_id, kind),
            "group_id": group_id,
        }
        if dry_run:
            writes.append({"written": False, "dry_run": True, "kind": kind})
        else:
            gmc.call_tool("add_memory", promo_payload)
            writes.append({"written": True, "kind": kind})
    return writes


def process_pending(
    *,
    max_jobs: int = 20,
    dry_run: bool = False,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
        "jobs": [],
        "started_at": datetime.now(UTC).isoformat(),
    }
    keys = list_pending_keys(runner=runner, max_keys=max_jobs)
    if not keys:
        report["status"] = "empty"
        return report

    with tempfile.TemporaryDirectory(prefix="distill-job-") as tmp:
        tmp_path = Path(tmp)
        for key in keys:
            job_path = tmp_path / "job.json"
            try:
                job = get_job_to_path(key, job_path, runner=runner)
                content_hash = str(job.get("content_hash") or "")
                if content_hash and already_ingested(content_hash, runner=runner):
                    report["skipped"] += 1
                    mark_done(key, job, runner=runner)
                    continue
                packet = distill_job(job)
                writes = ingest_to_graphiti(job, packet, dry_run=dry_run)
                if not dry_run:
                    mark_done(key, job, runner=runner)
                report["processed"] += 1
                report["jobs"].append(
                    {
                        "key": key,
                        "content_hash": content_hash,
                        "writes": len(writes),
                        "packet_id": packet.get("packet_id"),
                    }
                )
            except Exception:  # noqa: BLE001
                report["failed"] += 1
                report["errors"].append("job")
                _err("job")

    report["finished_at"] = datetime.now(UTC).isoformat()
    if report["failed"]:
        report["status"] = "failed"
    else:
        report["status"] = "ok"
    return report


def _public_report(report: dict[str, Any]) -> dict[str, Any]:
    """Stdout-safe subset — ints/bools/counts only (breaks secret taint)."""
    return {
        "status": "ok" if report.get("status") == "ok" else "other",
        "processed": int(report.get("processed") or 0),
        "failed": int(report.get("failed") or 0),
        "skipped": int(report.get("skipped") or 0),
        "job_count": len(report.get("jobs") or []),
        "error_count": len(report.get("errors") or []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Process S3 distill queue → Graphiti")
    parser.add_argument("--max-jobs", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    # Fail-loud on missing mandatory config
    if not os.environ.get("MEMORY_DISTILL_S3_BUCKET", "").strip():
        _err("missing_bucket")
        return 1

    key, _key_reason = resolve_openai_api_key()
    if not key:
        _err("openai_key")
        return 1

    if not os.environ.get("GRAPHITI_MCP_TOKEN", "").strip() and not args.dry_run:
        # Token may be optional on some deployments; warn loudly but continue if URL set.
        print("WARN: graphiti_token_unset", file=sys.stderr)

    try:
        report = process_pending(max_jobs=args.max_jobs, dry_run=args.dry_run)
    except Exception:  # noqa: BLE001
        _err("main")
        return 1

    print(json.dumps(_public_report(report), indent=2, ensure_ascii=False))
    if report.get("status") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
