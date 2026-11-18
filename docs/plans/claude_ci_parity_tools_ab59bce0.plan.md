---
name: Claude Code CI-parity scanners with Infisical-bound paid tiers
overview: "In hosted Claude Code sessions only (Cursor untouched), install CI-parity scanners pinned to the versions CI actually runs (CodeQL CLI 2.27.0, Semgrep 1.178.0 incl. Semgrep Pro via SEMGREP_APP_TOKEN, Biome 2.5.5, pip-audit 2.10.1) plus actionlint, zizmor, shellcheck, osv-scanner and yamllint, bind the paid-tier tokens (SEMGREP_APP_TOKEN, SONAR_TOKEN) from Infisical project cursor-governance thr..."
todos:
  - id: T1
    content: "Create the single pin manifest ops/ci_parity/tools.yaml: per tool version, install method (github-release binary with sha256 | uv tool install pkg==ver), ci_ref evidence (workflow path + pinned ref + observed version), lane(s), file triggers, blocking class (block_new | advisory), thread weight; plus README with lane/timing table. Add a drift validator that fails when a CI pin line recorded in ci_ref (codeql.yml reusable ref, l9-lint-test-node biome ref) changes without a manifest bump."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Create ops/ci_parity/install.py: idempotent, flock single-flight (~/.local/share/l9-ci-parity/.install.lock), sha256-verified release binaries (codeql bundle 2.27.0, actionlint, shellcheck, osv-scanner, biome 2.5.5) into ~/.local/share/l9-ci-parity/<tool>/<ver> with ~/.local/bin symlinks; `uv tool install pkg==ver` for semgrep/zizmor/yamllint/pip-audit; version probe skips reinstall; --check prints literal per-tool status; sha mismatch refuses and leaves prior install intact."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Wire the installer Claude-only: add an install step to environment/agents/adapters/claude-code/web/setup.sh (snapshot-cached) and a self-heal call inside the existing setsid background worker of hooks/session_deps_cloud.sh (hosted-only, never blocks SessionStart); fix the fingerprint typo package-lock.yaml -> package-lock.json in that same file; keep validate_claude_env.py rules green."
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T4
    content: "Create ops/ci_parity/findings.py: normalise SARIF (codeql, semgrep, zizmor, osv) and JSON/gcc outputs (shellcheck, actionlint, yamllint, biome, pip-audit) into one finding record {tool, rule, severity, path, line, message}; compute changed line ranges from `git diff -U0 merge-base(PR_BASE,HEAD)..<sha>`; keep only findings inside changed ranges (emulates CodeQL pr-diff-range and Semgrep diff-aware); map severity to block/advisory per tools.yaml mirroring CI (code-scanning error / security-severity high+ blocks)."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T5
    content: "Create the allowlisted exec broker ops/secrets/capability_exec.py + capability-exec.json (one entry: semgrep-pro -> `semgrep ci --dry-run --baseline-commit <merge-base> --sarif-output <receipt-path>`): binds SEMGREP_APP_TOKEN in-process via capability_bind, builds a minimal child env (PATH, HOME, token) with no caller-supplied argv beyond registered placeholders, runs inside the scan snapshot clone, scrubs the token from stdout/stderr/output files (withhold on echo), literal-only diagnostics. Amend doctrine: capabilities.yaml semgrep.appsec_scan execution trusted_worker (retired broker) -> capability_exec with the bounded /proc residual stated; AGENTS.md append section CI_PARITY_HOSTED_CLAUDE_V1; ops/secrets/README.md; skills/l9-aws-secrets/SKILL.md."
    status: pending
    phase: execute
    depends_on: []
  - id: T6
    content: "Create ops/ci_parity/run.py: table-driven lanes (fast: ruff, shellcheck, actionlint, zizmor --offline, yamllint, biome; heavy: codeql database create+analyze with .github/codeql/codeql-config.yml, semgrep-pro via T5, semgrep-l9-analysis parity with identity-map strict, osv-scanner + pip-audit only when lockfiles change); scan in a per-repo snapshot clone (`git clone --shared` under ~/.cache/l9-ci-parity/<repo>/clone, flock-serialised detached checkout) so the worktree is never read mid-edit or dirtied; weighted CPU semaphore <= nproc with nice 10; latest-wins cancellation of older-sha runs per repo; receipts keyed by (sha, lane, tool version, config digest) under ~/.cache/l9-ci-parity/<repo>/<sha>/. Modes: --file PATH (edit-time), --commit SHA --background (setsid), --gate SHA (consume receipts, wait on in-flight up to L9_CI_PARITY_WAIT, run missing lanes, exit 2 on blocking new findings), --status. Kill switch L9_CI_PARITY=0."
    status: pending
    phase: execute
    depends_on: [T1, T4, T5]
  - id: T7
    content: "Resolve U3 then create ops/ci_parity/sonar_status.py: SONAR_TOKEN bound in-process (capability_bind) and sent only via safe_https to sonarcloud.io; read-only project_status + issues for the PR (pullRequest=N) into a receipt; post-push lane. If /api/ce/activity shows analysis failing on missing source dir `hooks`, remove it from sonar.sources in both properties files."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T8
    content: "Create Claude hooks: ci_parity_posttool.py (PostToolUse Edit|Write|MultiEdit -> run.py --file, findings as additionalContext; PostToolUse Bash on successful `git commit` -> run.py --commit HEAD --background) and ci_parity_push_gate.py (PreToolUse Bash `git push` -> run.py --gate HEAD; deny with a compact finding list on blocking new findings; SKIP-with-notice when tools absent; exit 0 silently on any non-Claude surface incl. CURSOR_AGENT). Register via l9_hook_exec.sh in settings.template.json, re-project .claude/settings.json, mirror .claude/hooks."
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T9
    content: "Add a Claude-guarded `_wave_start ci-parity` entry to ops/scripts/run_pr_gate.sh parallel reader wave (runs run.py --gate HEAD niced so pytest keeps priority; guard = l9_is_claude_gate_surface && tools present && L9_CI_PARITY!=0) and add ops/ci_parity/*.py, tools.yaml and lane configs to _GATE_CODE_FILES."
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T10
    content: "Docs + environment: network-policy.md adds app.infisical.com, semgrep.dev, sonarcloud.io, GitHub release asset hosts; web/README.md describes the tools, timing tiers and kill switch; environment.env.example documents optional L9_CI_PARITY / L9_CI_PARITY_WAIT; recommend narrowing the claude-code identity from project Viewer to Additional Privileges on SEMGREP_APP_TOKEN, SONAR_TOKEN, CONTEXT7_API_KEY."
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T11
    content: "Cut CI minutes: add `concurrency: {group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}, cancel-in-progress: ${{ github.event_name == 'pull_request' }}}` to the six PR-triggered workflows that lack one; validate with actionlint, zizmor --offline and validate_workflow_action_pins.py."
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T12
    content: "Parity proof: run `run.py --gate` on 745a1b06 and 29c767df in the snapshot clone; record the CodeQL/semgrep verdicts next to the CI verdicts for those heads in ops/ci_parity/README.md and the PR body."
    status: pending
    phase: execute
    depends_on: [T6, T3]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Claude Code CI-parity scanners with Infisical-bound paid tiers

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `claude-code-ci-parity-scanners-with-infisical-bound-paid-tiers_def06daf.plan.md`

## Objective (from PLAN_DOCUMENT)

In hosted Claude Code sessions only (Cursor untouched), install CI-parity scanners pinned to the versions CI actually runs (CodeQL CLI 2.27.0, Semgrep 1.178.0 incl. Semgrep Pro via SEMGREP_APP_TOKEN, Biome 2.5.5, pip-audit 2.10.1) plus actionlint, zizmor, shellcheck, osv-scanner and yamllint, bind the paid-tier tokens (SEMGREP_APP_TOKEN, SONAR_TOKEN) from Infisical project cursor-governance through the claude-code machine identity without ever placing them in the ambient environment, argv, files, logs or chat, and run every scanner automatically at the cheapest moment that still precedes the push (edit, commit, pre-push, post-push), concurrently under a CPU budget and without touching the working tree, so CI-only findings stop costing push-and-wait cycles.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | A fresh hosted Claude session reaches `python3 ops/ci_parity/install.py --check` = all 10 tools present at tools.yaml versions with sha256-verified binaries, with no manual step by the user beyond setting L9_INFISICAL_CLIENT_ID / L9_INFISICAL_CLIENT_SECRET | filesystem | `install.py --check` → 10/10 OK at pinned versions | true |
| SP-02 | Replaying #659 commit 745a1b06 through `ops/ci_parity/run.py --gate` reports the same CodeQL py/clear-text-logging-sensitive-data alerts CI reported on that head, and 29c767df reports zero new blocking CodeQL findings (discriminating parity proof) | runtime_behavior | replay `run.py --gate` 745a1b06 vs 29c767df against CI verdicts | true |
| SP-03 | The Semgrep Pro lane runs `semgrep ci --dry-run` with SEMGREP_APP_TOKEN bound from Infisical; canary tests prove the token value never appears in argv, the ambient/session environment, stdout, stderr, receipts, or any file | runtime_behavior | canary token absent from argv/env/stdout/stderr/receipts/files | true |
| SP-04 | Edit-time single-file lanes return feedback in <= 3 s p95; commit-time heavy lanes run detached; `make pr` on a Claude surface adds <= 15 s when a receipt for HEAD exists | runtime_behavior | hook timing log p95; `.l9/pr/gate-timing.json` | true |
| SP-05 | The push gate denies a push whose diff introduces a blocking new finding in changed lines, allows a clean diff, and never blocks on findings outside changed lines | runtime_behavior | push-gate state-machine tests | true |
| SP-06 | With CURSOR_AGENT=1 (Cursor surface) every new hook exits 0 with no output and the make pr wave list is byte-identical to main; `git diff origin/main... -- environment/agents/adapters/cursor ops/hooks .cursor` is empty | structural | CURSOR_AGENT=1 invariance tests + empty Cursor-path diff | true |
| SP-07 | Six PR-triggered workflows without a concurrency group gain cancel-superseded-PR-run groups and pass actionlint + zizmor --offline + validate_workflow_action_pins.py | quality_gate | actionlint + zizmor --offline + validate_workflow_action_pins.py | true |

## Scope (from PLAN_DOCUMENT)

**In:** ops/ci_parity/ engine: tools.yaml pin manifest, install.py, findings.py (diff-range filter + normaliser), run.py (lanes, scheduler, snapshot clone, receipts), sonar_status.py, lane configs, README, ops/secrets/capability_exec.py + capability-exec.json allowlisted exec broker (single entry: semgrep ci --dry-run) and its doctrine amendment, Claude adapter wiring: web/setup.sh install step, hooks/session_deps_cloud.sh self-heal, new PostToolUse/PreToolUse hooks, settings.template.json + projected .claude/settings.json, Claude-guarded ci-parity wave entry in ops/scripts/run_pr_gate.sh + _GATE_CODE_FILES, CI minutes: concurrency groups on codeql.yml, governance-self-check.yml, governance.yml, repo-hygiene.yml, validate-org-policy.yml, claude-preservation.yml, SonarCloud root-cause fix in sonar-project.properties + .sonarcloud.properties if probe U3 confirms, Docs: AGENTS.md append section, ops/secrets/README.md, capabilities.yaml semgrep entry, web/network-policy.md, web/README.md, environment.env.example, skills/l9-aws-secrets/SKILL.md

**Out:**
- Any Cursor surface file or behaviour: environment/agents/adapters/cursor/, ops/hooks/, .cursor/, Cursor AWS seed path (aws_cli_preflight.py, login_registry.py, allow_aws_seed branch of infisical_cli_login.py)
- Adding the new tools as CI jobs (would change every surface's PR checks; separate decision)
- Changing ops/scripts/run_pr_security.sh community Semgrep lane, .pre-commit-config.yaml, uv.lock, pyproject.toml, requirements.txt
- .gitleaks.toml zero-rules defect (queued as separate task task_fe02e326: shared gate)
- Running sonar-scanner locally (it publishes an analysis; SonarCloud stays CI/automatic-owned)
- Claude Code Desktop tool installation (hooks degrade to SKIP when tools are absent)
- Weakening any CI check, required context, or reducing CI rigor on the basis of local receipts

## Critical path (seed)

T1 → T4 → T5 → T6 → T8 → T9 → T12

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Hosted Claude sessions: a faulty push gate can block pushes and a faulty post-edit hook can slow edits; a secret-handling defect in capability_exec could expose SEMGREP_APP_TOKEN in output. The make pr gate changes only on Claude surfaces. CI concurrency groups affect every PR's superseded runs. Cursor is unaffected by construction.
- Rollback: Immediate: set L9_CI_PARITY=0 (disables hooks and the gate wave without a revert). Full: revert the PR; installed binaries are inert under ~/.local/share/l9-ci-parity and ~/.cache/l9-ci-parity and are removed by explicit path; rotate SEMGREP_APP_TOKEN in Infisical if any canary test ever fails post-merge.

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: plan validated structurally; U1-U3/U5 are execution-time probes with defined fallbacks; P5 needs the user to set the claude-code identity in the environment before secret lanes can be proven live
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: Claude Code CI-parity scanners with Infisical-bound paid tiers

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` · machine artifact `claude_ci_parity_tools_ab59bce0.plan.json` (validate_plan_document.py PASS)
> **Execute:** press **Build**; stack on the unique open-PR tip (#659 `feat/infisical-without-aws`, `PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.

Chain tip for this plan: this work depends on #659 (Infisical env identity in `capability_bind`, `session_start_secrets` Claude path). Stack on `feat/infisical-without-aws`. Sibling chain #651 → #652 → #657 is disjoint from every path in the write envelope below.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.claude_code.ci_parity_tools.v1` |
| name | Claude Code CI-parity scanners with Infisical-bound paid tiers |
| overview | *(same as frontmatter `overview`)* |
| schema_version | `1.0.0` |
| status | `draft` — becomes `executable` when CP-01..CP-04 pass at Build start |
| is_project | `false` |
| owner | igor_beylin (human) · executor: Claude Code hosted session |
| created_at | `2026-09-24` |
| updated_at | `2026-09-24` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `AGENTS.md` (append section `CI_PARITY_HOSTED_CLAUDE_V1`, created by T5) · `ops/ci_parity/README.md` · `ops/secrets/capabilities.yaml` |
| plan_class | `integration_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | GAR run: depth **DEEP** (security boundary, concurrency, cross-module). MEMORY_PREFETCH namespace=cursor-governance digest 81ee1855… conflicts=0. |

### GAR decision record

**Objective (derived):** realization_mode `MUTATION`; validation_required `true`; delivery = stacked PR via `make pr`.

**Candidates.**

| id | Candidate | Verdict |
|----|-----------|---------|
| A | Pre-push-only wrapper: run every scanner synchronously inside `make pr` | Rejected. CodeQL alone is ~2 min on 4 CPU and would serialize behind pytest (106 s). It also misses remediator pushes that bypass `make pr`. |
| B | **Tiered, receipt-driven engine** (`ops/ci_parity`): fast lanes at edit time; heavy lanes detached at commit time in a snapshot clone; receipts consumed by the `make pr` wave and a PreToolUse push gate; Sonar read post-push | **Selected.** It hides latency behind work the agent already does, never touches the worktree, has one receipt owner (the key is the invalidation owner), and is Claude-only by wiring rather than by forking. |
| C | Add the new tools as CI jobs and keep local unchanged | Rejected for this plan. It changes every surface's PR checks (Cursor included) and does not reduce push-and-wait cycles. Kept as a follow-on. |

**Paid-tier secret sub-decision.**

| id | Candidate | Verdict |
|----|-----------|---------|
| S1 | Put SEMGREP_APP_TOKEN in the ambient session env | Rejected. It violates the secret plane; the stub deliberately unsets it. |
| S2 | Re-implement Semgrep's private API in-process to prefetch rules and the Pro engine | Rejected. This is KP-003 (copied brain) and depends on an unknown, undocumented API. |
| S3 | **Allowlisted `capability_exec`**: a fixed-argv registry entry; the token is bound in-process and placed only in that one child's environment; output is scrubbed | **Selected.** It is the smallest governed extension of the vault-bridge precedent. The residual (`/proc/<pid>/environ` is readable while semgrep runs) is the same class as the bridge's in-process key and is stated in the amendment. |
| S4 | Sonar through a local `sonar-scanner` run | Rejected. It publishes an analysis. Sonar gets an in-process read-only API client instead (no child env). |

**Kill-pattern screen:**
- KP-001/002 (duplicate SSOT or shadow owner): avoided. Pins live only in `tools.yaml`, and the CE Semgrep lane in `run_pr_security.sh` is untouched.
- KP-008 (cache without an invalidation owner): avoided. The receipt key is (sha, lane, tool version, config digest).
- KP-010 (silent fallback): avoided. A missing tool is an explicit SKIP with a notice.
- KP-011 (tautological verification): avoided. SP-02 is a replay against CI's recorded verdicts.

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | 2026-09-24T16:10Z |
| repository | `Quantum-L9/Cursor-Governance` (public) |
| workspace | `/home/user/wt-infisical` (hosted Claude) |
| ssot_clone | `/root/.cursor-governance` @ main 69a25a1 (read-only for this plan) |
| branch | `feat/infisical-without-aws` (PR #659, CI green on head) |
| commit_sha | `29c767df88b7c1c821cd2c7399f19f8f4d37a2c4` |
| dirty | `false` |
| artifact_hashes | recorded at Build start for `ops/scripts/run_pr_gate.sh`, `.claude/settings.json`, `environment/agents/adapters/claude-code/settings.template.json` |
| allowed_local_dirt | none |
| overlap_policy | `require_clean_tree` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` (if #659 head moves: re-stack on the new tip, re-run CP-01) |

## Objective

### Mission

**Residual defect.** Hosted Claude sessions have none of the scanners CI runs:
- CodeQL, Semgrep beyond CE, Biome and pip-audit only partially;
- actionlint, zizmor, shellcheck, osv-scanner and yamllint not at all.

So CI is the first place findings appear. On #659 that cost three push-and-wait rounds of CodeQL.

**Bound.** Hosted Claude Code sessions: the installer, hooks, a Claude-guarded `make pr` wave, and a Semgrep Pro exec broker. Plus two small shared fixes:
- concurrency groups on CI workflows;
- the SonarCloud source list.

**Preserved, non-negotiable:**
- Cursor behaviour stays byte-identical.
- CI stays authoritative and unweakened.
- Tokens never enter the ambient env, argv, files, logs, receipts or chat.
- Scanners never write inside the worktree.
- Publication goes only through `make pr`.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Fresh hosted session installs all 10 tools at manifest versions, sha256-verified, with no manual step | `filesystem` | `ops/ci_parity/install.py --check` → `10/10 OK`, each line `tool=<name> version=<pinned> sha256=verified` | true |
| SP-02 | Local verdicts reproduce CI's on real heads | `runtime_behavior` | `run.py --gate 745a1b06` lists the py/clear-text-logging-sensitive-data alerts CI raised on that head; `run.py --gate 29c767df` → `blocking_new=0` | true |
| SP-03 | Semgrep Pro runs with the Infisical token and never leaks it | `runtime_behavior` | `test_capability_exec.py` canary: the token is absent from argv, os.environ, stdout, stderr, receipts and every file under the output dir; a live run records `source=infisical` | true |
| SP-04 | Latency budget holds | `runtime_behavior` | hook timing log: fast lane p95 ≤ 3 s over 20 edits; `.l9/pr/gate-timing.json` ci-parity ≤ 15 s with receipt hit | true |
| SP-05 | Push gate blocks only new blocking findings in changed lines | `runtime_behavior` | `test_ci_parity_hooks.py` state machine: new-finding → deny; clean → allow; pre-existing outside diff → allow; tools absent → SKIP notice | true |
| SP-06 | Cursor untouched | `structural` | `CURSOR_AGENT=1` invariance tests (no output, exit 0; gate wave list identical) + `git diff --stat origin/main... -- environment/agents/adapters/cursor ops/hooks .cursor` empty | true |
| SP-07 | Superseded PR CI runs are cancelled | `quality_gate` | actionlint + `zizmor --offline` + `validate_workflow_action_pins.py` clean on the six workflows; next PR push shows the prior run `cancelled` | true |
| SP-08 | Repository gate green | `quality_gate` | `OPEN_PR=0 make pr` PASS; `.pre-commit-config.yaml` hook catalog green | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` inline (below)

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.claude_code.ci_parity_tools.v1` |
| source_ref | `plan.claude_code.ci_parity_tools.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | Immutable baseline section |
| baseline_verified | pending (Build start) |
| drift_detected | pending |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` on the #659 tip | equals current `origin/feat/infisical-without-aws` | true |
| CP-02 | `network_read` | GET a GitHub release asset, pypi.org, registry.npmjs.org, sonarcloud.io, semgrep.dev, app.infisical.com | HTTP 2xx/206 for each (HEAD is 403 on the proxy: use GET) | true |
| CP-03 | `secret_bind` | `capability_bind.py --check SEMGREP_APP_TOKEN` and `--check SONAR_TOKEN` | `source=infisical` for both | false (blocks only the Semgrep Pro and Sonar lanes; they stay SKIP until the user sets the identity) |
| CP-04 | `filesystem_write` | write probe to `~/.local/share/l9-ci-parity` and `~/.cache/l9-ci-parity` | writable, ≥ 20 GB free | true |
| CP-05 | `probe U1` | in a scratch snapshot: `capability_exec semgrep-pro` on 29c767df | SARIF written; semgrep.dev shows no new scan | false (U1 decides block vs advisory) |
| CP-06 | `probe U3` | `sonar_status.py --ce-activity` (in-process token) | failing task message captured | false |
| CP-07 | `probe U2` | request read scope for `Quantum-L9/l9-ci-core` once | pinned central policy readable, or recorded as residual | false |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:**
  - `ops/ci_parity/**`, `tests/ops/ci_parity/**`
  - `ops/secrets/capability_exec.py`, `ops/secrets/capability-exec.json`, `ops/secrets/capabilities.yaml`, `ops/secrets/README.md`, `tests/ops/secrets/test_capability_exec.py`
  - `ops/scripts/run_pr_gate.sh`, `tests/ops/scripts/test_run_pr_gate_ci_parity.py`
  - `environment/agents/adapters/claude-code/**`, `.claude/settings.json`, `.claude/hooks/**`
  - the six named `.github/workflows/*.yml`
  - `sonar-project.properties`, `.sonarcloud.properties`
  - `AGENTS.md` (append-only tail)
  - `skills/l9-aws-secrets/SKILL.md`
  - generated projections regenerated by `sync_generated_artifacts.py --force`
  - outside the repo: `~/.local/share/l9-ci-parity/**`, `~/.local/bin/<tool>` symlinks, `~/.cache/l9-ci-parity/**`
- **write_deny:**
  - `environment/agents/adapters/cursor/**`, `ops/hooks/**`, `.cursor/**`
  - `ops/secrets/{aws_cli_preflight,login_registry,infisical_cli_login}.py`
  - `ops/scripts/run_pr_security.sh`, `.pre-commit-config.yaml`, `.gitleaks.toml`
  - `uv.lock`, `pyproject.toml`, `requirements.txt`, `CANONICAL_LAW.md`, `Makefile`
  - any `.env*`, Docker or infra file
- **delete_allow:** none in the repo; outside it, only `~/.cache/l9-ci-parity/<repo>/<sha>` receipts beyond the newest 5 (explicit paths, never a glob with an empty variable)

### Commands

- **allow:**
  - `uv tool install <pkg>==<ver>`
  - `curl -sSL` GET of the pinned release assets, verified with `sha256sum -c`
  - `git clone --shared` into `~/.cache/l9-ci-parity`
  - the scanners in read mode
  - `python3 -m pytest` on named test paths
  - `OPEN_PR=0 make pr`, `l4_local.py authorize-release`, `PR_STACK=auto PR_REMEDIATE=0 make pr`
- **deny:**
  - force-push, hard-reset, `git worktree add` (use a clone)
  - `sonar-scanner` (it publishes)
  - `semgrep ci` without `--dry-run`
  - `hydrate --export`, printing any secret, `pip install` into the governance venv, edits to CI required contexts

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | github.com + release-asset hosts, pypi.org, files.pythonhosted.org, registry.npmjs.org, app.infisical.com, semgrep.dev (dry-run config fetch only), sonarcloud.io (GET only) |

### Secrets

| Field | Value |
|-------|-------|
| access | `runtime_injected_only`: SEMGREP_APP_TOKEN (child env of the one registered semgrep invocation), SONAR_TOKEN (in-process header only), via `capability_bind` as the `claude-code` Infisical identity |
| redaction_required | `true`. Literal-only diagnostics; output withheld when it echoes the token. |

### Autonomous merge

`autonomous_merge:` `false`. The finish state is a green, merge-ready PR. Merging happens only through `/l9-pr-remediation`, which the user invokes.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1, T4, T6, T7, T8, T9, T10 | `filesystem_mutation` | `safe_to_repeat` | `bounded_retry` | revert scoped paths | false |
| T2, T3 (install) | `network_read`, `filesystem_mutation` (home dir) | `safe_with_dedupe` (version probe + flock) | `retry_once` per asset | delete `~/.local/share/l9-ci-parity/<tool>/<ver>` by explicit path | false |
| T5 | `filesystem_mutation`; runtime `network_read` (Infisical, semgrep.dev) | `safe_to_repeat` | `none` on secret errors | revert; rotate the token if a canary ever fails | false |
| T7 (runtime) | `network_read` (sonarcloud.io GET) | `safe_to_repeat` | `retry_once` | none | false |
| T11 | `filesystem_mutation` (CI config) | `safe_to_repeat` | `none` | revert the workflow hunks | false |
| T12 | `filesystem_read`, local CPU | `safe_to_repeat` | `retry_once` | none | false |
| publish | `network_write` (push + PR via `make pr`) | `safe_with_dedupe` | `manual_only` | close the PR | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1, T2, T4, T6 | ci-parity engine | `assurance` | `ops/ci_parity/README.md` + `tools.yaml` | second pin location; writing inside the worktree |
| T5 | secret plane | `policy` | `ops/secrets/capabilities.yaml` + AGENTS.md `CI_PARITY_HOSTED_CLAUDE_V1` | generic exec; caller-supplied argv; ambient env |
| T3, T8 | Claude adapter | `ops` | `environment/agents/adapters/claude-code/SESSION_START_SPEC.md`, `l9_hook_exec.sh` | new SessionStart hook; blocking SessionStart |
| T9 | PR gate | `control_plane` | `ops/scripts/run_pr_gate.sh` | any change visible on non-Claude surfaces |
| T11 | CI | `assurance` | `.github/workflows` | changing required contexts, triggers or path filters |
| T7 | Sonar read | `external_system` | `sonar-project.properties` | publishing analyses |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` inline

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.claude_code.ci_parity_tools.v1` |
| source_execution_ref | `plan.claude_code.ci_parity_tools.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | push gate false-blocks; token canary failure; CI-parity wave regresses make pr beyond budget; Cursor invariance test fails |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | whole PR, or per-todo commits |
| data | `none` | |
| external_state | `manual_recovery` | rotate SEMGREP_APP_TOKEN / SONAR_TOKEN in Infisical if exposure is ever suspected |
| local_state | `manual_recovery` | `L9_CI_PARITY=0` immediately; remove `~/.local/share/l9-ci-parity` and `~/.cache/l9-ci-parity` by explicit path |

### Irreversible operations

- none

### Rollback verification

- With `L9_CI_PARITY=0`: the hooks print nothing, the gate wave list equals main's, and the push is allowed (the same tests as SP-05/SP-06 with the switch set).

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` |
| uncertainty | `medium` (U1–U3, U5 are bounded probes with fallbacks) |
| blast_radius | `medium` |
| architectural_boundaries_crossed | `3` (secret plane, Claude adapter, PR gate) |
| external_systems_touched | `4` (Infisical, semgrep.dev, sonarcloud.io, GitHub releases) |
| migration_required | `false` |
| unknown_dependency_count | `4` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated: this change retires nothing. The `capabilities.yaml` semgrep entry is amended in place, not retired.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated: no irreversible or external writes. Semgrep runs `--dry-run` and Sonar is GET-only.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` inline — acyclic

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.claude_code.ci_parity_tools.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| PF | agent | assurance | [] | CP-01..CP-07 receipts |
| T1 | agent | assurance | [PF] | tools.yaml, validate_manifest.py |
| T5 | agent | policy | [PF] | capability_exec + amendment |
| T2 | agent | assurance | [T1] | install.py |
| T4 | agent | assurance | [T1] | findings.py |
| T7 | agent | external_system | [T1] | sonar_status.py (+ properties fix) |
| T3 | agent | ops | [T2] | setup.sh / deps-worker wiring |
| T11 | agent | assurance | [T2] | workflow concurrency |
| T6 | agent | assurance | [T1, T4, T5] | run.py, receipts |
| T8 | agent | ops | [T6] | hooks + settings projection |
| T9 | agent | control_plane | [T6] | gate wave entry |
| T10 | agent | docs | [T6] | docs/env |
| T12 | agent | assurance | [T6, T3] | parity replay evidence |
| PUB | agent | control_plane | [T8, T9, T10, T11, T12, T7] | PR URL |

**Critical path:** `PF` → `T1` → `T4` → `T6` → `T8` → `T9` → `T12` → `PUB`. T5 runs in parallel with T1→T4 and joins at T6.

**Forbidden edges:**
- T8 or T9 before T6 (hooks with no engine).
- PUB before V6 (Cursor invariance) passes.

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` inline

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `structural_evidence` | installer check | `python3 ops/ci_parity/install.py --check` | `10/10 OK` with pinned versions | `not_run` |
| EV-SP-02 | SP-02 | `runtime_behavior_evidence` | replay vs CI verdicts | `run.py --gate 745a1b06` / `--gate 29c767df` | CI's alert rule ids at the same paths / `blocking_new=0` | `not_run` |
| EV-SP-03 | SP-03 | `property_evidence` | canary token | `pytest tests/ops/secrets/test_capability_exec.py` | canary absent from every sink | `not_run` |
| EV-SP-04 | SP-04 | `runtime_behavior_evidence` | timing | hook timing log + `.l9/pr/gate-timing.json` | ≤ 3 s p95 / ≤ 15 s | `not_run` |
| EV-SP-05 | SP-05 | `runtime_behavior_evidence` | state machine | `pytest environment/agents/adapters/claude-code/tests/test_ci_parity_hooks.py` | 4 transitions as specified | `not_run` |
| EV-SP-06 | SP-06 | `structural_evidence` | invariance | `CURSOR_AGENT=1` tests + `git diff --stat origin/main... -- environment/agents/adapters/cursor ops/hooks .cursor` | empty diff, silent hooks | `not_run` |
| EV-SP-07 | SP-07 | `quality_gate_evidence` | workflow lint | `actionlint`, `zizmor --offline`, `validate_workflow_action_pins.py` | 0 errors | `not_run` |
| EV-SP-08 | SP-08 | `quality_gate_evidence` | catalog | `OPEN_PR=0 make pr` (`.pre-commit-config.yaml` catalog) | gate PASS | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Local full-database CodeQL flags pre-existing alerts that CI's pr-diff-range hides → T4's diff-range filter must make 29c767df clean, or the lane stays advisory.
- Heavy lanes during `make pr` push the gate past today's ~120 s → receipts from commit-time runs plus `nice 10` must hold the wave at +15 s.
- `/proc/<pid>/environ` exposes SEMGREP_APP_TOKEN during the run → a bounded residual, stated in the amendment. It is never logged, and the child's lifetime is one scan.
- A PreToolUse push gate reads as a "workflow deny" of the remediator's push (rule zz §2a) → it denies only on blocking new findings (checker semantics). Absent tools are a SKIP, and the kill switch is honoured.
- CI's floating L9 Analysis Semgrep (`>=1.100,<2`) drifts from the 1.178.0 pin → a recorded residual. The drift validator covers the pinned CodeQL and Biome refs.
- The hosted setup snapshot (~7-day cache) keeps stale tools after a manifest bump → the deps-worker self-heal compares versions every session.

### Assumption failure conditions

- The dirty tree overlaps `write_allow` (policy `require_clean_tree`) → stop.
- #659's head moves → re-stack, re-run CP-01.
- A blocking success property fails after mutation.
- An unknown dependency surfaces mid-flight (PLAN-SCHEMA-013) → record it and stop the affected lane.
- The claude-code identity lacks read on SEMGREP_APP_TOKEN / SONAR_TOKEN → the Pro and Sonar lanes stay SKIP and are reported, never pasted.

### Blast radius notes

- Hosted Claude sessions: edit latency, the push path and `make pr` on Claude surfaces.
- CI: superseded PR runs are cancelled on six workflows (all PRs, all surfaces). No required context changes.
- Cursor: none. `.claude/settings.json` is loaded by Cursor, but every new hook exits silently on non-Claude surfaces, and SP-06 proves it.

### Rollback constraints

- No force-push or history rewrite.
- Secret exposure is not reversible by revert; rotating in Infisical is the compensation.

## Out of scope

- The Cursor adapter, `ops/hooks`, `.cursor`, and Cursor's AWS seed path.
- New CI jobs for actionlint, zizmor, shellcheck, osv-scanner or yamllint.
- `.gitleaks.toml` zero-rules defect (queued separately: task_fe02e326).
- `run_pr_security.sh` CE Semgrep lane, `.pre-commit-config.yaml`, `uv.lock`, `pyproject.toml`, `requirements.txt`.
- Local `sonar-scanner` runs; Claude Code Desktop installs.
- Force-push, hard-reset, admin-merge, secret exfil; weakening scanners or gates to obtain a PASS.

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | Add actionlint, zizmor, shellcheck and osv-scanner as advisory CI jobs, then blocking once their debt is burned down | quality for every surface, Cursor included |
| P1 | Narrow the `claude-code` Infisical identity from project Viewer to Additional Privileges on the 3 names | least privilege |
| P2 | Offer the same `ops/ci_parity` engine to Cursor as opt-in (the user decides) | parity across peers |
| P2 | Bump `codeql.yml`'s reusable pin to the local v4.38.1 and re-pin the manifest | removes the known drift |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` inline

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.claude_code.ci_parity_tools.v1` |
| source_ref | `plan.claude_code.ci_parity_tools.v1` |
| current_state | `draft` |
| implementation_ready | `false` until CP-01, CP-02 and CP-04 pass at Build start |

### Gates

- **executable_when:**
  - the baseline is re-verified on the #659 tip;
  - CP-01, CP-02 and CP-04 pass;
  - the DAG is acyclic (it is);
  - the envelope and side-effect matrix are complete (they are);
  - no blocking unknowns remain (U1–U3 and U5 are non-blocking probes with fallbacks).
- **complete_when:**
  - EV-SP-01 … EV-SP-08 have `passed`;
  - the rollback contract is still valid;
  - out_of_scope is respected (V6 empty diff).
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property
  - token canary failure

### Evidence

- **required_evidence_refs:** `EV-SP-01` … `EV-SP-08`
- **observed_evidence_refs:** *(fill during execution)*
- **missing_evidence:** EV-SP-02 and EV-SP-03 (live) need the user's claude-code identity in the environment (P5)

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| open_blocker | P5 | `L9_INFISICAL_CLIENT_ID` / `_SECRET` unset in this session; the screenshot shows identity `claude-code` never logged in | user: Universal Auth → create client secret → paste the client **ID** (the Universal Auth client id, not the identity id `2d879442…`) and the secret into the environment settings |
| unknown | U1 | Semgrep Pro dry-run parity with semgrep-cloud-platform/scan | probe CP-05 |
| unknown | U2 | central Core policy readable (l9-ci-core) | probe CP-07; else residual |
| unknown | U3 | SonarCloud idle since 2026-08-12 | probe CP-06 |
| unknown | U4 | identity is project Viewer (broad) | accept_bounded; follow-on P1 |
| unknown | U5 | environment networking Full vs Custom | probe CP-02 |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | When status=`executable`, press **Build** on the #659 tip (`PR_STACK=auto`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not free-form execute. |
| execute_via | Cursor Build; stacked PR on #659; display PR URL |
| broader_work_requires_separate_contract | `true` |
