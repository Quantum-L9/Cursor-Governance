#!/usr/bin/env python3
"""Transcript Distiller — batch text-to-memory pipeline for L9.

DEPRECATED for new writes (2026-06-06): ingest target is Graphiti VPS via
`ops/graphiti/graphiti_memory_client.py bootstrap`. This script remains for
offline C1 read/migration with --force-legacy-c1 only.

General-purpose offline pipeline that:
1. Reads text files (transcripts, ADRs, READMEs, GMP reports, etc.)
2. Chunks them via L9's ChunkView (content-addressed, deterministic)
3. Distills via LLM into structured facts + insights
4. Classifies each item: lesson | insight | pattern | error | note
5. Ingests into L9 memory via ingest_packet() — full DAG pipeline
   (facts → knowledge_facts, insights → packet_store, embeddings → semantic_memory)

Runs OFFLINE during downtime — not inside Cursor sessions.

Usage:
    # Distill all new agent transcripts
    python transcript_distiller.py --source transcripts

    # Distill ADRs
    python transcript_distiller.py --source adrs

    # Distill GMP reports
    python transcript_distiller.py --source reports

    # Distill a specific file
    python transcript_distiller.py --file /path/to/file.txt

    # Dry run (parse + chunk + classify, no LLM calls, no ingestion)
    python transcript_distiller.py --source transcripts --dry-run

    # Dry run with LLM distillation but no ingestion
    python transcript_distiller.py --source transcripts --dry-run --with-llm

Environment Variables:
    L9_DISTILLER_MODEL      LLM model for distillation (default: gpt-4o-mini)
    L9_DISTILLER_API_KEY    OpenAI API key (falls back to OPENAI_API_KEY)
    L9_DISTILLER_API_BASE   OpenAI-compatible base URL (optional)
    L9_API_URL              L9 API URL for ingestion (default: http://46.62.243.82)
    L9_DISTILLER_CHUNK_SIZE Chunk size in chars (default: 512)
    L9_DISTILLER_OVERLAP    Chunk overlap in chars (default: 64)

ADR: 0006 (PacketEnvelope), 0012 (DAG pipeline), 0014 (DORA), 0019 (structlog)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


# ---------------------------------------------------------------------------
# Load .env from L9 root if available
# ---------------------------------------------------------------------------
def _load_env_file():
    """Load variables from .env file in L9 root."""
    # Try to find L9 root
    l9_root = None
    for candidate in [
        Path.home() / "Projects" / "L9",
        Path.home() / "Projects" / "l9",
        Path.cwd(),
    ]:
        if (candidate / ".env").exists():
            l9_root = candidate
            break

    if l9_root:
        env_path = l9_root / ".env"
        try:
            content = env_path.read_text()
            env_vars = {}
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    if key:
                        env_vars[key] = value

            # Resolve ${VAR} references
            def resolve(val, seen=None):
                if seen is None:
                    seen = set()
                if val in seen:
                    return val
                seen.add(val)

                pattern = re.compile(r"\$\{([^}]+)\}")
                while True:
                    match = pattern.search(val)
                    if not match:
                        break
                    var_name = match.group(1)
                    var_val = env_vars.get(var_name, os.environ.get(var_name, ""))
                    val = val[: match.start()] + resolve(var_val, seen) + val[match.end() :]
                return val

            for key, value in env_vars.items():
                resolved_value = resolve(value)
                if not os.environ.get(key):
                    os.environ[key] = resolved_value
        except Exception:
            pass


_load_env_file()

# ---------------------------------------------------------------------------
# Ensure L9 project root is on sys.path so memory/ imports work
# ---------------------------------------------------------------------------
_L9_ROOT = os.environ.get("L9_PROJECT_ROOT", "")
if not _L9_ROOT:
    # Try common locations
    for candidate in [
        Path.home() / "Projects" / "L9",
        Path.home() / "Projects" / "l9",
        Path(__file__).resolve().parents[3],  # Dropbox/.../ops/scripts → L9
    ]:
        if (candidate / "memory" / "__init__.py").exists():
            _L9_ROOT = str(candidate)
            break

if _L9_ROOT and _L9_ROOT not in sys.path:
    sys.path.insert(0, _L9_ROOT)

# ---------------------------------------------------------------------------
# Configuration from environment (NO hardcoded values)
# ---------------------------------------------------------------------------
DISTILLER_MODEL = os.environ.get("L9_DISTILLER_MODEL", "gpt-4o-mini")
DISTILLER_API_KEY = os.environ.get("L9_DISTILLER_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
DISTILLER_API_BASE = os.environ.get("L9_DISTILLER_API_BASE", "")
L9_API_URL = os.environ.get("L9_API_URL", "http://46.62.243.82")
CHUNK_SIZE = int(os.environ.get("L9_DISTILLER_CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.environ.get("L9_DISTILLER_OVERLAP", "64"))

# Source directories (all relative to $HOME — NO hardcoded usernames)
HOME = Path.home()
TRANSCRIPT_DIRS = [
    HOME / ".cursor" / "projects",
]
ADR_DIR_RELATIVE = "readme/adr"
REPORTS_DIR_RELATIVE = "reports"
README_DIR_RELATIVE = "readme"

# State file for tracking processed files (content-hash based)
GLOBAL_COMMANDS = HOME / "Dropbox" / "Cursor Governance" / "GlobalCommands"
STATE_FILE = GLOBAL_COMMANDS / "ops" / "logs" / "distiller_state.json"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class DistilledItem:
    """A single distilled fact or insight ready for ingestion."""

    item_type: str  # "fact" or "insight"
    kind: str  # lesson | insight | pattern | error | note
    content: str
    confidence: float = 0.7
    source_file: str = ""
    source_type: str = ""  # transcript | adr | readme | report | generic
    chunk_id: str = ""
    tags: list[str] = field(default_factory=list)

    # Fact-specific fields (SPO triple for knowledge_facts)
    subject: str = ""
    predicate: str = ""
    object_value: str = ""


@dataclass
class DistillerResult:
    """Result of distilling a single file."""

    file_path: str
    content_hash: str
    chunks_count: int
    facts: list[DistilledItem] = field(default_factory=list)
    insights: list[DistilledItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


# ---------------------------------------------------------------------------
# State management (idempotent — skip already-processed files)
# ---------------------------------------------------------------------------


def _load_state() -> dict[str, Any]:
    """Load processed file hashes from state file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {"version": "1.0.0", "processed": {}}
    return {"version": "1.0.0", "processed": {}}


def _save_state(state: dict[str, Any]) -> None:
    """Save state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _content_hash(text: str) -> str:
    """SHA-256 content hash for dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def discover_transcripts(
    since: str | None = None,
    until: str | None = None,
) -> list[Path]:
    """Find agent transcript .txt files, optionally filtered by date range.

    Args:
        since: ISO date string (YYYY-MM-DD). Only include files modified
               on or after this date. None = no lower bound.
        until: ISO date string (YYYY-MM-DD). Only include files modified
               before this date (exclusive). None = no upper bound.
               Tip: --since 2026-02-13 --until 2026-02-14 = just Feb 13.
    """
    files: list[Path] = []
    since_ts: float | None = None
    until_ts: float | None = None

    if since:
        try:
            since_ts = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
        except ValueError:
            print(f"  ⚠️  Invalid --since date '{since}', ignoring filter")

    if until:
        try:
            until_ts = datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
        except ValueError:
            print(f"  ⚠️  Invalid --until date '{until}', ignoring filter")

    for base in TRANSCRIPT_DIRS:
        if not base.exists():
            continue
        # Pattern: ~/.cursor/projects/*/agent-transcripts/*.txt
        for transcript_dir in base.glob("*/agent-transcripts"):
            if transcript_dir.is_dir():
                for f in sorted(transcript_dir.glob("*.txt")):
                    mtime = f.stat().st_mtime
                    if since_ts is not None and mtime < since_ts:
                        continue
                    if until_ts is not None and mtime >= until_ts:
                        continue
                    files.append(f)
    return files


def discover_adrs(l9_root: Path) -> list[Path]:
    """Find all ADR markdown files."""
    adr_dir = l9_root / ADR_DIR_RELATIVE
    if not adr_dir.exists():
        return []
    return sorted(adr_dir.glob("*.md"))


def discover_reports(l9_root: Path) -> list[Path]:
    """Find all GMP report files."""
    reports_dir = l9_root / REPORTS_DIR_RELATIVE
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("GMP-Report-*.md"))


def discover_readmes(l9_root: Path) -> list[Path]:
    """Find all README files."""
    readme_dir = l9_root / README_DIR_RELATIVE
    if not readme_dir.exists():
        return []
    return sorted(readme_dir.glob("**/*.md"))


# ---------------------------------------------------------------------------
# Transcript parser
# ---------------------------------------------------------------------------


def parse_transcript(text: str) -> list[dict[str, str]]:
    """Parse a Cursor agent transcript into structured segments.

    Transcript format:
        user: message text
        assistant: response text
        [Tool call] toolName with arguments
        [Tool result] toolName
        [Thinking] reasoning text

    Returns list of segments with 'role' and 'content' keys.
    """
    segments: list[dict[str, str]] = []
    current_role = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        # Detect role transitions
        role_match = re.match(r"^(user|assistant|tool|system):\s*(.*)", line, re.IGNORECASE)
        bracket_match = re.match(
            r"^\[(Tool call|Tool result|Thinking|Image|File)\]\s*(.*)",
            line,
            re.IGNORECASE,
        )

        if role_match:
            # Flush previous segment
            if current_role and current_lines:
                segments.append(
                    {
                        "role": current_role,
                        "content": "\n".join(current_lines).strip(),
                    }
                )
            current_role = role_match.group(1).lower()
            current_lines = [role_match.group(2)] if role_match.group(2) else []

        elif bracket_match:
            # Flush previous segment
            if current_role and current_lines:
                segments.append(
                    {
                        "role": current_role,
                        "content": "\n".join(current_lines).strip(),
                    }
                )
            tag = bracket_match.group(1).lower().replace(" ", "_")
            current_role = tag
            current_lines = [bracket_match.group(2)] if bracket_match.group(2) else []

        else:
            current_lines.append(line)

    # Flush final segment
    if current_role and current_lines:
        segments.append(
            {
                "role": current_role,
                "content": "\n".join(current_lines).strip(),
            }
        )

    return segments


def extract_distillable_text(file_path: Path, source_type: str) -> str:
    """Extract text suitable for distillation from a file.

    For transcripts: extracts user + assistant messages (skips tool calls/results).
    For ADRs/READMEs/reports: returns full text.
    """
    text = file_path.read_text(errors="replace")

    if source_type == "transcript":
        segments = parse_transcript(text)
        # Keep user messages, assistant messages, and thinking blocks
        # Skip tool calls/results (too verbose, low signal)
        keep_roles = {"user", "assistant", "thinking"}
        filtered = [
            f"[{s['role'].upper()}] {s['content']}"
            for s in segments
            if s["role"] in keep_roles and len(s["content"]) > 20
        ]
        return "\n\n---\n\n".join(filtered)

    # ADRs, READMEs, reports — return full text
    return text


# ---------------------------------------------------------------------------
# Chunking (uses L9 ChunkView)
# ---------------------------------------------------------------------------


def chunk_text(text: str, source_id: str) -> list[dict[str, Any]]:
    """Chunk text using L9's ChunkView for content-addressed chunks."""
    try:
        from memory.chunk_view import Chunk, ChunkConfig, ChunkView

        config = ChunkConfig(
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
            min_length=32,
        )
        view = ChunkView(config=config)
        chunks = view.chunk_text(text, source_packet_id=source_id)
        return [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "offset": c.offset,
                "length": c.length,
            }
            for c in chunks
        ]
    except ImportError:
        # Fallback: simple fixed-size chunking if L9 not on path
        chunks = []
        for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk_text_slice = text[i : i + CHUNK_SIZE]
            if len(chunk_text_slice) < 32:
                continue
            cid = hashlib.sha256(f"{source_id}:{i}:{chunk_text_slice}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "chunk_id": cid,
                    "content": chunk_text_slice,
                    "offset": i,
                    "length": len(chunk_text_slice),
                }
            )
        return chunks


# ---------------------------------------------------------------------------
# LLM distillation
# ---------------------------------------------------------------------------


async def distill_chunks(
    chunks: list[dict[str, Any]],
    source_type: str,
    source_file: str,
) -> tuple[list[DistilledItem], list[DistilledItem]]:
    """Distill chunks into facts and insights using LLM.

    Uses L9's LLMMemoryOps.semantic_distill() if available,
    falls back to direct OpenAI API call.

    Returns (facts, insights).
    """
    all_facts: list[DistilledItem] = []
    all_insights: list[DistilledItem] = []

    # Build combined content (batch chunks to reduce API calls)
    batch_size = 5  # Process 5 chunks per LLM call
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        combined = "\n\n---\n\n".join(c["content"] for c in batch)
        chunk_ids = [c["chunk_id"] for c in batch]

        facts_raw, insights_raw = await _distill_single(combined, source_type)

        for fact_text in facts_raw:
            item = _classify_fact(fact_text, source_type, source_file, chunk_ids)
            all_facts.append(item)

        for insight_text in insights_raw:
            item = _classify_insight(insight_text, source_type, source_file, chunk_ids)
            all_insights.append(item)

    return all_facts, all_insights


async def _distill_single(content: str, source_type: str) -> tuple[list[str], list[str]]:
    """Run LLM distillation on a single content block.

    Returns (fact_strings, insight_strings).
    """
    # Build a source-type-aware prompt
    type_hint = {
        "transcript": "a Cursor AI agent conversation transcript",
        "adr": "an Architecture Decision Record (ADR)",
        "readme": "a README or documentation file",
        "report": "a GMP (Governance Managed Process) execution report",
        "generic": "a technical document",
    }.get(source_type, "a technical document")

    prompt = f"""Extract structured facts and insights from the following {type_hint}.

For FACTS, use subject-predicate-object format when possible:
FACT: <subject> | <predicate> | <object or value>

For INSIGHTS, classify each as one of: lesson, insight, pattern, error, note
INSIGHT [<kind>]: <analytical insight or lesson learned>

Content:
{content[:4000]}"""

    try:
        # Try L9's LLMMemoryOps first
        from memory.llm_memory_ops import LLMMemoryOps

        client = _get_llm_client()
        ops = LLMMemoryOps(llm_client=client)
        result = await ops.semantic_distill(content[:4000], max_tokens=1024)
        return result.facts, result.insights
    except ImportError:
        pass

    # Direct OpenAI API fallback
    return await _openai_distill(prompt)


async def _openai_distill(prompt: str) -> tuple[list[str], list[str]]:
    """Direct OpenAI API call for distillation."""
    try:
        import httpx

        headers = {
            "Authorization": f"Bearer {DISTILLER_API_KEY}",
            "Content-Type": "application/json",
        }
        base_url = DISTILLER_API_BASE or "https://api.openai.com/v1"
        payload = {
            "model": DISTILLER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]

        # Parse FACT: and INSIGHT: lines
        facts: list[str] = []
        insights: list[str] = []
        for line in raw.strip().splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("FACT:"):
                facts.append(stripped.split(":", 1)[1].strip())
            elif stripped.upper().startswith("INSIGHT"):
                # Handle "INSIGHT [kind]: text" or "INSIGHT: text"
                after_insight = stripped.split(":", 1)[1].strip() if ":" in stripped else stripped
                insights.append(after_insight)
        return facts, insights

    except Exception as e:
        print(f"  ⚠️  LLM distillation failed: {e}")
        return [], []


def _get_llm_client() -> Any:
    """Create an LLM client compatible with LLMMemoryOps.LLMClient protocol."""

    class OpenAILLMClient:
        """Async LLM client wrapping OpenAI chat completions."""

        async def complete(
            self,
            prompt: str,
            *,
            model: str = "",
            max_tokens: int = 1024,
            temperature: float = 0.1,
        ) -> str:
            import httpx

            use_model = model or DISTILLER_MODEL
            headers = {
                "Authorization": f"Bearer {DISTILLER_API_KEY}",
                "Content-Type": "application/json",
            }
            base_url = DISTILLER_API_BASE or "https://api.openai.com/v1"
            payload = {
                "model": use_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

    return OpenAILLMClient()


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_KIND_PATTERNS = {
    "lesson": re.compile(
        r"lesson|learned|mistake|never|always|rule|correction|wrong|fixed",
        re.IGNORECASE,
    ),
    "error": re.compile(
        r"error|bug|fail|crash|exception|broken|regression|issue",
        re.IGNORECASE,
    ),
    "pattern": re.compile(
        r"pattern|approach|technique|strategy|method|workflow|pipeline",
        re.IGNORECASE,
    ),
    "note": re.compile(
        r"note|todo|reminder|context|status|update",
        re.IGNORECASE,
    ),
}


def _classify_kind(text: str, default: str = "insight") -> str:
    """Classify text into lesson | insight | pattern | error | note."""
    # Check for explicit [kind] tag first
    tag_match = re.match(r"\[(\w+)\]\s*", text)
    if tag_match:
        tag = tag_match.group(1).lower()
        if tag in ("lesson", "insight", "pattern", "error", "note"):
            return tag

    # Heuristic classification
    scores: dict[str, int] = {}
    for kind, pattern in _KIND_PATTERNS.items():
        matches = pattern.findall(text)
        scores[kind] = len(matches)

    if scores:
        best = max(scores, key=lambda k: scores[k])
        if scores[best] > 0:
            return best

    return default


def _infer_tags(text: str, source_type: str) -> list[str]:
    """Infer tags from content and source type."""
    tags = [source_type]

    tag_keywords = {
        "memory": r"\bmemory\b",
        "governance": r"\bgovernance\b|\bpolicy\b|\bapproval\b",
        "agent": r"\bagent\b|\bexecutor\b",
        "kernel": r"\bkernel\b",
        "tool": r"\btool\b|\bregistry\b",
        "api": r"\bapi\b|\broute\b|\bendpoint\b",
        "database": r"\bdatabase\b|\bpostgres\b|\bneo4j\b|\bredis\b",
        "testing": r"\btest\b|\bpytest\b",
        "deployment": r"\bdeploy\b|\bdocker\b|\bvps\b",
        "dtb": r"\bdtb\b|\btensor\b|\banalogical\b|\bcausal\b",
    }

    for tag, pattern in tag_keywords.items():
        if re.search(pattern, text, re.IGNORECASE):
            tags.append(tag)

    return tags[:8]  # Cap at 8 tags


def _classify_fact(
    text: str, source_type: str, source_file: str, chunk_ids: list[str]
) -> DistilledItem:
    """Build a DistilledItem for a fact (SPO triple)."""
    # Try to parse "subject | predicate | object" format
    parts = [p.strip() for p in text.split("|")]
    if len(parts) >= 3:
        subject, predicate, object_value = parts[0], parts[1], " | ".join(parts[2:])
    else:
        # Fallback: entire text as object, generic subject/predicate
        subject = source_type
        predicate = "states"
        object_value = text

    return DistilledItem(
        item_type="fact",
        kind="note",  # Facts are always "note" kind
        content=text,
        confidence=0.75,
        source_file=source_file,
        source_type=source_type,
        chunk_id=chunk_ids[0] if chunk_ids else "",
        tags=_infer_tags(text, source_type),
        subject=subject,
        predicate=predicate,
        object_value=object_value,
    )


def _classify_insight(
    text: str, source_type: str, source_file: str, chunk_ids: list[str]
) -> DistilledItem:
    """Build a DistilledItem for an insight."""
    kind = _classify_kind(text)
    return DistilledItem(
        item_type="insight",
        kind=kind,
        content=text,
        confidence=0.7,
        source_file=source_file,
        source_type=source_type,
        chunk_id=chunk_ids[0] if chunk_ids else "",
        tags=_infer_tags(text, source_type),
    )


# ---------------------------------------------------------------------------
# Ingestion (writes to L9 memory via ingest_packet)
# ---------------------------------------------------------------------------


async def ingest_distilled(
    facts: list[DistilledItem],
    insights: list[DistilledItem],
    source_file: str,
    source_type: str,
) -> dict[str, int]:
    """Ingest distilled facts and insights into L9 memory.

    Facts → PacketEnvelopeIn with packet_type="distilled_fact"
            → DAG → knowledge_facts (SPO triples) + embedding
    Insights → PacketEnvelopeIn with packet_type="distilled_{kind}"
            → DAG → packet_store (native shape) + embedding

    Returns stats dict.
    """
    stats = {"facts_ingested": 0, "insights_ingested": 0, "errors": 0}

    # Use MCP API for ingestion (more robust for remote access)
    mcp_url = os.environ.get("C1_MEMORY_MCP_CALL_URL")
    if not mcp_url:
        host = os.environ.get("C1_HOST", "46.62.243.82")
        mcp_url = f"http://{host}/memory/mcp/call"

    api_key = os.environ.get("MCP_API_KEY_C") or os.environ.get("L9_EXECUTOR_API_KEY")

    if not api_key:
        print("  ❌ MCP_API_KEY_C not set. Cannot ingest via MCP.")
        stats["errors"] = len(facts) + len(insights)
        return stats

    import httpx

    async def mcp_save_memory(tool_name: str, arguments: dict):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {"tool_name": tool_name, "arguments": arguments}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(mcp_url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    # Ingest facts
    for fact in facts:
        try:
            args = {
                "content": fact.content,
                "kind": fact.kind,
                "scope": "cursor",
                "duration": "long",
                "user_id": "l9-shared",
                "tags": fact.tags + ["distilled_fact"],
                "importance": fact.confidence,
                "metadata": {
                    "project_id": "l9-default",
                    "subject": fact.subject,
                    "predicate": fact.predicate,
                    "object": fact.object_value,
                },
            }
            await mcp_save_memory("save_memory", args)
            stats["facts_ingested"] += 1
        except Exception as e:
            print(f"  ⚠️  Fact ingestion failed: {e}")
            stats["errors"] += 1

    # Ingest insights
    for insight in insights:
        try:
            args = {
                "content": insight.content,
                "kind": insight.kind,
                "scope": "cursor",
                "duration": "long",
                "user_id": "l9-shared",
                "tags": insight.tags + ["distilled_insight"],
                "importance": insight.confidence,
                "metadata": {
                    "project_id": "l9-default",
                },
            }
            await mcp_save_memory("save_memory", args)
            stats["insights_ingested"] += 1
        except Exception as e:
            print(f"  ⚠️  Insight ingestion failed: {e}")
            stats["errors"] += 1

    return stats


# ---------------------------------------------------------------------------
# Main distillation pipeline
# ---------------------------------------------------------------------------


async def distill_file(
    file_path: Path,
    source_type: str,
    *,
    dry_run: bool = False,
    with_llm: bool = False,
    state: dict[str, Any] | None = None,
) -> DistillerResult:
    """Distill a single file through the full pipeline.

    Args:
        file_path: Path to the file to distill.
        source_type: One of: transcript, adr, readme, report, generic.
        dry_run: If True, skip ingestion. If with_llm=False, also skip LLM.
        with_llm: If True during dry_run, still run LLM distillation.
        state: State dict for dedup tracking.

    Returns:
        DistillerResult with facts, insights, and stats.
    """
    result = DistillerResult(
        file_path=str(file_path),
        content_hash="",
        chunks_count=0,
    )

    # 1. Read and extract distillable text
    try:
        text = extract_distillable_text(file_path, source_type)
    except Exception as e:
        result.errors.append(f"Read failed: {e}")
        return result

    if not text or len(text) < 50:
        result.skipped = True
        result.skip_reason = "Too short (< 50 chars)"
        return result

    # 2. Content hash for dedup
    content_hash = _content_hash(text)
    result.content_hash = content_hash

    if state and content_hash in state.get("processed", {}):
        result.skipped = True
        result.skip_reason = "Already processed (content hash match)"
        return result

    # 3. Chunk
    source_id = str(uuid4())
    chunks = chunk_text(text, source_id)
    result.chunks_count = len(chunks)

    if not chunks:
        result.skipped = True
        result.skip_reason = "No chunks produced"
        return result

    print(f"  📦 {len(chunks)} chunks ({len(text):,} chars)")

    # 4. Distill via LLM
    if dry_run and not with_llm:
        # Dry run without LLM — show chunk stats only
        print(f"  🔍 [DRY RUN] Would distill {len(chunks)} chunks with {DISTILLER_MODEL}")
        return result

    facts, insights = await distill_chunks(chunks, source_type, str(file_path))
    result.facts = facts
    result.insights = insights

    print(f"  📊 Distilled: {len(facts)} facts, {len(insights)} insights")

    if dry_run:
        # Show what would be ingested
        for f in facts[:3]:
            print(f"    FACT: {f.subject} | {f.predicate} | {f.object_value[:60]}")
        for ins in insights[:3]:
            print(f"    INSIGHT [{ins.kind}]: {ins.content[:80]}")
        if len(facts) > 3 or len(insights) > 3:
            print(f"    ... and {len(facts) + len(insights) - 6} more")
        return result

    # 5. Ingest into L9 memory
    stats = await ingest_distilled(facts, insights, str(file_path), source_type)
    print(
        f"  ✅ Ingested: {stats['facts_ingested']} facts, " f"{stats['insights_ingested']} insights"
    )
    if stats["errors"]:
        print(f"  ⚠️  {stats['errors']} ingestion errors")
        result.errors.append(f"{stats['errors']} ingestion errors")

    # 6. Update state
    if state is not None:
        state.setdefault("processed", {})[content_hash] = {
            "file": str(file_path),
            "source_type": source_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "facts": len(facts),
            "insights": len(insights),
        }

    return result


async def run_pipeline(
    source: str,
    *,
    file_path: str | None = None,
    since: str | None = None,
    until: str | None = None,
    dry_run: bool = False,
    with_llm: bool = False,
    l9_root: str = "",
) -> None:
    """Run the full distillation pipeline for a source type."""
    l9_path = Path(l9_root) if l9_root else Path(_L9_ROOT) if _L9_ROOT else Path.cwd()
    run_start = datetime.now(UTC)

    # Discover files
    if file_path:
        files = [Path(file_path)]
        source_type = source if source != "auto" else "generic"
    elif source == "transcripts":
        files = discover_transcripts(since=since, until=until)
        source_type = "transcript"
    elif source == "adrs":
        files = discover_adrs(l9_path)
        source_type = "adr"
    elif source == "reports":
        files = discover_reports(l9_path)
        source_type = "report"
    elif source == "readmes":
        files = discover_readmes(l9_path)
        source_type = "readme"
    else:
        print(f"❌ Unknown source: {source}")
        print("   Valid sources: transcripts, adrs, reports, readmes")
        return

    if not files:
        print(f"📭 No files found for source '{source}'" + (f" since {since}" if since else ""))
        return

    print(f"{'=' * 60}")
    print("L9 TRANSCRIPT DISTILLER")
    print(f"{'=' * 60}")
    print(f"Source:    {source}")
    date_range = since or "all"
    if until:
        date_range = f"{since or 'start'} → {until}"
    print(f"Since:     {date_range}")
    print(f"Files:     {len(files)}")
    print(f"Model:     {DISTILLER_MODEL}")
    print(f"Chunk:     {CHUNK_SIZE} chars / {CHUNK_OVERLAP} overlap")
    print(f"Dry run:   {dry_run}")
    print(f"With LLM:  {with_llm}")
    print(f"L9 root:   {l9_path}")
    print(f"{'=' * 60}")

    state = _load_state()
    totals = {
        "processed": 0,
        "skipped": 0,
        "facts": 0,
        "insights": 0,
        "errors": 0,
    }
    file_results: list[dict[str, Any]] = []

    for i, fp in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {fp.name}")
        result = await distill_file(
            fp, source_type, dry_run=dry_run, with_llm=with_llm, state=state
        )

        if result.skipped:
            print(f"  ⏭️  Skipped: {result.skip_reason}")
            totals["skipped"] += 1
        else:
            totals["processed"] += 1
            totals["facts"] += len(result.facts)
            totals["insights"] += len(result.insights)
            totals["errors"] += len(result.errors)

        file_results.append(
            {
                "file": fp.name,
                "path": str(fp),
                "skipped": result.skipped,
                "skip_reason": result.skip_reason,
                "chunks": result.chunks_count,
                "facts": len(result.facts),
                "insights": len(result.insights),
                "errors": result.errors,
                "content_hash": result.content_hash,
            }
        )

    # Save state (even for dry runs — tracks what was seen)
    if not dry_run:
        _save_state(state)

    run_end = datetime.now(UTC)
    elapsed = (run_end - run_start).total_seconds()

    print(f"\n{'=' * 60}")
    print("DISTILLER RESULTS")
    print(f"{'=' * 60}")
    print(f"Processed: {totals['processed']}")
    print(f"Skipped:   {totals['skipped']}")
    print(f"Facts:     {totals['facts']}")
    print(f"Insights:  {totals['insights']}")
    print(f"Errors:    {totals['errors']}")
    print(f"Duration:  {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print(f"{'=' * 60}")

    # -----------------------------------------------------------------------
    # Write completion report (JSON + human-readable)
    # -----------------------------------------------------------------------
    report = {
        "run_id": str(uuid4())[:8],
        "started_at": run_start.isoformat(),
        "finished_at": run_end.isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "source": source,
        "since": since,
        "until": until,
        "model": DISTILLER_MODEL,
        "dry_run": dry_run,
        "totals": totals,
        "files": file_results,
    }

    report_dir = GLOBAL_COMMANDS / "ops" / "logs" / "distiller_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"distiller-{run_start.strftime('%Y-%m-%d_%H-%M')}.json"
    report_file.write_text(json.dumps(report, indent=2))
    print(f"\n📄 Report: {report_file}")

    # Also write a human-readable summary
    summary_file = report_dir / f"distiller-{run_start.strftime('%Y-%m-%d_%H-%M')}.txt"
    summary_lines = [
        f"L9 DISTILLER RUN — {run_start.strftime('%Y-%m-%d %H:%M UTC')}",
        f"{'=' * 50}",
        f"Source:     {source} (range: {date_range})",
        f"Model:      {DISTILLER_MODEL}",
        f"Duration:   {elapsed:.0f}s ({elapsed / 60:.1f} min)",
        f"Dry run:    {dry_run}",
        "",
        "TOTALS:",
        f"  Processed: {totals['processed']} files",
        f"  Skipped:   {totals['skipped']} files",
        f"  Facts:     {totals['facts']} (→ knowledge_facts table)",
        f"  Insights:  {totals['insights']} (→ packet_store table)",
        f"  Errors:    {totals['errors']}",
        "",
        "FILES PROCESSED:",
    ]
    for fr in file_results:
        status = "SKIP" if fr["skipped"] else "OK"
        detail = fr["skip_reason"] if fr["skipped"] else f"{fr['facts']}F {fr['insights']}I"
        summary_lines.append(f"  [{status}] {fr['file']}: {detail}")

    summary_file.write_text("\n".join(summary_lines) + "\n")
    print(f"📋 Summary: {summary_file}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="L9 Transcript Distiller — batch text-to-memory pipeline"
    )
    parser.add_argument(
        "--source",
        choices=["transcripts", "adrs", "reports", "readmes", "auto"],
        default="transcripts",
        help="Source type to distill (default: transcripts)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Distill a specific file (overrides --source for discovery)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only process files modified on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--until",
        type=str,
        default=None,
        help="Only process files modified before this date, exclusive (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk only — no LLM calls or ingestion",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="During dry-run, still run LLM distillation (but skip ingestion)",
    )
    parser.add_argument(
        "--l9-root",
        type=str,
        default="",
        help="L9 project root (default: auto-detect)",
    )

    args = parser.parse_args()

    asyncio.run(
        run_pipeline(
            source=args.source,
            file_path=args.file,
            since=args.since,
            until=args.until,
            dry_run=args.dry_run,
            with_llm=args.with_llm,
            l9_root=args.l9_root,
        )
    )


if __name__ == "__main__":
    main()
