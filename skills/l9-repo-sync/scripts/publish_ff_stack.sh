#!/usr/bin/env bash
# Publish a reconciled /ff stack via Makefile preconfig.
# Never git push. Never gh pr create. Bottom-up: first lane PR_STACK=, later auto.
set -euo pipefail

STACK_JSON="${1:?stack json}"
GOV_ROOT="${FF_GOV_ROOT:-${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}}"
GOV_ROOT="$(cd "$GOV_ROOT" && pwd)"
MAKE="${FF_MAKE:-make}"

if [ ! -f "$STACK_JSON" ]; then
  echo "FAIL: stack json missing: $STACK_JSON" >&2
  exit 1
fi

if [ "${FF_DRY_PUBLISH:-0}" = "1" ]; then
  echo "OK: dry-publish — would run make pr-check then PR_REMEDIATE=0 make pr per lane"
  python3 - "$STACK_JSON" <<'PY'
import json, sys
stack = json.loads(open(sys.argv[1], encoding="utf-8").read())
for i, lane in enumerate(stack.get("lanes") or []):
    stack_flag = lane.get("pr_stack") or ""
    print(
        f"lane {i} dest={lane.get('dest')} branch={lane.get('branch')} "
        f"PR_BASE={lane.get('pr_base')} PR_STACK={stack_flag!r} "
        f"PR_REMEDIATE=0 WS={lane.get('worktree')}"
    )
    if "git push" in json.dumps(lane):
        raise SystemExit("stack lane must not request git push")
PY
  exit 0
fi

python3 - "$STACK_JSON" "$GOV_ROOT" "$MAKE" <<'PY'
import json, os, subprocess, sys

stack_path, gov, make = sys.argv[1], sys.argv[2], sys.argv[3]
stack = json.loads(open(stack_path, encoding="utf-8").read())
if not stack.get("ok", True):
    raise SystemExit("stack is not ok — refuse publish")
lanes = stack.get("lanes") or []
if not lanes:
    print("OK: nothing to publish via make pr")
    raise SystemExit(0)

for i, lane in enumerate(lanes):
    worktree = lane["worktree"]
    env = os.environ.copy()
    env["PR_REMEDIATE"] = "0"
    env["PR_BASE"] = lane.get("pr_base") or "origin/main"
    env["PR_STACK"] = lane.get("pr_stack") or ""
    env["WS"] = worktree
    env["OPEN_PR"] = "1"
    print(
        f"ff-publish: lane={i} dest={lane.get('dest')} "
        f"make -C {gov} pr-check WS={worktree}"
    )
    check = subprocess.run([make, "-C", gov, "pr-check", f"WS={worktree}"], env=env)
    if check.returncode != 0:
        raise SystemExit(f"FAIL: make pr-check failed for {lane.get('branch')}")
    print(
        f"ff-publish: lane={i} PR_REMEDIATE=0 PR_STACK={env['PR_STACK']!r} "
        f"make -C {gov} pr WS={worktree}"
    )
    published = subprocess.run(
        [
            make,
            "-C",
            gov,
            "pr",
            f"WS={worktree}",
            "PR_REMEDIATE=0",
            f"PR_BASE={env['PR_BASE']}",
            f"PR_STACK={env['PR_STACK']}",
            "OPEN_PR=1",
        ],
        env=env,
    )
    if published.returncode != 0:
        raise SystemExit(f"FAIL: make pr failed for {lane.get('branch')}")
    print(f"OK: published {lane.get('branch')} via make pr")
PY
