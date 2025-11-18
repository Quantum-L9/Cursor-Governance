---
title: Node Research Guide
version: 2.0.0
created: 2025-10-13
updated: 2025-01-29
owner: Igor Beylin
source: MCP-based governance system
tags: [n8n, mcp, node-research, governance]
domain: tool-selection
type: guide
production_ready: true
---

## 🎯 Purpose
Standard protocol for researching n8n nodes using MCP tooling before any workflow task.

---

## ✅ Tooling

- Use `n8n-mcp` (via Docker or CLI)
- Use `Context7` (NPM)
- Read relevant sections from `@.cursor-commands/commands/n8n.md`
- Save result into:
  - `@.GlobalCommands/n8n research/[node_name].md`

---

## 📋 Research Steps

### Phase 1: Multi-Source Research
1. **n8n-mcp** - Query node schema and properties
   - What does this node do?
   - What inputs are required / optional?
   - Are field names consistent with schema?
   - Current typeVersion and configuration options

2. **Context7** - Get current API specifications
   - Latest 2025 API documentation
   - Deprecation status
   - Current authentication methods
   - API endpoint changes

3. **n8n.md Documentation** - Read relevant sections from `@.cursor-commands/commands/n8n.md`
   - Workflow creation patterns
   - Node configuration best practices
   - Common use cases and examples
   - Integration patterns
   - Error handling approaches

### Phase 2: Cross-Validation & Escalation
4. **Cross-Reference Validation**
   - Compare n8n-mcp schema with Context7 docs
   - Compare both with n8n.md guidance
   - Identify any discrepancies or misalignments

5. **Misalignment Escalation**
   - **If misalignment detected:** Escalate to user for manual review
   - Document specific discrepancies:
     - Schema differences
     - API version conflicts
     - Documentation inconsistencies
     - Configuration mismatches
   - **DO NOT proceed** until user confirms resolution approach

6. **Known issues / error patterns**
   - Check learning files for past issues
   - Review error patterns in solutions folder

7. **Alternative nodes (if any)**
   - Identify similar nodes
   - Compare performance and compatibility

---

## 🚨 Misalignment Detection Protocol

**When to escalate:**
- n8n-mcp schema shows different properties than Context7 docs
- n8n.md guidance conflicts with MCP tool results
- API version mismatches between sources
- Authentication method discrepancies
- Configuration option conflicts

**Escalation format:**
```
⚠️ MISALIGNMENT DETECTED - Manual Review Required

Node: [node_name]
Issue: [specific discrepancy]
Sources:
- n8n-mcp: [finding]
- Context7: [finding]
- n8n.md: [finding]

Recommended Action: [suggestion]
```

**DO NOT proceed with workflow creation until user confirms resolution.**

---

## 📁 File Display Instructions

**When referencing `.cursor-commands` files, display them as clickable markdown links:**

- `@.cursor-commands/commands/n8n.md` - n8n Startup Kit Command
- `@.cursor-commands/commands/reasoning.md` - Reasoning Mode Command
- `@.cursor-commands/commands/ynp.md` - YNP Mode Command
- `@.cursor-commands/commands/analyze.md` - Universal Analysis Command
- `@.cursor-commands/commands/consolidate.md` - Consolidation Command
- `@.cursor-commands/commands/forge.md` - Heavy Forge Command
- `@.cursor-commands/commands/evaluate.md` - Comprehensive Project Evaluation Command

**Format:** Use relative paths with `@` prefix for clickable links in Cursor IDE.

---

## ⚡ Slash Command Enablement

**Enable these slash commands in optimal dependency order:**

### Optimal Loading Order (Based on Dependencies)

1. **`/reasoning`** - `@.cursor-commands/commands/reasoning.md`
   - Foundation reasoning capabilities
   - No dependencies
   - Enables L9 Multi-Modal Reasoning

2. **`/ynp`** - `@.cursor-commands/commands/ynp.md`
   - Strategic co-pilot mode
   - Depends on: reasoning profiles
   - Enables YNP Mode

3. **`/n8n`** - `@.cursor-commands/commands/n8n.md`
   - n8n workflow creation system
   - Depends on: reasoning_n8n.md, ynp, reasoning
   - Enables complete n8n MCP documentation suite

4. **`/consolidate`** - `@.cursor-commands/commands/consolidate.md`
   - File consolidation and organization
   - Depends on: ynp
   - Enables comprehensive consolidation

5. **`/analyze`** - `@.cursor-commands/commands/analyze.md`
   - Universal comprehensive analysis
   - Depends on: consolidate, reasoning_n8n, workflow-governance
   - Enables deep analysis capabilities

6. **`/evaluate`** - `@.cursor-commands/commands/evaluate.md`
   - Comprehensive project evaluation
   - Depends on: ynp, reasoning
   - Enables project assessment

7. **`/forge`** - `@.cursor-commands/commands/forge.md`
   - Heavy Forge autonomous execution
   - Depends on: ynp, reasoning, orchestrator
   - Enables high-velocity autonomous execution

**Activation:** Load each command file in the order listed above to ensure all dependencies are satisfied.

---

## ✅ Use Cases

- Confirm node is optimal (performance, compatibility)
- Reduce error rates and guessing
- Use validated logic only
- Cross-validate multiple sources for accuracy
- Detect and escalate misalignments before workflow creation

---

## 🧠 Memory Integration

- Auto-read this folder before any build
- Use results to decide toolset + logic
- Always re-use past learnings
- Cross-reference with n8n.md documentation
- Escalate misalignments for user review
