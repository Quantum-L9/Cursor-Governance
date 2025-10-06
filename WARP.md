# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a governance and configuration repository for Cursor AI development workflows. It defines a structured system of AI agent profiles, rules, and operational frameworks for high-velocity development. The project implements a "YNP (Yes/No/Pause) Mode" system for production-grade AI-assisted development.

## Architecture

### Core Components

**Governance Profiles System** (`/profiles/`)
- **Orchestrator** (`orchestrator.md`) - Top-level governance layer that coordinates all other profiles
- **Security & Access** (`security-access.md`) - Handles secrets, authentication, and least privilege access
- **Operational Health** (`operational-health.md`) - Manages preflight checks, health monitoring, and rollbacks
- **Versioning** (`versioning.md`) - Enforces headers, semantic versioning, and file archiving
- **Workflow Governance** (`workflow-governance.md`) - n8n workflow validation, deployment, and testing
- **Reasoning** (`reasoning.md`) - Decision-making modes and self-verification protocols

**AI Mode Definitions**
- **Architect Mode** - Systems architect for modular, production-grade code
- **Think Tank Mode** - Strategic thinking partner for structured documentation
- **Strategist Mode** - Protocol designer for governance and decision-making systems

**Configuration Files**
- `config.json` - Cursor AI prompt configuration
- `snippets.json` - Reusable AI mode prompts
- `meta.md` - Project decision log and active concepts

## Key Operational Patterns

### YNP (Yes/No/Pause) Mode System
- **Light YNP (Default)** - Fast, lean, production-ready outputs
- **Heavy Forge** - Triggered by "Enable YNP", "/forge", or "Heavy Forge"
  - 3-step chain: Scope & Integrity → Draft & Chain → Finalize & Deliver

### Governance Precedence Rules (highest to lowest priority)
1. Security & Access (secrets, auth, least privilege)
2. Operational Health (preflight, env sync, checkpoints)  
3. Versioning (headers, naming, archiving, version map)
4. Workflow Governance (n8n validation, deploy, migrate, test)
5. Reasoning (modes, self-verification, evidence discipline)

### Standard File Headers
All created/edited files must include the standard header from `profiles/versioning.md`:
```
/*
====================================================================
| Workflow: <Workflow Name>
| Agent: <Primary Agent>
| Sub-Agent: <Sub-Agent or Node>
|
| File: <filename_with_version.ext>
| Created: <YYYY-MM-DD HH:MM:SS UTC>
| Last Modified: <YYYY-MM-DD HH:MM:SS UTC>
| Version: v<major.minor.patch>
| Author: <Assistant/Tool Name>
| Description: <one-liner purpose>
| Dependencies: <key libs/other files/APIs>
====================================================================
*/
```

## Development Workflows

### Working with Profiles
```bash
# View all governance profiles
ls -la profiles/

# Read specific profile
cat profiles/orchestrator.md

# Edit profile (remember to update version header)
# Follow versioning rules from profiles/versioning.md
```

### AI Mode Activation
Use these snippet prefixes in Cursor:
- `mode-architect` - Activates Systems Architect mode
- `mode-thinktank` - Activates Strategic Thinking Partner mode  
- `mode-strategist` - Activates Protocol Designer mode

### Configuration Management
```bash
# Update AI prompt configuration
# Edit config.json (auto-applied by Cursor)

# Add new AI mode snippets
# Edit snippets.json with new mode definitions

# Update project decisions and concepts
# Edit meta.md with new decisions or active roles
```

### File Versioning
All files follow semantic versioning (major.minor.patch):
- **Major**: Breaking changes, schema/structure shift
- **Minor**: New features or nodes, non-breaking  
- **Patch**: Fixes, refactors, docs-only changes

File naming convention: `<Workflow>_<Agent>_<SubAgent>_vX.Y[.Z].ext`

### Security & Environment
- Never echo secrets or API keys - use `****…****` redaction
- Environment variables should be managed via `.env` files
- Follow least privilege access patterns
- All credentials must be properly scoped and validated

## Key Governance Rules

### Non-Negotiable Behavior
- **No Drifting**: Obey all linked governance files
- **Autonomous Execution**: Fix issues silently and proceed (log actions)
- **No Pausing for Confirmation**: Proceed automatically unless security requires human auth
- **Self-Verification**: Apply reasoning profile checks before delivery
- **Mandatory Output Shape**: Follow profile-defined response structures exactly

### Completion Gates
A task is complete only after:
1. Security and environment checks pass or are repaired
2. Headers + versioning are correct  
3. Workflow governance validations satisfied (if relevant)
4. Reasoning self-check recorded
5. Delivery log + "Your Next Prompt" section included

### Triggers and Commands
- "Break it down" - Decompose complex tasks
- "Optimize for deploy" - Focus on production readiness
- "Snapshot this" - Use Think Tank mode for documentation
- "Enable YNP" / "/forge" / "Heavy Forge" - Activate Heavy Forge mode

## Environment Context
- **Default Profile**: Architect Mode (as per meta.md decisions)
- **Guardrails**: Clarity, modularity, test hooks enforced
- **Node Agents**: Automated actors with scoped responsibilities in n8n
- **Protocol Framing**: Structured decision-making across roles