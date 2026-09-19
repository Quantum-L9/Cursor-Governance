#!/usr/bin/env python3
"""SessionStart secrets plane — one owner, fail loud.

SessionStart binds Infisical. AWS CLI must be installed and authorized so the
one login secret can seed the machine profile. If that preflight fails, the
downstream secrets plane cannot start.

On a model-controlled surface it cannot start *by design*: that surface holds
no Infisical bind, no PAT and no bearer, so the AWS CLI is absent as a property
of the environment rather than as a fault in it. Reporting that absence as a
bootstrap failure produces a false DEGRADED, which is the same class of lie as
a false READY and just as expensive to chase. The plane therefore carries a
tri-state — the probe stays truthful, only the scoring is classified.

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

import aws_cli_preflight as aws_preflight  # noqa: E402
import capability_bind as cb  # noqa: E402
import infisical_cli_login as login  # noqa: E402

BIND_NAMES = ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "GITHUB_TOKEN")

#: Surface classes. Only ``model_controlled`` earns the carve-out below: a
#: self-hosted pool and an operator machine *can* hold a credential plane, so
#: AWS absence there is a real fault and must keep degrading.
MODEL_CONTROLLED = "model_controlled"
SELF_HOSTED = "self_hosted"
OPERATOR = "operator"

#: Plane states. ``ok`` and ``unavailable_by_surface`` both exit 0; only
#: ``failed`` — a surface that should have bound and did not — exits 1.
STATE_OK = "ok"
STATE_UNAVAILABLE_BY_SURFACE = "unavailable_by_surface"
STATE_FAILED = "failed"


def surface_class(env: Mapping[str, str] | None = None) -> str:
    """Classify the surface this plane is running on.

    The predicate is taken from ``capability_client.session_identity`` rather
    than invented, including its order: the ``ccpool_`` test runs first, so a
    self-hosted pool is never mistaken for a hosted one. That order is also the
    safe direction — misreading a pool as model-controlled would silence a real
    fault, while the reverse only reports one loudly.
    """
    source = os.environ if env is None else env
    pool = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_ID") or "").strip()
    if pool.startswith("ccpool_"):
        return SELF_HOSTED
    hosted = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE") or "").strip()
    if hosted == "cloud_default":
        return MODEL_CONTROLLED
    return OPERATOR


def plane_state(aws: Mapping[str, Any], login_state: str, klass: str) -> str:
    """Score the plane. The probe is not consulted for anything but its truth.

    A present-but-broken CLI (``AWS_NOT_AUTHORIZED``, ``TIMEOUT``) is a fault on
    every surface, including a hosted one. Only an *absent* CLI on a
    model-controlled surface is an environment property.
    """
    if bool(aws.get("ok")) and login_state != "failed":
        return STATE_OK
    if klass == MODEL_CONTROLLED and str(aws.get("code") or "") == aws_preflight.AWS_CLI_NOT_FOUND:
        return STATE_UNAVAILABLE_BY_SURFACE
    return STATE_FAILED


def run_plane(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    aws = aws_preflight.probe()
    klass = surface_class(env)
    login_state = "skipped"
    if aws.get("ok"):
        login_state = login.ensure_machine_profile()
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
        "aws": {
            "ok": bool(aws.get("ok")),
            "code": str(aws.get("code") or ""),
            "summary": str(aws.get("summary") or ""),
        },
        "login": login_state,
        "binds": binds,
        "plane_ok": bool(aws.get("ok")) and login_state != "failed",
        "surface_class": klass,
        "state": plane_state(aws, login_state, klass),
    }


def receipt_payload(result: dict[str, Any]) -> dict[str, Any]:
    aws = result.get("aws") if isinstance(result.get("aws"), dict) else {}
    binds = result.get("binds") if isinstance(result.get("binds"), list) else []
    return {
        # `ok` keeps its old meaning — did the plane bind — and stays false when
        # it did not, because it did not. Only the scoring of that fact moved.
        "ok": bool(result.get("plane_ok")),
        "state": str(result.get("state") or STATE_FAILED),
        "surface_class": str(result.get("surface_class") or OPERATOR),
        "login": result.get("login"),
        "aws": {
            "ok": bool(aws.get("ok")),
            "code": str(aws.get("code") or ""),
            "summary": str(aws.get("summary") or ""),
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
    if result["state"] == STATE_UNAVAILABLE_BY_SURFACE:
        # Visible, never silent — just not a fault. The inventoried secrets stay
        # unbound and the receipt still says so; there is nothing to repair here
        # and nothing to paste (rule 62).
        print(
            "session_start_secrets: secrets plane unavailable by surface "
            f"({MODEL_CONTROLLED}; no Infisical bind by design) — not a fault. "
            + " ".join(f"{b['name']}={b['source']}" for b in result["binds"]),
            file=sys.stderr,
        )
        return 0
    if not result["plane_ok"]:
        if not result["aws"]["ok"]:
            print(
                "FAILED: AWS CLI is missing or not authorized. "
                "Infisical bind cannot start. Repair: install AWS CLI v2 && "
                "aws sts get-caller-identity",
                file=sys.stderr,
            )
        else:
            print(
                f"FAILED: Infisical machine profile {result['login']}. "
                "SessionStart cannot bind inventoried secrets.",
                file=sys.stderr,
            )
        return 1
    print(
        f"session_start_secrets: ok login={result['login']} "
        + " ".join(f"{b['name']}={b['source']}" for b in result["binds"]),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
