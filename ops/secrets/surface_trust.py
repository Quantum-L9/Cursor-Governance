#!/usr/bin/env python3
"""Trust classification for agent surfaces — the boundary every secret path obeys.

One question is asked here and nowhere else: *is this caller inside a
model-controlled runtime?* Everything in ``ops/secrets`` that could return a
secret value routes through :func:`classify` first, so the answer cannot drift
between the shell bootstrap, the Python provider and the capability plane.

Two trust classes, and no third:

``MODEL_CONTROLLED``
    Claude Code, Codex, Gemini, Manus, Cursor, the generic adapter — anything
    where an LLM chooses what executes. Raw secret material MUST NOT be
    delivered here. The runtime is assumed capable of reading its own
    environment, filesystem, process table and child-process environment, so a
    secret placed in it is a secret the model possesses. Such a caller receives
    *capabilities*, never values.

``TRUSTED_OPERATOR``
    A human at a terminal, or a broker/worker process that has already proven
    it is outside the model boundary. Retains raw resolution.

Default-deny is the whole point: an unknown surface classifies as
``MODEL_CONTROLLED``. Trust is never inferred from the *absence* of a known id,
because that is exactly how a new adapter would silently acquire secret access
(contract R2). Adding a surface means adding it to ``MODEL_SURFACES`` — which
grants nothing — and operator trust must be claimed explicitly and proven.

Even an explicit ``--surface operator`` claim is not taken at face value: an
LLM can pass that flag as easily as an operator can. :func:`classify` therefore
audits the *runtime* for model-control markers (CLAUDECODE, CURSOR_AGENT, the
CCR remote session vars, ...) and refuses to honour an operator claim made from
inside one. A shell that Claude can spawn cannot promote itself.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

MODEL_CONTROLLED = "model-controlled"
TRUSTED_OPERATOR = "trusted-operator"

#: Registered model-controlled surface ids. Membership grants NOTHING; it exists
#: so a known surface is reported by name rather than as "unknown". Unregistered
#: ids are treated identically (deny), never more permissively.
MODEL_SURFACES = frozenset(
    {
        "claude-code",
        "claude-cli",
        "codex",
        "cursor",
        "gemini",
        "generic",
        "manus",
    }
)

#: The only ids that may *claim* operator trust. The claim is still audited.
OPERATOR_SURFACES = frozenset({"operator", "broker", "trusted-worker"})

#: Environment markers that prove a model-controlled runtime regardless of the
#: surface id a caller passes. Presence of any one of these makes an operator
#: claim a lie, so the claim is refused and the caller is pinned to
#: MODEL_CONTROLLED. Value is irrelevant — only whether the name is set and
#: non-empty — so none of these is ever read for content.
MODEL_RUNTIME_MARKERS = (
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_REMOTE",
    "CURSOR_AGENT",
    "CURSOR_TRACE_ID",
    "CODEX_SANDBOX",
    "GEMINI_CLI",
    "MANUS_AGENT",
    "AI_AGENT",
)


@dataclass(frozen=True)
class SurfaceTrust:
    """The decision, plus enough context for an audit record.

    ``raw_secret_allowed`` is the only field a caller should branch on. It is
    deliberately not derived at the call site: one place decides, everywhere
    else obeys.
    """

    surface: str
    trust_class: str
    raw_secret_allowed: bool
    reason: str
    markers: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_model_controlled(self) -> bool:
        return self.trust_class == MODEL_CONTROLLED


def detected_model_markers(env: dict[str, str] | None = None) -> tuple[str, ...]:
    """Names (never values) of model-runtime markers present in ``env``."""
    source = os.environ if env is None else env
    return tuple(name for name in MODEL_RUNTIME_MARKERS if (source.get(name) or "").strip())


def classify(surface: str | None = None, env: dict[str, str] | None = None) -> SurfaceTrust:
    """Classify a caller. Unknown and unset both mean ``MODEL_CONTROLLED``.

    ``surface`` falls back to ``L9_GOVERNANCE_SURFACE`` and then to the literal
    ``"unknown"`` — never to a permissive default.
    """
    source = os.environ if env is None else env
    resolved = (surface or source.get("L9_GOVERNANCE_SURFACE") or "unknown").strip().lower()
    markers = detected_model_markers(source)

    if resolved in OPERATOR_SURFACES:
        if markers:
            # An operator claim raised from inside a model runtime. This is the
            # exact escalation the boundary exists to stop, so it is refused
            # loudly rather than downgraded quietly.
            return SurfaceTrust(
                surface=resolved,
                trust_class=MODEL_CONTROLLED,
                raw_secret_allowed=False,
                reason=(
                    f"surface '{resolved}' claimed operator trust from inside a "
                    f"model-controlled runtime ({', '.join(markers)}); claim refused"
                ),
                markers=markers,
            )
        return SurfaceTrust(
            surface=resolved,
            trust_class=TRUSTED_OPERATOR,
            raw_secret_allowed=True,
            reason=f"surface '{resolved}' is a registered trusted-operator class",
            markers=markers,
        )

    if resolved in MODEL_SURFACES:
        reason = f"surface '{resolved}' is a registered model-controlled agent surface"
    else:
        reason = (
            f"surface '{resolved}' is not registered; unknown surfaces are "
            "model-controlled by default (trust is never inferred from absence)"
        )

    return SurfaceTrust(
        surface=resolved,
        trust_class=MODEL_CONTROLLED,
        raw_secret_allowed=False,
        reason=reason,
        markers=markers,
    )


def require_trusted(surface: str | None = None, env: dict[str, str] | None = None) -> SurfaceTrust:
    """Return the trust decision, raising ``PermissionError`` unless trusted.

    The guard used by every value-returning code path in ``ops/secrets``. The
    message names the surface and the refusal reason and never names a secret.
    """
    trust = classify(surface, env)
    if not trust.raw_secret_allowed:
        raise PermissionError(
            f"DENIED: raw secret export is prohibited on model-controlled surfaces "
            f"({trust.reason})"
        )
    return trust


__all__ = [
    "MODEL_CONTROLLED",
    "MODEL_RUNTIME_MARKERS",
    "MODEL_SURFACES",
    "OPERATOR_SURFACES",
    "TRUSTED_OPERATOR",
    "SurfaceTrust",
    "classify",
    "detected_model_markers",
    "require_trusted",
]
