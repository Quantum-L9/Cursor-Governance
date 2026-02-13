---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "DOC-CAP-001"
component_name: "System Capabilities Manifest"
layer: "documentation"
domain: "system_overview"
type: "manifest"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "informational"
compliance_required: false
audit_trail: false
security_classification: "internal"

# === BUSINESS METADATA ===
purpose: "Comprehensive inventory of available reasoning systems, tools, and capabilities"
summary: "Self-awareness manifest for AI agents to understand what tools and systems are available at workspace initialization"
business_value: "Enables proactive capability utilization and prevents reactive tool discovery"
---

# 🧠 Suite 6 System Capabilities Manifest

**Purpose**: AI agents should read this file at workspace initialization to understand available capabilities.

---

## 🎯 Core Reasoning Systems

### 1. Bayesian Probabilistic Engine
**Location**: `foundation/logic/probabilistic_engine.py`  
**Component ID**: `FND-PE-001`  
**Status**: ✅ Active

**Capabilities**:
- Weighted evidence combination (PAC-Bayesian)
- Temperature-based calibration
- Subjective logic decomposition (Trust/Disbelief/Uncertainty)
- Expected Calibration Error (ECE) optimization
- Self-learning from user feedback

**Performance**:
- Inference time: <50ms (typically ~8ms)
- Memory overhead: <10MB (typically ~4MB)
- Target ECE: <0.05 (calibrated confidence)

**Use Cases**:
- Risk assessment (file compliance, command execution, escalation need)
- Confidence scoring with uncertainty quantification
- Evidence-based decision making
- Any probabilistic reasoning task requiring calibrated outputs

**API**:
```python
from foundation.logic.probabilistic_engine import CursorProbabilisticEngine

engine = CursorProbabilisticEngine()
assessment = engine.assess_file_compliance_risk(
    file_path="path/to/file.py",
    file_type="governance",
    edit_frequency=3.0,
    user_correction_count=0,
    references_count=8
)
# Returns: probability, confidence, risk_level, subjective_logic, reasoning
```

---

### 2. Hybrid Reasoning Kernel
**Location**: `foundation/logic/hybrid_kernel.py`  
**Component ID**: `FND-HK-001`  
**Status**: ✅ Active

**Capabilities**:
- Combines probabilistic + symbolic reasoning
- DSL/FOL integration for formal logic
- Real-time policy enforcement
- Cross-layer coordination

**Use Cases**:
- Complex governance decisions requiring both probability and logic
- Hybrid symbolic-probabilistic inference
- Multi-constraint optimization

---

### 3. Universal Governance Kernel
**Location**: `foundation/logic/universal-kernel.md`  
**Component ID**: `FND-LG-002`  
**Status**: ✅ Active

**Capabilities**:
- DSL/FOL-based rule enforcement
- <10ms policy checking
- Autonomous enforcement
- Real-time governance validation

**Use Cases**:
- Governance rule enforcement
- Policy compliance checking
- Autonomous operation triggers

---

### 4. Cursor Native Reasoning Framework
**Location**: `intelligence/reasoning/cursor-native-reasoning.md`  
**Component ID**: `INT-RE-001`  
**Status**: ✅ Active

**Capabilities**:
- 10-step structured reasoning framework
- Context hydration and system decomposition
- Strategy selection and validation
- Integration with Suite 6 governance

**Use Cases**:
- Technical evaluations
- Architecture decisions
- Problem decomposition
- Implementation planning

**Steps**:
1. Define Objective
2. Hydrate Context
3. Decompose System
4. Choose Strategy
5. Execute Analysis
6. Synthesize Decision
7. Validate Approach
8. Document Actions
9. Identify Risks
10. Confirm Maintainability

---

## 🧬 Intelligence Systems

### 1. Meta-Learning System
**Location**: `intelligence/meta-learning/meta-learning-log.md`  
**Component ID**: `INT-ML-001`  
**Status**: ✅ Active

**Capabilities**:
- Pattern extraction from conversations
- Mistake tracking and prevention
- Solution cataloging
- Autonomous learning updates

**Learning Sources**:
- Chat exports (hourly)
- User corrections
- Outcome tracking
- Performance metrics

---

### 2. Context-Memory System
**Location**: `intelligence/context-memory/`  
**Component ID**: `INT-CTX-001`  
**Status**: ✅ Active

**Capabilities**:
- Session context capture (hourly)
- Project detection
- Key actions extraction
- Decisions and next steps tracking
- Context restoration on startup

**Files**:
- `context-extractor.py` - Extracts from chat SQLite DB
- `sessions/` - Hourly context snapshots
- `index.json` - 7-day rolling index

**Usage**:
```bash
# Manual extraction
./ops/scripts/process_context.sh

# View last session
./ops/scripts/show_context.sh
```

---

### 3. Learning Processor System
**Location**: `ops/scripts/process_learnings.sh`  
**Status**: ✅ Active (runs hourly)

**Capabilities**:
- Automated pattern extraction
- Mistake aggregation
- Solution indexing
- Memory database updates

**Outputs**:
- `learning/failures/repeated-mistakes.md`
- `learning/patterns/quick-fixes.md`
- `learning/solutions/*.md`
- `ops/logs/memory_index.json`

---

## 🔧 Foundation Components

### Rule Registry
**Location**: `foundation/logic/rule-registry.json`  
**Component ID**: `FND-LG-001`

**Contains**:
- Governance rules and policies
- Probabilistic model definitions
- Threshold configurations
- Calibration parameters

### Agent Stub Manager
**Location**: `foundation/agents/agent-stub-manager.py`  
**Component ID**: `FND-AG-001`

**Capabilities**:
- Agent discovery and registration
- Stub validation
- Capability inventory
- Cross-agent coordination

### Governance Integrity System
**Location**: `foundation/security/governance-integrity.py`

**Capabilities**:
- File signature verification
- Tamper detection
- Integrity auditing
- Security validation

---

## 📊 Telemetry & Monitoring

### Calibration Dashboard
**Location**: `telemetry/calibration_dashboard.py`

**Capabilities**:
- ECE monitoring
- Threshold optimization
- Model performance tracking
- Confidence calibration visualization

### Auto-Calibrator
**Location**: `learning/auto_calibrator.py`

**Capabilities**:
- Autonomous threshold adjustment
- Temperature optimization
- Evidence weight tuning
- Real-time calibration

### Feedback Collector
**Location**: `learning/feedback_collector.py`

**Capabilities**:
- User feedback capture
- Outcome tracking
- Learning signal generation
- Beta distribution updates

---

## 🎭 Reasoning Profiles

Available in `profiles/`:

| Profile | File | Use Case |
|---------|------|----------|
| **L9 Agent Reasoning** | `reasoning_technical_operations.md` | Agent and workflow development |
| **Document Reasoning** | `reasoning_docs.md` | Documentation creation |
| **Technical Operations** | `reasoning_technical_operations.md` | System architecture |
| **YNP Mode** | `ynp_mode.md` | Yes/No/Partial decision framework |
| **Dev Mode** | `dev_mode.md` | Development workflow |
| **Orchestrator** | `orchestrator.md` | Multi-agent coordination |

---

## 💾 MCP Memory Stack (C1 Hetzner)

**Source of Truth**: `memory/MCP-MEMORY-CAPSULE.md`
**Client**: `agents/cursor/cursor_memory_client.py`
**Quick Reference**: `mcp_memory/QUICK_REFERENCE.md`

### Architecture

```
Cursor IDE → HTTPS → Caddy (VPS 157.180.73.53) → l9-api (port 8000)
                                                    ├─ /mcp/tools (list tools)
                                                    ├─ /mcp/call (execute tool)
                                                    └─ MemorySubstrateService → PostgreSQL + pgvector
```

### CLI Commands

```bash
python3 agents/cursor/cursor_memory_client.py health          # Check C1 health
python3 agents/cursor/cursor_memory_client.py search "query"  # Semantic search
python3 agents/cursor/cursor_memory_client.py write "content" --kind lesson  # Store memory
python3 agents/cursor/cursor_memory_client.py stats           # Memory statistics
python3 agents/cursor/cursor_memory_client.py inject "task"   # Context injection
```

### MCP Tools

| Tool                        | Purpose                |
| --------------------------- | ---------------------- |
| `save_memory`               | Store with embedding   |
| `search_memory`             | Semantic search        |
| `get_memory_stats`          | Statistics             |
| `graph_query`               | Neo4j Cypher queries   |
| `graph_get_entity`          | Get entity by type/ID  |
| `get_context_injection`     | Auto-context for tasks |
| `extract_session_learnings` | Extract patterns       |
| `query_temporal`            | Time-based queries     |

### Pipeline

Writes to 4 tables: `packet_store`, `memory_embeddings`, `knowledge_facts`, `reasoning_traces`
**Pipeline:** `main_dag` | **Latency:** 650-1800ms

### Environment (Local `.env`)

```bash
L9_API_URL=https://157.180.73.53:9001
L9_EXECUTOR_API_KEY=<MCP_API_KEY_C from VPS>
```

### Governance

| Caller | Key             | Read         | Write    | Delete   |
| ------ | --------------- | ------------ | -------- | -------- |
| L-CTO  | `MCP_API_KEY_L` | All memories | All      | All      |
| Cursor | `MCP_API_KEY_C` | All memories | Own only | Own only |

**Kinds:** `fact`, `insight`, `lesson`, `milestone`, `preference`, `pattern`
**Scopes:** `developer` (shared), `l-private` (L only), `global`

---

## ⚡ Slash Commands

Available globally (registered in `.cursor-commands/commands/`):

| Command | File | Purpose |
|---------|------|---------|
| `/gmp` | `gmp.md` | Governance Managed Process - phased execution |
| `/harvest` | `harvest.md` | Extract code from documents via sed |
| `/wire` | `wire.md` | Wire/integrate components |
| `/reasoning` | `reasoning.md` | L9 Multi-Modal Reasoning |
| `/forge` | `forge.md` | Heavy implementation mode |
| `/ynp` | `ynp.md` | Yes/No/Partial evaluation |
| `/consolidate` | `consolidate.md` | File consolidation |
| `/analyze` | `analyze.md` | Codebase analysis |
| `/evaluate` | `evaluate.md` | Comprehensive project evaluation |
| `/start-session` | `start-session.md` | Initialize session context |
| `/end-session` | `end-session.md` | Close session, extract learnings |

See `.cursor/rules/02-slash-commands.mdc` for full registry.

---

## 🔄 Automated Processes

### LaunchAgent Services (hourly):

| Service | Script | Purpose |
|---------|--------|---------|
| `com.tenx.chat-export` | `export_chats.sh` | Export Cursor chats |
| `com.tenx.learning-processor` | `process_learnings.sh` | Extract patterns/mistakes |
| `com.cursor.context.processor` | `process_context.sh` | Capture session context |

**Check Status**:
```bash
launchctl list | grep -E "tenx|cursor"
```

---

## 📦 Available in Other Workspaces

### Mack v7.1 Revolutionary Reasoning
**Location**: `Work Files/Mack.v7.1 Revolutionary Reasoning/`

**Capabilities**:
- 45-step KB enrichment framework
- Bayesian confidence scoring (integrated)
- Beta distribution learning updates
- Communication intelligence
- BCP intelligence APIs
- Neo4j graph reasoning

### Bayesian Upgrade Kit
**Location**: `Bayesian Upgrade/`

**Components**:
- `foundation/probabilistic_engine.py` (production)
- `foundation/hybrid_kernel.py`
- `learning/auto_calibrator.py`
- `learning/feedback_collector.py`
- `telemetry/calibration_dashboard.py`
- Model schemas for risk assessment

---

## 🎯 How to Use This Manifest

### At Workspace Initialization:
1. **Read this file** to understand available capabilities
2. **Check `.suite6-config.json`** for workspace-specific features
3. **Explore `foundation/logic/`** for reasoning engines
4. **Review `intelligence/`** for learning systems
5. **Check `ops/scripts/`** for automation tools

### When Solving Problems:
1. **Check if Bayesian reasoning applies** - Use for uncertainty, risk, evidence combination
2. **Check if formal logic applies** - Use universal kernel for strict rule enforcement
3. **Check if learning data exists** - Query `memory_index.json` for patterns
4. **Check if context is available** - Review `context-memory/sessions/` for session history

### Before Implementing:
1. **Don't reinvent probabilistic reasoning** - Use `probabilistic_engine.py`
2. **Don't use naive heuristics** - Prefer Bayesian inference when handling uncertainty
3. **Don't ignore learning data** - Check `learning/` for existing solutions
4. **Don't skip governance** - Validate against `rule-registry.json`

---

## 🔍 Quick Capability Lookup

**Need to:**
- **Store a lesson/insight?** → `python3 agents/cursor/cursor_memory_client.py write "content" --kind lesson`
- **Search past solutions?** → `python3 agents/cursor/cursor_memory_client.py search "query"`
- **Check memory health?** → `python3 agents/cursor/cursor_memory_client.py health`
- **Inject context?** → `python3 agents/cursor/cursor_memory_client.py inject "task"`
- **Assess risk?** → `foundation/logic/probabilistic_engine.py`
- **Combine evidence?** → Bayesian weighted ensemble
- **Score confidence?** → Temperature-calibrated Bayesian
- **Enforce rules?** → `foundation/logic/universal-kernel.md`
- **Learn from outcomes?** → `learning/auto_calibrator.py`
- **Remember context?** → `intelligence/context-memory/`
- **Extract patterns?** → `ops/scripts/process_learnings.sh`
- **Structured reasoning?** → `intelligence/reasoning/cursor-native-reasoning.md`
- **Multi-modal reasoning?** → `/reasoning` command
- **Heavy implementation?** → `/forge` command

---

## 📝 Capability Self-Check

**Before claiming "I don't have X":**

```bash
# 1. Check foundation
ls foundation/logic/

# 2. Check intelligence
ls intelligence/

# 3. Check if script exists
find ops/scripts/ -name "*$KEYWORD*"

# 4. Check learning data
cat ops/logs/memory_index.json | grep "$TOPIC"

# 5. Check context history
ls intelligence/context-memory/sessions/
```

---

## 🚀 Integration Patterns

### Pattern 1: Probabilistic Assessment
```python
# DON'T: Use naive thresholds
if message_count > 3:
    return True

# DO: Use Bayesian reasoning
from foundation.logic.probabilistic_engine import CursorProbabilisticEngine
engine = CursorProbabilisticEngine()
assessment = engine.assess_file_compliance_risk(...)
return assessment.probability > engine.get_threshold('medium_risk')
```

### Pattern 2: Evidence Combination
```python
# DON'T: Simple average
confidence = sum(scores) / len(scores)

# DO: Weighted Bayesian ensemble
evidence_list = [
    Evidence("signal_1", value=0.8, weight=0.3, source="detector"),
    Evidence("signal_2", value=0.6, weight=0.5, source="analyzer")
]
confidence = engine._weighted_combination(evidence_list)
calibrated = engine._apply_temperature_scaling(confidence, temperature=1.0)
```

### Pattern 3: Learning Integration
```python
# DON'T: Fixed thresholds
THRESHOLD = 0.7  # Never changes

# DO: Self-calibrating
engine.record_outcome(decision_id, outcome='too_strict')
optimized_temp = engine.optimize_temperature(target_ece=0.05)
# Threshold automatically adjusts based on feedback
```

---

## 📚 Documentation Hierarchy

1. **This file (CAPABILITIES.md)** - What exists
2. **README.md** - How to access
3. **Component files** - How to use specific capabilities
4. **`.suite6-config.json`** - What's enabled in this workspace

---

## ✅ Capability Verification

**To verify all systems are operational:**
```bash
cd ~/Dropbox/Cursor\ Governance/GlobalCommands
./ops/scripts/verify-setup-alignment.sh
```

**Expected output**: 7/7 tests passed

---

## 🔄 Version & Updates

**Current Version**: Suite 6 v6.0.0  
**Last Updated**: 2025-11-08  
**Maintained By**: Igor Beylin  

**Change Log**:
- 2025-11-08: Initial capabilities manifest created
- Bayesian probabilistic engine documented
- Intelligence systems cataloged
- Integration patterns defined

---

## 🎯 Success Metrics

**A well-integrated AI agent should:**
- ✅ Know about Bayesian engine before being asked
- ✅ Use probabilistic reasoning for uncertainty
- ✅ Check learning data before solving known problems
- ✅ Reference context-memory for session continuity
- ✅ Apply reasoning frameworks systematically
- ✅ Self-calibrate based on feedback

**Signs of poor integration:**
- ❌ Claims "I don't have X" when X exists in foundation/
- ❌ Uses naive thresholds instead of Bayesian reasoning
- ❌ Doesn't check learning/ for existing solutions
- ❌ Forgets context between sessions
- ❌ Reinvents existing capabilities

---

**Read this file at every workspace initialization to maintain self-awareness of available capabilities!**

