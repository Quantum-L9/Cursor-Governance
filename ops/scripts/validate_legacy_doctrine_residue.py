#!/usr/bin/env python3
"""Fail if active surfaces teach retired doctrine.

Two ratchets, one script:

1. **Side doors (2026-08).** Active surfaces must not teach the retired Dropbox
   SSOT, the ``L9_MEMORY_HTTP`` side door, or a live invocation of the retired
   ``agents/cursor/cursor_memory_client.py``.
2. **Memory doctrine (2026-09-07, PR #509 doctrine closure; ADR-0030 items
   7-9, CANONICAL_LAW 8.3).** Surfaces converged on the canonical memory
   control plane must not regress to the retired direct-Graphiti
   architecture: the tombstone ``ops/graphiti/graphiti_memory_client.py``
   taught as a live front door, provider URL / bearer possession, Graphiti
   ``inject`` / PICKUP taught as the current resume SSOT, or generic ingest /
   the operator CLI ``write`` taught as the model's alternative to
   ``memory.write_governed``. Converged surfaces must also *carry* the governed
   write contract (positive presence), so a rewrite cannot drop it silently.

Surface classes for ratchet 2:

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

#: Positive presence: a converged surface must still CARRY the contract.
MEMORY_DOCTRINE_REQUIRED_TOKENS: dict[str, tuple[str, ...]] = {
    "rules/03-graphiti-memory.mdc": ("memory.phase_lock", "memory.write_governed"),
    "rules/87-cursor-memory-kernel.mdc": ("memory.phase_lock", "memory.write_governed"),
    "rules/97-graph-layer-boundary.mdc": (
        "memory.write_governed",
        "ContinuationCapsuleV2",
    ),
    "rules/98-graphiti-memory-gate.mdc": ("memory.phase_lock", "memory.write_governed"),
    "environment/generated/llm-rules/03-graphiti-memory.md": (
        "memory.phase_lock",
        "memory.write_governed",
    ),
    "environment/generated/llm-rules/87-cursor-memory-kernel.md": (
        "memory.phase_lock",
        "memory.write_governed",
    ),
    "environment/generated/llm-rules/97-graph-layer-boundary.md": (
        "memory.write_governed",
        "ContinuationCapsuleV2",
    ),
    "environment/generated/llm-rules/98-graphiti-memory-gate.md": (
        "memory.phase_lock",
        "memory.write_governed",
    ),
    "skills/l9-graphiti-memory/SKILL.md": ("memory.phase_lock", "memory.write_governed"),
    "skills/l9-end-session/SKILL.md": ("memory.write_governed", "repair-write"),
    "skills/l9-end-session/references/end-session-protocol.md": (
        "memory.phase_lock",
        "memory.write_governed",
        "repair-write",
    ),
    "skills/l9-chat-extraction/SKILL.md": ("memory.phase_lock", "memory.write_governed"),
    "skills/l9-chat-extraction/references/extract-chat.md": (
        "memory.phase_lock",
        "memory.write_governed",
    ),
    "skills/l9-gmp-protocol/SKILL.md": ("snapshot_digest",),
    "skills/l9-gmp-protocol/references/phase-contracts.md": ("snapshot_digest",),
    "docs/MEMORY_PIPELINE_MAP.md": ("memory.phase_lock", "memory.write_governed"),
    "environment/agents/docs/MEMORY_TOPOLOGY.md": (
        "memory.phase_lock",
        "memory.write_governed",
    ),
    "ops/memory/README.md": ("memory.phase_lock", "memory.write_governed"),
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
    """A dated ``##`` heading that names ADR-0030 or the memory control plane."""
    for line in text.splitlines():
        if not _DATED_HEADING.match(line):
            continue
        lowered = line.lower()
        if "adr-0030" in lowered or "memory control plane" in lowered:
            return True
    return False


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
                    "(governed interactive write contract, ADR-0030 item 7)"
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
    if args.strict_memory_doctrine and doctrine_warnings:
        doctrine_failures.extend(f"{hit} (strict)" for hit in doctrine_warnings)
        doctrine_warnings = []

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
            "One authority (MemoryService), one egress (ops/memory); the model writes "
            "memory.phase_lock -> memory.write_governed; Graphiti is a projection."
        )
        for hit in doctrine_failures[:120]:
            print(f"  {hit}")
        if len(doctrine_failures) > 120:
            print(f"  ... and {len(doctrine_failures) - 120} more")
        rc = 1
    if doctrine_warnings:
        print(
            f"WARN: {len(doctrine_warnings)} memory-doctrine residue hit(s) on surfaces not yet "
            "converged by a locked run (pending convergence; --strict-memory-doctrine fails them)"
        )
        for hit in doctrine_warnings[:120]:
            print(f"  WARN {hit}")
        if len(doctrine_warnings) > 120:
            print(f"  ... and {len(doctrine_warnings) - 120} more")

    if rc:
        return rc
    print(
        "PASS: no active Dropbox SSOT / L9_MEMORY_HTTP side-door or retired-client teaching; "
        "converged memory-doctrine surfaces carry the canonical write contract"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
