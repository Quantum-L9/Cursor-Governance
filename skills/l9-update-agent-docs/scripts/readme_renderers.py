#!/usr/bin/env python3
"""Kind-specific README renderers owned by l9-update-agent-docs.

One closed-world renderer per documentation kind. A section is emitted
only when the model carries content for it, so a README shrinks as its
evidence thins instead of growing placeholders that say a directory has
no classes, no functions, no exports and no imports.

The renderer never consults the filesystem and never re-derives a fact:
it projects a :class:`ReadmeModel`, and target identity comes from
:attr:`ReadmeTarget.path` so configuration cannot make a README claim a
directory it does not describe.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from readme_evidence import (
    CORPUS_TYPE_LABELS,
    MAX_INTERFACES_PER_MODULE,
    MAX_MODULES_RENDERED,
)
from readme_model import DependencyDoc, ModuleDoc, ReadmeKind, ReadmeModel

__all__ = [
    "GENERATOR_NAME",
    "LEGACY_FOLDER_MARKER",
    "LEGACY_MARKERS",
    "LEGACY_MODULE_MARKER",
    "MARKER_PREFIX",
    "MARKER_VERSION",
    "RENDERERS",
    "UNREADABLE_MARKER_VERSION",
    "marker_for",
    "marker_kind",
    "marker_version",
    "owns_any_marker",
    "owns_marker",
    "render_readme",
]

GENERATOR_NAME = "l9-update-agent-docs"
MARKER_VERSION = 2
#: Reported by :func:`marker_version` for an owned marker whose ``version=``
#: token is not an integer. It is deliberately not a version number: the only
#: safe reading of an unreadable version is "newer than anything this
#: compiler understands", so the planner must treat it as a conflict rather
#: than compare it.
UNREADABLE_MARKER_VERSION = -1
#: Ownership is identified by generator and format version, not by the
#: technique that happened to produce the bytes. `generated-from-ast` made
#: the extraction method part of the identity; AST is evidence, not format.
MARKER_PREFIX = "<!-- l9-readme: generated-by="
#: Version-1 markers. Still strong ownership: this generator wrote them,
#: so a stale one may be retired and a live one migrates on refresh.
LEGACY_MODULE_MARKER = "<!-- l9-module-readme: generated-from-ast -->"
LEGACY_FOLDER_MARKER = "<!-- l9-folder-readme: generated-from-tree -->"
LEGACY_MARKERS = (LEGACY_MODULE_MARKER, LEGACY_FOLDER_MARKER)


def marker_for(kind: str) -> str:
    return f"{MARKER_PREFIX}{GENERATOR_NAME} version={MARKER_VERSION} kind={kind} -->"


def _marker_body(text: str) -> str | None:
    """Inner text of the last well-formed current-format marker.

    Ownership is decided by a *complete* marker comment, not by the prefix
    appearing anywhere in the file. A document that quotes the prefix while
    explaining the format — this module's own docs, a README describing the
    convention — would otherwise be classified as generator-owned and become
    eligible for refresh or retirement, which is an overwrite of handwritten
    work.

    Well-formed means: the prefix, a ``-->`` closing it on the same line, and
    a ``version=`` token inside. The version is not parsed here — a marker
    carrying a version this compiler cannot read is still this generator's
    marker, and is reported as a conflict rather than silently disowned.

    The last occurrence wins because the marker is written as the final line,
    so an example quoted earlier in a generated file cannot outrank it.
    """
    opener = f"{MARKER_PREFIX}{GENERATOR_NAME} "
    search_from = len(text)
    while True:
        start = text.rfind(opener, 0, search_from)
        if start == -1:
            return None
        search_from = start
        end = text.find("-->", start)
        if end != -1:
            body = text[start:end]
            if "\n" not in body and any(token.startswith("version=") for token in body.split()):
                return body
        if start == 0:
            return None


def owns_marker(text: str) -> bool:
    """True for a well-formed current-format marker only."""
    return _marker_body(text) is not None


def owns_any_marker(text: str) -> bool:
    """True for any marker this generator has ever written."""
    return owns_marker(text) or any(marker in text for marker in LEGACY_MARKERS)


def _marker_token(text: str, key: str) -> str | None:
    body = _marker_body(text)
    if body is None:
        return None
    for token in body.split():
        if token.startswith(f"{key}="):
            return token[len(key) + 1 :] or None
    return None


def marker_kind(text: str) -> str | None:
    """Kind recorded in an owned README's marker, if it carries one."""
    return _marker_token(text, "kind")


def marker_version(text: str) -> int | None:
    """Format version recorded in an owned README's marker.

    A version this compiler does not know belongs to a newer generator.
    Rewriting or deleting its output silently is how a rollback quietly
    destroys work, so the planner reports it rather than acting.

    Three outcomes, and conflating any two of them reopens that hole:
    an integer is a version this compiler can compare; ``None`` means the
    file carries no marker of this generator's at all; and
    :data:`UNREADABLE_MARKER_VERSION` means it carries one whose version
    token is not an integer — a newer format, not an absent claim.
    """
    raw = _marker_token(text, "version")
    if raw is None:
        return 1 if any(marker in text for marker in LEGACY_MARKERS) else None
    try:
        return int(raw)
    except ValueError:
        return UNREADABLE_MARKER_VERSION


def _join(blocks: Sequence[str]) -> str:
    """Join non-empty blocks with exactly one blank line between them."""
    body = "\n\n".join(block.strip("\n") for block in blocks if block and block.strip())
    return body.rstrip("\n") + "\n"


def _section(heading: str, body: str | None) -> str:
    if not body or not body.strip():
        return ""
    return f"## {heading}\n\n{body.strip()}"


def _header(model: ReadmeModel) -> str:
    target = model.target
    return f"# {target.title}\n\n**Path:** `{target.path}` | **Kind:** {target.kind}"


def _interface_lines(module: ModuleDoc) -> list[str]:
    lines: list[str] = []
    for cls in module.classes[:MAX_INTERFACES_PER_MODULE]:
        suffix = f" — {cls.summary}" if cls.summary else ""
        lines.append(f"- `{cls.name}`{suffix}")
    remaining = MAX_INTERFACES_PER_MODULE - len(lines)
    for func in module.functions[: max(remaining, 0)]:
        suffix = f" — {func.summary}" if func.summary else ""
        lines.append(f"- `{func.signature or func.name}`{suffix}")
    hidden = (len(module.classes) + len(module.functions)) - len(lines)
    if hidden > 0:
        lines.append(f"- _+{hidden} more public symbol(s)_")
    return lines


def _modules_block(modules: Sequence[ModuleDoc]) -> str:
    blocks: list[str] = []
    for module in modules[:MAX_MODULES_RENDERED]:
        parts = [f"### `{module.file}`"]
        if module.purpose:
            parts.append(module.purpose)
        lines = _interface_lines(module)
        if lines:
            parts.append("\n".join(lines))
        if module.exports:
            shown = ", ".join(f"`{name}`" for name in module.exports[:12])
            extra = f" (+{len(module.exports) - 12} more)" if len(module.exports) > 12 else ""
            parts.append(f"Exports: {shown}{extra}")
        blocks.append("\n\n".join(parts))
    if len(modules) > MAX_MODULES_RENDERED:
        hidden = len(modules) - MAX_MODULES_RENDERED
        blocks.append(f"_+{hidden} further module(s) in this directory._")
    return "\n\n".join(blocks)


def _dependencies_block(dependencies: DependencyDoc) -> str:
    lines: list[str] = []
    if dependencies.internal:
        lines.append("**Internal:** " + ", ".join(f"`{name}`" for name in dependencies.internal))
    if dependencies.external:
        lines.append("**External:** " + ", ".join(f"`{name}`" for name in dependencies.external))
    return "\n\n".join(lines)


def _shell_block(entrypoints: Sequence[str]) -> str:
    if not entrypoints:
        return ""
    return "\n".join(f"- `{name}`" for name in entrypoints)


def render_skill_readme(model: ReadmeModel) -> str:
    """Orientation for a skill pack. `SKILL.md` remains the contract."""
    components: list[str] = []
    for child in model.children:
        components.append(f"- [`{child}/`]({child}/)")
    authority = (
        "`SKILL.md` in this directory is the authoritative operating contract. "
        "This README is a navigation projection of it and never outranks it."
    )
    return _join(
        [
            _header(model),
            _section("Purpose", model.purpose),
            _section("Responsibilities", "\n".join(f"- {item}" for item in model.responsibilities)),
            _section("Key components", "\n".join(components)),
            _section("Entrypoints", _shell_block(model.shell_entrypoints)),
            _section("Authority", authority),
            marker_for(model.target.kind),
        ]
    )


def render_module_readme(model: ReadmeModel) -> str:
    """A single-module directory: its own public surface, nothing more."""
    interfaces = ""
    if model.modules:
        lines: list[str] = []
        for module in model.modules:
            lines.extend(_interface_lines(module))
        interfaces = "\n".join(lines)
    return _join(
        [
            _header(model),
            _section("Purpose", model.purpose),
            _section("Description", model.description),
            _section("Public interface", interfaces),
            _section("Entrypoints", _shell_block(model.shell_entrypoints)),
            _section("Dependencies", _dependencies_block(model.dependencies)),
            marker_for(model.target.kind),
        ]
    )


def render_subsystem_readme(model: ReadmeModel) -> str:
    """Several modules: module identity is preserved, never flattened."""
    return _join(
        [
            _header(model),
            _section("Purpose", model.purpose),
            _section("Description", model.description),
            _section("Modules", _modules_block(model.modules)),
            _section("Entrypoints", _shell_block(model.shell_entrypoints)),
            _section("Dependencies", _dependencies_block(model.dependencies)),
            marker_for(model.target.kind),
        ]
    )


def render_corpus_readme(model: ReadmeModel) -> str:
    """A document/config folder. The file inventory is itself the value."""
    contents = "\n".join(
        f"- `{name}`" + (f" — {label}" if (label := _type_label(name)) else "")
        for name in model.contents
    )
    file_types = "\n".join(f"- {label}: {count}" for label, count in model.file_types)
    return _join(
        [
            _header(model),
            _section("Purpose", model.purpose),
            _section("Description", model.description),
            _section("Contents", contents),
            _section("File types", file_types),
            marker_for(model.target.kind),
        ]
    )


def _type_label(name: str) -> str | None:
    suffix = name[name.rfind(".") :].lower() if "." in name else ""
    return CORPUS_TYPE_LABELS.get(suffix)


def render_index_readme(model: ReadmeModel) -> str:
    """A structural parent. No invented purpose; the children are the point."""
    children = "\n".join(f"- [`{name}/`]({name}/)" for name in model.children)
    files = "\n".join(
        f"- `{name}`" + (f" — {label}" if (label := _type_label(name)) else "")
        for name in model.contents
    )
    return _join(
        [
            _header(model),
            _section("Purpose", model.purpose),
            _section("Description", model.description),
            _section("Contents", children),
            _section("Files", files),
            marker_for(model.target.kind),
        ]
    )


RENDERERS: dict[ReadmeKind, Callable[[ReadmeModel], str]] = {
    "skill": render_skill_readme,
    "module": render_module_readme,
    "subsystem": render_subsystem_readme,
    "corpus": render_corpus_readme,
    "index": render_index_readme,
}


def render_readme(model: ReadmeModel) -> str:
    renderer = RENDERERS.get(model.target.kind)
    if renderer is None:
        raise ValueError(f"no renderer for README kind {model.target.kind!r}")
    return renderer(model)
