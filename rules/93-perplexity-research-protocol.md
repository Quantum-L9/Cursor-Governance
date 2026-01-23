# Perplexity Research Protocol (L9)

## 🔒 MANDATORY: Docs-First, Perplexity-Second

**RULE:** Before ANY Perplexity research query, you MUST:

1. **READ available @DOCS first** — Check Cursor's indexed docs for the topic
2. **IDENTIFY remaining gaps** — What the docs DON'T cover
3. **ONLY THEN query Perplexity** — To bridge the REMAINING gap

---

## Research Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: CHECK INDEXED @DOCS                                 │
│ ─────────────────────────────────────────────────────────── │
│ Read available docs in Cursor's indexed collection          │
│ Use firecrawl_scrape on official doc URLs if needed         │
│ Extract: API interfaces, patterns, code examples            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: IDENTIFY GAPS                                       │
│ ─────────────────────────────────────────────────────────── │
│ What questions remain UNANSWERED by official docs?          │
│ What production patterns are NOT in official docs?          │
│ What L9-specific integration needs custom research?         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: PERPLEXITY SUPERPROMPT (gaps only)                  │
│ ─────────────────────────────────────────────────────────── │
│ Use deep_research tool                                      │
│ Frontier superprompt format                                 │
│ Request: "Top Frontier AI Lab, enterprise-grade,            │
│          production-ready, L9 repo aligned quality!"        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: SAVE + ANALYZE                                      │
│ ─────────────────────────────────────────────────────────── │
│ Save query → agents/cursor/perplexity_research_queries/     │
│ Save results → agents/cursor/perplexity_research_results/   │
│ Run /analyze_evaluate on results                            │
│ Report inline executive summary                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Superprompt Quality Requirements

Every Perplexity query MUST include this quality gate:

```
### QUALITY REQUIREMENTS
- Top Frontier AI Lab, enterprise-grade, production-ready code
- L9 repo aligned: async/await, structlog, Pydantic v2, type hints
- Zero placeholders — complete implementations only
- Error handling with specific exceptions
- DORA compliance patterns where applicable
```

---

## File Locations

| Artifact | Location |
|----------|----------|
| Query logs | `agents/cursor/perplexity_research_queries/{date}-{topic}.md` |
| Research results | `agents/cursor/perplexity_research_results/{date}-{topic}/` |
| Analysis reports | `agents/cursor/perplexity_research_results/{date}-{topic}/ANALYZE-EVALUATE-REPORT.md` |

---

## What @DOCS Cover (Example Sources)

| Source | What It Covers | Gaps |
|--------|---------------|------|
| LangGraph docs | API, interfaces, basic patterns | Production issues, real incidents |
| PostgreSQL docs | SQL, VACUUM, config params | Connection pooling issues, checkpoint workloads |
| LangChain docs | Integrations, tools | Multi-tenant patterns, L9-specific |

---

## What Perplexity Bridges

| Gap Type | Perplexity Strength |
|----------|-------------------|
| Production incidents | GitHub issues, forum posts |
| Real-world patterns | Blog posts, case studies |
| Current best practices | 2025-2026 articles |
| Connection pool exhaustion | Documented incidents |
| Migration strategies | Community solutions |

---

## Anti-Patterns

❌ **DON'T:** Run Perplexity without checking @DOCS first
❌ **DON'T:** Ask Perplexity for basic API information (it's in docs)
❌ **DON'T:** Skip saving queries and results
❌ **DON'T:** Accept non-production-grade code

✅ **DO:** Read official docs thoroughly first
✅ **DO:** Use Perplexity only for production patterns and gap-bridging
✅ **DO:** Always request frontier-grade, L9-aligned code
✅ **DO:** Save and analyze all research artifacts

---

## Example: Good vs Bad

### ❌ BAD Query (Docs already cover this)
```
"What is the BaseCheckpointSaver interface in LangGraph?"
```
→ This is in official docs. Don't waste Perplexity.

### ✅ GOOD Query (Bridges gap)
```
"What are the production incidents and solutions for AsyncPostgresSaver 
connection pool exhaustion in LangGraph 1.0+? Include retry patterns 
and pool health monitoring used by production deployments in 2025-2026."
```
→ This is NOT in official docs. Use Perplexity.

---

## Version

- Rule version: 1.0.0
- Created: 2026-01-20
- Author: Igor Beylin
