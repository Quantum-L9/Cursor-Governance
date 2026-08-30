#!/usr/bin/env python3
"""tools/agent_git.py — concurrent-agent-safe git driver."""
from __future__ import annotations
import argparse, json, os, socket, subprocess, sys, time
from pathlib import Path

PROTECTED_BRANCHES = {"main", "master", "release", "develop"}
LOCK_GRACE_SECONDS = 120
LEASE_TTL_SECONDS = 300

def run(cmd, cwd=None, check=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()

def git_common_dir(cwd): return Path(run(["git", "rev-parse", "--git-common-dir"], cwd=cwd))
def git_dir(cwd): return Path(run(["git", "rev-parse", "--absolute-git-dir"], cwd=cwd))
def current_branch(cwd): return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)

def assert_worktree_isolated(cwd):
    if git_dir(cwd).resolve() == git_common_dir(cwd).resolve():
        raise RuntimeError("FAIL: refusing to operate in the shared/primary checkout. Use `claim` first.")

def assert_safe_branch(cwd):
    branch = current_branch(cwd)
    if branch == "HEAD":
        raise RuntimeError("FAIL: detached HEAD is not allowed for agent operations.")
    if branch in PROTECTED_BRANCHES:
        raise RuntimeError(f"FAIL: refusing to operate directly on protected branch '{branch}'.")

def lease_dir(cwd):
    d = git_common_dir(cwd) / "l9-agent-leases"; d.mkdir(parents=True, exist_ok=True); return d
def lease_path(cwd, scope): return lease_dir(cwd) / f"{scope}.lease"

def pid_is_alive(pid):
    if not pid: return False
    try: os.kill(pid, 0); return True
    except (OSError, ProcessLookupError, PermissionError): return False

def journal_reclaim(cwd, scope, holder):
    journal_dir = Path(os.environ.get("L9_GIT_JOURNAL_DIR", git_common_dir(cwd) / "l9-journal"))
    journal_dir.mkdir(parents=True, exist_ok=True)
    with open(journal_dir / "git_ops.jsonl", "a") as f:
        f.write(json.dumps({"event": "lease_reclaimed", "scope": scope, "prior_holder": holder, "at": time.time()}) + "\n")

def acquire_lease(cwd, scope, agent_id, ttl=LEASE_TTL_SECONDS):
    path = lease_path(cwd, scope)
    payload = {"agent_id": agent_id, "pid": os.getpid(), "host": socket.gethostname(), "scope": scope, "acquired_at": time.time(), "ttl": ttl}
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f: json.dump(payload, f)
        return path
    except FileExistsError:
        holder = json.loads(path.read_text())
        age = time.time() - holder["acquired_at"]
        same_host = holder.get("host") == socket.gethostname()
        pid_alive = same_host and pid_is_alive(holder.get("pid"))
        reclaim_after = holder["ttl"] * (4 if pid_alive else 1)
        if age > reclaim_after:
            journal_reclaim(cwd, scope, holder); path.unlink(missing_ok=True)
            return acquire_lease(cwd, scope, agent_id, ttl)
        raise RuntimeError(f"lease busy: {holder['agent_id']} holds {path.name}")

def release_lease(cwd, scope): lease_path(cwd, scope).unlink(missing_ok=True)

def reclaim_stale_index_lock(cwd):
    lock = git_dir(cwd) / "index.lock"
    if not lock.exists(): return
    age = time.time() - lock.stat().st_mtime
    if age > LOCK_GRACE_SECONDS:
        lock.unlink(); print(f"reclaimed stale index.lock (age={age:.0f}s)")
    else:
        raise RuntimeError(f"FAIL: index.lock is only {age:.0f}s old (< {LOCK_GRACE_SECONDS}s grace)")

def cmd_doctor(args):
    cwd = Path(args.cwd)
    assert_worktree_isolated(cwd); assert_safe_branch(cwd); reclaim_stale_index_lock(cwd)
    print("PASS: worktree isolated, branch safe, no stale lock.")

def cmd_claim(args):
    cwd = Path(args.cwd)
    existing = run(["git", "worktree", "list", "--porcelain"], cwd=cwd)
    branch_ref = f"branch refs/heads/{args.branch}"
    if args.path in existing or branch_ref in existing:
        raise RuntimeError(f"FAIL: branch or path already checked out in another worktree: {existing}")
    acquire_lease(cwd, "worktree-admin", args.agent_id)
    try:
        run(["git", "worktree", "add", "-b", args.branch, args.path, f"origin/{args.base}"], cwd=cwd)
        print(f"PASS: claimed worktree {args.path} on branch {args.branch} from origin/{args.base}")
    finally:
        release_lease(cwd, "worktree-admin")

def cmd_commit(args):
    cwd = Path(args.cwd)
    assert_worktree_isolated(cwd); assert_safe_branch(cwd)
    scope = f"index-{Path(cwd).name}"
    acquire_lease(cwd, scope, args.agent_id)
    try:
        reclaim_stale_index_lock(cwd)
        run(["git", "add", "-A"], cwd=cwd)
        branch = current_branch(cwd); worktree = Path(cwd).name
        trailer_msg = f"{args.message}\n\nL9-Agent: {args.agent_id}\nL9-Worktree: {worktree}\nL9-Node: {args.node_id}"
        run(["git", "commit", "-m", trailer_msg], cwd=cwd)
        print(f"PASS: committed on {branch} with L9-Agent trailer.")
    finally:
        release_lease(cwd, scope)

def cmd_conflicts(args):
    cwd = Path(args.cwd)
    branch = current_branch(cwd)
    out = run(["git", "merge-tree", "--write-tree", branch, args.against], cwd=cwd, check=False)
    if "<<<<<<<" in out or "conflict" in out.lower():
        print(f"CONFLICT PREDICTED between {branch} and {args.against}\n{out}"); sys.exit(1)
    print(f"PASS: no predicted conflict between {branch} and {args.against}")

def cmd_push(args):
    cwd = Path(args.cwd)
    assert_worktree_isolated(cwd); assert_safe_branch(cwd)
    branch = current_branch(cwd)
    scope = f"remote-{branch}"
    acquire_lease(cwd, scope, args.agent_id)
    attempts = 0
    try:
        while attempts < args.max_retries:
            attempts += 1
            run(["git", "fetch", "origin", branch, args.base], cwd=cwd, check=False)
            if "CONFLICT" in run(["git", "rebase", f"origin/{branch}"], cwd=cwd, check=False):
                run(["git", "rebase", "--abort"], cwd=cwd, check=False)
                print(f"FAIL: rebase onto origin/{branch} conflicted; hand-off required."); sys.exit(1)
            if "CONFLICT" in run(["git", "rebase", f"origin/{args.base}"], cwd=cwd, check=False):
                run(["git", "rebase", "--abort"], cwd=cwd, check=False)
                print(f"FAIL: rebase onto origin/{args.base} conflicted; hand-off required."); sys.exit(1)
            push_out = run(["git", "push", "--force-with-lease", "--force-if-includes", "origin", branch], cwd=cwd, check=False)
            if "rejected" not in push_out.lower() and "error" not in push_out.lower():
                print(f"PASS: pushed {branch} (attempt {attempts})")
                print(json.dumps({"verdict": "PASS", "branch": branch, "attempts": attempts}))
                return
            time.sleep(1 + attempts * 0.5)
        print("FAIL: push exhausted retries; re-run after peer branch settles."); sys.exit(1)
    finally:
        release_lease(cwd, scope)

def cmd_release(args):
    cwd = Path(args.cwd)
    for scope in ("worktree-admin", f"index-{Path(cwd).name}", f"remote-{args.branch}"):
        release_lease(cwd, scope)
    print("PASS: released leases for this worktree/branch.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    p_claim = sub.add_parser("claim")
    p_claim.add_argument("--branch", required=True); p_claim.add_argument("--path", required=True)
    p_claim.add_argument("--base", required=True); p_claim.add_argument("--agent-id", required=True, dest="agent_id")
    p_claim.set_defaults(func=cmd_claim)
    p_commit = sub.add_parser("commit")
    p_commit.add_argument("--message", required=True); p_commit.add_argument("--agent-id", required=True, dest="agent_id")
    p_commit.add_argument("--node-id", required=True, dest="node_id"); p_commit.set_defaults(func=cmd_commit)
    p_conflicts = sub.add_parser("conflicts")
    p_conflicts.add_argument("--against", required=True); p_conflicts.set_defaults(func=cmd_conflicts)
    p_push = sub.add_parser("push")
    p_push.add_argument("--base", required=True); p_push.add_argument("--agent-id", required=True, dest="agent_id")
    p_push.add_argument("--max-retries", type=int, default=3, dest="max_retries"); p_push.set_defaults(func=cmd_push)
    p_release = sub.add_parser("release")
    p_release.add_argument("--branch", required=True); p_release.set_defaults(func=cmd_release)
    args = parser.parse_args()
    try: args.func(args)
    except RuntimeError as e:
        print(str(e), file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()
