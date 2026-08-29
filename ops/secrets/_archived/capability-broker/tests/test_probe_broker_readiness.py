"""Authenticated-readiness semantics for ops/secrets/probe_broker.py.

TCP reachability is not health. A broker that answers /healthz but rejects the
session identity at /whoami is NOT READY; a broker that verifies the identity
is. These tests drive probe_broker.run() with a stubbed env + monkeypatched
network primitives — no sockets, no real broker, no credentials.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

try:
    import probe_broker as pb  # noqa: E402
    from capability_client import SessionIdentity  # noqa: E402
except ImportError as exc:  # pragma: no cover - ABI/edge only
    pytest.skip(f"probe broker imports unavailable: {exc}", allow_module_level=True)


def _patch(monkeypatch, *, identity, dns="resolves", health="http_200", whoami="http_200"):
    monkeypatch.setattr(pb, "session_identity", lambda env=None: identity)
    monkeypatch.setattr(pb, "broker_url", lambda env=None: "https://broker.example/l9")
    monkeypatch.setattr(pb, "dns_state", lambda host: dns)
    monkeypatch.setattr(pb, "health_state", lambda url, timeout=pb.TIMEOUT: health)
    monkeypatch.setattr(pb, "readiness_state", lambda url, token, timeout=pb.TIMEOUT: whoami)


def _available(token: str = "s.jwt") -> SessionIdentity:
    return SessionIdentity("ccr-session-jwt", token, "self-hosted pool ccpool_test")


def _unavailable() -> SessionIdentity:
    return SessionIdentity(
        "none",
        None,
        "hosted surface issues no identity",
        reason="hosted_surface_issues_no_session_identity",
        remediation="none_available_in_repo",
    )


def test_verified_identity_is_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, identity=_available(), whoami="http_200")
    result = pb.run(env={})
    assert result["authenticated_readiness"] == "http_200"
    assert result["primary_blocker"] == pb.NONE
    assert result["ok"] is True


def test_reachable_but_identity_rejected_is_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    # /healthz 200 (reachable) but /whoami 401 (identity rejected) → NOT READY.
    # This is the reachability-is-not-health case the readiness gate exists for.
    _patch(monkeypatch, identity=_available(), health="http_200", whoami="http_401")
    result = pb.run(env={})
    assert result["health"] == "http_200"
    assert result["authenticated_readiness"] == "http_401"
    assert result["primary_blocker"] == pb.IDENTITY
    assert result["ok"] is False


def test_no_identity_is_identity_blocker(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, identity=_unavailable())
    result = pb.run(env={})
    assert result["primary_blocker"] == pb.IDENTITY
    assert result["ok"] is False
    # No authenticated probe is even attempted without a token.
    assert "authenticated_readiness" not in result


def test_no_dns_record_is_reachability_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, identity=_available(), dns="no_dns_record")
    result = pb.run(env={})
    assert result["primary_blocker"] == pb.REACHABILITY
    assert result["ok"] is False
    # The broker never resolved, so no authenticated readiness was claimed.
    assert "authenticated_readiness" not in result


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
