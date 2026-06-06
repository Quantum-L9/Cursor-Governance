---
name: core-REASONING_MODES_GUIDE
description: 🧠 Reasoning Modes - Quick Selection Guide
disable-model-invocation: true
---

# 🧠 Reasoning Modes - Quick Selection Guide

**Choose the right reasoning mode for your task**

---

## 📊 Quick Decision Matrix

| Task Complexity | Files Affected | Unknowns | Use This Mode | Time |
|-----------------|----------------|----------|---------------|------|
| Simple | 1-3 files | Clear | **@quick-reason** | 3-5min |
| Moderate | 3-8 files | Some | **@think** | 8-10min |
| Complex | 8+ files | Many | **@deep-reason** | 15-30min |

---

## ⚡ @quick-reason (DAILY DRIVER)

**Use for 90% of your tasks:**

### ✅ Perfect For:
- File organization and cleanup
- Simple refactoring (rename, move)
- Documentation updates
- Configuration changes
- Quick bug fixes
- Single-system modifications

### 📊 Characteristics:
- **Time:** 3-5 minutes
- **Blocks:** 5 streamlined
- **Files:** 1-3 files
- **Unknowns:** None or minimal
- **Risk:** Safe

### 💡 Examples:
```bash
@quick-reason "organize these audit reports"
@quick-reason "rename function across 3 files"
@quick-reason "update README with new commands"
@quick-reason "fix typo in config"
@quick-reason "add error logging to webhook"
```

---

## 🧠 @think (BALANCED ANALYSIS)

**Use for moderate complexity work:**

### ✅ Perfect For:
- New feature development
- System integrations (2-3 systems)
- Non-trivial refactoring
- Bug investigation
- Implementation planning
- Multi-file changes with dependencies

### 📊 Characteristics:
- **Time:** 8-10 minutes
- **Blocks:** 8 balanced
- **Files:** 3-8 files
- **Unknowns:** Some, manageable
- **Risk:** Safe to moderate

### 💡 Examples:
```bash
@think "add email notifications for buyer matches"
@think "integrate VanillaSoft with lead qualification"
@think "refactor error handling across material agent"
@think "build buyer matching validation system"
@think "investigate classification failures"
```

---

## 🔬 @deep-reason (ARCHITECTURAL POWER)

**Use sparingly for complex decisions:**

### ✅ Perfect For:
- Major architecture changes
- Entire system rewrites
- Multi-system orchestration
- High-risk production changes
- Unclear requirements needing deep analysis
- Building new agent constellations

### 📊 Characteristics:
- **Time:** 15-30 minutes
- **Blocks:** 13 comprehensive
- **Files:** 8+ files
- **Unknowns:** Many or complex
- **Risk:** Moderate to high

### 💡 Examples:
```bash
@deep-reason "refactor agent constellation for multi-tenancy"
@deep-reason "redesign error handling across all systems"
@deep-reason "implement complete authentication overhaul"
@deep-reason "build new master orchestration agent"
@deep-reason "migrate from monolith to microservices"
```

---

## 🎯 Real-World Decision Flow

### Start Here:
```
1. Look at the task
2. Ask: "Is this obvious and low-risk?"
   YES → @quick-reason
   NO → Continue to 3

3. Ask: "Does this affect multiple systems or have unknowns?"
   NO → @quick-reason
   YES → Continue to 4

4. Ask: "Is this a major architecture change or very high risk?"
   NO → @think
   YES → @deep-reason
```

### Escalation Path:
```
@quick-reason → Realizes complexity → @think
@think → Realizes architecture impact → @deep-reason
```

### De-escalation Path:
```
@think → Problem simpler than expected → Switch to @quick-reason
@deep-reason → Scope reduced → Switch to @think
```

---

## 📈 Usage Statistics (Typical Distribution)

```
Your workflow should look like this:

@quick-reason: ████████████████████ 90% (Daily tasks)
@think:        █████ 9% (Dev work)
@deep-reason:  █ 1% (Architecture)
```

**If you're using @deep-reason more than 1-2x per week, something's wrong!**

---

## 💡 Pro Tips

### Choosing Wisely:
1. **Default to @quick-reason** - You can always escalate
2. **Use @think for features** - Most development work
3. **Save @deep-reason for architecture** - Rare but necessary

### Speed Hacks:
- Start with @quick-reason even if unsure
- Let it tell you to escalate if needed
- Don't overthink the choice

### Quality Assurance:
- All modes enforce enterprise standards
- All modes validate incrementally
- All modes integrate with memories

### Common Mistakes:
- ❌ Using @deep-reason for simple tasks (wastes 20+ minutes)
- ❌ Using @quick-reason for architecture (causes rework)
- ✅ Starting with @quick-reason and escalating as needed

---

## 🔗 Command Combinations

### Daily Workflow:
```bash
# Morning cleanup
@quick-reason "organize yesterday's files"

# Feature work
@think "add new material classification rule"

# Quick fix
@quick-reason "update docs with new endpoints"

# Deployment
@backup-versioned
@deploy-production
```

### Investigation Flow:
```bash
# Start investigating
@quick-reason "check error logs"

# Realizes complexity
@think "investigate and fix classification bug"

# If very complex
@deep-reason "redesign classification engine"
```

### Development Pipeline:
```bash
# Plan
@think "design email notification system"

# Implement pieces
@quick-reason "create email template"
@quick-reason "setup SMTP config"
@think "integrate with existing workflows"

# Validate & Deploy
@workflow-validate
@backup-versioned
@deploy-production
```

---

## 🎯 Mode Comparison Chart

| Feature | Quick-Reason | Think | Deep-Reason |
|---------|--------------|-------|-------------|
| **Time** | 3-5min | 8-10min | 15-30min |
| **Blocks** | 5 | 8 | 13 |
| **Analysis Depth** | Light | Moderate | Comprehensive |
| **Enterprise Checks** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Memory Integration** | ✅ Basic | ✅ Full | ✅ Advanced |
| **Quality Gates** | ✅ Light | ✅ Moderate | ✅ Comprehensive |
| **Parallel Execution** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Progress Validation** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Investigation Block** | ❌ No | ✅ If stuck | ✅ Always available |
| **Risk Analysis** | ⚠️ Basic | ✅ Moderate | ✅ Extensive |
| **Rollback Planning** | ❌ No | ✅ Yes | ✅ Comprehensive |

---

## 🚀 Getting Started

### For New Users:
1. Start with **@quick-reason** for everything
2. Learn when it tells you to escalate
3. Gradually develop intuition for mode selection

### For Experienced Users:
1. Use **@quick-reason** as default
2. Use **@think** when building features
3. Use **@deep-reason** only for architecture

### For Emergency Situations:
1. Use appropriate mode (don't rush to @deep-reason)
2. Let the framework guide you
3. Trust the quality gates

---

## 📚 Related Documentation

- **@quick-reason** - See `.cursor/commands/core/quick-reason.md`
- **@think** - See `.cursor/commands/core/thinking-mode-lite.md`
- **@deep-reason** - See `.cursor/commands/core/thinking-mode.md`

---

## 🎓 Training Scenarios

### Scenario 1: File Cleanup
**Task:** "Move old reports to archive folder"
**Choose:** @quick-reason (obvious, low-risk, 1-2 files)

### Scenario 2: New Integration
**Task:** "Connect Slack to error notifications"
**Choose:** @think (integration, multiple systems, some unknowns)

### Scenario 3: System Redesign
**Task:** "Refactor entire agent architecture for multi-region support"
**Choose:** @deep-reason (architecture, high complexity, many unknowns)

### Scenario 4: Quick Bug Fix
**Task:** "Fix validation error in lead form"
**Choose:** @quick-reason (single file, clear issue)

### Scenario 5: Feature Addition
**Task:** "Add buyer preference filtering to matching engine"
**Choose:** @think (moderate complexity, multiple files, needs planning)

---

**Last Updated:** October 1, 2025  
**Version:** 1.0.0  
**Optimization:** Speed + Quality Balance

