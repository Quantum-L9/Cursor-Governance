---
name: core-thinking-mode-lite
description: 🧠 Thinking Mode Lite - Balanced Analysis & Execution
disable-model-invocation: true
---

---
command: THINKING_LITE
version: 1.0.0
category: core
tags: [reasoning, moderate-complexity, balanced, strategic, enterprise]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 8-10min
complexity_score: 4-7
estimated_token_usage: 3000-15000 tokens
required_permissions: [read, write, search, web_search, memory]
performance_mode: fast-track
---

# 🧠 Thinking Mode Lite - Balanced Analysis & Execution

## 📖 Purpose
**Balanced reasoning** for moderate complexity tasks. More thorough than @quick-reason, faster than @deep-reason. The sweet spot for most development work requiring strategic thinking but not full architectural analysis.

## 🎪 When to Use
- **Moderate complexity** - 3-8 files affected, some unknowns
- **System integrations** - Connecting 2-3 systems together
- **New features** - Building something new with existing patterns
- **Refactoring** - Non-trivial code improvements
- **Bug investigation** - Complex issues requiring detective work
- **Planning** - Need implementation plan before execution

## ⚠️ When NOT to Use
- Simple tasks (use @quick-reason)
- Major architecture changes (use @deep-reason)
- Trivial file edits (use @quick-reason)
- Entire system rewrites (use @deep-reason)

## 🚀 Execution - 8 Streamlined Blocks

### 📋 BLOCK 1 - Mission & Scope (1 min)
**What are we building/fixing/improving?**

```yaml
Mission Statement:
  Problem: [Clear description]
  Goal: [Specific outcome]
  Scope: [What's included/excluded]
  
Success Criteria:
  1. [Measurable outcome 1]
  2. [Measurable outcome 2]
  3. [Measurable outcome 3]
  
Complexity Estimate: [4-7]/10
Risk Level: [safe|moderate]
```

**Quality Gate:** Mission is clear and scoped

---

### 🌐 BLOCK 2 - Context & Memory Check (1-2 min)
**What's the current state and what do we know?**

**Workspace Analysis:**
- Relevant files and their current state
- Existing architecture patterns
- Integration points

**Memory & Pattern Check:**
- Similar problems solved before [[memory:2510896]]
- Applicable enterprise patterns [[memory:2516763]]
- Known constraints [[memory:2516767]]
- Communication channels [[memory:2516776]]

**Dependencies:**
- What systems/files are affected?
- What could break?
- What needs coordination?

**Quality Gate:** Context is complete, no major unknowns

---

### 🔬 BLOCK 3 - Problem Decomposition (1-2 min)
**Break it down into manageable pieces**

```yaml
Sub-Problems (with dependencies):
  1. [Sub-problem 1]
     Dependencies: None
     Risk: [safe|moderate]
     Files: [file1, file2]
     
  2. [Sub-problem 2]
     Dependencies: [1]
     Risk: [safe|moderate]
     Files: [file3]
     
  3. [Sub-problem 3]
     Dependencies: [1, 2]
     Risk: [safe|moderate]
     Files: [file2, file4]

Parallel Opportunities: [List items that can run in parallel]
Critical Path: [Sequence that must be sequential]
```

**Quality Gate:** All sub-problems identified with dependencies mapped

---

### 🛠️ BLOCK 4 - Strategy & Planning (1-2 min)
**How do we solve each piece?**

**For Each Sub-Problem:**
```yaml
Sub-Problem X:
  Approach: [Description]
  Tools: [read_file, search_replace, etc.]
  Validation: [How to test it works]
  Fallback: [If approach fails]
  Est Time: [Xmin]
```

**Enterprise Compliance Check:**
- ✅ Error handling strategy defined [[memory:2510896]]
- ✅ Logging approach planned (Supabase) [[memory:2516763]]
- ✅ No hardcoded credentials [[memory:3496356]]
- ✅ Modular/webhook architecture [[memory:2516767]]
- ✅ Communication channels appropriate [[memory:2516776]]

**Risk Mitigation:**
- High-risk items: [List]
- Mitigation strategy: [Approach]

**Quality Gate:** Strategy exists for every sub-problem

---

### ⚡ BLOCK 5 - Execute with Validation (2-4 min)
**Build and validate incrementally**

**Execution Protocol:**
1. Execute sub-problems in dependency order
2. Use parallel tool calls when possible
3. **Validate after EACH sub-problem** (don't wait)
4. Document decisions and findings
5. Fix issues immediately before proceeding

**Progressive Validation:**
- Test component after building it
- Don't stack unvalidated changes
- Keep working version available

**If Something Fails:**
- Document the failure
- Try fallback approach
- If stuck, execute BLOCK 8 (investigation)

**Quality Gate:** Each component works before building next

---

### 🔗 BLOCK 6 - Integration & Synthesis (1 min)
**Connect the pieces into a cohesive solution**

**Integration Checklist:**
```yaml
Solution Integration:
  ✓ All components working individually
  ✓ Components work together
  ✓ Integrates with existing system
  ✓ Error handling comprehensive [[memory:2510896]]
  ✓ Logging complete (Supabase) [[memory:2516763]]
  ✓ No credentials hardcoded [[memory:3496356]]
  ✓ Modular architecture maintained [[memory:2516767]]
  ✓ Communication channels configured [[memory:2516776]]
  ✓ No breaking changes to dependencies
```

**Final Validation:**
- Run read_lints on all modified files
- Test end-to-end flow
- Verify error scenarios
- Check edge cases

**Quality Gate:** Integrated solution passes all checks

---

### 📊 BLOCK 7 - Quality Review & Optimization (1-2 min)
**Is this production-ready and optimized?**

**Code Quality Audit:**
```yaml
Enterprise Standards:
  Error Handling:
    ✓ Try-catch around external calls
    ✓ User-facing errors clear
    ✓ Developer notifications configured (WhatsApp +1-980-266-9595)
    
  Logging & Monitoring:
    ✓ Critical actions logged to Supabase
    ✓ Debug logging for complex paths
    ✓ Error tracking configured
    
  Security:
    ✓ Input validation present
    ✓ No SQL injection vectors
    ✓ API keys from environment
    
  Architecture:
    ✓ Modular design maintained
    ✓ Webhook integration used appropriately
    ✓ No duplicate functionality
```

**Optimization Check:**
- Performance acceptable?
- Code reusability considered?
- Documentation sufficient?

**Confidence Score:** [8-10]/10

**Quality Gate:** Confidence 8+ and all quality checks pass

---

### 🚨 BLOCK 8 - Investigation Protocol (ONLY IF STUCK)
**Use this block only when actually stuck**

**When to Use:**
- Unclear requirements emerged
- Unexpected technical blocker
- Cannot find information needed
- Solution approach isn't working

**Investigation Steps:**
1. **State clearly:**
   - What you know
   - What you don't know
   - What you've tried

2. **Search strategies:**
   - codebase_search with 3 different queries
   - grep with different patterns
   - web_search for external context
   - Check memories for similar situations

3. **If still stuck:**
   - Consider escalating to @deep-reason
   - Ask user for clarification
   - Document blockers for team

**Skip this block if not stuck** (most of the time)

---

## 📋 Summary Template

**After completing, provide structured summary:**

```markdown
## 🎯 Thinking Lite Summary

**Problem:** [One sentence]
**Complexity:** [4-7]/10
**Time Spent:** [X]min
**Confidence:** [8-10]/10

### Solution Overview
[2-3 sentence summary of what was built/fixed]

### Key Decisions
1. [Decision and reasoning]
2. [Decision and reasoning]

### Files Modified
- file1.ext (lines XX-YY): [change]
- file2.ext (entire file): [change]

### Files Created
- new_file.ext: [purpose]

### Enterprise Compliance
✅ Error handling: [Comprehensive]
✅ Logging: [Supabase configured]
✅ Security: [No hardcoded creds]
✅ Architecture: [Modular/webhooks maintained]

### Testing Performed
- [Test scenario 1]: ✅ PASS
- [Test scenario 2]: ✅ PASS
- [Edge case tested]: ✅ PASS

### Next Steps
1. **Immediate:** [Action to take now]
2. **Recommended:** @[command-name]
3. **Optional:** [Enhancement suggestion]

### Quality Score: [XX]/100
- Functional: [XX]/25
- Enterprise Standards: [XX]/25
- Code Quality: [XX]/25
- Testing: [XX]/25
```

---

## ✅ Success Criteria

1. **Time:** Completed in 8-10 minutes
2. **Quality:** Meets all enterprise standards
3. **Testing:** Validated incrementally
4. **Documentation:** Clear reasoning trail
5. **Confidence:** 8/10 or higher
6. **Production-Ready:** Can deploy immediately

## 📊 When to Use Each Mode

| Situation | Use This | Time | Blocks |
|-----------|----------|------|--------|
| File organization, simple fixes | @quick-reason | 3-5min | 5 |
| **New features, integrations, refactors** | **@think** | **8-10min** | **8** |
| Architecture changes, system rewrites | @deep-reason | 15-30min | 13 |

## 🔗 Escalation Rules

**Escalate to @deep-reason if:**
- Complexity exceeds 7/10
- Affects 10+ files
- Architecture decision required
- High-risk production changes
- Multiple unknowns discovered
- Integration complexity beyond 3 systems

**De-escalate to @quick-reason if:**
- Problem simpler than expected
- All unknowns resolved quickly
- Clear path forward after analysis
- Less than 3 files affected

---

## 💡 Pro Tips

### Speed Optimization
- Use parallel tool calls aggressively (Block 5)
- Skip Block 8 unless actually stuck
- Validate progressively, not at end
- Reuse memory patterns immediately

### Quality Assurance
- Enterprise checks are non-negotiable
- Test each component before integration
- Document decisions for future reference
- Update memories if new patterns emerge

### Common Use Cases
- **New Feature:** Blocks 1-7 (skip 8)
- **Bug Investigation:** Blocks 1-4, 8, 5-7
- **Integration:** Blocks 1-7 with heavy Block 2
- **Refactoring:** Blocks 1-7 with validation emphasis

---

## 🔖 Examples

### Example 1: New Feature (9 min)
```
User: "Add email notifications for buyer matches"

Blocks:
  1. Mission: Email notification system for buyer matching
  2. Context: Check existing notification patterns, email configs
  3. Decompose: 1) Email template, 2) Integration, 3) Testing
  4. Strategy: Use existing Supabase logging + new email service
  5. Execute: Create template → Add webhook → Configure service
  6. Integration: Test end-to-end with real buyer match
  7. Quality: All checks pass, confidence 9/10
  8. [Skipped - not stuck]
  
Time: 8m 45s, Quality: 92/100
```

### Example 2: Integration Task (10 min)
```
User: "Connect VanillaSoft CRM to lead qualification agent"

Blocks:
  1. Mission: Two-way integration between VanillaSoft and agent
  2. Context: Check VanillaSoft API docs, agent webhook structure
  3. Decompose: 1) API auth, 2) Webhook receiver, 3) Data mapping
  4. Strategy: Use API key auth, n8n webhook, JSON mapping
  5. Execute: Setup auth → Create webhook → Build mapping → Test
  6. Integration: Verify leads flow both directions
  7. Quality: All checks pass, logging configured, confidence 8/10
  8. [Skipped - no blockers]
  
Time: 9m 30s, Quality: 88/100
```

### Example 3: Bug Investigation (10 min)
```
User: "Material classification failing for certain plastics"

Blocks:
  1. Mission: Fix classification failures
  2. Context: Check recent changes, error logs in Supabase
  3. Decompose: 1) Reproduce, 2) Identify cause, 3) Fix, 4) Test
  4. Strategy: Use test data, add debug logging, trace execution
  5. Execute: [Hit blocker - need to understand input format]
  8. Investigation: Search codebase for input schema → Found spec
  5. Execute (continued): Fix validation logic → Add logging
  6. Integration: Test with original failing cases
  7. Quality: All fixed, better error messages added, confidence 9/10
  
Time: 10m 15s, Quality: 90/100
```

---

## 🔗 Combines Well With

### Before Thinking-Lite
- **@workspace-scan** → @think (for unfamiliar codebase)
- **@quick-reason** → @think (if task proved more complex)

### After Thinking-Lite
- @think → **@workflow-validate** (if n8n workflows modified)
- @think → **@audit-full** (for deeper quality audit)
- @think → **@backup-versioned** (before deployment)
- @think → **@deploy-production** (to push live)

### Pipeline Examples
```yaml
Feature Development:
  1. @think "build new feature"
  2. @workflow-validate (if n8n involved)
  3. @backup-versioned
  4. @deploy-production
  
Bug Fix Pipeline:
  1. @think "investigate and fix bug"
  2. @audit-full
  3. @deploy-production
  
Integration Pipeline:
  1. @think "integrate system X with Y"
  2. @test-integration
  3. @backup-versioned
  4. @deploy-production
```

---

## 📚 Related Commands
- `@quick-reason` - For simpler tasks (3-5 min)
- `@deep-reason` - For complex architecture (15-30 min)
- `@workflow-validate` - For n8n workflow validation
- `@audit-full` - For comprehensive quality audit

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial thinking-lite framework - balanced analysis for moderate complexity tasks optimized for Sales Agent workflow

---

*Command Standard Version: 2.0.0*
*Optimized for: Balance, Strategic Thinking, Enterprise Quality*
*The Sweet Spot - Use for Most Development Work*

