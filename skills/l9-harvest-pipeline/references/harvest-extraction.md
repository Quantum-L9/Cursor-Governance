<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-harvest-pipeline
layer: reference
role: harvest_extraction_protocol
tags: [l9, harvest, sed, extraction, dag]
owner: igor_beylin
status: active
version: 3.2.1
updated: 2026-06-06
dag: harvest-deploy-v1
dag_file: .cursor-commands/workflows/dags/harvest_deploy_dag.py
auto_chain: use-harvest
--- /SKILL_META ---
-->

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

## HARVEST TABLE FORMAT

Before extracting, catalog what you'll harvest:

```markdown
| # | Pattern | Source Lines | Target |
|---|---------|--------------|--------|
| 1 | `orchestrator.py` | 27-693 | `core/agents/bootstrap/orchestrator.py` |
| 2 | `models.py` | 702-828 | `core/agents/bootstrap/models.py` |
```

## EXTRACTION COMMANDS

Use `sed` to extract code blocks directly (removes the triple backtick lines):

```bash
sed -n '859,1453p' "source.md" | sed '1d' | sed '$d' > "harvested-files/1_semantic_discovery.py"
```

**Pattern:** `sed -n 'START,ENDp' "SOURCE" | sed '1d' | sed '$d' > "TARGET"`

## VERIFICATION

```bash
ls -la "harvested-files/" && wc -l "harvested-files/"*
```

## ANTI-PATTERNS

❌ **DON'T** manually type out code you see in the source
❌ **DON'T** regenerate code from memory
❌ **DON'T** "write" by composing the code yourself

✅ **DO** use `sed` to extract exact content
✅ **DO** verify with `ls -la` and `wc -l`

## GOVERNANCE REFERENCE

From `92-learned-lessons.mdc`:

> **🔴 CRITICAL: Copy Complete Code, Don't Rewrite**
> If code exists, COPY it. Rewriting existing code is a governance violation.

**Copying via tools = sed extraction. Use it.**
