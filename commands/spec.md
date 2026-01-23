---
name: spec
version: "7.0.0"
description: "Generate specification before building"
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

--- End Command ---
