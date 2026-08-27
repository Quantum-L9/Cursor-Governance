#!/usr/bin/env python3
# CLASSIFY_SKILL_PROFILE: deterministic rules first; bounded LLM only on ambiguity.
import re
import sys

from _common import emit, fail, load_json, policy

RULES = [
    ("compiler", r"compil|render|transform|codegen"),
    ("orchestrator", r"orchestrat|coordinate coordinat|\bdag\b"),
    ("lifecycle", r"lifecycle|durable state|resume|checkpoint"),
    ("adapter", r"adapter|bind external|third-party|connector"),
    ("operator", r"mutate|deploy|remediat|migrat"),
    ("diagnostic", r"diagnos|audit|inspect|triage"),
    ("advisory", r"advis|guidance|recommend|doctrine|methodolog"),
]


def classify(objective):
    text = (objective or "").lower()
    hits = [(family, rule) for family, rule in RULES if re.search(rule, text)]
    families = policy("skill-families.yaml")["families"]
    if len(hits) == 1:
        family = hits[0][0]
        return {
            "primary_family": family,
            "traits": families[family]["default_traits"],
            "evidence": ["deterministic_rule_matched:" + hits[0][1]],
            "decided_by": "deterministic_rule",
            "rule_id": hits[0][1],
        }
    reason = (
        "no_deterministic_rule_matched"
        if not hits
        else "ambiguous_multi_family_match:" + ",".join(family for family, _ in hits)
    )
    return {
        "primary_family": None,
        "traits": None,
        "evidence": [reason],
        "decided_by": "bounded_llm",
        "rule_id": None,
    }


def apply_trait_implications(profile):
    requirements = []
    if not profile.get("traits"):
        return requirements
    for rule in policy("skill-families.yaml").get("trait_implications", []):
        if all(profile["traits"].get(key) == value for key, value in rule.get("if", {}).items()):
            requirements += rule.get("then_required", [])
    return sorted(set(requirements))


def main(argv):
    if len(argv) < 2:
        return fail("usage: classify_skill_profile.py <compile-request.json>")
    req = load_json(argv[1])
    profile = classify(req.get("subject", {}).get("stated_objective", ""))
    status = "ESCALATE_TO_BOUNDED_LLM" if profile["primary_family"] is None else "PASS"
    return emit(
        {
            "stage": "CLASSIFY_SKILL_PROFILE",
            "profile": profile,
            "derived_requirements": apply_trait_implications(profile),
            "status": status,
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
