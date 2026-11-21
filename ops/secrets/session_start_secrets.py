#!/usr/bin/env python3
"""SessionStart secrets plane — one owner, fail loud, Infisical is the vault.

Every surface binds secrets from Infisical as its machine identity, and no
surface is exempt: a surface without one FAILS, loudly, with the fix named —
secrets are not optional. How the identity is obtained DIVERGES BY PEER:

* Claude Code (model-controlled) — or any surface whose environment carries
  ``L9_INFISICAL_CLIENT_ID`` + ``L9_INFISICAL_CLIENT_SECRET``: that identity,
  with no AWS step and no AWS import.
* Cursor / operator machines: unchanged — AWS CLI preflight, then the existing
  ``~/.infisical/l9-machine.json`` or the AWS login seed that writes it, and the
  ``aws`` receipt object the reporter's ``aws-cli`` line reads.

This is not a Makefile ceremony. Values are never printed or exported.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_SECRETS = Path(__file__).resolve().parent
if str(_SECRETS) not in sys.path:
    sys.path.insert(0, str(_SECRETS))

import capability_bind as cb  # noqa: E402
import infisical_cli_login as login  # noqa: E402

BIND_NAMES = ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "GITHUB_TOKEN", "CONTEXT7_API_KEY")

#: The memory path's Cursor-Governance credentials (lane MEM-HOOK-2): the hosted
#: hook carrier's client-credentials pair (``ops/memory/hook_carrier.py``
#: ``HOOK_CREDENTIALS``) and the signed agent door ``ops/memory/run_memory_mcp.sh``
#: mints at MCP spawn. Each is reported by name and source with the hook carrier
#: it resolves; an unbound name is a named WARN, never a plane failure.
MEMORY_BIND_NAMES = (
    "L9_MEMORY_HOOK_CLIENT_ID",
    "L9_MEMORY_HOOK_CLIENT_SECRET",
    "L9_MEMORY_AGENT_AUTHORITY_JSON",
)
#: What an unbound memory name costs, keyed by name (module literals only).
MEMORY_IMPACT = {
    "L9_MEMORY_HOOK_CLIENT_ID": "hosted hook carrier needs both hook credentials",
    "L9_MEMORY_HOOK_CLIENT_SECRET": "hosted hook carrier needs both hook credentials",
    "L9_MEMORY_AGENT_AUTHORITY_JSON": (
        "run_memory_mcp.sh cannot mint the signed agent door, so memory.write_agent "
        "cannot run as this agent"
    ),
}
#: Hook carriers the report may name (``ops/memory/hook_carrier.py``), as literals.
CARRIER_NAMES = ("hosted", "relay", "local")
CARRIER_REFUSED = "refused"
CARRIER_UNKNOWN = "unknown"

#: Surface classes, reported for context only: no class is exempt from binding.
MODEL_CONTROLLED = "model_controlled"
SELF_HOSTED = "self_hosted"
OPERATOR = "operator"

#: Plane states. Only ``ok`` exits 0.
STATE_OK = "ok"
STATE_FAILED = "failed"

#: Identity codes (names only, never values).
IDENTITY_OK = "OK"
IDENTITY_ABSENT = "IDENTITY_ABSENT"
IDENTITY_REFUSED = "LOGIN_REFUSED"
IDENTITY_AWS_UNAVAILABLE = "AWS_PREFLIGHT_FAILED"


def surface_class(env: Mapping[str, str] | None = None) -> str:
    """Classify the surface this plane is running on.

    The ``ccpool_`` / ``cloud_default`` signals and their precedence are taken
    from ``capability_client.session_identity`` rather than invented: the pool
    test runs first there and here, so a self-hosted pool is never mistaken for
    a hosted one. That order is also the safe direction — misreading a pool as
    model-controlled would silence a real fault, while the reverse only reports
    one loudly.

    The two are not equivalent, and this is deliberately the broader of the
    two. ``session_identity`` mints a pool identity only when
    ``CLAUDE_SESSION_IDENTITY_TOKEN_FILE`` is also present and readable,
    because it needs a token to return; classification needs no token, so any
    ``ccpool_`` prefix is enough here. The difference only ever moves a surface
    *out* of the carve-out: a pool whose token file is missing is still scored
    ``self_hosted`` and still degrades.
    """
    source = os.environ if env is None else env
    # Shared canonical detection, not a private Manus host-marker list. An
    # intentional Manus surface must never inherit a Claude pool/operator seed.
    if login.environment_only_surface(source):
        return MODEL_CONTROLLED
    pool = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_ID") or "").strip()
    if pool.startswith("ccpool_"):
        return SELF_HOSTED
    hosted = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE") or "").strip()
    if hosted == "cloud_default":
        return MODEL_CONTROLLED
    return OPERATOR


#: The only identity messages this module prints: literals, keyed by code.
IDENTITY_MESSAGES = {
    IDENTITY_OK: "Infisical machine identity logged in",
    IDENTITY_ABSENT: (
        "no Infisical machine identity — set L9_INFISICAL_CLIENT_ID and "
        "L9_INFISICAL_CLIENT_SECRET in the environment settings"
    ),
    IDENTITY_REFUSED: "Infisical refused the machine identity or was unreachable",
    IDENTITY_AWS_UNAVAILABLE: (
        "AWS CLI is missing or not authorized. Infisical bind cannot start. "
        "Repair: install AWS CLI v2 && aws sts get-caller-identity"
    ),
}


def catalog_names() -> list[str]:
    """Allow-list names an agent may bind. Refused identity secrets stay off the catalog."""
    return sorted(name for name in cb.allowed_names() if name not in cb.REFUSED_NAMES)


def _bind_line(binds: list[dict[str, Any]]) -> str:
    """NAME=source for each probed name, built from module literals only."""
    by_name = {str(b.get("name")): b.get("source") for b in binds}
    return " ".join(f"{name}={cb.literal_source(by_name.get(name))}" for name in BIND_NAMES)


#: Identity sources the receipt may carry, as literals.
IDENTITY_SOURCES = ("env", "profile")


def _bind_entry(name: str, context: Mapping[str, str]) -> dict[str, Any]:
    status = cb.bind_status(name, env=context)
    return {
        "name": name,  # the module's own literal, not the bind result's echo
        "bound": bool(status.get("bound")),
        "source": cb.literal_source(status.get("source")),
    }


def hook_carrier_for(binds: list[dict[str, Any]], context: Mapping[str, str]) -> str:
    """The carrier ``ops/memory/hook_carrier.py`` resolves from these binds.

    Uses the owner's own decision with the statuses already bound here, so the
    report cannot drift from what the hook lane will do. A module literal.
    """
    repo = Path(__file__).resolve().parents[2]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    bound = {str(b.get("name")): bool(b.get("bound")) for b in binds}
    try:
        from ops.memory import hook_carrier  # noqa: PLC0415

        carrier = hook_carrier.resolve_carrier(
            context, binder=lambda name, _env: bound.get(name, False)
        )
    except ValueError:  # CarrierError: the override names no carrier
        return CARRIER_REFUSED
    except Exception:  # noqa: BLE001 - the report never fails on the carrier probe
        return CARRIER_UNKNOWN
    return next((known for known in CARRIER_NAMES if known == carrier), CARRIER_UNKNOWN)


def memory_plane(context: Mapping[str, str]) -> dict[str, Any]:
    """Memory credentials by name and source, the hook carrier, and named WARNs."""
    binds = [_bind_entry(name, context) for name in MEMORY_BIND_NAMES]
    carrier = hook_carrier_for(binds, context)
    warnings = [
        f"WARN: {name} unbound ({source}) — {MEMORY_IMPACT[name]}; hook carrier: {carrier}"
        for name, source in (
            (
                next(known for known in MEMORY_BIND_NAMES if known == b["name"]),
                cb.literal_source(b.get("source")),
            )
            for b in binds
            if not b["bound"]
        )
    ]
    return {"binds": binds, "carrier": carrier, "warnings": warnings}


def _memory_line(memory: dict[str, Any]) -> str:
    by_name = {str(b.get("name")): b.get("source") for b in memory.get("binds") or []}
    names = " ".join(f"{name}={cb.literal_source(by_name.get(name))}" for name in MEMORY_BIND_NAMES)
    carrier = next(
        (known for known in (*CARRIER_NAMES, CARRIER_REFUSED) if known == memory.get("carrier")),
        CARRIER_UNKNOWN,
    )
    return f"memory: {names} hook_carrier={carrier}"


def identity_status(login_state: str, source: str) -> dict[str, Any]:
    """The machine identity's state as module literals only (names, codes, messages)."""
    if login_state == "skipped":
        code = IDENTITY_AWS_UNAVAILABLE
    elif login_state in {"env", "present", "seeded"}:
        code = IDENTITY_OK
    elif login_state == "absent":
        code = IDENTITY_ABSENT
    else:
        code = IDENTITY_REFUSED
    shown = next((known for known in IDENTITY_SOURCES if known == source), "")
    return {
        "ok": code == IDENTITY_OK,
        "code": code,
        "source": shown if code in {IDENTITY_OK, IDENTITY_REFUSED} else "",
        "summary": IDENTITY_MESSAGES[code],
    }


def _aws_probe() -> dict[str, Any]:
    """Cursor / operator only. Imported lazily: Claude never loads AWS code."""
    import aws_cli_preflight  # noqa: PLC0415

    return aws_cli_preflight.probe()


def run_plane(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    # One snapshot for classification, login and every bind. Never install a
    # caller's context into os.environ or borrow ambient operator credentials.
    context = dict(os.environ if env is None else env)
    klass = surface_class(context)
    source = login.machine_identity(context)[0]
    aws: dict[str, Any] | None = None
    if klass == MODEL_CONTROLLED or source == login.SOURCE_ENV:
        # Hosted Claude / Manus: no AWS step. Manus's shared identity owner
        # additionally refuses the operator profile even when env is incomplete.
        login_state = login.ensure_machine_profile(context)
        if login_state == "failed":
            # Same identity the binds below would log in as: one attempt, not
            # one per name. Their sources still read unbound.
            cb.note_login_failed(context)
    else:
        # Cursor / operator: main's behaviour, unchanged — AWS preflight, then
        # the existing profile or the AWS seed that writes it.
        aws = _aws_probe()
        login_state = (
            login.ensure_machine_profile(context, allow_aws_seed=True)
            if aws.get("ok")
            else "skipped"
        )
        source = login.machine_identity(context)[0] or source
    identity = identity_status(login_state, source)
    binds = [_bind_entry(name, context) for name in BIND_NAMES]
    memory = memory_plane(context)
    plane_ok = bool(identity["ok"]) and (aws is None or bool(aws.get("ok")))
    result: dict[str, Any] = {
        "identity": identity,
        "login": login_state,
        "binds": binds,
        "memory": memory,
        "authorized_names": catalog_names(),
        "plane_ok": plane_ok,
        "surface_class": klass,
        "state": STATE_OK if plane_ok else STATE_FAILED,
    }
    if aws is not None:
        result["aws"] = {
            "ok": bool(aws.get("ok")),
            "code": str(aws.get("code") or ""),
            "summary": str(aws.get("summary") or ""),
        }
    return result


def receipt_payload(result: dict[str, Any]) -> dict[str, Any]:
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    binds = result.get("binds") if isinstance(result.get("binds"), list) else []
    return {
        "ok": bool(result.get("plane_ok")),
        "state": str(result.get("state") or STATE_FAILED),
        "surface_class": str(result.get("surface_class") or OPERATOR),
        "login": result.get("login"),
        "identity": {
            "ok": bool(identity.get("ok")),
            "code": str(identity.get("code") or ""),
            "source": str(identity.get("source") or ""),
            "summary": str(identity.get("summary") or ""),
        },
        "binds": binds,
        "memory": _memory_receipt(result.get("memory")),
        "authorized_names": [
            name
            for name in result.get("authorized_names") or []
            if isinstance(name, str) and name in cb.allowed_names() and name not in cb.REFUSED_NAMES
        ],
        **({"aws": result["aws"]} if isinstance(result.get("aws"), dict) else {}),
    }


def _memory_receipt(raw: object) -> dict[str, Any]:
    memory = raw if isinstance(raw, dict) else {}
    binds = memory.get("binds") if isinstance(memory.get("binds"), list) else []
    return {
        "binds": [
            {
                "name": next((k for k in MEMORY_BIND_NAMES if k == b.get("name")), "?"),
                "bound": bool(b.get("bound")),
                "source": cb.literal_source(b.get("source")),
            }
            for b in binds
            if isinstance(b, dict)
        ],
        "carrier": next(
            (
                known
                for known in (*CARRIER_NAMES, CARRIER_REFUSED)
                if known == memory.get("carrier")
            ),
            CARRIER_UNKNOWN,
        ),
        "warnings": len(memory.get("warnings") or []),
    }


def write_receipt(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt_payload(result), sort_keys=True) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--receipt-out",
        default="",
        help="Write the receipt JSON to this path. Omit to write no file.",
    )
    args = parser.parse_args(argv)
    result = run_plane()
    payload = receipt_payload(result)
    if args.receipt_out:
        write_receipt(Path(args.receipt_out), result)
    if args.json:
        print(json.dumps(payload))
    binds = _bind_line(result["binds"])
    memory = result.get("memory") or {}
    print(f"session_start_secrets: {_memory_line(memory)}", file=sys.stderr)
    for line in memory.get("warnings") or []:
        print(f"session_start_secrets: {line}", file=sys.stderr)
    if not result["plane_ok"]:
        code = next(
            (
                c
                for c in (IDENTITY_ABSENT, IDENTITY_REFUSED, IDENTITY_AWS_UNAVAILABLE)
                if c == result["identity"]["code"]
            ),
            IDENTITY_REFUSED,
        )
        print(f"FAILED: {IDENTITY_MESSAGES[code]}. {binds}", file=sys.stderr)
        return 1
    print(f"session_start_secrets: ok {IDENTITY_MESSAGES[IDENTITY_OK]}. {binds}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
