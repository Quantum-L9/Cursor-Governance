# ruff: noqa: E402
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
_existing = sys.modules.get("_common")
_want = os.path.realpath(os.path.join(SCRIPTS, "_common.py"))
if _existing is not None:
    _have = os.path.realpath(getattr(_existing, "__file__", "") or "")
    if _have != _want:
        sys.modules.pop("_common", None)

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


def test_namespace_prefix_is_not_ownership_evidence():
    """Every live skill is named l9-*, so the prefix proves nothing about ownership."""
    assert st.uninformative_tokens(live()) == {"l9"}
    unrelated = {"domain": "unrelated", "stated_objective": "xyzzy plugh"}
    bare, _, _, _ = st.decide({"proposed_name": "zzz-quantum-widget", **unrelated}, live())
    prefixed, _, _, _ = st.decide({"proposed_name": "l9-zzz-quantum-widget", **unrelated}, live())
    assert prefixed == bare == "CREATE_NEW"


def test_a_single_real_token_match_does_not_deterministically_claim_ownership():
    rows = st.candidates(
        {"proposed_name": "l9-dag-authoring", "domain": "", "stated_objective": ""},
        live(),
    )
    by_skill = {row["skill"]: row for row in rows}
    # "dag" and "authoring" are real evidence; "l9" must not add a free point.
    assert by_skill["l9-dag-authoring"]["capability_overlap"] == 2
    assert "l9-structured-reasoning" not in by_skill


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


# --- dag_skill_ownership invariant ---------------------------------------
# "The existence of a DAG does not justify a Skill." Policy:
# ../policies/topology-ownership.yaml

OWNER_LIVE = {
    "l9-dag-authoring": {"role": "dag_lifecycle_owner", "description": "dag lifecycle"},
    "l9-gmp-protocol": {"role": "skill_entrypoint", "description": "phased execution"},
}


def test_policy_loads_and_declares_the_invariant():
    rule = st.load_topology_policy()
    assert rule, "topology-ownership.yaml must be readable from the scanner"
    assert "does not justify a Skill" in rule["invariant"]
    assert rule["on_violation"] == "REJECT_NEW_SKILL"


def test_dag_wrapper_skill_is_rejected_when_a_lifecycle_owner_exists():
    decision, evidence, _, decided_by = st.decide(
        {"proposed_name": "l9-inspect-dag", "stated_objective": "wrap the inspect dag"},
        OWNER_LIVE,
    )
    assert decision == "REJECT_NEW_SKILL"
    assert decided_by == "deterministic_rule"
    assert any("dag_lifecycle_owner=l9-dag-authoring" in row for row in evidence)


def test_the_dag_lifecycle_capability_itself_is_not_rejected():
    """A lifecycle verb means the capability IS DAG management; creation is legitimate."""
    for objective in (
        "author and register l9 dags",
        "validate dag structure before registration",
        "bind a command to a dag as a thin trigger",
    ):
        assert (
            st.dag_skill_ownership_violation(
                {"proposed_name": "l9-dag-authoring", "stated_objective": objective}, OWNER_LIVE
            )
            is None
        ), objective


def test_non_dag_subjects_are_untouched_by_the_rule():
    for subject in (
        {"proposed_name": "l9-auditing-security", "stated_objective": "scan for exposed secrets"},
        {"proposed_name": "l9-incident-response", "stated_objective": "triage a sev1"},
    ):
        assert st.dag_skill_ownership_violation(subject, OWNER_LIVE) is None


def test_missing_owner_escalates_rather_than_silently_rejecting():
    no_owner = {"l9-gmp-protocol": {"role": "skill_entrypoint", "description": "phases"}}
    decision, evidence, _, decided_by = st.decide(
        {"proposed_name": "l9-harvest-dag", "stated_objective": "run the harvest deploy dag"},
        no_owner,
    )
    assert decision == "ESCALATE_TO_BOUNDED_LLM"
    assert decided_by == "bounded_llm"
    assert "no_live_dag_lifecycle_owner" in evidence


def test_absent_policy_disables_the_rule_rather_than_inventing_one():
    assert (
        st.dag_skill_ownership_violation(
            {"proposed_name": "l9-inspect-dag", "stated_objective": "wrap the inspect dag"},
            OWNER_LIVE,
            rule={},
        )
        is None
    )


def test_an_explicit_rebuild_of_the_owner_still_wins_over_the_rule():
    """REPLACE_EXISTING is evaluated first; the invariant must not block a rebuild."""
    decision, _, _, _ = st.decide(
        {
            "proposed_name": "l9-dag-authoring",
            "existing_skill": "l9-dag-authoring",
            "stated_objective": "rebuild the dag pack",
        },
        OWNER_LIVE,
    )
    assert decision == "REPLACE_EXISTING"


def test_the_live_repo_declares_exactly_one_dag_lifecycle_owner():
    live_repo = st.enumerate_live_skills(os.path.join(HERE, "..", "..", "..", "skills"))
    assert st.find_owner(live_repo, "dag_lifecycle_owner") == "l9-dag-authoring"
