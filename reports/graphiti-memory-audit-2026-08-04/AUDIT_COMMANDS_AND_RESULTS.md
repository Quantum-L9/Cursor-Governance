# AUDIT_COMMANDS_AND_RESULTS

Read-only. Secrets redacted throughout; the memory bearer was passed via env header and never printed. Repo scope: Quantum-L9/Cursor-Governance (runtime `/root/.cursor-governance` main@3c9ba5c; working `/home/user/Cursor-Governance` @1cccf49) and Quantum-L9/l9-graphiti-memory (@c0dd23b). Service: `l9-graphite-memory 2.2.0`.

| # | command (abridged) | env | exit | result / evidence |
|---|---|---|---|---|
| 1 | `uname -a; claude --version; whoami; ls -la /home/user /root` | host | 0 | Linux 6.18.5 x86_64; Claude 2.1.221; root; HOME=/root; cwd=/home/user; 14 repo clones present |
| 2 | `git -C <repo> rev-parse HEAD/branch` (both repos + /root/.cursor-governance) | host | 0 | CG working `claude/graphiti-memory-audit-0vnnuv@1cccf49`; l9-gm `…@c0dd23b`; runtime gov `main@3c9ba5c` |
| 3 | `env | grep -iE GRAPHITI\|L9_MEMORY\|MCP` (sanitized) | host | 0 | `L9_MEMORY_HTTP_URL=https://memory.quantumaipartners.com`, token set, agent_id=claude-code; `GRAPHITI_MEMORY_ENABLED` unset; `~/.cursor/graphiti.env` MISSING |
| 4 | `ls -la /home/user/.claude/skills; find / -name SKILL.md -path *graphiti*` | host | 0 | skills symlink→`/root/.cursor-governance/skills/*`; `l9-graphiti-memory` present; extra SKILL.md only inside l9-gm repo (not on Claude path) |
| 5 | `sha256sum` active vs working SKILL.md | host | 0 | identical `03f8885…` |
| 6 | read `.l9-managed-skills.json` | host | 0 | mode=symlink; `l9-graphiti-memory` listed |
| 7 | `curl -o/dev/null -w %{http_code} $BASE/{healthz,mcp,health}` | host | 0 | `/healthz`=200, `/mcp`=405 (POST-only), `/health`=404 |
| 8 | inspect `~/.claude.json` mcpServers/projects | host | 0 | `projects: []`; no `mcpServers` |
| 9 | `claude mcp list` | host | 0 | "No MCP servers configured" |
| 10 | read `environment/claude-code/mcp.template.json` | host | 0 | intended `l9-shared-memory` http server → `${L9_MEMORY_HTTP_URL}/mcp`, Bearer, alwaysLoad:true |
| 11 | read `/home/user/.claude/settings.json` | host | 0 | SessionStart=[session_start_claude_governance.sh, memory_prefetch.py]; Stop=[memory_writeback.py]; PreToolUse gate; env; skillOverrides |
| 12 | read `memory_prefetch.py`, `memory_client.py` | host | 0 | prefetch: `records=bundle.get('records') or bundle.get('hits') or []`; client: correct https guard, `/mcp`, `memory.*` tool names |
| 13 | **live MCP probe** via `memory_client`: tools/list, initialize, health, hydrate, search | host | 0 | server `l9-graphite-memory 2.2.0`; tools=`memory.*`; **health: sqlite healthy, records=11**, projection healthy, circuit closed; **hydrate(cursor-governance).sections=[]**; **search(cursor-governance).hits=[]** (all strategies/stores succeeded) |
| 14 | per-namespace search (10 candidates) | host | 0 | `cursor-governance, Cursor-Governance, igor-workspace, claude-code, global, default, workspace, l9, quantum-l9, l9-graphiti-memory` → **all hits=0** |
| 15 | hydrate keys check | host | 0 | keys include `sections`; **no `records`, no `hits`** → confirms MEM-001 |
| 16 | grep server hydrate contract | host | 0 | `retrieval/budget.py:90` emits `{"sections":[...]}`; `contracts/receipts.py:176` `HydrationResult.sections` |
| 17 | read contract `default_namespaces`; `group_registry.yaml` | host | 0 | default `['cursor-governance']`; registry resolver order explicit_env→git_remote→path_hint (unused by prefetch) |
| 18 | attempt `memory.{stats,namespaces,list}` | host | 0 | `-32601 unknown tool` (governed surface has no namespace-inventory tool) |
| 19 | read validators | host | 0 | both check presence/parity only; never call the server or check MCP registry |
| 20 | `ps aux`/read `--mcp-config` file | host | 0 | runtime MCP set = {github, calendar, vercel, anthropic-meta×2}; **l9-shared-memory ABSENT** → RC2 |
| 21 | read session receipt | host | 0 | `{hydrated_records:0, status:prefetched, namespaces:[cursor-governance]}` → RC1 confirmed on-disk |
| 22 | `python3 -c import l9_graphite_memory` | host | 0 | not installed locally (by design; HTTP client is stdlib) |

No writes were issued to the memory service. No source, config, git, or remote mutation occurred.
