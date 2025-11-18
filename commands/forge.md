---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "CMD-004"
component_name: "Heavy Forge Command"
layer: "intelligence"
domain: "high_velocity"
type: "command"
status: "active"
created: "2025-01-27T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["CMD-001", "CMD-002", "INT-ORC-001"]
api_endpoints: []
data_sources: []
outputs: ["autonomous_executions", "governance_compliant_deliverables"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Activate Heavy Forge mode for autonomous high-velocity execution with NO PAUSES"
summary: "Single command activating Heavy Forge 3-step chain (Scope & Integrity → Draft & Chain → Finalize & Deliver) enabling autonomous execution with automatic governance checks and fixes"
business_value: "Enables maximum velocity autonomous execution with zero pauses, accelerating delivery while maintaining governance compliance"
success_metrics: ["execution_velocity >= 10x", "governance_compliance >= 1.0", "pause_count = 0"]

# === INTEGRATION METADATA ===
suite_2_origin: "forge.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and autonomous execution capabilities"

# === TAGS & CLASSIFICATION ===
tags: ["high-velocity", "forge", "autonomous", "governance", "no-pauses", "command"]
keywords: ["forge", "heavy", "autonomous", "high-velocity", "no-pauses", "governance"]
related_components: ["CMD-001", "CMD-002", "INT-ORC-001"]
startup_required: true
mode_type: "command"
---

name: forge
description: Activate Heavy Forge mode for autonomous high-velocity execution with NO PAUSES

# `/forge` - Heavy Forge Mode (NO PAUSES)

**Activate Ultra High-Velocity Reasoning Mode with Heavy Forge 3-Step Chain**

## ⚡ MAXIMUM VELOCITY = NO PAUSES

**CRITICAL RULE:** Maximum velocity means **ZERO PAUSES FOR MANUAL APPROVALS**. Execute autonomously with no interruptions.

## Execution Mode
**Heavy Forge** - Autonomous execution with **NO PAUSES**, automatic fixes, governance compliance

---

## 🚨 MANDATORY: Pre-Build Strategic Questions

**⚠️ BEFORE AUTONOMOUS EXECUTION:** Must ask strategic questions to prevent building the wrong thing correctly.

**Full Framework:** `@.cursor-commands/intelligence/pre-build-question-framework.md`

### **Minimum Required Questions (Ask User BEFORE Building):**

**PHASE 1: Success (Q1-Q3)**
- Q1: "What does success look like when this is done?"
- Q2: "What job is this system being hired to do?"
- Q3: "How will you measure if it's working?"

**PHASE 2: Constraints (Q4-Q6)**
- Q5: "Production-ready or MVP? Are placeholders acceptable?"
- Q6: "What existing systems can this NOT break?"

**PHASE 3: Resources (Q7-Q9)**
- Q7: "What data exists vs what are we assuming exists?"
- Q8: "What prior work can we leverage vs build from scratch?"

**PHASE 5: Quality (Q13-Q15)**  
- Q14: ⚠️ **CRITICAL** "Should this have confidence scores? If yes, calculated how?"
- Q15: "What's the testing/validation plan?"

**Full question list:** See `pre-build-question-framework.md` for all 20 questions across 7 phases.

### **Pre-Execution Checklist:**

- [ ] Success vision clear (Q1-Q3 answered)
- [ ] Governance standards confirmed (Q5 answered)
- [ ] Data availability validated (Q7 answered)
- [ ] Confidence/scoring approach clarified (Q14 answered if applicable)
- [ ] No placeholders will be used without disclosure

**STOP Rule:** If ANY checkbox unchecked → PAUSE and ASK QUESTIONS (even in NO PAUSES mode, this takes precedence)

---

## 3-Step Chain (Autonomous, No Interruptions)

### Step 1: Scope & Integrity
- Clarify scope and objective
- Confirm constraints from governance profiles
- Identify dependencies and risks
- Set success criteria
- Load all required context (schema, research, learning files)
- **NO PAUSES** - Proceed immediately to Step 2

### Step 2: Draft & Chain
- Produce artifacts (code, docs, configs)
- Chain required sub-prompts automatically
- Generate complete packet (code + docs + schema + tests)
- Execute research, validation, and build in parallel when safe
- **NO PAUSES** - Proceed immediately to Step 3

### Step 3: Finalize & Deliver
- Apply governance checks (security, versioning, headers, env)
- Run recursive self-check protocol
- Fix issues automatically (don't pause for confirmation)
- Self-verify: Plan A vs Plan B, risk scan, confidence note
- Deliver artifact + delivery log + YNP
- **NO PAUSES** - Complete and deliver immediately

## Usage

```
/forge [objective]

Examples:
/forge analyze @UNIFIED_PROMPT_TOOLKIT/
/forge consolidate duplicate files
/forge evaluate project status
```

## Behavior (NO PAUSES POLICY)

- **NO PAUSES:** Execute entire chain without stopping for manual approval
- **Autonomous Execution:** Fix issues silently and proceed - never ask for permission
- **No Confirmation Requests:** Proceed automatically unless human authorization explicitly required by Security/Access rules (only for security-critical operations)
- **No Drifting:** Obey all linked governance files
- **Mandatory Output Shape:** Follow defined response structures exactly
- **Self-Verification:** Apply reasoning checks before delivery
- **Auto-Decision:** When uncertain, choose best path and proceed - document decision in delivery log

## Exceptions (ONLY Security-Critical)

**ONLY pause for:**
- Security violations requiring explicit human authorization
- Critical secrets exposure requiring user confirmation
- Operations that would cause irreversible data loss without explicit confirmation

**NEVER pause for:**
- File moves/renames
- Header updates
- Version bumps
- Naming standardization
- Consolidation actions
- Code generation
- Documentation updates
- Governance fixes

## Precedence Rules (Auto-Resolve Conflicts)

1. **Security & Access** (secrets, auth, least privilege)
2. **Operational Health** (preflight, env sync, checkpoints)
3. **Versioning** (headers, naming, archiving, version map)
4. **Workflow Governance** (n8n validation, deploy, migrate, diff, test)
5. **Reasoning** (modes, self-verification, evidence discipline)

If conflicts arise, resolve automatically using precedence rules above. Document resolution in delivery log.

## Reference
- Source: `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/01_High_Velocity_Prompts/orchestrator.md`
- YNP Framework: `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/01_High_Velocity_Prompts/YNP_Framework_v3.md`

## Delivery Log Format (Required)

Every `/forge` execution MUST include:

```markdown
## 📋 Delivery Log
- **Actions Taken:** [List all actions executed]
- **Auto-Fixes Applied:** [List all automatic fixes]
- **Decisions Made:** [List autonomous decisions with rationale]
- **Checks Passed:** [Governance validations]
- **No Pauses:** ✅ Confirmed - Zero manual approval pauses
- **Completion Time:** [Timestamp]
```

## Completion Gate

Task is complete only after:
1. Security and env checks pass or are repaired (auto-repair, no pause)
2. Headers + versioning are correct (auto-fix, no pause)
3. Workflow governance validations satisfied (auto-validate, no pause)
4. Reasoning self-check recorded (auto-record, no pause)

**Then deliver artifact + log + YNP immediately - NO PAUSES.**

---
**Remember: Maximum velocity = NO PAUSES. Execute autonomously.**

