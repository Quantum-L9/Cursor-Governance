---
description: Agents MUST use openclaw-igorbot/github#token for GitHub where the surface holds credentials; on a model-controlled surface the REST `gh api` route and the mcp__github__* tools are the sanctioned capability, by observation and without a mechanism asserted. MUST NOT ask humans to operate github.com UI.
---

# GitHub Openclaw PAT authority (CANONICAL_LAW §14)

- **Sole PAT:** resolve `openclaw-igorbot/github#token` via `ops/secrets` /
  `l9-aws-secrets`. Export as `GH_TOKEN` / `GITHUB_TOKEN` for `gh` and GitHub API.
  **Applies where the surface holds credentials.** See the surface-transport
  section below before reaching for it.
- **No second PAT** in AWS while that ref works. Rotate in place if scopes change.
- **No human GitHub UI:** do not ask the operator to click Installations,
  permission accepts, settings toggles, or Actions secret paste when the PAT
  (or already-wired App env secrets) can complete the same outcome via API.
- **App vs PAT:** Actions seeder may use `GOVERNANCE_APP_*` on env
  `governance-distribution`. Interactive/agent `gh` work still uses the openclaw PAT.
- **Ask-human only** after `resolve_secret.py --check` fails, **the surface can hold
  that credential**, and no sanctioned transport below reaches the outcome — or for
  true non-API human factors (name the failing ref).
- **REST `gh api` is the same PAT, not a second secret.** GraphQL (`gh pr view
  --json`, `gh repo view --json`) may 403 on restricted gateways. `gh api
  repos/...` is a sanctioned route for the same `openclaw-igorbot/github#token`.
  Do not provision another GitHub credential to "fix" a GraphQL 403.

## Surface transport (model-controlled surfaces)

A `model-controlled` surface holds **no** credential of its own: no Infisical import,
no PAT, no bearer. The capability broker that was once going to bridge this **never
shipped and is retired** — do not reach for it, and do not set
`L9_CAPABILITY_BROKER_URL` (`docs/DEGRADED_MODE_CONTRACT.md`).

What is observable on such a surface, and all that should be claimed: **`gh api`
succeeds while the session's own `GH_TOKEN` is an invalid sentinel.** The credential
reaching GitHub is therefore supplied outside this repository's control. Do not
assert a mechanism the repository cannot verify — record the probe, not a theory.

The practical consequence is unchanged: `gh api` and the `mcp__github__*` tools are
the sanctioned GitHub route here. Prefer them over asking a human, and over treating
an absent PAT as a dead end. A capability reporting `UNAVAILABLE` is never a
reason to paste a secret into the sandbox.

### `gh auth status` is not a capability probe

It reports the `GH_TOKEN` sentinel invalid, **and its exit code does not agree with
itself across containers**: 0 on 2026-08-29/30 and 1 on 2026-08-31, in the same
surface class, with the same message and the same working `gh api`
(`docs/DEGRADED_MODE_CONTRACT.md`). So a script that gates on it is wrong in both
directions — it takes the success path while the output says the opposite, or it
declares GitHub unreachable while `gh api` works — and which of the two is not
predictable. A human reading only the text reaches the second conclusion either way.
Probe the capability you actually need — `gh api user`, or the specific endpoint —
and never gate on `gh auth status`.

Observed transports are recorded, dated and per-container, in
`docs/DEGRADED_MODE_CONTRACT.md`. A container that contradicts a recorded row is
new evidence: add a dated row, do not silently rewrite the old one.

### Scope of this section

This section names which GitHub **transport** is sanctioned. It changes nothing
about the publication path: `make pr` remains the sanctioned route, for the reasons
in `48-make-pr-remediation`, and merge authority is untouched.

<!-- generated-from: rules/62-github-openclaw-authority.mdc; do-not-edit -->
