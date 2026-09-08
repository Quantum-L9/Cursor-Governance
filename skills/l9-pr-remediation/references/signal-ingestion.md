<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: signal_ingestion
tags: [pr, ci, review, ingestion, github-api, gate-discovery]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-09-07
/L9_META -->

# Signal Ingestion

## Purpose

Fetch all actionable signals from an open PR: CI gate failures, code review comments, workflow definitions, SonarCloud static-analysis findings, and Semgrep hits when that check is failing. Normalize them into a unified finding list for classification.

**Deterministic retrieve** is `scripts/ingest_signals.py` (reviewer class + path ownership hints + scanner merge). Do not reconstruct `gh api` loops. Confirm / disposition / HUMAN / FALSE_POSITIVE stay judgment.

## SonarCloud finding ingestion

When `sonar-project.properties` exists or the SonarCloud check is failing, SonarCloud is a
signal source. Do not parse the SonarCloud check summary or dashboard screenshots — retrieve
the structured issue set from the API and confirm it against current source. The full
fail-closed protocol (identity binding, pagination, root-cause clustering, minimal-fix
contract, security-hotspot policy, and the local-fix-is-not-remote-closure rule) lives in
[sonarcloud-remediation.md](sonarcloud-remediation.md). Deterministic retrieval:

Run on **every** Converge when Sonar is configured (`sonar-project.properties`), authenticated via `capability_bind` (`SONAR_TOKEN`); the check's colour does not matter and a red Sonar check never blocks merge. Write `--output` under `$PWD` (never `/tmp`). A path-blocked fetch is recorded, never a reason to stop the train.

```bash
"${GOV_PY:-$PWD/.venv/bin/python}" scripts/sonar_fetch.py \
  --project "$(sed -n 's/^sonar.projectKey=//p' sonar-project.properties)" \
  --organization "$(sed -n 's/^sonar.organization=//p' sonar-project.properties)" \
  --pull-request <PR_NUMBER> --output sonarcloud-issues-before.json
```

Normalize each issue to the unified finding list with `source: sonarcloud`, its `rule_key`,
`severity`, `type`, `component` path, `line`, and `message`, so it flows through the same
classify → fix → validate gates as CI and review signals.

## Semgrep finding ingestion

When the Semgrep / L9 Analysis / `pr-security` check is failing, or findings are
present, Semgrep is a signal source. Do not parse GH logs, dashboard screenshots,
or MCP `semgrep_findings` (default limit 10) — retrieve the complete issue set
from the App API and confirm it against current source. The full fail-closed
protocol (env-token GET, no paste, no authenticated scan, pagination, root-cause
clustering) lives in [semgrep-remediation.md](semgrep-remediation.md). A red
Semgrep check never blocks merge unless `pr_board.py` lists it.

```bash
"${GOV_PY:-$PWD/.venv/bin/python}" scripts/semgrep_fetch.py \
  --repo <owner/repo> --pull-request <PR_NUMBER> \
  --output semgrep-findings-before.json
```

Normalize each hit to the unified finding list with `source: semgrep`, its
`rule_name`, path, line, severity, and message.

## Unified retrieve (do this, not the gh cookbook)

```bash
"${GOV_PY:-$PWD/.venv/bin/python}" skills/l9-pr-remediation/scripts/ingest_signals.py \
  --repo {owner}/{repo} --pr {n} --output findings.json \
  --required-checks "{comma-separated from pr_board.py}"
# optional scanner snapshots already written under $PWD:
#   --sonar sonarcloud-issues-before.json \
#   --semgrep semgrep-findings-before.json \
#   --codeql codeql-alerts-before.json \
#   --debt debt-baseline.json
```

`--fixture-dir` is tests/offline only. Live runs call `gh`. The snapshot includes `gate_registry`, `findings[]`, and `completeness`. A FAIL on CRA completeness is STOP — do not drop Notes.

## Gate Discovery (FIRST — before CI log ingestion)

When a Makefile exists, skip reconstructing a local suite from workflow YAML.
Record remediator `make precommit-repo` / `git push`. Do not run ceremony `make pr-check` / `make pr`. Continue to CI log ingestion only for already-red checks.

### Step 0: Parse workflow YAML (fallback only — no Makefile)

```bash
# List all workflow files
find .github/workflows -name "*.yml" -o -name "*.yaml"

# Read each one — extract job names and run commands
cat .github/workflows/*.yml
```

For each workflow file, extract:
- **Job names** and their `runs-on` value
- **Step names** and their `run:` commands
- **Conditions** (`if:` clauses that might skip steps)
- **Environment variables** required (`env:` blocks)

Build the **gate registry**:

```yaml
ci_gates:
  - gate: "type-check"
    command: "npx tsc --noEmit"
    workflow: "build-and-validate.yml"
    job: "validate"
    step: "Type check"
    can_run_locally: true
  - gate: "pipeline-dry"
    command: "npm run pipeline:dry"
    workflow: "build-and-validate.yml"
    job: "validate"
    step: "Run pipeline dry"
    can_run_locally: true
  - gate: "verify-env"
    command: "node scripts/verify-launch-env.mjs --ci"
    workflow: "build-and-validate.yml"
    job: "validate"
    step: "Verify launch env"
    can_run_locally: true
    note: "May warn on missing secrets — check if --ci flag handles this"
```

Also check `package.json` scripts for additional gates:
```bash
cat package.json | grep -A1 '"scripts"'
```

**Remediator verbs (required)** — `make precommit-repo` is the local-verify surface, `git push` is publish. Ceremony `make pr-check` / `make pr` must not be invoked. See [remediation-plan.md](remediation-plan.md).

```bash
test -f Makefile && grep -E '^(precommit-repo|improve):' Makefile
test -f .pre-commit-config.yaml && grep -E '^[[:space:]]+- id:' .pre-commit-config.yaml
```

A census that lists CI failures but omits remediator `make precommit-repo` is incomplete. Workflow `run:` replay is leftover fallback only when no Makefile exists. Ceremony `make pr-check` is not the remediator gate.

## CI Signal Ingestion

`ingest_signals.py` already captured failed checks. For **root cause**, still read logs — that is judgment, not retrieve:

```bash
gh run view {RUN_ID} --log-failed
```

Extract: gate name, error, file+line, the command CI ran.

## Review Comment Ingestion

Retrieve is the snapshot. Keep every CRA comment even when the body looks like a Note, nit, or discussion. Only `isResolved: true` threads are dropped. See [code-review-agents.md](code-review-agents.md).

## Unified Finding Format

The machine snapshot is `findings.json` from `ingest_signals.py`. Fields it **does** fill: `id`, `source` (plan vocabulary: `ci` / `human` / `bot` / `github-code-quality` / `copilot` / `sonar` / `codeql` / `semgrep` / `debt`), `surface`, `author`, `reviewer_class`, `ownership_hint`, `severity_hint`, `file`, `line`, `message`, `gate`, `raw`. Fields it **does not** fill: `ownership` (final), `disposition`, `root_cause`, `board`.

## Bot Detection

Login table is `scripts/protocol.py` `reviewer_class`. Do not invent extra CRA members. See [code-review-agents.md](code-review-agents.md).

## Deduplication

Same file+line collapses in `ingest_signals.py`. CI message wins; review text stays in `raw`.

## Ingestion Completeness Check

After ingestion, verify:
- [ ] Remediator verbs recorded when a Makefile exists (`make precommit-repo` verify, `git push` publish)
- [ ] Workflow `run:` leftover recorded only when no Makefile exists
- [ ] Cited/planned-path hook ids recorded (not all-files as the gate)
- [ ] Semgrep hits ingested when that check is failing (`source: semgrep`)
- [ ] All CI failures mapped to a gate in the registry
- [ ] All unresolved review threads captured
- [ ] All inline suggestions captured with file+line
- [ ] Every `github-code-quality[bot]` / Copilot comment ingested (no actionable-body drop)
- [ ] Code-review agent vs other-bot vs human attribution correct
- [ ] Duplicates merged
