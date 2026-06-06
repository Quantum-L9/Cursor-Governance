---
name: l9-plan
description: Create an execution plan or implementation specification before building. Use when scope is unclear, requirements need decomposition, or the next step should be planned before code changes.
---

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

---

<!-- migrated-from: commands/spec.md -->

---
name: spec
version: "7.1.0"
description: "Generate specification before building"
before_chain: rules
auto_chain: ynp
---

# /spec — Specification Generator

## WHAT IT DOES

Generate complete spec before implementation:

1. Context & Goals
2. Constraints
3. Architecture
4. Detailed Design
5. Operations
6. Risks
7. Acceptance Criteria

**Output:** Spec document ready for `/forge` or `/gmp`

---

## EXECUTION

### 1. GATHER CONTEXT

```
QUESTIONS:
├── What problem does this solve?
├── Who are the users?
├── What are the constraints?
├── What already exists to leverage?
└── What does success look like?
```

### 2. GENERATE SPEC

```markdown
# {Project} Specification

## 1. Overview
**Problem:** ...
**Solution:** ...
**Success Criteria:** ...

## 2. Constraints
- Must: ...
- Must Not: ...
- Should: ...

## 3. Architecture
```
[diagram]
```

## 4. Components
| Component | Purpose | Interface |
|-----------|---------|-----------|

## 5. Data Flow
Entry → Process → Store → Return

## 6. Operations
- Deployment: ...
- Monitoring: ...
- Rollback: ...

## 7. Risks
| Risk | Mitigation |
|------|------------|

## 8. Acceptance
- [ ] Criterion 1
- [ ] Criterion 2

## 9. Phases
| Phase | Scope | GMPs |
|-------|-------|------|
```

---

## OUTPUT LOCATION

```
specs/{project}-spec.md
```

→ **Auto-chains to /ynp** (recommends /forge or /gmp)

---

## Future: IR Engine Integration

The IR engine (`ir_engine/`) can enhance spec generation:

- **`SemanticCompiler`** (`ir_engine/semantic_compiler.py`) converts natural language descriptions into structured `IRGraph` representations, extracting requirements, constraints, and dependencies automatically.
- **`UnifiedController.compile_only(text, context)`** provides a single entry point for NL-to-IR compilation.

When wired, `/spec` could use `SemanticCompiler` to:
1. Parse the user's NL description into structured intent
2. Auto-detect constraints and dependencies from the IRGraph
3. Pre-populate the spec template with machine-extracted requirements

**Status:** Not yet wired. The `UnifiedController` is complete (v2.0.0) and exported from `orchestration/`. Integration requires calling `compile_only()` during the "GATHER CONTEXT" phase and feeding the IRGraph into spec template generation.

--- End Command ---
