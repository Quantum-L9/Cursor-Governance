# Cloud smoke receipt (Wave 4)

Date: 2026-08-12

| Probe | Result |
|---|---|
| `GET https://memory.quantumaipartners.com/graphiti/health` | 200 |
| HTTPS MCP `initialize` on `/graphiti/mcp` (no trailing slash) | 200 + protocol result |
| Token rotation | See TOKEN_ROTATION_RECEIPT.md |
| `make claude-env` | PASS |
| `make agents-env` / peer bindings | PASS |
| `make peer-execution-conformance` | PASS |
| `make pr-check` | PASS |

Anthropic account paste still uses WIP triad placeholders; live values stay in UI only.
