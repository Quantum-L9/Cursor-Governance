---
name: rules
version: "2.2.0"
description: "List ALL governance rules from .cursor/rules/ with status"
auto_chain: null
---

# /rules — Governance Rules (v2.1.0)

## EXECUTION

When `/rules` is invoked, read ALL `.mdc` files from `.cursor/rules/` and report:

### Step 1: Count and List

```bash
# Count total rules
ls .cursor/rules/*.mdc | wc -l

# List rules with alwaysApply: true
grep -l "alwaysApply: true" .cursor/rules/*.mdc | xargs -I{} basename {}

# List rules WITHOUT alwaysApply: true
grep -L "alwaysApply: true" .cursor/rules/*.mdc | xargs -I{} basename {}
```

### Step 2: Output Format

```markdown
## 📜 GOVERNANCE RULES

**Total:** {count} rules | **Always-Applied:** {count} | **Context-Only:** {count}

### ✅ Always-Applied Rules (loaded every session)

| # | File | Description |
|---|------|-------------|
| 1 | 00-global.mdc | L9 global rules |
| 2 | 30-odoo-native.mdc | Odoo-native patterns |
| ... | ... | ... |

### ⚠️ Context-Only Rules (loaded when matching globs)

| # | File | Trigger |
|---|------|---------|
| 1 | 10-lang-typescript.mdc | `**/*.ts` files |
| ... | ... | ... |

### 🔴 Rules Without Frontmatter (need fixing)

| # | File |
|---|------|
| 1 | ... |
```

---

## CRITICAL ODOO RULES (Always-Applied)

| File | Purpose |
|------|---------|
| `30-odoo-native.mdc` | ORM patterns, recordsets, domains, actions |
| `95-plasticos-equipment-policy.mdc` | Equipment wiring requirements |

---

## CRITICAL SAFETY RULES (Always-Applied)

| File | Purpose |
|------|---------|
| `01-git-push-prohibition.mdc` | NEVER push without explicit request |
| `96-git-push-approval.mdc` | Git push requires approval |
| `99-no-auto-commit.mdc` | Never auto-commit |
| `99-execute-as-instructed.mdc` | Execute exactly as instructed |
| `91-existing-code-source-of-truth.mdc` | Existing code wins |
| `92-learned-lessons.mdc` | Critical prevention rules |

---

## HOW TO ENABLE A RULE

Add this frontmatter to any `.mdc` file:

```yaml
---
description: "Brief description of the rule"
alwaysApply: true
---
```

Or for context-triggered rules:

```yaml
---
description: "Brief description"
alwaysApply: false
globs: ["**/*.py", "plasticos_*/**/*"]
---
```

---

## RULE CATEGORIES

| Prefix | Category | Examples |
|--------|----------|----------|
| `00-09` | Global | Core rules, git, slash commands |
| `10-29` | Language | Python, TypeScript |
| `30-39` | Framework | Odoo, React |
| `40-49` | Domain | Business logic |
| `50-59` | QA | Testing |
| `60-69` | Anti-patterns | What NOT to do |
| `70-79` | Workflow | CI/CD, reviews |
| `80-89` | GMP | Governance process |
| `90-99` | Protection | Lessons, policies |
