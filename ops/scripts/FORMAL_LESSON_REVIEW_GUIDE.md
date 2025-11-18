---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "DOC-FLR-001"
component_name: "Formal Lesson Review Guide"
layer: "documentation"
domain: "learning"
type: "guide"
status: "active"
created: "2025-11-17T22:06:00Z"
updated: "2025-11-17T22:06:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "medium"
compliance_required: false
audit_trail: false
security_classification: "internal"

# === BUSINESS METADATA ===
purpose: "Guide for reviewing and refining formal lesson candidates"
summary: "Step-by-step process for converting raw patterns into actionable formal lessons"
business_value: "Ensures high-quality, actionable prevention rules"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "review", "formal_lessons", "documentation"]
keywords: ["formal", "lessons", "review", "refinement", "prevention"]
---

# Formal Lesson Review Guide

**Purpose:** Convert auto-detected patterns into actionable formal lessons

---

## 📊 Two-Level Learning System

### Level 1: Auto-Detection (Automated)
- ✅ Runs hourly via LaunchAgent
- ✅ Captures raw patterns
- ✅ Updates tracking tables
- **Output:** `memory_index.json`

### Level 2: Formal Lesson Creation (Manual Review Required)
- ⏰ Run weekly or when candidates accumulate
- 🔍 Requires human analysis
- ✍️ Creates detailed prevention rules
- **Output:** New entries in `repeated-mistakes.md`

---

## 🔄 Weekly Review Workflow

### Step 1: Run Formal Lesson Extractor

```bash
cd "/Users/ib-mac/Dropbox/Cursor Governance/GlobalCommands"
python3 ops/scripts/formal_lesson_extractor.py
```

**Output:** `learning/failures/formal_lessons_pending.json`

---

### Step 2: Review Candidates

Open the candidates file:

```bash
cat learning/failures/formal_lessons_pending.json
```

**Look for:**
- Pattern count (higher = more important)
- Severity (HIGH/MEDIUM/LOW)
- Category (what type of issue)
- Date range (how long it's been happening)

---

### Step 3: Refine Lesson Template

For each candidate, replace `[REVIEW REQUIRED]` sections:

**Example Candidate:**
```json
{
  "id": "FL_20251118_user_correction",
  "category": "User Correction",
  "pattern_count": 8,
  "severity": "HIGH",
  "lesson_template": {
    "title": "User Correction Pattern (8 occurrences)",
    "mistake": "[REVIEW REQUIRED] Multiple user correction issues detected",
    "impact": "Occurred 8 times between 2025-11-09 and 2025-11-15",
    "prevention": "[REVIEW REQUIRED] Analyze patterns and define prevention protocol",
    "rule": "[REVIEW REQUIRED] Create enforcement rule"
  }
}
```

**After Review (Example):**
```markdown
### **11. Not Verifying Schema Before Database Operations**
**Mistake:** Attempted to update database fields without first reading schema
**Impact:** Multiple failures, user corrections required, wasted time
**Prevention:** ALWAYS read schema file before ANY database operation
**Rule:** Pre-execution checklist: Read `supabase-schema.sql` before database tasks
**Date Added:** 2025-11-18
```

---

### Step 4: Add to repeated-mistakes.md

1. Open `learning/failures/repeated-mistakes.md`
2. Find the `## 🚨 **CRITICAL FAILURES TO NEVER REPEAT**` section
3. Add new lesson with next sequential number
4. Update the tracking table at bottom
5. Update `**Last Updated:**` timestamp

---

### Step 5: Mark as Formalized

Update `memory_index.json` to mark patterns as formalized:

```bash
# Add candidate hashes to "formalized_learnings" array
# This prevents re-processing same patterns
```

**(This step will be automated in future version)**

---

## 📋 Quality Checklist

Before adding a formal lesson, ensure:

- [ ] **Title** is clear and specific
- [ ] **Mistake** describes what went wrong
- [ ] **Impact** quantifies the cost (time, errors, corrections)
- [ ] **Prevention** provides actionable protocol
- [ ] **Rule** is enforceable and checkable
- [ ] **Date Added** is current
- [ ] Tracking table updated
- [ ] Timestamp updated

---

## 🎯 Prioritization Criteria

**HIGH Priority (Add immediately):**
- Pattern count >= 5
- Causes > 1 hour rework
- Violates governance rules
- Affects data integrity

**MEDIUM Priority (Add in batch):**
- Pattern count 3-4
- Causes 15-60 min rework
- Workflow inefficiency

**LOW Priority (Monitor):**
- Pattern count < 3
- Minor inconvenience
- Already has workaround

---

## 📅 Recommended Schedule

**Weekly Review:**
- Run `formal_lesson_extractor.py`
- Review HIGH severity candidates
- Add 1-3 formal lessons
- Update tracking

**Monthly Audit:**
- Review all candidates
- Clean up old patterns
- Archive formalized learnings
- Update prevention protocols

---

## 🔍 Pattern Analysis Tips

**When reviewing raw patterns, ask:**

1. **Is this actually a mistake?**
   - Or just normal iteration?
   - Does it require prevention?

2. **What's the root cause?**
   - Not reading files first?
   - Making assumptions?
   - Missing prerequisite check?

3. **Is this actionable?**
   - Can we create a rule?
   - Can we enforce it?
   - Can AI check for it?

4. **Is this already covered?**
   - Check existing lessons
   - Avoid duplicates
   - Enhance existing if needed

---

## ✅ Success Metrics

**Target Formalization Rate:** 15-25% of auto-detected patterns

**Current Status:**
- Auto-detected: 82 patterns
- Formalized: 2 lessons (2.4% rate)
- **Target:** 12-20 lessons

**Quality Metrics:**
- Lesson clarity: >= 90%
- Prevention effectiveness: >= 80%
- Zero repetition of formalized mistakes

---

## 📝 Example: Good vs. Bad Formal Lessons

### ❌ BAD (Too vague):
```markdown
### **11. Making Mistakes**
**Mistake:** Did something wrong
**Impact:** Bad things happened
**Prevention:** Don't do it again
**Rule:** Be more careful
```

### ✅ GOOD (Specific and actionable):
```markdown
### **11. Not Verifying Schema Before Database Operations**
**Mistake:** Attempted to insert data into `suppliers` table without first checking schema, 
resulting in field name mismatch (`company_name` vs `name`)
**Impact:** 3 failed attempts, 25 minutes debugging, user had to correct manually
**Prevention:** 
1. BEFORE any database operation, run: `grep "CREATE TABLE tablename" supabase-schema.sql`
2. List actual column names from schema
3. Verify all field names match exactly
**Rule:** Pre-execution checklist MANDATORY: Read schema before ANY database task
**Date Added:** 2025-11-18
```

---

## 🚀 Future Automation

**Planned Enhancements:**
1. AI-assisted lesson refinement
2. Automatic schema extraction from patterns
3. Suggested prevention rules based on category
4. Auto-marking of formalized patterns
5. Integration with Bayesian confidence scoring

---

**Last Updated:** 2025-11-17  
**Component:** DOC-FLR-001  
**Status:** Active

