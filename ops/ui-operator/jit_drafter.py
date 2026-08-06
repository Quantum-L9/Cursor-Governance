#!/usr/bin/env python3
"""JIT-draft a UI-operator cartridge scaffold (requires human approve before run)."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

HERE = Path(__file__).resolve().parent
DRAFTS = HERE / "drafts"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:64] or "draft-cartridge"


def draft_cartridge(
    *,
    site: str,
    goal: str,
    url: str,
    cartridge_id: str | None = None,
) -> dict:
    cid = cartridge_id or _slug(f"{site}-{goal}")[:48]
    return {
        "schema_version": "1.0.0",
        "id": cid,
        "version": "0.1.0-draft",
        "site": site,
        "goal": goal,
        "urls": {"primary": url},
        "auth": {
            "refs": [f"openclaw-igorbot/ui-session-{site}#storage_state"],
            "ui_session_ref": f"openclaw-igorbot/ui-session-{site}#storage_state",
        },
        "mutation_allowlist": [],
        "forbidden": [
            "change_visibility",
            "remove_unrelated_entries",
            "create_pat",
            "destructive_delete",
        ],
        "targets": {},
        "selectors": {},
        "journey": [
            {"step": "bind_goal", "description": "Confirm goal and allowlist"},
            {"step": "resolve_secrets", "description": "Resolve auth refs"},
            {"step": "prefer_api", "description": "Record why UI is required"},
            {"step": "human_approve", "description": "REQUIRED before first run"},
            {"step": "capture_before", "description": "Before evidence"},
            {"step": "execute_journey", "description": "Fill selectors + mutations"},
            {"step": "capture_after", "description": "After evidence"},
            {"step": "emit_receipt", "description": "Redacted receipt"},
        ],
        "human_approve_required": True,
        "notes": (
            f"JIT draft at {datetime.now(UTC).replace(microsecond=0).isoformat()}. "
            "Fill mutation_allowlist, selectors, and targets; human must approve "
            "before console --mode run."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, help="Site key (github, vercel, …)")
    parser.add_argument("--goal", required=True, help="One-sentence goal")
    parser.add_argument("--url", required=True, help="Primary dashboard URL")
    parser.add_argument("--id", default=None, help="Cartridge id (slug)")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default drafts/<id>.yaml)",
    )
    args = parser.parse_args(argv)

    if yaml is None:
        print("jit_drafter: PyYAML required", file=sys.stderr)
        return 2

    cartridge = draft_cartridge(
        site=args.site.strip(),
        goal=args.goal.strip(),
        url=args.url.strip(),
        cartridge_id=args.id,
    )
    out = args.out or (DRAFTS / f"{cartridge['id']}.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(cartridge, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"jit_drafter: wrote {out} (DRAFT — human approve required)", file=sys.stderr)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
