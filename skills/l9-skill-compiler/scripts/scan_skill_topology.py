#!/usr/bin/env python3
# SCAN_SKILL_TOPOLOGY: deterministic. Creation is never the default outcome.
import os
import re
import sys

import yaml
from _common import REPO, emit, fail, load_json


def parse_skill_metadata(skill_md):
    with open(skill_md, encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    parsed = yaml.safe_load(text[4:end]) or {}
    if not isinstance(parsed, dict):
        return {}
    nested = parsed.get("metadata")
    if isinstance(nested, dict):
        for key, value in nested.items():
            parsed.setdefault(key, value)
    return parsed


def enumerate_live_skills(skills_dir=None):
    root = skills_dir or os.path.join(str(REPO), "skills")
    output = {}
    if not os.path.isdir(root):
        return output
    for name in sorted(os.listdir(root)):
        if name.startswith(("_", ".")):
            continue
        skill_md = os.path.join(root, name, "SKILL.md")
        if os.path.isfile(skill_md):
            output[name] = parse_skill_metadata(skill_md)
    return output


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def uninformative_tokens(live):
    """Tokens every live skill shares, which therefore prove no ownership.

    A namespace prefix is the common case: every skill in this repository is
    named ``l9-*``, so counting ``l9`` as capability evidence gives every
    candidate a free point and biases the decision toward EXTEND_EXISTING on no
    real overlap. Derived from the live corpus rather than a hardcoded list.
    """
    if len(live) < 2:
        return set()
    sets = [tokens(meta.get("role", "")) | tokens(name) for name, meta in live.items()]
    return set.intersection(*sets)


def candidates(subject, live):
    wanted = (
        tokens(subject.get("proposed_name", ""))
        | tokens(subject.get("domain", ""))
        | tokens(subject.get("stated_objective", ""))
    ) - uninformative_tokens(live)
    scored = []
    for name, meta in live.items():
        trigger_tokens = tokens(meta.get("description", ""))
        capability_tokens = tokens(meta.get("role", "")) | tokens(name)
        trigger_overlap = len(wanted & trigger_tokens)
        capability_overlap = len(wanted & capability_tokens)
        if trigger_overlap or capability_overlap:
            scored.append(
                {
                    "skill": name,
                    "trigger_overlap": trigger_overlap,
                    "capability_overlap": capability_overlap,
                    "specificity": len(capability_tokens),
                }
            )
    scored.sort(
        key=lambda row: (
            -row["capability_overlap"],
            -row["specificity"],
            -row["trigger_overlap"],
        )
    )
    return scored


POLICY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "policies")


def load_topology_policy():
    """dag_skill_ownership rules. Absent policy disables the rule, never invents one."""
    path = os.path.join(POLICY, "topology-ownership.yaml")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle) or {}
    rule = parsed.get("dag_skill_ownership")
    return rule if isinstance(rule, dict) else {}


def find_owner(live, owner_role):
    """The live skill declaring owner_role, if exactly one does."""
    owners = [name for name, meta in live.items() if str(meta.get("role", "")) == owner_role]
    return owners[0] if len(owners) == 1 else None


def dag_skill_ownership_violation(subject, live, rule=None):
    """A DAG does not justify a Skill.

    Fires when the subject is DAG-shaped (carries a graph-runtime marker) but
    does not itself claim the DAG lifecycle capability (carries no lifecycle
    verb). Such a subject is asking for a sibling Skill around an execution
    graph that some other capability already owns.

    Returns (decision, evidence) or None when the rule does not apply.
    """
    rule = load_topology_policy() if rule is None else rule
    if not rule:
        return None
    wanted = (
        tokens(subject.get("proposed_name", ""))
        | tokens(subject.get("domain", ""))
        | tokens(subject.get("stated_objective", ""))
    )
    markers = wanted & set(rule.get("runtime_markers", []))
    if not markers:
        return None
    if wanted & set(rule.get("lifecycle_verbs", [])):
        return None  # the capability IS DAG lifecycle management; creation is legitimate
    evidence = ["dag_skill_ownership_marker=" + ",".join(sorted(markers))]
    owner = find_owner(live, rule.get("owner_role", "dag_lifecycle_owner"))
    if not owner:
        evidence.append("no_live_dag_lifecycle_owner")
        return str(rule.get("on_violation_without_owner", "ESCALATE_TO_BOUNDED_LLM")), evidence
    evidence.append("dag_lifecycle_owner=" + owner)
    evidence.append("dag_is_runtime_artifact_of_owning_capability_not_a_skill")
    return str(rule.get("on_violation", "REJECT_NEW_SKILL")), evidence


def decide(subject, live):
    existing = subject.get("existing_skill")
    candidate_rows = candidates(subject, live)
    evidence = ["live_skills_enumerated=" + str(len(live))]
    if existing and existing in live:
        evidence.append("existing_skill_present=" + existing)
        return "REPLACE_EXISTING", evidence, candidate_rows, "deterministic_rule"
    violation = dag_skill_ownership_violation(subject, live)
    if violation:
        decision, rule_evidence = violation
        evidence.extend(rule_evidence)
        decided_by = (
            "bounded_llm" if decision == "ESCALATE_TO_BOUNDED_LLM" else "deterministic_rule"
        )
        return decision, evidence, candidate_rows, decided_by
    if candidate_rows and candidate_rows[0]["capability_overlap"] >= 2:
        evidence.append(
            "nearest_owner="
            + candidate_rows[0]["skill"]
            + " capability_overlap="
            + str(candidate_rows[0]["capability_overlap"])
        )
        return "EXTEND_EXISTING", evidence, candidate_rows, "deterministic_rule"
    if len(candidate_rows) >= 3:
        evidence.append(
            "multiple_partial_owners=" + ",".join(row["skill"] for row in candidate_rows[:3])
        )
        return "ESCALATE_TO_BOUNDED_LLM", evidence, candidate_rows, "bounded_llm"
    if (
        candidate_rows
        and candidate_rows[0]["trigger_overlap"]
        and not candidate_rows[0]["capability_overlap"]
    ):
        evidence.append("trigger_overlap_only=" + candidate_rows[0]["skill"])
        return "CREATE_NEW", evidence, candidate_rows, "deterministic_rule"
    if not candidate_rows:
        evidence.append("no_ownership_candidates")
        return "CREATE_NEW", evidence, candidate_rows, "deterministic_rule"
    evidence.append("weak_overlap_nearest=" + candidate_rows[0]["skill"])
    return "ESCALATE_TO_BOUNDED_LLM", evidence, candidate_rows, "bounded_llm"


def main(argv):
    if len(argv) < 2:
        return fail("usage: scan_skill_topology.py <compile-request.json> [skills_dir]")
    req = load_json(argv[1])
    live = enumerate_live_skills(argv[2] if len(argv) > 2 else None)
    decision, evidence, candidate_rows, decided_by = decide(req.get("subject", {}), live)
    return emit(
        {
            "stage": "SCAN_SKILL_TOPOLOGY",
            "decision": decision,
            "decided_by": decided_by,
            "evidence": evidence,
            "candidates": candidate_rows[:10],
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
