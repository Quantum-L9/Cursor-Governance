# ruff: noqa: E402
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import classify_skill_profile as cls
import normalize_skill_ir as nsi
import render_target_profile as rtp


def ir():
    with open(os.path.join(HERE, "fixtures", "self-ir.json"), encoding="utf-8") as handle:
        return json.load(handle)


def test_compiler_family_is_deterministic():
    profile = cls.classify("rebuild a compiler that renders skill artifacts")
    assert profile["primary_family"] == "compiler"
    assert profile["decided_by"] == "deterministic_rule"


def test_diagnostic_family_is_deterministic():
    profile = cls.classify("audit and inspect the repository for drift")
    assert profile["primary_family"] == "diagnostic"


def test_ambiguity_escalates_to_bounded_llm():
    profile = cls.classify("audit and then deploy and also compile things")
    assert profile["primary_family"] is None
    assert profile["decided_by"] == "bounded_llm"


def test_no_match_escalates():
    profile = cls.classify("xyzzy plugh frobnicate")
    assert profile["decided_by"] == "bounded_llm"


def test_dag_trait_requires_registration():
    profile = cls.classify("rebuild a compiler that renders skill artifacts")
    assert "canonical_dag_registration" in cls.apply_trait_implications(profile)


def test_render_is_deterministic():
    data = nsi.normalize(ir())
    assert rtp.render(data, "portable") == rtp.render(data, "portable")


def test_l9_profile_carries_dag_metadata_portable_does_not():
    data = nsi.normalize(ir())
    assert "Canonical DAG" in rtp.render(data, "l9")
    assert "Canonical DAG" not in rtp.render(data, "portable")


def test_unverified_profiles_are_gated():
    data = nsi.normalize(ir())
    for profile in ("cursor", "claude_code", "openai"):
        with pytest.raises(PermissionError):
            rtp.render(data, profile)


def test_ir_round_trips_and_validates():
    data = nsi.normalize(ir())
    assert nsi.validate(data) == []
    assert nsi.round_trip(data)
