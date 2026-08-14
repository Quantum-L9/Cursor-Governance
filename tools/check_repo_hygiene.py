#!/usr/bin/env python3
"""RB-HK-001 hygiene gate. Run from repo root. Exit non-zero on violation."""
import json
import os
import pathlib
import re
import subprocess
import sys

BANNED_TRACKED = [
    "governance-health-report.json",
    ".harvest_executor_state.json",
    "docs/rules-frontmatter-inventory.md",
    "docs/skills-inventory.md",
]
# H-03 named paths from RB-HK-001. Other historical space paths are deferred.
SECRET_PAT = re.compile(
    r"lin_api_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}"
)
ALLOWED_MCP = {"graphiti-memory"}

errs, warns = [], []


def sh(*args):
    try:
        return subprocess.run(
            args, capture_output=True, text=True, check=False
        ).stdout.splitlines()
    except FileNotFoundError:
        return []


def is_h03(path: str) -> bool:
    return (
        path == "Activation Command.md"
        or path == "commands/harvest copy.md"
        or path.startswith("key components/")
    )


tracked = sh("git", "ls-files")
if not tracked:
    sys.exit("no tracked files found - run from repo root inside a git repo")
tracked_set = set(tracked)

print(f"tracked files: {len(tracked)}")

h03 = [t for t in tracked if is_h03(t)]
if h03:
    errs.append(f"H-03 space paths still tracked ({len(h03)}): {', '.join(h03[:8])}")

other_spaces = [
    t
    for t in tracked
    if " " in t
    and not is_h03(t)
    and not t.startswith("WIP/")
    and not t.startswith("current_work/")
]
if other_spaces:
    preview = ", ".join(other_spaces[:6])
    warns.append(f"deferred space paths outside H-03 ({len(other_spaces)}): {preview}")

for b in BANNED_TRACKED:
    hits = [t for t in tracked if t.endswith(b) or t == b]
    if hits:
        errs.append(f"generated/runtime file tracked: {', '.join(hits)}")

if pathlib.Path(".env.template").exists() and pathlib.Path(".env.example").exists():
    errs.append("both .env.example and .env.template exist - keep .env.example only")

if pathlib.Path("current_work").is_dir():
    msg = "current_work/ is retired - use WIP/ (human) or TODO.md (agent)"
    # Local commits stay possible until the human migrates; CI stays fail-closed.
    if os.environ.get("GITHUB_ACTIONS"):
        errs.append(msg)
    else:
        warns.append(msg)

ci = pathlib.Path(".cursorignore")
if pathlib.Path("WIP").is_dir():
    if not ci.exists():
        errs.append("WIP/ exists but .cursorignore is missing")
    elif not re.search(r"^WIP/?$", ci.read_text(encoding="utf-8"), re.M):
        errs.append("WIP/ exists but is not listed in .cursorignore")

if not pathlib.Path("TODO.md").exists():
    warns.append("TODO.md missing - it is the agent task queue")

if not pathlib.Path(".github/dependabot.yml").exists():
    warns.append(".github/dependabot.yml missing (H-06)")

for wf in ("repo-hygiene.yml", "governance-self-check.yml", "branch-hygiene.yml"):
    if not pathlib.Path(".github/workflows", wf).exists():
        warns.append(f".github/workflows/{wf} not installed")

for cfg in (".mcp.json", ".cursor/mcp.json"):
    if cfg not in tracked_set:
        continue
    p = pathlib.Path(cfg)
    try:
        servers = json.loads(p.read_text(encoding="utf-8")).get("mcpServers", {})
    except Exception as e:
        errs.append(f"{cfg} invalid JSON: {e}")
        continue
    unknown = sorted(set(servers) - ALLOWED_MCP)
    if unknown:
        errs.append(f"{cfg} non-allowlisted MCP server(s): {', '.join(unknown)}")
    else:
        print(f"  {cfg} -> {', '.join(sorted(servers)) or 'none'}")

skip = (
    "-pack/",
    ".example",
    ".template",
    "uv.lock",
    "tools/check_repo_hygiene.py",
    ".github/workflows/governance-self-check.yml",
)
for t in tracked:
    if any(s in t for s in skip):
        continue
    p = pathlib.Path(t)
    if not p.is_file() or p.stat().st_size > 400_000:
        continue
    try:
        body = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if SECRET_PAT.search(body):
        errs.append(f"credential pattern in tracked file: {t}")

print("")
for w in warns:
    print(f"  warn: {w}")
if errs:
    print(f"\nFAIL ({len(errs)})")
    for e in errs:
        print(f"  - {e}")
    print("\nSee WIP/housekeeping-pack/RUNBOOK.md Section 4")
    sys.exit(1)
print("PASS")
