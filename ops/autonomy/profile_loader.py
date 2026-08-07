#!/usr/bin/env python3
"""Load ops/autonomy/surface_profile.yaml for SessionStart / projectors / tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

PROFILE_REL = Path("ops/autonomy/surface_profile.yaml")


def governance_root() -> Path:
    return Path.home() / ".cursor-governance"


def profile_path(root: Path | None = None) -> Path:
    return (root or governance_root()) / PROFILE_REL


def load_profile(root: Path | None = None) -> dict[str, Any]:
    path = profile_path(root)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"surface profile must be a mapping: {path}")
    return data


def session_start_block(root: Path | None = None) -> str:
    return str(load_profile(root).get("session_start_block") or "").rstrip() + "\n"


def llm_rules_override(root: Path | None = None) -> str:
    return str(load_profile(root).get("llm_rules_override") or "").rstrip() + "\n"


def block_sha256(root: Path | None = None) -> str:
    return hashlib.sha256(session_start_block(root).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    print(session_start_block(), end="")
