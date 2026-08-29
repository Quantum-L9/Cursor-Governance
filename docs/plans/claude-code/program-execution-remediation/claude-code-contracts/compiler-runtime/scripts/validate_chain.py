#!/usr/bin/env python3
"""
validate_chain.py — claude-coding-contract-compiler v2.7.0
Chain-level validation for same-branch, one-commit-per-contract execution.

Rules:
  1. Each contract handoff token exactly matches the next contract resume token.
  2. chain_digest over ordered contract IDs is identical in every contract.
  3. source_commits are exactly one ordinal per contract and form contiguous 1..N.
  4. Internal prerequisites are strictly linear and require committed_and_validated.
  5. All contracts target the same repo and the same shared branch.
  6. Contract N+1 preflight proves contract N by checking N's exact HEAD commit subject
     and re-running only N's dedicated completion proof. Repository-wide commit gates are not replayed.
  7. Every contract requires exactly one local commit; no nonterminal contract may deliver.
     The terminal contract alone is authorized to run exactly `make pr`.
"""
import argparse, hashlib, json, shlex, sys
from pathlib import Path


def sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()


def compute_chain_digest(ids: list[str]) -> str:
    return sha256(json.dumps(ids, separators=(",", ":")))


def head_commit_assertion(subject: str) -> str:
    return f'test "$(git show -s --format=%s HEAD)" = {shlex.quote(subject)}'


def validate_chain(contracts: list[dict]) -> list[str]:
    errors = []
    if not contracts:
        return ["CHAIN_EMPTY"]

    ids = [c["contract_id"] for c in contracts]
    digest = compute_chain_digest(ids)

    # 1. Handoff seams and 6. predecessor proof reachability.
    for i in range(len(contracts) - 1):
        cur = contracts[i]
        nxt = contracts[i + 1]
        cur_green = set(cur.get("handoff", {}).get("next_session_may_assume_green", []))
        nxt_assumes = set(nxt.get("resume_from", {}).get("assumes_already_green", []))
        if cur_green != nxt_assumes:
            errors.append(
                f"HANDOFF_SEAM_MISMATCH [{cur['contract_id']} -> {nxt['contract_id']}]: "
                f"green={sorted(cur_green)} assumes={sorted(nxt_assumes)}")

        expected_state = {"id": cur["contract_id"], "required_state": "committed_and_validated"}
        if nxt.get("prerequisite_contract") != expected_state:
            errors.append(
                f"PREREQUISITE_MISMATCH [{nxt['contract_id']}]: "
                f"expected={expected_state} actual={nxt.get('prerequisite_contract')}")

        cur_git = cur.get("git_workflow", {})
        nxt_cmds = nxt.get("resume_from", {}).get("verify_before_starting", [])
        subject = cur_git.get("commit_subject")
        if subject:
            expected_head = head_commit_assertion(subject)
            if expected_head not in nxt_cmds:
                errors.append(
                    f"PREDECESSOR_COMMIT_NOT_PROVEN [{cur['contract_id']} -> {nxt['contract_id']}]: "
                    f"missing {expected_head!r}")
        completion_proof = cur_git.get("completion_proof")
        if not completion_proof or completion_proof not in nxt_cmds:
            errors.append(
                f"PREDECESSOR_COMPLETION_PROOF_NOT_PROVEN "
                f"[{cur['contract_id']} -> {nxt['contract_id']}]: missing={completion_proof!r}")

    # 2. chain_digest consistency.
    for c in contracts:
        stored = c.get("handoff", {}).get("chain_digest")
        if stored and stored != digest:
            errors.append(
                f"CHAIN_DIGEST_MISMATCH [{c['contract_id']}]: stored={stored} computed={digest}")

    # 3. Exactly one source commit ordinal per contract, contiguous 1..N.
    all_commits = []
    for c in contracts:
        commits = c.get("session_budget", {}).get("source_commits") or []
        if len(commits) != 1:
            errors.append(
                f"ONE_COMMIT_POLICY_VIOLATION [{c['contract_id']}]: source_commits={commits}")
        for co in commits:
            if co in all_commits:
                errors.append(f"DUPLICATE_COMMIT [{c['contract_id']}]: commit {co}")
            all_commits.append(co)
    if all_commits:
        ordered = sorted(all_commits)
        expected = list(range(1, len(contracts) + 1))
        if ordered != expected:
            errors.append(
                f"COMMIT_GAP: source commits {ordered} must equal one-per-contract ordinals {expected}")

    # 4. First contract may use an external base prerequisite; all later prerequisites checked above.
    for i, c in enumerate(contracts[1:], start=1):
        expected_id = contracts[i - 1]["contract_id"]
        prereq = c.get("prerequisite_contract") or {}
        if prereq.get("id") != expected_id:
            errors.append(
                f"LINEARITY_VIOLATION [{c['contract_id']}]: prerequisite={prereq.get('id')} "
                f"expected={expected_id}")

    # 5. Same repo and branch, plus git_workflow branch parity.
    repos = {c.get("target_repo") for c in contracts}
    branches = {c.get("target_branch") for c in contracts}
    if len(repos) > 1:
        errors.append(f"REPO_MISMATCH: {repos}")
    if len(branches) > 1:
        errors.append(f"BRANCH_MISMATCH: {branches}")
    branch = contracts[0].get("target_branch")

    # 7. Exact one-commit policy + one terminal make-pr delivery.
    for i, c in enumerate(contracts):
        git = c.get("git_workflow", {})
        cid = c["contract_id"]
        if git.get("shared_branch") != branch or git.get("shared_branch") != c.get("target_branch"):
            errors.append(f"SHARED_BRANCH_MISMATCH [{cid}]: {git.get('shared_branch')!r}")
        if git.get("commit_policy") != "exactly_one_local_commit_per_contract":
            errors.append(f"COMMIT_POLICY_MISMATCH [{cid}]")
        if git.get("commit_subject") != cid:
            errors.append(
                f"COMMIT_SUBJECT_MISMATCH [{cid}]: expected exact subject {cid!r}, "
                f"got {git.get('commit_subject')!r}")
        expected_commit = f'git commit -m {json.dumps(cid)}'
        if git.get("commit_command") != expected_commit:
            errors.append(f"COMMIT_COMMAND_MISMATCH [{cid}]: expected {expected_commit!r}")
        proof = git.get("completion_proof")
        gate = c.get("commit_gate", {}).get("required_before_commit", [])
        if not proof or proof not in gate:
            errors.append(f"COMPLETION_PROOF_NOT_COMMIT_GATED [{cid}]")
        if git.get("push_policy") != "terminal_contract_only_via_make_pr":
            errors.append(f"PUSH_POLICY_MISMATCH [{cid}]")

        delivery = git.get("terminal_delivery", {})
        is_terminal = i == len(contracts) - 1
        if is_terminal:
            if delivery != {"authorized": True, "command": "make pr"}:
                errors.append(
                    f"TERMINAL_DELIVERY_MISMATCH [{cid}]: expected authorized make pr, got {delivery}")
        else:
            if delivery != {"authorized": False, "command": None}:
                errors.append(
                    f"EARLY_DELIVERY_AUTHORIZED [{cid}]: expected no delivery, got {delivery}")

    return errors


def main():
    ap = argparse.ArgumentParser(description="Validate contract chain seams, one-commit policy, and terminal delivery.")
    ap.add_argument("instances", nargs="+", help="Contract JSON files IN ORDER")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    contracts = [json.loads(Path(p).read_text()) for p in args.instances]
    errors = validate_chain(contracts)
    ids = [c["contract_id"] for c in contracts]
    digest = compute_chain_digest(ids)
    result = {
        "schema_version": "2.0",
        "chain_ids": ids,
        "chain_digest": digest,
        "errors": errors,
        "valid": len(errors) == 0,
    }
    out = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(out)
    print(out)
    if errors:
        print(f"\nCHAIN INVALID: {len(errors)} error(s)", file=sys.stderr)
        sys.exit(1)
    print(f"\nCHAIN VALID: {len(contracts)} contracts, digest={digest}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
