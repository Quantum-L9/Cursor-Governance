---
description: Global non-negotiable agent behavior for governed Cursor workspaces
---

# Global rules

## MUST

- Follow `CANONICAL_LAW.md` and `AGENTS.md` authority order
- Prefer existing code and verified repo ground truth over invention
- Fail closed on protected paths, secrets, and irreversible remote actions
- Keep responses concise; put long procedures in skills/commands
- Use Graphiti for episodic resume — not Cursor native Memories for repo facts
- Scoped-commit authored pathspecs on this branch before you finish a coding turn (`99-no-auto-commit`). Do not ask.

## MUST NOT

- Leave unique dirty files you authored this session
- Push / `make pr` without satisfying `99-no-auto-commit` / L4 / surface_profile precedence
- Deploy, mutate production, or edit C1/VPS without explicit approval (`93-c1`, `94-deployment-prohibition`)
- Create a second governance tree or duplicate `.cursor/commands` / skills
- Hand-edit generated manifests (`RULES-MANIFEST.*`, `environment/generated/llm-rules/**`)
- Overwrite `AGENTS.md` or `Makefile` (same `additive_only` rule). Append only.
  A rewrite needs a GitHub issue first. Do not invent `ALLOW-ROOT-DELETION`
  or chase the protected-root PR template — that is the delay this rule exists
  to prevent.

## See also

- Slash commands: `02-slash-commands.mdc`
- Skill routing: `23-l9-skill-routing.mdc`
- Wiring: `84-cursor-governance-wiring.mdc`

<!-- generated-from: rules/00-global.mdc; do-not-edit -->
