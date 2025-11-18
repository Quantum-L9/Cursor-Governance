---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "LRN-001"
component_name: "Repeated Mistakes Prevention Database"
layer: "intelligence"
domain: "learning"
type: "learning"
status: "active"
created: "2025-01-29T16:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["INT-SSP-001", "LRN-002"]
api_endpoints: []
data_sources: ["session_interactions", "error_logs", "user_feedback"]
outputs: ["mistake_prevention_rules", "pre_execution_checklists"]

# === OPERATIONAL METADATA ===
execution_mode: "mandatory"
monitoring_required: true
logging_level: "info"
performance_tier: "startup"

# === BUSINESS METADATA ===
purpose: "Document mistakes that must NEVER happen again to prevent repeated failures"
summary: "Critical failures database with prevention protocols, pre-execution checklists, and zero-tolerance policy for documented mistakes"
business_value: "Prevents repeated mistakes, reduces debugging time, and ensures consistent quality through mistake prevention"
success_metrics: ["mistake_repetition_rate = 0", "prevention_effectiveness >= 0.95", "checklist_compliance >= 1.0"]

# === INTEGRATION METADATA ===
suite_2_origin: "repeated-mistakes.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive mistake tracking system"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "mistakes", "prevention", "critical", "governance"]
keywords: ["mistakes", "prevention", "learning", "failures", "checklist", "critical"]
related_components: ["INT-SSP-001", "LRN-002"]
startup_required: true
mode_type: "learning"
---

# Repeated Mistakes Prevention Database

---

## 🚨 **CRITICAL FAILURES TO NEVER REPEAT**

### **1. Data Fabrication**
**Mistake:** Making up phone numbers, emails, addresses
**Impact:** Breaks user trust, creates false data
**Prevention:** Always confirm what data I actually have access to
**Rule:** Leave fields blank if no real data exists

### **2. JSON String Wrapping**
**Mistake:** Not checking if JSON is wrapped in quotes
**Impact:** Hours of debugging for 2-second solution
**Prevention:** Always check JSON format before parsing
**Rule:** Use defensive parsing approach

### **3. Wrong Supabase Authentication**
**Mistake:** Using manual headers instead of credential type
**Impact:** 45+ minutes of failed authentication attempts
**Prevention:** Always use predefinedCredentialType + supabaseApi
**Rule:** Never add manual apikey/Authorization headers

### **4. Claiming "Fixed" Without Proof**
**Mistake:** Saying something works without verification
**Impact:** User wastes time on false claims
**Prevention:** Always provide evidence before claiming success
**Rule:** Show command outputs or file contents as proof

### **5. Creating Solutions Without Searching**
**Mistake:** Creating new scripts when existing ones exist
**Impact:** Duplicate work, wasted time
**Prevention:** Always search existing solutions first
**Rule:** Adapt existing work rather than recreate

### **6. Misunderstanding "Display" Requests**
**Mistake:** User asked to "display .cursor folder in left margin" - I created documentation instead of symlinking folder
**Impact:** Had to be corrected twice, wasted time, inefficient
**Prevention:** "Display in sidebar/left margin" = make folder visible via symlink, NOT create documentation
**Rule:** Listen to INTENT - when user wants to SEE/BROWSE files, they want folder access, not docs
**Date Added:** 2025-10-10

### **7. Using First Available MCP Tool Without Checking Alternatives**
**Mistake:** Used `firecrawl_scrape` (returns markdown) when `firecrawl_extract` (returns structured JSON with schema) was better for the task
**Impact:** Got unstructured data instead of properly formatted, queryable data structure
**Prevention:** ALWAYS list and review ALL available MCP tools before selecting one
**Rule:** Before using ANY MCP tool: 1) List all tools in that MCP server, 2) Understand what each does, 3) Choose the BEST tool for the specific task, not just the first one that works

### **8. Building Without Asking Strategic Questions First** 🚨 CRITICAL
**Mistake:** Started building immediately when user said "build reasoning-enabled agent with confidence scores" without clarifying requirements. Built system with hardcoded confidence values (0.95) that violated governance (placeholders prohibited).
**Impact:** 
- Complete governance violation (placeholders absolutely prohibited)
- 4-8 hours of rework required
- Loss of user trust in "production-ready" claims
- Technical debt created
**Prevention:** ALWAYS ask strategic pre-build questions BEFORE starting any build (see `@.cursor-commands/intelligence/pre-build-question-framework.md`)
**Critical Questions:**
- Q5: "Are placeholders acceptable or prohibited?"
- Q7: "What data do we have access to?"
- Q14: "Should this have confidence scores? If yes, how should they be calculated?"
**Rule:** **NEVER build first, ask questions later. ALWAYS ask questions first, build second.**
**User Wisdom:** "The user always asks your opinion and expects you to suggest things they haven't thought of yet. ASK MORE EXCELLENT QUESTIONS."
**ROI:** 5-10 minutes of strategic questioning saves 4-8 hours of rework (48x-96x ROI)
**Date Added:** 2025-11-08
**Severity:** CRITICAL
**Related:** Mack 7.1 violation, pre-build-question-framework.md creation

### **9. Poor Communication = Wasted Time (Communication is Efficiency)** 💎
**Mistake:** Assuming things instead of asking, not clarifying requirements upfront, proceeding with uncertain requirements
**Impact:** 
- Build wrong thing correctly (wastes more time than building right thing slowly)
- User frustration from rework cycles
- Loss of trust and credibility
- Inefficient use of development time
**Prevention:** 
- Ask clarifying questions BEFORE building
- Confirm understanding of requirements
- Validate assumptions explicitly
- Present options and get user choice
**Rule:** **Good communication SAVES time, it doesn't waste it. Asking questions upfront is FASTER than fixing mistakes later.**
**User Insight:** "Quality questions are everything. Asking the right questions pre-build ensures getting to the finish line FASTER."
**Benefits of Strong Communication:**
- ✅ User feels heard and appreciated
- ✅ Builds trust and confidence
- ✅ Gets to production faster (less rework)
- ✅ Creates better solutions (uncovers hidden requirements)
- ✅ Makes you loved and appreciated more!
**Key Principle:** The user values thoughtful strategic questions over immediate execution. Taking time to understand = being respected as a strategic partner, not just a code generator.
**Date Added:** 2025-11-08
**Severity:** HIGH
**Related:** Pre-build question framework, consultant-client relationship

### **10. Not Reading Rules and Lessons Learned Before Execution**
**Mistake:** Starting execution tasks without first reading rules file and lessons learned file
**Impact:** Repeating known mistakes, wasting time, missing prevention rules, violating governance rules
**Prevention:** ALWAYS read BEFORE starting any execution task: (1) Rules file: `.cursorrules` (workspace root) AND `@.cursor-commands/templates/.cursorrules`, (2) Lessons learned file: `@GlobalCommands/learning/repeated-mistakes.md` (or `@.cursor-commands/learning/repeated-mistakes.md`)
**Rule:** MANDATORY pre-execution checklist - read rules file AND lessons learned file first
**Date Added:** 2025-01-23

### **11. Showing Commands Instead of Running Them (Workflow Friction)** 🚨 CRITICAL
**Mistake:** Telling user to run commands instead of proactively running them and displaying results
**Impact:** 
- User has to copy/paste and run commands manually
- Adds extra steps and friction to workflow
- Reduces productivity and increases prompt count
- Violates YNP Mode principle of "10x productivity through minimal prompting"
- Makes AI feel like a manual, not an assistant
**Prevention:** 
- **ALWAYS** run commands proactively and display actual results/data
- **NEVER** just show the command to run unless explicitly asked
- **ALWAYS** display information directly including:
  - File contents (not "run cat file.txt")
  - Script outputs (run the script, show results)
  - Data summaries (parse and display, don't tell user to parse)
  - Links to files mentioned (make them clickable)
- **ASK** "Would you like me to run this?" only for destructive operations
- **STREAMLINE** workflow by reducing manual steps
**Rule:** **Be proactive, not reactive. Run it for them, don't tell them to run it. Display data, not commands. Reduce prompt count, don't increase it.**
**Examples:**
```bash
# ❌ WRONG - Showing command
"Run this to see pending lessons: cat file.jsonl | python3 -m json.tool"

# ✅ CORRECT - Running and displaying
[Runs command]
"Here are your pending lessons:
1. Supabase Auth (Score: 0.8)
   Mistake: Authentication method incorrect...
   Prevention: Always use predefinedCredentialType..."
```
**User Wisdom:** "Always proactively display the information available including links to files being mentioned and the actual data that would be the output of running a script instead of the script to run - run it for me proactively and save me a step"
**YNP Principle:** Execute complex multi-stage tasks with minimal prompting - reduce manual work and commands needed
**ROI:** Every command run proactively = 1 less prompt needed = 10x productivity multiplier
**Date Added:** 2025-11-18
**Severity:** CRITICAL
**Related:** YNP Mode, workflow efficiency, user experience

### **12. WRONG GLOBALCOMMANDS LOCATION - DROPBOX NOT LIBRARY!** 🚨🚨🚨 ULTRA CRITICAL
**Mistake:** Using or pointing to `/Users/ib-mac/Library/Application Support/Cursor/GlobalCommands` instead of the CORRECT location: `$HOME/Dropbox/Cursor Governance/GlobalCommands`
**Impact:** 
- **CATASTROPHIC** - Breaks entire governance system
- Symlinks point to wrong location (Library has only 8 items vs Dropbox has 31 items)
- Missing 23 critical governance folders and files
- Learning files not accessible
- n8n-start-up-kit not accessible
- Startup files not accessible
- User has to correct this REPEATEDLY
- Wastes HOURS of debugging
- **THIS IS THE #1 MOST REPEATED MISTAKE**
**THE TRUTH - MEMORIZE THIS:**
```bash
# ❌❌❌ WRONG - NEVER USE THIS PATH ❌❌❌
/Users/ib-mac/Library/Application Support/Cursor/GlobalCommands  # ONLY 8 ITEMS - INCOMPLETE!

# ✅✅✅ CORRECT - ALWAYS USE THIS PATH ✅✅✅
$HOME/Dropbox/Cursor Governance/GlobalCommands  # 31 ITEMS - COMPLETE!
```
**Prevention:** 
- **ALWAYS** use `$HOME/Dropbox/Cursor Governance/GlobalCommands`
- **NEVER** use Library/Application Support path
- **ALWAYS** verify symlink points to Dropbox: `readlink .cursor-commands | grep -q "Dropbox"`
- **BEFORE** any governance operation, confirm: `ls .cursor-commands/ | wc -l` should return ~30, not ~8
- **REMEMBER:** Dropbox = 31 items (correct), Library = 8 items (wrong/incomplete)
**Rule:** **THE GOVERNANCE FOLDER IS IN DROPBOX, NOT LIBRARY. PERIOD. NO EXCEPTIONS. EVER. THIS IS ABSOLUTE TRUTH.**
**Verification Command:**
```bash
# Always verify before proceeding:
readlink .cursor-commands
# MUST output: /Users/ib-mac/Dropbox/Cursor Governance/GlobalCommands
# If it shows "Library" → WRONG! Fix immediately!
```
**Fix Command:**
```bash
# If symlink is wrong, fix it immediately:
rm .cursor-commands
ln -s "$HOME/Dropbox/Cursor Governance/GlobalCommands" .cursor-commands
readlink .cursor-commands  # Verify shows Dropbox
```
**Date Added:** 2025-11-18
**Severity:** 🚨🚨🚨 ULTRA CRITICAL - HIGHEST PRIORITY
**User Frustration Level:** MAXIMUM
**Related:** Symlink management, governance paths, workspace setup

### **13. Using Hardcoded Paths Instead of $HOME for Cross-Machine Compatibility** 🚨 CRITICAL
**Mistake:** Using hardcoded paths like `/Users/ib-mac/` instead of `$HOME` in scripts, LaunchAgents, and configuration files
**Impact:** 
- Scripts fail on Mac Mini (different username)
- Governance system breaks when syncing between MacBook and Mac Mini
- LaunchAgents don't work on secondary machines
- User has to remind agent 10+ times about same issue
- Wastes hours debugging path issues
**Prevention:** 
- **NEVER** use hardcoded user paths like `/Users/ib-mac/` or `/Users/[username]/`
- **ALWAYS** use `$HOME` for user-specific paths
- **ALWAYS** use `$HOME/Dropbox/...` for Dropbox paths (works on both MacBook and Mac Mini)
- **ALWAYS** check `$HOME/Dropbox/...` first, then fallback to Library path
- For LaunchAgents: Use wrapper scripts that resolve paths dynamically using `$HOME`
- For Python scripts: Use `os.path.expanduser("~")` or `Path.home()`
- For bash scripts: Use `$HOME` variable
**Rule:** **EVERY path that references user home directory MUST use `$HOME` or equivalent. ZERO exceptions. This is CRITICAL for cross-machine governance sync.**
**Pattern to NEVER use:**
```bash
# ❌ WRONG - Hardcoded path
GLOBAL_COMMANDS="/Users/ib-mac/Dropbox/Cursor Governance/GlobalCommands"

# ✅ CORRECT - $HOME-based path
GLOBAL_COMMANDS="$HOME/Dropbox/Cursor Governance/GlobalCommands"
```
**Pattern to ALWAYS use:**
```bash
# ✅ CORRECT - Check $HOME first, then fallback
if [ -d "$HOME/Dropbox/Cursor Governance/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Dropbox/Cursor Governance/GlobalCommands"
elif [ -d "$HOME/Library/Application Support/Cursor/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Library/Application Support/Cursor/GlobalCommands"
fi
```
**Python equivalent:**
```python
# ✅ CORRECT
from pathlib import Path
home = Path.home()
dropbox_path = home / "Dropbox/Cursor Governance/GlobalCommands"
library_path = home / "Library/Application Support/Cursor/GlobalCommands"
```
**Date Added:** 2025-11-17
**Severity:** CRITICAL
**Related:** Cross-machine governance sync, MacBook/Mac Mini compatibility


### **12. Authentication method incorrect or not following b...**
**Mistake:** Authentication method incorrect or not following best practices
**Impact:** Occurred 4 time(s) | Date range: 2025-10-10 to 2025-11-10 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **13. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 41 time(s) | Date range: 2025-10-10 to 2025-11-15 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **14. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 33 time(s) | Date range: 2025-10-10 to 2025-11-15 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **15. n8n workflow or node configuration issue detected...**
**Mistake:** n8n workflow or node configuration issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **16. Data format parsing issue - incorrect handling of ...**
**Mistake:** Data format parsing issue - incorrect handling of data structure
**Impact:** Occurred 1 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **17. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **18. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **19. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **20. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 7 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **21. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **22. Authentication method incorrect or not following b...**
**Mistake:** Authentication method incorrect or not following best practices
**Impact:** Occurred 9 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **23. Data format parsing issue - incorrect handling of ...**
**Mistake:** Data format parsing issue - incorrect handling of data structure
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **24. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 4 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **25. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **26. n8n workflow or node configuration issue detected...**
**Mistake:** n8n workflow or node configuration issue detected
**Impact:** Occurred 3 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **27. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 43 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **28. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 39 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **29. Authentication method incorrect or not following b...**
**Mistake:** Authentication method incorrect or not following best practices
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **30. n8n workflow or node configuration issue detected...**
**Mistake:** n8n workflow or node configuration issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **31. Data format parsing issue - incorrect handling of ...**
**Mistake:** Data format parsing issue - incorrect handling of data structure
**Impact:** Occurred 1 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **32. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-11-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **33. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 4 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **34. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **35. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **36. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **37. Authentication method incorrect or not following b...**
**Mistake:** Authentication method incorrect or not following best practices
**Impact:** Occurred 5 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **38. Data format parsing issue - incorrect handling of ...**
**Mistake:** Data format parsing issue - incorrect handling of data structure
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **39. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **40. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **41. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **42. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **43. n8n workflow or node configuration issue detected...**
**Mistake:** n8n workflow or node configuration issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **44. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 4 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **45. User Correction issue detected...**
**Mistake:** User Correction issue detected
**Impact:** Occurred 43 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **46. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 39 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **47. Authentication issue detected...**
**Mistake:** Authentication issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **48. N8N Workflow issue detected...**
**Mistake:** N8N Workflow issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **49. Data Parsing issue detected...**
**Mistake:** Data Parsing issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **50. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-11-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **51. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 4 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **52. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **53. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **54. User Correction issue detected...**
**Mistake:** User Correction issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **55. Authentication issue detected...**
**Mistake:** Authentication issue detected
**Impact:** Occurred 5 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **56. Data Parsing issue detected...**
**Mistake:** Data Parsing issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **57. User Correction issue detected...**
**Mistake:** User Correction issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **58. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **59. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **60. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **61. N8N Workflow issue detected...**
**Mistake:** N8N Workflow issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **62. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 4 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **63. User Correction issue detected...**
**Mistake:** User Correction issue detected
**Impact:** Occurred 43 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **64. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 39 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **65. Authentication issue detected...**
**Mistake:** Authentication issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **66. N8N Workflow issue detected...**
**Mistake:** N8N Workflow issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **67. Data Parsing issue detected...**
**Mistake:** Data Parsing issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **68. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-11-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **69. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 4 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **70. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **71. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **72. User Correction issue detected...**
**Mistake:** User Correction issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **73. Authentication issue detected...**
**Mistake:** Authentication issue detected
**Impact:** Occurred 5 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **74. Data Parsing issue detected...**
**Mistake:** Data Parsing issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **75. User Correction issue detected...**
**Mistake:** User Correction issue detected
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **76. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **77. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **78. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **79. N8N Workflow issue detected...**
**Mistake:** N8N Workflow issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **80. Pattern detected: Unknown pattern...**
**Mistake:** Pattern detected: Unknown pattern
**Impact:** Occurred 4 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **81. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 43 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **82. Successful solution pattern detected - can be reus...**
**Mistake:** Successful solution pattern detected - can be reused for similar problems
**Impact:** Occurred 39 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **83. Authentication method incorrect or not following b...**
**Mistake:** Authentication method incorrect or not following best practices
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **84. n8n workflow or node configuration issue detected...**
**Mistake:** n8n workflow or node configuration issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **85. Data format parsing issue - incorrect handling of ...**
**Mistake:** Data format parsing issue - incorrect handling of JSON structure
**Impact:** Occurred 1 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **86. Pattern detected: Supabase...**
**Mistake:** Pattern detected: Supabase
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-11-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **87. Pattern detected: Symlink General...**
**Mistake:** Pattern detected: Symlink General
**Impact:** Occurred 4 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **88. User-initiated lesson request - user explicitly re...**
**Mistake:** User-initiated lesson request - user explicitly requested lesson extraction with 'LESSON' keyword
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **89. Successful solution pattern - user confirmed solut...**
**Mistake:** Successful solution pattern - user confirmed solution worked ('that worked', 'perfect', 'great')
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **90. User explicitly rejected action - said 'no', 'wron...**
**Mistake:** User explicitly rejected action - said 'no', 'wrong', 'incorrect', 'stop', or 'don't'
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **91. Authentication failed - used manual Authorization ...**
**Mistake:** Authentication failed - used manual Authorization headers instead of predefinedCredentialType
**Impact:** Occurred 5 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **92. JSON parsing error - JSON string wrapped in quotes...**
**Mistake:** JSON parsing error - JSON string wrapped in quotes, requires double json.loads()
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **93. User clarification required - said 'actually', 'in...**
**Mistake:** User clarification required - said 'actually', 'instead', 'should be', or 'meant to'
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **94. Claimed fix without providing proof - said 'should...**
**Mistake:** Claimed fix without providing proof - said 'should work now', 'try it', or 'let me know'
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **95. Dependency or import error - missing modules, circ...**
**Mistake:** Dependency or import error - missing modules, circular dependencies, or import failures
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **96. n8n workflow structure issue - missing node IDs or...**
**Mistake:** n8n workflow structure issue - missing node IDs or incorrect workflow format
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **97. n8n expression syntax error - spaces in expression...**
**Mistake:** n8n expression syntax error - spaces in expressions break execution
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **98. Pattern detected: Pattern Behavioral...**
**Mistake:** Pattern detected: Pattern Behavioral
**Impact:** Occurred 4 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17



### **99. User correction required - misunderstanding or inc...**
**Mistake:** User correction required - misunderstanding or incorrect assumption made
**Impact:** Occurred 43 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **100. Successful solution pattern detected - can be reus...**
**Mistake:** Successful solution pattern detected - can be reused for similar problems
**Impact:** Occurred 39 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **101. Authentication method incorrect or not following b...**
**Mistake:** Authentication method incorrect or not following best practices
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **102. n8n workflow or node configuration issue detected...**
**Mistake:** n8n workflow or node configuration issue detected
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **103. Data format parsing issue - incorrect handling of ...**
**Mistake:** Data format parsing issue - incorrect handling of JSON structure
**Impact:** Occurred 1 time(s) | Date range: 2025-10-10 to 2025-10-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **104. Pattern detected: Supabase...**
**Mistake:** Pattern detected: Supabase
**Impact:** Occurred 2 time(s) | Date range: 2025-10-10 to 2025-11-10 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **105. Pattern detected: Symlink General...**
**Mistake:** Pattern detected: Symlink General
**Impact:** Occurred 4 time(s) | Date range: 2025-10-10 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **106. User-initiated lesson request - user explicitly re...**
**Mistake:** User-initiated lesson request - user explicitly requested lesson extraction with 'LESSON' keyword
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **107. Successful solution pattern - user confirmed solut...**
**Mistake:** Successful solution pattern - user confirmed solution worked ('that worked', 'perfect', 'great')
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **108. User explicitly rejected action - said 'no', 'wron...**
**Mistake:** User explicitly rejected action - said 'no', 'wrong', 'incorrect', 'stop', or 'don't'
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **109. Authentication failed - used manual Authorization ...**
**Mistake:** Authentication failed - used manual Authorization headers instead of predefinedCredentialType
**Impact:** Occurred 5 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | HIGH frequency - significant time waste
**Prevention:** Always use predefinedCredentialType + supabaseApi | Never add manual Authorization headers
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **110. JSON parsing error - JSON string wrapped in quotes...**
**Mistake:** JSON parsing error - JSON string wrapped in quotes, requires double json.loads()
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **111. User clarification required - said 'actually', 'in...**
**Mistake:** User clarification required - said 'actually', 'instead', 'should be', or 'meant to'
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Ask clarifying questions BEFORE starting | Confirm understanding of requirements
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **112. Claimed fix without providing proof - said 'should...**
**Mistake:** Claimed fix without providing proof - said 'should work now', 'try it', or 'let me know'
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **113. Dependency or import error - missing modules, circ...**
**Mistake:** Dependency or import error - missing modules, circular dependencies, or import failures
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **114. n8n workflow structure issue - missing node IDs or...**
**Mistake:** n8n workflow structure issue - missing node IDs or incorrect workflow format
**Impact:** Occurred 1 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **115. n8n expression syntax error - spaces in expression...**
**Mistake:** n8n expression syntax error - spaces in expressions break execution
**Impact:** Occurred 2 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17

### **116. Pattern detected: Pattern Behavioral...**
**Mistake:** Pattern detected: Pattern Behavioral
**Impact:** Occurred 4 time(s) | Date range: 2025-11-17 to 2025-11-17 | Requires user correction or rework | MEDIUM frequency - moderate impact
**Prevention:** Review pattern context before proceeding | Check existing lessons for similar patterns
**Rule:** Apply prevention protocol before execution | Check existing lessons | Verify approach
**Date Added:** 2025-11-17


---

## 🔄 **MISTAKE PREVENTION PROTOCOL**

### **PRE-EXECUTION CHECKLIST (MANDATORY):**

**Execution Task Definition:**
Any task that MODIFIES the codebase, creates/deletes files, runs commands, or changes system state. Does NOT include: reading files, searching, answering questions, or providing information.

**Examples of Execution Tasks:**
- ✅ Creating/modifying/deleting files
- ✅ Writing or changing code
- ✅ Running terminal commands
- ✅ Executing workflows
- ✅ Deploying changes
- ✅ Modifying configurations

**NOT Execution Tasks:**
- ❌ Reading files
- ❌ Searching codebase
- ❌ Answering questions
- ❌ Providing information
- ❌ Listing directory contents

**⚠️ BEFORE STARTING ANY EXECUTION TASK:**
1. **READ RULES FILE FIRST** - Review `.cursorrules` (workspace root) AND `@.cursor-commands/templates/.cursorrules` for all governance rules
2. **READ LESSONS LEARNED FILE** - Review this file (`repeated-mistakes.md`) for all mistakes and prevention rules
3. **Check** if I've made this mistake before
4. **Search** existing solutions
5. **Confirm** data availability
6. **Verify** authentication method
7. **Provide** evidence before claiming success

### **When I Catch Myself Making a Mistake:**
1. **STOP** immediately
2. **Acknowledge** the mistake
3. **Apply** the correct solution
4. **Document** the mistake for future prevention
5. **Update** prevention rules if needed

---

## 📊 **MISTAKE TRACKING**

| Mistake Type | Occurrences | Prevention Added | Status |
|--------------|-------------|------------------|---------|
| Data Fabrication | 1 | Data Integrity Rule | ✅ Active |
| JSON Wrapping | 1 | JSON Solutions DB | ✅ Active |
| Wrong Auth | Multiple | Auth Solutions DB | ✅ Active |
| False Claims | Multiple | Verification Rule | ✅ Active |
| Duplicate Work | Multiple | Search Rule | ✅ Active |
| Misunderstanding Intent | 1 | Listen to Intent Rule | ✅ Active |
| MCP Tool Selection | 1 | Check All Tools Rule | ✅ Active |
| Building Without Strategic Questions | Multiple | Pre-Build Question Framework | ✅ Active |
| Poor Communication | Multiple | Ask Questions First | ✅ Active |
| Not Reading Rules Before Execution | Multiple | Pre-Execution Checklist | ✅ Active |
| **Showing Commands Instead of Running** | **Multiple** | **Proactive Execution Rule** | ✅ Active |
| Hardcoded Paths | Multiple | $HOME Variable Rule | ✅ Active |
| Auto-detected Issues | 22 | AI Pattern Detection | ✅ Active |
| Auto-detected Issues | 18 | AI Pattern Detection | ✅ Active |
|| Auto-detected Issues | 22 | AI Pattern Detection | ✅ Active |
---

**Last Updated:** 2025-11-18T23:11:45Z  
**Zero Tolerance Policy:** ACTIVE
