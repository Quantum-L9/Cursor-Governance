<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: signal_ingestion
tags: [pr, ci, review, ingestion, github-api, gate-discovery]
owner: igor_beylin
status: active
version: 2.2.0
updated: 2026-08-16
/L9_META -->

# Signal Ingestion

## Purpose

Fetch all actionable signals from an open PR: CI gate failures, code review comments, workflow definitions, and SonarCloud static-analysis findings. Normalize them into a unified finding list for classification.

## SonarCloud finding ingestion

When `sonar-project.properties` exists or the SonarCloud check is failing, SonarCloud is a
signal source. Do not parse the SonarCloud check summary or dashboard screenshots — retrieve
the structured issue set from the API and confirm it against current source. The full
fail-closed protocol (identity binding, pagination, root-cause clustering, minimal-fix
contract, security-hotspot policy, and the local-fix-is-not-remote-closure rule) lives in
[sonarcloud-remediation.md](sonarcloud-remediation.md). Deterministic retrieval:

```bash
python scripts/sonar_fetch.py \
  --project "$(sed -n 's/^sonar.projectKey=//p' sonar-project.properties)" \
  --organization "$(sed -n 's/^sonar.organization=//p' sonar-project.properties)" \
  --pull-request <PR_NUMBER> --output sonarcloud-issues-before.json
```

Normalize each issue to the unified finding list with `source: sonarcloud`, its `rule_key`,
`severity`, `type`, `component` path, `line`, and `message`, so it flows through the same
classify → fix → validate gates as CI and review signals.

## Gate Discovery (FIRST — before CI log ingestion)

### Step 0: Parse workflow YAML

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

**Makefile + pre-commit (required when present)** — these are the primary local-verify surfaces, not optional extras. Record every Makefile gate target (`agent-check`, `pr-check`, `check`, `ci`, `validate`, `test`) and **every** hook `id` in `.pre-commit-config.yaml`. See [remediation-plan.md](remediation-plan.md).

```bash
test -f Makefile && make -qp 2>/dev/null | awk -F: '/^[a-zA-Z0-9][^$#\/\t=]*:([^=]|$)/ {print $1}' | sort -u
test -f .pre-commit-config.yaml && grep -E '^[[:space:]]+- id:' .pre-commit-config.yaml
```

This gate registry is used by the fix-engine for local verification. A census that lists CI failures but omits Makefile/pre-commit hooks is incomplete.

## CI Signal Ingestion

### Step 1: Get latest CI run

```bash
gh run list --branch {branch} --limit 3 --json databaseId,status,conclusion,event
```

Pick the most recent run with `conclusion != success`.

### Step 2: Get failed job logs

```bash
gh run view {RUN_ID} --log-failed
```

If output is too large, get job-level summary first:

```bash
gh run view {RUN_ID} --json jobs --jq '.jobs[] | select(.conclusion == "failure") | {name, conclusion}'
```

Then fetch per-job:

```bash
gh run view {RUN_ID} --log --job-id {JOB_ID} 2>&1 | tail -100
```

### Step 3: Parse CI failures

Extract from logs:
- **Gate name**: the job/step that failed (match against gate registry from Step 0)
- **Error message**: the actual error output
- **File + line**: when available (lint errors, type errors, test failures)
- **Command**: the exact command the CI ran (from gate registry)

## Review Comment Ingestion

### Step 1: Get PR reviews

```bash
gh api /repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq '.[] | {id, user: .user.login, state, body}'
```

Keep `state: "CHANGES_REQUESTED"`. Keep `state: "COMMENTED"` when the body is actionable **or** the author is a [code-review agent](code-review-agents.md) (`github-code-quality[bot]`, Copilot). Do not drop Code Quality / Copilot reviews for lacking an "actionable" phrase.

### Step 2: Get inline (diff) comments

```bash
gh api /repos/{owner}/{repo}/pulls/{pr_number}/comments --jq '.[] | {id, user: .user.login, path, line, body, created_at}'
```

### Step 3: Get general PR comments (non-inline)

```bash
gh pr view {pr_number} --repo {owner}/{repo} --comments --json comments --jq '.comments[] | {author: .author.login, body, createdAt}'
```

### Step 4: Filter resolved threads

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            isResolved
            comments(first: 5) {
              nodes { body author { login } path line }
            }
          }
        }
      }
    }
  }
' -f owner={owner} -f repo={repo} -F pr={pr_number}
```

Only process threads where `isResolved: false`. If the first comment author is a code-review agent, keep the thread even when the body looks like a Note, nit, coverage overview, or discussion.

## Unified Finding Format

Normalize all signals into:

```yaml
findings:
  - id: "ci-1"
    source: ci | review_inline | review_general
    author: "github-code-quality" | "copilot" | "github-actions" | "gemini-code-assist" | "coderabbitai" | "{human}"
    reviewer_class: code_review_agent | bot | human | ci
    severity: blocking | actionable | discussion | deferred
    file: "src/index.ts"  # null for general comments
    line: 42              # null for general comments
    message: "Type error: Property 'foo' does not exist on type 'Bar'"
    gate: "type-check"    # null for review comments
    local_verify_command: "npx tsc --noEmit"  # from gate registry
    raw: "full original text"
```

## Bot Detection

Identify reviewers by login (strip a trailing `[bot]` before matching):

**Code-review agents** — full inspect / validate / fix-if-valid / reply-all. See [code-review-agents.md](code-review-agents.md). Never classify these as skippable chatter or as `human`.
- `github-code-quality[bot]` → GitHub Code Quality (`reviewer_class: code_review_agent`)
- `copilot[bot]` → GitHub Copilot code review (`reviewer_class: code_review_agent`)
- `copilot-pull-request-reviewer[bot]` → GitHub Copilot code review (`reviewer_class: code_review_agent`)

**Other bots**
- `gemini-code-assist[bot]` → Gemini (`reviewer_class: bot`)
- `coderabbitai[bot]` → CodeRabbit (`reviewer_class: bot`)
- `github-actions[bot]` → CI (should already be in CI signals; `reviewer_class: ci`)

**Everyone else** → human reviewer (`reviewer_class: human`)

## Deduplication

When a review comment references the same file+line as a CI error, merge into one finding. Prefer the CI error message (more precise) but retain the review comment's suggested fix if present.

## Ingestion Completeness Check

After ingestion, verify:
- [ ] All workflow files read and gates registered
- [ ] Makefile primary target recorded when a Makefile exists
- [ ] Every `.pre-commit-config.yaml` hook `id` recorded when the file exists
- [ ] All CI failures mapped to a gate in the registry
- [ ] All unresolved review threads captured
- [ ] All inline suggestions captured with file+line
- [ ] Every `github-code-quality[bot]` / Copilot comment ingested (no actionable-body drop)
- [ ] Code-review agent vs other-bot vs human attribution correct
- [ ] Duplicates merged
