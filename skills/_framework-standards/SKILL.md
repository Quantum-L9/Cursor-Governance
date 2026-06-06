---
name: _framework-standards
description: 📐 Command Writing Standards
disable-model-invocation: true
---

# 📐 Command Writing Standards
**Version:** 2.0.0  
**Last Updated:** 2025-10-01

---

## 🎯 Purpose
This document defines the standard format, structure, and best practices for creating high-quality Cursor commands that are composable, reliable, and enterprise-grade.

---

## 📋 Standard Command Template

```markdown
---
command: <COMMAND_NAME_IN_CAPS>
version: 1.0.0
category: [core|n8n|infrastructure|analysis|pipeline]
tags: [tag1, tag2, tag3]
dependencies: [other-command-1, other-command-2]
risk_level: [safe|moderate|high]
requires_backup: [yes|no]
estimated_duration: [<1min|1-5min|5-15min|15min+]
---

# 🎯 <COMMAND_NAME>

## 📖 Purpose
One clear sentence describing what this command does and why it exists.

## 🎪 When to Use
- Scenario 1 requiring this command
- Scenario 2 requiring this command  
- Scenario 3 requiring this command

## ⚠️ When NOT to Use
- Anti-pattern 1 where this command would be wrong
- Anti-pattern 2 where a different command is better

## 🔍 Pre-Conditions
- [ ] Condition 1 that must be true before running
- [ ] Condition 2 that must be verified
- [ ] Condition 3 that must exist

## 🚀 Execution

### Step 1: <Clear Action>
Detailed instructions for this step with specific examples.

### Step 2: <Next Action>
Detailed instructions with what to look for and validate.

### Step 3: <Final Action>
Final step with expected output description.

## ✅ Post-Conditions
- [ ] Expected outcome 1 to verify
- [ ] Expected outcome 2 to confirm
- [ ] Expected outcome 3 to validate

## 🔗 Success Metrics
1. **Metric 1:** How to measure success (e.g., "All workflows validate without errors")
2. **Metric 2:** Quantifiable outcome (e.g., "Zero credential placeholders found")
3. **Metric 3:** Quality indicator (e.g., "100% test coverage passes")

## 🚨 Error Handling

### Common Errors
1. **Error Type 1**
   - Cause: Why this happens
   - Solution: How to fix it
   - Prevention: How to avoid it

2. **Error Type 2**
   - Cause: Root cause
   - Solution: Fix steps
   - Prevention: Preventive measures

### Rollback Procedure
If this command fails, follow these steps to restore previous state:
1. Step 1 for rollback
2. Step 2 for rollback
3. Verification step

## 🔗 Combines Well With

### Before This Command
- **command-a** → THIS-COMMAND (prepares environment)
- **command-b** → THIS-COMMAND (validates prerequisites)

### After This Command  
- THIS-COMMAND → **command-c** (natural next step)
- THIS-COMMAND → **command-d** (optional enhancement)

### Common Pipelines
1. **Pipeline Name:** command-a → THIS-COMMAND → command-c
2. **Pipeline Name:** command-b → THIS-COMMAND → command-d

## 📊 Output Format
Describe what output this command produces:
- Reports generated
- Files created/modified
- Console output format
- Notifications sent

## 💡 Pro Tips
- Tip 1 for power users
- Tip 2 for optimization
- Tip 3 for edge cases

## 🔖 Examples

### Example 1: Basic Usage
\`\`\`
Input: <specific input example>
Expected Output: <what you should see>
\`\`\`

### Example 2: Advanced Usage
\`\`\`
Input: <complex scenario>
Expected Output: <detailed results>
\`\`\`

---

## 📚 Related Commands
- `other-command-1` - What it does and how it relates
- `other-command-2` - Comparison and use cases
- `other-command-3` - Alternative approaches

## 📝 Version History
- **1.0.0** (2025-10-01): Initial creation with full metadata

---

*Command Standard Version: 2.0.0*
```

---

## 🎨 Naming Conventions

### Command File Names
- Use **kebab-case**: `workflow-validate.md`, `backup-versioned.md`
- Be descriptive: `deploy-production.md` not `deploy.md`
- Action-focused: Use verbs (validate, deploy, analyze, generate)

### Command Keywords (in YAML)
- Use **SCREAMING_SNAKE_CASE**: `WORKFLOW_VALIDATE`, `DEPLOY_PRODUCTION`
- Match file name: `workflow-validate.md` → `WORKFLOW_VALIDATE`

---

## 📂 Category Guidelines

### **core**
Commands that change how the AI thinks or operates fundamentally.
- Reasoning frameworks
- Execution modes
- Meta-cognitive tools

### **n8n**
Commands specific to n8n workflow operations.
- Workflow manipulation
- Node operations
- n8n deployment

### **infrastructure**
Commands for project setup, maintenance, and operations.
- Backups and recovery
- Credential management
- Workspace organization

### **analysis**
Commands that analyze, report, or visualize without making changes.
- Architecture analysis
- Performance profiling
- Security audits

### **pipeline**
Multi-command orchestrated sequences.
- Deployment pipelines
- Maintenance routines
- Emergency procedures

---

## 🏷️ Tagging Best Practices

### Use Descriptive Tags
- **Function:** validation, deployment, analysis, backup
- **Domain:** n8n, supabase, api, database
- **Quality:** enterprise, production, testing
- **Risk:** destructive, safe, reversible
- **Automation:** scheduled, triggered, manual

### Tag Limit
- Minimum: 3 tags
- Maximum: 7 tags
- Focus on searchability

---

## ⚠️ Risk Level Definitions

### **safe**
- Read-only operations
- Additive changes only
- No destructive actions
- Can't break production
- No backup required

### **moderate**
- Makes changes but reversible
- Has safety checks built-in
- Low risk of data loss
- Backup recommended but optional
- Can be tested in isolation

### **high**
- Destructive operations possible
- Impacts production systems
- Requires backup ALWAYS
- Needs validation before execution
- Should have rollback procedure
- Examples: deployment, credential rotation, database migration

---

## 🔗 Dependency Declaration

### When to Declare Dependencies
- Command A requires output from Command B
- Command A needs environment setup by Command B
- Command A validates conditions set by Command B

### Dependency Types
1. **Hard Dependencies:** Must run before (workflow-validate before workflow-deploy)
2. **Soft Dependencies:** Recommended but optional (backup-versioned before any deployment)
3. **Alternative Dependencies:** Can use Command B OR Command C

### Example
```yaml
dependencies: [workflow-validate, backup-versioned]
optional_dependencies: [performance-profile]
alternative_dependencies: [[backup-versioned, manual-backup]]
```

---

## 📊 Success Metrics Guidelines

Every command should define **3-5 measurable success criteria**:

### ✅ Good Metrics
- "All 15 workflows validate without errors"
- "Backup file created with size > 1MB"
- "Zero exposed API keys detected"
- "Deployment completes in < 5 minutes"

### ❌ Bad Metrics
- "Everything works" (too vague)
- "Looks good" (not measurable)
- "No problems" (negative metric)

---

## 🧪 Testing Requirements

### Every Command Should Include
1. **Dry-run capability** where applicable
2. **Validation step** before execution
3. **Output verification** after execution
4. **Rollback procedure** for risky operations

### Test Scenarios to Document
- Happy path (everything works)
- Missing dependencies
- Invalid inputs
- Partial failures
- Network/API failures

---

## 📚 Documentation Requirements

### Mandatory Sections
- ✅ Purpose (1 sentence)
- ✅ When to Use (3+ scenarios)
- ✅ Pre-Conditions (2+ checks)
- ✅ Execution (step-by-step)
- ✅ Post-Conditions (2+ validations)
- ✅ Success Metrics (3-5 measures)
- ✅ Error Handling (2+ error types)
- ✅ Combines Well With (3+ combinations)

### Optional but Recommended
- When NOT to Use
- Output Format
- Pro Tips
- Examples
- Related Commands

---

## 🎯 Quality Checklist

Before submitting a new command, verify:

- [ ] Follows standard template structure
- [ ] Has complete YAML frontmatter
- [ ] Uses proper naming conventions
- [ ] Declares all dependencies
- [ ] Defines clear success metrics
- [ ] Includes error handling
- [ ] Documents command combinations
- [ ] Has at least 1 usage example
- [ ] Specifies estimated duration
- [ ] Assigns correct risk level
- [ ] Added to meta.yaml registry
- [ ] Tested in real scenario

---

## 🚀 Command Evolution

### Versioning Rules (Semantic Versioning)
- **Major (X.0.0):** Breaking changes, different execution flow
- **Minor (1.X.0):** New features, additional sections, enhanced functionality
- **Patch (1.0.X):** Bug fixes, typos, clarifications

### When to Update Version
- Any change to execution steps → Increment version
- New error handling → Minor version bump
- Fixed typo in description → Patch version bump

### Changelog Requirements
Every version change must be documented in the Version History section.

---

## 💡 Pro Command Design Tips

### 1. **Make Commands Composable**
Design commands that work well alone AND in combination with others.

### 2. **Fail Fast with Clear Errors**
Don't let commands run for 10 minutes before failing. Check prerequisites immediately.

### 3. **Idempotent When Possible**
Running a command multiple times should be safe and produce the same result.

### 4. **Progressive Enhancement**
Basic functionality works simply, advanced features available with flags/options.

### 5. **Self-Documenting Output**
Command output should explain what happened and what to do next.

---

## 📦 Command Packaging

### Standalone Commands
Single .md file with complete documentation.

### Command Sets
Multiple related commands in same category folder with shared README.

### Pipeline Commands
Reference other commands by name, include dependency diagram.

---

## 🎓 Learning from Usage

### Commands Should Improve Over Time
- Track which error scenarios users hit most
- Add FAQ section for common questions
- Include real-world examples from usage
- Optimize steps based on feedback

### Usage Analytics to Track
- Execution count
- Success rate
- Average duration
- Common error types
- Most common combinations

---

## ✨ Excellence Indicators

### A World-Class Command Has:
- 📖 Crystal clear purpose
- 🎯 Specific use cases  
- ✅ Verifiable success criteria
- 🚨 Comprehensive error handling
- 🔗 Documented combinations
- 💡 Real usage examples
- 🔄 Rollback procedure (if risky)
- 📊 Measurable outcomes

---

*Standard Version: 2.0.0*  
*Effective Date: 2025-10-01*  
*Maintained by: Enterprise Automation Team*

