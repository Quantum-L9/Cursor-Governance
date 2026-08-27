#!/usr/bin/env python3
# RENDER_TARGET_PROFILE: deterministic render from validated IR only.
import os
import sys

from _common import emit, fail, load_json, policy


def _front(ir, keys):
    authority = ir.get("authority", {})
    source = {
        "name": ir["identity"]["name"],
        "version": ir["identity"]["version"],
        "updated": ir["identity"].get("updated", ""),
        "description": ir["objective"],
        "role": authority.get("role", ir["primary_family"] + "_skill"),
        "tags": "[" + ", ".join(authority.get("tags", ["l9"])) + "]",
        "owner": authority.get("owner", "unassigned"),
    }
    lines = ["---"] + [key + ": " + str(source[key]) for key in keys if source.get(key)] + ["---"]
    return "\n".join(lines)


def render(ir, profile_name):
    profiles = policy("target-profiles.yaml")["profiles"]
    if profile_name not in profiles:
        raise KeyError("unknown profile " + profile_name)
    spec = profiles[profile_name]
    if spec.get("status") == "unverified":
        raise PermissionError("profile " + profile_name + " gated: " + str(spec.get("gate")))
    output = [
        _front(ir, spec["frontmatter_required"]),
        "",
        "# " + ir["identity"]["name"] + " v" + ir["identity"]["version"],
        "",
        "## Activate when",
        "",
    ]
    output += ["- " + activation for activation in ir["activation"]]
    output += ["", "## Do not activate", ""] + [
        "- " + exclusion for exclusion in ir["non_activation"]
    ]
    output += ["", "## Invariants", ""] + ["- " + item for item in ir["invariants"]]
    if profile_name == "l9":
        authority = ir.get("authority", {})
        output += [
            "",
            "## Runtime",
            "",
            "Canonical DAG: " + str(authority.get("canonical_dag")),
            "Registry id: " + str(authority.get("dag_registry_id")),
        ]
    return "\n".join(output) + "\n"


def main(argv):
    if len(argv) < 3:
        return fail("usage: render_target_profile.py <skill-ir.json> <profile> [outdir]")
    ir = load_json(argv[1])
    try:
        text = render(ir, argv[2])
    except (KeyError, PermissionError) as exc:
        return emit({"stage": "RENDER_TARGET_PROFILE", "status": "FAIL", "error": str(exc)}, 2)
    if len(argv) > 3:
        os.makedirs(argv[3], exist_ok=True)
        with open(os.path.join(argv[3], "SKILL.md"), "w", encoding="utf-8") as handle:
            handle.write(text)
    return emit(
        {
            "stage": "RENDER_TARGET_PROFILE",
            "status": "PASS",
            "profile": argv[2],
            "bytes": len(text),
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
