#!/usr/bin/env python3
"""L9 pipeline orchestrator — deterministic chain driver.

State-file driven. Each run answers ONE question: "what is the next contract to build, and is it
ready?" It never spawns sessions itself (that is the environment's Routine mechanism) and never
merges (that is the operator/CI gate). It only computes the next step and stamps status.

    python advance.py state.yaml next        # print the next ready contract id (or DONE / BLOCKED)
    python advance.py state.yaml seed <id>    # print the fresh-session seed prompt for <id>
    python advance.py state.yaml set <id> <status>   # green | building | merged | failed
    python advance.py state.yaml gate <id> pr_state.json  # run the auto-merge gate; promote green->merged if ELIGIBLE

merge_policy (state.yaml): 'auto' (default) promotes green->merged automatically ONLY when the
auto-merge gate passes (CI green + review flags resolved + review comments resolved / remediation ran).
'manual' leaves promotion to the operator. The build session NEVER merges its own work — a separate
authorized step runs the gate. Removing the human tap is a logged control relaxation, not a silent edit.

Statuses per item: pending -> building -> green -> merged  (failed is terminal until reset).
An item is READY when status==pending AND its prerequisite item is 'merged' (or it has none).
The 'merged' gate is deliberate: contracts deny push/merge, so promotion is the one authorized step.
For a relaxed 'green-chains-to-next' mode (no merge between builds), set state.chain_on: green.
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def merge_policy(state):
    return state.get("merge_policy", "auto")  # 'auto' (gate-driven) or 'manual' (operator)


def load(p):
    import yaml

    return yaml.safe_load(pathlib.Path(p).read_text())


def dump(p, data):
    import yaml

    pathlib.Path(p).write_text(yaml.safe_dump(data, sort_keys=False))


def ready_gate(state):
    return state.get(
        "chain_on", "green"
    )  # 'green' (default, hands-off) or 'merged' (tap/CI per PR)


def next_ready(state):
    gate = ready_gate(state)  # 'merged' (default) or 'green'
    items = state["items"]
    by_id = {it["contract_id"]: it for it in items}  # prerequisite holds the full contract_id
    ready_states = ("merged",) if gate == "merged" else ("green", "merged")
    awaiting = False
    for it in items:
        if it["status"] != "pending":
            continue
        prereq = it.get("prerequisite")
        if prereq is None:
            return it
        pstatus = by_id.get(prereq, {}).get("status")
        if pstatus in ready_states:
            return it
        if pstatus == "green":  # prereq built but not yet merged (merged-gate mode)
            awaiting = True
        if pstatus == "failed":
            return {"key": "__BLOCKED__", "reason": f"{prereq} failed"}
    if all(it["status"] == "merged" for it in items):
        return {"key": "__DONE__"}
    if awaiting:
        return {"key": "__AWAIT_MERGE__"}
    if all(it["status"] != "pending" for it in items):
        return {"key": "__DONE__"}  # all green in green-gate mode, or all merged
    return {"key": "__BLOCKED__", "reason": "no ready contract and none awaiting merge"}


def seed_prompt(state, item):
    c = state["campaign"]
    return SEED_TEMPLATE.format(
        contract_id=item["contract_id"],
        key=item["key"],
        title=item["title"],
        repo=c["target_repo"],
        branch=c["target_branch"],
        out_dir=c["out_dir"],
        prereq=item.get("prerequisite") or "none (first in chain)",
        gate=ready_gate(state),
    )


SEED_TEMPLATE = """You are executing exactly ONE contract from a compiled L9 chain, in a fresh session.

Contract: {contract_id}  ({title})
Repo: {repo}   Branch: {branch}
Contract artifacts: {out_dir}/PR-{key}/  (PR-{key}.contract.json, CLAUDE.md, settings.json, preflight.sh)
Prerequisite: {prereq}   Chain gate: {gate}

Do EXACTLY this, then stop:
1. Copy {out_dir}/PR-{key}/CLAUDE.md to repo root and {out_dir}/PR-{key}/settings.json to .claude/settings.json.
2. Run: bash {out_dir}/PR-{key}/preflight.sh   — if it exits non-zero, HALT and report RESUME_PRECONDITION_NOT_SATISFIED. Do not build.
3. Read PR-{key}.contract.json. Build STRICTLY within scope_lock.in_scope. Touch nothing in hard_out_of_scope or preserved_files.
4. Run: npm run validate  (the commit_gate). Must pass.
5. Commit locally with the contract's commit message. DO NOT push, open a PR, or merge (denied tools).
6. Update orchestration: `python advance.py state.yaml set {contract_id} green`.
7. Report: contract id, files changed, validate result. Then STOP.

The operator (or CI auto-merge, if authorized) promotes green -> merged, which unblocks the next contract.
"""


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    path, cmd = argv[1], argv[2]
    state = load(path)
    if cmd == "next":
        it = next_ready(state)
        print(it["key"] if it["key"].startswith("__") else it["contract_id"])
        return 0
    if cmd == "seed":
        cid = argv[3]
        it = next((i for i in state["items"] if i["contract_id"] == cid), None)
        if not it:
            print(f"unknown contract {cid}", file=sys.stderr)
            return 1
        print(seed_prompt(state, it))
        return 0
    if cmd == "set":
        cid, status = argv[3], argv[4]
        it = next((i for i in state["items"] if i["contract_id"] == cid), None)
        if not it:
            print(f"unknown contract {cid}", file=sys.stderr)
            return 1
        it["status"] = status
        dump(path, state)
        print(f"{cid} -> {status}")
        return 0
    if cmd == "gate":
        import json as _json

        import automerge_gate

        cid, pr_json = argv[3], argv[4]
        it = next((i for i in state["items"] if i["contract_id"] == cid), None)
        if not it:
            print(f"unknown contract {cid}", file=sys.stderr)
            return 1
        pr = _json.loads(pathlib.Path(pr_json).read_text())
        eligible, _conds, blocked = automerge_gate.evaluate(pr)
        if merge_policy(state) == "manual":
            print(
                f"{cid}: gate={'ELIGIBLE' if eligible else 'BLOCKED'} (merge_policy=manual; operator promotes)"
            )
            return 0 if eligible else 1
        if eligible:
            it["status"] = "merged"
            dump(path, state)
            print(f"{cid}: ELIGIBLE -> auto-merged (green->merged); next contract unblocked")
            return 0
        print(f"{cid}: BLOCKED — not auto-merged (stays green):", file=sys.stderr)
        for cond, why in blocked.items():
            for r in why:
                print(f"  - {cond}: {r}", file=sys.stderr)
        return 1
    print(f"unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
