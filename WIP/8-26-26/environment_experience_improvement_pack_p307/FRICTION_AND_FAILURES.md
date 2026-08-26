# Friction and Failures — Canonical Reconciliation

Corpus: 9 unique included versions, 2 byte-identical duplicate copies, 93 source objects. Recurring concepts are merged; source-specific observations remain as separate canonical records.

## Recurring failure classes

### CF-001 — GitHub GraphQL-dependent paths fail while REST can remain healthy
**Status:** ACTIVE_RECURRING
The environment repeatedly exposes a transport split: REST can work while GraphQL-backed gh operations, auth probes, PR commands, or merge helpers fail. Health checks and doctrine that collapse these into one GitHub state produce false diagnoses.
**Sources:** P1/failures/FAIL-01, P1/failures/FAIL-02, P1/failures/FAIL-03, P3/failures/FAIL-01, P4/failures/F-10, P7/failures/F-05, P8/failures/F-02, P9/failures/F-11, P9/failures/F-20

### CF-002 — Bootstrap projection violates consumer-repository ownership
**Status:** ACTIVE_CRITICAL
Session bootstrap can write, symlink, or project machine-local material into paths that a consumer repository already tracks. Pack 9 proves this can overwrite nine tracked .claude/rules files and leave a permanently dirty tree.
**Sources:** P3/failures/FAIL-02, P6/failures/FA-4, P9/failures/F-01

### CF-003 — Authority-sensitive environment drift persists without reachable repair
**Status:** ACTIVE_OPEN_DECISION
L9_AUTONOMY_AUTONOMOUS_MERGE repeatedly differs from the verifier expectation and the advertised repair path is not executable by the session. The intended value itself is not established by the corpus.
**Sources:** P3/failures/FAIL-06, P6/failures/FA-3, P8/failures/F-01, P9/failures/F-12

### CF-004 — Bootstrap health receipts become stale without re-probing degraded components
**Status:** ACTIVE_RECURRING
Bootstrap readiness can be structurally valid while runtime components remain degraded, and receipts can expire or survive restarts without regeneration or component re-probe.
**Sources:** P6/failures/FA-2, P8/failures/F-03, P9/failures/F-06

### CF-005 — Memory continuity is empty or internally contradictory
**Status:** ACTIVE_RECURRING
Hydration can carry no task-bearing state, writeback can produce zero durable writes, and aggregate memory health can disagree with the sanctioned Graphiti path.
**Sources:** P6/failures/FA-5, P6/failures/FA-6, P9/failures/F-04, P9/failures/F-07

### CF-006 — Capability broker path is degraded without cause discrimination
**Status:** ACTIVE_OPEN_UNKNOWN
Broker access fails at the network/proxy boundary, but the observed CONNECT failure does not distinguish proxy denial from upstream unavailability.
**Sources:** P1/failures/FAIL-05, P9/failures/F-08

### CF-007 — MCP responses can exceed the usable context/token envelope
**Status:** ACTIVE_RECURRING
Several MCP methods return payloads too large for the response budget, forcing diversion or loss of direct usability.
**Sources:** P1/failures/FAIL-06, P2/failures/FAIL-09, P7/failures/F-09

### CF-008 — Shell working-directory reset breaks relative-path operations
**Status:** ACTIVE_RECURRING
Independent shell invocations reset cwd, so relative commands can silently target the wrong place unless every governance/repo action receives an explicit target path.
**Sources:** P4/failures/F-01, P7/failures/F-07

### CF-009 — Fail-closed gates reject legitimate scoped operations without sufficiently actionable remediation
**Status:** ACTIVE_RECURRING
Safety gates correctly fail closed in ambiguous cases, but legitimate scoped cleanup/staging/compound operations can be rejected, diagnostic granularity is weak, and documented escape variables may be unreachable to the agent.
**Sources:** P1/failures/FAIL-07, P3/failures/FAIL-07, P4/failures/F-04, P4/failures/F-05, P7/failures/F-06, P8/failures/F-05, P8/failures/F-07, P9/failures/F-05, P9/failures/F-14

### CF-010 — Project interpreter and toolchain readiness do not reliably match repository requirements
**Status:** ACTIVE_RECURRING
PATH, system Python, project virtualenvs, pinned checker versions, and readiness banners can disagree. A tool being installed is not proof that the repository is importable or that CI-equivalent tools are selected.
**Sources:** P3/failures/FAIL-04, P3/failures/FAIL-05, P4/failures/F-03, P5/failures/FAIL-004, P7/failures/F-04, P9/failures/F-15

### CF-011 — Governance contracts require command surfaces absent from consumer repositories
**Status:** ACTIVE_OPEN_DECISION
The operating contract can name a mandatory local or publish entrypoint that the target repository does not implement, forcing off-doctrine workarounds or dead targets.
**Sources:** P3/failures/FAIL-09, P5/failures/FAIL-001, P5/failures/FAIL-003, P9/failures/F-10

### CF-012 — Concurrent branch writers cause non-fast-forward publication failures
**Status:** ACTIVE_RECURRING
Shared PR head branches can receive concurrent writes, invalidating local assumptions and causing repeated non-fast-forward push rejection.
**Sources:** P2/failures/FAIL-04, P7/failures/F-02

### CF-013 — Generated artifacts and manifest coupling make validation and merging fragile
**Status:** ACTIVE_RECURRING
Generated validation artifacts and manifests can fail on index/worktree mismatch, conflict during merge, or make release-readiness fail whenever files are added.
**Sources:** P2/failures/FAIL-02, P2/failures/FAIL-08, P8/failures/F-04

### CF-014 — MCP capability exposure is unstable or invalid across sessions
**Status:** ACTIVE_RECURRING
Declared MCP integrations can disappear, churn identities, fail schema parsing, require impossible interactive approval, or be loaded redundantly.
**Sources:** P4/failures/F-06, P6/failures/FA-7, P9/failures/F-03, P9/failures/F-16, P9/failures/F-18

## Context-specific failure observations

- **CF-100 — add_repo cannot attach a repository whose name begins with a dot**  
  Source: P1/failures/FAIL-04
- **CF-101 — Piping `git push` into `tail` masked a rejected push and reported success**  
  Source: P2/failures/FAIL-01
- **CF-102 — `git stash` / `git stash pop` silently discarded index staging**  
  Source: P2/failures/FAIL-03
- **CF-103 — `ruff format --check` failed on a file introduced by PR #64**  
  Source: P2/failures/FAIL-05
- **CF-104 — pytest: 5 failures, from two unrelated causes**  
  Source: P2/failures/FAIL-06
- **CF-105 — PR #70's CI never ran: every workflow was gated in `action_required`**  
  Source: P2/failures/FAIL-07
- **CF-106 — Bash quoting error passed a multi-word string as a single path**  
  Source: P2/failures/FAIL-10
- **CF-107 — Negative-control methodology error: `git stash` reverted the tests along with the fixes**  
  Source: P2/failures/FAIL-11
- **CF-108 — A regression test passed for the wrong reason because of an optional dependency**  
  Source: P2/failures/FAIL-12
- **CF-109 — git push returned INTERNAL_EVALUATION_ERROR from the worktree cwd**  
  Source: P3/failures/FAIL-03
- **CF-110 — Governance SSOT outside the session's GitHub scope while its rules are in force**  
  Source: P3/failures/FAIL-08
- **CF-111 — Governance CLI refused because it was invoked from the governance clone**  
  Source: P4/failures/F-02
- **CF-112 — Bash tool rejected commands containing control characters**  
  Source: P4/failures/F-07
- **CF-113 — Foreground sleep blocked**  
  Source: P4/failures/F-08
- **CF-114 — In-place edit script aborted because its anchor text did not match**  
  Source: P4/failures/F-09
- **CF-115 — bootstrap.sh aborts on its first copy**  
  Source: P5/failures/FAIL-002
- **CF-116 — GH_TOKEN invalid — sanctioned publish path cannot authenticate**  
  Source: P6/failures/FA-1
- **CF-117 — CI red on PR**  
  Source: P7/failures/F-01
- **CF-118 — make program-execution-adapters FAILED on pytest cache debris**  
  Source: P7/failures/F-03
- **CF-119 — deferred tool schemas not loaded — first TaskCreate call failed**  
  Source: P7/failures/F-08
- **CF-120 — Output sink refuses a destination directory that already exists**  
  Source: P8/failures/F-06
- **CF-121 — Harness stop hook demands a commit of bootstrap artifacts on every turn; complying would delete tracked files**  
  Source: P9/failures/F-02
- **CF-122 — CLAUDE_SESSION_JWT is unset, so every brokered MCP Authorization header expands empty**  
  Source: P9/failures/F-09
- **CF-123 — L4 release receipt is pinned to a head SHA that is no longer the branch tip**  
  Source: P9/failures/F-13
- **CF-124 — A one-time breakglass grant persists in the environment across container restarts**  
  Source: P9/failures/F-17
- **CF-125 — Skill usage logging captured one event across a multi-day session**  
  Source: P9/failures/F-19

## Recurring friction classes

### CR-001 — Stop-hook safety signal cannot distinguish authored work from bootstrap residue
**Status:** ACTIVE_RECURRING
The turn-ending hook treats bootstrap-owned residue as author work and repeatedly asks for commits that would violate repository ownership or delete tracked content.
**Sources:** P1/friction/FRICTION-01, P3/friction/FRIC-02, P9/friction/FR-10

### CR-002 — GitHub capability documentation disagrees with observed transport reality
**Status:** ACTIVE_RECURRING
Prompt/rule text can claim gh is unavailable while the CLI and REST path work, or otherwise disagree with the observed tool surface.
**Sources:** P1/friction/FRICTION-03, P3/friction/FRIC-10, P6/friction/FR-5

### CR-003 — make pr doctrine conflicts with repositories that do not define the target
**Status:** ACTIVE_OPEN_DECISION
An absolute publish-path rule and consumer repository Makefiles are not contractually aligned.
**Sources:** P1/friction/FRICTION-04, P6/friction/FR-2

### CR-004 — Hydration is capped, non-relevant, or tautological instead of task-bearing
**Status:** ACTIVE_RECURRING
Hydration can skip the target repo, omit the skipped set, or return only generic resume statements rather than actionable task state.
**Sources:** P1/friction/FRICTION-06, P4/friction/FR-07, P6/friction/FR-6, P7/friction/FR-05, P9/friction/FR-02

### CR-005 — Bootstrap degradation lacks reasons, retry guidance, and remediation
**Status:** ACTIVE_RECURRING
Degraded states recur without per-component cause, logs, or automatic re-probe/remediation, forcing raw receipt archaeology.
**Sources:** P1/friction/FRICTION-10, P3/friction/FRIC-06, P7/friction/FR-01, P8/friction/R-05, P9/friction/FR-03

### CR-006 — Shell cwd does not persist across command invocations
**Status:** ACTIVE_ENVIRONMENT_CONSTRAINT
The harness resets cwd between shell calls. This is documented behavior but becomes correctness friction when procedures assume persistent cd state.
**Sources:** P1/friction/FRICTION-07, P3/friction/FRIC-01

### CR-007 — One-time breakglass authority persists as standing configuration
**Status:** ACTIVE_RECURRING
A value explicitly described as one-time survives across sessions, making exceptional authority indistinguishable from baseline policy.
**Sources:** P1/friction/FRICTION-08, P6/friction/FR-4

### CR-008 — Interpreter and checker authority is fragmented across PATH, hooks, CI, and project envs
**Status:** ACTIVE_RECURRING
Multiple Python/checker versions and non-durable PYTHONPATH/PATH requirements create repeated setup cost and ambiguous validation authority.
**Sources:** P1/friction/FRICTION-13, P2/friction/FRIC-01, P2/friction/FRIC-02, P2/friction/FRIC-09, P3/friction/FRIC-03, P3/friction/FRIC-04, P5/friction/FR-003, P7/friction/FR-04, P8/friction/R-02, P9/friction/FR-05

### CR-009 — Destructive-path guardrails require fully literal targets
**Status:** ACTIVE_RECURRING
The guardrail evaluates command text and rejects same-line variable expansions even when the runtime value would be scoped. This is a usability constraint around an intentionally fail-closed boundary.
**Sources:** P1/friction/FRICTION-12, P9/friction/FR-07

### CR-010 — Multiple governance checkouts create wrong-tree risk
**Status:** ACTIVE_RECURRING
Two governance clones at different revisions coexist, making it easy to inspect or edit a non-authoritative tree.
**Sources:** P7/friction/FR-03, P8/friction/R-01, P9/friction/FR-04

### CR-011 — Queued notifications can arrive after their state has been superseded
**Status:** ACTIVE_RECURRING
Delayed notification/check-in delivery can present obsolete work as current without an obvious age signal.
**Sources:** P8/friction/R-08, P8/friction/R-09, P9/friction/FR-06

### CR-012 — Always-on rules can require capabilities the active surface does not expose
**Status:** ACTIVE_RECURRING
The projected rule corpus can mandate unavailable MCPs or mechanisms, leaving the rule in force but its prescribed execution path impossible.
**Sources:** P4/friction/FR-05, P9/friction/FR-01, P9/friction/FR-08

### CR-013 — Generated artifacts and clean-tree gates create regeneration churn
**Status:** ACTIVE_RECURRING
Tracked generated output and clean-tree-before-validate policies create regenerate/commit/revalidate loops and conflict risk.
**Sources:** P2/friction/FRIC-11, P4/friction/FR-01, P8/friction/R-03

### CR-014 — Variable-loading behavior is implicit, shell-sensitive, or multiply authoritative
**Status:** ACTIVE_RECURRING
Resolver scripts, interactive shell state, and multiple env authority files make effective values hard to reproduce and easy to lose in non-interactive commands.
**Sources:** P4/friction/FR-09, P4/friction/FR-10, P5/friction/FR-005, P6/friction/FR-7

### CR-015 — Local validation does not consistently mirror blocking CI
**Status:** ACTIVE_RECURRING
Hooks may be absent, local checker lists incomplete, or service-backed integration tests unavailable, so local green is not equivalent to merge-ready green.
**Sources:** P2/friction/FRIC-06, P2/friction/FRIC-08, P5/friction/FR-001, P9/friction/FR-09

### CR-016 — Wait and gate latency consume operator cycles
**Status:** ACTIVE_RECURRING
Foreground waits may be blocked and first-run gates can be slow, creating repeated polling or harness-specific workarounds.
**Sources:** P2/friction/FRIC-10, P4/friction/FR-02, P7/friction/FR-06, P7/friction/FR-07

## Context-specific friction observations

- **CR-100 — Bootstrap residue is gitignored in only some repos**  
  Source: P1/friction/FRICTION-02
- **CR-101 — L4 release receipt names a PR template path absent from the released repo**  
  Source: P1/friction/FRICTION-05
- **CR-102 — Drift report attributes a settings.json value to the account layer**  
  Source: P1/friction/FRICTION-09
- **CR-103 — MCP server identity is unstable across sessions**  
  Source: P1/friction/FRICTION-11
- **CR-104 — No variable-load script exists in this repository**  
  Source: P2/friction/FRIC-03
- **CR-105 — GH_TOKEN and GITHUB_TOKEN are set, but no gh CLI exists to consume them**  
  Source: P2/friction/FRIC-04
- **CR-106 — The repository's documented bootstrap path was never exercised; a parallel path was used instead**  
  Source: P2/friction/FRIC-05
- **CR-107 — CLAUDE.md's 'Live CI facts' understates the pre-commit hook set by 7 hooks**  
  Source: P2/friction/FRIC-07
- **CR-108 — Stale and obsolete paths encountered**  
  Source: P2/friction/FRIC-12
- **CR-109 — Two receipt scopes with no shared index**  
  Source: P3/friction/FRIC-05
- **CR-110 — L4 receipt stores a branch name that can go stale**  
  Source: P3/friction/FRIC-07
- **CR-111 — pytest summary line absent from captured stdout**  
  Source: P3/friction/FRIC-08
- **CR-112 — Governance revision moves mid-session**  
  Source: P3/friction/FRIC-09
- **CR-113 — Bootstrap receipt expired and is bound to a governance revision that is no longer checked out**  
  Source: P4/friction/FR-03
- **CR-114 — Account environment drift on a safety-relevant variable, with a manual-only repair**  
  Source: P4/friction/FR-04
- **CR-115 — Memory writes are read-only from the default working directory**  
  Source: P4/friction/FR-06
- **CR-116 — Editing was routed through shell heredocs rather than file-editing tools**  
  Source: P4/friction/FR-08
- **CR-117 — Context was lost and reconstructed mid-contract**  
  Source: P4/friction/FR-11
- **CR-118 — Duplicate user settings file in a non-effective location**  
  Source: P4/friction/FR-12
- **CR-119 — Superseded dependency stamps accumulate**  
  Source: P4/friction/FR-13
- **CR-120 — Environment supplies none of the application configuration**  
  Source: P5/friction/FR-002
- **CR-121 — Bootstrap entrypoint belongs to a different project**  
  Source: P5/friction/FR-004
- **CR-122 — Branch policy and actual work are disjoint**  
  Source: P5/friction/FR-006
- **CR-123 — TESTING=true is inert locally**  
  Source: P5/friction/FR-007
- **CR-124 — Core CLI tooling absent; GitHub work rerouted**  
  Source: P5/friction/FR-008
- **CR-125 — Build residue and duplicate config in the tree**  
  Source: P5/friction/FR-009
- **CR-126 — pip dependency backtracking during session-deps editable install**  
  Source: P6/friction/FR-1
- **CR-127 — Receipt CLI ergonomics — required --read flag is the only verb; 'status' rejected**  
  Source: P6/friction/FR-3
- **CR-128 — persistent account-field drift warning that a session cannot repair**  
  Source: P7/friction/FR-02
- **CR-129 — session wake resets create verification overhead for branch state**  
  Source: P7/friction/FR-08
- **CR-130 — GitHub API scope excludes repositories the task must read**  
  Source: P8/friction/R-04
- **CR-131 — Scratchpad artifacts needed for a repeatable run are not durable**  
  Source: P8/friction/R-06
- **CR-132 — TypeScript helpers need an import rewrite before Node can execute them**  
  Source: P8/friction/R-07
