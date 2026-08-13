"""Archive closed-chat words + timestamps to S3 (no sqlite, no tool dumps)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_GRAPHITI_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _GRAPHITI_DIR.parent.parent
if str(_GRAPHITI_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPHITI_DIR))
from episode_contract import redact_pii  # noqa: E402

SCHEMA = "l9-chat-transcript/v1"
DEFAULT_BUCKET = "l9-chat-transcripts-020125249784"
AWS_CALL_TIMEOUT = 30
USER_QUERY = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL | re.IGNORECASE)
TIMESTAMP = re.compile(r"<timestamp>\s*(.*?)\s*</timestamp>", re.DOTALL | re.IGNORECASE)
NOISE_PREFIXES = (
    "<git_status>",
    "<agent_transcripts>",
    "<agent_skills>",
    "<open_and_recently_viewed_files>",
)


def pending_root() -> Path:
    return Path.home() / ".local" / "share" / "l9" / "chat-transcripts"


def bucket_name() -> str:
    return os.environ.get("L9_CHAT_TRANSCRIPT_S3_BUCKET", "").strip() or DEFAULT_BUCKET


def _aws_region() -> str:
    return (
        os.environ.get("AWS_REGION", "").strip()
        or os.environ.get("AWS_DEFAULT_REGION", "").strip()
        or "us-east-1"
    )


def object_key(conversation_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", conversation_id)[:120] or "unknown"
    return f"v1/{safe}.json"


def _text_blocks(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") and block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()


def _user_words(raw: str) -> tuple[str | None, str]:
    ts = None
    match_ts = TIMESTAMP.search(raw)
    if match_ts:
        ts = match_ts.group(1).strip()
    match_q = USER_QUERY.search(raw)
    if match_q:
        return ts, match_q.group(1).strip()
    stripped = raw.strip()
    if any(stripped.startswith(p) for p in NOISE_PREFIXES):
        return ts, ""
    return ts, stripped


def extract_turns(path: Path) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return turns
    seq = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        role = str(obj.get("role") or "").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        message = obj.get("message") if isinstance(obj.get("message"), dict) else obj
        raw = _text_blocks(message.get("content") if isinstance(message, dict) else "")
        at = None
        if role == "user":
            at, raw = _user_words(raw)
        if not raw:
            continue
        seq += 1
        turns.append(
            {
                "seq": seq,
                "role": role,
                "at": at,
                "text": redact_pii(raw),
            }
        )
    return turns


def build_document(
    *,
    conversation_id: str,
    source_path: Path,
    project_dir: str,
    turns: list[dict[str, Any]],
    host: str | None = None,
) -> dict[str, Any]:
    times = file_times(source_path)
    parent_id = None
    if "subagents" in source_path.parts:
        try:
            idx = source_path.parts.index("agent-transcripts")
            parent_id = source_path.parts[idx + 1]
        except (ValueError, IndexError):
            parent_id = None
    try:
        size = source_path.stat().st_size
    except OSError:
        size = None
    closed_at = datetime.now(UTC).isoformat(timespec="seconds")
    return {
        "schema": SCHEMA,
        "conversation_id": conversation_id,
        "parent_conversation_id": parent_id,
        "closed_at": closed_at,
        "source_mtime": times["mtime"],
        "source_birth": times["birth"],
        "source_bytes": size,
        "host": host or socket.gethostname(),
        "workspace": Path(project_dir).expanduser().resolve().name if project_dir else "",
        "source_path": str(source_path),
        "turn_count": len(turns),
        "turns": turns,
    }


def resolve_source(
    *,
    transcript_path: str | None,
    conversation_id: str,
) -> Path | None:
    if transcript_path:
        candidate = Path(transcript_path).expanduser()
        if candidate.is_file():
            return candidate
    from ops.graphiti.hydration.transcript import _find_agent_transcript

    return _find_agent_transcript(conversation_id)


def write_pending(doc: dict[str, Any]) -> Path:
    root = pending_root()
    pending = root / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    path = pending / f"{doc['conversation_id']}.json"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def put_s3(doc: dict[str, Any], *, runner: Any = subprocess.run) -> dict[str, Any]:
    bucket = bucket_name()
    key = object_key(str(doc["conversation_id"]))
    body = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    tmp_path = pending_root() / "pending" / f".{doc['conversation_id']}.put.json"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(body, encoding="utf-8")
    try:
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
                str(tmp_path),
                "--content-type",
                "application/json",
                "--region",
                _aws_region(),
            ],
            capture_output=True,
            text=True,
            timeout=AWS_CALL_TIMEOUT,
            check=False,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "put-object failed").strip()[:300]
        raise RuntimeError(f"s3 put-object failed: {err}")
    return {"ok": True, "bucket": bucket, "key": key}


def mark_done(pending_path: Path, result: dict[str, Any]) -> None:
    root = pending_root()
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = {
        "conversation_id": pending_path.stem,
        "bucket": result.get("bucket"),
        "key": result.get("key"),
        "uploaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "bytes": pending_path.stat().st_size if pending_path.is_file() else 0,
    }
    (receipts / f"{pending_path.stem}.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    pending_path.unlink(missing_ok=True)


def archive_one(
    *,
    conversation_id: str,
    project_dir: str = "",
    transcript_path: str | None = None,
    dry_run: bool = False,
    upload: bool = True,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    source = resolve_source(transcript_path=transcript_path, conversation_id=conversation_id)
    if source is None:
        return {"ok": False, "reason": "no_transcript", "conversation_id": conversation_id}
    turns = extract_turns(source)
    if not turns:
        return {
            "ok": False,
            "reason": "no_words",
            "conversation_id": conversation_id,
            "source": str(source),
        }
    doc = build_document(
        conversation_id=conversation_id,
        source_path=source,
        project_dir=project_dir,
        turns=turns,
    )
    pending = write_pending(doc)
    report: dict[str, Any] = {
        "ok": True,
        "conversation_id": conversation_id,
        "turn_count": len(turns),
        "pending": str(pending),
        "key": object_key(conversation_id),
    }
    if dry_run or not upload:
        report["dry_run"] = True
        return report
    result = put_s3(doc, runner=runner)
    mark_done(pending, result)
    report.update(result)
    return report


def file_times(path: Path) -> dict[str, str | None]:
    try:
        st = path.stat()
    except OSError:
        return {"mtime": None, "birth": None}
    mtime = datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")
    birth_ts = getattr(st, "st_birthtime", None)
    birth = (
        datetime.fromtimestamp(birth_ts).astimezone().isoformat(timespec="seconds")
        if birth_ts
        else None
    )
    return {"mtime": mtime, "birth": birth}


def iter_live_jsonl() -> list[Path]:
    root = Path.home() / ".cursor" / "projects"
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.rglob("*.jsonl") if "agent-transcripts" in p.parts and p.is_file()
    )


def live_jsonl_meta(path: Path) -> dict[str, Any]:
    root = Path.home() / ".cursor" / "projects"
    rel = path.relative_to(root).as_posix()
    workspace = path.relative_to(root).parts[0]
    parent_id = None
    if "subagents" in path.parts:
        # .../agent-transcripts/<parent-uuid>/subagents/<child>.jsonl
        try:
            idx = path.parts.index("agent-transcripts")
            parent_id = path.parts[idx + 1]
        except (ValueError, IndexError):
            parent_id = None
    times = file_times(path)
    return {
        "key": f"raw/cursor-projects/{rel}",
        "source_path": str(path),
        "workspace": workspace,
        "conversation_id": path.stem,
        "parent_conversation_id": parent_id,
        "bytes": path.stat().st_size,
        "mtime": times["mtime"],
        "birth": times["birth"],
    }


def sync_raw(*, dry_run: bool = False) -> dict[str, Any]:
    files = iter_live_jsonl()
    stage = pending_root() / "raw-stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)
    manifest_files: list[dict[str, Any]] = []
    for path in files:
        meta = live_jsonl_meta(path)
        dest = stage / Path(meta["key"].removeprefix("raw/cursor-projects/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        manifest_files.append(meta)
    manifest = {
        "schema": "l9-chat-transcript-raw-manifest/v1",
        "uploaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "count": len(manifest_files),
        "files": manifest_files,
    }
    manifest_path = pending_root() / "raw-MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if dry_run:
        return {"ok": True, "dry_run": True, "count": len(manifest_files)}
    prefix = f"s3://{bucket_name()}/raw/cursor-projects/"
    proc = subprocess.run(
        [
            "aws",
            "s3",
            "sync",
            str(stage),
            prefix,
            "--region",
            _aws_region(),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "s3 sync failed").strip()[:300]
        return {"ok": False, "reason": err, "count": len(manifest_files)}
    man = subprocess.run(
        [
            "aws",
            "s3",
            "cp",
            str(manifest_path),
            f"s3://{bucket_name()}/raw/MANIFEST.json",
            "--content-type",
            "application/json",
            "--region",
            _aws_region(),
        ],
        capture_output=True,
        text=True,
        timeout=AWS_CALL_TIMEOUT,
        check=False,
    )
    if man.returncode != 0:
        err = (man.stderr or man.stdout or "manifest put failed").strip()[:300]
        return {"ok": False, "reason": err, "count": len(manifest_files)}
    return {"ok": True, "count": len(manifest_files), "prefix": prefix}


def backfill(*, dry_run: bool = False, upload: bool = True) -> dict[str, Any]:
    raw = sync_raw(dry_run=dry_run or not upload)
    reports: list[dict[str, Any]] = []
    receipts = pending_root() / "receipts"
    for jsonl in iter_live_jsonl():
        conversation_id = jsonl.stem
        if (receipts / f"{conversation_id}.json").is_file():
            continue
        workspace = ""
        if "projects" in jsonl.parts:
            workspace = jsonl.parts[jsonl.parts.index("projects") + 1]
        reports.append(
            archive_one(
                conversation_id=conversation_id,
                project_dir=workspace,
                transcript_path=str(jsonl),
                dry_run=True,
                upload=False,
            )
        )
    extracted = [r for r in reports if r.get("ok")]
    if dry_run or not upload:
        return {
            "ok": True,
            "archived": 0,
            "extracted": len(extracted),
            "raw": raw,
            "total": len(reports),
            "dry_run": True,
        }
    pending = pending_root() / "pending"
    if extracted:
        proc = subprocess.run(
            [
                "aws",
                "s3",
                "sync",
                str(pending),
                f"s3://{bucket_name()}/v1/",
                "--exclude",
                "*",
                "--include",
                "*.json",
                "--content-type",
                "application/json",
                "--region",
                _aws_region(),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "s3 sync failed").strip()[:300]
            return {"ok": False, "reason": err, "extracted": len(extracted), "raw": raw}
        for pending_file in pending.glob("*.json"):
            mark_done(pending_file, {"bucket": bucket_name(), "key": f"v1/{pending_file.name}"})
    return {
        "ok": bool(raw.get("ok")),
        "archived": len(extracted),
        "total": len(reports),
        "raw": raw,
    }


def _cmd_archive(args: argparse.Namespace) -> int:
    if args.backfill:
        result = backfill(dry_run=args.dry_run, upload=not args.dry_run)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    if not args.session_id:
        print(json.dumps({"ok": False, "reason": "session_id required"}))
        return 1
    result = archive_one(
        conversation_id=args.session_id,
        project_dir=args.project_dir or "",
        transcript_path=args.transcript_path,
        dry_run=args.dry_run,
        upload=not args.dry_run,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "turns"}, indent=2))
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive closed-chat words to S3")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--project-dir", default="")
    parser.add_argument("--transcript-path", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backfill", action="store_true")
    parser.set_defaults(func=_cmd_archive)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
