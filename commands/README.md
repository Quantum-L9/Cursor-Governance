# L9 slash commands

This folder holds live slash triggers (`commands/*.md`).

- Human index: `commands/commands-index.md`
- Machine registry: `commands/COMMANDS_MANIFEST.yaml` (generated)
- Recognition rule: `rules/02-slash-commands.mdc`

Use **`/docs`** (skill `l9-update-agent-docs`) to update agent-facing docs and to run the wired module README pipeline (`readme-pipeline-v1` → `scripts/generate_subsystem_readmes.py`). This file is not a `/readme` protocol.

Retired command files live in `commands/_archived/`.

## Projection binding commands

Every session is already bound to the operating plane
(`l9.projection/cursor-governance-operating-plane@2`) by SessionStart, with no command
(`governance/host-bindings/README.md`). These three commands add projections for the
current session only, by hand:

| Command | Binds | Contract |
|---|---|---|
| `/coding-agent` | `coding-agent-execution@1` | `governance/coding-agent-mode/MODE.yaml` |
| `/lcto` | technical-coordination plus seven domains | `governance/cto-mode/MODE.yaml` |
| `/architect` | seven architecture and strategic-planning domains | `governance/architect-mode/MODE.yaml` |

How they work: each runs its `ops/autonomy/<name>_mode.py on --workspace "$PWD"`. The
request is recorded for this host session only. The mode is `ACTIVE` only when every
required projection verifies with the verifier its binding declares, and then lists the
files to read in `load[].views`; otherwise it is `BLOCKED` with each reason and nothing
from a blocked projection is read. `off` releases it. None depends on a skill, and none
grants a permission.
