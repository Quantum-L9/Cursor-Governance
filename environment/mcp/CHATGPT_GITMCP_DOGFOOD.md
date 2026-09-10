# ChatGPT GitMCP dogfood

Temporary **read/search reconnaissance** over the public Cursor-Governance repository. It does not replace `environment/mcp/master.mcp.json`, does not activate the Program Execution ChatGPT adapter, and does not grant write or execution authority.

## Connection target

```text
https://gitmcp.io/Quantum-L9/Cursor-Governance
```

## ChatGPT prerequisites

- use ChatGPT web
- workspace/developer-mode access sufficient to create a custom MCP app
- keep the app in **Dev/draft** during dogfooding
- authentication: **none** for GitMCP

## Human setup path

UI wording may drift. The steps are:

1. Enable Developer Mode if not already enabled.
2. Apps -> Create custom app/MCP connector.
3. Name: `Cursor Governance - GitMCP`.
4. MCP endpoint: `https://gitmcp.io/Quantum-L9/Cursor-Governance`.
5. Authentication: none / no auth.
6. Scan Tools.
7. Confirm the scan exposes documentation fetch/search and code-search capability.
8. Create/save as a Dev/draft app.
9. Open a fresh chat and select or @mention the app for each message that needs new repository data.

Do not publish the app to the workspace during the first dogfood pass.

## First-pass acceptance prompts

### A. Canonical authority resolution

```text
Use Cursor Governance - GitMCP.
Find the canonical authority order for changes to Cursor-Governance.
Resolve conflicts between CANONICAL_LAW.md, AGENTS.md, invariants, ADRs,
README material, WIP, and archived copies. Cite the live source paths.
```

PASS if canonical live sources are selected without treating WIP/archive as peers.

### B. Skill resolution

```text
Use Cursor Governance - GitMCP.
Find the live GAR/global architect skill, read its canonical skill source,
identify its dependencies and activation contract. Do not use archived or WIP copies.
```

PASS if the live `skills/.../SKILL.md` path is found and archived copies are rejected.

### C. Program Execution ChatGPT seam

```text
Use Cursor Governance - GitMCP.
Find the canonical Program Execution ChatGPT adapter.
Explain its current provider type, authority model, dormant blocker,
and whether it is itself an MCP server.
```

PASS only if it identifies the current `manual_handoff` worker-host adapter and does **not** falsely claim it is the MCP server.

### D. MCP ownership seam

```text
Use Cursor Governance - GitMCP.
Find the canonical MCP configuration owner and explain how MCP configuration
is projected across Cursor, Claude Code, and cloud adapters.
```

PASS if `environment/mcp/master.mcp.json` and its current ownership model are found.

### E. Wiring owner

```text
Use Cursor Governance - GitMCP.
Find the canonical owner for wiring a new capability into the repository and
trace the source-first rule from owner to consumer. Ignore deprecated wiring paths.
```

PASS if the live wiring law/owner is resolved from canonical sources.

## Observation log

| # | Task | Correct canonical source? | WIP/archive avoided? | Hallucination? | Missing capability | Native MCP candidate |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | | | |
| 10 | | | | | | |

Dogfood is complete when 10 representative requests have been run and failures stabilize, or a repeated limitation clearly requires a first-party tool rather than better repository documentation.
