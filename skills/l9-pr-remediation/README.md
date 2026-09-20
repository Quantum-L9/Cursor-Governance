# L9 Pr Remediation

**Path:** `skills/l9-pr-remediation` | **Kind:** skill

## Purpose

diagnose or converge github prs — plan the fleet once, launch execution-profile-capped subagents to remediate, poll remediating PRs, and start stack-safe merge trains on the oldest green PRs that will not conflict downstream. do not wait for every PR to be green. do not run make pr

## Key components

- [`agents/`](agents/)
- [`references/`](references/)
- [`scripts/`](scripts/)

## Authority

`SKILL.md` in this directory is the authoritative operating contract. This README is a navigation projection of it and never outranks it.

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=skill -->
