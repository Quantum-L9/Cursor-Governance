# ruff: noqa: E402
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import scan_skill_topology as st

FIX = os.path.join(HERE, "fixtures", "repo", "skills")


def live():
    return st.enumerate_live_skills(FIX)


def test_fixture_repo_enumerates():
    assert set(live()) >= {"l9-skill-compiler", "l9-dag-authoring", "l9-wire-skill-into-repo"}


def test_nested_metadata_role_is_visible():
    assert live()["l9-dag-authoring"]["role"] == "l9_dag_authoring"


def test_replace_existing_when_named():
    decision, _, _, decided_by = st.decide(
        {"proposed_name": "l9-skill-compiler", "existing_skill": "l9-skill-compiler"},
        live(),
    )
    assert decision == "REPLACE_EXISTING"
    assert decided_by == "deterministic_rule"


def test_creation_is_not_default_for_overlapping_domain():
    decision, _, _, _ = st.decide(
        {
            "proposed_name": "l9-dag-authoring",
            "domain": "dag authoring",
            "stated_objective": "author l9 dag workflows",
        },
        live(),
    )
    assert decision != "CREATE_NEW"


def test_create_new_when_no_candidates():
    decision, evidence, _, _ = st.decide(
        {
            "proposed_name": "zzz-quantum-widget",
            "domain": "unrelated",
            "stated_objective": "xyzzy plugh",
        },
        live(),
    )
    assert decision == "CREATE_NEW"
    assert "no_ownership_candidates" in evidence


def test_trigger_overlap_is_distinguished_from_capability_overlap():
    rows = st.candidates(
        {
            "proposed_name": "compile",
            "domain": "skills",
            "stated_objective": "compile or rebuild reusable skills",
        },
        live(),
    )
    assert any(row["trigger_overlap"] for row in rows)
    assert all("capability_overlap" in row for row in rows)
