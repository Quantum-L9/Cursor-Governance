---
name: core-debug-mode
description: 🎯 Debug Mode
disable-model-invocation: true
---

---
command: DEBUG_MODE
version: 1.1.0
category: core
tags: [execution, precise, strict, minimal, direct]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: <1min
---

# 🎯 Debug Mode

## 📖 Purpose
Execute ONLY the specific command requested with zero additional analysis, suggestions, or proactive improvements. Strict, minimal, direct execution.

## 🎪 When to Use
- You know exactly what you want and how to do it
- Need precise execution without AI "helpfulness"
- Testing specific changes without side effects
- Quick edits or single-file operations
- When AI is being too proactive

## ⚠️ When NOT to Use
- Complex problems requiring analysis (use @thinking-mode)
- Unclear requirements needing clarification
- Multi-step processes requiring planning

## 🚀 Execution

**MODE: STRICT EXECUTION**

Execute only the specific command requested. 

**DO NOT:**
- Perform additional analysis
- Suggest improvements or enhancements
- Make proactive modifications
- Add extra features or "helpful" additions
- Explain reasoning unless asked

**DO:**
- Execute the exact task specified
- Confirm completion
- Report errors if any
- Ask for clarification if command is ambiguous

## ✅ Success Metrics
1. **Precision:** Only requested action performed
2. **Speed:** Minimal execution time
3. **No Extras:** Zero unsolicited additions

## 🔗 Combines Well With

### Before This Command
- **@thinking-mode** → **DEBUG_MODE** (plan first, then execute precisely)

### After This Command
- **DEBUG_MODE** → **@workflow-validate** (verify the change)
- **DEBUG_MODE** → **@audit-full** (check if more needed)

## 💡 Pro Tips
- Use when you're frustrated with over-helpful AI
- Perfect for experienced users who know what they want
- Great for rapid iteration without explanations
- Ideal for file operations, simple edits, command execution

## 🔖 Examples

### Example 1: Simple File Edit
```
User: "@debug-mode change line 45 to use const instead of let"
AI: [Changes line 45] Done.
```

### Example 2: Command Execution
```
User: "@debug-mode run npm install"
AI: [Executes npm install] Completed.
```

### Example 3: Multiple Specific Edits
```
User: "@debug-mode rename function getUserData to fetchUserData across all files"
AI: [Renames in all files] Renamed in 7 files.
```

---

## 📚 Related Commands
- `thinking-mode` - For complex analysis before execution
- `workflow-validate` - For verification after changes

## 📝 Version History
- **1.1.0** (2025-10-01): Added full metadata and enterprise standards
- **1.0.0** (2025-09-30): Initial debug mode

---

*Command Standard Version: 2.0.0*

