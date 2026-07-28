GMP-GRAPHITI complete. All phases ran read-only; signed report at reports/GMP-Report-GRAPHITI-20260630.md.

Verdict: CRITICAL
Graphiti's infrastructure is healthy but the MCP tool plane is dead — so it can neither read nor write. That's a BLOCKER-class failure → CRITICAL per the Phase-4 rule.

Health: healthy=false · liveness=true · tool_plane=false · circuit=closed Group: cursor-governance (registry, readonly=false) Blockers: 3 · Gaps: 3 · Misalignments: 3

The one root cause
The server responds 200 on /healthcheck but 404 on /, /mcp, and /mcp/. The tunnel is OPEN (port 8100), the LaunchAgent is loaded, the circuit is CLOSED, group resolution is correct, gate logic passes, and dry-runs build fine — but every real tool call (search, stats, write) returns HTTP 404. The Graphiti MCP server on the VPS is simply not serving the tool route.

🔴 Blockers (all one fix)
G6 tool plane 404 · G10 search 404 (both cursor-governance + igor-workspace) · G11 stats/Neo4j 404. All resolve by restoring the /mcp/ route on the VPS.
🟠 Gaps
G1 GRAPHITI_MCP_TOKEN=EMPTY (will 401 later if auth is enforced; not the current cause) · G13 WRITE_GATES=0 (intended default) · G15 no memory-bank/ scaffold in this workspace.
🟡 Misalignments
G5 (headline) server up but /mcp/ not serving tools · G8 editing clone origin is Quantum-L9/Cursor-Governance vs registry canonical cryptoxdog/Cursor-Governance (glob still matches) · G16 env missing MEMORY_DISTILL_TOKEN_BUDGET, extra GRAPHITI_SSH_KEYCHAIN_SERVICE (Keychain-backed secrets — explains why NEO4J_*/OPENAI_API_KEY aren't in the env file).
Same ground-truth deviation as before: the GMP's GOV="$HOME/.cursor-governance" is a logs dir; I diagnosed the real wired SSOT ($HOME/Dropbox/cursor governance/GlobalCommands) and documented it. Secrets reported only as SET/EMPTY/MISSING — no values printed. G12b (live round-trip) was correctly skipped since RUN_LIVE wasn't set.

Zero repo drift (Phase 5): SSOT porcelain unchanged (still the pre-existing 10), no e2e-test.json leftover, workspace untouched.

Smallest next action: restart the Graphiti MCP server on VPS 46.62.243.82 so /mcp/ serves the tool plane, then re-run graphiti_memory_client.py health until "healthy": true.
