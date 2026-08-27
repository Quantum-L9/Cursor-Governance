#!/usr/bin/env python3
# Compiler self-host validation. Runs the compiler against its own pack.
import json
import os
import sys

import check_capability_closure
import classify_skill_profile
import evaluate_activation
import normalize_skill_ir
import render_target_profile
import scan_skill_topology
import static_validate
from _common import PACK, emit

IR = os.path.join(str(PACK), "tests", "fixtures", "self-ir.json")
REPO_FIXTURE = os.path.join(str(PACK), "tests", "fixtures", "repo", "skills")
LIVE_SKILLS = {
    "l9-dag-authoring",
    "l9-structured-reasoning",
    "l9-wire-skill-into-repo",
}


def _load_ir():
    with open(IR, encoding="utf-8") as handle:
        return json.load(handle)


def run():
    steps = []
    ir = normalize_skill_ir.normalize(_load_ir())
    steps.append(("normalize_skill_ir.validate", not normalize_skill_ir.validate(ir)))
    steps.append(("normalize_skill_ir.round_trip", normalize_skill_ir.round_trip(ir)))

    static_exit = static_validate.main(["self_test", IR, str(PACK)])
    steps.append(("static_validate", static_exit == 0))

    closure = check_capability_closure.check(
        ir,
        str(PACK.parent.parent),
        live_skills=LIVE_SKILLS,
    )
    steps.append(("capability_closure", closure["result"] in ("CLOSED", "RUNTIME_BOUND")))

    activation = evaluate_activation.evaluate(ir, live_skills=LIVE_SKILLS)
    steps.append(("activation_eval", activation["status"] == "PASS"))

    portable = render_target_profile.render(ir, "portable")
    l9_profile = render_target_profile.render(ir, "l9")
    steps.append(
        (
            "deterministic_render",
            portable == render_target_profile.render(ir, "portable"),
        )
    )
    steps.append(
        (
            "profile_specific_validation",
            "Canonical DAG" in l9_profile and "Canonical DAG" not in portable,
        )
    )

    gated = False
    try:
        render_target_profile.render(ir, "cursor")
    except PermissionError:
        gated = True
    steps.append(("unverified_profile_is_gated", gated))

    profile = classify_skill_profile.classify("rebuild a compiler that renders skill artifacts")
    steps.append(("classification_compiler", profile["primary_family"] == "compiler"))

    live = scan_skill_topology.enumerate_live_skills(REPO_FIXTURE)
    decision, _, _, _ = scan_skill_topology.decide(
        {
            "proposed_name": "l9-skill-compiler",
            "existing_skill": "l9-skill-compiler",
        },
        live,
    )
    steps.append(("topology_replace_existing", decision == "REPLACE_EXISTING"))
    return steps, closure, activation


def main(argv):
    del argv
    steps, closure, activation = run()
    failed = [name for name, ok in steps if not ok]
    return emit(
        {
            "stage": "SELF_TEST",
            "status": "FAIL" if failed else "PASS",
            "checks": [
                {"id": name, "status": "pass" if ok else "fail"} for name, ok in steps
            ],
            "failed": failed,
            "capability_closure_result": closure["result"],
            "activation_status": activation["status"],
        },
        2 if failed else 0,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
