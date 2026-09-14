# AGENT_TASK - Linear MCP setup (Path A)

Execute all steps. Stop and report if a precondition fails.

## Step 1 - Preflight

- Confirm repo root contains `AGENTS.md` and `ORG_INVARIANTS.yaml`. If not,
  stop: wrong directory.
- Confirm current branch is not `main`. If it is, create
  `chore/linear-mcp-setup` and switch to it.
- Record whether `.cursor/mcp.json` already exists and print its current
  server names. Do not overwrite existing servers.

## Step 2 - Merge MCP config

- If `.cursor/mcp.json` does not exist, create it from
  `linear-cursor-pack/templates/mcp.linear.json`.
- If it exists, merge the `linear` key into the existing `mcpServers` object.
  Preserve every existing server verbatim. Preserve formatting and key order
  where practical.
- Verify the file parses as valid JSON after the edit.
- Confirm the path is exactly `.cursor/mcp.json` (a common failure is
  nesting it under `.cursor/rules/`).

## Step 3 - Secret hygiene

- Ensure `.gitignore` contains `.env.local`. Add it if missing.
- Grep the working tree for `lin_api_` and report any hit as a blocking
  finding. Do not commit if found.
- Do not create any file containing a Linear key. OAuth needs none.

## Step 4 - Install the workflow rule

- Copy `linear-cursor-pack/.cursor/rules/linear-workflow.mdc` to
  `.cursor/rules/linear-workflow.mdc`.
- If a rule with that name exists, diff and report rather than overwriting.

## Step 5 - Install verification scripts

- Copy `scripts/verify-linear-mcp.sh` and `scripts/verify-linear-mcp.ps1`
  into the repo's `scripts/` directory.
- Mark the `.sh` executable.

## Step 6 - Makefile targets

- If a `Makefile` exists, append these targets only if absent. Match the
  file's existing style and tab indentation.

```
linear-verify:
	./scripts/verify-linear-mcp.sh

linear-rollback:
	@echo "See linear-cursor-pack/RUNBOOK.md Section 7"
```

## Step 7 - Validate

- Run `./scripts/verify-linear-mcp.sh` and report output.
- Confirm `git status` shows only: `.cursor/mcp.json`, the new rule, the new
  scripts, and possibly `.gitignore` and `Makefile`.
- Do not commit or push unless I explicitly ask.

## Step 8 - Report

Output a table of file, action taken, and why. Then state:

1. The single command for me to run.
2. The single manual step only I can do (the OAuth login click).
3. Any blocking findings from Step 3.

## Prohibitions

- Do not touch `CANONICAL_LAW.md`, `ORG_INVARIANTS.yaml`, `CODEOWNERS`,
  `SECURITY.md`, `.claude/settings.json`, or `.claude/hooks/**`.
- Do not enable Cursor cloud agents or usage-based pricing.
- Do not install third-party Linear MCP bridges. Official server only.
- Do not create Linear issues during setup except one clearly-named test
  issue, and only if I ask you to validate step 4 of Section 5.
