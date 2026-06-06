---
name: l9-harvest-pipeline
description: Harvest code extraction (sed/DAG) and use-harvest deployment pipeline
disable-model-invocation: true
---

---
name: harvest
version: "3.2.0"
description: "Extract code from documents using sed — NEVER write/type code manually"
before_chain: rules
auto_chain: use-harvest
dag: harvest-deploy-v1
dag_file: .cursor-commands/workflows/dags/harvest_deploy_dag.py
---

# /harvest — Code Extraction via sed

**DAG-ENFORCED.** Execute the `harvest-deploy-v1` DAG.

## Absolute Rule

**sed ONLY.** Never use `Write`, `StrReplace`, or manually type code from documents. Use `grep -n` for boundaries, `sed -n` for extraction. Violation = governance breach.

## Usage

```
/harvest path/to/document.md              # Harvest from single doc
/harvest doc1.md doc2.md                  # Harvest from multiple docs
```

## Execution

Load and execute the DAG:

```python
from .cursor_commands.workflows.dags.harvest_deploy_dag import HARVEST_DEPLOY_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/harvest_deploy_dag.py`
- **CLI**: `python3 .cursor-commands/workflows/harvest_executor.py path/to/doc.md` (standalone alternative)
- **Next step**: `/use-harvest` after extraction completes

---
name: use-harvest
version: "2.0.0"
description: "TRIGGER ONLY — Invokes use_harvest_executor.py for deployment"
auto_chain: wire
dag_executor: .cursor-commands/workflows/use_harvest_executor.py
---

# /use-harvest — Deploy Harvested Code (v2.0.0)

## THIS IS A TRIGGER ONLY

`/use-harvest` invokes the Use-Harvest Executor DAG. All logic lives in the executor.

## INVOCATION

```bash
python3 .cursor-commands/workflows/use_harvest_executor.py path/to/harvested/
```

## WHAT THE DAG DOES (AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  READ-TABLE       │ Parse HARVEST_TABLE.md             │
├─────────────────────────────────────────────────────────┤
│  VERIFY-TARGETS   │ Check if targets exist (→ action)  │
├─────────────────────────────────────────────────────────┤
│  DEPLOY-FILES     │ cp to targets (NO manual rewrite)  │
├─────────────────────────────────────────────────────────┤
│  VALIDATE-SYNTAX  │ py_compile on deployed files       │
├─────────────────────────────────────────────────────────┤
│  WIRE-IMPORTS     │ Check __init__.py needs            │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — NO user confirmation gates
- **cp-based deployment** — Uses cp NOT manual rewrite
- **Action detection** — CREATE, REPLACE, or CREATE_DIR
- **Wire hints** — Identifies __init__.py updates needed
- **Auto-report** — Uses canonical report generator

## USAGE

```bash
# Deploy harvested files
python3 .cursor-commands/workflows/use_harvest_executor.py current_work/harvested/01-25-2026/Implementation/

# Check status
python3 .cursor-commands/workflows/use_harvest_executor.py --status

# Resume if interrupted
python3 .cursor-commands/workflows/use_harvest_executor.py --resume
```

## HARVEST_TABLE.md FORMAT

The executor reads this format:

```markdown
| # | Pattern | Source Lines | Target |
|---|---------|--------------|--------|
| 1 | `orchestrator.py` | 27-693 | `core/agents/bootstrap/orchestrator.py` |
| 2 | `models.py` | 702-828 | `core/agents/bootstrap/models.py` |
```

## NEXT STEP

After deployment completes, run:
```bash
python3 .cursor-commands/workflows/wire_executor.py {deployed_module}
```

Or use `/wire` to fix imports and exports.

> **DEPRECATED (v1.3):** The following section is from harvest2.md — superseded by harvest.md v3.2.0 above. Retained for reference.

---
name: harvest
version: "1.3.0"
description: "Harvest code from documents — READ source, WRITE to target, NO rewriting"
auto_chain: ynp
---

# /harvest — Pattern Harvesting

## WHAT IT DOES

Extract code blocks from source documents into target files.
**READ the source lines → WRITE to target file. That's it.**

---

## 🚨 CRITICAL RULE

**USE FILE TOOLS TO COPY CODE DIRECTLY.**

1. **Read** the source file at the exact line range
2. **Write** that content to the target file
3. **DO NOT TYPE THE CODE YOURSELF**

The Write tool IS copy-paste. Use it.

---

## INSTRUCTIONS

**Target folder or file:** `<TARGET>`

1. **Identify patterns/line range list** for complete files in source
2. **Locate filenames** from the source document headers (e.g., `**File**: filename.py`)
3. **For each pattern/file:**
   - Open `<TARGET>` source document
   - Go to the line range listed
   - Copy the code block (inside the triple backticks)
   - Paste into target file using same filename in `harvested-files/` subfolder of TARGET folder

---

## HARVEST TABLE FORMAT

Before extracting, catalog what you'll harvest:

```markdown
| # | Pattern | Source | Lines | Target |
|---|---------|--------|-------|--------|
| 1 | `ClassName` | doc.md | 100-250 | `1_file.py` |
| 2 | `AnotherClass` | doc.md | 300-450 | `2_file.py` |
```

Then execute the extractions.

---

## EXTRACTION COMMANDS

Use `sed` to extract code blocks directly (removes the triple backtick lines):

```bash
# Extract lines 859-1453 from source, strip first/last lines (backticks), write to target
sed -n '859,1453p' "source.md" | sed '1d' | sed '$d' > "harvested-files/1_semantic_discovery.py"

# Another example
sed -n '2342,2481p' "source.md" | sed '1d' | sed '$d' > "harvested-files/7_benchmarks.py"

# And another
sed -n '2492,2564p' "source.md" | sed '1d' | sed '$d' > "harvested-files/8_observability.py"
```

**Pattern:** `sed -n 'START,ENDp' "SOURCE" | sed '1d' | sed '$d' > "TARGET"`

- `sed -n 'START,ENDp'` — extracts lines START to END
- `sed '1d'` — removes first line (opening triple backticks)
- `sed '$d'` — removes last line (closing triple backticks)

---

## VERIFICATION

After extraction, verify files exist with content:

```bash
ls -la "harvested-files/" && wc -l "harvested-files/"*
```

Expected output shows files with line counts:

```
-rw-r--r--  1 user  staff  21271 Jan 25 10:36 1_semantic_discovery.py
-rw-r--r--  1 user  staff   8596 Jan 25 10:36 2_anthropic_tool_search.py
...
     593 harvested-files/1_semantic_discovery.py
     262 harvested-files/2_anthropic_tool_search.py
```

---

## COMPLETE EXAMPLE

**Source:** `Tool Discovery-2.md`
**Target folder:** `Tool Discovery/harvested-files/`

### Step 1: Identify patterns

| # | Pattern | Lines | Target |
|---|---------|-------|--------|
| 1 | `DynamicToolDiscoveryService` | 859-1453 | `1_semantic_discovery.py` |
| 2 | `AnthropicToolSearchAdapter` | 1465-1728 | `2_anthropic_tool_search.py` |
| 3 | `PromptCachingStrategy` | 1740-1977 | `3_prompt_caching.py` |

### Step 2: Execute extractions

```bash
sed -n '859,1453p' "Tool Discovery-2.md" | sed '1d' | sed '$d' > "harvested-files/1_semantic_discovery.py"
sed -n '1465,1728p' "Tool Discovery-2.md" | sed '1d' | sed '$d' > "harvested-files/2_anthropic_tool_search.py"
sed -n '1740,1977p' "Tool Discovery-2.md" | sed '1d' | sed '$d' > "harvested-files/3_prompt_caching.py"
```

### Step 3: Verify

```bash
ls -la "harvested-files/" && wc -l "harvested-files/"*
```

---

## ANTI-PATTERNS

❌ **DON'T** manually type out code you see in the source
❌ **DON'T** regenerate code from memory
❌ **DON'T** "write" by composing the code yourself
❌ **DON'T** give "instructions" to copy-paste — just DO IT with tools

✅ **DO** use `sed` to extract exact content
✅ **DO** verify with `ls -la` and `wc -l`
✅ **DO** strip backtick lines with `sed '1d' | sed '$d'`

---

## LESSON LEARNED (2026-01-25)

> "Don't write them, PASTE them. The Write tool IS paste.
> Read the lines, Write to file. That simple.
> Stop being a speed bump on the dumbest thing."

---

## GOVERNANCE REFERENCE

From `92-learned-lessons.mdc`:

> **🔴 CRITICAL: Copy Complete Code, Don't Rewrite**
> If code exists, COPY it. Rewriting existing code is a governance violation.

**Copying via tools = sed extraction. Use it.**

→ **Auto-chains to /ynp**
