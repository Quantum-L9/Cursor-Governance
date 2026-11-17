---
name: Modes and plane bind
overview: Add two thin slash commands that invoke the existing architect and coding-agent
  modes, and make SessionStart record a fail-open binding to l9.projection/cursor-governance-operating-plane@2.
todos:
- id: slash-commands
  content: Add /architect and /coding-agent command files that only invoke the existing
    mode packs, regenerate the command manifest, and update the index and slash-recognition
    rule on the live plugin tree.
  status: completed
- id: session-bind
  content: Make Cursor and Claude SessionStart record a fail-open binding to l9.projection/cursor-governance-operating-plane@2
    and update the projection tests.
  status: completed
isProject: false
built: true
status: built
---

# Slash modes and operating-plane bind

## Why only `/lcto` shows

Cursor lists slash commands from the `l9-governance` plugin field `"commands": "./commands"` in [`.cursor-plugin/plugin.json`](/Users/ib-mac/.cursor-governance/.cursor-plugin/plugin.json). The live plugin is `~/.cursor/plugins/local/l9-governance`, which points at `~/.cursor-governance`, not this workspace checkout.

- [`commands/lcto.md`](/Users/ib-mac/.cursor-governance/commands/lcto.md) is a top-level command, so `/lcto` appears.
- There is no `commands/architect.md` or `commands/coding-agent.md`.
- The modes already exist as skills [`skills/l9-global-architect/SKILL.md`](/Users/ib-mac/.cursor-governance/skills/l9-global-architect/SKILL.md) and [`skills/l9-coding-agent/SKILL.md`](/Users/ib-mac/.cursor-governance/skills/l9-coding-agent/SKILL.md). Cursor’s plugin skills path is only `l9-skill-gateway`, so those skill names never appear in the Cursor slash menu.

All three packs are present and bootable. `/lcto` is the command body itself. Architect boots from its `SKILL.md` into `runtime/MANIFEST.yaml`. Coding Agent boots from its `SKILL.md` into `runtime/BOOTSTRAP.yaml` (lazy; do not load the whole pack).

## Slash commands invoke the mode

Add two top-level command files on the live plugin tree (`~/.cursor-governance/commands/`). Each file only names the mode and tells the agent to read that pack and follow it. No second protocol.

- `commands/architect.md` — `/architect` reads and follows `skills/l9-global-architect/SKILL.md`.
- `commands/coding-agent.md` — `/coding-agent` reads and follows `skills/l9-coding-agent/SKILL.md`, whose first read is `runtime/BOOTSTRAP.yaml`.
- Leave [`commands/lcto.md`](/Users/ib-mac/.cursor-governance/commands/lcto.md) as the L CTO mode.

Then regenerate the registry with `ops/scripts/generate_commands_manifest.py` (the `commands:` list is generated). Add the two rows to [`commands/commands-index.md`](/Users/ib-mac/.cursor-governance/commands/commands-index.md) and [`rules/02-slash-commands.mdc`](/Users/ib-mac/.cursor-governance/rules/02-slash-commands.mdc), and project the rule with `ops/scripts/project_llm_rules.py`. Do not hand-edit `environment/generated/llm-rules/`.

These files have to land on `~/.cursor-governance`, because that is the tree Cursor lists. This workspace checkout is a different gitdir; copying them only here will not make the menu change.

## SessionStart binds the operating plane, fail-open

Today [`ops/hooks/session_start_bootstrap.sh`](/Users/ib-mac/.cursor-governance/ops/hooks/session_start_bootstrap.sh) runs [`ops/scripts/operating_plane_v2_projection.py`](/Users/ib-mac/.cursor-governance/ops/scripts/operating_plane_v2_projection.py) `--mode admitted` and prints a report-only line. A `CURRENT` / `ADMITTED_AND_SOURCE_CURRENT` result is a classification. It does not record a session binding. Line and markdown formats always exit 0 and refuse `--source-class`.

Change that SessionStart call so a proved admitted result becomes a binding of `l9.projection/cursor-governance-operating-plane@2`:

- Keep admitted mode. Do not switch to candidate mode. Candidate `BOUND` is bundle-verified only and is not admitted law.
- On `CURRENT`, write a small receipt (profile ref, profile digest, status, reason, authority revision, authority main) under `~/.l9/cursor/operating-plane-binding.json` and print `### operating-plane binding` with that proof.
- Do not release source-class payloads into the session text.
- Fail open: missing adapter, timeout, exception, `UNVERIFIED`, `BLOCKED`, `REJECTED`, or `STALE` still leave bootstrap at exit 0, print the status and reason, and do not write a success receipt.
- Apply the same bind-and-fail-open behavior in the Claude SessionStart emitter so the two hooks stay paired.
- Update [`tests/test_operating_plane_v2_projection.py`](/Users/ib-mac/.cursor-governance/tests/test_operating_plane_v2_projection.py), which currently pins the report-only wording and the “never releases a source class” rule. Keep the no-payload rule. Assert success writes the receipt and failure still exits 0.

## Build evidence (auto)

- detected_at: `2026-11-13T18:56:25Z`
- conversation_id: `d5c37364-3e3a-4618-8679-ddfe1589b2c2`
- generation_id: `1ef984a9-b197-4591-86f5-07f255c7ec05`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-Cursor-Governance/agent-transcripts/d5c37364-3e3a-4618-8679-ddfe1589b2c2/d5c37364-3e3a-4618-8679-ddfe1589b2c2.jsonl`
- todos at build time:
- `slash-commands`: completed
- `session-bind`: completed
