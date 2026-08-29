# Evidence

`verify.sh --pr <owner/repo> <n>` writes `remote-end-to-end-run.json` here.

Once both files below exist and show success, update
`l9-ci-core/.l9/org-runtime-interface.yaml` — the two claims that are the entire gap
between "the repo says it enforces" and "it enforces".

## `organization-ruleset-live-enforcement`

Capture from `bash verify.sh --check`, then:

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
