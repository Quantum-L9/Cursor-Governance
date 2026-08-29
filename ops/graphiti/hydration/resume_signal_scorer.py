"""Keep/drop for optional derived Graphiti episode writes.

Declared weights only — not a Bayesian engine. SessionHydrationPacket always
emits. archive_transcript is never filtered. Scorer exception → fail-open (write).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_RULES_PATH = Path(__file__).resolve().parent / "promotion_rules.yaml"
_FILE_RE = re.compile(r"[\w./-]+\.(?:py|md|ya?ml|json|sh|ts|tsx|js|jsx)")
_ACTION_RE = re.compile(r"\b(edit|wrote|commit|patch|implement|fix)\b", re.IGNORECASE)


def load_promotion_rules(path: Path | None = None) -> dict[str, Any]:
    try:
        import yaml

        return yaml.safe_load((path or _RULES_PATH).read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def score_resume_signals(signals: dict[str, Any], rules: dict[str, Any] | None = None) -> float:
    cfg = (rules or load_promotion_rules()).get("resume_signals") or {}
    actions = _clamp01(
        float(signals.get("action_count") or 0) / float(cfg.get("actions_divisor", 3))
    )
    files = _clamp01(float(signals.get("file_count") or 0) / float(cfg.get("files_divisor", 5)))
    decisions = _clamp01(
        float(signals.get("decision_count") or 0) / float(cfg.get("decisions_divisor", 2))
    )
    messages = _clamp01(
        float(signals.get("message_count") or 0) / float(cfg.get("messages_divisor", 10))
    )
    code = 1.0 if signals.get("code_present") else 0.0
    completion = (
        1.0 if signals.get("completed") else float(cfg.get("incomplete_completion_score", 0.3))
    )
    return (
        actions * float(cfg.get("actions_weight", 0.25))
        + files * float(cfg.get("files_weight", 0.20))
        + decisions * float(cfg.get("decisions_weight", 0.20))
        + messages * float(cfg.get("messages_weight", 0.15))
        + code * float(cfg.get("code_weight", 0.10))
        + completion * float(cfg.get("completion_weight", 0.10))
    )


def signals_from_close(
    *,
    transcript: str = "",
    reason: str = "",
    promotion_decisions: list[Any] | None = None,
) -> dict[str, Any]:
    text = transcript or ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    decisions = [
        item
        for item in (promotion_decisions or [])
        if isinstance(item, dict) and str(item.get("kind") or "") == "decision"
    ]
    action_hits = len(promotion_decisions or []) or len(_ACTION_RE.findall(text))
    return {
        "action_count": action_hits,
        "file_count": len(set(_FILE_RE.findall(text))),
        "decision_count": len(decisions),
        "message_count": len(lines),
        "code_present": "```" in text or bool(re.search(r"\b(def |class |function )", text)),
        "completed": reason == "completed",
    }


def should_persist_derived_episode(
    signals: dict[str, Any],
    rules: dict[str, Any] | None = None,
) -> bool:
    """False = drop optional derived write. Exception → True (fail-open)."""
    try:
        loaded = rules if rules is not None else load_promotion_rules()
        min_score = float(loaded.get("derived_episode_min_score", 0.35))
        return score_resume_signals(signals, loaded) >= min_score
    except Exception:  # noqa: BLE001
        return True
