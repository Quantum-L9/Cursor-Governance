#!/usr/bin/env python3
"""Fail if active surfaces teach retired doctrine.

Three ratchets, one script:

1. **Side doors (2026-08).** Active surfaces must not teach the retired Dropbox
   SSOT, the ``L9_MEMORY_HTTP`` side door, or a live invocation of the retired
   ``agents/cursor/cursor_memory_client.py``.
2. **Memory doctrine (2026-09-07, PR #509 doctrine closure; ADR-0030 items
   7-9, CANONICAL_LAW 8.3; amended 2026-09-15 by ADR-0033).** Surfaces
   converged on the canonical memory control plane must not regress to the
   retired direct-Graphiti architecture: the deleted
   ``ops/graphiti/graphiti_memory_client.py`` taught as a live front door,
   provider URL / bearer possession, Graphiti ``inject`` / PICKUP taught as
   the current resume SSOT, or generic ingest / the operator CLI ``write``
   taught as the model's ordinary write. Converged surfaces must also *carry*
   the agent write contract (positive presence) — ``memory.write_agent`` is
   the ordinary agent write; ``memory.phase_lock`` + ``memory.write_governed``
   is an *allowed optional* conflict-sensitive pair, no longer required — so a
   rewrite cannot drop the contract silently.
3. **Two lanes (2026-09-15, ADR-0033, INV-03b).** No memory persistence or
   cognition bypasses ``MemoryService``. Agent adapters may invoke public
   ``MemoryService`` operations directly. Automatic hooks may only invoke
   their bounded operations. Cursor-Governance may not interpose an
   authorization wall on agent-initiated memory writes. Two finding classes:

   * ``local-memory-cognition`` — production code on a memory path
     (``ops/graphiti``, ``ops/hooks``, ``ops/memory``,
     ``environment/agents/adapters``) holds a provider / LLM client import or
     model id, ``promotion_rules``, ``MEMORY_PHASE_B``, the retired local
     ``MEMORY_DISTILL*`` knobs, ``boto3`` / S3, or ``graphiti_memory_client``.
   * ``agent-lane-interposition`` — doctrine that makes an ordinary agent
     write wait on a phase lock, receipt, session close or PR gate; or a
     pre-execution hook matcher / gate tool-list that names a memory MCP
     tool (``mcp__l9-graphite-memory__*``) or an ``l9-memory`` /
     ``ops.memory.cli`` shell invocation for denial.

Surface classes for ratchet 2 (and the doctrine half of ratchet 3):

* ``FAIL``  - converged surfaces (rules 03/87/97/98 and their generated
  projections, the memory skills, the active memory docs). A hit fails.
* ``AMENDED`` - ADRs and the append-only root authority files. Historical
  text is permitted only when the file carries a dated supersession /
  amendment heading that names ADR-0030 or the memory control plane;
  without that marker a hit fails.
* ``WARN`` - the rest of the active corpus, not yet converged by a locked
  run. A hit is reported (``WARN pending convergence``) and does not fail
  unless ``--strict-memory-doctrine`` is passed. The knob only tightens: a
  surface moves from WARN to FAIL when its convergence lands, never back.

HistoricalEvidence (reports, archives, WIP, tests) is out of scope. A mention
that explicitly marks residue as forbidden / retired / historical / superseded
is allowed on every class.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ACTIVE_ROOTS = (
    "rules",
    "skills",
    "commands",
    "ops/scripts",
    "environment/agents/adapters",
    "environment/agents/tools",
    "environment/generated/llm-rules",
    "environment/agents/adapters/claude-code",
    "learning/failures",
)

# Root / top-level active contracts not covered by ACTIVE_ROOTS directories.
ACTIVE_FILES = (
    ".mcp.json",
    ".env.example",
    "end-session.yaml",
)

# Governance authority + session-protocol surfaces that must never carry a
# LIVE instruction to the retired memory client. Scoped deliberately: the
# execution engine (workflows/) and rules corpus migrate under a separate
# memory-front-door plan; this gate protects the authority/protocol class.
AUTHORITY_PROTOCOL_SURFACES = (
    "end-session.yaml",
    "AGENTS.md",
    "CANONICAL_LAW.md",
    "README.md",
    "CONTRIBUTING.md",
    ".github/pull_request_template.md",
)

# Retired session-memory client. The canonical memory control plane
# (ops/memory; operator CLI `python -m ops.memory.cli`) is the single front door.
RETIRED_MEMORY_CLIENT = re.compile(r"agents/cursor/cursor_memory_client\.py")

# A mention that teaches the client is gone (a retirement notice) is allowed;
# only a live invocation on an authority surface is a violation.
RETIRED_CLIENT_ALLOW = re.compile(
    r"(?i)("
    r"deprecated|retired|replaced by|superseded|no longer|historical|"
    r"do not use|don't use|use graphiti|instead of|forbidden|removed"
    r")"
)

SKIP_DIR_PARTS = {
    "_archived",
    "archived",
    "reports",
    "WIP",
    "__pycache__",
    ".git",
    "tests",
}

SKIP_NAME_SUFFIXES = (
    "test_graphiti_front_door.py",
    "validate_legacy_doctrine_residue.py",
    "validate_claude_env.py",
    "memory-enforcement.contract.json",
    "memory-enforcement.schema.json",
)

# Path / name teaching Dropbox as live SSOT or fallback.
DROPBOX_LIVE = re.compile(
    r"(?i)("
    r"Dropbox/Cursor Governance|"
    r"Dropbox/cursor governance|"
    r"Dropbox governance SSOT|"
    r"against the Dropbox|"
    r"legacy Dropbox is fallback|"
    r"Use Dropbox GlobalCommands as single source of truth|"
    r"points at Dropbox|"
    r"→ Dropbox|"
    r"under \$HOME/Dropbox"
    r")"
)

# Live HTTP side-door assignments / MCP server registration (not forbid lists).
HTTP_LIVE = re.compile(
    r"(?i)("
    r"L9_MEMORY_HTTP_URL\s*=|"
    r"L9_MEMORY_CLIENT_TOKEN\s*=|"
    r"L9_MEMORY_HTTP_TOKEN\s*=|"
    r'["\']l9-shared-memory["\']\s*:|'
    r"\[mcp_servers\.l9-shared-memory\]|"
    r'"name"\s*:\s*"l9-shared-memory"|'
    r"claude mcp add-json[^\n]*l9-shared-memory"
    r")"
)

ALLOW_LINE = re.compile(
    r"(?i)("
    r"forbidden|"
    r"retired|"
    r"historical|"
    r"not a fallback|"
    r"must not|"
    r"do \*\*not\*\*|"
    r"do not use|"
    r"do not probe|"
    r"\*\*Wrong:\*\*|"
    r"^Wrong:|"
    r"assertNotIn|"
    r"FORBIDDEN|"
    r"banned|"
    r"ADR-0006|"
    r"side door|"
    r"side-door|"
    r"no longer|"
    r"was retired|"
    r"Dropbox is not|"
    r"Dropbox governance fallback is retired|"
    r"never Dropbox|"
    r"must not be probed"
    r")"
)

TEXT_SUFFIXES = {
    ".md",
    ".mdc",
    ".py",
    ".sh",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".example",
    ".txt",
}

# --------------------------------------------------------------------------- #
# Memory doctrine ratchet (2026-09-07)
# --------------------------------------------------------------------------- #

#: Converged surfaces: a stale teaching here FAILS.
MEMORY_DOCTRINE_FAIL_SURFACES: tuple[str, ...] = (
    "rules/03-graphiti-memory.mdc",
    "rules/87-cursor-memory-kernel.mdc",
    "rules/97-graph-layer-boundary.mdc",
    "rules/98-graphiti-memory-gate.mdc",
    "environment/generated/llm-rules/03-graphiti-memory.md",
    "environment/generated/llm-rules/87-cursor-memory-kernel.md",
    "environment/generated/llm-rules/97-graph-layer-boundary.md",
    "environment/generated/llm-rules/98-graphiti-memory-gate.md",
    "skills/l9-graphiti-memory/SKILL.md",
    "skills/l9-end-session/SKILL.md",
    "skills/l9-end-session/references/end-session-protocol.md",
    "skills/l9-chat-extraction/SKILL.md",
    "skills/l9-chat-extraction/references/extract-chat.md",
    "skills/l9-gmp-protocol/SKILL.md",
    "skills/l9-gmp-protocol/references/phase-contracts.md",
    "docs/MEMORY_PIPELINE_MAP.md",
    "environment/agents/docs/MEMORY_TOPOLOGY.md",
    "ops/memory/README.md",
)

#: Append-only root authority files: historical text needs a dated
#: supersession / amendment marker (see MEMORY_DOCTRINE_MARKER).
MEMORY_DOCTRINE_AMENDED_ROOTS: tuple[str, ...] = ("CANONICAL_LAW.md", "AGENTS.md")
MEMORY_DOCTRINE_ADR_GLOB = "docs/decisions/ADR-*.md"

#: The ordinary agent write (ADR-0033). Every converged write-teaching surface
#: must carry it. ``memory.phase_lock`` + ``memory.write_governed`` remain an
#: allowed optional pair and are deliberately NOT required any more.
AGENT_WRITE_TOKEN = "memory.write_agent"

#: Positive presence: a converged surface must still CARRY the contract.
MEMORY_DOCTRINE_REQUIRED_TOKENS: dict[str, tuple[str, ...]] = {
    "rules/03-graphiti-memory.mdc": (AGENT_WRITE_TOKEN,),
    "rules/87-cursor-memory-kernel.mdc": (AGENT_WRITE_TOKEN,),
    "rules/97-graph-layer-boundary.mdc": (AGENT_WRITE_TOKEN, "ContinuationCapsuleV2"),
    "rules/98-graphiti-memory-gate.mdc": (AGENT_WRITE_TOKEN,),
    "environment/generated/llm-rules/03-graphiti-memory.md": (AGENT_WRITE_TOKEN,),
    "environment/generated/llm-rules/87-cursor-memory-kernel.md": (AGENT_WRITE_TOKEN,),
    "environment/generated/llm-rules/97-graph-layer-boundary.md": (
        AGENT_WRITE_TOKEN,
        "ContinuationCapsuleV2",
    ),
    "environment/generated/llm-rules/98-graphiti-memory-gate.md": (AGENT_WRITE_TOKEN,),
    "skills/l9-graphiti-memory/SKILL.md": (AGENT_WRITE_TOKEN,),
    "skills/l9-end-session/SKILL.md": (AGENT_WRITE_TOKEN, "repair-write"),
    "skills/l9-end-session/references/end-session-protocol.md": (
        AGENT_WRITE_TOKEN,
        "repair-write",
    ),
    "skills/l9-chat-extraction/SKILL.md": (AGENT_WRITE_TOKEN,),
    "skills/l9-chat-extraction/references/extract-chat.md": (AGENT_WRITE_TOKEN,),
    "skills/l9-gmp-protocol/SKILL.md": ("snapshot_digest",),
    "skills/l9-gmp-protocol/references/phase-contracts.md": ("snapshot_digest",),
    "docs/MEMORY_PIPELINE_MAP.md": (AGENT_WRITE_TOKEN,),
    "environment/agents/docs/MEMORY_TOPOLOGY.md": (AGENT_WRITE_TOKEN,),
    "ops/memory/README.md": (AGENT_WRITE_TOKEN,),
}

#: Positive absence: stale semantics a converged surface must not re-teach.
MEMORY_DOCTRINE_FORBIDDEN_TOKENS: dict[str, tuple[str, ...]] = {
    "skills/l9-gmp-protocol/SKILL.md": ("<episode names>",),
    "skills/l9-gmp-protocol/references/phase-contracts.md": ("<episode names>",),
}

# The provider variable names are assembled from parts so this validator is
# not itself an egress-scanner hit (ops/scripts/validate_memory_egress_boundary.py).
_PROVIDER_VAR = "GRAPHITI_MCP_" + "(?:URL|TOKEN)"

#: Finding classes. Each regex is line-level; paragraph context decides allow.
MEMORY_DOCTRINE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "retired-client-live",
        re.compile(
            r"graphiti_memory_client\.py\s+"
            r"(?:health|search|inject|write|bootstrap|conflicts|resolve|hydrate|prune)\b"
        ),
    ),
    (
        "provider-possession",
        re.compile(
            r"(?:^|[\s\"'`(])(?:export\s+)?" + _PROVIDER_VAR + r"\s*=|"
            r"\$\{" + _PROVIDER_VAR + r"\}|"
            r"(?i:set|sets|export|exports|hold|holds)\s+`?" + _PROVIDER_VAR + r"`?"
        ),
    ),
    (
        "graphiti-inject-pickup-resume-ssot",
        re.compile(
            r"(?i:resume\s+SSOT\s+is\s+\*{0,2}Graphiti)|"
            r"Graphiti\s+`?inject`?\s*/\s*`?PICKUP`?|"
            r"Graphiti\s+`?PICKUP`?\s*/\s*`?inject`?|"
            r"(?i:Graphiti\s+`?inject`?\s*\+\s*(?:search\s+)?PICKUP)|"
            r"(?i:resume\s+from\s+Graphiti\s+`?inject`?)"
        ),
    ),
    (
        "generic-write-as-model-write",
        re.compile(
            r"(?:memcli|ops\.memory\.cli|memory\.cli|-m ops\.memory\.cli)\s+write\b[^\n]*"
            r"\"(?:LESSON|PATTERN|ERROR|INSIGHT|PICKUP)[:|]|"
            r"(?:memcli|ops\.memory\.cli|memory\.cli)\s+write\b[^\n]*--kind\s+pickup_context|"
            r"(?<![\w.])memory\.ingest\b"
        ),
    ),
)

#: Allowances specific to ratchet 2, checked on the line and its paragraph.
MEMORY_DOCTRINE_ALLOW = re.compile(
    r"(?i)("
    r"tombstone|superseded|supersedes|supersession|amendment|"
    r"operator form|operator / adapter|operator/adapter|deterministic adapter|"
    r"not the model|write_governed|legacy operator infrastructure|"
    r"never a|is not a resume|not a resume|is gone|are gone|"
    r"retirement notice|residue|not this step|not an? live|"
    r"forbidden|retired|historical|must not|do not|never|no longer"
    r")"
)

#: A dated supersession / amendment heading that names the memory control
#: plane or ADR-0030 licenses historical text in an AMENDED-class file.
_DATED_HEADING = re.compile(r"^##+ .*\(20\d\d-\d\d-\d\d\)")

#: The write contract is only meaningful where a memory runtime is bound. A
#: tree without the binding manifest (a fixture, a consumer checkout) is not
#: required to carry the converged surfaces; one that has it must.
MEMORY_BINDING_MANIFEST = "ops/config/memory-binding.json"

# --------------------------------------------------------------------------- #
# Two-lane ratchet (2026-09-15, ADR-0033 / INV-03b)
# --------------------------------------------------------------------------- #

#: Production code on a memory path may hold no memory cognition of its own.
LOCAL_COGNITION_ROOTS: tuple[str, ...] = (
    "ops/graphiti",
    "ops/hooks",
    "ops/memory",
    "environment/agents/adapters",
)
LOCAL_COGNITION_SUFFIXES = frozenset({".py", ".sh"})

#: Adjacent, explicitly out of scope (ADR-0033 "Consequences"): the S3 chat
#: transcript archive is not memory and keeps its S3 client.
LOCAL_COGNITION_ALLOW_PATHS: tuple[str, ...] = ("ops/graphiti/hydration/archive_transcript.py",)

LOCAL_COGNITION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "provider-client-import",
        re.compile(
            r"^\s*(?:from|import)\s+"
            r"(?:openai|anthropic|langchain\w*|litellm|google\.generativeai|vertexai|"
            r"cohere|mistralai|together|groq)\b"
        ),
    ),
    (
        "provider-model-id",
        re.compile(
            r"(?<![\w-])(?:gpt-[3-5][\w.-]*|o[134]-(?:mini|preview)|"
            r"claude-(?:3|4|opus|sonnet|haiku)[\w.-]*|text-embedding-[\w-]+)(?![\w-])"
        ),
    ),
    ("promotion-rules", re.compile(r"promotion_rules")),
    ("phase-b-knob", re.compile(r"\bMEMORY_PHASE_B\b")),
    # The retired local knobs; the canonical kill switch is L9_MEMORY_DISTILL.
    ("local-distill-knob", re.compile(r"(?<![A-Z0-9_])MEMORY_DISTILL(?:_[A-Z0-9_]+)?\b")),
    ("s3-on-memory-path", re.compile(r"\bboto3\b|\baws\s+s3api\b|\bs3://")),
    ("retired-client", re.compile(r"graphiti_memory_client")),
)

#: Doctrine that turns the agent lane into a ceremony. Checked on the same
#: surfaces as ratchet 2; allowed only when the line / paragraph marks it as
#: superseded, optional, or forbidden.
AGENT_LANE_INTERPOSITION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "only-model-write",
        re.compile(r"(?i)\b(?:is|as)\s+the\s+only\s+(?:model|agent)\s+write\b"),
    ),
    (
        "ceremony-before-write",
        re.compile(
            r"(?i)\bagents?\s+(?:must|shall|need to|have to)\s+"
            r"(?:phase[- _]?lock|obtain\s+an?\s+(?:governance\s+)?receipt|"
            r"close\s+(?:the|a)\s+session|pass\s+(?:the\s+)?(?:PR|publish)\s+gate|"
            r"wait\s+for\s+(?:a\s+)?(?:phase|receipt|close|PR))\b[^\n]*\bbefore\b"
            r"[^\n]*\b(?:write|writing)\b"
        ),
    ),
    (
        "write-agent-gated",
        re.compile(
            r"(?i)\b(?:write_agent|l9-memory write)\b[^\n.]*\b(?:requires?|denied|blocked|"
            r"waits?\s+(?:for|on))\b[^\n.]*\b(?:phase[- _]?lock|receipt|session close|PR gate|"
            r"make pr)\b"
        ),
    ),
)

AGENT_LANE_INTERPOSITION_ALLOW = re.compile(
    r"(?i)("
    r"supersed|historical|retired|no longer|not the only|optional|never|"
    r"must not|do not|forbidden|residue|amendment|ADR-0033|two lanes|two-lane"
    r")"
)

#: The public agent-lane MCP surface. No pre-execution matcher may cover it.
MEMORY_MCP_PREFIX = "mcp__l9-graphite-memory__"
MEMORY_MCP_PROBES: tuple[str, ...] = tuple(
    f"{MEMORY_MCP_PREFIX}{name}"
    for name in ("write_agent", "write_governed", "search", "hydrate", "get", "phase_lock")
)
#: Shell forms of the agent lane. No gate command pattern may match them.
MEMORY_SHELL_PROBES: tuple[str, ...] = (
    'l9-memory write "fact" --kind insight',
    "l9-memory search q",
    "l9-memory hydrate --task t",
    "python -m ops.memory.cli write 'fact' --kind lesson",
)
CLAUDE_SETTINGS_TEMPLATE = "environment/agents/adapters/claude-code/settings.template.json"
CURSOR_HOOKS_TEMPLATE = "ops/hooks/hooks.json.template"
MEMORY_ENFORCEMENT_CONTRACT = (
    "environment/agents/adapters/claude-code/memory/memory-enforcement.contract.json"
)


def _skip_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIR_PARTS:
        return True
    if path.name in SKIP_NAME_SUFFIXES:
        return True
    if path.suffix not in TEXT_SUFFIXES and path.name != "environment.env.example":
        # allow *.env.example via suffix .example already
        if not path.name.endswith(".env.example"):
            return True
    return False


def _iter_active_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for rel in ACTIVE_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        if base.is_file():
            out.append(base)
            continue
        for path in base.rglob("*"):
            if path.is_file() and not _skip_path(path.relative_to(root)):
                out.append(path)
    # agent_registry + analysis notes + root active contracts
    for extra in (
        *(root / rel for rel in ACTIVE_FILES),
        root / "environment/agents/agent_registry.yaml",
        root / "environment/agents/analysis_notes.md",
        root / "environment/agents/HANDOFF.md",
        root / "environment/agents/README.md",
        root / "environment/agents/adapters/ADAPTER_CONTRACT.md",
    ):
        if extra.is_file():
            out.append(extra)
    return sorted(set(out))


def _scan_retired_client(rel: str, text: str, sink: set[str]) -> None:
    """Record any LIVE retired-client invocation (retirement notices exempt)."""
    for i, line in enumerate(text.splitlines(), 1):
        if not RETIRED_MEMORY_CLIENT.search(line):
            continue
        if ALLOW_LINE.search(line) or RETIRED_CLIENT_ALLOW.search(line):
            continue
        sink.add(f"{rel}:{i}: {line.strip()[:160]}")


# --------------------------------------------------------------------------- #
# Memory doctrine ratchet helpers
# --------------------------------------------------------------------------- #


def _paragraph(lines: list[str], index: int) -> str:
    """The contiguous non-blank block around ``lines[index]`` (0-based)."""
    start = index
    while start > 0 and lines[start - 1].strip():
        start -= 1
    end = index
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    return "\n".join(lines[start : end + 1])


def memory_doctrine_hits(text: str) -> list[tuple[int, str, str]]:
    """Return ``(line_no, finding_class, line)`` for every unallowed stale teaching."""
    lines = text.splitlines()
    hits: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        for finding, pattern in MEMORY_DOCTRINE_PATTERNS:
            if not pattern.search(line):
                continue
            if ALLOW_LINE.search(line) or MEMORY_DOCTRINE_ALLOW.search(line):
                continue
            if MEMORY_DOCTRINE_ALLOW.search(_paragraph(lines, index)):
                continue
            hits.append((index + 1, finding, line.strip()[:160]))
    return hits


def has_supersession_marker(text: str) -> bool:
    """A dated ``##`` heading that names ADR-0030 / ADR-0033, the memory
    control plane, or the two-lane model."""
    for line in text.splitlines():
        if not _DATED_HEADING.match(line):
            continue
        lowered = line.lower()
        if any(
            token in lowered
            for token in ("adr-0030", "adr-0033", "memory control plane", "two lanes", "two-lane")
        ):
            return True
    return False


# --------------------------------------------------------------------------- #
# Two-lane ratchet helpers
# --------------------------------------------------------------------------- #


def _memory_code_paths(root: Path) -> list[Path]:
    out: list[Path] = []
    for rel in LOCAL_COGNITION_ROOTS:
        base = root / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in LOCAL_COGNITION_SUFFIXES:
                continue
            relative = path.relative_to(root)
            if set(relative.parts) & SKIP_DIR_PARTS or relative.name.startswith("test_"):
                continue
            if relative.as_posix() in LOCAL_COGNITION_ALLOW_PATHS:
                continue
            out.append(path)
    return sorted(set(out))


def local_cognition_hits(text: str) -> list[tuple[int, str, str]]:
    """``(line_no, finding_class, line)`` for local memory cognition in code."""
    lines = text.splitlines()
    hits: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        for finding, pattern in LOCAL_COGNITION_PATTERNS:
            if not pattern.search(line):
                continue
            if ALLOW_LINE.search(line) or MEMORY_DOCTRINE_ALLOW.search(line):
                continue
            if MEMORY_DOCTRINE_ALLOW.search(_paragraph(lines, index)):
                continue
            hits.append((index + 1, finding, line.strip()[:160]))
    return hits


def local_cognition_findings(root: Path) -> list[str]:
    failures: list[str] = []
    for path in _memory_code_paths(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        failures.extend(
            f"{rel}:{n} [local-memory-cognition/{finding}] {line}"
            for n, finding, line in local_cognition_hits(text)
        )
    return failures


def agent_lane_doctrine_hits(text: str) -> list[tuple[int, str, str]]:
    """``(line_no, finding_class, line)`` for doctrine that gates the agent lane."""
    lines = text.splitlines()
    hits: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        for finding, pattern in AGENT_LANE_INTERPOSITION_PATTERNS:
            if not pattern.search(line):
                continue
            if AGENT_LANE_INTERPOSITION_ALLOW.search(line):
                continue
            if AGENT_LANE_INTERPOSITION_ALLOW.search(_paragraph(lines, index)):
                continue
            hits.append((index + 1, finding, line.strip()[:160]))
    return hits


def _load_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def hook_matcher_findings(root: Path) -> list[str]:
    """Pre-execution matchers / gate tool-lists that would deny the agent lane."""
    failures: list[str] = []

    settings = _load_json(root / CLAUDE_SETTINGS_TEMPLATE)
    if isinstance(settings, dict):
        for entry in settings.get("hooks", {}).get("PreToolUse", []) or []:
            matcher = str(entry.get("matcher", "") or "")
            if not matcher:
                continue
            try:
                compiled = re.compile(matcher)
            except re.error:
                continue
            for probe in MEMORY_MCP_PROBES:
                if compiled.fullmatch(probe):
                    failures.append(
                        f"{CLAUDE_SETTINGS_TEMPLATE}: PreToolUse matcher {matcher!r} "
                        f"covers {probe} [agent-lane-interposition]"
                    )
                    break

    cursor = _load_json(root / CURSOR_HOOKS_TEMPLATE)
    if isinstance(cursor, dict):
        hooks = cursor.get("hooks", cursor)
        for phase, entries in (hooks or {}).items():
            if not str(phase).lower().startswith("before"):
                continue
            for entry in entries or []:
                matcher = str((entry or {}).get("matcher", "") or "")
                if any(
                    needle in matcher
                    for needle in ("l9-graphite-memory", "memory.", "l9-memory", "ops.memory")
                ):
                    failures.append(
                        f"{CURSOR_HOOKS_TEMPLATE}: {phase} matcher {matcher!r} names the "
                        "memory lane [agent-lane-interposition]"
                    )

    contract = _load_json(root / MEMORY_ENFORCEMENT_CONTRACT)
    if isinstance(contract, dict):
        for rule in contract.get("rules", []) or []:
            match = rule.get("match", {}) or {}
            rule_id = rule.get("id", "?")
            for tool in match.get("tools", []) or []:
                if str(tool).startswith(MEMORY_MCP_PREFIX):
                    failures.append(
                        f"{MEMORY_ENFORCEMENT_CONTRACT}: rule {rule_id} governs {tool} "
                        "[agent-lane-interposition]"
                    )
            for pattern in match.get("command_patterns", []) or []:
                try:
                    compiled = re.compile(str(pattern))
                except re.error:
                    continue
                for probe in MEMORY_SHELL_PROBES:
                    if compiled.search(probe):
                        failures.append(
                            f"{MEMORY_ENFORCEMENT_CONTRACT}: rule {rule_id} pattern "
                            f"{pattern!r} matches {probe!r} [agent-lane-interposition]"
                        )
                        break
    return failures


def agent_lane_findings(root: Path) -> tuple[list[str], list[str]]:
    """``(failures, warnings)`` for the agent-lane interposition class.

    Doctrine hits follow the ratchet-2 surface classes (FAIL / AMENDED / WARN);
    matcher hits always fail.
    """
    failures: list[str] = list(hook_matcher_findings(root))
    warnings: list[str] = []
    for path in _memory_doctrine_surfaces(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        hits = agent_lane_doctrine_hits(text)
        if not hits:
            continue
        klass = _surface_class(root, rel)
        if klass == "AMENDED":
            if has_supersession_marker(text):
                continue
            failures.extend(
                f"{rel}:{n} [agent-lane-interposition/{finding}; no dated supersession "
                f"heading naming ADR-0033] {line}"
                for n, finding, line in hits
            )
        elif klass == "FAIL":
            failures.extend(
                f"{rel}:{n} [agent-lane-interposition/{finding}] {line}"
                for n, finding, line in hits
            )
        else:
            warnings.extend(
                f"{rel}:{n} [agent-lane-interposition/{finding}] {line}"
                for n, finding, line in hits
            )
    return failures, warnings


def _surface_class(root: Path, rel: str) -> str:
    if rel in MEMORY_DOCTRINE_FAIL_SURFACES:
        return "FAIL"
    if rel in MEMORY_DOCTRINE_AMENDED_ROOTS:
        return "AMENDED"
    if Path(rel).match(MEMORY_DOCTRINE_ADR_GLOB):
        return "AMENDED"
    return "WARN"


def _memory_doctrine_surfaces(root: Path) -> list[Path]:
    seen: set[Path] = set(_iter_active_files(root))
    for rel in (*MEMORY_DOCTRINE_FAIL_SURFACES, *MEMORY_DOCTRINE_AMENDED_ROOTS):
        path = root / rel
        if path.is_file():
            seen.add(path)
    seen.update(p for p in root.glob(MEMORY_DOCTRINE_ADR_GLOB) if p.is_file())
    return sorted(seen)


def memory_doctrine_findings(root: Path) -> tuple[list[str], list[str]]:
    """Return ``(failures, warnings)`` for the memory doctrine ratchet."""
    failures: list[str] = []
    warnings: list[str] = []
    for path in _memory_doctrine_surfaces(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        klass = _surface_class(root, rel)
        hits = memory_doctrine_hits(text)
        if hits:
            if klass == "AMENDED":
                if has_supersession_marker(text):
                    continue  # historical text licensed by the dated amendment
                failures.extend(
                    f"{rel}:{n} [{finding}; no dated supersession/amendment heading naming "
                    f"ADR-0030] {line}"
                    for n, finding, line in hits
                )
            elif klass == "FAIL":
                failures.extend(f"{rel}:{n} [{finding}] {line}" for n, finding, line in hits)
            else:
                warnings.extend(f"{rel}:{n} [{finding}] {line}" for n, finding, line in hits)
    memory_bound = (root / MEMORY_BINDING_MANIFEST).is_file()
    for rel, tokens in MEMORY_DOCTRINE_REQUIRED_TOKENS.items():
        path = root / rel
        if not path.is_file():
            if memory_bound:
                failures.append(
                    f"{rel}: converged surface missing (required to carry the write contract)"
                )
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                failures.append(
                    f"{rel}: converged surface no longer carries `{token}` "
                    "(agent write contract: ADR-0030 item 7 as amended by ADR-0033 — "
                    "memory.write_agent is the ordinary agent write; "
                    "phase_lock + write_governed is the optional pair)"
                )
    for rel, tokens in MEMORY_DOCTRINE_FORBIDDEN_TOKENS.items():
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token in text:
                failures.append(
                    f"{rel}: converged surface re-teaches `{token}` "
                    "(MEMORY_PREFETCH cites the canonical receipt, never episode names)"
                )
    return failures, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=str(ROOT), help="repository root (default: this clone)")
    parser.add_argument(
        "--strict-memory-doctrine",
        action="store_true",
        help="treat WARN-class memory-doctrine residue (not yet converged surfaces) as failures",
    )
    # ``None`` means "no flags" (library callers, the pre-existing unit tests);
    # the ``__main__`` entry passes ``sys.argv[1:]`` explicitly.
    args = parser.parse_args([] if argv is None else argv)
    root = Path(args.root).resolve()

    findings: list[str] = []
    client_findings: set[str] = set()

    # Full active corpus: Dropbox/HTTP side doors AND the retired memory client.
    for path in _iter_active_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        _scan_retired_client(rel, text, client_findings)
        for i, line in enumerate(text.splitlines(), 1):
            if ALLOW_LINE.search(line):
                continue
            if DROPBOX_LIVE.search(line) or HTTP_LIVE.search(line):
                findings.append(f"{rel}:{i}: {line.strip()[:160]}")

    # Authority / session-protocol root surfaces not covered by ACTIVE_ROOTS.
    for rel in AUTHORITY_PROTOCOL_SURFACES:
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        _scan_retired_client(rel, text, client_findings)

    doctrine_failures, doctrine_warnings = memory_doctrine_findings(root)
    lane_failures, lane_warnings = agent_lane_findings(root)
    cognition_failures = local_cognition_findings(root)
    if args.strict_memory_doctrine:
        if doctrine_warnings:
            doctrine_failures.extend(f"{hit} (strict)" for hit in doctrine_warnings)
            doctrine_warnings = []
        if lane_warnings:
            lane_failures.extend(f"{hit} (strict)" for hit in lane_warnings)
            lane_warnings = []

    rc = 0
    if findings:
        print("FAIL: active doctrine teaches retired Dropbox SSOT or L9_MEMORY_HTTP side door")
        print(
            "Active surfaces must use $HOME/.cursor-governance + the canonical memory "
            "control plane only (ADR-0006, ADR-0030)."
        )
        for hit in findings[:80]:
            print(f"  {hit}")
        if len(findings) > 80:
            print(f"  ... and {len(findings) - 80} more")
        rc = 1
    if client_findings:
        print(
            "FAIL: active surface calls the retired memory client "
            "(agents/cursor/cursor_memory_client.py)"
        )
        print("Use the memory control plane (python -m ops.memory.cli) instead.")
        for hit in sorted(client_findings):
            print(f"  {hit}")
        rc = 1
    if doctrine_failures:
        print(
            "FAIL: converged memory-doctrine surface teaches the retired direct-Graphiti "
            "architecture (ADR-0030 items 7-9, CANONICAL_LAW 8.3)"
        )
        print(
            "One authority (MemoryService); the ordinary agent write is memory.write_agent "
            "(phase_lock -> write_governed is the optional pair); Graphiti is a projection."
        )
        for hit in doctrine_failures[:120]:
            print(f"  {hit}")
        if len(doctrine_failures) > 120:
            print(f"  ... and {len(doctrine_failures) - 120} more")
        rc = 1
    if cognition_failures:
        print(
            "FAIL: production code on a memory path holds local memory cognition "
            "(ADR-0033 / INV-03b: no memory persistence or cognition bypasses MemoryService)"
        )
        print(
            "Delete the provider client / model id / promotion rule / local distill knob / "
            "S3 queue; hand the redacted material to `l9-memory distill` instead."
        )
        for hit in cognition_failures[:120]:
            print(f"  {hit}")
        if len(cognition_failures) > 120:
            print(f"  ... and {len(cognition_failures) - 120} more")
        rc = 1
    if lane_failures:
        print(
            "FAIL: the agent lane is interposed on (ADR-0033 / INV-03b: Cursor-Governance "
            "may not gate an agent-initiated memory write on a phase, receipt, close or PR)"
        )
        for hit in lane_failures[:120]:
            print(f"  {hit}")
        if len(lane_failures) > 120:
            print(f"  ... and {len(lane_failures) - 120} more")
        rc = 1
    pending = [*doctrine_warnings, *lane_warnings]
    if pending:
        print(
            f"WARN: {len(pending)} memory-doctrine residue hit(s) on surfaces not yet "
            "converged by a locked run (pending convergence; --strict-memory-doctrine fails them)"
        )
        for hit in pending[:120]:
            print(f"  WARN {hit}")
        if len(pending) > 120:
            print(f"  ... and {len(pending) - 120} more")

    if rc:
        return rc
    print(
        "PASS: no active Dropbox SSOT / L9_MEMORY_HTTP side-door or retired-client teaching; "
        "converged memory-doctrine surfaces carry the agent write contract; no local memory "
        "cognition; no agent-lane interposition"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
