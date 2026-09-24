#!/usr/bin/env python3
"""SessionStart secrets plane — one owner, fail loud, Infisical only.

SessionStart logs in to Infisical as this surface's machine identity
(``infisical_cli_login``: ``L9_INFISICAL_CLIENT_ID`` + ``L9_INFISICAL_CLIENT_SECRET``,
or an operator's ``~/.infisical/l9-machine.json``) and probes the inventoried
names. There is no AWS step: the AWS login seed and the AWS CLI preflight are
retired, and no surface is exempt. Every surface that runs agents needs its
identity; a surface without one FAILS, loudly, with the fix named — secrets are
not optional.

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


def identity_status(login_state: str, source: str) -> dict[str, Any]:
    """The machine identity's state, names only."""
    if login_state in {"env", "present"}:
        return {
            "ok": True,
            "code": IDENTITY_OK,
            "source": source,
            "summary": f"Infisical machine identity logged in (source={source})",
        }
    if login_state == "absent":
        return {
            "ok": False,
            "code": IDENTITY_ABSENT,
            "source": "",
            "summary": (
                f"no Infisical machine identity — set {login.ENV_CLIENT_ID} and "
                f"{login.ENV_CLIENT_SECRET} in the environment settings"
            ),
        }
    return {
        "ok": False,
        "code": IDENTITY_REFUSED,
        "source": source,
        "summary": "Infisical refused the machine identity or was unreachable",
    }


def run_plane(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    klass = surface_class(env)
    login_state = login.ensure_machine_profile(env)
    source = login.machine_identity(env)[0]
    identity = identity_status(login_state, source)
    binds: list[dict[str, Any]] = []
    for name in BIND_NAMES:
        status = cb.bind_status(name)
        binds.append(
            {
                "name": str(status.get("name") or name),
                "bound": bool(status.get("bound")),
                "source": str(status.get("source") or "unbound"),
            }
        )
    return {
        "identity": identity,
        "login": login_state,
        "binds": binds,
        "plane_ok": bool(identity["ok"]),
        "surface_class": klass,
        "state": STATE_OK if identity["ok"] else STATE_FAILED,
    }


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
    binds = " ".join(f"{b['name']}={b['source']}" for b in result["binds"])
    if not result["plane_ok"]:
        print(f"FAILED: {result['identity']['summary']}. {binds}", file=sys.stderr)
        return 1
    print(f"session_start_secrets: ok login={result['login']} {binds}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
