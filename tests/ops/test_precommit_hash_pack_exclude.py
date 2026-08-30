"""Issue #374: eof-fixer / trailing-whitespace skip hash-anchored plan packs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".pre-commit-config.yaml"

PACK_REL = "docs/plans/claude-code/program-execution-remediation/MANIFEST.yaml"
FLAT_REL = "docs/plans/claude-code/contract-v31-fixes.plan.md"
DIST_REL = "dist/index.js"


def _hook_exclude(hook_id: str) -> str:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    for repo in data["repos"]:
        for hook in repo.get("hooks") or []:
            if hook.get("id") == hook_id:
                return str(hook.get("exclude") or "")
    raise AssertionError(f"hook {hook_id} missing")


def test_eof_and_whitespace_share_dist_and_pack_exclude() -> None:
    eof = _hook_exclude("end-of-file-fixer")
    ws = _hook_exclude("trailing-whitespace")
    assert eof == ws
    rx = re.compile(eof)
    assert rx.search(PACK_REL)
    assert rx.search(DIST_REL)
    assert rx.search("docs/plans/claude-code/future-pack/foo.yaml")
    assert not rx.search(FLAT_REL)
    assert not rx.search("docs/plans/claude-code/README.md")
