"""Which agent is writing memory — DERIVED from the running process, never configured.

Every memory names the agent that wrote it (ADR-0031), and the operator must be
able to hold each surface accountable for what it wrote. The identity is
therefore derived at write time from markers the host itself sets on the
running process — never read from a hard-coded setting that can drift from
where the code is actually running:

    cursor        Cursor        CURSOR_AGENT is set and no Claude runtime
    claude-code   Claude Code   Claude Code markers. A live Claude runtime wins
                                over an inherited CURSOR_AGENT. Desktop, CLI,
                                and mobile are surfaces of this one actor,
                                not authors.
    manus         Manus         Manus host markers (MANUS_ADDON_*,
                                MANUS_GROUP_ENABLED, or RUNTIME_API_HOST on
                                manus.im). Manus is hosted: every such session
                                is the ``manus-cloud`` surface.

On a Cursor or Claude Code surface a static ``L9_MEMORY_AGENT_ID`` is IGNORED:
the host's own markers are the only evidence, so a pasted surface author
(``claude-code-desktop`` or ``claude-code-mobile``) can never mislabel a write.
:func:`static_drift` names such a value so SessionStart can report it.

Agents with no host markers of their own are identified by the
``L9_MEMORY_AGENT_ID`` their ADAPTER sets (never an operator's pasted value),
and only when it names one of ``manus``, ``codex``, or ``gemini``. Surface
stays unknown: an adapter id is actor evidence, not surface evidence. The
``manus`` adapter id alone therefore still yields no surface; only the host's
own markers do, and they yield ``manus-cloud``.

``perplexity``, ``perplexity-computer``, ``l-cto``, and ``igorbot`` are not
actors in the canonical registry. ``human`` is canonical and has no agent
binding here. None of those names resolve.

No guessing: Claude host markers prove the actor ``claude-code``, which has
exactly two surfaces (operator decision 2026-11-20). ``claude-code-cli`` is
the local CLI (``cli``, and ``claude-vscode`` for the CLI process inside an
IDE). ``claude-code-web`` is every hosted cloud session: ``CLAUDE_CODE_REMOTE=true``
with an observed hosted entrypoint (``remote_desktop``, observed 2026-11-20;
``remote_mobile``, a cloud session started from the phone). Every other
entrypoint, including a missing one, leaves the surface unknown.
``claude-code-desktop``, ``claude-code-ide`` and ``claude-code-mobile`` are
never assigned. ``claude-code-desktop`` and ``claude-code-mobile`` are
historical actor aliases of ``claude-code``; the same strings are not authors.
A live Claude runtime outranks an inherited
``CURSOR_AGENT``.

Pure: reads the mapping it is given, no I/O. ``python -m ops.memory.agent_identity``
prints the identity for the current process (exit 1 and a reason when none).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Mapping
from typing import Any, Final

CURSOR: Final = "cursor"
CLAUDE_ACTOR: Final = "claude-code"
MANUS: Final = "manus"
#: Every identity this resolver derives from host markers.
DERIVED_IDENTITIES: Final = frozenset({CURSOR, CLAUDE_ACTOR, MANUS})
CLAUDE_IDENTITIES: Final = frozenset({CLAUDE_ACTOR})
#: Adapter actors this plane resolves from ``L9_MEMORY_AGENT_ID`` when no host
#: marker is present. Surface stays unknown. ``human`` is canonical and unbound.
ADAPTER_IDENTITIES: Final = frozenset({"manus", "codex", "gemini"})
#: Actors this resolver emits. Role rows in the agent registry are not actors.
ALL_IDENTITIES: Final = DERIVED_IDENTITIES | ADAPTER_IDENTITIES
#: Retired surface authors. They name a surface of ``claude-code``, not an agent.
RETIRED: Final = frozenset({"claude-code-desktop", "claude-code-mobile"})
#: Read-compatibility fold for receipts and tags stamped before the surface/actor split.
#: A new write still refuses these names; see ``agent_write``.
HISTORICAL_ACTOR_ALIASES: Final = {name: CLAUDE_ACTOR for name in sorted(RETIRED)}
CURSOR_SURFACE: Final = "cursor-ide"
CLAUDE_CLI_SURFACE: Final = "claude-code-cli"
CLAUDE_WEB_SURFACE: Final = "claude-code-web"
#: Manus has exactly one canonical surface, the hosted cloud surface. There is
#: no manus-cli: the local shell a Manus session runs commands in is not a
#: separately registered interaction surface (surface_registry.yaml).
MANUS_SURFACE: Final = "manus-cloud"
#: Host-injected markers of the Manus runtime. They are the host's evidence,
#: not a configured label: an operator cannot set these from a project
#: instruction, and ``L9_MEMORY_AGENT_ID`` alone never produces a surface.
MANUS_MARKERS: Final = (
    "MANUS_ADDON_RUNTIME_SPEC_PATH",
    "MANUS_ADDON_REGISTRY_ENABLED",
    "MANUS_GROUP_ENABLED",
)
MANUS_RUNTIME_HOST: Final = "RUNTIME_API_HOST"
MANUS_APEX_DOMAIN: Final = "manus.im"
#: ``claude-vscode`` is the host marker for the CLI process inside an IDE.
#: It selects ``claude-code-cli``; there is no separate IDE surface.
LOCAL_ENTRYPOINTS: Final = {
    "cli": CLAUDE_CLI_SURFACE,
    "claude-vscode": CLAUDE_CLI_SURFACE,
}
#: Observed CLAUDE_CODE_ENTRYPOINT values of a hosted cloud session. Every
#: hosted session is Claude Code Web, whichever client drives it.
REMOTE_SURFACE_BY_ENTRYPOINT: Final = {
    "remote_desktop": CLAUDE_WEB_SURFACE,
    "remote_mobile": CLAUDE_WEB_SURFACE,
}
#: CLAUDE_CODE_ENTRYPOINT values of a cloud session this resolver admits.
REMOTE_ENTRYPOINTS: Final = frozenset(REMOTE_SURFACE_BY_ENTRYPOINT)
#: Local resolver identity. Cursor-Governance produces the assertion; memory verifies it.
RUNTIME_RESOLVER_REF: Final = "l9.cursor-governance/resolver/runtime-agent-identity@1"
ACTOR_REGISTRY_PREFIX: Final = "l9.actor-registry/global@1#"
SURFACE_REGISTRY_PREFIX: Final = "l9.surface-registry/global@1#"
UNKNOWN_IDENTITY: Final = "unknown"
MEMORY_PRODUCT_REF: Final = "l9-graphiti-memory:product/l9-graphite-memory"
#: Dependency-kind dimensions for the bound l9-graphite-memory 2.6.0 consumer.
#: The hosted-service exception adds runtime only from release 3.0.0 and does
#: not apply here. Constellation is outside both lists, so the key is omitted.
DEPENDENCY_IDENTITY_DIMENSIONS: Final = ("product_identity", "release_identity")
HOSTED_SERVICE_EXCEPTION_REF: Final = "l9.product-kind-exception/memory-hosted-service@1"
HOSTED_SERVICE_EXCEPTION_APPLIES_FROM: Final = "3.0.0"
#: Public OAuth client identifiers are not actors. They never select cursor
#: or claude-code, including when no host marker is present.
OAUTH_CLIENT_ENV_KEYS: Final = (
    "L9_MEMORY_OAUTH_CLIENT_ID",
    "AUTH0_CLIENT_ID",
    "OAUTH_CLIENT_ID",
)


class IdentityResolutionError(ValueError):
    """Actor or surface identity could not be taken from the binding without guessing."""


def _flag(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def _is_cursor(env: Mapping[str, str]) -> bool:
    return bool(_flag(env, "CURSOR_AGENT"))


def _is_claude(env: Mapping[str, str]) -> bool:
    return bool(
        _flag(env, "CLAUDECODE")
        or _flag(env, "CLAUDE_CODE_ENTRYPOINT")
        or _flag(env, "CLAUDE_CODE_SESSION_ID")
    )


def _authority_host(raw: str) -> str:
    """Lowercase hostname of an authority string, without a URL parser.

    ``ops/memory`` is boundary-pinned to the bound memory console's stdio
    (INV-03): no urllib, requests, socket, or HTTP client may be imported
    here, even for parsing. A host marker needs only the authority
    component, so a literal scan is sufficient and keeps the boundary
    intact. Returns "" when no host can be read.
    """

    text = raw.strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    for separator in ("/", "?", "#"):
        text = text.split(separator, 1)[0]
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    if text.startswith("["):
        closing = text.find("]")
        return text[1:closing].lower() if closing > 0 else ""
    return text.split(":", 1)[0].lower()


def _manus_api_host(env: Mapping[str, str]) -> str:
    """The hostname of ``RUNTIME_API_HOST`` when it is a manus.im host, else "".

    The apex is matched exactly and subdomains only with a dot boundary, so
    ``manus.im.evil.example`` is not a Manus host.
    """

    raw = _flag(env, MANUS_RUNTIME_HOST)
    if not raw:
        return ""
    hostname = _authority_host(raw)
    if hostname == MANUS_APEX_DOMAIN or hostname.endswith(f".{MANUS_APEX_DOMAIN}"):
        return hostname
    return ""


def _is_manus(env: Mapping[str, str]) -> bool:
    """True when the Manus host itself marked this process."""

    if any(_flag(env, name) for name in MANUS_MARKERS):
        return True
    return bool(_manus_api_host(env))


def _claude_identity(env: Mapping[str, str]) -> str:
    """Claude Code is one actor. An unrecognized surface stays unknown elsewhere.

    Desktop, CLI, web, and mobile share ``claude-code``. This function does
    not read ``L9_MEMORY_AGENT_ID`` or an OAuth public client id, and it does
    not relabel an unknown entrypoint as mobile.
    """

    if not _is_claude(env):
        return ""
    return CLAUDE_ACTOR


def canonical_actor_id(value: str | None) -> str:
    """Fold a retired surface-author tag to ``claude-code`` for receipt comparison.

    Call only on a value known to be an actor id. The same strings are surface
    names and must not be folded there.
    """
    actor = (value or "").strip()
    return HISTORICAL_ACTOR_ALIASES.get(actor, actor)


def resolve_identity_coordinates(
    env: Mapping[str, str] | None = None,
    oauth_claims: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Actor, surface, release, and runtime, each from its own evidence.

    An OAuth subject, client id, or audience is ignored. It cannot fill any
    coordinate. Release and runtime stay ``unknown`` until their owners publish
    a ref; this resolver does not mint one from a token.
    """

    source = os.environ if env is None else env
    claims = oauth_claims or {}
    ignored = sorted(
        key
        for key in claims
        if key in {"sub", "client_id", "azp", "aud", "release_identity", "runtime_identity"}
    )
    actor = resolve_agent_id(source)
    surface = resolve_surface_id(source)
    return {
        "actor_identity": actor or UNKNOWN_IDENTITY,
        "surface_identity": surface or UNKNOWN_IDENTITY,
        "release_identity": UNKNOWN_IDENTITY,
        "runtime_identity": UNKNOWN_IDENTITY,
        "ignored_oauth_claims": ignored,
        "oauth_subject_used": False,
        "oauth_client_id_used": False,
    }


def oauth_public_client_claim(env: Mapping[str, str] | None = None) -> str:
    """The first public OAuth client id in *env*, or "" when none is set.

    The value is not an actor. Callers must not map it to ``cursor`` or
    ``claude-code``.
    """

    source = os.environ if env is None else env
    for name in OAUTH_CLIENT_ENV_KEYS:
        claim = _flag(source, name)
        if claim:
            return claim
    return ""


def resolve_agent_id(env: Mapping[str, str] | None = None) -> str:
    """The writing agent's identity, derived from host markers; "" when unknown."""
    source = os.environ if env is None else env
    # A live Claude process wins over an inherited Cursor host marker. The IDE
    # panel sets both. Cursor with no Claude runtime stays cursor.
    if _is_claude(source):
        return _claude_identity(source)
    if _flag(source, "CLAUDE_CODE_REMOTE").lower() == "true":
        return CLAUDE_ACTOR
    if _is_cursor(source):
        return CURSOR
    # Manus sets its own markers on every hosted session; they outrank the
    # adapter's L9_MEMORY_AGENT_ID because they are host evidence, not a label.
    if _is_manus(source):
        return MANUS
    # A public OAuth client id is not an actor. It neither selects one nor
    # denies a registered adapter whose marker happens to equal that string.
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    return explicit if explicit in ADAPTER_IDENTITIES else ""


def resolve_surface_id(env: Mapping[str, str] | None = None) -> str:
    """The surface of this process, derived from host markers; "" when unknown."""
    source = os.environ if env is None else env
    claude = _is_claude(source) or _flag(source, "CLAUDE_CODE_REMOTE").lower() == "true"
    if not claude and _is_cursor(source):
        return CURSOR_SURFACE
    # Manus is hosted only: its host markers prove the cloud surface. A bare
    # adapter id is not surface evidence and still returns "" below.
    if not claude and _is_manus(source):
        return MANUS_SURFACE
    if not claude:
        return ""
    entry = _flag(source, "CLAUDE_CODE_ENTRYPOINT").lower()
    if _flag(source, "CLAUDE_CODE_REMOTE").lower() == "true":
        return REMOTE_SURFACE_BY_ENTRYPOINT.get(entry, "")
    return LOCAL_ENTRYPOINTS.get(entry, "")


def static_drift(env: Mapping[str, str] | None = None) -> str:
    """A configured L9_MEMORY_AGENT_ID that disagrees with the derived identity, or ""."""
    source = os.environ if env is None else env
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    if not explicit or not (_is_cursor(source) or _is_claude(source) or _is_manus(source)):
        return ""
    return explicit if explicit != resolve_agent_id(source) else ""


def unresolved_reason(env: Mapping[str, str] | None = None) -> str:
    """Why no identity could be derived (for a loud refusal), or ""."""
    source = os.environ if env is None else env
    if resolve_agent_id(source):
        return ""
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    if explicit in DERIVED_IDENTITIES:
        return f"L9_MEMORY_AGENT_ID={explicit} is derived from host markers, never configured"
    if explicit in RETIRED:
        return (
            f"L9_MEMORY_AGENT_ID={explicit} is a retired surface author; "
            f"the actor is {CLAUDE_ACTOR}"
        )
    if explicit:
        known = ", ".join(sorted(ALL_IDENTITIES))
        return f"L9_MEMORY_AGENT_ID={explicit} is not a registered memory identity (known: {known})"
    return "no host markers (CURSOR_AGENT / Claude Code / Manus) and no L9_MEMORY_AGENT_ID"


def normalized_runtime_evidence(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Facts that drive actor/surface resolution, with secrets and session ids removed.

    ``CLAUDE_CODE_SESSION_ID`` contributes only as a presence boolean. Adapter
    ``L9_MEMORY_AGENT_ID`` is included only when host markers did not already
    decide the actor.
    """

    source = os.environ if env is None else env
    cursor_present = _is_cursor(source)
    claude_present = _is_claude(source)
    manus_present = _is_manus(source)
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    adapter_id = ""
    if (
        not cursor_present
        and not claude_present
        and not manus_present
        and explicit in ADAPTER_IDENTITIES
    ):
        adapter_id = explicit
    return {
        "CURSOR_AGENT_present": cursor_present,
        "claude_markers_present": claude_present,
        "manus_markers_present": manus_present,
        "manus_runtime_api_host": _manus_api_host(source),
        "CLAUDE_CODE_REMOTE": _flag(source, "CLAUDE_CODE_REMOTE").lower() == "true",
        "CLAUDE_CODE_ENTRYPOINT": _flag(source, "CLAUDE_CODE_ENTRYPOINT").lower(),
        "CLAUDE_CODE_SESSION_ID_present": bool(_flag(source, "CLAUDE_CODE_SESSION_ID")),
        "L9_MEMORY_AGENT_ID": adapter_id,
    }


def runtime_evidence_digest(evidence: Mapping[str, Any]) -> str:
    """SHA-256 of the normalized evidence object. Same canonical JSON as the assertion digest."""

    payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def actor_ref_from_binding(actor_id: str, binding: Mapping[str, Any]) -> str:
    """The binding's ``actor_ref``. The fragment must already be the resolved actor id."""

    ref = binding.get("actor_ref")
    if not isinstance(ref, str) or not ref.startswith(ACTOR_REGISTRY_PREFIX):
        raise IdentityResolutionError(f"binding for {actor_id} has no canonical actor_ref")
    fragment = ref[len(ACTOR_REGISTRY_PREFIX) :]
    if not fragment or fragment != actor_id:
        raise IdentityResolutionError(
            f"binding actor_ref {ref} does not name resolved actor {actor_id}"
        )
    return ref


def surface_ref_from_binding(surface_id: str, binding: Mapping[str, Any]) -> str:
    """A bound canonical surface ref, or ``unknown`` when none is bound.

    An empty surface id is unknown. A local surface id that is not one of this
    actor's ``surface_refs`` is also unknown: another bound surface is not a
    guess, and an unbound coordinate is not emitted.
    """

    if not surface_id:
        return UNKNOWN_IDENTITY
    candidate = f"{SURFACE_REGISTRY_PREFIX}{surface_id}"
    refs = binding.get("surface_refs")
    if isinstance(refs, list) and candidate in refs:
        return candidate
    # A local surface id that this actor does not bind is not evidence of a
    # canonical surface. Do not substitute another bound surface.
    return UNKNOWN_IDENTITY


def user_id_for(agent_id: str) -> str:
    """The registry's USER_ID convention (validate_agents R3), derived from the identity."""
    return f"{agent_id.replace('-', '_')}_agent"


def main() -> int:
    agent_id = resolve_agent_id()
    if agent_id:
        print(agent_id)
        return 0
    print(f"no memory identity: {unresolved_reason()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
