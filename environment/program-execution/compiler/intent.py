"""Program Execution intent parsing and normalization (program-execution.intent.v1)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "intent.schema.json"

INTENT_ID_RE = re.compile(r"^INTENT-[A-Z0-9-]+$")


@dataclass(frozen=True)
class Intent:
    objective: str
    targets: tuple[str, ...] = ()
    policy_profile: str | None = None
    termination: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None

    @property
    def schema_name(self) -> str:
        return "program-execution.intent.v1"


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def parse_intent(raw: dict[str, Any]) -> Intent:
    """Validate raw user input against program-execution.intent.v1.

    Raises ValueError with a schema-violation summary when the input is not
    minimal (e.g. prescribes tasks, files, waves, worker prompts) or is
    otherwise malformed.
    """
    errors = sorted(
        Draft202012Validator(load_schema()).iter_errors(raw), key=lambda e: list(e.path)
    )
    if errors:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise ValueError(f"intent violates program-execution.intent.v1: {details}")
    termination = raw.get("termination")
    if termination is not None and "mode" not in termination:
        raise ValueError("intent.termination requires mode")
    return Intent(
        objective=_normalize_objective(str(raw["objective"])),
        targets=tuple(str(t) for t in raw.get("targets") or []),
        policy_profile=raw.get("policy_profile"),
        termination=dict(termination) if termination else None,
        constraints=dict(raw["constraints"]) if raw.get("constraints") else None,
    )


def _normalize_objective(objective: str) -> str:
    text = re.sub(r"\s+", " ", objective).strip()
    if not text:
        raise ValueError("intent.objective must not be empty")
    return text


def parse_intent_file(path: Path) -> Intent:
    import yaml

    return parse_intent(yaml.safe_load(path.read_text(encoding="utf-8")))


def intent_id(intent: Intent) -> str:
    """Deterministic INTENT id from the normalized objective (evidence of identity)."""
    import hashlib

    digest = hashlib.sha256(intent.objective.encode("utf-8")).hexdigest()[:12].upper()
    return f"INTENT-{digest}"


def to_dict(intent: Intent) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema": intent.schema_name,
        "objective": intent.objective,
    }
    if intent.targets:
        data["targets"] = list(intent.targets)
    if intent.policy_profile:
        data["policy_profile"] = intent.policy_profile
    if intent.termination:
        data["termination"] = intent.termination
    if intent.constraints:
        data["constraints"] = intent.constraints
    return data


__all__ = [
    "Intent",
    "INTENT_ID_RE",
    "intent_id",
    "load_schema",
    "parse_intent",
    "parse_intent_file",
    "to_dict",
]
