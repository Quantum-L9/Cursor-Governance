#!/usr/bin/env python3
"""Compose campaign-specific PR title/body from immutable CAMPAIGN_SOURCE.yaml."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PE_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGNS = PE_ROOT / "campaigns"
POLICY_PATH = CAMPAIGNS / "CAMPAIGN_EXECUTION_POLICY.yaml"
STATUS_SCHEMA = "program-execution-controller.campaign-status.v1"


class CopyError(RuntimeError):
    pass


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def branch_default_title(ref: str) -> str:
    text = ref.removeprefix("origin/")
    parts = [part for part in text.split("/") if part]
    if not parts:
        return text
    head = parts[0][:1].upper() + parts[0][1:]
    rest = [part.replace("-", " ") for part in parts[1:]]
    return "/".join([head, *rest]) if rest else head


def campaign_id_from_refs(
    *,
    campaign_id: str | None,
    pr_base: str | None,
    branch: str | None,
) -> str:
    if campaign_id and campaign_id.strip():
        return campaign_id.strip()
    for raw in (pr_base, branch):
        if not raw:
            continue
        text = raw.removeprefix("origin/")
        if text.startswith("campaign/"):
            value = text[len("campaign/") :].strip()
            if value:
                return value
    raise CopyError("not a campaign PR")


def source_path_for(campaign_id: str) -> Path:
    path = CAMPAIGNS / campaign_id / "CAMPAIGN_SOURCE.yaml"
    if not path.is_file():
        raise CopyError(f"missing campaign source: {path}")
    return path


def policy_entry(campaign_id: str) -> dict[str, Any]:
    raw = load_yaml(POLICY_PATH)
    campaigns = raw.get("campaigns") if isinstance(raw, dict) else None
    if not isinstance(campaigns, list):
        raise CopyError("CAMPAIGN_EXECUTION_POLICY.yaml has no campaigns")
    for item in campaigns:
        if isinstance(item, dict) and item.get("id") == campaign_id:
            return item
    raise CopyError(f"campaign {campaign_id} is not in CAMPAIGN_EXECUTION_POLICY.yaml")


def _one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def render(
    *,
    campaign_id: str,
    pr_base: str | None,
    branch: str | None,
) -> dict[str, Any]:
    source = source_path_for(campaign_id)
    src = load_yaml(source)
    if not isinstance(src, dict):
        raise CopyError("campaign source must be an object")
    meta = src.get("metadata") or {}
    program = src.get("program") or {}
    title_text = str(meta.get("title") or "").strip()
    if not title_text:
        raise CopyError(f"{campaign_id} metadata.title is missing")
    title = f"[{campaign_id}] {title_text}"
    for ref in (pr_base, branch, f"campaign/{campaign_id}"):
        if ref and title == branch_default_title(ref):
            raise CopyError(f"title collides with branch-default {title!r}")
    entry = policy_entry(campaign_id)
    integration = str(entry.get("integration_branch") or f"campaign/{campaign_id}")
    objective = _one_line(program.get("objective") or meta.get("title"))
    body = "\n".join(
        [
            "## Campaign",
            f"- id: `{campaign_id}`",
            f"- title: {title_text}",
            f"- objective: {objective}",
            f"- integration branch: `{integration}`",
            f"- PR base: `{pr_base or integration}`",
            f"- execute order: {entry.get('execute_order', 'UNKNOWN')}",
            "",
            "Do not reuse a branch-default GitHub title. Do not open against `main`.",
        ]
    )
    return {
        "campaign_id": campaign_id,
        "title": title,
        "body": body,
        "source": source.as_posix(),
        "metadata_title": title_text,
        "objective": objective,
        "integration_branch": integration,
    }


def write_runtime_status(
    *,
    campaign_id: str,
    runtime_root: Path,
    actor: str,
) -> Path:
    target = runtime_root.expanduser().resolve() / "runtime" / "campaign-status.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": STATUS_SCHEMA,
        "campaign_id": campaign_id,
        "source_status": "operator_intake",
        "runtime_status": "active",
        "activated_at": utc_now(),
        "actor": actor,
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="campaign-pr-copy")
    parser.add_argument("--campaign-id")
    parser.add_argument("--pr-base")
    parser.add_argument("--branch")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--actor", default=os.environ.get("USER", "agent"))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.source is not None:
            src = load_yaml(args.source)
            campaign_id = str((src.get("metadata") or {}).get("campaign_id") or "")
            if not campaign_id:
                raise CopyError("--source has no metadata.campaign_id")
        else:
            campaign_id = campaign_id_from_refs(
                campaign_id=args.campaign_id,
                pr_base=args.pr_base,
                branch=args.branch,
            )
        payload = render(
            campaign_id=campaign_id,
            pr_base=args.pr_base,
            branch=args.branch,
        )
        if args.activate:
            runtime_root = args.runtime_root
            if runtime_root is None:
                src = load_yaml(source_path_for(campaign_id))
                raw_root = str((src.get("metadata") or {}).get("runtime_root") or "")
                if not raw_root:
                    raise CopyError("metadata.runtime_root missing; pass --runtime-root")
                runtime_root = Path(os.path.expandvars(raw_root))
            payload["runtime_status_path"] = str(
                write_runtime_status(
                    campaign_id=campaign_id,
                    runtime_root=runtime_root,
                    actor=args.actor,
                )
            )
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(payload["title"])
            print(payload["body"])
        return 0
    except CopyError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}), file=sys.stderr)
        return 2 if str(exc) == "not a campaign PR" else 1


if __name__ == "__main__":
    raise SystemExit(main())
