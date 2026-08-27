#!/usr/bin/env python3
# CAPABILITY_CLOSURE: fully deterministic. Replaces the retired zero_stub concept.
import os
import sys
from datetime import UTC, datetime

from _common import REPO, emit, fail, load_json, policy

_POLICY = None


def _policy():
    global _POLICY
    if _POLICY is None:
        _POLICY = policy("capability-closure.yaml")
    return _POLICY


def _placeholder(text):
    value = text or ""
    return any(marker.lower() in value.lower() for marker in _policy()["placeholder_markers"])


def _live(repo_root):
    skill_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skill_dir):
        return set()
    return {
        name
        for name in os.listdir(skill_dir)
        if os.path.isfile(os.path.join(skill_dir, name, "SKILL.md"))
    }


def _reachable(ir):
    nodes = {node["id"]: node for node in ir.get("workflow", {}).get("nodes", [])}
    start = ir.get("workflow", {}).get("entrypoint")
    seen = set()
    stack = [start] if start in nodes else []
    while stack:
        current = stack.pop()
        if current in seen or current not in nodes:
            continue
        seen.add(current)
        stack += list(nodes[current].get("next", []))
    capabilities = set()
    for node_id in seen:
        capabilities |= set(nodes[node_id].get("capabilities", []))
    return seen, capabilities


def _cycles(capabilities):
    graph = {
        capability["id"]: list((capability.get("binding") or {}).get("depends_on", []))
        for capability in capabilities
    }
    found = []
    state = {}

    def dfs(node, path):
        state[node] = 1
        for dependency in graph.get(node, []):
            if state.get(dependency) == 1 and dependency in path:
                found.append(path[path.index(dependency) :] + [dependency])
            elif state.get(dependency, 0) == 0 and dependency in graph:
                dfs(dependency, path + [dependency])
        state[node] = 2

    for node in graph:
        if state.get(node, 0) == 0:
            dfs(node, [node])
    return found


def check(ir, repo_root=None, live_skills=None):
    repo_root = repo_root or str(REPO)
    live = live_skills if live_skills is not None else _live(repo_root)
    capabilities = ir.get("capabilities", [])
    dag_nodes = {node["id"] for node in ir.get("workflow", {}).get("nodes", [])}
    _, reachable_capabilities = _reachable(ir)
    checks = []
    rows = []
    unreachable = []
    kinds = set(_policy()["binding_kinds"]) | {"UNKNOWN"}
    runtime_bound = False
    blocked = False

    def add(check_id, status, detail=None):
        checks.append({"id": check_id, "status": status, "detail": detail})

    add(
        "closure_result_is_machine_readable",
        "pass",
        "emitted per capability-closure.schema.json",
    )
    missing_bindings = [
        capability["id"]
        for capability in capabilities
        if capability.get("required") and not capability.get("binding")
    ]
    add(
        "required_capabilities_have_bindings",
        "fail" if missing_bindings else "pass",
        ",".join(missing_bindings) or None,
    )
    bad_kind = [
        capability["id"]
        for capability in capabilities
        if (capability.get("binding") or {}).get("kind") not in kinds
    ]
    add(
        "binding_kind_is_known",
        "fail" if bad_kind else "pass",
        ",".join(bad_kind) or None,
    )

    local_missing = []
    executable_missing = []
    instruction_missing = []
    dag_missing = []
    skill_missing = []
    external_bad = []
    placeholders = []
    unbounded = []

    for capability in capabilities:
        binding = capability.get("binding") or {}
        kind = binding.get("kind")
        target = binding.get("target")
        status = "closed"
        detail = None

        needs_target = ("EXECUTABLE", "DAG_NODE", "DELEGATED_SKILL", "MODEL_INSTRUCTION")
        if kind in needs_target and not target:
            local_missing.append(capability["id"])
            status = "unresolved"
            detail = "no target"
        elif kind == "EXECUTABLE" and not os.path.exists(os.path.join(repo_root, target)):
            executable_missing.append(capability["id"])
            status = "unresolved"
            detail = "missing " + str(target)
        elif kind == "DAG_NODE" and target not in dag_nodes:
            dag_missing.append(capability["id"])
            status = "unresolved"
            detail = "no node " + str(target)
        elif (
            kind == "MODEL_INSTRUCTION"
            and "/" in target
            and not os.path.exists(os.path.join(repo_root, target))
        ):
            # A target naming a path must resolve. A bare string is inline
            # instruction text and has nothing to resolve.
            instruction_missing.append(capability["id"])
            status = "unresolved"
            detail = "missing " + str(target)
        elif kind == "DELEGATED_SKILL" and target not in live:
            skill_missing.append(capability["id"])
            status = "unresolved"
            detail = "not a live skill: " + str(target)
        elif kind == "EXTERNAL_CAPABILITY":
            if not binding.get("probe") or not binding.get("failure_behavior"):
                external_bad.append(capability["id"])
                status = "unresolved"
                detail = "probe and failure_behavior required"
            else:
                runtime_bound = True
                status = "runtime_bound"
                detail = "declared external runtime binding"
        elif kind == "UNKNOWN":
            if binding.get("bounded_unknown"):
                blocked = True
                status = "unresolved"
                detail = "bounded UNKNOWN"
            else:
                unbounded.append(capability["id"])
                status = "unresolved"
                detail = "unbounded UNKNOWN"

        if capability.get("required") and (
            _placeholder(binding.get("success_condition")) or _placeholder(target)
        ):
            placeholders.append(capability["id"])
            status = "placeholder"
        if capability.get("required") and capability["id"] not in reachable_capabilities:
            unreachable.append(capability["id"])

        rows.append(
            {
                "id": capability["id"],
                "binding_kind": kind or "NONE",
                "status": status,
                "detail": detail,
            }
        )

    add(
        "local_binding_targets_exist",
        "fail" if local_missing else "pass",
        ",".join(local_missing) or None,
    )
    add(
        "executable_bindings_resolve",
        "fail" if executable_missing else "pass",
        ",".join(executable_missing) or None,
    )
    add(
        "MODEL_INSTRUCTION_bindings_resolve",
        "fail" if instruction_missing else "pass",
        ",".join(instruction_missing) or None,
    )
    add(
        "DAG_NODE_bindings_resolve_to_real_nodes",
        "fail" if dag_missing else "pass",
        ",".join(dag_missing) or None,
    )
    add(
        "DELEGATED_SKILL_bindings_resolve_to_live_owned_skills",
        "fail" if skill_missing else "pass",
        ",".join(skill_missing) or None,
    )
    add(
        "EXTERNAL_CAPABILITY_bindings_define_probe_and_failure_behavior",
        "fail" if external_bad else "pass",
        ",".join(external_bad) or None,
    )
    add(
        "required_capabilities_are_reachable_from_entrypoint",
        "fail" if unreachable else "pass",
        ",".join(unreachable) or None,
    )
    cycles = _cycles(capabilities)
    add(
        "dependency_graph_is_acyclic",
        "fail" if cycles else "pass",
        str(cycles) if cycles else None,
    )
    add(
        "no_required_capability_is_satisfied_by_placeholder",
        "fail" if placeholders else "pass",
        ",".join(placeholders) or None,
    )
    add(
        "no_unresolved_reference_is_silently_accepted",
        "fail" if unbounded else "pass",
        ",".join(unbounded) or None,
    )
    add(
        "UNKNOWN_is_only_valid_when_explicitly_bounded",
        "block" if blocked else "pass",
        "bounded UNKNOWN present" if blocked else None,
    )

    if any(item["status"] == "fail" for item in checks):
        result = "FAIL"
    elif any(item["status"] == "block" for item in checks):
        result = "BLOCKED"
    elif runtime_bound:
        result = "RUNTIME_BOUND"
    else:
        result = "CLOSED"

    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "result": result,
        "generated_at": generated_at,
        "checks": checks,
        "capabilities": rows,
        "unreachable": unreachable,
        "cycles": cycles,
    }


EXIT = {"CLOSED": 0, "RUNTIME_BOUND": 0, "BLOCKED": 3, "FAIL": 2}


def main(argv):
    if len(argv) < 2:
        return fail("usage: check_capability_closure.py <skill-ir.json> [repo_root]")
    result = check(load_json(argv[1]), argv[2] if len(argv) > 2 else None)
    return emit(result, EXIT[result["result"]])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
