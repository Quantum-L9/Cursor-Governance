#!/usr/bin/env python3
# STATIC_VALIDATE: structural, partition, graph, eval-coverage and reference checks.
import os
import re
import sys

from _common import PACK, contract, emit, load_json, policy
from bind_inputs import structural_validate


def check_partition(ir):
    routing = policy("runtime-routing.yaml")
    deterministic = set(routing["deterministic_code"])
    semantic = set(routing["bounded_llm"])
    errors = []
    for node in ir.get("workflow", {}).get("nodes", []):
        implementation = node.get("impl") or ""
        if node["kind"] == "bounded_llm" and implementation in deterministic:
            errors.append(node["id"] + ": deterministic work routed to an LLM node")
        if node["kind"] == "deterministic" and implementation in semantic:
            errors.append(node["id"] + ": semantic work routed to a deterministic node")
        if node["kind"] == "deterministic" and not implementation:
            errors.append(node["id"] + ": deterministic node has no impl")
    return errors


def check_graph(ir):
    nodes = {node["id"]: node for node in ir.get("workflow", {}).get("nodes", [])}
    errors = []
    if ir.get("workflow", {}).get("entrypoint") not in nodes:
        errors.append("workflow.entrypoint does not resolve to a node")
    for node in nodes.values():
        for target in node.get("next", []):
            if target not in nodes:
                errors.append(node["id"] + ": dangling next -> " + target)
    if not any(node["kind"] == "terminal" for node in nodes.values()):
        errors.append("workflow has no terminal node")
    return errors


def check_evals(ir):
    errors = []
    classes = {item["class"] for item in ir.get("activation_evals", [])}
    for required in ("positive", "negative", "sibling_collision"):
        if required not in classes:
            errors.append("activation_evals: missing required class " + required)
    family = ir.get("primary_family")
    required_ids = {item["id"] for item in policy("behavior-evals.yaml").get(family, [])}
    present_ids = {item["id"] for item in ir.get("behavior_evals", [])}
    for missing in sorted(required_ids - present_ids):
        errors.append("behavior_evals: missing family-required eval " + missing)
    return errors


def check_pack_files(pack=None):
    pack = pack or str(PACK)
    errors = []
    contracts_dir = os.path.join(pack, "contracts")
    filenames = sorted(os.listdir(contracts_dir)) if os.path.isdir(contracts_dir) else []
    for filename in filenames:
        if filename.endswith(".json"):
            try:
                load_json(os.path.join(contracts_dir, filename))
            except Exception as exc:
                errors.append("contracts/" + filename + ": parse error: " + str(exc))

    policies_dir = os.path.join(pack, "policies")
    import yaml

    filenames = sorted(os.listdir(policies_dir)) if os.path.isdir(policies_dir) else []
    for filename in filenames:
        if filename.endswith(".yaml"):
            try:
                with open(os.path.join(policies_dir, filename), encoding="utf-8") as handle:
                    yaml.safe_load(handle)
            except Exception as exc:
                errors.append("policies/" + filename + ": parse error: " + str(exc))

    scripts_dir = os.path.join(pack, "scripts")
    filenames = sorted(os.listdir(scripts_dir)) if os.path.isdir(scripts_dir) else []
    for filename in filenames:
        if filename.endswith(".py"):
            with open(os.path.join(scripts_dir, filename), encoding="utf-8") as handle:
                source = handle.read()
            try:
                compile(source, filename, "exec")
            except SyntaxError as exc:
                errors.append("scripts/" + filename + ": syntax error: " + str(exc))

    skill_md = os.path.join(pack, "SKILL.md")
    if os.path.isfile(skill_md):
        with open(skill_md, encoding="utf-8") as handle:
            text = handle.read()
        if re.search(r"zero[-_ ]?stub", text, re.I):
            errors.append("SKILL.md: retired term zero_stub is present")
        references = re.findall(r"`([A-Za-z0-9_./-]+\.(?:json|yaml|py|md))`", text)
        for reference in references:
            is_local = "/" in reference and not reference.startswith("workflows/")
            if is_local and not os.path.exists(os.path.join(pack, reference)):
                errors.append("SKILL.md: dangling reference " + reference)
    return errors


def main(argv):
    errors = []
    if len(argv) > 1 and argv[1] != "-":
        ir = load_json(argv[1])
        errors += structural_validate(ir, contract("skill-ir.schema.json"))
        errors += check_partition(ir)
        errors += check_graph(ir)
        errors += check_evals(ir)
    errors += check_pack_files(argv[2] if len(argv) > 2 else None)
    return emit(
        {
            "stage": "STATIC_VALIDATE",
            "status": "FAIL" if errors else "PASS",
            "error_count": len(errors),
            "errors": errors,
        },
        2 if errors else 0,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
