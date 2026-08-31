# Evidence

| File | Written by | When |
|---|---|---|
| `ruleset-id` | `apply.sh` | every successful apply — the canonical ruleset ID, asserted on later runs so promotion cannot land on a different object |
| `org-rulesets.before.json` | operator, Phase 0 | baseline inventory |
| `organization-ruleset-live-enforcement.json` | `verify.sh --check` | only at `RESULT: LIVE_ENFORCING` |
| `remote-end-to-end-run.json` | `verify.sh --pr <owner/repo> <n>` | canary correlation |

`verify.sh` never prints a bare `PASS`. It names the state — `ADVISORY_VALID`,
`ADVISORY_CANARY_PASS`, `LIVE_ENFORCING`, `LIVE_CANARY_PASS` — because an
evaluate-mode ruleset reading as "PASS" is exactly how an advisory rule gets recorded
as live enforcement. Only `LIVE_ENFORCING` writes the enforcement evidence file.

Once both JSON files below exist and show success, update
`l9-ci-core/.l9/org-runtime-interface.yaml` — the two claims that are the entire gap
between "the repo says it enforces" and "it enforces".

## `organization-ruleset-live-enforcement`

From `evidence/organization-ruleset-live-enforcement.json`
(`bash verify.sh --check` at `RESULT: LIVE_ENFORCING`):

```yaml
  - id: organization-ruleset-live-enforcement
    statement: >-
      A Quantum-L9 organization ruleset currently requires this workflow for
      targeted repositories in production.
    evidence:
      - "orgs/Quantum-L9/rulesets/<id> — enforcement: active, requires .github/workflows/org-ci.yml"
    status: VALIDATED
```

## `remote-end-to-end-run`

From `evidence/remote-end-to-end-run.json`:

```yaml
  - id: remote-end-to-end-run
    statement: >-
      This exact candidate completes end-to-end in GitHub Actions against a
      real consumer repository and publishes its artifact set.
    evidence:
      - "<check_run_url> — <consumer>#<pr>, head_sha <sha>, conclusion success"
    status: VALIDATED
```

Do not flip either claim from a dry run, a workflow_dispatch, or a run on a different
commit. `.l9/org-runtime-contract.yaml` says it plainly:

> Repository-local tests cannot prove organization ruleset activation or a real
> remote run; those states remain UNKNOWN until GitHub evidence exists.
