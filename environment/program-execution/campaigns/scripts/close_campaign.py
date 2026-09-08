#!/usr/bin/env python3
"""Live campaign closeout ledger (in-repo): a projection, not an authority.

Immutable CAMPAIGN_SOURCE.yaml metadata.status stays operator_intake.
This ledger is what agents read to decide which campaign is next.

The terminal verdict is never supplied here. `close` consumes the Controller
Closure Receipt that `pec close` produced over its own canonical state, validates
its identity (schema, producer, program id, digest) and projects the verdict it
carries (PEC-P1-002). A caller cannot invent a terminal verdict.

  close  --id <campaign> --closure-receipt <path> [--expected-verdict V] [--evidence k=v]
  next
  status
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

LEDGER_SCHEMA = "l9.program-execution.campaign-status-ledger.v1"
LIFECYCLES = {"planned", "in_progress", "complete", "cancelled"}
TERMINAL_VERDICTS = {"CONVERGED", "CONVERGED_WITH_NON_BLOCKING_RISKS", "NOT_CONVERGED"}
LEDGER_NAME = "CAMPAIGN_STATUS.yaml"
POLICY_NAME = "CAMPAIGN_EXECUTION_POLICY.yaml"
COMPLETED_DIR = "COMPLETED"
CLOSURE_RECEIPT_SCHEMA = "program-execution-controller.closure-receipt.v1"
CLOSURE_PRODUCER = "Program Execution Controller"
_RECEIPT_REQUIRED = (
    "schema",
    "closure_id",
    "producer",
    "controller_id",
    "campaign_id",
    "program_id",
    "program_digest",
    "runtime_workspace",
    "verdict",
    "closed_by",
    "closed_at",
    "receipt_digest",
)


class ClosureReceiptError(ValueError):
    pass


def _canonical_digest(value: Any) -> str:
    import hashlib

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_closure_receipt(payload: Any, campaign_id: str) -> dict[str, Any]:
    """The Controller Closure Receipt, or why it cannot be accepted."""
    if not isinstance(payload, dict):
        raise ClosureReceiptError("closure receipt is not an object")
    missing = [key for key in _RECEIPT_REQUIRED if key not in payload]
    if missing:
        raise ClosureReceiptError(f"closure receipt missing fields: {missing}")
    if payload.get("schema") != CLOSURE_RECEIPT_SCHEMA:
        raise ClosureReceiptError(f"closure receipt schema {payload.get('schema')!r} not accepted")
    if payload.get("producer") != CLOSURE_PRODUCER:
        raise ClosureReceiptError(
            f"closure receipt producer {payload.get('producer')!r} not accepted"
        )
    body = dict(payload)
    claimed = body.pop("receipt_digest", None)
    if _canonical_digest(body) != claimed:
        raise ClosureReceiptError("closure receipt digest mismatch")
    if str(payload.get("campaign_id")) != campaign_id:
        raise ClosureReceiptError(
            f"closure receipt is for campaign {payload.get('campaign_id')!r}, not {campaign_id!r}"
        )
    if payload.get("verdict") not in TERMINAL_VERDICTS:
        raise ClosureReceiptError(
            f"closure receipt verdict {payload.get('verdict')!r} not terminal"
        )
    return payload


def load_closure_receipt(source: Path | dict[str, Any], campaign_id: str) -> dict[str, Any]:
    if isinstance(source, dict):
        return validate_closure_receipt(source, campaign_id)
    path = Path(source)
    if not path.is_file():
        raise ClosureReceiptError(f"closure receipt not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ClosureReceiptError(f"closure receipt unreadable: {path}: {exc}") from exc
    return validate_closure_receipt(payload, campaign_id)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def campaigns_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML required")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _dump_yaml(path: Path, value: dict[str, Any]) -> None:
    if yaml is None:
        raise SystemExit("PyYAML required")
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def load_policy(root: Path) -> dict[str, Any]:
    return _load_yaml(root / POLICY_NAME)


def load_ledger(root: Path) -> dict[str, Any]:
    path = root / LEDGER_NAME
    if not path.is_file():
        return {
            "schema": LEDGER_SCHEMA,
            "updated": _utc_now(),
            "campaigns": [],
        }
    return _load_yaml(path)


def policy_ids(policy: dict[str, Any]) -> list[str]:
    return [str(item["id"]) for item in policy.get("campaigns") or [] if item.get("id")]


def next_campaign(root: Path) -> dict[str, Any] | None:
    policy = load_policy(root)
    ledger = {item["id"]: item for item in load_ledger(root).get("campaigns") or []}
    ordered = sorted(
        policy.get("campaigns") or [],
        key=lambda item: int(item.get("execute_order") or 0),
    )
    for item in ordered:
        cid = str(item["id"])
        life = str((ledger.get(cid) or {}).get("lifecycle") or "planned")
        if (root / COMPLETED_DIR / cid).is_dir():
            continue
        if life not in {"complete", "cancelled"}:
            return {
                "id": cid,
                "execute_order": item.get("execute_order"),
                "lifecycle": life,
                "integration_branch": item.get("integration_branch"),
            }
    return None


def close_campaign(
    root: Path,
    campaign_id: str,
    closure_receipt: Path | dict[str, Any],
    actor: str,
    *,
    extra_evidence: dict[str, str] | None = None,
    expected_verdict: str | None = None,
) -> dict[str, Any]:
    """Project a Controller closure into the campaign ledger. Never decides."""
    try:
        receipt = load_closure_receipt(closure_receipt, campaign_id)
    except ClosureReceiptError as exc:
        raise SystemExit(f"closeout refused: {exc}") from exc
    verdict = str(receipt["verdict"])
    if expected_verdict is not None and expected_verdict != verdict:
        raise SystemExit(
            f"closeout refused: caller expected {expected_verdict}, the Controller closed "
            f"{campaign_id} as {verdict}"
        )
    policy = load_policy(root)
    if campaign_id not in policy_ids(policy):
        raise SystemExit(f"unknown campaign_id={campaign_id}")
    evidence: dict[str, Any] = {
        "closure_id": str(receipt["closure_id"]),
        "program_digest": str(receipt["program_digest"]),
        "closure_receipt_digest": str(receipt["receipt_digest"]),
        "pec_workspace": str(receipt["runtime_workspace"]),
        "closed_by_controller": str(receipt["controller_id"]),
    }
    for key, value in (extra_evidence or {}).items():
        evidence.setdefault(key, value)
    ledger = load_ledger(root)
    rows = list(ledger.get("campaigns") or [])
    found = False
    record = {
        "id": campaign_id,
        "lifecycle": "complete",
        "closed_at": _utc_now(),
        "verdict": verdict,
        "evidence": evidence,
        "closed_by": actor,
    }
    for index, item in enumerate(rows):
        if item.get("id") == campaign_id:
            rows[index] = {**item, **record}
            found = True
            break
    if not found:
        rows.append(record)
    ledger["schema"] = LEDGER_SCHEMA
    ledger["updated"] = record["closed_at"]
    ledger["campaigns"] = rows
    _dump_yaml(root / LEDGER_NAME, ledger)
    closeout_path = root / campaign_id / "handoff" / "CLOSEOUT.yaml"
    closeout_path.parent.mkdir(parents=True, exist_ok=True)
    _dump_yaml(
        closeout_path,
        {
            "schema": "l9.program-execution.campaign-closeout.v2",
            **record,
            "closure_receipt": {
                key: receipt.get(key)
                for key in ("closure_id", "program_id", "program_digest", "receipt_digest")
            },
        },
    )
    return record


def archive_completed(root: Path, campaign_id: str) -> Path:
    src = root / campaign_id
    dest = root / COMPLETED_DIR / campaign_id
    if not src.is_dir():
        raise SystemExit(f"campaign directory missing: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit(f"COMPLETED already has {campaign_id}")
    shutil.move(str(src), str(dest))
    return dest


def cmd_close(args: argparse.Namespace) -> int:
    evidence = {}
    for item in args.evidence:
        if "=" not in item:
            raise SystemExit(f"evidence must be key=value, got {item}")
        key, value = item.split("=", 1)
        evidence[key] = value
    record = close_campaign(
        campaigns_root(args.root),
        args.id,
        args.closure_receipt,
        args.actor,
        extra_evidence=evidence,
        expected_verdict=args.expected_verdict,
    )
    archive_completed(campaigns_root(args.root), args.id)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    nxt = next_campaign(campaigns_root(args.root))
    print(json.dumps(nxt, indent=2, sort_keys=True))
    return 0 if nxt else 2


def cmd_status(args: argparse.Namespace) -> int:
    root = campaigns_root(args.root)
    policy = load_policy(root)
    ledger = {item["id"]: item for item in load_ledger(root).get("campaigns") or []}
    rows = []
    for item in sorted(
        policy.get("campaigns") or [],
        key=lambda row: int(row.get("execute_order") or 0),
    ):
        cid = str(item["id"])
        live = ledger.get(cid) or {}
        rows.append(
            {
                "id": cid,
                "execute_order": item.get("execute_order"),
                "lifecycle": live.get("lifecycle") or "planned",
                "verdict": live.get("verdict"),
            }
        )
    print(json.dumps({"next": next_campaign(root), "campaigns": rows}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="In-repo campaign closeout ledger")
    p.add_argument("--root", type=Path, default=None)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("close")
    c.add_argument("--id", required=True)
    c.add_argument(
        "--closure-receipt",
        required=True,
        type=Path,
        help="Controller Closure Receipt written by `pec close` (the only verdict source)",
    )
    c.add_argument(
        "--expected-verdict",
        default=None,
        choices=sorted(TERMINAL_VERDICTS),
        help="non-authoritative: refuse if the receipt's verdict differs",
    )
    c.add_argument("--actor", default="AUTH-001")
    c.add_argument("--evidence", action="append", default=[], help="additive key=value only")
    c.set_defaults(func=cmd_close)
    n = sub.add_parser("next")
    n.set_defaults(func=cmd_next)
    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
