"""SessionStart must pass the live binding proof, not invent bound/unbound."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = ROOT / "ops" / "hooks" / "session_start_bootstrap.sh"


def test_bootstrap_does_not_invent_memory_slogans() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "bound ($BINDING_STATUS)" not in text
    assert "exact|compatible|development_checkout" not in text
    assert "exact|development_checkout" not in text
    assert """.get('status','unbound')""" not in text
    assert """echo '{"status":"unbound"}'""" not in text
    assert "MEMORY_HEALTH=\"$HEALTH_JSON\"" in text
