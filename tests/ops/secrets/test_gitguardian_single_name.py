"""#869: the GitGuardian API key has exactly one Infisical name.

The cloud environment once carried a network secret for api.gitguardian.com
outside Infisical. The vault-side half of the fix is that every consumer in
this repository resolves one inventory name, GITGUARDIAN_API_KEY.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import legacy_refs  # noqa: E402

NAME = "GITGUARDIAN_API_KEY"
HOST = "api.gitguardian.com"


def _inventory() -> dict:
    return yaml.safe_load((SECRETS_DIR / "infisical-cursor-governance.yaml").read_text())


def test_inventory_has_exactly_one_gitguardian_name() -> None:
    keys = _inventory()["root_env_keys"]
    assert [k for k in keys if "GITGUARDIAN" in k.upper()] == [NAME]


def test_gitguardian_host_binds_the_inventory_name() -> None:
    caps = yaml.safe_load((SECRETS_DIR / "capabilities.yaml").read_text())
    entries = caps["capabilities"] if isinstance(caps, dict) else caps
    for_host = [c for c in entries if c.get("upstream_host") == HOST]
    assert for_host, f"no capability declares {HOST}"
    for cap in for_host:
        assert cap["secret_refs"] == [NAME]


def test_every_gitguardian_consumer_reads_the_one_name() -> None:
    assert legacy_refs.ENV_MAP[("gitguardian", "apikey")] == NAME
    plan = json.loads((SECRETS_DIR / "actions-secret-sync.json").read_text())
    vault = {e["vault_name"] for e in plan["secrets"] if "GITGUARDIAN" in e["secret"]}
    assert vault == {NAME}


def test_inventory_records_the_network_secret_disposition() -> None:
    notes = " ".join(n for n in _inventory()["notes"] if isinstance(n, str))
    assert f"{NAME} is the one Infisical name" in notes
    assert HOST in notes
