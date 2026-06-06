---
name: core-quick-reason
description: ⚡ Quick Reason - Fast Structured Analysis
disable-model-invocation: true
---

---
command: QUICK_REASON
version: 1.0.0
category: core
tags: [reasoning, fast, daily-driver, practical, actionable]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 3-5min
complexity_score: 1-5
estimated_token_usage: 500-3000 tokens
required_permissions: [read, write, search, memory]
performance_mode: express
---

# ⚡ Quick Reason - Fast Structured Analysis

## 📖 Purpose
Your **daily driver** for 90% of tasks. Rapid structured analysis that gets you from problem to solution in 3-5 minutes with clear next steps.

## 🎪 When to Use
- **Daily tasks** - File organization, cleanup, quick refactors
- **Clear requirements** - You know what needs to be done, just need structured execution
- **Single-system changes** - Modifications to 1-3 files
- **Well-understood problems** - No major unknowns
- **Fast iterations** - Quick fixes, improvements, validations

## ⚠️ When NOT to Use
- Major architecture changes (use @deep-reason)
- Multiple system integrations (use @think)
- Unclear requirements needing deep analysis (use @think)
- High-risk production changes (use @think or @deep-reason)

## 🚀 Execution - 5 Fast Blocks

### ⚡ BLOCK 1 - Mission Clarity (30 seconds)
**What are we solving?**
- State the problem in one clear sentence
- Extract success criteria from user request
- Check if this is actually a quick-reason task (if not, escalate to @think)

**Output:** Clear mission statement + success criteria

---

### 🔍 BLOCK 2 - Context Scan (1-2 min)
**What do we need to know?**
- Scan workspace for relevant files (use list_dir, grep if needed)
- Check memories for similar patterns [[memory:2510896]] [[memory:2516763]]
- Identify files that need modification
- Note any enterprise standards that apply

**Output:** List of relevant files + applicable patterns

---

### 🎯 BLOCK 3 - Strategy & Execute (2-3 min)
**How do we solve it?**

**Strategy:**
- Break into 2-5 clear steps
- Identify parallel execution opportunities
- Plan tool usage (read_file, search_replace, write, etc.)

**Execute:**
- Run tool calls (parallelize when possible)
- Validate after each step
- Fix issues immediately

**Enterprise Checks:**
- ✅ No hardcoded credentials [[memory:3496356]]
- ✅ Supabase logging if needed [[memory:2516763]]
- ✅ Error handling for external calls [[memory:2510896]]
- ✅ Modular architecture maintained [[memory:2516767]]

**Output:** Solution implemented with validation

---

### ✅ BLOCK 4 - Validate & Verify (1 min)
**Does it work?**

**Quick Validation:**
- Run read_lints on modified files
- Test the change works as expected
- No console.log or debug code left
- No TODOs without tracking

**Quality Score (Quick):**
- Functional: ✅/❌
- Clean: ✅/❌
- Enterprise-compliant: ✅/❌

**Output:** Validated solution ready to use

---

### 📋 BLOCK 5 - Summary & Next (30 seconds)
**What changed and what's next?**

```yaml
Quick Summary:
  Problem: [One sentence]
  Solution: [One sentence]
  
  Files Changed:
    - file1.ext: [brief description]
    - file2.ext: [brief description]
  
  Confidence: [8-10]/10
  Time: [X]min
  
  Next Action:
    Immediate: [What to do now]
    Suggested: @[command-name] (if applicable)
    
  Notes: [Any gotchas or important info]
```

**Output:** Clear summary with next steps

---

## 🎯 Success Criteria

1. **Speed:** Completed in 3-5 minutes
2. **Clarity:** Problem → Solution path is obvious
3. **Quality:** Meets enterprise standards despite speed
4. **Actionable:** Clear next steps provided
5. **Validation:** Changes tested and working

## 📊 Performance Expectations

| Task Type | Typical Time | Confidence |
|-----------|--------------|------------|
| File organization | 2-3 min | 9/10 |
| Simple refactors | 3-4 min | 9/10 |
| Documentation updates | 2-3 min | 10/10 |
| Config changes | 3-5 min | 8/10 |
| Quick bug fixes | 4-5 min | 8/10 |

## 🔗 When to Escalate

**Escalate to @think if:**
- Takes longer than 5 minutes
- More than 5 files affected
- Unclear requirements emerge
- Integration complexity discovered
- Risk level is higher than expected

**Escalate to @deep-reason if:**
- Architectural decisions needed
- Multiple system impacts
- High-risk production changes
- Complex unknowns discovered

## 💡 Pro Tips

### Speed Optimization
- Start with clear problem statement
- Use parallel tool calls aggressively
- Validate incrementally, not at end
- Keep enterprise checks lightweight but thorough

### Common Patterns
- **File cleanup:** list_dir → identify targets → batch delete/move
- **Quick refactor:** grep → search_replace → validate
- **Documentation:** read → update → validate links
- **Config update:** read → modify → test → deploy

### Memory Integration
- Always check memories first (saves 1-2 min)
- Update memories if new pattern discovered
- Use memory shortcuts for common tasks

## 🔖 Examples

### Example 1: File Organization (2 min)
```
User: "Move these audit reports to proper location"
AI:
  Block 1: Organize reports to documentation structure
  Block 2: Scan for report files, check doc structure
  Block 3: Create folders → Move files → Update README
  Block 4: Verify locations, test links
  Block 5: Summary - 4 files moved, README updated
  
  Time: 2m 15s, Confidence: 10/10
```

### Example 2: Quick Refactor (4 min)
```
User: "Rename function processData to processPlasticData across project"
AI:
  Block 1: Rename function across all files
  Block 2: Grep for all occurrences (found 12 in 3 files)
  Block 3: search_replace in all 3 files → Validate each
  Block 4: Run linter, check no broken imports
  Block 5: Summary - Function renamed, 12 occurrences updated
  
  Time: 4m 10s, Confidence: 9/10
```

### Example 3: Documentation Update (3 min)
```
User: "Update README with new command structure"
AI:
  Block 1: Add new commands to README
  Block 2: Read current README, check command list
  Block 3: Add new section → Update TOC → Add examples
  Block 4: Validate markdown, check links
  Block 5: Summary - README updated with 5 new commands
  
  Time: 2m 45s, Confidence: 10/10
```

### Example 4: Escalation Needed
```
User: "Refactor authentication to support OAuth2"
AI:
  Block 1: OAuth2 authentication implementation
  Block 2: [Realizes this affects multiple systems]
  
  ⚠️ ESCALATION NEEDED
  This task requires @think or @deep-reason:
  - Affects 8+ files across 3 services
  - Architecture decision needed
  - Security implications
  - Integration complexity high
  
  Recommended: @think "refactor auth to OAuth2"
  
  Time: 45s (saved by early escalation)
```

---

## 🔗 Combines Well With

### Before Quick-Reason
- Start fresh - this is your first command for most tasks

### After Quick-Reason
- **@workflow-validate** - If you modified n8n workflows
- **@audit-full** - If you want deeper quality check
- **@backup-versioned** - Before deploying changes
- **@deploy-production** - To push changes live

### Quick-Reason in Pipelines
```yaml
Common Workflow:
  1. @quick-reason "organize files"
  2. @backup-versioned
  3. @audit-full (optional)
  4. Done!
  
Fast Iteration:
  1. @quick-reason "fix bug"
  2. @quick-reason "update docs"
  3. @quick-reason "add tests"
  4. @deploy-production
```

---

## 📚 Related Commands
- `@think` - For moderate complexity (8-10 min)
- `@deep-reason` - For complex architecture (15-30 min)
- `@debug-mode` - For ultra-fast single actions
- `@workflow-validate` - For n8n workflow checks

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial quick reasoning framework optimized for Sales Agent daily workflow

---

*Command Standard Version: 2.0.0*
*Optimized for: Speed, Daily Tasks, Practical Solutions*
*Your Daily Driver - Use for 90% of Tasks*

