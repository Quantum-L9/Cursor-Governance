---
name: pr
version: "9.0.0"
description: "PR analysis with INLINE presentation, git-native adoption"
before_chain: rules
auto_chain: ynp
strict_mode: true
workflow_injection: true
---

# /pr — PR Analysis & Gap Assessment (INLINE MODE)

## USAGE

```
/pr #45              # Analyze specific PR
/pr #45,#46          # Batch analyze (sequential)
```

## 🚨 CRITICAL: ADOPTION = MERGE (NOT MANUAL WRITE)

```
┌──────────────────────────────────────────────────────────────────────┐
│  MERGE THE PR = ADOPT THE FILES                                      │
│  Git handles file transfer. NEVER manually write PR files.           │
│                                                                      │
│  ❌ WRONG: Read diff → Write each file manually                      │
│  ✅ RIGHT: Analyze → Merge PR → Git brings in files automatically    │
└──────────────────────────────────────────────────────────────────────┘
```

**Anti-pattern detected:** Agent reads PR diff, then manually creates each file. This is WRONG.

**Correct workflow:**
1. Analyze PR (inline)
2. If adopt → `gh pr merge` (git brings files)
3. If cherry-pick → `/harvest` diff first, then apply selectively

---

## 🔄 EXECUTION MODEL (ADR-0059 + ADR-0060)

```
ANALYSIS (Inline)                     ADOPTION (Git-Native)
┌─────────────────────────┐           ┌─────────────────────────┐
│ Phases 0-5: Analysis    │           │ MERGE: gh pr merge      │
│ Present findings INLINE │  ──YNP──► │ CHERRY: /harvest + git  │
│ Recommend action        │           │ Git does file transfer  │
└─────────────────────────┘           └─────────────────────────┘
```

**Key Rules:**
1. Analysis = INLINE (no file generation)
2. Adoption = GIT MERGE (not manual write)
3. Cherry-pick = /harvest first, then selective apply

---

## 📋 INLINE OUTPUT FORMAT

Present analysis directly in chat using this structure:

```markdown
## PR #{number} Analysis: {title}

**Author:** @{author} | **Files:** {count} | **Tier:** {tier}

### 📊 File Status

| File | Status | Confidence | Notes |
|------|--------|------------|-------|
| `path/file.py` | ✅/⚠️/🆕/🔄 | XX% | ... |

### ✅ Adopt ({count})
- `file1.py` — reason
- `file2.py` — reason

### ❌ Skip ({count})
- `file3.py` — already exists at `existing/path.py`

### 🔧 Realign ({count})
- `file4.py` — PR uses X, repo uses Y

### /ynp

**YES:** Merge PR (11 files, no conflicts)
**NO:** None
**PROCEED:** `gh pr merge {number} --squash --delete-branch`
```

---

## FLOW (GATED)

```
/rules → MEMORY INJECT → DISCOVERY → INDEX SCAN → DEEP RESEARCH → GAP ANALYSIS → INLINE PRESENTATION → USER CONFIRM → [OPTIONAL REPORT]
         [GATE 1]        [GATE 2]    [GATE 3]     [GATE 4]        [GATE 5]       [GATE 6]              [GATE 7]       [GATE 8]
```

---

## 🔒 PHASE 0: MEMORY INJECTION [GATE 1]

```bash
python3 agents/cursor/cursor_memory_client.py search "PR merge lessons errors"
python3 agents/cursor/cursor_memory_client.py search "{pr_component} patterns"
```

**GATE 1:** Memory search executed or "no results" stated.

---

## 🔒 PHASE 1: DISCOVERY [GATE 2]

```bash
gh pr view {number} --json title,author,files,additions,deletions,baseRefName,headRefName
gh pr view {number} --json files --jq '.files[].path'
gh pr diff {number}
```

**GATE 2:** PR metadata fetched, files listed, tier classified.

---

## 🔒 PHASE 2: INDEX SCAN [GATE 3]

Query indexes BEFORE grep/rg:

```bash
grep -i "{ClassName}" readme/repo-index/class_definitions.txt
grep -i "{function}" readme/repo-index/function_signatures.txt
grep "{route}" readme/repo-index/route_handlers.txt
```

**GATE 3:** At least 3 indexes queried with evidence.

---

## 🔒 PHASE 3: DEEP RESEARCH [GATE 4]

For "not found" items:

```bash
rg -i "{concept}" --type py -l
rg "{pattern}" {suspected_file}
```

**GATE 4:** All gaps researched with evidence.

---

## 🔒 PHASE 4: GAP ANALYSIS [GATE 5]

Classify EVERY file:

| Status | Meaning |
|--------|---------|
| ✅ EXISTS | Identical in repo |
| ⚠️ PARTIAL | Some functionality exists |
| 🆕 NEW | Not in repo |
| 🔄 CONFLICTS | Different implementation |

Confidence scores required (95%+, 80-94%, 60-79%, <60% flagged).

**GATE 5:** Every file has status + confidence + evidence.

---

## 🔒 PHASE 5: INLINE PRESENTATION [GATE 6]

**Present analysis INLINE using format above. NO file generation.**

**GATE 6:** Analysis presented inline with YNP recommendation.

---

## 🔒 PHASE 6: USER CONFIRMATION [GATE 7]

Wait for user to:
- **Confirm:** "yes" / "proceed" / "merge"
- **Modify:** User provides corrections
- **Reject:** "no" / "stop"

**GATE 7:** User response received.

---

## 🔒 PHASE 7: EXECUTION + OPTIONAL REPORT [GATE 8]

After user confirms, choose ONE path:

### PATH A: FULL MERGE (Most Common)

**Use when:** All/most files should be adopted

```bash
# Git brings in ALL files automatically
gh pr merge {number} --squash --delete-branch -b "{summary}"
```

✅ Files appear in repo via git. No manual writing needed.

### PATH B: CHERRY-PICK (Selective Adoption)

**Use when:** Only some files wanted, others should be skipped

```bash
# Step 1: /harvest the diff to extract wanted changes
gh pr diff {number} > /tmp/pr_{number}.diff

# Step 2: Apply selectively (git handles files)
git apply --include='{path/to/wanted/*}' /tmp/pr_{number}.diff

# Step 3: Close PR without merge
gh pr close {number} --comment "Cherry-picked: {files}. Skipped: {files}."
```

### PATH C: CLOSE WITHOUT MERGE

**Use when:** PR rejected or superseded

```bash
gh pr close {number} --comment "{reason}"
```

---

### 🚫 FORBIDDEN: Manual File Writing

```
❌ NEVER DO THIS:
   1. Read PR diff
   2. Manually create file with Write tool
   3. Repeat for each file
   
✅ ALWAYS DO THIS:
   1. Analyze PR
   2. Merge (git transfers files) OR cherry-pick (git apply)
   3. Done
```

---

### If report requested (OPTIONAL):

```bash
python3 scripts/workflow/generate_gmp_report.py \
  --pr {number} \
  --title "{title}" \
  --adopted {count} \
  --skipped {count} \
  --realigned {count} \
  --tier {TIER} \
  --notes "{key findings}"
```

### Save lessons:

```bash
python3 agents/cursor/cursor_memory_client.py write \
  "PR #{number}: {key_finding}" --kind lesson
```

**GATE 8:** PR merged/closed via git, lessons saved, report generated if requested.

---

## 🚨 ENFORCEMENT RULES

| Rule | Response |
|------|----------|
| Skip Memory Injection | ❌ BLOCK |
| Skip Index Scan | ❌ BLOCK |
| File without status/confidence | ❌ BLOCK |
| Generate report mid-analysis | ❌ VIOLATION (ADR-0059) |
| Proceed without user confirm | ❌ VIOLATION |
| **Manual file write from PR diff** | ❌ VIOLATION (use git merge/apply) |
| Close PR before merge when adopting | ❌ VIOLATION (merge first!) |

---

## REPORT GENERATION (ON-DEMAND ONLY)

**Reports are NOT generated during analysis.** Per ADR-0059:

```bash
# Only run if user explicitly requests a report
python3 scripts/workflow/generate_gmp_report.py \
  --pr {number} \
  --title "{title}" \
  --adopted {count} \
  --skipped {count} \
  --realigned {count}
```

**When to generate:**
- User explicitly requests report
- Audit/compliance requirement
- Historical record needed

**When NOT to generate:**
- Quick PR analysis (inline sufficient)
- Simple merge (no complexity)
- User didn't ask

---

## EXAMPLE: Quick PR Analysis (Full Merge)

```
User: /pr #51

Agent:
## PR #51 Analysis: Spring Cleaning - Track All TODOs

**Author:** @cryptoxdog | **Files:** 11 | **Tier:** RUNTIME

### 📊 File Status

| File | Status | Confidence | Notes |
|------|--------|------------|-------|
| `core/governance/validation.py` | ⚠️ PARTIAL | 95% | Adds GMP-100 tag |
| `memory/consolidation.py` | ⚠️ PARTIAL | 95% | Adds GMP-118 tag |
| ... (9 more files) | | | |

### ✅ Adopt (11)
All 11 files — TODO tagging only, no behavior changes

### ❌ Skip (0)
None

### 🔧 Realign (0)
None

### /ynp

**YES:** Merge PR (git brings in 11 files automatically)
**NO:** None
**PROCEED:** `gh pr merge 51 --squash --delete-branch`

---

User: proceed

Agent: [executes: gh pr merge 51 --squash --delete-branch]
✅ PR #51 merged. Git transferred 11 files. No manual writing.
```

---

## EXAMPLE: Cherry-Pick (Selective Adoption)

```
User: /pr #52

Agent:
## PR #52 Analysis: New DI System

**Files:** 8 | **Tier:** KERNEL

### ✅ Adopt (5)
- `core/di/*.py` — new DI framework

### ❌ Skip (3)
- `config/settings.py` — conflicts with our config
- `tests/test_old.py` — outdated test patterns

### /ynp

**YES:** Cherry-pick 5 files (skip 3)
**PROCEED:** `/harvest` diff → selective apply

---

User: cherry-pick the 5

Agent: 
[Step 1: Harvest diff]
gh pr diff 52 > /tmp/pr_52.diff

[Step 2: Apply wanted files only]
git apply --include='core/di/*' /tmp/pr_52.diff

[Step 3: Close PR]
gh pr close 52 --comment "Cherry-picked: core/di/*. Skipped: config/settings.py, tests/test_old.py"

✅ 5 files adopted via git apply. PR closed.
```

---

## ANTI-PATTERN: What NOT To Do

```
❌ WRONG (actual mistake from PR #52):

User: proceed with adoption

Agent:
1. Read diff for file1.py
2. Write file1.py manually ← WRONG
3. Read diff for file2.py  
4. Write file2.py manually ← WRONG
... repeat 8 times...
5. Close PR without merging ← NOW FILES ARE ORPHANED

✅ CORRECT:

User: proceed with adoption

Agent:
1. gh pr merge 52 --squash --delete-branch
   ← Git transfers ALL files in one command
2. Done
```

---

## STOP CONDITIONS

| Condition | Action |
|-----------|--------|
| KERNEL_TIER touched | Flag, continue |
| >100 files | Suggest breaking PR |
| Confidence <60% | Flag for user |
| Conflicts found | Present options |

---

## REFERENCE

- **ADR-0059:** Inline Analysis with Script-Generated Reports
- **ADR-0060:** Git-Native PR Adoption (merge/apply, not manual write)
- **Report Script:** `scripts/workflow/generate_gmp_report.py`
- **Workflow Script:** `scripts/workflow/update_workflow_state.py`
- **/harvest:** Use for extracting selective changes from PR diff

---

## LESSONS LEARNED (2026-01-24)

**Mistake:** PR #52 analysis → manually wrote 8 files → closed PR → files orphaned from git history.

**Fix:** ALWAYS merge BEFORE close. Git handles file transfer. Manual write = violation.

--- End Command ---
