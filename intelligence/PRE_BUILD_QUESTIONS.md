---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-PBQ-001"
component_name: "Pre-Build Question Framework"
layer: "intelligence"
domain: "requirements_gathering"
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
integrates_with: ["CMD-004", "CMD-002", "INT-ORC-001"]
api_endpoints: []
data_sources: []
outputs: ["requirements_clarification", "build_validation", "rework_prevention"]

# === OPERATIONAL METADATA ===
execution_mode: "mandatory"
monitoring_required: true
logging_level: "info"
performance_tier: "pre-execution"

# === BUSINESS METADATA ===
purpose: "Prevent costly rework by asking the right strategic questions before starting any build"
summary: "Universal consultant-style question framework ensuring complete requirements understanding before autonomous execution"
business_value: "Saves 4-8 hours of rework per build by clarifying requirements upfront in 5-10 minutes"
success_metrics: ["rework_reduction >= 80%", "question_relevance >= 0.90", "requirement_clarity >= 0.95"]

# === INTEGRATION METADATA ===
suite_2_origin: "New component created from Mack 7.1 governance violation lesson"
migration_notes: "Created to capture strategic learning about importance of pre-build questioning"

# === TAGS & CLASSIFICATION ===
tags: ["requirements", "questioning", "consulting", "pre-build", "validation", "rework-prevention"]
keywords: ["questions", "requirements", "pre-build", "consulting", "validation"]
related_components: ["CMD-004", "CMD-002", "INT-ORC-001"]
startup_required: false
mode_type: "framework"
---

# The 20 Universal Pre-Build Questions

**Consultant Interview Framework for Software Builds**

---

## 🎯 Purpose

**Problem:** Building the wrong thing correctly wastes 4-8 hours on rework.  
**Solution:** Ask the right questions upfront (5-10 minutes) to get to "yes" faster.

**Core Insight:** Communication saves time in the long run. Users appreciate thoughtful questions that show you're thinking strategically about their needs.

---

## 🚨 When to Use This

**MANDATORY for:**
- ✅ Any /forge autonomous builds
- ✅ Any build with confidence/probability/uncertainty
- ✅ Any "reasoning-enabled" or "intelligent" system
- ✅ Any new architecture or foundational component

**RECOMMENDED for:**
- ✅ Complex integrations
- ✅ Production-ready systems
- ✅ Anything involving user-facing metrics/scores

---

## 📋 THE 20 QUESTIONS (Organized by Phase)

### **📍 PHASE 1: Understanding Success (Questions 1-3)**

**Q1. What does success look like?**
- "When this is done, what will you be able to do that you can't do today?"
- "If this works perfectly, what changes for you/your users/your business?"
- **Reveals:** The actual outcome that matters (not just features)

**Q2. What's the job this needs to do?**
- "What problem is this solving? What's broken/missing/inefficient right now?"
- "What are you 'hiring' this system to accomplish?"
- **Reveals:** The core problem (might be different from stated request)

**Q3. How will you know it's working?**
- "What's the measurable outcome? (Time saved, accuracy rate, user satisfaction)"
- "What metrics matter? What would make you say 'this is production-ready'?"
- **Reveals:** Definition of "done" and quality bar

---

### **🚫 PHASE 2: Identifying Constraints (Questions 4-6)**

**Q4. What are your hard constraints?**
- "What MUST this system do/not do? (compliance, security, performance)"
- "What are the deal-breakers? What would make this unacceptable?"
- **Reveals:** Non-negotiable requirements that will cause rejection if missed

**Q5. What are your governance/quality standards?**
- "Production-ready vs MVP/prototype - which standard applies here?"
- "Are placeholders acceptable or prohibited?"
- "What level of validation is required before deployment?"
- **Reveals:** Quality bar (prevents building to wrong standard)

**Q6. What can this NOT break?**
- "What existing systems/workflows must continue working?"
- "What's the backward compatibility requirement?"
- "What integrations are critical vs nice-to-have?"
- **Reveals:** Invisible dependencies that could cause breakage

---

### **📊 PHASE 3: Assessing Resources (Questions 7-9)**

**Q7. What data exists vs what are we assuming?**
- "What data do we actually have access to right now?"
- "What data would we NEED to build this properly?"
- "Are we assuming data exists that might not?"
- **Reveals:** Data availability gaps (prevents building on assumptions)

**Q8. What prior work can we leverage?**
- "Have you built something similar before?"
- "Are there existing tools/libraries/systems that do part of this?"
- "What should we adapt vs build from scratch?"
- **Reveals:** Opportunities to reuse vs reinvent

**Q9. What resources are available?**
- "APIs, databases, services - what's accessible?"
- "What credentials/access do we have?"
- "What budget/time constraints apply?"
- **Reveals:** Resource constraints (API limits, access issues, time pressure)

---

### **🔗 PHASE 4: Mapping Integration (Questions 10-12)**

**Q10. Where does this live in your system?**
- "Is this standalone or integrated with existing systems?"
- "What calls this? What does this call?"
- "What's the data flow in/out?"
- **Reveals:** Architecture context (where this fits)

**Q11. Who/what consumes the output?**
- "Who are the end users? What's their technical level?"
- "What systems read this data? What format do they expect?"
- "Human-facing UI or machine-to-machine?"
- **Reveals:** Output format requirements and UX expectations

**Q12. What does this need to interoperate with?**
- "Existing tech stack? (n8n, Odoo, Neo4j, etc.)"
- "Required integrations? (APIs, databases, services)"
- "Data format standards? (JSON, YAML, SQL, etc.)"
- **Reveals:** Technical compatibility requirements

---

### **✅ PHASE 5: Defining Quality (Questions 13-15)**

**Q13. How should outputs be validated?**
- "Manual review required or automated validation?"
- "What's the acceptable error rate? (0%? 5%? 10%?)"
- "How do we measure accuracy/quality?"
- **Reveals:** Quality thresholds and validation approach

**Q14. What about confidence/uncertainty?** 🚨 **CRITICAL**
- "Should this express confidence in its outputs?"
- "If yes: Calculated (from data) or Estimated (from expertise)?"
- "Binary results (yes/no) or scored results (0.0-1.0)?"
- "If scored: What's the source of the scores? (Historical data, Bayesian inference, expert judgment)"
- **Reveals:** How to handle uncertainty (prevents placeholder violations)

**Q15. What's the testing/validation plan?**
- "How do we test this before production?"
- "What edge cases must be handled?"
- "What failure modes are acceptable vs unacceptable?"
- **Reveals:** Testing strategy and risk tolerance

---

### **⏱️ PHASE 6: Clarifying Priorities (Questions 16-17)**

**Q16. What's the priority: Speed vs Quality vs Features?**
- "Ship fast with limitations, or ship complete but slower?"
- "MVP with iteration, or fully-featured v1?"
- "What features are must-have vs nice-to-have?"
- **Reveals:** Trade-off preferences (guides design decisions)

**Q17. What trade-offs are acceptable?**
- "Performance vs accuracy?"
- "Simplicity vs flexibility?"
- "Automated vs manual?"
- "Cost vs speed?"
- **Reveals:** Which dimension matters most when conflicts arise

---

### **🚀 PHASE 7: Strategic Positioning (Questions 18-20)**

**Q18. Is this a foundation or a solution?**
- "Will we build on top of this, or is this a terminal solution?"
- "Should this be extensible/pluggable, or purpose-built?"
- "Are we creating infrastructure or solving a specific problem?"
- **Reveals:** Architectural intent (affects design philosophy)

**Q19. What capabilities should this enable?**
- "What does this unlock for the future?"
- "What should be EASY to add later?"
- "What shouldn't we preclude with this design?"
- **Reveals:** Future requirements (ensures we don't paint ourselves into corner)

**Q20. What's the vision 6-12 months out?**
- "How does this evolve? What's v2, v3?"
- "What would make this obsolete?"
- "Are we building something that grows or gets replaced?"
- **Reveals:** Long-term plan (temporary solution vs permanent infrastructure)

---

## 🎯 Minimum Required Questions (Fast Track)

**For time-sensitive builds, MINIMUM ask these 7:**

1. **Q3** - How will you know it's working? (Success metrics)
2. **Q5** - Production-ready or MVP? (Quality standard)
3. **Q7** - What data exists? (Resource validation)
4. **Q14** - How to handle confidence/uncertainty? (Critical for reasoning builds)
5. **Q16** - Speed vs Quality priority? (Trade-off direction)
6. **Q18** - Foundation or solution? (Architecture intent)
7. **Q20** - Vision 6-12 months out? (Future-proofing)

**Time investment:** 5 minutes  
**Rework prevented:** 4-8 hours  
**ROI:** ~50x

---

## 📖 Case Study: Mack 7.1 Governance Violation

### **What Happened:**
User requested "reasoning-enabled agent with confidence scores."

I immediately built with hardcoded values:
```python
'confidence': 0.95  # Placeholder - not calculated
```

**Governance Violation:** Placeholders prohibited in production code.

### **What Questions Would Have Prevented This:**

**Q5 (Standards):** "Are placeholders acceptable?"  
→ Would have revealed governance prohibits them

**Q7 (Data):** "Do we have historical intake data?"  
→ Would have revealed no training data available

**Q14 (Confidence):** "Should confidence be calculated or estimated?"  
→ Would have clarified: calculated from data OR omit entirely

**Q18 (Foundation):** "Is this v1 to be replaced or long-term architecture?"  
→ Would have established whether to wait for proper Bayesian

### **Result If Questions Asked:**
- ✅ Built without confidence scores (governance compliant)
- ✅ Clear upgrade path to v7.2 with Bayesian (when data available)
- ✅ No rework needed
- ✅ Trust maintained

**Time Saved:** 4-8 hours of rebuilding

---

## 💡 Key Principle

**"5 Minutes of Questions Saves 5 Hours of Rework"**

Quality questions are everything. The user always asks your opinion and expects you to suggest things they haven't thought of yet.

**COMMUNICATION SAVES TIME** - Ask excellent questions upfront, build it right the first time.

---

## 🔗 References

**Primary Use:** See `@.cursor-commands/commands/forge.md` (full integration)  
**When to Check:** Before any build, especially autonomous /forge executions  
**Related:** `@.cursor-commands/commands/reasoning.md` (light reference for reasoning about builds)

