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


def _bind_line(binds: list[dict[str, Any]]) -> str:
    """NAME=source for each probed name, built from module literals only."""
    by_name = {str(b.get("name")): b.get("source") for b in binds}
    return " ".join(f"{name}={cb.literal_source(by_name.get(name))}" for name in BIND_NAMES)


#: Identity sources the receipt may carry, as literals.
IDENTITY_SOURCES = ("env", "profile")


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
    klass = surface_class(env)
    source = login.machine_identity(env)[0]
    aws: dict[str, Any] | None = None
    if klass == MODEL_CONTROLLED or source == login.SOURCE_ENV:
        # Claude: the environment identity; no AWS step at all.
        login_state = login.ensure_machine_profile(env)
    else:
        # Cursor / operator: main's behaviour, unchanged — AWS preflight, then
        # the existing profile or the AWS seed that writes it.
        aws = _aws_probe()
        login_state = (
            login.ensure_machine_profile(env, allow_aws_seed=True) if aws.get("ok") else "skipped"
        )
        source = login.machine_identity(env)[0] or source
    identity = identity_status(login_state, source)
    binds: list[dict[str, Any]] = []
    for name in BIND_NAMES:
        status = cb.bind_status(name)
        binds.append(
            {
                "name": name,  # the module's own literal, not the bind result's echo
                "bound": bool(status.get("bound")),
                "source": cb.literal_source(status.get("source")),
            }
        )
    plane_ok = bool(identity["ok"]) and (aws is None or bool(aws.get("ok")))
    result: dict[str, Any] = {
        "identity": identity,
        "login": login_state,
        "binds": binds,
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
        **({"aws": result["aws"]} if isinstance(result.get("aws"), dict) else {}),
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
