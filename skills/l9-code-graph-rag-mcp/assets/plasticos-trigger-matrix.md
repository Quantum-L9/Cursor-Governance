# PlasticOS Code-Graph Trigger Matrix

**SSOT:** when to **read from the graph** vs **Grep/Read** vs **skip entirely**.  
**Skill:** `@.cursor-commands/skills/l9-code-graph-rag-mcp/`  
**Rule:** repo `.cursor/rules/87-plasticos-code-graph-rag.mdc`  
**GMP Phase 0:** run `code_graph_gmp_baseline.sh` when this matrix says **GRAPH REQUIRED**.

---

## Decision order (always cheapest first)

1. **AGENTS.md / rules / manifest / wiring scripts** — CI, module map, deps
2. **Grep / Read** — symbol, model name, or file path is known
3. **Code-graph structural MCP or CLI** — cross-module, importers, impact, unknown location
4. **Scoped semantic_search** — last resort; module name in query; never whole-repo

---

## When to READ from the graph

Use the graph when Grep/Read cannot answer the question without reading many files across modules.

| Question you need answered | Read from graph? | Tool / action |
|----------------------------|------------------|---------------|
| Where is `_find_or_create_partner` defined? (unknown) | **Yes** | `resolve_entity` → `get_entity_source` scoped to `plasticos_web_leads/` |
| Who imports `plasticos_intake`? | **Yes** | `list_module_importers` (`moduleSource`: module folder name) |
| What breaks if I change `PlasticosMaterialProfile`? | **Yes** | `analyze_code_impact` (`entityId` + `filePath` hint) |
| What breaks if I touch `plasticos_base`? | **Yes** | `list_module_importers` + `analyze_code_impact` on touched symbols |
| What's in `transaction.py`? | **No** | `Read` the file — skip graph |
| Find `plasticos.match.result` in one module | **No** | `Grep` in `plasticos_matching/` |
| CI / XML / manifest deps | **No** | Rules + `scripts/check_module_wiring.py` |
| What did we decide last week? | **No** | Graphiti / `memory-bank/` — not code-graph |

### Graph READ means

- **Structural tools only** in chat: `resolve_entity`, `get_entity_source`, `list_module_importers`, `list_entity_relationships`, `analyze_code_impact`, `list_file_entities`
- **CLI in GMP Phase 0:** `code_graph_gmp_baseline.sh` (zero chat tokens)
- **Never in chat:** `batch_index`, `index`, `get_graph`, `reset_graph`, unscoped `semantic_search`

---

## Path patterns → required action

| Path pattern | Phase 0 / pre-edit gate | Graph tools |
|--------------|-------------------------|-------------|
| `plasticos_base/**` | **GRAPH REQUIRED** — high risk | importers + impact on touched entities |
| `plasticos_security_base/**` | **GRAPH REQUIRED** — high risk | importers + impact |
| `plasticos_*/models/*.py` (Layer 1–2 shared models) | **GRAPH REQUIRED** | `analyze_code_impact` per model class |
| `plasticos_web_leads/**` (cross-module flow) | **GRAPH if symbol unknown** | scoped `resolve_entity` |
| `plasticos_*/views/*.xml`, `**/tests/**`, `docs/**` | **SKIP graph** | Grep/Read only |
| Single module, known file, no shared model | **SKIP graph** | Read/Grep |

### Known shared models (always impact-check before field/schema edits)

| Model `_name` | Class | File hint |
|---------------|-------|-------------|
| `plasticos.material.profile` | `PlasticosMaterialProfile` | `plasticos_material_profile/models/material_profile.py` |
| `plasticos.facility.profile` | `PlasticosFacilityProfile` | `plasticos_facility_profile/models/facility_profile.py` |
| `plasticos.transaction` | `PlasticosTransaction` | `plasticos_transaction/models/transaction.py` |
| `plasticos.intake` | `PlasticosIntake` | `plasticos_intake/models/intake.py` |
| `plasticos.offer` | `PlasticosOffer` | `plasticos_offer/models/offer.py` |
| `plasticos.match.result` | `PlasticosMatchResult` | `plasticos_matching/models/match_result.py` |

---

## GMP Phase 0 — CODE_GRAPH_BASELINE

**Trigger:** any locked TODO file matches **GRAPH REQUIRED** rows above.

```bash
export REPO_ROOT="/path/to/IB-Odoo_19"
export GOV_SKILLS="$HOME/Dropbox/Cursor Governance/GlobalCommands/skills/l9-code-graph-rag-mcp/scripts"
bash "$GOV_SKILLS/code_graph_gmp_baseline.sh" "$REPO_ROOT" \
  --run-id "gmp-YYYYMMDD-NNN" \
  --files plasticos_material_profile/models/material_profile.py
```

**Output:** `.cursor/code-graph-phase0-evidence.json` (gitignored, 4h TTL)

**Phase 0 exit line must include one of:**

- `CODE_GRAPH_BASELINE: COMPLETE`
- `CODE_GRAPH_BASELINE: SKIPPED (grep-only / known path)`
- `CODE_GRAPH_BASELINE: BLOCKED (index unhealthy — run code_graph_batch_index.sh)`

---

## Copy-paste prompts

**Known file — skip graph:**

```
Read plasticos_transaction/models/transaction.py — do not use code-graph.
```

**Shared model edit:**

```
GMP Phase 0: run code_graph_gmp_baseline.sh for plasticos_material_profile/models/material_profile.py.
Then analyze_code_impact for PlasticosMaterialProfile only.
```

**Unknown cross-module symbol:**

```
resolve_entity name=web_lead filePathHint=plasticos_web_leads — then get_entity_source. Scope: plasticos_web_leads/ only.
```

---

## Hook enforcement (automatic)

| Hook | Behavior |
|------|----------|
| `sessionStart` | Health check + inject this matrix path + `CODE_GRAPH_HEALTHY` |
| `preToolUse` (Write) | High-impact path without fresh evidence → **ask** to run baseline |
| `beforeMCPExecution` | Deny chat indexing / `get_graph`; **ask** on `semantic_search` |

Evidence file: `.cursor/code-graph-phase0-evidence.json`
