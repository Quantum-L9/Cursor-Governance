# Infisical OIDC Machine Identity — Cursor-Governance

Configuration record for the `github-cursor-governance-claude-bootstrap` machine
identity. Keep this file in sync with the live Infisical org config; this is
documentation only, not executable — actual state lives in Infisical.

## Identity

| Field | Value |
|---|---|
| Name | `github-cursor-governance-claude-bootstrap` |
| Org role | least-privilege custom role, no admin scopes |
| Auth method | OIDC Auth (Universal Auth removed) |

## OIDC Auth config

| Field | Value |
|---|---|
| OIDC Discovery URL | `https://token.actions.githubusercontent.com` |
| Issuer | `https://token.actions.githubusercontent.com` |
| Audience | `https://github.com/Quantum-L9` |
| Subject | `repo:Quantum-L9/Cursor-Governance:environment:production` |
| Claims (optional binding) | `repository: Quantum-L9/Cursor-Governance` |

Rationale for subject choice: binding to `environment:production` (not `ref:refs/heads/main`)
ties the Infisical trust decision to the same GitHub Environment protection rules
(required reviewers / branch restriction) already enforced on this repo, so a
compromised PR branch cannot mint the identity even if it can push to `main`.

## Project membership

| Field | Value |
|---|---|
| Project slug | `cursor-governance` |
| Project role | `claude-bootstrap-reader` (custom: read-only on `/claude-code` secret path) |
| Environments granted | `prod` (add `dev`/`staging` only if a matching GitHub Environment + subject exists) |

## GitHub repo variables required

Set as repository Variables (not Secrets — this value is not sensitive):

| Name | Value |
|---|---|
| `INFISICAL_MACHINE_IDENTITY_ID` | `<identity UUID from Infisical>` |

## Rotation / audit checklist

- [ ] Confirm bound subject still matches the exact GitHub Environment name after any repo rename.
- [ ] Quarterly: review `claude-bootstrap-reader` role scope — confirm it still only covers `/claude-code`.
- [ ] Quarterly: pull Infisical audit log for this identity, confirm no calls from unexpected `job_workflow_ref` values.
- [ ] On any Infisical.com domain change (self-host migration), update `domain:` input in workflow.
