"""Shared primitives for the Manus governance tool surface.

Every tool in this package is read-only, bounded and root-confined. The
primitives here exist so those three properties are enforced once rather than
re-implemented per tool:

* :func:`resolve_within` confines a caller-supplied path to the governance root.
* :func:`read_text` refuses documents above the adapter read limit.
* :func:`truncate` caps every string that leaves a handler.
* :class:`RuntimeContext` is the only way a handler reaches a subprocess.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_OUTPUT_CHARS = 16_000
MAX_DOCUMENT_BYTES = 512_000
MAX_SEARCH_RESULTS = 50
DENIED_PARTS = frozenset({".git", ".venv", "__pycache__", "ops/secrets", "ops/vendor"})
READABLE_SUFFIXES = frozenset(
    {".json", ".md", ".mdc", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml"}
)


class ToolInputError(ValueError):
    """A caller supplied invalid tool input."""


@dataclass(frozen=True)
class ToolSpec:
    """A declared tool: schema, handler and its declared safety posture."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[RuntimeContext, dict[str, Any]], dict[str, Any]]
    read_only: bool = True
    max_output_chars: int = MAX_OUTPUT_CHARS

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n… output truncated after {limit} characters"


def _default_run(command: list[str], *, cwd: Path, timeout: int = 120) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timed_out", "command": command, "timeout_seconds": timeout}
    except OSError as exc:
        return {"status": "execution_error", "command": command, "error": str(exc)}
    return {
        "status": "completed",
        "command": command,
        "exit_code": completed.returncode,
        "stdout": truncate(completed.stdout),
        "stderr": truncate(completed.stderr),
    }


class RuntimeContext:
    """The narrow surface a tool handler is allowed to touch."""

    def __init__(
        self,
        governance_root: Path | str,
        adapter_root: Path | str | None = None,
        runner: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.governance_root = Path(governance_root).resolve()
        self.adapter_root = Path(
            adapter_root or (self.governance_root / "environment/agents/adapters/manus")
        ).resolve()
        self._runner = runner or _default_run

    def run(
        self,
        command: Iterable[Any],
        *,
        cwd: Path | str | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        return self._runner(
            [str(part) for part in command],
            cwd=Path(cwd or self.governance_root),
            timeout=timeout,
        )

    def path(self, relative: str) -> Path:
        return resolve_within(self.governance_root, relative)


def resolve_within(root: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``root``, refusing escapes and denied parts."""

    if not isinstance(relative, str) or not relative.strip():
        raise ToolInputError("path must be a non-empty string")
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ToolInputError(f"path escapes the governance root: {relative}")
    if any(part in DENIED_PARTS for part in candidate.parts):
        raise ToolInputError(f"path is denied: {relative}")
    return candidate


def read_text(path: Path, max_bytes: int = MAX_DOCUMENT_BYTES) -> str:
    if not path.is_file():
        raise ToolInputError(f"not a file: {path.name}")
    if path.stat().st_size > max_bytes:
        raise ToolInputError(f"file exceeds the governance MCP read limit ({max_bytes} bytes)")
    return path.read_text(encoding="utf-8", errors="replace")


def iter_documents(
    root: Path,
    prefixes: Iterable[str],
    suffixes: Iterable[str] = READABLE_SUFFIXES,
) -> Iterable[Path]:
    allowed = frozenset(suffixes)
    for prefix in prefixes:
        base = root / prefix
        if not base.is_dir():
            continue
        for candidate in sorted(base.rglob("*")):
            if not candidate.is_file() or candidate.suffix not in allowed:
                continue
            if any(part in DENIED_PARTS for part in candidate.parts):
                continue
            yield candidate


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "---", "//", "/*", "*")):
            continue
        return stripped[:200]
    return ""
