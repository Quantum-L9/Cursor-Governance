# RB-LIN-001 - Linear Integration for Cursor

| Field | Value |
|---|---|
| Runbook ID | RB-LIN-001 |
| Version | 1.0.0 |
| Owner | Quantum-L9 |
| Target repo | `Quantum-L9/Cursor-Governance` |
| Blast radius | Local: `.cursor/mcp.json`, `.cursor/rules/`, `scripts/`. Remote (Path B only): Linear workspace + Cursor org integration settings. |
| Reversibility | Path A: full, under 1 minute. Path B: full, requires disconnect in two dashboards. |
| Secrets touched | Optional Linear PAT (fallback transport only). None for OAuth path. |
| Est. duration | Path A: 5 min. Path B: 15 min. |

---

## 1. Objective

Give Cursor Agent first-class access to Linear so that issue context is
*queried* rather than pasted, and so governance findings can be filed as
issues without leaving the IDE.

Explicitly out of scope: using Linear as a memory or knowledge store. That
role belongs to `l9-graphiti-memory`. Linear is the work queue and the
audit record, not the recall layer.

## 2. Triggers

Run this runbook when:

1. Setting up a new workstation or dev container for `Cursor-Governance`.
2. Onboarding a collaborator who needs issue access from the IDE.
3. Linear MCP tools stop appearing in Cursor's tool list.
4. Rotating a Linear personal API key.
5. Deciding whether to enable Path B delegation for a wave.

## 3. Preconditions

- [ ] Cursor installed and updated; Agent mode available.
- [ ] A Linear workspace you can authorize (OAuth consent required).
- [ ] `node` and `npx` on PATH (needed only for the `mcp-remote` fallback).
- [ ] Repo cloned locally; you are on a branch, not directly on `main`.
- [ ] For Path B only: Cursor **Pro or Ultra**, and you are a Cursor **admin**.

**Stop condition.** If you are not a Cursor admin, Path B cannot be
completed. Do Path A only and hand Path B to an admin.

## 4. Procedure

### 4.1 Automated (preferred)

Paste the contents of `START-HERE-PROMPT.md` into Cursor Agent. It executes
`AGENT_TASK.md` and self-validates against Section 5 of this runbook.

### 4.2 Manual - Path A, Linear MCP

Preferred transport is the native remote server. No PAT, no npx subprocess.

1. Open Cursor Settings (`Ctrl/Cmd + Shift + J`), select **MCP** / **Tools & MCP**.
2. Either search for **Linear** in Cursor's list of trusted MCP servers and
   install with one click, or add the server manually.
3. For manual project-scoped setup, merge `templates/mcp.linear.json` into
   `.cursor/mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "linear": {
      "url": "https://mcp.linear.app/mcp"
    }
  }
}
```

4. Cursor will show **Needs login**. Click it and complete the OAuth flow in
   the browser. Choose the workspace containing your governance team.
5. Return to Settings and click **refresh tools** on the Linear server.
   Tools should populate. If the server shows zero tools, it is not
   authorized yet.
6. Switch the chat to **Agent** mode. MCP tools are unavailable in other modes.

**Fallback transport.** If your Cursor build does not support remote
streamable-HTTP MCP, use the `mcp-remote` bridge instead:

```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.linear.app/mcp"]
    }
  }
}
```

The legacy SSE endpoint `https://mcp.linear.app/sse` also still works with
older clients. Prefer `/mcp` when you have the choice.

**PAT transport (last resort).** Some third-party Linear MCP servers
authenticate with a personal API key instead of OAuth. If you must use one:
generate the key in Linear under **Settings > Account > Security & access >
Personal API keys**, then supply it via environment, never inline in a
tracked file. See `templates/env.linear.example`.

### 4.3 Manual - Path B, Cloud Agent delegation

Only proceed if Section 6.4 CI preconditions are satisfied.

1. Go to the Cursor integrations page in the Cursor dashboard.
2. Click **Connect** next to Linear.
3. Connect your Linear workspace and select the team.
4. Click **Authorize**.
5. Complete remaining Cloud Agent setup in Cursor:
   - connect a repository provider and select a default repository
   - enable usage-based pricing
   - confirm privacy settings
6. Test by assigning an issue to `@Cursor`, or mentioning `@Cursor` in a
   comment. Cursor analyzes the issue and kicks off a background agent,
   then opens a pull request and posts progress back to the issue.

### 4.4 Repo integration

1. Copy `.cursor/rules/linear-workflow.mdc` into the repo's `.cursor/rules/`.
   This teaches the agent your issue conventions so it files consistent,
   traceable issues instead of freeform ones.
2. Do **not** modify `CANONICAL_LAW.md`, `ORG_INVARIANTS.yaml`, `CODEOWNERS`,
   or anything under `.claude/hooks/` as part of this runbook.
3. Commit `.cursor/mcp.json` and the rule. Both are non-secret and should be
   shared. Never commit a PAT.

## 5. Validation

Setup is complete only when all of the following hold.

1. Cursor Settings shows the Linear server as connected with a non-zero tool count.
2. In Agent mode, the prompt `List my open Linear issues assigned to me. Use MCP tools.`
   returns real issue identifiers.
3. The agent can read a specific issue by identifier and summarize it.
4. The agent can create a test issue, and that issue is visible in Linear's web UI.
5. `git status` shows no untracked or modified secret-bearing file.
6. `./scripts/verify-linear-mcp.sh` exits 0.
7. Path B only: assigning a throwaway issue to `@Cursor` produces a run
   visible in the Cursor agents dashboard.

Delete the test issue from step 4 when done.

## 6. Known failure modes

| # | Symptom | Likely cause | Action |
|---|---|---|---|
| 6.1 | Server listed, zero tools | OAuth not completed | Click **Needs login**, authorize, then refresh tools |
| 6.2 | Agent says it has no Linear access | Chat is not in Agent mode | Switch to Agent mode; MCP tools are Agent-only |
| 6.3 | `npx` fallback hangs on first run | `mcp-remote` downloading, or browser callback blocked | Run the npx command once in a terminal to complete auth, then restart Cursor |
| 6.4 | Tools appear then vanish after restart | Config at wrong path | Must be `.cursor/mcp.json`, not `.cursor/rules/mcp.json` |
| 6.5 | Path B: nothing happens on assign | Integration silently dropped; no default repo set | Disconnect and reconnect Linear on both sides; verify Background Agents has a default repository |
| 6.6 | Path B: agent ignores your hooks | Cloud agent runs outside your machine | Enforce gates in `.github/workflows`, not only in `.claude/hooks` and `Makefile` |
| 6.7 | Wrong workspace's issues appear | Authorized the wrong Linear org | Revoke in Linear, re-authorize, select correct workspace |
| 6.8 | 401 after weeks of working | PAT rotated or revoked | Re-run Section 8 |

### Path B CI precondition

Before enabling Path B, confirm that the checks enforced locally by
`Makefile` targets and `.claude/hooks/` are *also* enforced in
`.github/workflows`. A cloud agent bypasses local hooks entirely. If your
governance gates only exist locally, Path B punches a hole in them.

## 7. Rollback

Path A, under one minute:

1. Remove the `linear` block from `.cursor/mcp.json`.
2. Delete `.cursor/rules/linear-workflow.mdc`.
3. Restart Cursor; confirm the server no longer appears under Tools & MCP.
4. In Linear, revoke the Cursor MCP OAuth grant under **Settings > Account >
   Security & access**.
5. If a PAT was used, delete it in Linear and remove it from your shell
   profile or `.env.local`.

Path B:

6. In the Cursor dashboard integrations page, disconnect Linear.
7. In Linear, **Settings > Integrations > Cursor**, remove the integration.
8. Confirm no new runs appear in the Cursor agents dashboard.

## 8. Key rotation (PAT transport only)

1. Generate a new key in Linear: **Settings > Account > Security & access >
   Personal API keys > New API key**. Scope to the minimum needed; avoid
   Full Access unless a tool demands it.
2. Update `.env.local` only. The secret exists in exactly one place.
3. Restart Cursor. Environment is read at server launch, not per request.
4. Revoke the old key in Linear and confirm tools still resolve.

## 9. Division of labour

Keep the boundaries explicit so this does not duplicate existing systems.

- `l9-graphiti-memory` - temporal recall. What was learned and when.
- Linear - commitment state. What is owed, by whom, in what status, did it ship.
- Git/GitHub - code truth. What actually changed.
- `Cursor-Governance` policies - what is permitted.

Linear's value here is that unresolved work stops being invisible. The rule
worth adopting: if it is not an issue, it does not exist.

## 10. Security notes

- OAuth transport is preferred precisely because there is no long-lived
  secret on disk.
- `.cursor/mcp.json` is committed and therefore an attack surface. An agent
  or a bad PR can add a server. Consider a `beforeMCPExecution` hook that
  validates the server list against an allowlist before any MCP call runs.
- Linear issues may contain customer data. Any MCP server you connect can
  read them. Prefer the official server over third-party bridges.
- Path B sends repository context to Cursor's cloud. Confirm privacy
  settings during setup and check them against `SECURITY.md`.

## 11. Change log

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-13 | Initial runbook. Path A + Path B, rollback, rotation. |
