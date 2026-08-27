# Environment Experience Improvement Pack — Progress

Assessed against **main@30c6ecd4 (post-#324/#325/#326/#327/#328 merge)** on 2026-08-27.
**CI-037** is new this pass (abandoned work fails closed instead of relying on doctrine).
**CI-001** and **CI-036** now name merge SHAs instead of "this branch" — both PRs landed.

**4 done · 15 partial · 19 not started** (of 38 records).

Previous pass (2026-08-27, main@8f73be9 (post-#320/#321 merge)): 3 done · 15 partial · 19 not started (of 37).
Pass before that (2026-08-26, main@78f122a (merged) + PR#307 open): 2 done · 9 partial · 25 not started.

> **Scope of this pass — targeted, not a re-assessment.** Only the records touched by #324
> and #325 were re-verified against the tree at `30c6ecd4`. Every other record carries its
> `main@8f73be9` judgement forward unchanged, and #326/#327/#328 were **not** assessed.
>
> The overlay was stale on arrival by **CI-034's own criterion** — it named `main@8f73be9`
> while main had advanced five merges. Third occurrence of that defect class, so
> `assessed_against_sha` is now recorded in `progress.yaml` rather than left proposed.
> CI-034 stays open: the drift *check* is still unbuilt, and recording the SHA without it
> only makes the staleness legible to a reader who thinks to compare.

Legend — **done**: merged and verified; **partial**: merged/open progress with a named residual; **not started**: not addressed yet. Rows marked _ext_ name a surface this org does not own (see *Proposed additions*). Rows marked ✱ were verified against the tree or the live container this pass; the rest carry their earlier assessment forward unchanged.

## What moved this pass

| Item | Was | Now | What changed |
|---|---|---|---|
| CI-037 | — | **done** ✱ | New. `rules/42-no-abandoned-work.mdc` + `ops/autonomy/session_debt.py` on the Stop hook as `--class gate`: exit 2 blocks a turn from ending over unpushed commits or open findings. Three standing rules that were doctrine only, and each of which failed on 2026-08-27, are now mechanical. `7ceeef38` (#324). |
| CI-001 | partial | **partial** ✱ | Unchanged in status; `delivered_by` resolved from the placeholder "this branch" to `be3f01c9` (#325, merge verb) + `7ceeef38` (#324, gate recognition of the REST merge). Residual is still IMP-01 only, still external. |
| CI-036 | partial | **partial** ✱ | Same: "This branch" resolved to `be3f01c9` (#325). A second, independent mechanism landed in #324 — a checker that does not trust local remote-tracking refs to *clear* it, because a cloud clone's single-branch refspec means `refs/remotes/origin/<feature>` never exists. Residuals unchanged. |
| CI-026 | not started | **done** | `Quantum-L9/.github` is attached: the clone is at `/home/user/.github` and the repo is in the session scope list. Was already true at 78f122a — the last pass did not check. |
| CI-001 | not started | **partial** | `5612f6b` gave `merge_gate._stacked_children` a REST transport and made the deny text name the blocked transport (IMP-11 + IMP-12, 229-line test). `gh_auth_probe.sh` (IMP-02) already existed at 78f122a. Only IMP-01, the session prompt, is left — and it is external. |
| CI-012 | not started | **partial** | PR#320 (merged 2026-08-27 as `c3ddeea`) makes an unevaluable `requires` precondition deny the capability instead of passing silently, and moves the generic adapter to the brokered front door. The `type` discriminator (I-BS-03) was already in the templates. |
| CI-017 | not started | **partial** | `7dc7e4f` moved the PE manifest from gate-time failure to commit-time heal — I-WT-03's shape, in the governance repo. The three named targets are untouched. |
| CI-029 | not started | **partial** | `tests/corpus_fixtures.py` persists a two-root corpus builder in l9-constellation-topology. Not proven to be I-WT-04's builder: `build_corpus.mjs` is absent and the committed fixture declares six formats, not eight. |
| CI-102 | not started | **partial** | `gh api user` returns `cryptoxdog` here and the stack probe answers over REST, so the blocked gate is unblocked — but by a third route that neither option (a) nor (b) records in any rule or profile. |

## Residuals that closed inside an existing status

- **CI-007** — the readiness `merge_authority` probe no longer crashes: the live receipt reports `merge_authority_status: READY` with the correct note. The stray env var is now `L9_AUTONOMY_AUTONOMOUS_MERGE=false`, not `=true`; still present, so the literal done_when is still unmet, but it no longer even nominally widens authority.
- **CI-015** — `read the SSOT's issues without add_repo` is now met: this session listed six open `Quantum-L9/Cursor-Governance` issues with no `add_repo` call. The duplicate-clone residual stands.
- **CI-009** — `interpreter_importable_status: READY` is live in the readiness receipt, so the merged importability probe is operative. The deps-banner residual is confirmed open: the log behind `toolchain ready` says only `install pass complete`.

## Sharpened with live evidence

- **CI-004** — the defect is reproducing right now. `bootstrap-state.json` is pinned to `governance_revision: c3081ee` (19:30) while `gov-refresh.json` (00:01) and `readiness-receipt.json` (23:23) both carry `498dcaa`. Two receipt stores disagree about the governance revision inside one session and nothing invalidated the stale one. One recorded residual was partly wrong: per-component log paths **do** exist for the deps stage (11 `deps-*.log` files); the gap is the other components.
- **CI-002** — unchanged and re-verified: `is_tracked` is called only in `reconcile_llm_rule_adapters.py`; `grep -c` returns 0 for all four remaining write sites and their last commit predates the guard. Phase 2c is unbuilt — `L9_AUTONOMY_STATE_DIR` still defaults inside the worktree.
- **CI-005** — confirmed not started, visibly: one collapsed `"memory": "DEGRADED"`, and `facts_returned=8` where all eight are self-referential PICKUP restatements. A hydration carrying no task state still reports as successful.
- **CI-101** — reproducing live: this session's branch directive names one branch across all ten in-scope repositories.

## Proposed additions

### CI-034 (P1) — Bind the progress overlay to a governance SHA and invalidate it on drift

**Why.** assessed_against was the prose label 'main@post-#307-merge'. main advanced 47 commits to 498dcaa and PR#320 opened; nothing marked the overlay stale, and six records were re-judged by hand to find it. This is CI-004's defect class — a receipt not bound to the revision it describes — applied to the pack itself. It recurred within the hour: this pack was rewritten at 498dcaa naming PR#320 as open, and PR#320 merged as c3ddeea before the overlay was published — stale again, by the same mechanism, on its second day.

**Change.** Record assessed_against_sha alongside the label, and add a check that compares it to the governance HEAD and reports the overlay stale when they differ.

**Done when.** A pack read at a governance revision other than assessed_against_sha reports itself stale before its counts are quoted.

### CI-035 (P1) — Cross-check the receipt stores against one another

**Why.** Live this session: bootstrap-state.json says governance_revision c3081ee while gov-refresh.json and readiness-receipt.json both say 498dcaa. CI-004 covers a receipt going stale against the world; nothing covers two concurrent receipt stores disagreeing with each other, which is the cheaper and more reliable detector.

**Change.** Have the readiness emitter compare governance_revision across every receipt under $HOME/.l9/claude and report a mismatch as a named DEGRADED dimension.

**Done when.** A bootstrap-state.json pinned to an older revision than gov-refresh.json produces a named readiness warning rather than silence.

_Fold into CI-004 instead if you prefer one record per defect class._

### Schema — `progress-schema/external-owner`

**Why.** CI-001 (IMP-01 session prompt), CI-003 (/root/.claude/stop-hook-git-check.sh), CI-011 (GitHub MCP server), CI-013 (IMP-10 harness tracker) and CI-020 (ReadNotifications envelope) all name surfaces this org does not own. They sit in the same not_started bucket as in-repo work that could ship tomorrow, so they never move and they inflate the not-started count.

**Change.** Add blocked_on: external to the progress block (or a status class EXTERNAL_BLOCKED) and report it as its own count, so 'not started' means 'startable and not started'.

### Verification hygiene

Two records were recorded not_started on 2026-08-26 for work already on disk at 78f122a: CI-001's IMP-02 leg (ops/scripts/lib/gh_auth_probe.sh) and CI-026 (the /home/user/.github clone). Populating each record's evidence list with the command that decides it makes the next pass re-runnable instead of re-judged.

## Next slice

**Ownership-aware writes (extend PR#307's is_tracked guard)**

Unchanged and now overdue: PR#307 merged the is_tracked() ownership guard on ONE write site and left the same-shape defect on the four others, verified again at 498dcaa. It is still the highest-value, lowest-risk next move — it reuses shipped code, is fully validatable in-repo with git fixtures, closes the biggest open P0 residual (CI-002), and folds in a P1 (CI-003) that shares the root cause.

- CI-002 residual (P0): apply is_tracked() before the remaining projection writes — claude_projection.py:422 (.mcp.json), reconcile_claude_l9_skills.py, reconcile_claude_commands.py, reconcile_claude_settings.py — and add Phase 2b (project to a non-owned sibling when the target is tracked). Verify the 8-fixture git-status-clean done_when.
- CI-003 (P1), re-scoped: the named target /root/.claude/stop-hook-git-check.sh is harness-owned. The in-repo lever is the .git/info/exclude glob list in ops/scripts/bootstrap_agent_environment.sh — add .claude/** and .mcp.json there, which --exclude-standard already honours.
- CI-031 (P3, opportunistic): keep tracked-path/gitignore hygiene synchronized as the guard and the ignore stanzas move together.

- _Excluded from this slice:_ CI-002 Phase 2c (L9_AUTONOMY_STATE_DIR relocation) touches l4_local.py + local_execution_gate.py + make pr together — sequence it as its own change.
- _Alternative slice:_ Receipt-integrity slice — CI-004's live revision disagreement plus the proposed CI-034 and CI-035. Small, in-repo, and it fixes the mechanism that let this overlay go stale unnoticed.

## Full status

| Progress | Item | P | Title | Delivered by / note |
|---|---|---|---|---|
| ✅ done | CI-007 | 0 | Replace standing breakglass environment strings with scoped expiring receipts ✱ | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| ✅ done | CI-026 | 3 | Support safe on-disk aliases for dot-prefixed repositories ✱ | Session repository scope (Quantum-L9/.github attached; clone at /home/user/.github) |
| ✅ done | CI-033 | 99 | Use pipefail in push/retry helpers | Pre-existing (already COMPLETED at pack generation) |
| 🟡 partial | CI-002 | 0 | Make bootstrap projection ownership-aware and non-destructive to tracked repo content ✱ | PR#304 (Contract 1) + PR#307 (CI-008/CI-009/CI-002 slice), both merged into main |
| 🟡 partial | CI-004 | 0 | Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components ✱ | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-006 | 0 | Resolve authority-sensitive environment drift at the actual source ✱ | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-008 | 0 | Reconcile make pr doctrine with consumer-repository command contracts ✱ | Quantum-L9/Cursor-Governance PR#307 (merged into main) |
| 🟡 partial | CI-009 | 0 | Establish one project interpreter/toolchain authority and verify importability before READY ✱ | Quantum-L9/Cursor-Governance PR#307 (merged into main) |
| 🟡 partial | CI-010 | 0 | Make broker authentication and reachability diagnosable ✱ | PR#305 (+ predecessor PR#304) and PR#320, all merged into main |
| 🟡 partial | CI-001 _ext_ | 1 | Publish and enforce the real GitHub REST/GraphQL capability boundary ✱ | `5612f6b` (probe) + `be3f01c9` (#325, merge verb) + `7ceeef38` (#324, gate recognition) + pre-existing ops/scripts/lib/gh_auth_probe.sh |
| 🟡 partial | CI-036 _ext_ | 2 | Keep unpushed-commit counts honest across merged-and-deleted branches ✱ | `be3f01c9` (#325, bootstrap prune + origin/HEAD) + `7ceeef38` (#324, checker independent of local refs) |
| ✅ done | CI-037 | 1 | Make abandoned work fail closed instead of relying on doctrine ✱ | `7ceeef38` (#324) — rule 42 + `ops/autonomy/session_debt.py` on the Stop hook as `--class gate` |
| 🟡 partial | CI-012 | 1 | Gate rules and MCP config on actual surface capabilities ✱ | Quantum-L9/Cursor-Governance PR#320 (merged as c3ddeea) + pre-existing adapter templates |
| 🟡 partial | CI-015 | 1 | Name and enforce the authoritative governance checkout ✱ | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-016 | 1 | Make L4/release receipts resolve paths, branch, and head dynamically ✱ | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-017 | 1 | Validate generated-artifact membership and report all drift in one pass ✱ | Quantum-L9/Cursor-Governance 7dc7e4f (merged) |
| 🟡 partial | CI-014 | 2 | Make target repository/cwd explicit for governance CLIs | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-029 | 3 | Persist repeatable cross-repo E2E fixtures ✱ | l9-constellation-topology tests/corpus_fixtures.py (3b02c6b) |
| 🟡 partial | CI-102 | 4 | Valid GH_TOKEN or formal surface exemption from gh-dependent gates ✱ | Quantum-L9/Cursor-Governance 5612f6b (merged) — a third path, unwritten |
| ⬜ not started | CI-003 _ext_ | 1 | Make the Stop hook ownership-aware instead of residue-blind ✱ | Stop-hook ownership-awareness: not started. |
| ⬜ not started | CI-005 | 1 | Make memory health transport-specific and continuity task-bearing ✱ | Memory health transport-specificity + continuity tasks: not started. |
| ⬜ not started | CI-013 _ext_ | 1 | Preserve fail-closed destructive/staging gates while making denials actionable | Not addressed by the merged work. |
| ⬜ not started | CI-018 | 1 | Make local CI parity and hooks first-class provisioning | Not addressed by the merged work. |
| ⬜ not started | CI-023 | 1 | Collapse variable-loading authorities into one reproducible loader contract ✱ | Not addressed by the merged work. |
| ⬜ not started | CI-011 _ext_ | 2 | Bound large MCP responses with field projection/pagination | Not addressed by the merged work. |
| ⬜ not started | CI-019 | 2 | Coordinate concurrent writers on shared PR branches | Not addressed by the merged work. |
| ⬜ not started | CI-021 | 2 | Make session-experience and skill-usage logging observable ✱ | Not addressed by the merged work. |
| ⬜ not started | CI-022 | 2 | Provision or explicitly declare service-backed integration-test dependencies | Not addressed by the merged work. |
| ⬜ not started | CI-024 | 2 | Repair or remove foreign/stale bootstrap and deploy entrypoints | Not addressed by the merged work. |
| ⬜ not started | CI-025 | 2 | Provide sanctioned cleanup of generated/cache residue | Not addressed by the merged work. |
| ⬜ not started | CI-028 | 2 | Improve dependency provisioning evidence and determinism ✱ | Not addressed by the merged work. |
| ⬜ not started | CI-020 _ext_ | 3 | Expose notification age when queued state is delivered | Not addressed by the merged work. |
| ⬜ not started | CI-027 | 3 | Correct rule rationale that no longer matches container reality ✱ | Not addressed by the merged work. |
| ⬜ not started | CI-030 | 3 | Improve receipt CLI ergonomics without multiplying state owners ✱ | Not addressed by the merged work. |
| ⬜ not started | CI-031 | 3 | Keep repo documentation and tracked-path hygiene synchronized ✱ | Not addressed by the merged work. |
| ⬜ not started | CI-032 | 3 | Give slow validation units explicit headroom without weakening total proof | Not addressed by the merged work. |
| ⬜ not started | CI-100 | 4 | Investigate why PR #70's workflow runs were gated in action_required | Context-specific investigation (PR #70 action_required): not started. |
| ⬜ not started | CI-101 | 4 | Align the branch directive with the repository actually worked in ✱ | Context-specific (branch directive vs repo worked in): not started, and still recurring. |

✱ = verified against the tree or the live container this pass.

_ext_ = the record's named target is owned outside this org CI-001: IMP-01 leg only (Anthropic session prompt); CI-003: harness-owned stop hook; in-repo lever exists; CI-011: GitHub MCP server; CI-013: IMP-10 leg (harness tracker); CI-020: ReadNotifications envelope.

## Residual detail

### ✅ done — CI-007: Replace standing breakglass environment strings with scoped expiring receipts
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- evidence: live readiness receipt: merge_authority_status=READY, note 'env boolean does not authorize merge; receipt/breakglass required'
- residual: CLOSED since 2026-08-26: the readiness merge_authority probe no longer crashes or false-reports 'regression' — /root/.l9/claude/readiness-receipt.json reports READY with a correct note.
- residual: done_when literal 'variable absent from a fresh session' still unmet, but the value changed: the live account now carries L9_AUTONOMY_AUTONOMOUS_MERGE=false, not =true. Still inert, still authorizes nothing; delete the env line to satisfy the literal.

### ✅ done — CI-026: Support safe on-disk aliases for dot-prefixed repositories
- delivered_by: Session repository scope (Quantum-L9/.github attached; clone at /home/user/.github)
- evidence: ls -d /home/user/.github -> present, carrying .claude/, .l9/, .mcp.json, AGENTS.md
- evidence: session repository scope list names quantum-l9/.github
- residual: done_when names 'its CLAUDE.md and skills load': that repo carries AGENTS.md, not CLAUDE.md, and ships no skills/ tree — the clause is moot rather than unmet. Its .claude/ tree is present.
- residual: Attachment predates this assessment; the 2026-08-26 pass recorded not_started without checking the on-disk clone.

### ✅ done — CI-033: Use pipefail in push/retry helpers
- delivered_by: Pre-existing (already COMPLETED at pack generation)
- evidence: Marked COMPLETED in the source pack (pipefail in push/retry helpers).

### 🟡 partial — CI-002: Make bootstrap projection ownership-aware and non-destructive to tracked repo content
- delivered_by: PR#304 (Contract 1) + PR#307 (CI-008/CI-009/CI-002 slice), both merged into main
- evidence: is_tracked is defined and called only in ops/scripts/reconcile_llm_rule_adapters.py (lines 27, 146); grep -c is_tracked returns 0 for claude_projection.py, reconcile_claude_l9_skills.py, reconcile_claude_commands.py, reconcile_claude_settings.py, and the last commit on all four predates the guard
- evidence: Phase 2c unbuilt: L9_AUTONOMY_STATE_DIR still defaults to '.l9/autonomy' inside the worktree in peer_execution/autonomy/{cli,bootstrap}.py
- residual: UNCHANGED since 2026-08-26. The is_tracked guard still covers only the rule-adapter reconciler. It must extend to claude_projection.py:422 (.mcp.json), reconcile_claude_l9_skills.py, reconcile_claude_commands.py, reconcile_claude_settings.py.
- residual: Phase 2b (project to a non-owned sibling when the target is tracked), 2c (L9_AUTONOMY_STATE_DIR outside the worktree), and 2d (per-repo gitignore propagation) are not built; the 8-fixture git-status-clean done_when is unverified.

### 🟡 partial — CI-004: Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- evidence: LIVE DEFECT, this session: /root/.l9/claude/bootstrap-state.json is pinned to governance_revision c3081ee, generated_at 2026-08-26T19:30:48Z, while gov-refresh.json (2026-08-27T00:01:55Z) and readiness-receipt.json (2026-08-26T23:23:01Z) both carry 498dcaa. Two receipt stores disagree about the governance revision inside one session and nothing invalidated the stale one.
- evidence: partial correction to the recorded residual: per-component log paths DO exist for the deps stage — 11 deps-<fingerprint>.log files with content under /root/.l9/claude/.
- residual: bootstrap-state.json is still not regenerated on container/session lifecycle or on a governance revision change; stale-receipt invalidation is not wired.
- residual: Per-component log paths exist only for deps; the other components (capabilities, memory, mcp, plugins) report a bare DEGRADED with no evidence path.
- residual: No cross-check between the three receipt stores — see the proposed CI-035.

### 🟡 partial — CI-006: Resolve authority-sensitive environment drift at the actual source
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- evidence: live: env carries L9_AUTONOMY_AUTONOMOUS_MERGE=false (was =true at assessment)
- residual: General mechanism (separate authority-widening drift from cosmetic drift, make repair reachable/human-only, record the governing value) is not built.
- residual: done_when '0 of 33 in exactly one layer': the stray var is still present, now valued false rather than true, so it no longer even nominally widens authority. Delete it to reach the exact-one-layer end state.

### 🟡 partial — CI-008: Reconcile make pr doctrine with consumer-repository command contracts
- delivered_by: Quantum-L9/Cursor-Governance PR#307 (merged into main)
- evidence: ops/scripts/run_pr_precommit.sh lines 22-32 bind the governance pre-commit config explicitly and carry the consumer-workspace gap as an in-script scoped follow-up
- evidence: tests/ops/scripts/test_publish_verb_governance_always.py asserts the governance-rooted verb, that a consumer needs no pr target, and that the gate binds the governance config
- residual: Running the governance pre-commit config against a *consumer* workspace (cwd=$GOV, absolute --files, governance-only-local-hook skip subset) needs real-consumer validation and is scoped in-script, not enabled. The done_when's consumer-side leg is unverified.

### 🟡 partial — CI-009: Establish one project interpreter/toolchain authority and verify importability before READY
- delivered_by: Quantum-L9/Cursor-Governance PR#307 (merged into main)
- evidence: ops/scripts/emit_claude_readiness.py::_interpreter_importable_status probes the locked interpreter for yaml/jsonschema/pydantic; UNKNOWN on a missing interpreter, DEGRADED on an import failure
- evidence: live readiness receipt: interpreter_importable_status=READY, note 'governance interpreter imports core deps'
- residual: CONFIRMED still open: session-deps asserts readiness without an import smoke. The live banner says 'session-deps: toolchain ready (fingerprint 9ff843f2…)' and the backing log /root/.l9/claude/deps-9ff843f2….log contains only 'installing workspace toolchain' and 'install pass complete' — no import proof and no exit code.
- residual: A sourceable scripts/env.sh (IMP-E1) was deliberately NOT added: this repo already has one interpreter authority (Makefile + ensure_gov_python.sh + gov-python prereq). Container-image items (A2-A5) are external (SC-IMG).

### 🟡 partial — CI-010: Make broker authentication and reachability diagnosable
- delivered_by: PR#305 (+ predecessor PR#304) and PR#320, all merged into main
- evidence: live capability plane: broker_reachability=no_dns_record/unreachable_URLError, broker_identity_status=none:hosted_surface_issues_no_session_identity, primary_blocker=identity — the states are named, not collapsed
- evidence: PR#320 (merged) moves every adapter's memory front door to the broker URL with no inline bearer, so an unset broker returns an honest 401 and memory runs DEGRADED
- residual: CONNECT cannot succeed (no platform-issued identity — external; tracked as Quantum-L9/Cursor-Governance issues #301, #302).
- residual: Broker states not fully split into proxy-denied vs upstream-error for allowlist remediation decisions.

### 🟡 partial — CI-001: Publish and enforce the real GitHub REST/GraphQL capability boundary
- delivered_by: Quantum-L9/Cursor-Governance 5612f6b (merged) + pre-existing ops/scripts/lib/gh_auth_probe.sh
- evidence: ops/autonomy/merge_gate.py: _gh_rest_json / _stacked_children_rest resolve head and children over GET repos/{o}/{r}/pulls, gh pr view|list kept as fallback (IMP-11)
- evidence: merge_gate.py _transport_blocked + the 'both probe transports were refused' deny text names the transport instead of 'unknown' (IMP-12)
- evidence: tests/ops/autonomy/test_merge_gate_rest_probe.py (229 lines) drives both transports and the both-failed fail-closed path
- evidence: ops/scripts/lib/gh_auth_probe.sh probes `gh api user` and outranks a failing `gh auth status` (IMP-02) — present at 78f122a, so the 2026-08-26 not_started was wrong
- evidence: live: `gh api user --jq .login` -> cryptoxdog on this surface
- residual: IMP-01 only: the Anthropic remote-session prompt still tells agents they have no gh access. Harness-owned; no in-repo lever. See the external-owner note in PROGRESS.md.

### 🟡 partial — CI-012: Gate rules and MCP config on actual surface capabilities
- delivered_by: Quantum-L9/Cursor-Governance PR#320 (merged as c3ddeea) + pre-existing adapter templates
- evidence: PR#320 ops/secrets/capabilities.yaml: `requires` may name only capability_broker.EVALUABLE_REQUIREMENTS — a precondition no code evaluates now denies the capability instead of passing silently; unevaluable phase_lock_held removed
- evidence: PR#320 ops/secrets/capability_broker.py +96, tests/ops/secrets/test_capability_plane.py +110
- evidence: PR#320 environment/agents/adapters/generic/mcp.template.json moved to the brokered front door (no inline bearer), matching the claude-code peer
- evidence: I-BS-03 already satisfied at 78f122a: claude-code and codex mcp.template.json both carry the `type` discriminator, and so does the live /home/user/.mcp.json
- residual: IMP-07: rule 22 still mandates Context7 on every surface. This surface exposes no context7 MCP server (live tool roster carries graphiti-memory, github, Vercel, Tavily, Google Calendar — no context7), so the rule names a mechanism the surface lacks.
- residual: I-BS-12: projected always-on rules still carry no capability precondition annotation.
- residual: PR#320 is open, not merged.

### 🟡 partial — CI-015: Name and enforce the authoritative governance checkout
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- evidence: done_when met this session: listed 6 open Quantum-L9/Cursor-Governance issues via the GitHub MCP with no add_repo call — the SSOT is in the session repository scope
- residual: CLOSED since 2026-08-26: 'read the SSOT's issues without add_repo' (C2) is now met.
- residual: Non-authoritative clones are still not relabelled or removed: /root/.cursor-governance and /home/user/Cursor-Governance both sit at 498dcaa, and the session banner names only the first (I-WT-01, I-BS-13).

### 🟡 partial — CI-016: Make L4/release receipts resolve paths, branch, and head dynamically
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- evidence: ops/autonomy/l4_local.py resolves branch and head dynamically (current_branch, current_head, branch-drift check at lines 173-334)
- evidence: pr_template is still the literal 'PULL_REQUEST_TEMPLATE.md' at lines 339 and 436; the file has not been touched since 3cc4cab
- residual: The L4/release receipt's pr_template resolution is still hardcoded, so the done_when (a receipt written in org-github-defaults names .github/pull_request_template.md or null) remains unmet.

### 🟡 partial — CI-017: Validate generated-artifact membership and report all drift in one pass
- delivered_by: Quantum-L9/Cursor-Governance 7dc7e4f (merged)
- evidence: ops/scripts/sync_generated_artifacts.py: environment/program-execution/MANIFEST.json is no longer 'advisory, never auto-synced'; the commit-time hook opts in so the manifest tracks the tree it hashes, instead of every PE edit failing `make program-execution-conformance` into a regenerate-by-hand-and-retry loop
- evidence: that is I-WT-03's shape — surface the omission at commit time rather than only at the release gate — applied to the governance repo's own generated manifest
- residual: The three named targets are untouched: CEG scripts/generate_validation_report.py still aborts gate 7 on a staged-but-deleted path (IMP-B1); l9-meta-injector still reports manifest staleness and dist divergence in separate passes (IMP-09); CEG validate_release_readiness.py still only fails at the gate on missing MANIFEST.md membership, with no --fix and no pre-commit surface (I-WT-03).

### 🟡 partial — CI-014: Make target repository/cwd explicit for governance CLIs
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- evidence: environment/agents/adapters/claude-code/bin/l9 passes explicit WS=$PWD and -C $GOV; the Makefile owns CONSUMER_SAFE target classification (single authority).
- residual: Covers the make-target facade only; many ops/scripts governance CLIs still depend on persistent shell cwd.

### 🟡 partial — CI-029: Persist repeatable cross-repo E2E fixtures
- delivered_by: l9-constellation-topology tests/corpus_fixtures.py (3b02c6b)
- evidence: tests/corpus_fixtures.py is committed in the target repo and builds the two-root corpus in memory, deliberately rather than as checked-in bytes
- evidence: tests/fixtures/topology_packets/foundational-two-repo/ persists the compiled bundle
- evidence: scripts/generate_fixture_packets.py regenerates fixtures byte-reproducibly and its --check is part of the standard validation gate
- residual: Not proven to be I-WT-04's builder: build_corpus.mjs is absent from the repo (no .mjs files at all), and corpus_fixtures.py declares six document formats where I-WT-04 named an eight-format corpus. Whether the real producer/consumer qualification now runs off this fixture, or still off a scratchpad builder, is unverified.
- residual: 'importing the producer's fixture helpers rather than duplicating them' is unconfirmed.

### 🟡 partial — CI-102: Valid GH_TOKEN or formal surface exemption from gh-dependent gates
- delivered_by: Quantum-L9/Cursor-Governance 5612f6b (merged) — a third path, unwritten
- evidence: live: `gh api user --jq .login` -> cryptoxdog with GH_TOKEN=proxy-injected
- evidence: merge_gate.py answers the stack probe over REST, so the gh-dependent gate that was exit-2 blocked on this surface now returns an answer
- residual: Neither sanctioned option was taken: no openclaw PAT via the secret plane (option a), and no surface_profile / rules 53 / rules 62 amendment sanctioning the MCP path for claude-cloud (option b). The gates work by a third route — REST-capable probes — that no rule or profile records, so the next gh-dependent gate written will reproduce the original block.

### ⬜ not started — CI-003: Make the Stop hook ownership-aware instead of residue-blind
- evidence: read /root/.claude/stop-hook-git-check.sh: it fires on any `git diff` delta and on any `git ls-files --others --exclude-standard` output, with no ownership classification
- evidence: partial mitigation already present at 78f122a: bootstrap_agent_environment.sh writes /.cursor-commands, /.cursor/, /.l9/, memory-bank/ into .git/info/exclude, which --exclude-standard honours — but .claude/** and .mcp.json are not in that list
- residual: Stop-hook ownership-awareness: not started.
- residual: OWNERSHIP NOTE: the named target /root/.claude/stop-hook-git-check.sh is harness-owned and not editable from this repo. The in-repo lever is the .git/info/exclude glob list in ops/scripts/bootstrap_agent_environment.sh — re-scope the record to that, or mark it external.

### ⬜ not started — CI-005: Make memory health transport-specific and continuity task-bearing
- evidence: live: bootstrap-state.json carries one collapsed "memory": "DEGRADED" — no memory.cli / memory.mcp split (I-BS-05)
- evidence: live hydrate: stats facts_returned=8, and all 8 are self-referential PICKUP restatements ('The next action involves resuming from the latest Graphiti PICKUP') — a hydration carrying no task state reports as successful (I-BS-06, IMP-09)
- evidence: the multi-repo banner naming the cap and the skip reason predates this assessment (78f122a) and does not enumerate skipped repo names with per-repo reasons (BOOT-7)
- residual: Memory health transport-specificity + continuity tasks: not started.

### ⬜ not started — CI-023: Collapse variable-loading authorities into one reproducible loader contract
- evidence: rules/06-governance-ssot-paths.mdc still says scripts 'source resolve_governance_paths.sh and use the exported values' — no must-call wording (IMP-02)
- evidence: ops/scripts/resolve_governance_paths.sh carries no source-without-call guard (LOADER-2)
- residual: Not addressed by the merged work.

### ⬜ not started — CI-021: Make session-experience and skill-usage logging observable
- evidence: live: /root/.claude/l9/ does not exist — skill-usage logging still reaches no disk
- residual: Not addressed by the merged work.

### ⬜ not started — CI-028: Improve dependency provisioning evidence and determinism
- evidence: live deps log contains no exit code and no in-content timestamp; the paired .stamp file is zero bytes (I-EL-03)
- residual: Not addressed by the merged work.

### ⬜ not started — CI-027: Correct rule rationale that no longer matches container reality
- evidence: rules/03-graphiti-memory.mdc:56 still reads 'system `python3` often lacks PyYAML'; `python3 -c 'import yaml'` succeeds on this container
- residual: Not addressed by the merged work.

### ⬜ not started — CI-030: Improve receipt CLI ergonomics without multiplying state owners
- evidence: ops/scripts/claude_bootstrap_receipt.py:144 still declares --read with required=True — no default read action
- residual: Not addressed by the merged work.

### ⬜ not started — CI-031: Keep repo documentation and tracked-path hygiene synchronized
- evidence: l9-ci-sdk/CLAUDE.md:45 still states 'Pre-commit has two hooks'; l9-ci-sdk/.pre-commit-config.yaml declares 9 (ruff, ruff-format, yamllint x2, biome-check, l9-governance-json, l9-action-pins, l9-zizmor, l9-make-check)
- residual: Not addressed by the merged work.

### ⬜ not started — CI-101: Align the branch directive with the repository actually worked in
- evidence: reproducing live: this session's branch directive names one branch, claude/zip-task-review-33gw3m, identically across all 10 in-scope repositories
- residual: Context-specific (branch directive vs repo worked in): not started, and still recurring.
