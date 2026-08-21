#!/usr/bin/env python3
"""Extract candidate governance doctrine from active skill surfaces.
This module is deliberately non-authoritative.
It discovers statements that *may* encode governance, preserves their exact
source provenance, classifies them conservatively, and emits canonical
contract-extraction records. It NEVER promotes extracted prose into an active
contract and NEVER resolves contradictions by inference.
The extractor is designed to be used both as a CLI and as the foundation for:
- cluster_doctrine.py
- detect_hidden_doctrine.py
- build_doctrine_census.py
- validate_doctrine_ratchet.py
Production properties:
- immutable Git commit binding;
- source SHA-256 binding;
- deterministic ordering and serialization;
- safe YAML parsing with duplicate-key rejection;
- active skill surfaces only by default;
- native SKILL.md frontmatter preserved as metadata, not reinterpreted as law;
- frontmatter descriptions remain discoverable as routing/activation candidates;
- fenced examples are excluded by default;
- archived/test/generated surfaces are excluded by default;
- no LLM dependency;
- no network dependency;
- no mutation of source files;
- no automatic contract activation.
Exit codes:
0
    Successful extraction. Candidate doctrine may exist; that is expected.
1
    Reserved for future policy-level extraction failures.
2
    Configuration, repository-integrity, parse, or filesystem failure.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import urlsplit
try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install repository development dependencies "
        "or run inside the repository CI environment."
    ) from exc
ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR_VERSION = "1.0.0"
EXTRACTION_SCHEMA_ID = "canonical.schema.contract_extraction_record.v1"
EXTRACTION_SCHEMA_PATH = (
    Path("contracts")
    / "schemas"
    / "canonical.schema.contract_extraction_record.v1.yaml"
)
GOVERNANCE_TEXT_EXTENSIONS = {
    ".md",
    ".mdc",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
}
CODE_TEXT_EXTENSIONS = {
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}
EXCLUDED_DIRECTORY_NAMES = {
    "_archived",
    "archived",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "tests",
    "fixtures",
    "generated",
}
MAX_TEXT_FILE_BYTES = 2_000_000
CANONICAL_ANNOTATION_PREFIX = "l9-doctrine:"
ANNOTATION_RE = re.compile(
    r"^\s*<!--\s*l9-doctrine:\s*.*?-->\s*$",
    re.IGNORECASE,
)
CONTRACT_ID_RE = re.compile(
    r"^[A-Z][A-Z0-9]*(?:\.[A-Z][A-Z0-9_]*)+\.\d{3}$"
)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""
def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            line = key_node.start_mark.line + 1
            raise ValueError(
                f"duplicate YAML mapping key {key!r} at line {line}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping
UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)
@dataclass(frozen=True)
class Finding:
    """Structured extraction diagnostic."""
    code: str
    severity: str
    path: str
    message: str
    line: int | None = None
    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }
        if self.line is not None:
            result["line"] = self.line
        return result
@dataclass(frozen=True)
class SourceBlock:
    """Exact source unit considered by the doctrine classifier."""
    path: str
    skill_name: str
    line_start: int
    line_end: int
    section: str | None
    exact_text: str
@dataclass(frozen=True)
class SignalRule:
    """One deterministic lexical signal."""
    token: str
    pattern: re.Pattern[str]
    weight: int
HARD_NORMATIVE_RULES = (
    SignalRule("must_not", re.compile(r"\bmust\s+not\b", re.I), 8),
    SignalRule("shall_not", re.compile(r"\bshall\s+not\b", re.I), 8),
    SignalRule("may_not", re.compile(r"\bmay\s+not\b", re.I), 7),
    SignalRule("never", re.compile(r"\bnever\b", re.I), 8),
    SignalRule("do_not", re.compile(r"\bdo\s+not\b", re.I), 7),
    SignalRule("prohibited", re.compile(r"\bprohibit(?:ed|s)?\b", re.I), 8),
    SignalRule("forbidden", re.compile(r"\bforbidden\b", re.I), 8),
    SignalRule("mandatory", re.compile(r"\bmandatory\b", re.I), 7),
    SignalRule("must", re.compile(r"\bmust\b", re.I), 7),
    SignalRule("shall", re.compile(r"\bshall\b", re.I), 7),
    SignalRule("required", re.compile(r"\brequired\b", re.I), 6),
    SignalRule("requires", re.compile(r"\brequires?\b", re.I), 5),
)
ADVISORY_RULES = (
    SignalRule("should_not", re.compile(r"\bshould\s+not\b", re.I), 4),
    SignalRule("should", re.compile(r"\bshould\b", re.I), 3),
    SignalRule("recommended", re.compile(r"\brecommend(?:ed|s)?\b", re.I), 3),
    SignalRule("prefer", re.compile(r"\bprefer(?:red|s)?\b", re.I), 3),
)
AUTHORITY_RULES = (
    SignalRule(
        "source_of_truth",
        re.compile(r"\bsource\s+of\s+truth\b", re.I),
        8,
    ),
    SignalRule("ssot", re.compile(r"\bSSOT\b", re.I), 8),
    SignalRule("authoritative", re.compile(r"\bauthoritative\b", re.I), 8),
    SignalRule("canonical", re.compile(r"\bcanonical\b", re.I), 5),
    SignalRule(
        "authority_order",
        re.compile(r"\bauthority\s+order\b", re.I),
        7,
    ),
    SignalRule(
        "single_owner",
        re.compile(r"\b(?:sole|single)\s+(?:owner|authority|source)\b", re.I),
        6,
    ),
)
FAILURE_RULES = (
    SignalRule(
        "fail_closed",
        re.compile(r"\bfail(?:s|ed|ing)?[-\s]+closed\b", re.I),
        8,
    ),
    SignalRule("stop", re.compile(r"\bSTOP\b", re.I), 7),
    SignalRule("deny", re.compile(r"\bden(?:y|ied|ies)\b", re.I), 6),
    SignalRule("block", re.compile(r"\bblock(?:ed|ing|s)?\b", re.I), 5),
    SignalRule(
        "abort",
        re.compile(r"\babort(?:ed|ing|s)?\b", re.I),
        5,
    ),
)
OWNERSHIP_RULES = (
    SignalRule(
        "approval_required",
        re.compile(r"\bapproval\s+(?:is\s+)?required\b", re.I),
        7,
    ),
    SignalRule(
        "permission_required",
        re.compile(r"\bpermission\s+(?:is\s+)?required\b", re.I),
        7,
    ),
    SignalRule(
        "protected",
        re.compile(r"\bprotected\b", re.I),
        4,
    ),
    SignalRule(
        "owner",
        re.compile(r"\b(?:owner|owned\s+by|ownership)\b", re.I),
        4,
    ),
    SignalRule(
        "immutable",
        re.compile(r"\bimmutable\b", re.I),
        4,
    ),
    SignalRule(
        "append_only",
        re.compile(r"\bappend[-\s]+only\b", re.I),
        5,
    ),
)
ROUTING_RULES = (
    SignalRule(
        "use_when",
        re.compile(r"\buse\s+when\b", re.I),
        5,
    ),
    SignalRule(
        "invoke_when",
        re.compile(r"\binvoke\s+when\b", re.I),
        5,
    ),
    SignalRule(
        "activate_when",
        re.compile(r"\bactivat(?:e|es|ed)\s+when\b", re.I),
        5,
    ),
    SignalRule(
        "route",
        re.compile(r"\brout(?:e|es|ed|ing)\b", re.I),
        3,
    ),
    SignalRule(
        "trigger",
        re.compile(r"\btrigger(?:s|ed|ing)?\b", re.I),
        3,
    ),
)
CAPABILITY_RULES = (
    SignalRule(
        "supports",
        re.compile(r"\bsupport(?:s|ed)?\b", re.I),
        2,
    ),
    SignalRule(
        "capability",
        re.compile(r"\bcapabilit(?:y|ies)\b", re.I),
        3,
    ),
    SignalRule(
        "can",
        re.compile(r"\bcan\b", re.I),
        1,
    ),
    SignalRule(
        "available",
        re.compile(r"\bavailable\b", re.I),
        1,
    ),
)
EVIDENCE_RULES = (
    SignalRule(
        "evidence",
        re.compile(r"\bevidence\b", re.I),
        3,
    ),
    SignalRule(
        "proof",
        re.compile(r"\bproof\b|\bprove(?:s|d)?\b", re.I),
        3,
    ),
    SignalRule(
        "verify",
        re.compile(r"\bverif(?:y|ies|ied|ication)\b", re.I),
        3,
    ),
    SignalRule(
        "validate",
        re.compile(r"\bvalidat(?:e|es|ed|ion)\b", re.I),
        2,
    ),
    SignalRule(
        "must_pass",
        re.compile(r"\bmust\s+pass\b", re.I),
        6,
    ),
)
CONDITION_RE = re.compile(
    r"\b(?:if|when|whenever|unless|only\s+if|provided\s+that)\b",
    re.I,
)
PERMISSION_RE = re.compile(
    r"\b(?:may|can)\s+(?:only\s+)?(?:perform|execute|write|modify|change|use|run)\b",
    re.I,
)
CONSTRAINT_RE = re.compile(
    r"\b(?:only|exactly|at\s+most|at\s+least|no\s+more\s+than)\b",
    re.I,
)
WORKFLOW_RE = re.compile(
    r"\b(?:phase|step|transition|state|workflow|before|after|then|next)\b",
    re.I,
)
RATIONALE_SECTION_RE = re.compile(
    r"\b(?:rationale|why|background|context|motivation)\b",
    re.I,
)
EXAMPLE_SECTION_RE = re.compile(
    r"\b(?:example|examples|sample|samples|illustration)\b",
    re.I,
)
OBSOLETE_SECTION_RE = re.compile(
    r"\b(?:deprecated|retired|historical|legacy\s+reference|obsolete)\b",
    re.I,
)
EXAMPLE_PREFIX_RE = re.compile(
    r"^\s*(?:>\s*)?(?:example|sample|e\.g\.|for\s+example|wrong|bad)\s*[:\-]",
    re.I,
)
QUOTED_BLOCK_RE = re.compile(r"^\s*>")
CRITICAL_RISK_RE = re.compile(
    r"\b(?:"
    r"force[-\s]+push|"
    r"credential|secret|token|password|"
    r"production|prod\b|"
    r"destructive|delete|drop\s+table|"
    r"authorization|permission|"
    r"protected\s+(?:path|file|branch)|"
    r"external\s+write"
    r")\b",
    re.I,
)
HIGH_RISK_RE = re.compile(
    r"\b(?:"
    r"git|push|pull\s+request|merge|"
    r"CI|workflow|gate|deploy|"
    r"memory|graphiti|SSOT|"
    r"governance|contract|"
    r"database|network|"
    r"approval|validator|validation"
    r")\b",
    re.I,
)
REPOSITORY_GLOBAL_RE = re.compile(
    r"\b(?:"
    r"all\s+agents?|any\s+agents?|"
    r"repository|repo\b|workspace|"
    r"global|governance|canonical\s+law|"
    r"source\s+of\s+truth|SSOT|"
    r"protected\s+(?:path|file|branch)"
    r")\b",
    re.I,
)
DOMAIN_SHARED_RE = re.compile(
    r"\b(?:"
    r"git|github|CI|workflow|deployment|"
    r"memory|graphiti|database|postgres|"
    r"secrets?|terraform|kubernetes|"
    r"testing|validation|evidence|"
    r"incident|security"
    r")\b",
    re.I,
)
SKILL_LOCAL_RE = re.compile(
    r"\b(?:this\s+skill|within\s+this\s+skill|skill[-\s]+local)\b",
    re.I,
)
MODAL_PARSE_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?"
    r"(?P<subject>[^.;:\n]{1,120}?)\s+"
    r"(?P<modal>"
    r"must\s+not|must|"
    r"shall\s+not|shall|"
    r"may\s+not|may\s+only|"
    r"should\s+not|should"
    r")\s+"
    r"(?P<action>[^.;\n]{1,240})",
    re.I,
)
DO_NOT_PARSE_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?do\s+not\s+(?P<action>[^.;\n]{1,240})",
    re.I,
)
def load_yaml_unique(path: Path) -> Any:
    """Load YAML safely and reject duplicate mapping keys."""
    with path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=UniqueKeyLoader)
def dump_yaml(value: Any) -> str:
    """Serialize YAML deterministically enough for repository generation."""
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )
def canonical_json_bytes(value: Any) -> bytes:
    """Return stable JSON bytes suitable for hashing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))
def stable_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))
def stable_id(prefix: str, *parts: str, length: int = 16) -> str:
    payload = "\x1f".join(parts)
    return f"{prefix}.{sha256_text(payload)[:length].upper()}"
def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
def _run_git(root: Path, *args: str) -> str:
    command = ["git", "-C", str(root), *args]
    process = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if process.returncode != 0:
        message = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(
            f"git command failed ({' '.join(args)}): {message or 'unknown error'}"
        )
    return process.stdout.strip()
def git_head_sha(root: Path) -> str:
    sha = _run_git(root, "rev-parse", "HEAD")
    if not FULL_SHA_RE.fullmatch(sha):
        raise RuntimeError(f"HEAD is not an immutable 40-character SHA: {sha!r}")
    return sha
def git_commit_timestamp(root: Path, sha: str) -> str:
    timestamp = _run_git(root, "show", "-s", "--format=%cI", sha)
    if not timestamp:
        raise RuntimeError(f"could not determine commit timestamp for {sha}")
    return timestamp
def git_workspace_dirty(root: Path) -> bool:
    output = _run_git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    )
    return bool(output.strip())
def _sanitize_remote(remote: str) -> str:
    """Normalize Git remote without ever emitting embedded credentials."""
    remote = remote.strip()
    if not remote:
        return ""
    if remote.startswith("git@") and ":" in remote:
        host, path = remote.split(":", 1)
        host = host.split("@", 1)[-1]
        return f"{host}/{path.removesuffix('.git')}"
    if "://" in remote:
        parsed = urlsplit(remote)
        host = parsed.hostname or ""
        path = parsed.path.strip("/").removesuffix(".git")
        if host and path:
            return f"{host}/{path}"
    return remote.removesuffix(".git")
def repository_identity(root: Path) -> str:
    try:
        remote = _run_git(root, "config", "--get", "remote.origin.url")
    except RuntimeError:
        return root.name
    normalized = _sanitize_remote(remote)
    return normalized or root.name
def ensure_extraction_schema(root: Path) -> None:
    """Fail closed if the assumed canonical extraction schema is absent or wrong."""
    path = root / EXTRACTION_SCHEMA_PATH
    if not path.is_file():
        raise RuntimeError(
            "canonical extraction schema is missing: "
            f"{path.relative_to(root)}"
        )
    data = load_yaml_unique(path)
    if not isinstance(data, dict):
        raise RuntimeError(
            f"{path.relative_to(root)} must contain a YAML mapping"
        )
    if data.get("schema_id") != EXTRACTION_SCHEMA_ID:
        raise RuntimeError(
            f"{path.relative_to(root)} has unexpected schema_id "
            f"{data.get('schema_id')!r}"
        )
def _surface_extensions(surface_mode: str) -> set[str]:
    if surface_mode == "governance-text":
        return set(GOVERNANCE_TEXT_EXTENSIONS)
    if surface_mode == "all-text":
        return GOVERNANCE_TEXT_EXTENSIONS | CODE_TEXT_EXTENSIONS
    raise ValueError(f"unsupported surface mode: {surface_mode}")
def scan_profile(
    *,
    surface_mode: str,
    include_archived: bool,
    include_code_fences: bool,
) -> dict[str, Any]:
    """Return the exact scan profile included in census/baseline integrity."""
    extensions = sorted(_surface_extensions(surface_mode))
    excluded = sorted(
        name
        for name in EXCLUDED_DIRECTORY_NAMES
        if include_archived or name not in {"_archived", "archived"}
    )
    if not include_archived:
        excluded = sorted(EXCLUDED_DIRECTORY_NAMES)
    return {
        "scope_root": "skills",
        "surface_mode": surface_mode,
        "include_archived": include_archived,
        "include_code_fences": include_code_fences,
        "extensions": extensions,
        "excluded_directory_names": excluded,
        "max_text_file_bytes": MAX_TEXT_FILE_BYTES,
        "frontmatter_policy": "scan-description-only-v1",
        "annotation_syntax": "l9-doctrine-html-comment-v1",
    }
def scan_profile_digest(profile: dict[str, Any]) -> str:
    return stable_digest(profile)
def _path_is_excluded(
    relative_to_skills: Path,
    *,
    include_archived: bool,
) -> bool:
    for part in relative_to_skills.parts[:-1]:
        normalized = part.casefold()
        if normalized in {"_archived", "archived"} and include_archived:
            continue
        if normalized in EXCLUDED_DIRECTORY_NAMES:
            return True
    return False
def discover_skill_files(
    root: Path,
    *,
    surface_mode: str = "governance-text",
    include_archived: bool = False,
) -> list[Path]:
    """Discover deterministic active skill text surfaces."""
    skills_root = root / "skills"
    if not skills_root.is_dir():
        raise RuntimeError("skills/ directory is missing")
    extensions = _surface_extensions(surface_mode)
    discovered: list[Path] = []
    for path in skills_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(skills_root)
        if _path_is_excluded(relative, include_archived=include_archived):
            continue
        if path.suffix.casefold() not in extensions:
            continue
        discovered.append(path)
    return sorted(discovered, key=lambda item: item.as_posix().casefold())
def _skill_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root / "skills")
    if len(relative.parts) <= 1:
        return "_skills_root"
    return relative.parts[0]
def _frontmatter_end(lines: list[str]) -> int | None:
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index
    return None
def _frontmatter_description_block(
    path: str,
    skill_name: str,
    lines: list[str],
    end_index: int,
) -> SourceBlock | None:
    """Preserve skill-description routing language without scanning all metadata."""
    start: int | None = None
    finish: int | None = None
    top_level_key = re.compile(r"^[A-Za-z0-9_-]+:")
    for index in range(1, end_index):
        line = lines[index]
        if start is None:
            if re.match(r"^description\s*:", line):
                start = index
            continue
        if top_level_key.match(line) and not line.startswith((" ", "\t")):
            finish = index - 1
            break
    if start is None:
        return None
    if finish is None:
        finish = end_index - 1
    exact = "\n".join(lines[start : finish + 1]).rstrip()
    if not exact:
        return None
    return SourceBlock(
        path=path,
        skill_name=skill_name,
        line_start=start + 1,
        line_end=finish + 1,
        section="frontmatter.description",
        exact_text=exact,
    )
def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)
def iter_markdown_blocks(
    *,
    path: str,
    skill_name: str,
    text: str,
    scan_frontmatter_description: bool,
    include_code_fences: bool,
) -> Iterator[SourceBlock]:
    """Yield exact Markdown source blocks with stable source line numbers."""
    lines = text.splitlines()
    section: str | None = None
    body_start = 0
    if scan_frontmatter_description:
        end_index = _frontmatter_end(lines)
        if end_index is not None:
            description = _frontmatter_description_block(
                path,
                skill_name,
                lines,
                end_index,
            )
            if description is not None:
                yield description
            body_start = end_index + 1
    current: list[tuple[int, str]] = []
    in_fence = False
    fence_marker = ""
    def flush() -> SourceBlock | None:
        nonlocal current
        if not current:
            return None
        exact = "\n".join(line for _, line in current).rstrip()
        start = current[0][0] + 1
        end = current[-1][0] + 1
        current = []
        if not exact:
            return None
        return SourceBlock(
            path=path,
            skill_name=skill_name,
            line_start=start,
            line_end=end,
            section=section,
            exact_text=exact,
        )
    for index in range(body_start, len(lines)):
        line = lines[index]
        stripped = line.strip()
        fence_match = re.match(r"^\s*(```+|~~~+)", line)
        if fence_match:
            pending = flush()
            if pending is not None:
                yield pending
            marker = fence_match.group(1)[0:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
                if include_code_fences:
                    current.append((index, line))
                continue
            if marker == fence_marker:
                if include_code_fences:
                    current.append((index, line))
                    pending = flush()
                    if pending is not None:
                        yield pending
                in_fence = False
                fence_marker = ""
                continue
        if in_fence:
            if include_code_fences:
                current.append((index, line))
            continue
        if ANNOTATION_RE.fullmatch(line):
            pending = flush()
            if pending is not None:
                yield pending
            continue
        heading = re.match(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            pending = flush()
            if pending is not None:
                yield pending
            section = normalize_space(heading.group(1))
            continue
        if not stripped:
            pending = flush()
            if pending is not None:
                yield pending
            continue
        if stripped.startswith("|"):
            pending = flush()
            if pending is not None:
                yield pending
            if not _is_table_separator(line):
                yield SourceBlock(
                    path=path,
                    skill_name=skill_name,
                    line_start=index + 1,
                    line_end=index + 1,
                    section=section,
                    exact_text=line.rstrip(),
                )
            continue
        list_item = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line)
        if list_item:
            pending = flush()
            if pending is not None:
                yield pending
            current.append((index, line))
            continue
        current.append((index, line))
    pending = flush()
    if pending is not None:
        yield pending
def iter_plain_blocks(
    *,
    path: str,
    skill_name: str,
    text: str,
) -> Iterator[SourceBlock]:
    """Yield conservative line-oriented blocks for YAML/JSON/TOML/code text."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if ANNOTATION_RE.fullmatch(line):
            continue
        if stripped.startswith(("#", "//")) and CANONICAL_ANNOTATION_PREFIX in stripped:
            continue
        yield SourceBlock(
            path=path,
            skill_name=skill_name,
            line_start=index + 1,
            line_end=index + 1,
            section=None,
            exact_text=line.rstrip(),
        )
def iter_source_blocks(
    *,
    root: Path,
    path: Path,
    text: str,
    include_code_fences: bool,
) -> Iterator[SourceBlock]:
    relative = path.relative_to(root).as_posix()
    skill_name = _skill_name(root, path)
    if path.suffix.casefold() in {".md", ".mdc"}:
        yield from iter_markdown_blocks(
            path=relative,
            skill_name=skill_name,
            text=text,
            scan_frontmatter_description=path.name == "SKILL.md",
            include_code_fences=include_code_fences,
        )
        return
    yield from iter_plain_blocks(
        path=relative,
        skill_name=skill_name,
        text=text,
    )
def _matched_tokens(
    rules: Iterable[SignalRule],
    text: str,
) -> tuple[list[str], int]:
    tokens: list[str] = []
    score = 0
    for rule in rules:
        if rule.pattern.search(text):
            tokens.append(rule.token)
            score += rule.weight
    return sorted(set(tokens)), score
def _strip_markdown_for_analysis(text: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    value = re.sub(r"$begin:math:display$\(\[\^$end:math:display$]+)\]$begin:math:text$\[\^\)\]\+$end:math:text$", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"[*_~]+", "", value)
    return normalize_space(value)
def _classify_strength(
    *,
    hard_tokens: list[str],
    advisory_tokens: list[str],
    text: str,
) -> str:
    if hard_tokens:
        if CONDITION_RE.search(text):
            return "conditional_normative"
        return "hard_normative"
    if advisory_tokens:
        if CONDITION_RE.search(text):
            return "conditional_normative"
        return "advisory"
    return "descriptive"
def _classify_kind(
    *,
    block: SourceBlock,
    text: str,
    hard_tokens: list[str],
    authority_tokens: list[str],
    routing_tokens: list[str],
    capability_tokens: list[str],
    evidence_tokens: list[str],
) -> str:
    section = block.section or ""
    if OBSOLETE_SECTION_RE.search(section):
        return "obsolete"
    if EXAMPLE_SECTION_RE.search(section) and (
        EXAMPLE_PREFIX_RE.search(text) or QUOTED_BLOCK_RE.search(block.exact_text)
    ):
        return "example"
    if EXAMPLE_PREFIX_RE.search(text):
        return "example"
    if RATIONALE_SECTION_RE.search(section) and not hard_tokens:
        return "rationale"
    if block.section == "frontmatter.description" and routing_tokens:
        return "routing_activation"
    if routing_tokens and not hard_tokens:
        return "routing_activation"
    if evidence_tokens and re.search(
        r"\b(?:pass|fail|check|verify|evidence|proof|validate)\b",
        text,
        re.I,
    ):
        return "evidence"
    if capability_tokens and re.search(
        r"\b(?:supports?|capabilit(?:y|ies)|available|can)\b",
        text,
        re.I,
    ):
        if not hard_tokens and not authority_tokens:
            return "capability"
    if WORKFLOW_RE.search(text) and hard_tokens:
        return "workflow"
    if CONDITION_RE.search(text) and (
        hard_tokens
        or PERMISSION_RE.search(text)
        or re.search(r"\b(?:allow|deny|approval|permission)\b", text, re.I)
    ):
        return "policy"
    if hard_tokens or authority_tokens:
        return "invariant"
    return "unknown"
def _classify_sharedness(
    *,
    block: SourceBlock,
    text: str,
    kind: str,
) -> str:
    if block.section == "frontmatter.description" and kind == "routing_activation":
        return "projection_only"
    if SKILL_LOCAL_RE.search(text):
        return "skill_local"
    if REPOSITORY_GLOBAL_RE.search(text):
        return "repository_global"
    if DOMAIN_SHARED_RE.search(text):
        return "domain_shared"
    skill_token = block.skill_name.replace("-", " ")
    if block.skill_name != "_skills_root" and skill_token.casefold() in text.casefold():
        return "skill_local"
    return "unknown"
def _classify_risk(
    *,
    text: str,
    strength: str,
    authority_tokens: list[str],
) -> str:
    if CRITICAL_RISK_RE.search(text):
        return "critical"
    if HIGH_RISK_RE.search(text) or authority_tokens:
        return "high"
    if strength in {"hard_normative", "conditional_normative"}:
        return "medium"
    return "low"
def _classify_effect(
    *,
    text: str,
    hard_tokens: list[str],
    advisory_tokens: list[str],
    failure_tokens: list[str],
    routing_tokens: list[str],
    evidence_tokens: list[str],
) -> str:
    negative = {
        "must_not",
        "shall_not",
        "may_not",
        "never",
        "do_not",
        "prohibited",
        "forbidden",
    }
    if set(hard_tokens) & negative:
        return "prohibit"
    if {"fail_closed", "stop", "abort"} & set(failure_tokens):
        return "stop"
    if PERMISSION_RE.search(text):
        return "permit"
    if routing_tokens and re.search(
        r"\b(?:route|use\s+when|invoke\s+when|activate\s+when)\b",
        text,
        re.I,
    ):
        return "route"
    if evidence_tokens and re.search(
        r"\b(?:attest|record|capture|prove|evidence)\b",
        text,
        re.I,
    ):
        return "attest"
    if CONSTRAINT_RE.search(text) and (hard_tokens or advisory_tokens):
        return "constrain"
    if hard_tokens:
        return "require"
    if advisory_tokens:
        return "constrain"
    return "unknown"
def _parse_subject_action(
    text: str,
) -> tuple[str | None, str | None]:
    modal = MODAL_PARSE_RE.search(text)
    if modal:
        subject = normalize_space(modal.group("subject"))
        action = normalize_space(modal.group("action"))
        return subject or None, action or None
    do_not = DO_NOT_PARSE_RE.search(text)
    if do_not:
        action = normalize_space(do_not.group("action"))
        return None, action or None
    return None, None
def _candidate_score(
    *,
    hard_score: int,
    advisory_score: int,
    authority_score: int,
    failure_score: int,
    ownership_score: int,
    routing_score: int,
    capability_score: int,
    evidence_score: int,
) -> int:
    return (
        hard_score
        + advisory_score
        + authority_score
        + failure_score
        + ownership_score
        + routing_score
        + capability_score
        + evidence_score
    )
def _confidence(
    *,
    score: int,
    kind: str,
    strength: str,
    effect: str,
    subject: str | None,
    action: str | None,
) -> tuple[float, list[str]]:
    confidence = 0.45
    ambiguity: list[str] = []
    confidence += min(score, 25) / 100
    if kind != "unknown":
        confidence += 0.08
    else:
        ambiguity.append("candidate_kind_uncertain")
    if strength in {"hard_normative", "conditional_normative"}:
        confidence += 0.08
    if effect != "unknown":
        confidence += 0.06
    else:
        ambiguity.append("normative_effect_uncertain")
    if subject is not None:
        confidence += 0.03
    else:
        ambiguity.append("subject_not_safely_parseable")
    if action is not None:
        confidence += 0.03
    else:
        ambiguity.append("action_not_safely_parseable")
    return round(min(confidence, 0.99), 2), ambiguity
def _resolution_for(
    *,
    kind: str,
    strength: str,
    sharedness: str,
    confidence: float,
) -> str:
    if kind == "obsolete":
        return "retire_obsolete"
    if kind in {"rationale", "example"}:
        return "retain_as_rationale"
    if (
        sharedness == "skill_local"
        and strength in {"hard_normative", "conditional_normative"}
    ):
        return "create_skill_local_contract"
    if (
        kind in {"invariant", "policy", "capability", "workflow", "evidence"}
        and sharedness in {"repository_global", "domain_shared"}
        and confidence >= 0.75
    ):
        return "extract_new_contract"
    return "needs_human_review"
def analyze_block(
    *,
    block: SourceBlock,
    repository: str,
    commit_sha: str,
    commit_timestamp: str,
    source_sha256: str,
) -> dict[str, Any] | None:
    """Convert one source block into a canonical extraction record candidate."""
    analysis_text = _strip_markdown_for_analysis(block.exact_text)
    if not analysis_text:
        return None
    hard_tokens, hard_score = _matched_tokens(HARD_NORMATIVE_RULES, analysis_text)
    advisory_tokens, advisory_score = _matched_tokens(ADVISORY_RULES, analysis_text)
    authority_tokens, authority_score = _matched_tokens(AUTHORITY_RULES, analysis_text)
    failure_tokens, failure_score = _matched_tokens(FAILURE_RULES, analysis_text)
    ownership_tokens, ownership_score = _matched_tokens(OWNERSHIP_RULES, analysis_text)
    routing_tokens, routing_score = _matched_tokens(ROUTING_RULES, analysis_text)
    capability_tokens, capability_score = _matched_tokens(CAPABILITY_RULES, analysis_text)
    evidence_tokens, evidence_score = _matched_tokens(EVIDENCE_RULES, analysis_text)
    score = _candidate_score(
        hard_score=hard_score,
        advisory_score=advisory_score,
        authority_score=authority_score,
        failure_score=failure_score,
        ownership_score=ownership_score,
        routing_score=routing_score,
        capability_score=capability_score,
        evidence_score=evidence_score,
    )
    high_value_signal = bool(
        hard_tokens
        or authority_tokens
        or failure_tokens
        or routing_tokens
        or ownership_score >= 7
    )
    if score < 4 and not high_value_signal:
        return None
    strength = _classify_strength(
        hard_tokens=hard_tokens,
        advisory_tokens=advisory_tokens,
        text=analysis_text,
    )
    kind = _classify_kind(
        block=block,
        text=analysis_text,
        hard_tokens=hard_tokens,
        authority_tokens=authority_tokens,
        routing_tokens=routing_tokens,
        capability_tokens=capability_tokens,
        evidence_tokens=evidence_tokens,
    )
    sharedness = _classify_sharedness(
        block=block,
        text=analysis_text,
        kind=kind,
    )
    risk = _classify_risk(
        text=analysis_text,
        strength=strength,
        authority_tokens=authority_tokens,
    )
    effect = _classify_effect(
        text=analysis_text,
        hard_tokens=hard_tokens,
        advisory_tokens=advisory_tokens,
        failure_tokens=failure_tokens,
        routing_tokens=routing_tokens,
        evidence_tokens=evidence_tokens,
    )
    subject, action = _parse_subject_action(analysis_text)
    confidence, ambiguity = _confidence(
        score=score,
        kind=kind,
        strength=strength,
        effect=effect,
        subject=subject,
        action=action,
    )
    extraction_id = stable_id(
        "EXT.SKILL",
        block.path,
        block.section or "",
        normalize_space(block.exact_text).casefold(),
    )
    disposition = _resolution_for(
        kind=kind,
        strength=strength,
        sharedness=sharedness,
        confidence=confidence,
    )
    record = {
        "extraction_identity": {
            "extraction_id": extraction_id,
            "extracted_at": commit_timestamp,
            "extractor": f"ops/contracts/extract_doctrine.py@{EXTRACTOR_VERSION}",
        },
        "source": {
            "source_kind": "skill",
            "repository": repository,
            "commit_sha": commit_sha,
            "path": block.path,
            "line_start": block.line_start,
            "line_end": block.line_end,
            "section": block.section,
            "source_sha256": source_sha256,
            "exact_text": block.exact_text,
        },
        "signals": {
            "normative_tokens": sorted(set(hard_tokens + advisory_tokens)),
            "authority_tokens": authority_tokens,
            "failure_tokens": failure_tokens,
            "ownership_tokens": ownership_tokens,
        },
        "classification": {
            "candidate_kind": kind,
            "doctrine_strength": strength,
            "sharedness": sharedness,
            "risk": risk,
        },
        "normalized_semantics": {
            "subject": subject,
            "action": action,
            "object": None,
            "effect": effect,
            "conditions": (
                ["conditional_language_present"]
                if CONDITION_RE.search(analysis_text)
                else []
            ),
            "exceptions": [],
            "inferred_scope": [sharedness],
            "authority_hint": (
                ",".join(authority_tokens) if authority_tokens else None
            ),
        },
        "extraction_quality": {
            "confidence": confidence,
            "ambiguity": ambiguity,
            "meaning_preserved": True,
        },
        "resolution": {
            "disposition": disposition,
            "proposed_contract_id": None,
            "existing_contract_refs": [],
            "duplicate_cluster": None,
            "conflict_cluster": None,
            "review_status": "unreviewed",
        },
    }
    return record
def validate_extraction_record(record: dict[str, Any]) -> list[str]:
    """Validate extractor-owned structural invariants before emitting a record."""
    errors: list[str] = []
    identity = record.get("extraction_identity")
    source = record.get("source")
    classification = record.get("classification")
    semantics = record.get("normalized_semantics")
    resolution = record.get("resolution")
    if not isinstance(identity, dict):
        return ["missing extraction_identity mapping"]
    if not isinstance(source, dict):
        return ["missing source mapping"]
    if not isinstance(classification, dict):
        return ["missing classification mapping"]
    if not isinstance(semantics, dict):
        return ["missing normalized_semantics mapping"]
    if not isinstance(resolution, dict):
        return ["missing resolution mapping"]
    if not FULL_SHA_RE.fullmatch(str(source.get("commit_sha", ""))):
        errors.append("source.commit_sha is not a full immutable SHA")
    if not SHA256_RE.fullmatch(str(source.get("source_sha256", ""))):
        errors.append("source.source_sha256 is not a SHA-256 digest")
    if classification.get("candidate_kind") not in {
        "invariant",
        "policy",
        "capability",
        "workflow",
        "evidence",
        "routing_activation",
        "rationale",
        "example",
        "obsolete",
        "conflict",
        "unknown",
    }:
        errors.append("classification.candidate_kind is invalid")
    if classification.get("doctrine_strength") not in {
        "hard_normative",
        "conditional_normative",
        "advisory",
        "descriptive",
        "unknown",
    }:
        errors.append("classification.doctrine_strength is invalid")
    if classification.get("sharedness") not in {
        "repository_global",
        "domain_shared",
        "skill_local",
        "projection_only",
        "unknown",
    }:
        errors.append("classification.sharedness is invalid")
    if semantics.get("effect") not in {
        "require",
        "prohibit",
        "permit",
        "constrain",
        "stop",
        "route",
        "attest",
        "none",
        "unknown",
    }:
        errors.append("normalized_semantics.effect is invalid")
    if resolution.get("review_status") != "unreviewed":
        errors.append("extractor may emit only unreviewed records")
    return errors
def _read_text_file(
    root: Path,
    path: Path,
    findings: list[Finding],
) -> tuple[str, str] | None:
    relative = path.relative_to(root).as_posix()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        findings.append(
            Finding(
                code="SOURCE_READ_FAILED",
                severity="error",
                path=relative,
                message=str(exc),
            )
        )
        return None
    if len(raw) > MAX_TEXT_FILE_BYTES:
        findings.append(
            Finding(
                code="SOURCE_TOO_LARGE",
                severity="error",
                path=relative,
                message=(
                    f"text surface is {len(raw)} bytes; limit is "
                    f"{MAX_TEXT_FILE_BYTES}"
                ),
            )
        )
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        findings.append(
            Finding(
                code="SOURCE_NOT_UTF8",
                severity="error",
                path=relative,
                message=str(exc),
            )
        )
        return None
    return text, sha256_bytes(raw)
def extract_repository(
    root: Path = ROOT,
    *,
    surface_mode: str = "governance-text",
    include_archived: bool = False,
    include_code_fences: bool = False,
    require_schema: bool = True,
) -> dict[str, Any]:
    """Extract candidate doctrine from the requested repository state."""
    root = root.resolve()
    findings: list[Finding] = []
    if require_schema:
        ensure_extraction_schema(root)
    commit_sha = git_head_sha(root)
    commit_timestamp = git_commit_timestamp(root, commit_sha)
    repository = repository_identity(root)
    workspace_dirty = git_workspace_dirty(root)
    profile = scan_profile(
        surface_mode=surface_mode,
        include_archived=include_archived,
        include_code_fences=include_code_fences,
    )
    paths = discover_skill_files(
        root,
        surface_mode=surface_mode,
        include_archived=include_archived,
    )
    records: list[dict[str, Any]] = []
    files_scanned = 0
    for path in paths:
        loaded = _read_text_file(root, path, findings)
        if loaded is None:
            continue
        text, source_digest = loaded
        files_scanned += 1
        for block in iter_source_blocks(
            root=root,
            path=path,
            text=text,
            include_code_fences=include_code_fences,
        ):
            record = analyze_block(
                block=block,
                repository=repository,
                commit_sha=commit_sha,
                commit_timestamp=commit_timestamp,
                source_sha256=source_digest,
            )
            if record is None:
                continue
            errors = validate_extraction_record(record)
            if errors:
                source = record["source"]
                for message in errors:
                    findings.append(
                        Finding(
                            code="EXTRACTION_RECORD_INVALID",
                            severity="error",
                            path=str(source["path"]),
                            line=int(source["line_start"]),
                            message=message,
                        )
                    )
                continue
            records.append(record)
    records.sort(
        key=lambda record: (
            str(record["source"]["path"]).casefold(),
            int(record["source"]["line_start"]),
            str(record["extraction_identity"]["extraction_id"]),
        )
    )
    findings.sort(
        key=lambda finding: (
            finding.path.casefold(),
            finding.line or 0,
            finding.code,
        )
    )
    return {
        "format_version": 1,
        "schema_ref": EXTRACTION_SCHEMA_ID,
        "extractor_version": EXTRACTOR_VERSION,
        "source": {
            "repository": repository,
            "commit_sha": commit_sha,
            "commit_timestamp": commit_timestamp,
            "workspace_dirty": workspace_dirty,
        },
        "scan_profile": profile,
        "scan_profile_digest": scan_profile_digest(profile),
        "statistics": {
            "files_discovered": len(paths),
            "files_scanned": files_scanned,
            "candidate_count": len(records),
            "error_count": sum(
                1 for finding in findings if finding.severity == "error"
            ),
            "warning_count": sum(
                1 for finding in findings if finding.severity == "warning"
            ),
        },
        "records": records,
        "findings": [finding.as_dict() for finding in findings],
    }
def load_serialized(path: Path) -> Any:
    suffix = path.suffix.casefold()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix in {".yaml", ".yml"}:
        return load_yaml_unique(path)
    if suffix == ".jsonl":
        values: list[Any] = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSONL: {exc}"
                ) from exc
        return values
    raise ValueError(f"unsupported serialized input extension: {path.suffix}")
def serialize_output(value: Any, output_format: str) -> str:
    if output_format == "yaml":
        return dump_yaml(value)
    if output_format == "json":
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    if output_format == "jsonl":
        records = value.get("records") if isinstance(value, dict) else value
        if not isinstance(records, list):
            raise ValueError("JSONL output requires a record list")
        return "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        )
    raise ValueError(f"unsupported output format: {output_format}")
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract non-authoritative candidate governance doctrine "
            "from active skills."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root. Defaults to the repository containing this script.",
    )
    parser.add_argument(
        "--surface-mode",
        choices=("governance-text", "all-text"),
        default="governance-text",
        help=(
            "governance-text scans prose/config surfaces; all-text additionally "
            "includes source-code text."
        ),
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived skill surfaces. Off by default.",
    )
    parser.add_argument(
        "--include-code-fences",
        action="store_true",
        help="Include fenced Markdown code/examples. Off by default.",
    )
    parser.add_argument(
        "--format",
        choices=("yaml", "json", "jsonl"),
        default="yaml",
        help="Output serialization.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write output to this path instead of stdout.",
    )
    return parser.parse_args()
def main() -> int:
    args = _parse_args()
    try:
        result = extract_repository(
            args.root,
            surface_mode=args.surface_mode,
            include_archived=args.include_archived,
            include_code_fences=args.include_code_fences,
        )
        rendered = serialize_output(result, args.format)
    except (
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        print(f"DOCTRINE_EXTRACTION_ERROR: {exc}", file=sys.stderr)
        return 2
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    if result["statistics"]["error_count"]:
        return 2
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
