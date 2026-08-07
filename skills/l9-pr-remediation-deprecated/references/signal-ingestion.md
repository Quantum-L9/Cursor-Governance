<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: signal_ingestion
tags: [pr, ci, review, ingestion, scope-discovery, github-api, gate-discovery]
owner: igor_beylin
status: active
version: 3.5.0
updated: 2026-07-28
/L9_META -->

# Signal Ingestion

## Purpose

Resolve the PR scope, then fetch all actionable signals from each in-scope PR: CI gate failures, code-review comments, inline suggestions, and workflow definitions. Normalize everything into a unified finding list for ownership-first classification. Read CI definitions as evidence only; never mutate them in this Skill.

## Scope Discovery (FIRST — before any per-PR work)

Expand the configured `pr_scope` into a concrete list of PR numbers. Run the per-PR loop (gate discovery → ingest → … → report) independently for each. **Never share a commit across PRs.**

```bash
# ALL_OPEN
gh pr list --repo {owner}/{repo} --state open --json number,headRefName,author,labels

# PR_NUMBERS: use the given list directly
# LABEL:<x>
gh pr list --repo {owner}/{repo} --state open --label "{x}" --json number,headRefName

# AUTHOR:<u>
gh pr list --repo {owner}/{repo} --state open --author "{u}" --json number,headRefName
```

Produce the scope artifact:

```yaml
pr_scope_resolved:
  repo: "{owner}/{repo}"
  selector: "ALL_OPEN | PR_NUMBERS:[...] | LABEL:x | AUTHOR:u"
  prs:
    - number: 42
      branch: "feat/x"
    - number: 43
      branch: "fix/y"
  total: 2
```

If scope resolves to zero PRs → STOP and report "no PRs in scope".

## Gate Discovery (per PR — before CI log ingestion)

### Step 0: Parse workflow YAML

```bash
find .github/workflows -name "*.yml" -o -name "*.yaml"
cat .github/workflows/*.yml
```

For each workflow file extract: job names + `runs-on`, step names + `run:` commands, `if:` conditions, and required `env:` blocks. Build the **gate registry**:

```yaml
ci_gates:
  - gate: "type-check"
    command: "npx tsc --noEmit"
    workflow: "build-and-validate.yml"
    job: "validate"
    step: "Type check"
    can_run_locally: true
    requires_secrets: false
```

Also check `package.json` scripts and any `Makefile` `ci`/`pr-check` targets:

```bash
cat package.json | grep -A20 '"scripts"'
```

This gate registry drives codebase verification. Workflow, action, branch-protection, and CI-only configuration files are read-only evidence. If no workflows exist, derive commands from package scripts, Makefiles, repository docs, and branch-protection checks. If no trustworthy local command exists, record the gate as remote-only; do not invent, weaken, or repair CI.

## CI Signal Ingestion

```bash
# Latest run on the PR branch
gh run list --branch {branch} --limit 3 --json databaseId,status,conclusion,event
# Failed logs (pick most recent run with conclusion != success)
gh run view {RUN_ID} --log-failed
# Job-level summary if logs are large
gh run view {RUN_ID} --json jobs --jq '.jobs[] | select(.conclusion=="failure") | {name, conclusion}'
```

Parse each failure into: gate name (match the registry), error message, file + line when available, and the exact command CI ran.

## Review Comment Ingestion

```bash
# Reviews (state CHANGES_REQUESTED / COMMENTED)
gh api /repos/{owner}/{repo}/pulls/{pr}/reviews --jq '.[] | {id, user: .user.login, state, body}'
# Inline (diff) comments — include suggestion blocks
gh api /repos/{owner}/{repo}/pulls/{pr}/comments --jq '.[] | {id, user: .user.login, path, line, body, created_at}'
# General PR comments
gh pr view {pr} --repo {owner}/{repo} --comments --json comments
```

### Thread resolution state (GraphQL) — only process `isResolved: false`

```bash
gh api graphql -f query='
  query($owner:String!,$repo:String!,$pr:Int!){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$pr){
        reviewThreads(first:100){ nodes{
          id isResolved
          comments(first:5){ nodes{ body author{login} path line } } } } } } }
' -f owner={owner} -f repo={repo} -F pr={pr}
```

Capture each thread's `id` (needed later to resolve it). Skip threads already resolved or clearly addressed by a later commit (idempotency).

## Unified Finding Format

```yaml
findings:
  - id: "ci-1"
    source: ci | review_inline | review_general
    author: "github-actions" | "gemini-code-assist" | "coderabbitai" | "sonarcloud" | "{human}"
    ownership: CODEBASE_REPAIR | CI_PIPELINE_SIGNAL | HUMAN_DECISION | FALSE_POSITIVE
    severity: blocking | actionable | discussion | deferred
    file: "src/index.ts"        # null for general comments
    line: 42                    # null for general comments
    thread_id: "PRRT_..."       # for review threads (to resolve later)
    has_suggestion_block: true | false
    message: "Type error: Property 'foo' does not exist on type 'Bar'"
    rule: "typescript:S1128"    # vendor rule id when present — used for cross-source dedup
    gate: "type-check"          # null for review comments
    local_verify_command: "npx tsc --noEmit"
    owning_surface: source | test | workflow | reusable_workflow | action | runner | permissions | secrets | oidc | branch_protection | check_wiring | cache | external_service | shared_ci | ci_only_script | policy_config | unknown
    root_cause_fingerprint: null
    raw: "full original text"
```

## Review Sources (multi-tool) — beyond PR comments

PR comments are only one source. The GitHub PR page shows a scanner's *summary + gate*; its **full findings live in check-run annotations, code-scanning/SARIF, or the vendor API**. After ingesting comments, walk the source registry in [references/review-sources.md](review-sources.md):

1. **Tier 1 (always on, `GITHUB_TOKEN` with `checks: read` + `security_events: read`):**
   - `check_run_annotations` — `GET /repos/{o}/{r}/commits/{sha}/check-runs` then `/check-runs/{id}/annotations` (file+line findings from tools that annotate but don't comment).
   - `code_scanning` — `GET /repos/{o}/{r}/code-scanning/alerts?ref=refs/pull/{n}/head` (SARIF uploaders: Snyk, Semgrep, CodeQL, Trivy).
2. **Tier 2 (enabled iff the source's `token_env` is set):** e.g. SonarCloud —
   ```bash
   curl -sS -u "$SONAR_TOKEN:" "https://sonarcloud.io/api/issues/search?componentKeys=$SONAR_PROJECT_KEY&pullRequest={pr}&resolved=false"
   curl -sS -u "$SONAR_TOKEN:" "https://sonarcloud.io/api/qualitygates/project_status?projectKey=$SONAR_PROJECT_KEY&pullRequest={pr}"
   ```
   `projectKey` auto-discovers from `sonar-project.properties` or the Sonar check-run `details_url`.

For each **enabled** source, normalize results into the unified finding format below (set `source`/`author` to the registry id, keep the vendor `rule`). A source with no token or no data is **skipped and recorded** (`summary.review_sources[].queried: false`) — never a blocker. Capture each scanner's gate status for the run report. **Never read, log, or store the token value** — reference `$SONAR_TOKEN` only.

## Bot Detection

`gemini-code-assist[bot]` → Gemini · `coderabbitai[bot]` → CodeRabbit · `copilot[bot]` → GitHub Copilot · `sonarcloud[bot]` → SonarCloud · `github-actions[bot]` → CI · all others → human. Vendor-API sources use their registry id as the reviewer (`sonarcloud`, `snyk`, `semgrep`) so `bot_false_positive_rate` tracks them.

## Deduplication

When a review comment references the same file and line as a CI error, merge only when ownership and root cause also match. Keep the more precise CI evidence and retain a still-valid code suggestion. Never merge a pipeline cause into a codebase finding.

**Cross-source dedup:** the same issue often arrives from multiple sources (a Sonar issue posted both as a check annotation and via the vendor API). Merge findings with the same `(file, line, rule)` — or `(file, line, message)` when no rule id — into one, keeping the vendor `rule` and the most precise message. Count the merged finding once for that reviewer's `bot_false_positive_rate`.

## Idempotency (skip already-done work)

A re-run MUST NOT duplicate commits or replies. Drop a signal from the finding list when ANY of these hold:

- its review thread is already **resolved** (GraphQL `isResolved: true`);
- the thread already contains the reply marker `<!-- l9-remediation:{pr}:{finding_id} -->` (see `references/review-replies.md`);
- a commit on the branch already carries the trailer `Remediation-Cycle: {repo}#{pr}/cycle-{N}` for the cycle that would address it (see `references/fix-engine.md`).

The idempotency key is therefore the triple **(resolved thread state, reply marker, commit trailer)** — check all three during ingestion so re-entry is safe and unattended re-runs converge instead of re-doing work.

## Ingestion Completeness Check

- [ ] Scope resolved to a concrete PR list
- [ ] All workflow files read; gate registry built (≥1 gate)
- [ ] All CI failures mapped to a registry gate
- [ ] Every CI failure classified by ownership before fix strategy
- [ ] Every CI-pipeline root cause has a stable fingerprint
- [ ] All unresolved review threads captured with `thread_id`
- [ ] All inline suggestions captured with file+line + `has_suggestion_block`
- [ ] Bot vs human attribution correct
- [ ] Duplicates merged
