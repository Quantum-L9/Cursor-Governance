---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-SSP-001"
component_name: "Session Startup Protocol"
layer: "intelligence"
domain: "session_management"
type: "protocol"
status: "active"
created: "2025-11-07T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["INT-RSN-001", "INT-RSN-002", "INT-RSN-003", "INT-ORC-001"]
integrates_with: ["INT-ADV-001", "EXE-WF-001", "EXE-OP-001"]
api_endpoints: []
data_sources: [".cursorrules", ".suite6-config.json", ".cursor-commands/learning/"]
outputs: ["session_initialization", "mode_activation", "verification_reports"]

# === OPERATIONAL METADATA ===
execution_mode: "mandatory"
monitoring_required: true
logging_level: "info"
performance_tier: "startup"

# === BUSINESS METADATA ===
purpose: "Ensure every session starts correctly with proper file loading, verification, and task routing to prevent mistakes"
summary: "Mandatory access sequence and verification protocol combining AI_ACCESS_PATTERN and MISTAKE_PREVENTION_SYSTEM for correct startup"
business_value: "Prevents repeated mistakes and ensures consistent governance activation across all sessions"
success_metrics: ["startup_success_rate >= 0.99", "mistake_prevention_rate >= 0.95", "governance_activation >= 1.0"]

# === INTEGRATION METADATA ===
suite_2_origin: "session-startup-protocol.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure, reasoning/YNP/dev mode activation, and comprehensive pre-action verification"

# === TAGS & CLASSIFICATION ===
tags: ["protocol", "session-startup", "verification", "mistake-prevention", "governance", "critical"]
keywords: ["startup", "session", "protocol", "verification", "mistake", "prevention"]
related_components: ["INT-RSN-001", "INT-RSN-002", "INT-RSN-003", "INT-ORC-001"]
startup_required: true
mode_type: "protocol"
---

# Session Startup Protocol

## Purpose

Ensure every session starts correctly with proper file loading, verification, and task routing. Prevent mistakes through systematic pre-action verification.

---

## A. Mandatory Session Initialization

### STEP 1: Load Governance Files (MANDATORY)

**Execute at EVERY session start:**

```
1. READ: .cursorrules (workspace root) AND @.cursor-commands/templates/.cursorrules
   └─ Purpose: Core governance rules and standards (workspace-specific AND GlobalCommands template)
   └─ Duration: 1 minute (both files)
   └─ Skip: NEVER
   └─ Note: Read BOTH files to ensure complete governance coverage

2. READ: ALL files in @.cursor-commands/learning/ folder (recursive, GlobalCommands)
   └─ Purpose: Load ALL learning files from GlobalCommands (failures, patterns, solutions, n8n lessons)
   └─ Method: Read every .md file found recursively in .cursor-commands/learning/
   └─ Duration: 2-3 minutes (all files)
   └─ Skip: NEVER
   └─ Note: This is the GlobalCommands learning folder (via symlink)

3. CHECK: .suite6-config.json
   └─ Purpose: Verify governance enabled
   └─ Duration: 5 seconds
   └─ Skip: Only if checked in last 10 minutes
```

### STEP 1.5: Load Standard Operating Modes (MANDATORY)

**Enable Reasoning, YNP, and Dev Mode at EVERY session start:**

```
4. READ: @.cursor-commands/profiles/reasoning_n8n.md
   └─ Purpose: Enable n8n-specific reasoning capabilities
   └─ Mode Type: Reasoning
   └─ Duration: 2 minutes
   └─ Skip: NEVER

5. READ: @.cursor-commands/profiles/reasoning_docs.md
   └─ Purpose: Enable strategic document reasoning capabilities
   └─ Mode Type: Reasoning
   └─ Duration: 2 minutes
   └─ Skip: NEVER

6. READ: @.cursor-commands/profiles/reasoning_technical_operations.md
   └─ Purpose: Enable technical operations reasoning capabilities
   └─ Mode Type: Reasoning
   └─ Duration: 2 minutes
   └─ Skip: NEVER

7. READ: @.cursor-commands/profiles/ynp_mode.md
   └─ Purpose: Enable YNP (Your Next Prompt) Mode - strategic co-pilot operation
   └─ Mode Type: YNP
   └─ Component: CMD-001
   └─ Duration: 1 minute
   └─ Skip: NEVER

8. READ: @.cursor-commands/profiles/dev_mode.md
   └─ Purpose: Enable Development Automation Mode - code analysis, module management, testing
   └─ Mode Type: Dev Mode
   └─ Component: CMD-003
   └─ Duration: 1 minute
   └─ Skip: NEVER

9. READ: @.cursor-commands/profiles/orchestrator.md
   └─ Purpose: Enable governance orchestration and coordination
   └─ Mode Type: Orchestration
   └─ Component: INT-ORC-001
   └─ Duration: 30 seconds
   └─ Skip: NEVER

10. READ: @.cursor-commands/commands/reasoning.md
   └─ Purpose: Enable /reasoning slash command - L9 Multi-Modal Reasoning
   └─ Mode Type: Command
   └─ Component: CMD-002
   └─ Duration: 2 minutes
   └─ Skip: NEVER

11. READ: @.cursor-commands/commands/forge.md
   └─ Purpose: Enable /forge slash command - Heavy Forge Mode
   └─ Mode Type: Command
   └─ Component: CMD-004
   └─ Duration: 1 minute
   └─ Skip: NEVER

12. READ: @.cursor-commands/commands/consolidate.md
   └─ Purpose: Enable /consolidate slash command
   └─ Mode Type: Command
   └─ Component: CMD-005
   └─ Duration: 1 minute
   └─ Skip: NEVER

13. READ: @.cursor-commands/commands/analyze-toolkit.md
   └─ Purpose: Enable /analyze-toolkit slash command
   └─ Mode Type: Command
   └─ Component: CMD-006
   └─ Duration: 1 minute
   └─ Skip: NEVER

14. READ: @.cursor-commands/commands/evaluate- Comprehensive Project Evaluation.md
   └─ Purpose: Enable /evaluate slash command
   └─ Mode Type: Command
   └─ Component: CMD-007
   └─ Duration: 1 minute
   └─ Skip: NEVER

15. READ: @.cursor-commands/profiles/workflow-governance.md
   └─ Purpose: Enable n8n workflow governance (referenced by orchestrator and reasoning profiles)
   └─ Mode Type: Validation
   └─ Component: EXE-WF-001
   └─ Duration: 1 minute
   └─ Skip: NEVER

16. READ: @.cursor-commands/profiles/operational-health.md
   └─ Purpose: System health monitoring (referenced by orchestrator and reasoning profiles)
   └─ Mode Type: Monitoring
   └─ Component: EXE-OP-001
   └─ Duration: 1 minute
   └─ Skip: NEVER

17. READ: @.cursor-commands/intelligence/meta-learning/meta-learning-log.md
   └─ Purpose: Meta-learning log (enabled in .suite6-config.json: meta_learning: true)
   └─ Mode Type: Learning System
   └─ Component: INT-ML-001
   └─ Duration: 1 minute
   └─ Skip: NEVER

18. READ: @.cursor-commands/intelligence/reasoning/cursor-native-reasoning.md
   └─ Purpose: 10-step reasoning framework (enabled in .suite6-config.json: cursor_native_reasoning: true)
   └─ Mode Type: Reasoning Engine
   └─ Component: INT-RE-001
   └─ Duration: 2 minutes
   └─ Skip: NEVER

19. READ: @.cursor-commands/foundation/logic/universal-kernel.md
   └─ Purpose: Formal logic validation kernel (enabled in .suite6-config.json: formal_logic_validation: true)
   └─ Mode Type: Kernel
   └─ Component: FND-LG-002
   └─ Duration: 1 minute
   └─ Skip: NEVER

20. READ: @.cursor-commands/foundation/logic/rule-registry.json
   └─ Purpose: Rule registry for formal validation (enabled in .suite6-config.json: formal_logic_validation: true)
   └─ Mode Type: Registry
   └─ Component: FND-LG-001
   └─ Duration: 30 seconds
   └─ Skip: NEVER
```

**Verification**: Post confirmation after loading
```
✅ Session initialized
   - Governance rules loaded (.cursorrules)
   - ALL GlobalCommands learning files loaded (.cursor-commands/learning/ - recursive)
   - Reasoning Mode ENABLED (n8n, docs, technical operations)
   - YNP Mode ENABLED (strategic co-pilot)
   - Dev Mode ENABLED (development automation)
   - Orchestrator ENABLED (governance coordination)
   - Slash Commands ENABLED (/reasoning, /forge, /consolidate, /analyze-toolkit, /evaluate)
   - Supporting Profiles ENABLED (workflow-governance, operational-health)
   - Feature Files ENABLED (meta-learning, cursor-native-reasoning, formal-logic-validation)
   - Suite 6 governance: ACTIVE
```

---

### STEP 2: Understand Task Context

**Before ANY action, determine task type:**

```
Task Type Decision Tree
    │
    ├─> n8n workflow operation?
    │   └─> Go to: n8n Workflow Pattern (Section B)
    │
    ├─> Database operation?
    │   └─> Go to: Database Operation Pattern (Section C)
    │
    ├─> Code generation/refactoring?
    │   └─> Go to: Code Development Pattern (Section D)
    │
    ├─> Analysis/research?
    │   └─> Go to: Analysis Pattern (Section E)
    │
    └─> Unsure?
        └─> STOP → Read relevant rules → Ask user
```

---

## B. n8n Workflow Pattern

### Pre-Action Verification (MANDATORY)

**Before ANY n8n workflow operation:**

```markdown
## 🛡️ PRE-ACTION VERIFICATION

**Action**: [Describe what I'm about to do]

**Checklist**:
- [ ] Read HARD_RULES.md
- [ ] Read SUPABASE_AUTH_CORRECT_METHOD.md (if Supabase involved)
- [ ] Searched existing workflows for patterns
- [ ] Verified credentials from Configuration/.env
- [ ] Checked schema compliance (Data_Management/supabase-schema.sql)
- [ ] Intent confirmed with user (analysis vs execution)

**Ready to Proceed**: [YES/NO]
**If NO**: [What needs to be done first]
```

### Execution Sequence

```
1. RUN: Pre-Action Verification (above)
2. CHECK: Data_Management/supabase-schema.sql (schema compliance)
3. READ: Existing working workflows (pattern matching)
4. VALIDATE: Environment variables (Configuration/.env)
5. EXECUTE: Workflow operation
6. VERIFY: Results match expectations
7. POST: Success verification (Section F)
```

---

## C. Database Operation Pattern

### Pre-Action Verification (MANDATORY)

**Before ANY database operation:**

```markdown
## 🛡️ PRE-ACTION VERIFICATION

**Action**: [Describe database operation]

**Checklist**:
- [ ] Read Data_Management/supabase-schema.sql
- [ ] Listed available columns for target table
- [ ] Verified every field exists in schema
- [ ] Confirmed NO schema modifications needed
- [ ] Identified JSONB fields for extra data if needed

**Schema Compliance**: [YES/NO]
**If NO**: [Use JSONB fields or remove feature]
```

### Execution Sequence

```
1. RUN: Pre-Action Verification (above)
2. READ: Data_Management/supabase-schema.sql
3. LIST: Available columns for target table
4. VERIFY: Every field exists in schema
5. NEVER: Suggest adding columns
6. USE: JSONB fields for extra data if needed
7. EXECUTE: Database operation
```

---

## D. Code Development Pattern

### Pre-Action Verification (MANDATORY)

**Before ANY code creation:**

```markdown
## 🛡️ PRE-ACTION VERIFICATION

**Action**: [Describe code to be created]

**Checklist**:
- [ ] Searched existing codebase for similar solutions
- [ ] Checked scripts/ directory
- [ ] Checked .cursor/commands/ directory
- [ ] Reviewed production-speed-pack.md for templates
- [ ] Confirmed no duplication

**Existing Solution Found**: [YES/NO]
**If YES**: [Adapt existing solution]
**If NO**: [Proceed with creation]
```

### Execution Sequence

```
1. RUN: Pre-Action Verification (above)
2. SEARCH: Existing solutions first (MANDATORY)
   - ls scripts/ | grep -i <keyword>
   - grep -r "<pattern>" scripts/ .cursor/commands/
   - find . -name "*.py" | grep <keyword>
3. IF FOUND: Adapt existing solution
4. IF NOT FOUND: Use template from production-speed-pack.md
5. EXECUTE: Code creation
6. VERIFY: Production standards met (Section F)
```

---

## E. Analysis Pattern

### Pre-Action Verification (MANDATORY)

**Before ANY analysis task:**

```markdown
## 🛡️ PRE-ACTION VERIFICATION

**Action**: [Describe analysis task]

**Checklist**:
- [ ] Identified complexity level (Simple/Moderate/Complex/Highly Complex)
- [ ] Determined if L9 reasoning required (Moderate+)
- [ ] Gathered necessary context
- [ ] Confirmed data sources available

**Complexity**: [Simple/Moderate/Complex/Highly Complex]
**L9 Reasoning Required**: [YES for Moderate+, NO for Simple]
```

### Execution Sequence

```
1. RUN: Pre-Action Verification (above)
2. IF Moderate+ complexity: Apply L9 reasoning framework
3. GATHER: Necessary context and data
4. EXECUTE: Analysis
5. DELIVER: Results with confidence scores
```

---

## F. Success Verification Protocol

### After ANY successful operation, post:

```markdown
## ✅ SUCCESS VERIFICATION

**Operation**: [What was completed]

**Evidence**: 
[Command output, file created, test results, etc.]

**Standards Met**:
- [ ] Production-ready (no placeholders)
- [ ] Error handling included
- [ ] Documentation complete
- [ ] Tests passing (if applicable)
- [ ] Schema compliant (if database operation)
- [ ] Pattern followed (if workflow operation)

**Ready for Next Step**: [YES/NO]
```

---

## G. Failure Stop Protocol

### When ANY operation fails:

```markdown
## 🚨 FAILURE ANALYSIS

**What failed**: [Specific error]

**Why it failed**: [Root cause]

**Have I tried this before**: [YES/NO]

**Correct approach**: [What should I do instead]

**Next action**: [Wait for user guidance]
```

**Then:**
1. **STOP immediately**
2. **DO NOT repeat the same approach**
3. **WAIT for user input**
4. **Apply correct solution from learning files**

---

## H. Anti-Patterns (Never Do This)

### ❌ Skipping Pre-Action Verification

```
WRONG: 
  User: "Update this workflow"
  AI: *immediately starts editing*

RIGHT:
  User: "Update this workflow" 
  AI: *runs Pre-Action Verification first*
  AI: *checks schema*
  AI: *validates*
  AI: *then edits*
```

### ❌ Assuming Credentials

```
WRONG:
  AI: "I'll use the n8n API key you provided earlier..."
  
RIGHT:
  AI: *reads Configuration/.env*
  AI: "Using N8N_API_KEY from .env: eyJ..."
```

### ❌ Guessing Schema

```
WRONG:
  AI: "I'll add a compile_after_ts column..."
  
RIGHT:
  AI: *reads supabase-schema.sql*
  AI: "Schema is locked, using original_message JSONB field instead"
```

### ❌ Creating Without Searching

```
WRONG:
  AI: "I'll create a new import script..."
  
RIGHT:
  AI: *searches scripts/ directory*
  AI: "Found existing import_workflows.py, adapting it..."
```

---

## I. Prevention Rules (NEVER VIOLATE)

### RULE 1: Mandatory Search Before Creating

**BEFORE creating ANY new solution:**
```bash
# Search for existing solutions
find . -name "*.py" -o -name "*.sh" -o -name "*.json" | grep -i "keyword"
ls scripts/
grep -r "keyword" scripts/ .cursor/commands/
```

**NEVER create new solutions if existing ones exist**

---

### RULE 2: Intent Verification Before Execution

**BEFORE running ANY command that affects the system:**

**MANDATORY QUESTION:**
> "I found [X] existing scripts. Should I:
> A) Analyze and create a strategy (analysis mode)
> B) Execute the fixes (deployment mode)
> C) Something else?"

**NEVER assume intent. ALWAYS confirm.**

---

### RULE 3: Credential Verification Before API Calls

**BEFORE any API operation:**
```bash
# MANDATORY: Read actual credentials
cat Configuration/.env | grep -E "N8N_|SUPABASE_|API"
```

**NEVER use hardcoded credentials. NEVER guess.**

---

### RULE 4: Production Standards Enforcement

**BEFORE claiming any code is "ready":**

**MANDATORY CHECKLIST:**
- [ ] Has error handling?
- [ ] Has type hints (Python) or types (TypeScript)?
- [ ] Has docstrings/documentation?
- [ ] Has logging?
- [ ] Has validation logic?
- [ ] No placeholders or TODOs?
- [ ] No console.log or print statements?

**NEVER claim incomplete code is production-ready**

---

### RULE 5: Failure Analysis Before Repetition

**WHEN something fails:**

**MANDATORY ANALYSIS:**
1. What exactly failed?
2. Why did it fail?
3. What's the correct approach?
4. Have I tried this before?

**NEVER repeat the same fix twice**

---

### RULE 6: Pattern Compliance Enforcement

**BEFORE any operation:**

**MANDATORY PATTERN CHECK:**
- [ ] Read existing working examples first
- [ ] Follow the same structure
- [ ] Use same authentication method
- [ ] Use same error handling
- [ ] Use same validation approach

**NEVER reinvent patterns that already work**

---

## J. Quick Reference

### Session Start Checklist
1. ✅ Load .cursorrules
2. ✅ Load ALL files in .cursor-commands/learning/ (recursive)
3. ✅ Check .suite6-config.json
4. ✅ Load Reasoning Mode profiles (n8n, docs, technical operations)
5. ✅ Load YNP Mode command
6. ✅ Load Dev Mode command
7. ✅ Load Orchestrator profile
8. ✅ Post initialization confirmation with mode status

### Before Any Action
1. ✅ Run pre-action verification
2. ✅ Search existing solutions
3. ✅ Confirm intent with user
4. ✅ Verify credentials from .env
5. ✅ Check schema compliance
6. ✅ Follow existing patterns

### After Any Action
1. ✅ Post success verification
2. ✅ Provide evidence
3. ✅ Confirm standards met
4. ✅ Ready for next step

### When Action Fails
1. ✅ STOP immediately
2. ✅ Post failure analysis
3. ✅ Identify root cause
4. ✅ Wait for user guidance
5. ✅ DO NOT repeat same approach

---

## K. Decision Matrix

| Situation | Read First | Then Do |
|-----------|-----------|---------|
| **Any task** | `.cursorrules` → `repeated-mistakes.md` | Execute |
| **Workflow edit** | `HARD_RULES.md` → `schema.sql` | Validate → Edit |
| **Import workflow** | Validate scripts | Import |
| **Database op** | `schema.sql` | Verify fields → Execute |
| **Credentials** | `Configuration/.env` | Use values found |
| **Supabase** | `SUPABASE_AUTH_CORRECT_METHOD.md` | Use credential type |
| **Code creation** | Search scripts/ | Adapt or create |
| **Unsure** | Relevant rules | Ask user |

---

**Last Updated**: 2025-11-07  
**Source**: AI_ACCESS_PATTERN.md + MISTAKE_PREVENTION_SYSTEM.md  
**Confidence**: 0.95

