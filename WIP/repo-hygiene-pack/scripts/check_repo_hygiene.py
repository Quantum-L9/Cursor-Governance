#!/usr/bin/env python3
"""RB-HK-001 hygiene gate. Run from repo root. Exit non-zero on violation."""
import re, subprocess, sys, pathlib

BANNED_TRACKED = [
    "governance-health-report.json",
    ".harvest_executor_state.json",
    "docs/rules-frontmatter-inventory.md",
    "docs/skills-inventory.md",
]
SECRET_PAT = re.compile(
    r"lin_api_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}")
ALLOWED_MCP = {"linear", "supabase", "vercel", "context7", "github", "graphiti"}

errs, warns = [], []


def sh(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              check=False).stdout.splitlines()
    except FileNotFoundError:
        return []


tracked = sh("git", "ls-files")
if not tracked:
    sys.exit("no tracked files found - run from repo root inside a git repo")

print("tracked files: %d" % len(tracked))

spaces = [t for t in tracked if " " in t]
if spaces:
    errs.append("paths containing spaces (%d): %s" % (len(spaces), ", ".join(spaces[:8])))

for b in BANNED_TRACKED:
    hits = [t for t in tracked if t.endswith(b) or t == b]
    if hits:
        errs.append("generated/runtime file tracked: %s" % ", ".join(hits))

if pathlib.Path(".env.template").exists() and pathlib.Path(".env.example").exists():
    errs.append("both .env.example and .env.template exist - keep .env.example only")

if pathlib.Path("current_work").is_dir():
    errs.append("current_work/ is retired - use WIP/ (human) or TODO.md (agent)")

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
        warns.append(".github/workflows/%s not installed" % wf)

import json
for cfg in (".mcp.json", ".cursor/mcp.json"):
    p = pathlib.Path(cfg)
    if not p.exists():
        continue
    try:
        servers = json.loads(p.read_text(encoding="utf-8")).get("mcpServers", {})
    except Exception as e:
        errs.append("%s invalid JSON: %s" % (cfg, e))
        continue
    unknown = sorted(set(servers) - ALLOWED_MCP)
    if unknown:
        errs.append("%s non-allowlisted MCP server(s): %s" % (cfg, ", ".join(unknown)))
    else:
        print("  %s -> %s" % (cfg, ", ".join(sorted(servers)) or "none"))

skip = ("-pack/", ".example", ".template", "uv.lock")
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
        errs.append("credential pattern in tracked file: %s" % t)

print("")
for w in warns:
    print("  warn: %s" % w)
if errs:
    print("\nFAIL (%d)" % len(errs))
    for e in errs:
        print("  - %s" % e)
    print("\nSee housekeeping-pack/RUNBOOK.md Section 4")
    sys.exit(1)
print("PASS")
