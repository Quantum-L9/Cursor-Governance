"""Transcript load + cap + PII redact for session close."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_GRAPHITI_DIR = Path(__file__).resolve().parent.parent
if str(_GRAPHITI_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPHITI_DIR))
from episode_contract import redact_pii  # noqa: E402

DEFAULT_TRANSCRIPT_CHARS = 12_000


def transcript_char_cap() -> int:
    raw = os.environ.get("MEMORY_CLOSE_TRANSCRIPT_CHARS", "").strip()
    if raw.isdigit():
        return max(500, int(raw))
    return DEFAULT_TRANSCRIPT_CHARS


def load_transcript_excerpt(
    *,
    transcript_path: str | None = None,
    conversation_id: str | None = None,
    max_chars: int | None = None,
) -> tuple[str, str]:
    """Return (excerpt, source_label). Empty excerpt if nothing found."""
    cap = max_chars if max_chars is not None else transcript_char_cap()
    path: Path | None = None
    source = "none"
    if transcript_path:
        candidate = Path(transcript_path).expanduser()
        if candidate.is_file():
            path = candidate
            source = "stdin_transcript_path"
    if path is None and conversation_id:
        path = _find_agent_transcript(conversation_id)
        if path is not None:
            source = "agent_transcripts_fallback"
    if path is None:
        return "", source
    raw = _read_transcript_text(path)
    cleaned = redact_pii(raw)
    if len(cleaned) > cap:
        cleaned = cleaned[-cap:]
    return cleaned, source


def _find_agent_transcript(conversation_id: str) -> Path | None:
    root = Path.home() / ".cursor" / "projects"
    if not root.is_dir():
        return None
    matches: list[Path] = []
    for projects in root.iterdir():
        transcripts = projects / "agent-transcripts"
        if not transcripts.is_dir():
            continue
        # Exact uuid.jsonl or uuid/uuid.jsonl layouts
        direct = transcripts / f"{conversation_id}.jsonl"
        if direct.is_file():
            matches.append(direct)
        nested = transcripts / conversation_id / f"{conversation_id}.jsonl"
        if nested.is_file():
            matches.append(nested)
        for path in transcripts.glob(f"*{conversation_id}*.jsonl"):
            if path.is_file():
                matches.append(path)
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def _read_transcript_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if path.suffix == ".jsonl":
        lines_out: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                lines_out.append(line[:500])
                continue
            role = obj.get("role") or obj.get("type") or ""
            content = obj.get("content") or obj.get("text") or obj.get("message") or ""
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(str(block.get("text") or block.get("content") or "")[:800])
                    else:
                        parts.append(str(block)[:800])
                content = " ".join(p for p in parts if p)
            elif not isinstance(content, str):
                content = str(content)[:800]
            # Skip huge tool dumps
            if len(content) > 2000:
                content = content[:2000] + "…"
            if content.strip():
                lines_out.append(f"{role}: {content.strip()}")
        return "\n".join(lines_out)
    return text
