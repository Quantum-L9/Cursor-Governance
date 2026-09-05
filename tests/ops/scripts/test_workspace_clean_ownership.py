"""A tracked file is repo content, even when it matches a machine-local glob.

`workspace-clean-routing.yaml` lists `.claude/` and `.mcp.json` under
`skip_machine_local`, while the Claude adapter's installer classifies
`.claude/settings.json` and `.claude/hooks/` as committable consumer wiring and
excludes them only when untracked. Both cannot be right.

`classify_path` tested the glob before tracked-ness, so the machine-local list
won: a committed `.mcp.json` — tracked in Cursor-Governance itself — classified
`machine_local` and never shipped, silently dropping a real edit to repo
content. Tracked-ness is the ownership signal on both sides now.

`never_commit` is deliberately still unconditional: a tracked secret is a
secret.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "workspace_clean.py"
ROUTING = ROOT / "ops" / "config" / "workspace-clean-routing.yaml"


@pytest.fixture(scope="module")
def clean():
    spec = importlib.util.spec_from_file_location("_workspace_clean", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def routing():
    import yaml

    return yaml.safe_load(ROUTING.read_text(encoding="utf-8"))


def test_machine_local_glob_still_skips_an_untracked_artifact(clean, routing) -> None:
    """The list keeps doing its job for the activation artifacts it exists for."""
    verdict = clean.classify_path(
        ".claude/settings.json", routing=routing, current_dest=None, tracked=False
    )
    assert verdict["action"] == "skip"
    assert verdict["reason"] == "machine_local"


def test_tracked_file_matching_a_machine_local_glob_is_repo_content(clean, routing) -> None:
    """The reported contradiction: a committed .mcp.json must not be dropped."""
    verdict = clean.classify_path(
        ".mcp.json", routing=routing, current_dest="cursor-governance", tracked=True
    )
    assert verdict["action"] != "skip", "tracked repo content classified as machine-local"
    assert verdict["reason"] == "tracked_current_remote"


def test_committed_consumer_wiring_is_shippable(clean, routing) -> None:
    """`.claude/settings.json` is committable wiring where a repo commits it."""
    verdict = clean.classify_path(
        ".claude/settings.json", routing=routing, current_dest="cursor-governance", tracked=True
    )
    assert verdict["action"] == "ship"


def test_never_commit_still_wins_over_tracked_ness(clean, routing) -> None:
    """A tracked secret is still a secret — that list stays unconditional."""
    verdict = clean.classify_path(
        ".env", routing=routing, current_dest="cursor-governance", tracked=True
    )
    assert verdict["action"] == "skip"
    assert verdict["reason"] == "never_commit"
