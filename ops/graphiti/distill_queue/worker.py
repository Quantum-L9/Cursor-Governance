"""GHA / offline worker: pull pending S3 distill jobs → OpenAI → canonical memory.

Since realignment stage C10 every write crosses the memory control plane
(``ops/memory``): the distilled PICKUP becomes a continuation capsule admitted
as a governed candidate, and promoted atomics go through the generic canonical
write with idempotency keys. Nothing here calls a provider; the memory
runtime the worker is bound to (``L9_MEMORY_INTERPRETER`` /
``ops/config/memory-binding.json``) owns storage and projection.
"""

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
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
from ops.memory.control_plane_client import OutcomeStatus  # noqa: E402
from ops.memory.session_contracts import ContinuationCapsuleV2  # noqa: E402

AWS_CALL_TIMEOUT = 60
DONE_PREFIX_DEFAULT = "distill-queue/done/"
DISTILL_PRODUCER_VERSION = "distill-queue/2.0.0"
#: Promotion kinds -> canonical memory classes (write taxonomy, plan §14).
_PROMOTION_CLASSES = {"lesson": "insight", "insight": "insight", "decision": "decision"}
_NOT_ADMITTED = frozenset(
    {
        OutcomeStatus.CANONICAL_UNAVAILABLE,
        OutcomeStatus.TIMEOUT,
        OutcomeStatus.BINDING_FAILED,
        OutcomeStatus.INVALID_RECEIPT,
    }
)


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


def build_continuation(job: dict[str, Any], packet: dict[str, Any]) -> ContinuationCapsuleV2:
    """The distilled PICKUP as the Cursor-owned continuation capsule (plan §12).

    The job carries no checkout, so the repository state is ``unknown`` and the
    next hydrate reports the capsule stale against any real HEAD — current git
    state wins, which is the correct precedence for an offline distillation.
    """
    rich = packet.get("pickup") or {}
    blockers = rich.get("blockers") or ()
    if isinstance(blockers, str):
        blockers = (blockers,)
    return ContinuationCapsuleV2(
        session_id=str(job.get("session_id") or packet.get("packet_id") or "distill"),
        repository_identity=str(job.get("repository") or job.get("group_id") or "unknown"),
        objective=str(rich.get("active_objective") or "Resume from distill queue"),
        next_action=str(rich.get("next_action") or "Continue from the canonical continuation"),
        repository_state_digest=str(job.get("source_sha") or "unknown"),
        producer_version=DISTILL_PRODUCER_VERSION,
        blockers=tuple(str(b) for b in blockers)[:8],
    )


def _memory_client(session_id: str | None) -> Any:
    from ops.memory.control_plane_client import MemoryControlPlaneClient
    from ops.memory.runtime_binding import resolve_runtime_binding

    return MemoryControlPlaneClient(resolve_runtime_binding(), session_id=session_id, timeout=60.0)


def ingest_to_memory(
    job: dict[str, Any],
    packet: dict[str, Any],
    *,
    dry_run: bool = False,
    client: Any = None,
    workspace: str | None = None,
) -> list[dict[str, Any]]:
    """Admit the continuation capsule and promoted atomics through the control plane.

    A rejected or quarantined verdict is recorded and the job still completes
    (memory's verdict is the answer); an unavailable, unbound, timed-out or
    invalid-receipt outcome raises so the job stays pending and is retried.
    """
    writes: list[dict[str, Any]] = []
    namespace = str(job["group_id"])
    agent_id = str(job.get("agent_id") or "gha-distill")
    session_id = str(job.get("session_id") or "")
    content_hash = str(job.get("content_hash") or packet.get("packet_id") or "")
    client = client or _memory_client(session_id or None)
    workspace = workspace or os.getcwd()
    if not client.binding.ok:
        raise RuntimeError("memory runtime unbound: " + ("; ".join(client.binding.reasons) or "?"))

    capsule = build_continuation(job, packet)
    candidate = capsule.to_governed_candidate(
        namespace=namespace,
        source_sha=capsule.repository_state_digest or "unknown",
        agent_id=agent_id,
    )
    if dry_run:
        writes.append({"written": False, "dry_run": True, "kind": "session_continuation"})
    else:
        admitted = client.ingest_candidate(candidate, workspace=workspace)
        if admitted.status in _NOT_ADMITTED:
            raise RuntimeError(f"continuation not admitted: {admitted.status.value}")
        receipt = admitted.receipt
        writes.append(
            {
                "written": admitted.ok,
                "kind": "session_continuation",
                "status": receipt.status if receipt is not None else admitted.status.value,
                "record_id": getattr(receipt, "record_id", None),
            }
        )

    for idx, item in enumerate(_eligible_promotions(packet)):
        kind = item["kind"]
        memory_class = _PROMOTION_CLASSES.get(kind, "insight")
        if dry_run:
            writes.append({"written": False, "dry_run": True, "kind": kind})
            continue
        outcome = client.write(
            item["body"],
            workspace=workspace,
            namespace=namespace,
            memory_class=memory_class,
            tags=("distill", kind),
            idempotency_key=f"distill:{content_hash}:{idx}",
            source="gha-distill",
            source_id=f"{packet.get('packet_id')}:{idx}",
        )
        if outcome.status in _NOT_ADMITTED:
            raise RuntimeError(f"promotion not admitted: {outcome.status.value}")
        receipt = outcome.receipt
        writes.append(
            {
                "written": outcome.ok,
                "kind": kind,
                "status": receipt.status if receipt is not None else outcome.status.value,
                "record_id": getattr(receipt, "record_id", None),
            }
        )
    return writes


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


def process_pending(
    *,
    max_jobs: int = 20,
    dry_run: bool = False,
    runner: Any = subprocess.run,
    client: Any = None,
    workspace: str | None = None,
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
            # Broad by design; the handler below carries the reason.
            # nosemgrep: l9.baseline.python.broad-except
            try:
                job = get_job_to_path(key, job_path, runner=runner)
                content_hash = str(job.get("content_hash") or "")
                if content_hash and already_ingested(content_hash, runner=runner):
                    report["skipped"] += 1
                    mark_done(key, job, runner=runner)
                    continue
                packet = distill_job(job)
                writes = ingest_to_memory(
                    job, packet, dry_run=dry_run, client=client, workspace=workspace
                )
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
    parser = argparse.ArgumentParser(description="Process S3 distill queue → canonical memory")
    parser.add_argument("--max-jobs", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--workspace",
        default=None,
        help="checkout the memory CLI runs in (its principal derives from it); default cwd",
    )
    args = parser.parse_args(argv)

    # Fail-loud on missing mandatory config
    if not os.environ.get("MEMORY_DISTILL_S3_BUCKET", "").strip():
        _err("missing_bucket")
        return 1

    key, _key_reason = resolve_openai_api_key()
    if not key:
        _err("openai_key")
        return 1

    # The memory runtime is proven, never assumed (INV-11): an unbound worker
    # writes nothing and says so before touching the queue.
    client = _memory_client(None)
    if not client.binding.ok:
        _err("runtime")
        print(
            "ERROR: memory runtime unbound — " + "; ".join(client.binding.reasons), file=sys.stderr
        )
        return 1

    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        report = process_pending(
            max_jobs=args.max_jobs, dry_run=args.dry_run, client=client, workspace=args.workspace
        )
    except Exception:  # noqa: BLE001
        _err("main")
        return 1

    print(json.dumps(_public_report(report), indent=2, ensure_ascii=False))
    if report.get("status") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
