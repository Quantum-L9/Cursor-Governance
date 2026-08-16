#!/usr/bin/env python3
"""Live campaign closeout ledger (in-repo).

Immutable CAMPAIGN_SOURCE.yaml metadata.status stays operator_intake.
This ledger is what agents read to decide which campaign is next.

  close  --id <campaign> --verdict CONVERGED --evidence key=value
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
    verdict: str,
    evidence: dict[str, str],
    actor: str,
) -> dict[str, Any]:
    if verdict not in TERMINAL_VERDICTS:
        raise SystemExit(f"closeout requires a terminal verdict, got {verdict}")
    policy = load_policy(root)
    if campaign_id not in policy_ids(policy):
        raise SystemExit(f"unknown campaign_id={campaign_id}")
    if not evidence:
        raise SystemExit("closeout requires evidence (PR, SHA, or handoff)")
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
    _dump_yaml(closeout_path, {"schema": "l9.program-execution.campaign-closeout.v1", **record})
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
        args.verdict,
        evidence,
        args.actor,
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
    c.add_argument("--verdict", required=True, choices=sorted(TERMINAL_VERDICTS))
    c.add_argument("--actor", default="AUTH-001")
    c.add_argument("--evidence", action="append", default=[])
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
