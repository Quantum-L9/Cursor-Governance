"""Program action resolution: create | extend | supersede (contract §14, ADR-0011)."""

from __future__ import annotations

from typing import Any


def decide(existing: list[dict[str, Any]] | None, resolution: dict[str, Any]) -> dict[str, Any]:
    """Choose how the new request relates to accepted programs.

    - create: no accepted program governs the requested objective.
    - extend: work is already within an accepted program's authority and scope.
    - supersede: objective, authority, decisions, ceiling, targets, or
      convergence semantics materially change; a locked program must never be
      silently mutated (it is replaced with a new program that references its
      parent).
    """
    normalized = (resolution.get("intent") or {}).get("normalized_objective", "")
    for program in existing or []:
        if _governs(program, normalized):
            if _materially_changed(program, resolution):
                return {
                    "mode": "supersede",
                    "parent_program_ref": program.get("id"),
                    "reason": "material change to objective, authority, targets, or convergence",
                }
            return {
                "mode": "extend",
                "parent_program_ref": program.get("id"),
                "reason": "requested work is within the accepted program's authority and scope",
            }
    return {"mode": "create", "parent_program_ref": None}


def _governs(program: dict[str, Any], normalized_objective: str) -> bool:
    objective = program.get("objective") or ""
    identity = program.get("program_id") or program.get("id") or ""
    if not objective:
        return False
    if identity and identity.replace("-", " ") in normalized_objective.lower():
        return True
    tokens = {t for t in objective.lower().split() if len(t) > 3}
    if not tokens:
        return False
    return len(tokens & {t for t in normalized_objective.lower().split() if len(t) > 3}) >= 3


def _materially_changed(program: dict[str, Any], resolution: dict[str, Any]) -> bool:
    normalized = (resolution.get("intent") or {}).get("normalized_objective", "")
    objective = program.get("objective") or ""
    if objective and normalized and objective not in normalized and normalized not in objective:
        # Non-substring objectives govern the same space: an incremental
        # refinement (most prior tokens preserved) extends; anything less
        # materially changes the program.
        old_tokens = _tokens(objective)
        if old_tokens and _shared_tokens(objective, normalized) / len(old_tokens) < 0.6:
            return True
    targets = {t.get("repository_id") for t in resolution.get("targets") or []}
    program_targets = {
        t.get("repository_id") for t in (program.get("targets") or []) if t.get("repository_id")
    }
    if targets and program_targets and targets != program_targets:
        return True
    profile = (resolution.get("governing_authority") or {}).get("policy_profile")
    program_profile = (program.get("governing_authority") or {}).get("policy_profile")
    if profile and program_profile and profile != program_profile:
        return True
    return False


def _tokens(text: str) -> set[str]:
    return {t for t in text.lower().split() if len(t) > 3}


def _shared_tokens(left: str, right: str) -> int:
    return len(_tokens(left) & _tokens(right))


__all__ = ["decide"]
