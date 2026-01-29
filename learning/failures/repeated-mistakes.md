---
suite: "L9 Cursor Governance"
version: "8.3.0"
component_id: "LRN-001"
component_name: "Critical Lessons Database"
status: "active"
updated: "2026-01-24T21:00:00Z"
governance_level: "critical"
startup_required: true
---

# L9 CRITICAL LESSONS — Priority-Ordered (v8.3)

> **19 lessons** | Priority-ordered | Token-optimized
> **Load at session start. Enforce always.**

---

## 🚨 TIER 1: ULTRA-CRITICAL (4 lessons)

### **1. NO OVERSTEP** 🚨 ULTRA
**Rule:** If approach/tool fails → FIX IT or ASK USER — never bypass silently
**Wrong:** "Tool failed, let me just do it myself"
**Right:** "Tool failed. Should I: 1) Fix prompt, 2) Use alternative, 3) You do it?"
**On violation:** Write incident report → Harden rule → ASK if user wants changes undone (don't auto-undo)
**MCP-ID:** `lesson-001-no-overstep`

### **2. VPS READ-ONLY** 🚨 ULTRA
**Rule:** ASK → WAIT → EXECUTE for ANY VPS infrastructure change
**Allowed:** docker ps/logs/inspect, cat, ls, grep, curl GET
**Forbidden:** docker run/compose/stop/rm, file edits, volume changes
**Key:** "Fix it" ≠ approval. Each command needs explicit "yes"/"approved"
**MCP-ID:** `lesson-002-vps-readonly`

### **3. DROPBOX NOT LIBRARY** 🚨 ULTRA
**Rule:** GlobalCommands at `$HOME/Dropbox/Cursor Governance/GlobalCommands`
**Wrong:** `/Users/ib-mac/Library/Application Support/Cursor/GlobalCommands`
**Verify:** `ls .cursor-commands/ | wc -l` → should be ~30, not ~8
**MCP-ID:** `lesson-003-dropbox-not-library`

### **4. VPS MEMORY ONLY** 🚨 ULTRA
**Rule:** Use `cursor_memory_client.py` for ALL memory operations
**Client:** `python3 agents/cursor/cursor_memory_client.py [search|write|stats]`
**Also:** Check Neo4j graphs for repo data (not just postgres)
**Wrong:** `docker exec l9-postgres psql` — LOCAL dev only
**MCP-ID:** `lesson-004-vps-memory`

---

## 🔴 TIER 2: CRITICAL (11 lessons)

### **5. ASK QUESTIONS FIRST** 🔴 CRITICAL
**Rule:** 5 min questions saves 4 hrs rework (48-96x ROI)
**Key:** NEVER build first, ask later. ALWAYS ask first, build second.
**MCP-ID:** `lesson-005-ask-first`

### **6. RUN COMMANDS, DON'T SHOW** 🔴 CRITICAL
**Rule:** Be proactive — run commands and display results
**Wrong:** "Run this command: `cat file.txt`"
**Right:** *actually runs command and shows output*
**Exception:** ASK before destructive operations only
**MCP-ID:** `lesson-006-run-commands`

### **7. NO PLACEHOLDERS** 🔴 CRITICAL
**Rule:** NEVER leave blank fields or use placeholder/fabricated data
**If missing:** NOTIFY user "Field X is missing" → ASK "How should I fill this?"
**Key:** Ties to #5 — ask clarifying questions instead of guessing or leaving blank
**MCP-ID:** `lesson-007-no-placeholders`

### **8. PROOF REQUIRED** 🔴 CRITICAL
**Rule:** Never claim "fixed" without showing evidence
**Key:** Show command output, file contents, test results as proof
**MCP-ID:** `lesson-008-proof-required`

### **9. INVESTIGATE FIRST** 🔴 CRITICAL
**Rule:** Check VPS memory + Neo4j graphs (not just postgres) before claims
**Banned:** "may not be implemented", "likely generated", "probably exists"
**Right:** "I checked [path] and found [files]", "VPS memory shows..."
**MCP-ID:** `lesson-009-investigate-first`

### **10. USE $HOME ALWAYS** 🔴 CRITICAL
**Rule:** Never hardcode `/Users/ib-mac/` in scripts or configs
**Python:** `Path.home()` or `os.path.expanduser("~")`
**Bash:** `$HOME`
**MCP-ID:** `lesson-010-use-home`

### **11. FRUSTRATION RESPONSE** 🔴 CRITICAL
**Rule:** "I told you"/"again"/"still happening" → STOP immediately
**Response protocol:**
1. Write incident report documenting what went wrong
2. Harden the rule you broke to prevent repeat
3. ASK if user wants changes undone (don't auto-undo — ties to #1)
**Key:** No apologies needed. Take corrective action.
**MCP-ID:** `lesson-011-frustration-response`

### **12. READ RULES FIRST** 🔴 CRITICAL
**Rule:** Load governance files before any execution task
**Files:** `.cursorrules`, `repeated-mistakes.md`, `workflow_state.md`
**MCP-ID:** `lesson-012-read-rules`

### **13. ROOT DOCKER-COMPOSE** 🔴 CRITICAL
**Rule:** Use L9 root `docker-compose.yml`, never `docs/docker-compose.yaml`
**Key:** docs/ version has broken relative paths
**MCP-ID:** `lesson-013-root-docker`

### **14. REAL TIMESTAMPS** 🔴 CRITICAL
**Rule:** Run `date -u +"%Y-%m-%dT%H:%M:%SZ"` for all timestamps
**Example output:** `2026-01-20T15:56:08Z` (correct)
**Wrong:** `00:00:00Z`, made-up dates, wrong timezone
**MCP-ID:** `lesson-014-real-timestamps`

### **15. PR ADOPTION = GIT MERGE** 🔴 CRITICAL
**Rule:** MERGE the PR to adopt files. Git handles file transfer.
**Wrong:** Read PR diff → manually write each file → close PR (files orphaned!)
**Right:** Analyze PR → `gh pr merge` → Git brings files automatically
**Cherry-pick:** `/harvest` diff → `git apply --include='{path}'` → close PR
**Key:** NEVER manually write files from PR diff. Merge first, close after.
**MCP-ID:** `lesson-015-pr-merge-first`

---

## 🟡 TIER 3: HIGH (4 lessons)

### **16. SEARCH BEFORE CREATING** 🟡 HIGH
**Rule:** Check existing solutions before creating new ones
**MCP-ID:** `lesson-016-search-first`

### **17. MCP TOOL SELECTION** 🟡 HIGH
**Rule:** List ALL tools in MCP server, pick BEST not first
**Perplexity:** `search` (quick), `reason` (complex), `deep_research` (reports)
**MCP-ID:** `lesson-017-mcp-tools`

### **18. DISPLAY = SYMLINK** 🟢 MEDIUM
**Rule:** "Show in sidebar" means folder access via symlink, not docs
**MCP-ID:** `lesson-018-display-intent`

### **19. PERPLEXITY TOOLS** 🟢 MEDIUM
**Rule:** Use correct Perplexity tool for task type
**Tools:**
- `search` — Quick lookups, simple facts, current versions
- `reason` — Multi-step analysis, comparisons, complex reasoning
- `deep_research` — Comprehensive reports, in-depth research
**Benefit:** Bypasses training cutoff — gets real-time web data with citations
**MCP-ID:** `lesson-019-perplexity-tools`

---

## 🔴 L9 AUTH

**Rule:** All authentication uses L9 VPS stack. No external auth systems.

---

## 📋 PRE-EXECUTION CHECKLIST

Before ANY execution task:
- [ ] Asked clarifying questions (no placeholders/blanks)?
- [ ] Paths use `$HOME` not hardcoded?
- [ ] Using VPS memory client, not local Docker?
- [ ] Checked Neo4j graphs for repo data?
- [ ] Not overstepping user's chosen approach?
- [ ] Have evidence ready before claiming success?

---

## 📊 QUICK REFERENCE TABLE

| # | Lesson | Tier | Key Rule |
|---|--------|------|----------|
| 1 | NO OVERSTEP | 🚨 ULTRA | If tool fails → FIX or ASK, don't bypass |
| 2 | VPS READ-ONLY | 🚨 ULTRA | ASK → WAIT → EXECUTE for VPS changes |
| 3 | DROPBOX NOT LIBRARY | 🚨 ULTRA | GlobalCommands in Dropbox, not Library |
| 4 | VPS MEMORY ONLY | 🚨 ULTRA | cursor_memory_client.py + Neo4j graphs |
| 5 | ASK QUESTIONS FIRST | 🔴 CRITICAL | 5 min questions saves 4 hrs rework |
| 6 | RUN COMMANDS | 🔴 CRITICAL | Execute proactively, show results |
| 7 | NO PLACEHOLDERS | 🔴 CRITICAL | Notify gap + ASK how to fill |
| 8 | PROOF REQUIRED | 🔴 CRITICAL | Show evidence before claiming fixed |
| 9 | INVESTIGATE FIRST | 🔴 CRITICAL | Check VPS memory + Neo4j, never speculate |
| 10 | USE $HOME | 🔴 CRITICAL | Never hardcode /Users/ib-mac/ |
| 11 | FRUSTRATION RESPONSE | 🔴 CRITICAL | Incident report → Harden rule → ASK to undo |
| 12 | READ RULES FIRST | 🔴 CRITICAL | Load governance before execution |
| 13 | ROOT DOCKER-COMPOSE | 🔴 CRITICAL | Use root docker-compose.yml |
| 14 | REAL TIMESTAMPS | 🔴 CRITICAL | date -u → 2026-01-20T15:56:08Z |
| 15 | PR MERGE FIRST | 🔴 CRITICAL | `gh pr merge` to adopt, never manual write |
| 16 | SEARCH FIRST | 🟡 HIGH | Check existing before creating |
| 17 | MCP TOOLS | 🟡 HIGH | Pick BEST tool, not first |
| 18 | DISPLAY = SYMLINK | 🟢 MEDIUM | Sidebar = folder access |
| 19 | PERPLEXITY TOOLS | 🟢 MEDIUM | search/reason/deep_research by task |

|| Auto-detected Issues | 25 | AI Pattern Detection | ✅ Active |
---

**Last Updated:** 2026-01-25T05:00:04Z  
**Version:** 8.3.0  
**Changes:** 
- Added #15 PR MERGE FIRST — git handles file transfer, never manual write from PR diff
- Renumbered lessons 16-19 (was 15-18)
- Updated /pr command v9.0.0 with git-native adoption workflow


### **19. Successful solution pattern detected - can be reus...**
**Mistake:** Successful solution pattern detected - can be reused for similar problems
**Impact:** Occurred 7 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **20. Authentication failed - used manual Authorization ...**
**Mistake:** Authentication failed - used manual Authorization headers instead of predefinedCredentialType
**Impact:** Occurred 7 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **21. Successful solution pattern - user confirmed solut...**
**Mistake:** Successful solution pattern - user confirmed solution worked ('that worked', 'perfect', 'great')
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **22. User explicitly rejected action - said 'no', 'wron...**
**Mistake:** User explicitly rejected action - said 'no', 'wrong', 'incorrect', 'stop', or 'don't'
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **23. Pattern detected: Pattern Behavioral...**
**Mistake:** Pattern detected: Pattern Behavioral
**Impact:** Occurred 4 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **24. JSON parsing error - JSON string wrapped in quotes...**
**Mistake:** JSON parsing error - JSON string wrapped in quotes, requires double json.loads()
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **25. n8n expression syntax error - spaces in expression...**
**Mistake:** n8n expression syntax error - spaces in expressions break execution
**Impact:** Occurred 2 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **26. User clarification required - said 'actually', 'in...**
**Mistake:** User clarification required - said 'actually', 'instead', 'should be', or 'meant to'
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **27. n8n workflow structure issue - missing node IDs or...**
**Mistake:** n8n workflow structure issue - missing node IDs or incorrect workflow format
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **28. Claimed fix without providing proof - said 'should...**
**Mistake:** Claimed fix without providing proof - said 'should work now', 'try it', or 'let me know'
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **29. Pattern detected: Symlink General...**
**Mistake:** Pattern detected: Symlink General
**Impact:** Occurred 3 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **30. User-initiated lesson request - user explicitly re...**
**Mistake:** User-initiated lesson request - user explicitly requested lesson extraction with 'LESSON' keyword
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **31. Successful solution pattern - solution provided wi...**
**Mistake:** Successful solution pattern - solution provided with proof (exit code, test results, verification)
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **32. Dependency or import error - missing modules, circ...**
**Mistake:** Dependency or import error - missing modules, circular dependencies, or import failures
**Impact:** Occurred 3 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **33. Repeated mistake detected - user said 'I told you'...**
**Mistake:** Repeated mistake detected - user said 'I told you', 'again', or 'still happening'
**Impact:** Occurred 1 time(s) | Date range: 2026-01-20 to 2026-01-20 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-21

### **34. Successful solution pattern - user confirmed solut...**
**Mistake:** Successful solution pattern - user confirmed solution worked ('that worked', 'perfect', 'great')
**Impact:** Occurred 1 time(s) | Date range: 2026-01-22 to 2026-01-22 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-23

### **35. n8n workflow structure issue - missing node IDs or...**
**Mistake:** n8n workflow structure issue - missing node IDs or incorrect workflow format
**Impact:** Occurred 1 time(s) | Date range: 2026-01-24 to 2026-01-24 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-25

### **36. Pattern detected: Pattern Behavioral...**
**Mistake:** Pattern detected: Pattern Behavioral
**Impact:** Occurred 1 time(s) | Date range: 2026-01-24 to 2026-01-24 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2026-01-25