#!/usr/bin/env python3
# SCAN_SKILL_TOPOLOGY: deterministic. Creation is never the default outcome.
import os
import re
import sys

from _common import REPO, emit, fail, load_json


def parse_skill_metadata(skill_md):
    meta = {}
    lines = []
    inside = False
    with open(skill_md, encoding="utf-8") as handle:
        for line in handle:
            if line.strip() == "---":
                if inside:
                    break
                inside = True
                continue
            if inside:
                lines.append(line.rstrip("\n"))
    key = None
    for line in lines:
        match = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if match:
            key = match.group(1)
            meta[key] = match.group(2).strip()
        elif key and line.startswith(" "):
            meta[key] = (meta.get(key, "") + " " + line.strip()).strip()
    return meta


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


def candidates(subject, live):
    wanted = (
        tokens(subject.get("proposed_name", ""))
        | tokens(subject.get("domain", ""))
        | tokens(subject.get("stated_objective", ""))
    )
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


def decide(subject, live):
    existing = subject.get("existing_skill")
    candidate_rows = candidates(subject, live)
    evidence = ["live_skills_enumerated=" + str(len(live))]
    if existing and existing in live:
        evidence.append("existing_skill_present=" + existing)
        return "REPLACE_EXISTING", evidence, candidate_rows, "deterministic_rule"
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
