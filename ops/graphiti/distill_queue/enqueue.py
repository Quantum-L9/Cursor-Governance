"""Enqueue redacted SessionEnd distill jobs to S3 (content-hash idempotent)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA_VERSION = "distill_queue_job/v1"
DEFAULT_PREFIX = "distill-queue/pending/"
AWS_CALL_TIMEOUT = 20
EXCERPT_CAP = 12000


def enqueue_enabled() -> bool:
    flag = os.environ.get("MEMORY_DISTILL_ENQUEUE", "1").strip()
    if flag in ("0", "false", "False"):
        return False
    return bool(os.environ.get("MEMORY_DISTILL_S3_BUCKET", "").strip())


def bucket_configured() -> bool:
    return bool(os.environ.get("MEMORY_DISTILL_S3_BUCKET", "").strip())


def job_content_hash(*, session_id: str, excerpt: str) -> str:
    material = f"{session_id}\n{excerpt}".encode()
    return hashlib.sha256(material).hexdigest()


def build_job(
    *,
    session_id: str,
    group_id: str,
    agent_id: str,
    transcript_excerpt: str,
    heuristic_pickup: dict[str, Any] | None = None,
    reason: str = "completed",
    project_name: str = "",
) -> dict[str, Any]:
    excerpt = (transcript_excerpt or "").strip()[:EXCERPT_CAP]
    if not excerpt:
        raise ValueError("transcript_excerpt required for distill enqueue")
    content_hash = job_content_hash(session_id=session_id, excerpt=excerpt)
    return {
        "schema_version": SCHEMA_VERSION,
        "job_id": content_hash[:32],
        "content_hash": content_hash,
        "session_id": session_id,
        "group_id": group_id,
        "agent_id": agent_id,
        "reason": reason,
        "transcript_excerpt": excerpt,
        "heuristic_pickup": heuristic_pickup or {},
        "enqueued_at": datetime.now(UTC).isoformat(),
        "project_name": project_name or "",
    }


def object_key(content_hash: str) -> str:
    prefix = os.environ.get("MEMORY_DISTILL_S3_PREFIX", DEFAULT_PREFIX).strip()
    if not prefix.endswith("/"):
        prefix += "/"
    return f"{prefix}{content_hash}.json"


def _aws_region() -> str:
    return (
        os.environ.get("AWS_REGION", "").strip()
        or os.environ.get("AWS_DEFAULT_REGION", "").strip()
        or "us-east-1"
    )


def put_job_s3(
    job: dict[str, Any],
    *,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    """Put job JSON to S3. Idempotent overwrite on same content_hash key."""
    bucket = os.environ.get("MEMORY_DISTILL_S3_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("MEMORY_DISTILL_S3_BUCKET unset")
    key = object_key(str(job["content_hash"]))
    body = json.dumps(job, ensure_ascii=False, indent=2) + "\n"
    proc = runner(
        [
            "aws",
            "s3api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--body",
            "-",
            "--content-type",
            "application/json",
            "--region",
            _aws_region(),
        ],
        input=body,
        capture_output=True,
        text=True,
        timeout=AWS_CALL_TIMEOUT,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "put-object failed").strip()[:300]
        raise RuntimeError(f"s3 put-object failed: {err}")
    return {"ok": True, "bucket": bucket, "key": key, "content_hash": job["content_hash"]}


def enqueue_job(
    *,
    session_id: str,
    group_id: str,
    agent_id: str,
    transcript_excerpt: str,
    heuristic_pickup: dict[str, Any] | None = None,
    reason: str = "completed",
    project_name: str = "",
    dry_run: bool = False,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    """Build + enqueue. Raises on failure when called (caller decides fail-loud)."""
    job = build_job(
        session_id=session_id,
        group_id=group_id,
        agent_id=agent_id,
        transcript_excerpt=transcript_excerpt,
        heuristic_pickup=heuristic_pickup,
        reason=reason,
        project_name=project_name,
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "key": object_key(str(job["content_hash"])),
            "content_hash": job["content_hash"],
            "job": job,
        }
    result = put_job_s3(job, runner=runner)
    result["job_id"] = job["job_id"]
    return result
