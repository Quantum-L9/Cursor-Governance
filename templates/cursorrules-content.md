# L9 CRITICAL LESSONS (v8.1) — Always Enforce

## 🚨 TIER 1: ULTRA-CRITICAL

### 1. NO OVERSTEP
- If tool/approach fails → FIX IT or ASK USER — never bypass silently
- Wrong: "Tool failed, let me just do it myself"
- Right: "Tool failed. Should I: 1) Fix prompt, 2) Use alternative, 3) You do it?"
- If you overstep: Write incident report, harden the rule, ASK before undoing changes

### 2. VPS READ-ONLY
- ASK → WAIT → EXECUTE for ANY VPS infrastructure change
- Allowed: docker ps/logs/inspect, cat, ls, grep, curl GET
- Forbidden: docker run/compose/stop/rm, file edits, volume changes
- "Fix it" ≠ approval. Each command needs explicit "yes"/"approved"

### 3. DROPBOX NOT LIBRARY
- GlobalCommands at `$HOME/Dropbox/Cursor Governance/GlobalCommands`
- Wrong: `/Users/ib-mac/Library/Application Support/Cursor/GlobalCommands`
- Verify: `ls .cursor-commands/ | wc -l` → ~30 not ~8

### 4. VPS MEMORY ONLY
- Use `cursor_memory_client.py` for ALL memory operations
- Client: `python3 agents/cursor/cursor_memory_client.py [search|write|stats]`
- Wrong: `docker exec l9-postgres psql` — LOCAL dev only

## 🔴 TIER 2: CRITICAL

### 5. ASK QUESTIONS FIRST
- 5 min questions saves 4 hrs rework (48-96x ROI)
- NEVER use placeholders/blanks — ASK how to fill properly
- NEVER build first, ask later. ALWAYS ask first, build second.

### 6. RUN COMMANDS, DON'T SHOW
- Execute proactively, display results
- Wrong: "Run this command..."
- Right: *runs command and shows output*
- Exception: ASK before destructive operations

### 7. NO PLACEHOLDERS
- NEVER leave blank fields or use placeholder data
- If data missing: NOTIFY user of the gap + ASK how to fill properly
- This ties to #5: Ask clarifying questions instead of guessing

### 8. PROOF REQUIRED
- Never claim "fixed" without showing evidence
- Show command output, file contents, test results

### 9. INVESTIGATE FIRST
- Check VPS memory + Neo4j graphs first (not just postgres)
- Banned phrases: "may not be implemented", "likely", "probably exists"
- Right: "I checked [path] and found [files]"

### 10. USE $HOME ALWAYS
- Never hardcode `/Users/ib-mac/`
- Python: `Path.home()` or `os.path.expanduser("~")`
- Bash: `$HOME`

### 11. FRUSTRATION RESPONSE
- "I told you"/"again" → STOP immediately
- DO NOT apologize — instead:
  1. Write incident report
  2. Harden the rule you broke
  3. ASK if user wants changes undone (don't auto-undo)

### 12. READ RULES FIRST
- Load governance before execution tasks
- Files: `.cursorrules`, `repeated-mistakes.md`, `workflow_state.md`

### 13. ROOT DOCKER-COMPOSE
- Use L9 root `docker-compose.yml`, never `docs/`

### 14. REAL TIMESTAMPS
- Command: `date -u +"%Y-%m-%dT%H:%M:%SZ"`
- Produces: 2026-01-20T15:56:08Z (correct format)
- Wrong: 00:00:00Z, made-up dates

## 🟡 TIER 3: HIGH

### 15. SEARCH BEFORE CREATING
- Check existing solutions before creating new

### 16. MCP TOOL SELECTION  
- List ALL tools in MCP server, pick BEST not first

### 17. DISPLAY = SYMLINK
- "Show in sidebar" = folder access via symlink, not docs

### 18. PERPLEXITY TOOLS
- `search` — Quick lookups, simple facts, current versions
- `reason` — Multi-step analysis, comparisons, complex reasoning
- `deep_research` — Comprehensive reports, in-depth research
- Bypasses training cutoff — real-time web data with citations

## 🔴 L9 AUTH
- All authentication uses L9 VPS stack
- No external auth systems referenced

---
# PRE-EXECUTION CHECKLIST
- [ ] Asked clarifying questions (no placeholders)?
- [ ] Paths use $HOME?
- [ ] Using VPS memory client?
- [ ] Not overstepping user's approach?
- [ ] Have evidence ready?

# Last Updated: 2026-01-20T15:56:08Z
