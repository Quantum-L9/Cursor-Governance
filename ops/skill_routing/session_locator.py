#!/usr/bin/env python3
"""One route-receipt identity per Cursor conversation.

Cursor delivers ``conversation_id`` and ``workspace_roots`` on both
``sessionStart`` and ``beforeSubmitPrompt`` (cursor.com/docs/agent/hooks). The
locator hashes those into a stable receipt path so every prompt in a
conversation writes, and the always-apply rule reads, exactly one file:

    <state_root>/<conversation-key>/current.json

``session_id`` (sessionStart-only) is deliberately *not* used as the key: the
contract forbids assuming session_id == conversation_id without runtime
proof. All correlation lives in ``extract_conversation_id`` so a differing
runtime identifier is a one-function adapter change.

CLI (consumed by ops/hooks/session_start_bootstrap.sh — Python owns the JSON):

    session_locator.py --payload-json '<hook payload>' [--banner | --env | --json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_STATE_ROOT_REL = Path(".cursor") / "l9" / "routes"
STATE_ROOT_ENV = "L9_ROUTE_STATE_ROOT"
CONVERSATION_ENV = "L9_ROUTE_CONVERSATION_ID"
LOCATOR_ENV = "L9_ROUTE_RECEIPT_PATH"
RECEIPT_FILENAME = "current.json"
KEY_LENGTH = 32


def default_state_root() -> Path:
    configured = os.environ.get(STATE_ROOT_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / DEFAULT_STATE_ROOT_REL


def conversation_key(conversation_id: str) -> str:
    """sha256 of the UTF-8 conversation id, truncated to a safe dir token."""
    if not conversation_id:
        raise ValueError("conversation_id is required")
    return hashlib.sha256(conversation_id.encode("utf-8")).hexdigest()[:KEY_LENGTH]


def normalize_workspace_roots(roots: Any) -> list[str]:
    if isinstance(roots, str):
        roots = [roots]
    if not isinstance(roots, list):
        return []
    normalized: list[str] = []
    for item in roots:
        if not isinstance(item, str) or not item.strip():
            continue
        try:
            normalized.append(str(Path(item).expanduser().resolve(strict=False)))
        except (OSError, RuntimeError):
            normalized.append(item.strip())
    return sorted(set(normalized))


def workspace_key(roots: list[str]) -> str:
    return hashlib.sha256("\n".join(roots).encode("utf-8")).hexdigest()[:KEY_LENGTH]


def extract_conversation_id(payload: dict[str, Any]) -> str:
    """The single correlation adapter between Cursor payloads and receipts."""
    value = payload.get("conversation_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    env_value = os.environ.get(CONVERSATION_ENV, "").strip()
    return env_value


@dataclass(frozen=True)
class RouteLocator:
    conversation_id: str
    conversation_key: str
    workspace_roots: list[str]
    workspace_key: str
    state_root: str
    receipt_path: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def env(self) -> dict[str, str]:
        """Env exported by sessionStart for later hook executions."""
        return {
            CONVERSATION_ENV: self.conversation_id,
            LOCATOR_ENV: self.receipt_path,
        }

    def banner(self) -> str:
        return (
            "### Route locator\n"
            f"- conversation-key: {self.conversation_key}\n"
            f"- receipt: {self.receipt_path}\n"
            "- consume: routed → load the materialized SKILL.md paths; "
            "no_route → proceed without a canonical skill; "
            "degraded/absent → l9-skill-gateway fallback"
        )


def receipt_path_for(conversation_id: str, state_root: Path | None = None) -> Path:
    root = state_root or default_state_root()
    return root / conversation_key(conversation_id) / RECEIPT_FILENAME


def locator_from_payload(
    payload: dict[str, Any], state_root: Path | None = None
) -> RouteLocator | None:
    """Return a locator, or ``None`` when the payload has no conversation."""
    conversation_id = extract_conversation_id(payload)
    if not conversation_id:
        return None
    roots = normalize_workspace_roots(payload.get("workspace_roots"))
    root = state_root or default_state_root()
    return RouteLocator(
        conversation_id=conversation_id,
        conversation_key=conversation_key(conversation_id),
        workspace_roots=roots,
        workspace_key=workspace_key(roots),
        state_root=str(root),
        receipt_path=str(receipt_path_for(conversation_id, root)),
    )


def _read_payload(raw: str | None) -> dict[str, Any]:
    text = raw if raw is not None else os.environ.get("L9_HOOK_PAYLOAD", "")
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--payload-json", default=None, help="hook payload (default: $L9_HOOK_PAYLOAD)"
    )
    parser.add_argument("--state-root", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--banner", action="store_true", help="markdown section for additional_context"
    )
    mode.add_argument(
        "--env", action="store_true", help="JSON env object for the sessionStart hook"
    )
    mode.add_argument("--json", action="store_true", help="full locator JSON (default)")
    args = parser.parse_args(argv)

    payload = _read_payload(args.payload_json)
    state_root = Path(args.state_root).expanduser() if args.state_root else None
    locator = locator_from_payload(payload, state_root)
    if locator is None:
        if args.banner:
            print("### Route locator\n- unresolved: hook payload carried no conversation_id")
        elif args.env:
            print("{}")
        else:
            print(json.dumps({"resolved": False, "reason": "no conversation_id"}))
        return 0
    if args.banner:
        print(locator.banner())
    elif args.env:
        print(json.dumps(locator.env(), sort_keys=True))
    else:
        print(json.dumps({"resolved": True, **locator.as_dict()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
