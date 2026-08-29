# RB-LIN-001 Sign-off Checklist

## Preconditions
- [ ] Cursor updated, Agent mode available
- [ ] Linear workspace identified and authorizable
- [ ] `node`/`npx` present (fallback transport only)
- [ ] Working on a non-`main` branch

## Path A - Linear MCP
- [ ] `linear` server merged into `.cursor/mcp.json` (correct path, valid JSON)
- [ ] Existing MCP servers preserved
- [ ] OAuth login completed; server shows non-zero tool count
- [ ] Tools refreshed in Cursor Settings
- [ ] Chat set to Agent mode
- [ ] `.cursor/rules/linear-workflow.mdc` installed
- [ ] `.env.local` present in `.gitignore`
- [ ] No `lin_api_` string anywhere in tracked files

## Validation
- [ ] Agent lists open issues assigned to me
- [ ] Agent reads a specific issue by identifier
- [ ] Agent creates a test issue, visible in Linear web UI
- [ ] Test issue deleted
- [ ] `./scripts/verify-linear-mcp.sh` exits 0

## Path B - Cloud Agent (optional, gated)
- [ ] Local gates confirmed mirrored in `.github/workflows`
- [ ] Cursor admin on Pro or Ultra
- [ ] Linear connected via Cursor integrations page, team selected
- [ ] Default repository set for Background Agents
- [ ] Usage-based pricing decision recorded
- [ ] Privacy settings reviewed against `SECURITY.md`
- [ ] Throwaway issue assigned to `@Cursor` produced a visible run

## Sign-off

| Field | Value |
|---|---|
| Operator | |
| Host | |
| Date | |
| Path(s) completed | |
| Deviations from runbook | |
