---
name: plan
version: "1.0.0"
description: "Create execution plan before action"
auto_chain: ynp
---

# /plan — Execution Planning

## WHAT IT DOES

Create structured plan before implementation:

1. Define objective
2. Identify scope
3. List TODO items
4. Estimate effort
5. Identify risks

---

## EXECUTION

### 1. OBJECTIVE

```
What: {goal}
Why: {rationale}
Success: {criteria}
```

### 2. SCOPE

```
IN SCOPE:
- {item}

OUT OF SCOPE:
- {item}
```

### 3. TODO PLAN

| # | Task | Files | Effort | Risk |
|---|------|-------|--------|------|
| 1 | ... | ... | S/M/L | 🟢/🟡/🔴 |

### 4. DEPENDENCIES

```
Task 1 → Task 2 → Task 3
              ↘ Task 4
```

### 5. RISKS

| Risk | Impact | Mitigation |
|------|--------|------------|

---

## OUTPUT

```markdown
## 📋 PLAN: {title}

### Objective
{what and why}

### Scope
**In:** {list}
**Out:** {list}

### TODO Plan
| # | Task | Files | Effort |
|---|------|-------|--------|

### Dependencies
{graph}

### Risks
| Risk | Mitigation |
|------|------------|

### Estimate
**Total:** {time}
**GMPs:** {count}
```

→ **Auto-chains to /ynp** (recommends /gmp or /forge)

--- End Command ---
