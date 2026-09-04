# Cursor adapter — thin binding over the shared ops/ brain

First-class adapter for the Cursor IDE surface (`agent_id: cursor` in
[`../../agent_registry.yaml`](../../agent_registry.yaml)). It binds the shared
capability that already lives in `ops/`; it owns none of it
(`CANONICAL_LAW.md` §2.1, [`../ADAPTER_CONTRACT.md`](../ADAPTER_CONTRACT.md)).

Unlike the hosted Claude Code surfaces, Cursor runs on a persistent machine:
there is no ephemeral-sandbox story, no per-container governance clone, and no
setup.bootstrap chain. Activation is the standing wiring:

| Plane | Mechanism |
|---|---|
| SessionStart | `~/.cursor/hooks.json` → `~/.cursor/hooks/session-start-bootstrap.sh` (installed from [`ops/hooks/session_start_bootstrap.sh`](../../../../ops/hooks/session_start_bootstrap.sh)) |
| Rules / skills / commands | `l9-governance` local plugin at `~/.cursor/plugins/local/l9-governance` |
| Reference plane | workspace `.cursor-commands` → `$HOME/.cursor-governance` (consumers only) |
| Memory | Graphiti front door (`GRAPHITI_MCP_URL`) — see [`mcp.template.json`](mcp.template.json) |
| Receipt | `~/.l9/cursor/bootstrap-state.json` (schema `l9.cursor-bootstrap.v1`) |

## Install / verify

```bash
make cursor-install WS="$(pwd)"        # wire + write the receipt
make cursor-install-check WS="$(pwd)"  # read-only verify (writes bootstrap-check.json)
```

Or directly: `bash environment/agents/adapters/cursor/install.sh --workspace <git-root>`.

`install.sh` refuses `--workspace $HOME` — a `$HOME` workspace is how a
foreign-surface receipt got reported as session state (see
`WIP/9-2-26/cursor-remediation/TECH_DEBT.md`).

## What this adapter MUST NOT do

- Call any `claude-code/` installer, or read/write `~/.l9/claude/*`.
- Carry credentials or a second secret resolver (broker is retired).
- Own hydrate, receipt-expiry, or autonomy logic — those are `ops/scripts/`
  (`classify_hydrate_state.py`, `claude_bootstrap_receipt.py --surface cursor`,
  `bootstrap_agent_environment.sh`).
- Add a second activation path beside the SessionStart hook (`AGENTS.md` §2).

## PATH and interpreter in agent shells

SessionStart prepends `/opt/homebrew/bin` (and `/usr/local/bin`) so `gh` and
brew-installed checkers resolve in hook subprocesses without per-command
prefixes. The Python interpreter for governed scripts is always the locked
venv — `"$HOME/.cursor-governance/.venv/bin/python"` — never system
`python3` (`AGENTS.md` §5). `ModuleNotFoundError: No module named 'yaml'`
means the wrong interpreter, not a missing dependency.

## Reading the receipt

```bash
"$HOME/.cursor-governance/.venv/bin/python" ops/scripts/claude_bootstrap_receipt.py --surface cursor --json
```

One reader, one expiry rule, for every surface. A receipt whose `workspace`
is not the session git root is `stale_other_surface` in the SessionStart
report — never a this-session fault.

The SessionStart banner contract is [`SESSION_START_SPEC.md`](SESSION_START_SPEC.md).
