#!/usr/bin/env python3
"""SessionStart secrets plane — one owner, fail loud.

SessionStart binds Infisical. AWS CLI must be installed and authorized so the
one login secret can seed the machine profile. If that preflight fails, the
downstream secrets plane cannot start.

This is not a Makefile ceremony. Values are never printed or exported.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SECRETS = Path(__file__).resolve().parent
if str(_SECRETS) not in sys.path:
    sys.path.insert(0, str(_SECRETS))

import aws_cli_preflight as aws_preflight  # noqa: E402
import capability_bind as cb  # noqa: E402
import infisical_cli_login as login  # noqa: E402
import surface_trust  # noqa: E402

BIND_NAMES = ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "GITHUB_TOKEN")


#: ``login`` state when the surface may not hold raw secret material at all, so
#: the seeding path was never attempted. Distinct from ``"skipped"``, which
#: means the surface CAN seed and the AWS preflight stopped it.
NOT_APPLICABLE = "not-applicable"

#: ``aws.code`` for the same case. The preflight is not run, so reporting one of
#: its failure codes would claim a probe that never happened.
NOT_ATTEMPTED = "SEEDING_NOT_APPLICABLE"


def _bind_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in BIND_NAMES:
        status = cb.bind_status(name)
        rows.append(
            {
                "name": str(status.get("name") or name),
                "bound": bool(status.get("bound")),
                "source": str(status.get("source") or "unbound"),
            }
        )
    return rows


def run_plane(*, trust: Any = None) -> dict[str, Any]:
    """Bind the SessionStart secrets plane, or report that it does not apply here.

    On a model-controlled surface the AWS/Infisical seeding path is not merely
    unavailable, it is **prohibited**: ``surface_trust`` says such a caller
    "receives *capabilities*, never values". Probing for an AWS CLI there and
    reporting its absence as a failure asked the shared bootstrap to count a
    degradation against a condition the surface is designed to be in, whose only
    printed repair ("install AWS CLI v2") governance forbids executing here.
    `bootstrap_agent_environment.sh` counted the non-zero exit, `install.sh`
    mapped exit 6 to `STATUS_SHARED=DEGRADED`, and because `downgrade` is
    monotone that pinned the whole bootstrap receipt DEGRADED on every hosted
    session, permanently.

    That is the same class of lie the shared bootstrap already refuses to tell
    elsewhere: its proxy-sentinel carve-out notes that counting a
    structurally-absent credential as a leak "produces a false DEGRADED, which
    is the same class of lie as a false READY and just as expensive to chase".
    `emit_claude_readiness.py` already grades this posture
    `secret_boundary_status=READY`.

    ``raw_secret_allowed`` is the branch because ``surface_trust`` documents it
    as "the only field a caller should branch on … one place decides, everywhere
    else obeys" — so this is not a second surface check, and emphatically not a
    read of ``L9_GOVERNANCE_SURFACE`` here. ``classify`` default-denies and
    audits the runtime for model markers, refusing an operator claim raised from
    inside a model runtime, so the branch cannot be talked into the seeding path
    by a passed id.

    Nothing is weakened: on a surface that may hold raw material, every probe,
    exit code and message below is unchanged.
    """
    decision = surface_trust.classify() if trust is None else trust
    if not decision.raw_secret_allowed:
        return {
            # `summary` is carried even though no probe ran: `receipt_payload`
            # reads it, so omitting it would make `--receipt-out` write a
            # receipt missing a declared field.
            "aws": {
                "ok": False,
                "code": NOT_ATTEMPTED,
                "summary": "seeding not applicable on a model-controlled surface",
            },
            "login": NOT_APPLICABLE,
            "binds": _bind_rows(),
            "plane_ok": True,
            "trust_class": decision.trust_class,
        }
    aws = aws_preflight.probe()
    login_state = "skipped"
    if aws.get("ok"):
        login_state = login.ensure_machine_profile()
    binds = _bind_rows()
    return {
        "aws": {
            "ok": bool(aws.get("ok")),
            "code": str(aws.get("code") or ""),
            "summary": str(aws.get("summary") or ""),
        },
        "login": login_state,
        "binds": binds,
        "plane_ok": bool(aws.get("ok")) and login_state != "failed",
    }


def receipt_payload(result: dict[str, Any]) -> dict[str, Any]:
    aws = result.get("aws") if isinstance(result.get("aws"), dict) else {}
    binds = result.get("binds") if isinstance(result.get("binds"), list) else []
    return {
        "ok": bool(result.get("plane_ok")),
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
    if result["login"] == NOT_APPLICABLE:
        # Reported, not swallowed. `plane_ok` is true here, so without this arm
        # the run would print the generic success line and the one fact a reader
        # needs — that the seeding path was never attempted, and why — would be
        # inferable only from `login=not-applicable`. The bind rows stay on the
        # line so exit 0 is legible: what is capability-bound is still named.
        print(
            "session_start_secrets: seeding not applicable by design on a "
            f"model-controlled surface ({result.get('trust_class', '')}); "
            "raw secret material is not delivered here. "
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
