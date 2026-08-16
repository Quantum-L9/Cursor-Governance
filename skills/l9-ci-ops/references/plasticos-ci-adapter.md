<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [ci, plasticos, makefile]
status: active
/L9_META -->

# PlasticOS CI Adapter

Load when a consumer PlasticOS repo still exposes a historical `pr-check` target. Cursor-Governance shipping is `make pr`.

## Local gate (authoritative)

Cursor-Governance:

```bash
OPEN_PR=0 make pr
```

Historical PlasticOS consumers may still expose `pr-check` as a local alias.
That name is not a Cursor-Governance shipping command.

## GitHub Actions (`ci.yml` blocking jobs)

| Job | Tier | What |
|-----|------|------|
| lint | 1 | ruff check + format |
| static-checks | 2 | XML, manifest, Odoo patterns, wiring, audits |
| pure-python-tests | 3 | pytest suite |

## Push workflow

```bash
make pr
```

Never raw `git push`. On failure: diagnose → fix → `make pr`.

## Multi-job triage

When multiple jobs fail independently, load [parallel-ci-triage.md](parallel-ci-triage.md).

## Non-blocking (advisory)

mypy (pre-commit hook, warn-only in many modules), secret-scan continue-on-error, Odoo.sh commit statuses.
