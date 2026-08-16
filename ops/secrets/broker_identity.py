#!/usr/bin/env python3
"""Session-identity verification for the L9 capability broker (contract §5).

Runs on the TRUSTED side only. The broker uses this to decide whether an
inbound capability request really comes from an L9 Claude session worker, or
from something wearing its name.

The rule that shapes every line below: a caller-supplied token is *evidence*,
never *authority*. Nothing here trusts a claim because it is present. The
signature is checked against the issuer's published keys, and then each claim
the contract names is checked for the exact expected value:

    prefix/type      is this even a JWT of the right type
    alg == ES256     pinned; `none` and HMAC confusion are rejected outright
    signature        ES256 over header.payload against the Anthropic JWKS
    iss == ccr       issued by the CCR control plane
    aud contains     the exact ccpool_<environment> this broker serves
    ccr:role         session_worker
    exp              unexpired, with a bounded clock skew
    ccr:org_id       the expected organization
    ccr:session_id   present, so the request is attributable

A token that is valid but audienced to a *different* pool is rejected: that is
the cross-environment case (T5), and accepting it would let one deployment's
sessions borrow another's capabilities.

The verified JWT is never logged and never returned. :func:`verify` yields an
:class:`SessionClaims` carrying identifiers for the audit record only — the
contract's list (session_id, jti, org_id, account_id) and nothing else (§5).
"""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256

EXPECTED_ISSUER = "ccr"
EXPECTED_ROLE = "session_worker"
EXPECTED_ALG = "ES256"
DEFAULT_JWKS_URL = "https://claude.ai/.well-known/ccr-jwks.json"
CLOCK_SKEW_SECONDS = 60
JWKS_CACHE_SECONDS = 300


class IdentityError(Exception):
    """Verification failed. The message names the reason, never the token."""


@dataclass(frozen=True)
class SessionClaims:
    """Audit-safe identifiers extracted from a verified assertion."""

    session_id: str
    jti: str
    org_id: str
    account_id: str
    audience: str
    role: str
    expires_at: int

    def audit_record(self) -> dict[str, Any]:
        """Exactly the fields contract §5 says to record. No token, ever."""
        return {
            "ccr:session_id": self.session_id,
            "jti": self.jti,
            "ccr:org_id": self.org_id,
            "ccr:account_id": self.account_id,
            "ccr:role": self.role,
            "audience": self.audience,
        }


def _b64url(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


class JWKSCache:
    """Small TTL cache so verification does not fetch keys per request."""

    def __init__(self, url: str = DEFAULT_JWKS_URL, ttl: int = JWKS_CACHE_SECONDS) -> None:
        self.url = url
        self.ttl = ttl
        self._keys: dict[str, ec.EllipticCurvePublicKey] = {}
        self._fetched_at = 0.0

    def get(self, kid: str, *, now: float | None = None) -> ec.EllipticCurvePublicKey:
        current = time.time() if now is None else now
        if kid not in self._keys or current - self._fetched_at > self.ttl:
            self._refresh(current)
        key = self._keys.get(kid)
        if key is None:
            raise IdentityError(f"signing key '{kid}' not published by the issuer")
        return key

    def _refresh(self, now: float) -> None:
        try:
            with urllib.request.urlopen(self.url, timeout=10) as response:  # noqa: S310 - https const
                document = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise IdentityError(f"JWKS unavailable: {type(exc).__name__}") from exc
        keys: dict[str, ec.EllipticCurvePublicKey] = {}
        for jwk in document.get("keys") or []:
            if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
                continue
            kid = jwk.get("kid")
            if not kid:
                continue
            x = int.from_bytes(_b64url(jwk["x"]), "big")
            y = int.from_bytes(_b64url(jwk["y"]), "big")
            keys[kid] = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(),
                b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big"),
            )
        if not keys:
            raise IdentityError("JWKS contained no usable P-256 keys")
        self._keys = keys
        self._fetched_at = now


def verify(
    token: str,
    *,
    expected_audience: str,
    expected_org: str | None = None,
    jwks: JWKSCache | None = None,
    now: float | None = None,
) -> SessionClaims:
    """Verify a session assertion. Raises :class:`IdentityError` on any failure.

    ``expected_audience`` must be the exact ``ccpool_<environment>`` this broker
    serves. It is a required argument on purpose — there is no "any audience"
    mode to accidentally deploy with.
    """
    if not expected_audience.startswith("ccpool_"):
        raise IdentityError("broker misconfigured: expected audience is not a ccpool id")

    parts = (token or "").split(".")
    if len(parts) != 3:
        raise IdentityError("malformed assertion: not a three-segment JWT")

    try:
        header = json.loads(_b64url(parts[0]))
        payload = json.loads(_b64url(parts[1]))
        signature = _b64url(parts[2])
    except (ValueError, KeyError) as exc:
        raise IdentityError("malformed assertion: undecodable segments") from exc

    # Algorithm is pinned before any key work. Accepting the token's own `alg`
    # is the classic confusion bug: `none` forges everything, and HMAC turns a
    # public key into a shared secret.
    if header.get("alg") != EXPECTED_ALG:
        raise IdentityError(f"unexpected algorithm '{header.get('alg')}' (require {EXPECTED_ALG})")
    if header.get("typ") not in (None, "JWT", "at+jwt"):
        raise IdentityError(f"unexpected token type '{header.get('typ')}'")
    kid = header.get("kid")
    if not kid:
        raise IdentityError("assertion header carries no kid")

    if len(signature) != 64:
        raise IdentityError("malformed ES256 signature length")
    key = (jwks or JWKSCache()).get(str(kid), now=now)
    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    signed = f"{parts[0]}.{parts[1]}".encode("ascii")
    try:
        key.verify(encode_dss_signature(r, s), signed, ec.ECDSA(SHA256()))
    except InvalidSignature as exc:
        raise IdentityError("signature verification failed") from exc

    # Signature is good; now the claims must be the ones we expect. A correctly
    # signed token from the wrong pool, role or org is still a rejection.
    if payload.get("iss") != EXPECTED_ISSUER:
        raise IdentityError(f"unexpected issuer '{payload.get('iss')}'")

    audience = payload.get("aud")
    audiences = [audience] if isinstance(audience, str) else list(audience or [])
    if expected_audience not in audiences:
        raise IdentityError("assertion audience does not include this broker's ccpool")

    if payload.get("ccr:role") != EXPECTED_ROLE:
        raise IdentityError(f"unexpected role '{payload.get('ccr:role')}'")

    expires = payload.get("exp")
    if not isinstance(expires, int):
        raise IdentityError("assertion carries no integer exp")
    current = time.time() if now is None else now
    if expires + CLOCK_SKEW_SECONDS < current:
        raise IdentityError("assertion expired")

    org_id = str(payload.get("ccr:org_id") or "")
    if expected_org and org_id != expected_org:
        raise IdentityError("assertion organization is not the expected organization")

    session_id = str(payload.get("ccr:session_id") or "")
    if not session_id:
        raise IdentityError("assertion carries no session identity")

    act = payload.get("act") or {}
    account_id = str(payload.get("ccr:account_id") or act.get("sub") or "")

    return SessionClaims(
        session_id=session_id,
        jti=str(payload.get("jti") or ""),
        org_id=org_id,
        account_id=account_id,
        audience=expected_audience,
        role=EXPECTED_ROLE,
        expires_at=expires,
    )


__all__ = [
    "CLOCK_SKEW_SECONDS",
    "DEFAULT_JWKS_URL",
    "EXPECTED_ALG",
    "EXPECTED_ISSUER",
    "EXPECTED_ROLE",
    "IdentityError",
    "JWKSCache",
    "SessionClaims",
    "verify",
]
