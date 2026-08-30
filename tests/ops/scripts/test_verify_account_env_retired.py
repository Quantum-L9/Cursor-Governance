"""Retired account fields must fail the verifier, not pass as "all match".

The verifier compared only the EXPECTED set, so a variable the contract had
retired could sit live in the account environment while the report read
`OK: all 31 expected variables match`. That is how `L9_CAPABILITY_BROKER_URL`
survived in a real environment for as long as it did — three sentences after the
example file that calls it "deliberately absent".
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "environment" / "agents" / "adapters" / "claude-code"))

import verify_account_env as vae  # noqa: E402


def test_retired_field_is_reported() -> None:
    assert vae.retired_present({"L9_CAPABILITY_BROKER_URL": "https://broker.example/x"}) == [
        "L9_CAPABILITY_BROKER_URL"
    ]


def test_empty_or_absent_retired_field_is_not_reported() -> None:
    """Absence is the correct state; an empty string is not a value."""
    assert vae.retired_present({}) == []
    assert vae.retired_present({"L9_CAPABILITY_BROKER_URL": "  "}) == []


def test_retired_field_denies_ok(tmp_path: Path) -> None:
    """A retired field must flip `ok` false — reporting it is not enough."""
    expected = vae.parse_env_example()
    env = dict(expected)
    env["L9_STUB_REVISION"] = vae.stub_revision_expected()
    clean = vae.run(env=env, session_env=tmp_path / "absent.env")
    assert clean["retired_present"] == []

    env["L9_MEMORY_HTTP_URL"] = "https://retired.example/memory"
    dirty = vae.run(env=env, session_env=tmp_path / "absent.env")
    assert dirty["retired_present"] == ["L9_MEMORY_HTTP_URL"]
    assert dirty["ok"] is False


def test_legitimate_overrides_are_not_flagged() -> None:
    """Noise is how a real finding gets scrolled past.

    A per-shell GRAPHITI_GROUP_ID is the documented one-off override, the stub
    itself exports L9_GOVERNANCE_DIR, and install.sh derives the SONAR project
    keys per repository. None of them may be reported as retired.
    """
    live = {
        "GRAPHITI_GROUP_ID": "l9-ci-core",
        "L9_GOVERNANCE_DIR": "/root/.cursor-governance",
        "SONAR_PROJECT_KEY": "some-project",
        "SONAR_ORG_KEY": "some-org",
    }
    assert vae.retired_present(live) == []


def test_retired_and_prohibited_sets_are_disjoint() -> None:
    """Two different failures with two different remedies; never double-reported."""
    assert not (vae.RETIRED_FIELDS & vae.PROHIBITED_PRESENT)
