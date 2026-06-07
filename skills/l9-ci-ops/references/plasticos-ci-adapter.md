<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [ci, plasticos, pr-check, makefile]
status: active
/L9_META -->

# PlasticOS CI Adapter

Load when `AGENTS.md` or `make pr-check` exists in the repo.

## Local gate (authoritative)

```bash
make pr-check
```

Runs: ruff, XML, module wiring, circular deps, Odoo 19 patterns, semgrep, pytest (pure-python tier).

## GitHub Actions (`ci.yml` blocking jobs)

| Job | Tier | What |
|-----|------|------|
| lint | 1 | ruff check + format |
| static-checks | 2 | XML, manifest, Odoo patterns, wiring, audits |
| pure-python-tests | 3 | pytest suite |

## Push workflow

```bash
make push          # pr-check then push
make push pr=1     # push + open PR into Staging
```

Never raw `git push` — see rule 70-github-api-commit.

## Multi-job triage

When multiple jobs fail independently, load [parallel-ci-triage.md](parallel-ci-triage.md).

## Non-blocking (advisory)

mypy (pre-commit hook, warn-only in many modules), secret-scan continue-on-error, Odoo.sh commit statuses.
