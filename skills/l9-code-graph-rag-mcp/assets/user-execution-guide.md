# Code Graph RAG — User Execution Guide

Terminal-first workflow to **seed the graph once**, **verify health**, and **use MCP in Cursor without burning chat tokens**.

**Skill pack:** `@.cursor-commands/skills/l9-code-graph-rag-mcp/`  
**MCP server:** `@er77/code-graph-rag-mcp` v2.7.15+  
**Index cache:** `<repo>/.code-graph-rag/vectors.db` (gitignored)

---

## 1. One-time setup (already done on this Mac)

If you need to reinstall on another machine:

```bash
# Download latest release (cursor.directory "Add to Cursor" often 404s — use GitHub)
curl -sL -o /tmp/code-graph-rag-mcp.tgz \
  "https://github.com/er77/code-graph-rag-mcp/releases/download/v2.7.15/er77-code-graph-rag-mcp-2.7.15.tgz"

# User-local install (no sudo)
mkdir -p "$HOME/.local/code-graph-rag-mcp"
npm install --prefix "$HOME/.local/code-graph-rag-mcp" /tmp/code-graph-rag-mcp.tgz

# Verify
"$HOME/.local/code-graph-rag-mcp/node_modules/.bin/code-graph-rag-mcp" --version
```

**MCP config** (`~/.cursor/mcp.json`) — server entry `code-graph-rag` must point at your repo root. After editing, **reload MCP** in Cursor (Settings → MCP) or restart Cursor.

**Environment (recommended):**

| Variable | Value | Why |
|----------|-------|-----|
| `MCP_EMBEDDING_PROVIDER` | `memory` | No OpenAI key; use structural tools first |
| `MCP_TIMEOUT` | `800000` | Avoid first-call timeouts on large repos |

---

## 2. Set paths (every new terminal)

```bash
# PlasticOS repo — adjust if your clone path differs
export REPO_ROOT="$HOME/IB-Odoo_19 (LOCAL)/IB-Odoo_19"

# Governance scripts (Dropbox SSOT)
export GOV_SKILLS="$HOME/.cursor-governance/skills/l9-code-graph-rag-mcp/scripts"

# Optional overrides
export CODE_GRAPH_BIN="$HOME/.local/code-graph-rag-mcp/node_modules/.bin/code-graph-rag-mcp"
export BATCH_SIZE=100
```

Add `.code-graph-rag/` to repo `.gitignore` (one-time):

```bash
grep -q '.code-graph-rag/' "$REPO_ROOT/.gitignore" || \
  echo '.code-graph-rag/' >> "$REPO_ROOT/.gitignore"
```

---

## 3. Seed the graph (CLI only — zero chat tokens)

**Never ask the agent to `batch_index` in chat.** Run this in Terminal:

```bash
cd "$REPO_ROOT"
bash "$GOV_SKILLS/code_graph_batch_index.sh" "$REPO_ROOT"
```

Expected output (458 indexable files on PlasticOS after default excludes):

```
round  1: 100/458 files (21.8%) done=False
...
round  5: 458/458 files (100.0%) done=True
Index complete.
{ "healthy": true, "totals": { "entities": ~4700, "relationships": ~600, "files": 458 } }
```

**Time:** ~1–3 minutes. **Cost:** $0 LLM tokens.

### After large refactors (incremental)

Re-run the same script — it resumes incrementally:

```bash
bash "$GOV_SKILLS/code_graph_batch_index.sh" "$REPO_ROOT"
```

### Health check only

```bash
bash "$GOV_SKILLS/code_graph_health.sh" "$REPO_ROOT"
```

Exit `0` = healthy; exit `1` = empty or broken → run batch index.

### Manual single-tool probe (debug)

```bash
python3 "$GOV_SKILLS/code_graph_cli.py" get_graph_health "{}" "$REPO_ROOT"
python3 "$GOV_SKILLS/code_graph_cli.py" resolve_entity '{"name":"PlasticosOffer"}' "$REPO_ROOT"
```

---

## 4. Reload Cursor MCP

After seeding:

1. Cursor → **Settings → MCP**
2. Confirm `code-graph-rag` shows **green / connected**
3. If red: restart Cursor; check log at `/tmp/code-graph-rag-mcp/mcp-server-$(date +%Y-%m-%d).log`

---

## 5. Token-minimal agent usage

### Authority order (cheapest first)

1. **Rules + AGENTS.md** — CI, modules, invariants (already in context)
2. **Grep / Read** — when you know symbol or file path
3. **Code-graph structural MCP** — importers, impact, unknown cross-module location
4. **Scoped semantic_search** — last resort, always include module path

### Copy-paste prompts (scoped)

**Find symbol (known name — use grep, not graph):**

```
Grep for plasticos.match.result in plasticos_matching/ — do not use code-graph.
```

**Who imports a module:**

```
Use code-graph list_module_importers for plasticos_intake only.
Do not read full files. Do not semantic_search the whole repo.
```

**Before editing a shared model:**

```
Use code-graph analyze_code_impact for plasticos.material.profile field changes only.
Then grep/read the files it lists — max 2 files.
```

**Unknown location across modules:**

```
Use code-graph: resolve_entity for web_lead with filePathHint plasticos_web_leads,
then get_entity_source with minimal context. Scope: plasticos_web_leads/ only.
```

### Never in chat (CLI or skip)

| Tool | Why |
|------|-----|
| `batch_index`, `index`, `clean_index`, `reset_graph` | Run `code_graph_batch_index.sh` in Terminal |
| `get_graph` | Dumps huge graph into context |
| `detect_code_clones`, `jscpd_detect_clones` | Audit-only; massive output |
| `suggest_refactoring` | Extra LLM-style suggestions |
| Unscoped `semantic_search` | Burns tokens; always add module path |

---

## 6. What gets indexed (PlasticOS)

Default excludes (from server): `node_modules`, `.git`, `.code-graph-rag`, `tests/**`, `**/*.md`, `.venv`, `odoo-enterprise` if outside tree, etc.

**~458 files** indexed → **~4700 entities** (functions, classes, imports, relationships).

Not indexed: most markdown docs, test trees, build artifacts. Use **Grep/Read** for those.

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| MCP red in Cursor | Restart Cursor; verify `CODE_GRAPH_BIN` path in `mcp.json` |
| `healthy: false`, 0 entities | Run `code_graph_batch_index.sh` |
| `agent_busy` / timeout in chat | Don't index in chat; increase `MCP_TIMEOUT`; use CLI scripts |
| Node `EBADENGINE >=24` warning | v22 often works; upgrade Node later if crashes |
| Stale graph after big refactor | Re-run `code_graph_batch_index.sh` |
| Logs | `/tmp/code-graph-rag-mcp/mcp-server-YYYY-MM-DD.log` |

**Full reset (rare):**

```bash
rm -rf "$REPO_ROOT/.code-graph-rag"
bash "$GOV_SKILLS/code_graph_batch_index.sh" "$REPO_ROOT"
```

---

## 8. Memory layers (don't confuse)

| Layer | Use for |
|-------|---------|
| **code-graph** | Where in code, who imports, impact radius |
| **memory-bank/** (git) | Session resume, active task |
| **Graphiti** (VPS) | Decisions, constraints, cross-repo edges |
| **AGENTS.md / rules** | CI, Odoo patterns, module map |

Code-graph does **not** remember "what we decided last Tuesday."

---

## 9. Quick reference card

```bash
# Paths
export REPO_ROOT="$HOME/IB-Odoo_19 (LOCAL)/IB-Odoo_19"
export GOV_SKILLS="$HOME/.cursor-governance/skills/l9-code-graph-rag-mcp/scripts"

# Seed (once / after big changes)
bash "$GOV_SKILLS/code_graph_batch_index.sh" "$REPO_ROOT"

# Verify
bash "$GOV_SKILLS/code_graph_health.sh" "$REPO_ROOT"

# Then in Cursor: reload MCP → use scoped prompts from §5
```

---

## 10. Current machine status (2026-06-06)

IB-Odoo_19 graph was seeded via CLI:

- **healthy:** true  
- **entities:** 4708  
- **relationships:** 605  
- **files:** 458  

No further indexing needed until the next large refactor.
