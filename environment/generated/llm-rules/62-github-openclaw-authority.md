---
description: Agents MUST use openclaw-igorbot/github#token for GitHub; MUST NOT ask humans to operate github.com UI.
---

# GitHub Openclaw PAT authority (CANONICAL_LAW §14)

- **Sole PAT:** resolve `openclaw-igorbot/github#token` via `ops/secrets` /
  `l9-aws-secrets`. Export as `GH_TOKEN` / `GITHUB_TOKEN` for `gh` and GitHub API.
- **No second PAT** in AWS while that ref works. Rotate in place if scopes change.
- **No human GitHub UI:** do not ask the operator to click Installations,
  permission accepts, settings toggles, or Actions secret paste when the PAT
  (or already-wired App env secrets) can complete the same outcome via API.
- **App vs PAT:** Actions seeder may use `GOVERNANCE_APP_*` on env
  `governance-distribution`. Interactive/agent `gh` work still uses the openclaw PAT.
- **Ask-human only** after `resolve_secret.py --check` fails, or for true
  non-API human factors (name the failing ref).

<!-- generated-from: rules/62-github-openclaw-authority.mdc; do-not-edit -->
