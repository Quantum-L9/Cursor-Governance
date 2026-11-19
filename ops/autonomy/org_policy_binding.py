#!/usr/bin/env python3
"""Bind this operating plane to organization policy authored in Quantum-L9/.github.

The local ``ORG_INVARIANTS.yaml`` is a projection of that pin. Operating law
(``CANONICAL_LAW.md``, modes, skills, and ``make pr``) stays a separate authority.
This module reports the pin. It does not admit the policy, fetch it, or grant
permission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REPO = Path(__file__).resolve().parents[2]
BINDING_REL = Path("governance/authority-bindings/org-invariants.yaml")
ROLES = ("session", "cto", "architect", "planner", "coding-agent")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_binding(root: Path | None = None) -> dict[str, Any]:
    """Return the consumer binding. Missing or unreadable is ``MISSING``."""
    root = root or REPO
    path = root / BINDING_REL
    if yaml is None:
        return {"status": "MISSING", "reason": "INTERPRETER_UNRESOLVED"}
    if not path.is_file():
        return {"status": "MISSING", "reason": f"BINDING_ABSENT: {BINDING_REL}"}
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return {"status": "MISSING", "reason": f"BINDING_UNREADABLE: {exc}"}
    if not isinstance(document, dict):
        return {"status": "MISSING", "reason": "BINDING_NOT_A_MAPPING"}
    return document


def bind(role: str, root: Path | None = None) -> dict[str, Any]:
    """Status of the organization-policy pin for one role."""
    root = root or REPO
    if role not in ROLES:
        return {"status": "MISSING", "reason": f"ROLE_UNKNOWN: {role}"}
    document = load_binding(root)
    if document.get("status") == "MISSING":
        return document
    upstream = document.get("upstream") if isinstance(document.get("upstream"), dict) else {}
    projection = document.get("projection") if isinstance(document.get("projection"), dict) else {}
    roles = document.get("roles") if isinstance(document.get("roles"), dict) else {}
    role_view = roles.get(role) if isinstance(roles.get(role), dict) else {}
    relative = str(projection.get("path") or "ORG_INVARIANTS.yaml")
    local = root / relative
    expected = str(projection.get("sha256") or "")
    if not local.is_file() or not expected:
        status = "MISSING"
        actual = ""
    else:
        actual = _sha256(local)
        status = "BOUND" if actual == expected else "STALE"
    return {
        "status": status,
        "role": role,
        "repository": upstream.get("repository"),
        "path": upstream.get("path"),
        "revision": upstream.get("revision"),
        "pull_request": upstream.get("pull_request"),
        "policy_version": upstream.get("policy_version"),
        "payload_sha256": upstream.get("payload_sha256"),
        "admission": upstream.get("admission"),
        "signature_status": upstream.get("signature_status"),
        "release_pull_request": upstream.get("release_pull_request"),
        "release_status": upstream.get("release_status"),
        "projection_path": relative,
        "projection_canonical": projection.get("canonical"),
        "projection_sha256": expected,
        "projection_actual_sha256": actual,
        "operating_law": "CANONICAL_LAW.md",
        "applies": role_view.get("applies"),
        "must_not": list(role_view.get("must_not") or []),
    }


AUTHORITY_CLAIMS = (
    "author_organization_policy",
    "claim_admission",
    "claim_signed_release",
)


def govern(action: str, role: str = "session", root: Path | None = None) -> dict[str, Any]:
    """Deny an organization-policy authority claim.

    This repository is the consumer. A local ``admission: true`` or a local
    signature string does not authorize the claim. Session reports stay
    separate and do not call this function.
    """
    item = bind(role, root)
    if action not in AUTHORITY_CLAIMS:
        return {
            "action": action,
            "allowed": True,
            "reason": "not an organization-policy authority claim",
        }
    return {
        "action": action,
        "allowed": False,
        "reason": (
            "Cursor-Governance does not author, admit, or sign organization policy "
            f"(admission={item.get('admission')}, "
            f"signature={item.get('signature_status')}, "
            f"release={item.get('release_status')})"
        ),
    }


def markdown(role: str = "session", root: Path | None = None) -> str:
    """SessionStart section. A missing bind is reported, not hidden."""
    item = bind(role, root)
    if item.get("status") == "MISSING":
        return (
            "### organization policy\n"
            f"- NOT BOUND — {item.get('reason', 'organization-policy binding unavailable')}"
        )
    revision = str(item.get("revision") or "")
    short = revision[:12]
    if item["status"] == "BOUND":
        headline = f"BOUND — projection of {item['repository']} {item['path']} @{short}"
    else:
        headline = "STALE — local ORG_INVARIANTS.yaml does not match the bound projection digest"
    lines = [
        "### organization policy",
        f"- {headline}",
        f"- admission: {str(item.get('admission')).lower()}",
        f"- signature: {item.get('signature_status')}",
        (
            f"- release: {item.get('release_status')} "
            f"(Quantum-L9/.github#{item.get('release_pull_request')})"
        ),
        (
            f"- local projection: {item.get('projection_path')} "
            f"canonical {str(item.get('projection_canonical')).lower()}"
        ),
        "- operating law stays here; this binding does not author organization policy",
        "- denied: author_organization_policy, claim_admission, claim_signed_release",
        f"- this role: {item.get('applies')}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", default="session", choices=ROLES)
    parser.add_argument("--format", choices=("markdown", "json"), default="json")
    parser.add_argument("--action", choices=AUTHORITY_CLAIMS)
    parser.add_argument("--root", type=Path, default=REPO)
    args = parser.parse_args(argv)
    if args.action:
        decision = govern(args.action, args.role, args.root)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0 if decision["allowed"] else 1
    if args.format == "markdown":
        print(markdown(args.role, args.root))
    else:
        print(json.dumps(bind(args.role, args.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
