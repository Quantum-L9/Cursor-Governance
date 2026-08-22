"""CWE-939: skill fetchers never hand URLs to urllib.urlopen."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "lib"))

from safe_https import require_exchange_url, require_https_url  # noqa: E402

_FETCHERS = (
    REPO / "skills" / "l9-pr-remediation" / "scripts" / "codeql_fetch.py",
    REPO / "skills" / "l9-pr-remediation" / "scripts" / "sonar_fetch.py",
    REPO / "skills" / "l9-issue-remediation" / "scripts" / "post_issue_comment.py",
    REPO / "ops" / "lib" / "safe_https.py",
    REPO / "ops" / "secrets" / "probe_broker.py",
    REPO / "ops" / "secrets" / "port_aws_to_infisical.py",
    REPO / "ops" / "secrets" / "capability_client.py",
    REPO / "ops" / "secrets" / "capability_broker.py",
    REPO / "ops" / "secrets" / "broker_identity.py",
    REPO / "ops" / "scripts" / "validate_gh_package_deps.py",
    REPO / "ops" / "scripts" / "probe_network_posture.py",
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
