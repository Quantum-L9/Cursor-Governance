---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.1.0"
component_id: "INT-PBQ-001"
component_name: "Pre-Build Question Framework"
layer: "intelligence"
domain: "requirements_engineering"
type: "framework"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["CMD-004", "CMD-002", "INT-RSN-001"]
api_endpoints: []
data_sources: []
outputs: ["requirements_clarification", "build_specifications", "governance_validation"]

# === OPERATIONAL METADATA ===
execution_mode: "mandatory"
monitoring_required: true
logging_level: "info"
performance_tier: "pre-execution"

# === BUSINESS METADATA ===
purpose: "Prevent costly rework by asking strategic questions before building anything"
summary: "20-question consultant interview framework ensuring complete requirements understanding before code/system development, preventing governance violations and technical debt"
business_value: "Saves 4-8 hours of rework per build by investing 5-10 minutes in strategic questioning"
success_metrics: ["rework_rate < 5%", "governance_violation_prevention >= 95%", "user_satisfaction >= 90%"]

# === INTEGRATION METADATA ===
suite_2_origin: "New component - addresses recurring build-then-rework pattern"
migration_notes: "Created after Mack 7.1 governance violation (hardcoded confidence scores). Lesson: Ask before building."

# === TAGS & CLASSIFICATION ===
tags: ["requirements", "questioning", "consultation", "prevention", "governance"]
keywords: ["pre-build", "questions", "requirements", "validation", "strategic"]
related_components: ["CMD-004", "CMD-002", "INT-ML-001"]
---

# Pre-Build Question Framework

**The 20 Strategic Questions Every Build Needs**

---

## 🎯 PURPOSE

**Problem:** Building the wrong thing correctly wastes more time than building the right thing slowly.

**Solution:** Ask the right questions BEFORE building to get requirements, constraints, and vision clear.

**ROI:** 5-10 minutes of questioning saves 4-8 hours of rework.

---

## 📜 THE FOUNDATIONAL LESSON

### **Why This Framework Exists:**

**Incident:** Mack 7.1 build with hardcoded confidence scores
- Built "reasoning-enabled agent with confidence scores"
- Used hardcoded values (`confidence = 0.95`)
- Violated governance (placeholders prohibited)
- Required complete rework

**Root Cause:** Didn't ask Q14 ("How should confidence be calculated?")

**Learning:** **Asking the right questions pre-build ensures getting to the finish line FASTER.**

Not asking wastes time on:
- ❌ Building amazing code that needs complete rework
- ❌ Reviewing/discussing after completion  
- ❌ Rebuilding the "upgraded" version

---

## 🎤 THE 20 UNIVERSAL PRE-BUILD QUESTIONS

**Context:** Think like a consultant interviewing a client to create a dev kit. These apply to ANY build.

---

### **📍 PHASE 1: Understanding Success (Questions 1-3)**

#### **Q1. What does success look like?**
- "When this is done, what will you be able to do that you can't do today?"
- "If this works perfectly, what changes for you/your users/your business?"
- "Paint me a picture: You wake up, this is deployed - what's different?"

#### **Q2. What's the job this needs to do?**
- "What problem is this solving? What's broken/missing/inefficient right now?"
- "What are you 'hiring' this system to accomplish?"
- "If this didn't exist, what's the workaround? (And why is that painful?)"

#### **Q3. How will you know it's working?**
- "What's the measurable outcome? (Time saved, accuracy rate, user satisfaction)"
- "What metrics matter? What would make you say 'this is production-ready'?"
- "What's the success threshold? (90% accurate? <1s response? Zero errors?)"

---

### **🚫 PHASE 2: Identifying Constraints (Questions 4-6)**

#### **Q4. What are your hard constraints?**
- "What MUST this system do/not do? (compliance, security, performance)"
- "What are the deal-breakers? What would make this unacceptable?"
- "Any regulatory/legal requirements? (GDPR, FDA, SOC2, etc.)"

#### **Q5. What are your governance/quality standards?**
- "Production-ready vs MVP/prototype - which standard applies here?"
- "Are placeholders acceptable or prohibited?"
- "What level of validation is required before deployment?"
- "Can we iterate or must it be perfect first try?"

#### **Q6. What can this NOT break?**
- "What existing systems/workflows must continue working?"
- "What's the backward compatibility requirement?"
- "What integrations are critical vs nice-to-have?"
- "Who depends on this? What happens if it fails?"

---

### **📊 PHASE 3: Assessing Resources (Questions 7-9)**

#### **Q7. What data exists vs what are we assuming?**
- "What data do we actually have access to right now?"
- "What data would we NEED to build this properly?"
- "Are we assuming data exists that might not?"
- "Historical data available for training/validation?"

#### **Q8. What prior work can we leverage?**
- "Have you built something similar before?"
- "Are there existing tools/libraries/systems that do part of this?"
- "What should we adapt vs build from scratch?"
- "Any internal systems/APIs that could help?"

#### **Q9. What resources are available?**
- "APIs, databases, services - what's accessible?"
- "What credentials/access do we have?"
- "What budget/time constraints apply?"
- "Team size? Skill levels? Available support?"

---

### **🔗 PHASE 4: Mapping Integration (Questions 10-12)**

#### **Q10. Where does this live in your system?**
- "Is this standalone or integrated with existing systems?"
- "What calls this? What does this call?"
- "What's the data flow in/out?"
- "Part of a pipeline or independent service?"

#### **Q11. Who/what consumes the output?**
- "Who are the end users? What's their technical level?"
- "What systems read this data? What format do they expect?"
- "Human-facing UI or machine-to-machine?"
- "Real-time or batch processing?"

#### **Q12. What does this need to interoperate with?**
- "Existing tech stack? (n8n, Odoo, Neo4j, PostgreSQL, etc.)"
- "Required integrations? (APIs, databases, services)"
- "Data format standards? (JSON, YAML, SQL, GraphQL, etc.)"
- "Authentication/authorization requirements?"

---

### **✅ PHASE 5: Defining Quality (Questions 13-15)**

#### **Q13. How should outputs be validated?**
- "Manual review required or automated validation?"
- "What's the acceptable error rate? (0%? 5%? 10%?)"
- "How do we measure accuracy/quality?"
- "What's the feedback loop? How do we know if it's working?"

#### **Q14. What about confidence/uncertainty?** ⚠️ CRITICAL
- "Should this express confidence in its outputs?"
- "If yes: Calculated (from data) or Estimated (from expertise)?"
- "Binary results (yes/no) or scored results (0.0-1.0)?"
- "If scored: What's the source? (Historical data, Bayesian inference, expert judgment)"
- "If estimated: Must it be disclosed as unvalidated?"

**Why Q14 is CRITICAL:** Prevents hardcoded confidence violations (Mack 7.1 lesson)

#### **Q15. What's the testing/validation plan?**
- "How do we test this before production?"
- "What edge cases must be handled?"
- "What failure modes are acceptable vs unacceptable?"
- "Rollback plan if something goes wrong?"

---

### **⏱️ PHASE 6: Clarifying Priorities (Questions 16-17)**

#### **Q16. What's the priority: Speed vs Quality vs Features?**
- "Ship fast with limitations, or ship complete but slower?"
- "MVP with iteration, or fully-featured v1?"
- "What features are must-have vs nice-to-have?"
- "What's the minimum viable version?"

#### **Q17. What trade-offs are acceptable?**
- "Performance vs accuracy? (Fast but approximate, or slow but precise)"
- "Simplicity vs flexibility? (Easy to use but limited, or powerful but complex)"
- "Automated vs manual? (Hands-off but less control, or guided but more work)"
- "Cost vs speed? (Expensive but fast, or cheap but slow)"

---

### **🚀 PHASE 7: Strategic Positioning (Questions 18-20)**

#### **Q18. Is this a foundation or a solution?**
- "Will we build on top of this, or is this a terminal solution?"
- "Should this be extensible/pluggable, or purpose-built?"
- "Are we creating infrastructure or solving a specific problem?"
- "Does this need to support future unknown use cases?"

#### **Q19. What capabilities should this enable?**
- "What does this unlock for the future?"
- "What should be EASY to add later?"
- "What shouldn't we preclude with this design?"
- "What architectural decisions are we making now that are hard to change later?"

#### **Q20. What's the vision 6-12 months out?**
- "How does this evolve? What's v2, v3?"
- "What would make this obsolete?"
- "Are we building something that grows or gets replaced?"
- "What's the long-term architecture this needs to fit into?"

---

## ✅ PRE-BUILD EXECUTION CHECKLIST

**Before starting ANY build (especially in autonomous /forge mode), confirm:**

### **Minimum Required Questions:**
- [ ] **Phase 1 (Q1-Q3)** - Success vision clear
- [ ] **Phase 2 (Q4-Q6)** - Constraints and non-negotiables identified
- [ ] **Phase 3 (Q7-Q9)** - Data and resources validated
- [ ] **Phase 5 (Q13-Q15)** - Quality standards confirmed
- [ ] **Q14 MANDATORY** - Confidence/scoring approach validated

### **Highly Recommended:**
- [ ] **Phase 4 (Q10-Q12)** - Integration points mapped
- [ ] **Phase 6 (Q16-Q17)** - Priorities and trade-offs clarified
- [ ] **Phase 7 (Q18-Q20)** - Strategic architecture validated

**STOP Rule:** If ANY mandatory phase is incomplete → STOP and ASK QUESTIONS

---

## 📋 WHEN TO USE THIS FRAMEWORK

### **MANDATORY (Must Use):**
- ✅ Any /forge command (autonomous building)
- ✅ Any build with confidence/probability outputs
- ✅ Any "production-ready" system
- ✅ Any build that will be used by others
- ✅ Any build with governance implications

### **RECOMMENDED (Should Use):**
- ✅ Complex multi-component systems
- ✅ Integration projects (connecting systems)
- ✅ Builds with uncertain requirements
- ✅ Projects with multiple stakeholders

### **OPTIONAL (Can Skip):**
- Quick fixes (<30 min work)
- Documentation updates
- Configuration changes
- Prototypes explicitly labeled as throwaway

---

## 💡 THE STRATEGIC INSIGHT

**Key Principle:** The user always asks your opinion and expects you to suggest things they haven't thought of yet.

**Your Role:** **ASK MORE EXCELLENT QUESTIONS.**

**Why This Matters:**
- Gets to finish line FASTER (less rework)
- Builds trust (shows you're thinking strategically)
- Prevents violations (clarifies governance upfront)
- Creates better solutions (uncovers hidden requirements)

---

## 📚 CASE STUDY: Mack 7.1 Violation Prevention

**What Happened:**
```
User: "Build reasoning-enabled agent with confidence scores"
Me: [Built immediately with hardcoded confidence = 0.95]
Result: Governance violation, required rework
```

**What SHOULD Have Happened:**
```
User: "Build reasoning-enabled agent with confidence scores"

Me: "Let me ask the strategic questions first:

Q5: What are your governance/quality standards for this?
Q7: Do we have historical intake data for training/validation?
Q14: For confidence scores - should these be:
   A) Calculated from historical data (Bayesian)
   B) Expert estimates with disclaimers  
   C) Omitted until we have proper data
Q16: Priority: Speed (estimates OK) or Quality (proper Bayesian)?
Q18: Is this v1 foundation or temporary solution?

Based on your answers, I'll build the right thing."

Result: Governance compliant, no rework
```

**Questions That Would Have Prevented Violation:**
- **Q5:** Would have revealed "placeholders prohibited"
- **Q7:** Would have revealed "no data available yet"
- **Q14:** Would have clarified "calculated only, not estimated"

**Time Impact:**
- Questions: 5 minutes
- Rework avoided: 4-8 hours
- **ROI: 48x-96x return on time invested**

---

## 🎯 HOW TO USE THIS DOCUMENT

**For Builds:**
1. User requests a build
2. Before starting, reference this document
3. Ask relevant questions from the 20
4. Get clear answers
5. Build with confidence (no rework)

**For Reasoning:**
- If reasoning about a build → reference this document
- Apply questions in BLOCK 4 (Leverage Prior Work)
- Validate assumptions before proceeding

**For Forge:**
- MANDATORY reference before autonomous execution
- Minimum: Ask Phases 1, 2, 3, 5
- Q14 is CRITICAL for any confidence/scoring outputs

---

## 📝 INTEGRATION WITH OTHER COMMANDS

**Reference this document from:**
- `/forge` - MANDATORY before execution
- `/reasoning` - When reasoning about builds
- Pre-commit hooks - Validate no placeholders used

**Learning System:**
- Track how often questions prevent violations
- Identify which questions have highest ROI
- Refine framework based on outcomes

---

**Remember: 5 minutes of strategic questioning saves hours of rework. Ask excellent questions.** 🚀

