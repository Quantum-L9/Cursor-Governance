"""CWE-939: skill fetchers never hand URLs to urllib.urlopen."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "lib"))

import safe_https  # noqa: E402
from safe_https import require_exchange_url, require_https_url  # noqa: E402

_FETCHERS = (
    REPO / "skills" / "l9-pr-remediation" / "scripts" / "codeql_fetch.py",
    REPO / "skills" / "l9-pr-remediation" / "scripts" / "sonar_fetch.py",
    REPO / "skills" / "l9-issue-remediation" / "scripts" / "post_issue_comment.py",
    REPO / "ops" / "lib" / "safe_https.py",
    REPO / "ops" / "secrets" / "port_aws_to_infisical.py",
    REPO / "ops" / "secrets" / "capability_client.py",
    REPO / "ops" / "scripts" / "validate_gh_package_deps.py",
    REPO / "ops" / "scripts" / "probe_network_posture.py",
    REPO / "ops" / "scripts" / "emit_claude_readiness.py",
    REPO / "ops" / "graphiti" / "prune.py",
    REPO / "environment" / "program-execution" / "scripts" / "context7_stack_proof.py",
    REPO / "environment" / "agents" / "generated-data" / "adapters" / "graphiti_memory.py",
)


def test_fetchers_do_not_call_urllib_urlopen() -> None:
    for path in _FETCHERS:
        src = path.read_text(encoding="utf-8")
        assert "urllib.request.urlopen" not in src
        assert "from urllib.request import urlopen" not in src


def test_require_https_url_rejects_file_and_http() -> None:
    hosts = frozenset({"api.github.com"})
    with pytest.raises(ValueError, match="non-https"):
        require_https_url("file:///etc/passwd", allowed_hosts=hosts)
    with pytest.raises(ValueError, match="non-https"):
        require_https_url("http://api.github.com/repos", allowed_hosts=hosts)


def test_require_https_url_rejects_wrong_host_and_userinfo() -> None:
    hosts = frozenset({"api.github.com"})
    with pytest.raises(ValueError, match="host"):
        require_https_url("https://evil.example/x", allowed_hosts=hosts)
    with pytest.raises(ValueError, match="userinfo"):
        require_https_url("https://user:pass@api.github.com/x", allowed_hosts=hosts)


def test_require_https_url_accepts_allowlisted_https() -> None:
    url = require_https_url(
        "https://api.github.com/repos/a/b",
        allowed_hosts=frozenset({"api.github.com"}),
    )
    assert url.startswith("https://api.github.com/")


def test_tls12_context_refuses_legacy_protocols() -> None:
    import ssl

    from safe_https import tls12_context

    ctx = tls12_context()
    assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_require_exchange_url_allows_loopback_http_only() -> None:
    assert require_exchange_url(
        "http://127.0.0.1:8100/mcp",
        allow_loopback_http=True,
    ).startswith("http://")
    with pytest.raises(ValueError, match="scheme"):
        require_exchange_url("file:///etc/passwd", allow_loopback_http=True)
    with pytest.raises(ValueError, match="non-loopback"):
        require_exchange_url("http://example.com/x", allow_loopback_http=True)


# --- Proxy awareness ----------------------------------------------------------
# A raw socket silently ignores HTTPS_PROXY. In a hosted container where all
# egress is brokered, that made a health probe measure a path no real client
# takes: the probe reached the origin directly while every genuine client was
# refused at the proxy, so a blocked host reported healthy.


def test_proxy_is_used_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:8080")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    assert safe_https.proxy_for_https("example.com") == "http://proxy.internal:8080"


def test_no_proxy_exempts_exact_host(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "example.com,other.test")
    assert safe_https.proxy_for_https("example.com") is None
    assert safe_https.proxy_for_https("elsewhere.test") is not None


def test_no_proxy_suffix_and_wildcard(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", ".svc.cluster.local,*.internal.test")
    assert safe_https.proxy_for_https("api.svc.cluster.local") is None
    assert safe_https.proxy_for_https("db.internal.test") is None
    assert safe_https.proxy_for_https("public.example") is not None


def test_no_proxy_cidr_entries_do_not_exempt_names(monkeypatch) -> None:
    """CIDR entries scope IP literals; every caller here dials a DNS name."""
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "10.0.0.0/8,172.16.0.0/12")
    assert safe_https.proxy_for_https("example.com") is not None


def test_absent_proxy_means_direct_dial(monkeypatch) -> None:
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)
    assert safe_https.proxy_for_https("example.com") is None
