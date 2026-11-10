"""Load ops/ci_parity/tools.yaml — the one pin manifest for CI-parity tools.

Every consumer (install.py, run.py, validate_manifest.py, the Claude hooks)
reads tools and lanes through here so there is a single parser and a single
notion of "installed at the pinned version".

A tool declaring ``track: ci_ref`` takes its version from the CI file its
``ci_ref`` names (``extract`` holds a regex with a ``version`` group), not from
the hand pin: install.py resolves it, installs it and records it in state.json
with ``source: ci_ref``. ``load()`` overlays that recorded version, so every
reader sees the version actually installed; ``version`` stays the reviewed
fallback used when the CI file cannot be read.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "tools.yaml"
SCHEMA = "l9.ci-parity.tools.v1"
METHODS = frozenset({"release_archive", "release_binary", "uv_tool", "venv"})
TIERS = frozenset({"fast", "heavy"})
STATE_FILE = "state.json"
TRACK_MODES = frozenset({"ci_ref"})
#: A tracked revision is a full commit SHA, never a branch or a short SHA.
TRACKED_VERSION = re.compile(r"[0-9a-f]{40}")


class ManifestError(ValueError):
    """tools.yaml is malformed."""


@dataclass(frozen=True)
class Tool:
    name: str
    version: str
    method: str
    binary: str
    version_cmd: tuple[str, ...]
    expect: str
    url: str = ""
    sha256: str = ""
    package: str = ""
    ci_ref: dict[str, str] = field(default_factory=dict)
    #: "ci_ref" when the version follows the CI file; "" for a hand pin.
    track: str = ""
    #: The hand pin when a recorded tracked version is overlaid on ``version``.
    pinned: str = ""

    @property
    def fallback_version(self) -> str:
        """The reviewed hand pin: what installs when the CI file is unreadable."""
        return self.pinned or self.version


def tracked_version(tool: Tool, text: str) -> str | None:
    """The one full SHA ``tool.ci_ref['extract']`` finds in ``text``, else None.

    Zero matches, or matches naming different revisions, are both None: the CI
    file changed shape and nothing is guessed.
    """
    pattern = tool.ci_ref.get("extract", "")
    if not tool.track or not pattern:
        return None
    found = {m.group("version") for m in re.finditer(pattern, text)}
    if len(found) != 1:
        return None
    (version,) = found
    return version if TRACKED_VERSION.fullmatch(version) else None


@dataclass(frozen=True)
class Lane:
    name: str
    tool: str
    tier: str
    globs: tuple[str, ...]
    block: tuple[str, ...]
    weight: int
    extra: dict[str, Any] = field(default_factory=dict)

    def matches(self, rel_path: str) -> bool:
        base = rel_path.rsplit("/", 1)[-1]
        return any(
            fnmatch.fnmatchcase(rel_path, g) or ("/" not in g and fnmatch.fnmatchcase(base, g))
            for g in self.globs
        )


@dataclass(frozen=True)
class Manifest:
    install_root: Path
    bin_dir: Path
    cache_root: Path
    tools: dict[str, Tool]
    lanes: dict[str, Lane]

    @property
    def state_path(self) -> Path:
        return self.install_root / STATE_FILE

    def read_state(self) -> dict[str, dict[str, str]]:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def resolve(self, tool_name: str) -> Path | None:
        """Absolute path of the tool at its pinned version, or None."""
        tool = self.tools[tool_name]
        if tool.method == "venv":
            gov = Path(os.environ.get("L9_GOVERNANCE_DIR") or Path.home() / ".cursor-governance")
            candidate = gov / ".venv" / "bin" / tool.binary
            return candidate if candidate.is_file() else None
        entry = self.read_state().get(tool_name) or {}
        if entry.get("version") != tool.version:
            return None
        path = Path(str(entry.get("path") or ""))
        return path if path.is_file() and os.access(path, os.X_OK) else None


def _expand(raw: object) -> Path:
    return Path(os.path.expanduser(str(raw)))


def _req(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data or data[key] in (None, "", []):
        raise ManifestError(f"{where}: missing {key!r}")
    return data[key]


def load(path: Path = MANIFEST) -> Manifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ManifestError(f"{path.name}: schema must be {SCHEMA}")
    tools: dict[str, Tool] = {}
    for name, raw in (data.get("tools") or {}).items():
        where = f"tools.{name}"
        method = _req(raw, "method", where)
        if method not in METHODS:
            raise ManifestError(f"{where}: unknown method {method!r}")
        tool = Tool(
            name=name,
            version=str(_req(raw, "version", where)),
            method=method,
            binary=str(_req(raw, "binary", where)),
            version_cmd=tuple(str(a) for a in _req(raw, "version_cmd", where)),
            expect=str(_req(raw, "expect", where)),
            url=str(raw.get("url") or ""),
            sha256=str(raw.get("sha256") or ""),
            package=str(raw.get("package") or ""),
            ci_ref={k: str(v) for k, v in (raw.get("ci_ref") or {}).items()},
            track=str(raw.get("track") or ""),
        )
        _check_track(tool, where)
        if method.startswith("release_") and (
            not tool.url.startswith("https://") or len(tool.sha256) != 64
        ):
            raise ManifestError(f"{where}: release tools need an https url and a sha256")
        if method == "uv_tool" and not tool.package:
            raise ManifestError(f"{where}: uv_tool needs a package")
        tools[name] = tool
    lanes: dict[str, Lane] = {}
    known = {"tool", "tier", "globs", "block", "weight"}
    for name, raw in (data.get("lanes") or {}).items():
        where = f"lanes.{name}"
        tool_name = _req(raw, "tool", where)
        if tool_name not in tools:
            raise ManifestError(f"{where}: unknown tool {tool_name!r}")
        tier = _req(raw, "tier", where)
        if tier not in TIERS:
            raise ManifestError(f"{where}: tier must be one of {sorted(TIERS)}")
        weight = int(raw.get("weight") or 1)
        if weight < 1:
            raise ManifestError(f"{where}: weight must be >= 1")
        lanes[name] = Lane(
            name=name,
            tool=tool_name,
            tier=tier,
            globs=tuple(str(g) for g in _req(raw, "globs", where)),
            block=tuple(str(b) for b in (raw.get("block") or [])),
            weight=weight,
            extra={k: v for k, v in raw.items() if k not in known},
        )
    loaded = Manifest(
        install_root=_expand(data.get("install_root") or "~/.local/share/l9-ci-parity"),
        bin_dir=_expand(data.get("bin_dir") or "~/.local/bin"),
        cache_root=_expand(data.get("cache_root") or "~/.cache/l9-ci-parity"),
        tools=tools,
        lanes=lanes,
    )
    return _overlay_tracked(loaded)


def _check_track(tool: Tool, where: str) -> None:
    if not tool.track:
        return
    if tool.track not in TRACK_MODES:
        raise ManifestError(f"{where}: track must be one of {sorted(TRACK_MODES)}")
    if not tool.ci_ref.get("repo"):
        raise ManifestError(f"{where}: track: ci_ref needs a ci_ref with repo")
    pattern = tool.ci_ref.get("extract", "")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise ManifestError(f"{where}: ci_ref.extract is not a regex ({exc})") from exc
    if not pattern or "version" not in compiled.groupindex:
        raise ManifestError(f"{where}: ci_ref.extract needs a (?P<version>...) group")
    if tool.method != "uv_tool" or not tool.package.startswith("git+"):
        raise ManifestError(f"{where}: only a git-pinned uv_tool can track its CI revision")


def _overlay_tracked(loaded: Manifest) -> Manifest:
    """Show each tracked tool at the version install.py recorded from CI."""
    state = loaded.read_state()
    tools = dict(loaded.tools)
    for name, tool in loaded.tools.items():
        entry = state.get(name) or {}
        version = str(entry.get("version") or "")
        if tool.track and entry.get("source") == "ci_ref" and TRACKED_VERSION.fullmatch(version):
            tools[name] = dataclasses.replace(tool, version=version, pinned=tool.version)
    return dataclasses.replace(loaded, tools=tools)


def disabled(env: dict[str, str] | None = None) -> bool:
    """The session kill switch: L9_CI_PARITY=0 disables every lane and hook."""
    source = os.environ if env is None else env
    return (source.get("L9_CI_PARITY") or "1").strip() == "0"
