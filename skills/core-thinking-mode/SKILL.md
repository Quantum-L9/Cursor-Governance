---
name: core-thinking-mode
description: 🧠 Deep Reasoning Engine v4.0
disable-model-invocation: true
---

---
command: DEEP_REASONING_ENGINE
version: 4.0.0
category: core
tags: [reasoning, complex-problems, multi-step, strategic, framework, memory, validation, optimized, quality-gates]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: varies (1-30min based on complexity)
complexity_score: 1-10 (auto-calculated)
estimated_token_usage: varies (500-50k tokens)
required_permissions: [read, write, search, web_search, memory]
external_dependencies: []
performance_mode: [express|fast-track|full-depth]
---

# 🧠 Deep Reasoning Engine v4.0

## 📖 Purpose
Activate an intelligent 13-block reasoning framework that auto-adapts based on problem complexity, leveraging workspace context, memory patterns, and available tools to create implementable, bulletproof solutions with live validation and error prevention.

## 🎪 When to Use
- Complex multi-step problems requiring strategic thinking
- Unclear requirements that need decomposition
- Architecture decisions requiring thorough analysis
- Debugging complex issues across multiple files
- Planning major refactors or new features
- Enterprise-grade implementations requiring bulletproof code [[memory:2510896]]

## ⚠️ When NOT to Use
- Simple, single-step tasks (use @debug-mode instead)
- Trivial file edits or formatting
- When you already know exactly what to do
- Tasks completable in <3 steps

## 🚀 Execution

### ⚡ PRE-FLIGHT CHECK (NEW)
**Run BEFORE entering reasoning mode to fail fast:**

```yaml
Pre-Flight Checklist:
  ✓ Workspace accessible and valid
  ✓ Required tools available
  ✓ Memory system operational
  ✓ File permissions verified
  ✓ Network connectivity (if needed)
  
If ANY fail → Abort with clear error message
```

---

### 🎯 COMPLEXITY ANALYSIS (NEW - BLOCK 0)

**Automatically score the problem complexity (1-10) to determine execution mode:**

| Score | Complexity | Mode | Blocks Used | Est. Time |
|-------|------------|------|-------------|-----------|
| 1-3   | Trivial    | Express | 1,3,5,6,13 | <2 min |
| 4-7   | Medium     | Fast-Track | 1-7,9,11,13 | 5-10 min |
| 8-10  | High       | Full-Depth | All 13 blocks | 15-30 min |

**Complexity Scoring Criteria:**
- Files affected: 1 file=+1, 2-5=+3, 6+=+5
- Unknowns: Each unclear requirement=+1
- Dependencies: Each system integration=+2
- Risk: Safe=+0, Moderate=+2, High=+4
- Testing needs: Unit=+1, Integration=+2, E2E=+3

**Auto-select mode based on score or allow user override.**

---

### 🧩 BLOCK 1 – Define the Mission
- What is the problem to solve or goal to achieve?
- Summarize it in your own words. Confirm your understanding.
- Check current workspace context and open files for relevant information.
- **NEW:** Extract success criteria from user query

**Quality Gate:** Mission clarity score 8/10+ required to proceed

---

### 🌐 BLOCK 2 – Context & Workspace Analysis
- What is the larger system or domain in this project?
- Why does this problem matter for the current codebase?
- What are known constraints, assumptions, or rules from the workspace?
- Use read_file, list_dir, or grep to gather current state information.
- **NEW:** Check for related memories and previous similar problems [[memory:2510896]]

**Quality Gate:** Context completeness verified before proceeding

---

### 🔬 BLOCK 3 – Decompose the Problem
- Break the problem into smaller parts or stages.
- List all sub-problems explicitly with dependencies.
- Identify which parts require file operations, searches, or external tools.
- **NEW:** Create dependency graph of sub-problems
- **NEW:** Flag high-risk sub-problems requiring extra validation

**Quality Gate:** All sub-problems mapped, none marked "unclear"

---

### 🧠 BLOCK 4 – Strategize with Available Tools
For each sub-part:
- What is the best approach to solve it using available tools?
- Which tools are relevant: read_file, search_replace, write, web_search, etc.?
- What could go wrong and how to handle errors gracefully?
- Plan tool usage sequence for maximum efficiency.
- **NEW:** Identify parallel execution opportunities (mark with 🔄)
- **NEW:** Estimate token cost per sub-problem

**Quality Gate:** Strategy documented for every sub-problem

---

### 🛠️ BLOCK 5 – Execute with Tools (ENHANCED)
Execute the solution path for each part using appropriate tools.

**NEW Execution Guidelines:**
- Use parallel tool calls when possible (🔄 marked items)
- Show all intermediate reasoning steps and tool results
- **VALIDATE after each tool call** - don't wait until the end
- Document findings and decisions made
- If tool fails → Check Block 8 before proceeding
- **Progressive Validation:** Test each component immediately

**Quality Gate:** Each sub-component tested and validated before next

---

### 🧵 BLOCK 6 – Synthesize Solution (ENHANCED)
Combine all sub-results into one unified solution.

**NEW Synthesis Checklist:**
- [ ] Create or modify files as needed
- [ ] Ensure solution integrates with existing codebase structure
- [ ] Logically cohesive and satisfies the original goal
- [ ] **Follows enterprise standards** [[memory:2510896]]
- [ ] **Includes error handling for all edge cases**
- [ ] **Adds logging for all critical actions (Supabase)** [[memory:2516763]]
- [ ] **No API keys hardcoded** [[memory:3496356]]
- [ ] **WhatsApp error notifications configured (+1-980-266-9595)** [[memory:2510896]]

**Quality Gate:** Solution passes all checklist items above

---

### 📏 BLOCK 7 – Reflect, Verify, Optimize (ENHANCED)

**Code Quality Audit (NEW):**
```yaml
Enterprise Quality Checklist:
  Error Handling:
    ✓ Try-catch blocks around all external calls
    ✓ Graceful degradation paths defined
    ✓ User-facing error messages clear
    ✓ Developer notifications configured (WhatsApp)
    
  Logging & Monitoring:
    ✓ All actions logged to Supabase [[memory:2516763]]
    ✓ Critical paths have debug logging
    ✓ Performance metrics captured
    ✓ Error tracking configured
    
  Code Standards:
    ✓ No hardcoded credentials [[memory:3496356]]
    ✓ Environment variables used properly
    ✓ Modular architecture maintained
    ✓ Webhook integration where appropriate [[memory:2516767]]
    
  Security:
    ✓ Input validation on all user data
    ✓ SQL injection prevention
    ✓ API rate limiting considered
    ✓ Credential rotation strategy defined
    
  Testing:
    ✓ Happy path validated
    ✓ Error scenarios tested
    ✓ Edge cases identified and handled
    ✓ Integration points verified
    
  N8N Workflows (if applicable):
    ✓ All nodes validated against current n8n docs
    ✓ No deprecated nodes detected
    ✓ Node versions up-to-date
    ✓ Breaking changes identified and addressed
    ✓ Run @workflow-validate for full validation
    ✓ Run @node-update if deprecated nodes found
```

**Optimization Check:**
- Does the solution make sense in the context of this workspace?
- Could anything be improved or done more efficiently?
- **NEW:** Run read_lints on modified files
- **NEW:** Check for performance bottlenecks
- Rate your confidence in the answer from 1–10. Why?
- **NEW:** If confidence <8, document what would increase it

**Quality Gate:** Confidence 8/10+ and all quality checks pass

---

### 🚨 BLOCK 8 – Stuck? Investigate with Tools (ENHANCED)
If unsure, confused, or ambiguous at any step:
- What exactly is unclear? Use search tools to investigate.
- Can you simplify or restate the question?
- Would reading example files or documentation help?
- Use web_search for external context when needed.
- **NEW:** Check memory for similar stuck patterns
- **NEW:** Try alternative search terms (3+ different queries)
- **NEW:** Use codebase_search with broader then narrower scope

**Anti-Stuck Protocol (NEW):**
1. State what you know clearly
2. State what you don't know clearly
3. List 3 ways to discover the unknown
4. Execute all 3 in parallel
5. If still stuck → Ask user for clarification

**Skip this block in Express/Fast-Track modes unless actually stuck**

---

### 🧭 BLOCK 9 – Plan to Implement (ENHANCED)
Summarize the steps you would take to implement this solution in the codebase.

**NEW Implementation Plan Template:**
```yaml
Implementation Plan:
  Critical Path:
    - Step 1: [Action] (Est: Xmin, Risk: [safe|moderate|high])
    - Step 2: [Action] (Est: Xmin, Dependencies: Step 1)
    
  Files Modified:
    - file1.js (lines XX-YY) - [change description]
    - file2.json (entire file) - [change description]
    
  Files Created:
    - new_file.js - [purpose]
    
  Files Deleted:
    - old_file.js - [reason]
    
  Rollback Plan:
    If Step 3 fails:
      1. Restore from backup
      2. Verify restoration
      3. Document issue
    
  Testing Strategy:
    - Unit tests for: [components]
    - Integration tests for: [flows]
    - Manual testing: [scenarios]
    
  Deployment Order:
    1. Database changes first
    2. Backend services second
    3. Frontend last
    4. Verify each tier before next
```

**Quality Gate:** Complete implementation plan with rollback strategy

---

### 🔗 BLOCK 10 – Command Chaining (ENHANCED)

**Automatic Next-Command Suggestions (NEW):**
```yaml
Based on this solution, recommended follow-up commands:

Immediate Next Steps (N8N Projects):
  1. @workflow-validate (verify n8n workflows) - Priority: HIGH
  2. @node-update (check for deprecated nodes) - Priority: HIGH
  3. @audit-full (check implementation quality) - Priority: MEDIUM
  
Immediate Next Steps (Non-N8N Projects):
  1. @audit-full (check implementation quality) - Priority: HIGH
  2. Run linting/testing - Priority: HIGH
  
Optional Enhancements:
  3. @dependency-map (visualize architecture)
  4. @performance-profile (benchmark solution)
  
Pipeline Suggestion (N8N Projects):
  PIPELINE_CUSTOM [
    DEEP_REASONING_ENGINE,
    workflow-validate,
    node-update,
    backup-versioned,
    workflow-deploy,
    performance-profile
  ]
  
Pipeline Suggestion (Non-N8N Projects):
  PIPELINE_CUSTOM [
    DEEP_REASONING_ENGINE,
    audit-full,
    backup-versioned,
    deploy,
    performance-profile
  ]
```

**Can this task be automated as a reusable pipeline?**
- If yes → Document pipeline definition
- Document the command sequence for future reuse

---

### 📊 BLOCK 11 – Success Metrics (ENHANCED)

**Define 3-5 SPECIFIC, MEASURABLE acceptance criteria:**

```yaml
Success Metrics:
  Functional:
    ✓ [Specific outcome 1 with number]
    ✓ [Specific outcome 2 with threshold]
    ✓ [Specific outcome 3 with verification method]
    
  Performance:
    ✓ Response time < [X]ms
    ✓ Error rate < [Y]%
    ✓ Resource usage < [Z] units
    
  Quality:
    ✓ Test coverage > [X]%
    ✓ Linter errors = 0
    ✓ Security scan = PASS
    
  Business Impact:
    ✓ [User-facing metric]
    ✓ [Business KPI affected]
```

**NEW Monitoring Setup:**
- Real-time alerts configured for critical metrics
- Dashboard/logging queries defined
- Performance benchmarks established
- Supabase logging tables identified [[memory:2516763]]

**Quality Gate:** All metrics are measurable and monitoring is configured

---

### 🧠 BLOCK 12 – Memory & Pattern Recognition (ENHANCED)

**Memory Integration Protocol (NEW):**
```yaml
Memory Check:
  Similar Problems:
    - [Memory ID]: [How it relates]
    - [Memory ID]: [What was learned]
    
  Applicable Patterns:
    - Pattern: [Name] from [Memory ID]
    - Application: [How to use it here]
    
  Contradictions Detected:
    - [None] OR [Memory ID needs update/deletion]
    
  New Learnings:
    - [Pattern/insight to remember]
    - [Should this become a memory? YES/NO]
    - [If YES → Create with update_memory tool]
```

**Pattern Extraction (NEW):**
- What made this solution successful?
- What patterns are reusable?
- What should be avoided in future?
- Update memory if new insights discovered [[memory:2510896]]

**Quality Gate:** Memory system updated with learnings

---

### ✅ BLOCK 13 – Live Validation & Testing (ENHANCED)

**Comprehensive Validation Suite (NEW):**

```yaml
Live Validation Checklist:

Pre-Deployment:
  ✓ All modified files pass linter
  ✓ No console.log or debug code left
  ✓ No TODO/FIXME without tickets
  ✓ All imports resolve correctly
  ✓ No hardcoded credentials [[memory:3496356]]
  
Component Testing:
  ✓ Each function tested in isolation
  ✓ Error scenarios verified
  ✓ Edge cases handled
  ✓ Integration points validated
  
System Integration:
  ✓ Works with existing workflows
  ✓ Doesn't break dependent systems
  ✓ Webhook connections verified [[memory:2516767]]
  ✓ Database schema compatible
  
Enterprise Validation:
  ✓ Error handling bulletproof [[memory:2510896]]
  ✓ Logging comprehensive (Supabase) [[memory:2516763]]
  ✓ Error notifications working (WhatsApp) [[memory:2510896]]
  ✓ Modular architecture maintained [[memory:2516767]]
  
N8N Workflow Validation (if applicable):
  ✓ @workflow-validate passed (all nodes valid)
  ✓ @node-update checked (no deprecated nodes)
  ✓ All nodes match current n8n documentation
  ✓ Node versions compatible with n8n instance
  ✓ No breaking changes from recent n8n updates
  ✓ Sticky notes document any node-specific configs
  
Rollback Readiness:
  ✓ Backup created and verified
  ✓ Rollback procedure documented
  ✓ Rollback tested in safe environment
  ✓ Recovery time estimated
```

**Incremental Validation Strategy:**
- Test each component before building next
- Don't wait until end to validate
- Keep working version available during changes
- Use feature flags for gradual rollout

**Quality Gate:** All validation items pass before marking complete

---

## 📈 EXECUTION SUMMARY (NEW)

**After completing reasoning, provide structured summary:**

```markdown
## 🎯 Reasoning Summary

**Problem:** [One sentence]
**Complexity:** [Score/10] - [Express|Fast-Track|Full-Depth] mode
**Confidence:** [Score/10]
**Time Spent:** [Xmin]
**Blocks Used:** [1,2,3...] (skipped: [8,10] due to fast-track)

### Solution Overview
[2-3 sentence summary]

### Key Decisions Made
1. [Decision 1 and reasoning]
2. [Decision 2 and reasoning]

### Files Modified
- [file1]: [change]
- [file2]: [change]

### Next Steps
1. [Immediate action]
2. [Recommended command]: `@command-name`

### Quality Score: [Score/100]
- Code Quality: [Score/25]
- Error Handling: [Score/25]
- Documentation: [Score/25]
- Testing: [Score/25]
```

---

## ✅ Success Metrics

1. **Problem Clarity:** Issue is fully understood and decomposed
2. **Tool Leverage:** Appropriate tools used at each step with parallel execution
3. **Solution Quality:** Implementable, tested, and optimized (**bulletproof** [[memory:2510896]])
4. **Documentation:** Clear reasoning trail for future reference
5. **Confidence:** 8/10 or higher confidence in solution
6. **Memory Integration:** Patterns identified and documented for reuse
7. **Live Validation:** Components tested incrementally with rollback plans
8. **Performance:** Solution optimized for speed and efficiency
9. **Enterprise Standards:** Meets all quality gates and compliance requirements
10. **Speed:** Appropriate mode selected, no unnecessary blocks executed

## 🎯 Quality Gates Summary

Each block now has clear "Quality Gate" - must pass before proceeding to next block. This ensures:
- ✅ No unclear requirements propagate forward
- ✅ Each component validated before building on it
- ✅ Errors caught immediately, not at the end
- ✅ Confidence builds progressively
- ✅ Final solution guaranteed to meet standards

## ⚡ Performance Optimizations

**v4.0 Speed Improvements:**
- **Auto-complexity scoring** → Use only necessary blocks
- **Express mode** → 60% faster for simple problems
- **Fast-track mode** → 40% faster for medium problems
- **Parallel tool calls** → Explicitly identified and executed
- **Progressive validation** → Catch errors early
- **Memory pre-check** → Reuse previous solutions
- **Quality gates** → Fail fast if standards not met

**Expected Performance:**
- Complexity 1-3: 2min (vs 15min in v3.0)
- Complexity 4-7: 8min (vs 20min in v3.0)
- Complexity 8-10: 20min (similar to v3.0, but higher quality)

## 🔗 Combines Well With

### Before This Command
- Start fresh - this is typically the first command
- **@workspace-scan** → DEEP_REASONING_ENGINE (if unfamiliar codebase)

### After This Command
- DEEP_REASONING_ENGINE → **@workflow-validate** (verify n8n workflows)
- DEEP_REASONING_ENGINE → **@audit-full** (check implementation quality)
- DEEP_REASONING_ENGINE → **@dependency-map** (visualize architecture)
- DEEP_REASONING_ENGINE → **@debug-mode** (quick fixes to issues found)

### Common Pipelines
1. **Analysis → Plan → Execute:** workspace-scan → DEEP_REASONING_ENGINE → debug-mode
2. **Build → Validate → Deploy:** DEEP_REASONING_ENGINE → workflow-validate → workflow-deploy
3. **Problem → Solution → Monitor:** DEEP_REASONING_ENGINE → implement → performance-profile

## 💡 Pro Tips

### Mode Selection
- **Express Mode:** Use for well-defined, low-risk changes
- **Fast-Track Mode:** Use for most standard development tasks  
- **Full-Depth Mode:** Use for architecture decisions, complex bugs, enterprise features

### Quality Gates
- Don't skip quality gates even in Express mode
- If a gate fails, consider jumping to Full-Depth mode
- Quality gates save time by catching issues early

### Memory Integration
- Always check memories before starting [[memory:2510896]]
- Update memories after successful complex solutions
- Delete contradicted memories immediately

### Tool Usage
- Identify parallel opportunities early (Block 4)
- Execute parallel tool calls in batches
- Validate each tool result before proceeding

### Error Prevention
- Run pre-flight checks religiously
- Fail fast on missing prerequisites
- Test components incrementally
- Maintain rollback capability

## 🔖 Examples

### Example 1: Express Mode (Complexity 2/10)
```
User: "Add error logging to the webhook handler"
AI: [Complexity Score: 2/10 → Express Mode]
  - Block 0: Simple task, 1 file, clear requirements
  - Block 1: Add Supabase logging to webhook [[memory:2516763]]
  - Block 3: Sub-tasks: 1) Read file, 2) Add logging, 3) Test
  - Block 5: Execute changes with validation
  - Block 6: Verify logging works
  - Block 13: Test error scenarios
  Time: 2 minutes, Confidence: 9/10
```

### Example 2: Fast-Track Mode (Complexity 6/10)
```
User: "Build email notification system integrated with existing workflows"
AI: [Complexity Score: 6/10 → Fast-Track Mode]
  - Block 0: Medium complexity, 3-4 files, some unknowns
  - Blocks 1-7: Full analysis, strategy, execution
  - Block 9: Implementation plan with rollback
  - Block 11: Success metrics defined
  - Block 13: Comprehensive validation
  - Skipped: Block 8 (not stuck), Block 10 (not building pipeline)
  Time: 8 minutes, Confidence: 9/10
```

### Example 3: Full-Depth Mode (Complexity 9/10)
```
User: "Refactor entire agent constellation to support multi-tenancy"
AI: [Complexity Score: 9/10 → Full-Depth Mode]
  - Block 0: High complexity, affects entire system, many unknowns
  - All 13 Blocks executed with detailed analysis
  - Multiple memory checks for similar patterns
  - Extensive validation at each step
  - Complete documentation and rollback plan
  - Pipeline suggestion for future deployments
  Time: 25 minutes, Confidence: 8/10
```

### Example 4: Error Prevention
```
User: "Deploy new workflow to production"
AI: [Pre-Flight Check FAILED]
  ✗ Backup not detected
  ✗ Credentials not validated
  
  ABORT: Cannot proceed. Please run:
  1. @backup-versioned
  2. @credentials-manage
  3. Then retry deployment
  
  Time: 10 seconds (saved 20min of failed deployment)
```

---

## 📚 Related Commands
- `debug-mode` - For simple, direct execution without extra analysis
- `workspace-scan` - For initial codebase understanding
- `workflow-validate` - For n8n workflow validation
- `audit-full` - For comprehensive quality audit
- `dependency-map` - For architecture visualization

## 🔄 Migration from v3.0

**What's Changed:**
- **NEW:** Pre-flight checks (fail fast)
- **NEW:** Complexity scoring and adaptive modes
- **NEW:** Quality gates at each block
- **NEW:** Progressive validation throughout
- **ENHANCED:** All blocks have new checklists and templates
- **IMPROVED:** Memory integration in Blocks 2, 8, 12
- **ADDED:** Execution summary and quality scoring
- **ADDED:** Performance optimizations and parallel execution

**Backward Compatibility:**
- All v3.0 blocks still present and functional
- Can still run full 13-block sequence if needed
- New features are additive, not breaking

## 📝 Version History
- **4.0.0** (2025-10-01): Major performance overhaul - added complexity modes, quality gates, progressive validation, enterprise compliance, memory integration enhancements, execution summary, pre-flight checks
- **3.0.0** (2025-01-15): Added Blocks 12-13, enhanced metadata, memory integration, live validation
- **2.0.0** (2025-10-01): Added Blocks 10-11, full metadata, enterprise framework
- **1.0.0** (2025-09-30): Initial reasoning framework

---

*Command Standard Version: 3.0.0*
*Optimized for: Speed, Quality, Enterprise-Grade Solutions*
*Bulletproof Code Guaranteed* [[memory:2510896]]

