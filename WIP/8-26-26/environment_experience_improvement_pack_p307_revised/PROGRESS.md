# Environment Experience Improvement Pack — Progress (revision r2)

Assessed against **main@59f03a5d** on 2026-08-28, full SHA `59f03a5d4460b939360bc2fd5dd85239d47416a5`.
Predecessor: `WIP/8-26-26/environment_experience_improvement_pack_p307`, assessed at `30c6ecd4`.

**2 done · 16 partial · 16 not started · 1 blocked · 3 unknown** (of 38 records).

**Active queue: 27.** 6 external-blocked, 3 unverifiable without a repository attachment, 2 closed.

> **This pass is full, not targeted.** The predecessor was explicit that it re-verified only
> the records touched by #324 and #325 and carried the rest forward. It named `30c6ecd4`;
> main is at `59f03a5d`, 59 commits and 514 files later. Carrying judgements forward across
> that gap is how three records came to be wrong, so every record here was re-judged against
> the tree and the live container.

## Headline: three records were wrong, and two of them were wrong in the direction that hides work

| Item | Was | Now | Why the previous judgement did not hold |
|---|---|---|---|
| **CI-007** | ✅ done | 🟡 **partial** | Closed on evidence about a different question. The proof cited was `merge_authority_status: READY` — that the readiness probe stopped crashing. The record is about whether exceptional publish authority is scoped and expiring. At this binding the session env carries `L9_PUBLISH_PATH_OVERRIDE='one-time breakglass authorized by user'`, read live by `local_execution_gate.py:194`, with no issuer, scope or expiry, unreported at session start, and outside the 32 variables `verify_account_env.py` compares. All three source improvements unmet. |
| **CI-026** | ✅ done | ⛔ **blocked** | Closed on non-durable evidence: that `/home/user/.github` existed and `quantum-l9/.github` was in the session scope list. Both are properties of one session's configuration. At this binding neither holds — the clone is absent and the scope list names four repositories, none of them `.github`. `add_repo`, the named target, is unchanged. |
| **CI-003** | ⬜ not started | 🟡 **partial** | Understated. The recorded residual says the in-repo lever lacks `.claude/**`; the adapter's `install.sh:391-405` already excludes `.claude/skills/`, `.claude/rules/` and `.claude/commands/`, with the scoping decision written out: *'Only the GENERATED mirrors are excluded — .claude/settings.json and .claude/hooks/ are committable consumer wiring.'* Unchanged since before `30c6ecd4`, so it was there and unrecorded. One glob (`.mcp.json`) remains. |

## The next slice the predecessor named would have been rework

`slice-ownership-aware-writes` rested on one claim: PR#307 guarded one write site with `is_tracked()` and left four unguarded. The `grep` behind it is correct — `is_tracked` is still called only in `reconcile_llm_rule_adapters.py`. The inference is not.

Each of the four sites already implements the property CI-002's `canonical_action` asks for, by a different mechanism:

| Site | Mechanism | Where |
|---|---|---|
| `reconcile_claude_l9_skills.py` | managed-entry symlink set; unmanaged entries never overwritten or removed | docstring lines 4-6 |
| `reconcile_claude_commands.py` | same managed-entry model, per-command | docstring line 5, write at 209 |
| `reconcile_claude_settings.py` | `merge_workspace_settings()` — consumer keys survive; write-if-changed | lines 92-110, 113 |
| `claude_projection.py` | renders `.mcp.json` preserving every server the template does not define | `preserved_unmanaged`, 415; write-if-changed, 419 |

And the live proof: at this binding all four in-scope repositories report an empty `git status --porcelain --untracked-files=all` — **including `l9-meta-injector`, which tracks `.claude/settings.json`**. A tracked projection target survived a bootstrap with a clean tree.

Applying `is_tracked()` to those four would add a *report*, not a protection they lack. CI-002 therefore drops from the pack's headline slice to leverage rank 23 of 27; its genuine remainder is Phase 2c alone (`L9_AUTONOMY_STATE_DIR` still defaults to `.l9/autonomy` inside the worktree, confirmed live). One of its legs is invalidated outright: IMP-06 asks for four `.gitignore` lines in eight consumer repos, and the current design writes `.git/info/exclude` *specifically so that* "a consumer's tracked .gitignore is never mutated" (`bootstrap_agent_environment.sh:462-464`).

## Reproducing at this binding

- **CI-004** — fourth recorded occurrence. `bootstrap-state.json` carries `governance_revision b618338d…` at 04:34; `gov-refresh.json` carries `59f03a5d` at 21:39; `readiness-receipt.json` carries `59f03a5d`. The stale receipt is 17h old against a 24h TTL, so TTL will never catch it, and `claude_bootstrap_receipt.py` compares TTL only — `governance_revision` is carried at line 88 and never compared.
- **CI-001** — this session's own system prompt says *"You do NOT have access to the `gh` CLI, `hub` CLI, or direct GitHub API access"* while `gh api user --jq .login` returns `cryptoxdog`. IMP-01 verbatim, four assessments running. External.
- **CI-009 / CI-028** — the banner says `toolchain ready`; the log behind it is two lines with no exit code, no interpreter, no import proof, and the paired `.stamp` is zero bytes. All five stamps in the directory are zero bytes.
- **CI-021** — `L9_SKILL_USAGE_LOGGING=true` and `/root/.claude/l9/` does not exist. Enabled, reaching no disk, silently.
- **CI-012** — sharper than recorded: the live `.mcp.json` declares exactly one server, `graphiti-memory`, and that server failed to connect this session (502). Rule 22 mandates Context7 on every surface and says a missing allow-list entry is not permission to skip — an obligation this surface cannot close.
- **CI-005** — all four namespaces hydrated `facts_returned=8`, and the previewed facts are self-referential PICKUP restatements. Meanwhile the MCP transport was down and the CLI transport worked: exactly the divergence `I-BS-05` exists to expose, hidden behind one word.
- **CI-022** — no `neo4j` binary, `127.0.0.1:7687` refused. **CI-027** — rule 03 still says system `python3` "often lacks PyYAML"; it imports fine on 3.11.15. **CI-101** — one branch directive across all four in-scope repositories.

## Residuals that closed, and residuals that were wrong

- **CI-006** — IMP-03's `done_when` is now **met**. `verify_account_env.py` reports *all 32 expected variables match*, zero drift, and `L9_AUTONOMY_AUTONOMOUS_MERGE=false` is in the session env but not in `settings.json`'s env block — set in exactly one layer. Only the class mechanism remains.
- **CI-014** — the recorded residual is wrong on its principal target. `l4_local.py:478` already declares `--workspace`, and `git show 30c6ecd4:ops/autonomy/l4_local.py` contains it too. The open legs are `graphiti_memory_client.py` and the actionable refusal message.
- **CI-036** — advanced. `af33b4d` (#331, merged after the assessment) taught `session_debt.py` that a merged-and-deleted branch is not unpushed work, using `branch.<name>.remote` because a squash merge leaves the commits unreachable and the deleted ref leaves nothing to compare against. Both directions pinned against a real bare upstream.
- **CI-037** — re-verified live: `session_debt.py` and rule 42 present, and `session_debt_wrap.py` registered on the Stop hook as `--class gate` in the running `settings.json`. Stays done.

## The pack disagreed with itself again

The predecessor's `improvements.yaml` carried `progress_meta` stamped `main@post-#307-merge` with counts 2/9/25 of **36**; its `progress.yaml` carried 4/15/19 of **38** at `30c6ecd4`; and `improvements.yaml` held only **37** records because CI-037 was introduced into `progress.yaml` alone. Three stores, three answers, inside the artifact that proposed CI-035 for exactly this. Reconciled here: CI-037 is promoted to a first-class improvement record and both stores carry 38 and the same counts.

## Optimized execution order

Two constraints govern this order, and the second is the one the dependency graph does not express.

**The DAG is shallow.** Longest chain `CI-004 -> CI-005`, depth 2. Seven of the nine historical dependency edges were removed as no longer true.

**Mutation surface is what actually serializes.** Three records edit `bootstrap_agent_environment.sh`; three edit the execution gate; five edit rules behind one shared regeneration. Ordering by dependency alone schedules conflicting writers into one wave and loses the time it thought it saved.

### Wave 1 — Live authority and receipt-truth defects

> Everything here is either reproducing at this binding or is the prerequisite for a Wave-2 lane. CI-007 leads because it is the only active authority-widening defect in the queue and because it was wrongly closed, so nothing was going to reach it.

| Lane | Sequence | Shared surface | Released by |
|---|---|---|---|
| 1A | CI-007 → CI-006 | G-env-authority | — |
| 1B | CI-004 | G-receipt | — |
| 1C | CI-009+CI-028 | G-bootstrap | — |
| 1D | CI-003 | — | — |

### Wave 2 — Receipt consumers and the rest of the bootstrap file

> Each lane is released by Wave 1 — the two receipt consumers by CI-004's schema, the bootstrap lane by CI-009+CI-028 finishing with that file.

| Lane | Sequence | Shared surface | Released by |
|---|---|---|---|
| 2A | CI-005 | — | CI-004 |
| 2B | CI-010 | — | CI-004 |
| 2C | CI-036 | — | CI-009+CI-028 (G-bootstrap) |
| 2D | CI-030 | — | CI-004 |

### Wave 3 — Rules and doctrine plane

> One lane, one regeneration. CI-012 first because rule 22 currently mandates a mechanism this surface does not expose, which every session pays for.

| Lane | Sequence | Shared surface | Released by |
|---|---|---|---|
| 3A | CI-012 → CI-102 → CI-023 → CI-027 → CI-015 | G-rules | — |

### Wave 4 — Publish, gate, and release-receipt planes

| Lane | Sequence | Shared surface | Released by |
|---|---|---|---|
| 4A | CI-008 → CI-019 | G-publish | — |
| 4B | CI-025 → CI-013 | G-gate | — |
| 4C | CI-016 | G-l4 | — |
| 4D | CI-014 | — | — |

- **4B:** CI-025 first — it removes the pressure that motivates CI-013's C3.

### Wave 5 — Ownership model, observability, and consumer-repo cleanup

| Lane | Sequence | Shared surface | Released by |
|---|---|---|---|
| 5A | CI-002(Phase 2c) | — | CI-013 (G-gate releases local_execution_gate.py) |
| 5B | CI-018 → CI-021 → CI-022 | — | — |
| 5C | CI-017 → CI-032 | — | — |

- **5C:** Both land in l9-meta-injector — a different repository, so no governance-tree conflict.

### Wave 6 — Blocked on repository attachment

> Not deferred by priority. These cannot be assessed, let alone executed, until a session carries the repositories they name.

| Lane | Sequence | Shared surface | Released by |
|---|---|---|---|
| 6A | CI-024 → CI-029 → CI-031 | — | attach Enrichment.Inference.Engine, l9-constellation-topology, l9-ci-sdk |

### Removed dependency edges

A historical edge is not evidence. Each of these was re-derived and dropped:

- **CI-003 -> CI-002** — The remaining in-repo lever for CI-003 is a single glob added to the Claude-specific exclude block in install.sh. It does not consume an ownership guard, and CI-002's hazard is already mitigated by four independent mechanisms. The two records are now independent.
- **CI-012 -> CI-004** — CI-012's residual is rule-22 text plus capability preconditions in rule frontmatter. Neither reads or writes the bootstrap receipt CI-004 governs. I-BS-12 needs capability state from the capability plane, not from CI-004's work.
- **CI-018 -> CI-009** — A `make test-ci-parity` target running suites under an emptied git identity does not depend on the deps-stage import smoke existing. The env recipe is already proven in test_run_campaign._GIT_IDENTITY.
- **CI-022 -> CI-009** — CI-022's in-repo half is a session-start declaration that service-backed coverage is unavailable. It has no relationship to interpreter authority.
- **CI-023 -> CI-009** — CI-023's remaining scope is BASH_ENV/.bashrc loading, a resolver source-without-call guard, and rule-06 wording. None of it changes WHICH interpreter resolves — the pack itself recorded that IMP-E1 was deliberately not added because one interpreter authority already exists. Independent in both directions.
- **CI-025 -> CI-013** — Inverted in practice. `make clean-pyc` is independently deliverable and REMOVES the pressure that motivates narrowing the forced-removal guardrail. Scheduling CI-025 behind CI-013 delays the cheaper fix behind the riskier one.
- **CI-028 -> CI-009** — Not a dependency — the same edit. Both change the deps stage of bootstrap_agent_environment.sh, and the exit-code plumbing CI-028 asks for is the natural carrier for the smoke result CI-009 asks for. Collapsed into one execution unit rather than sequenced.

### Added edges

- **CI-030 -> CI-004** (soft) — CI-030 gives claude_bootstrap_receipt.py and governance_refresh_receipt.py a default read action. CI-004 changes what those receipts contain. Doing CI-030 first prints a schema that is about to change.
- **CI-006 -> CI-007** (mutation_surface) — CI-007's remedy may add L9_PUBLISH_PATH_OVERRIDE to the account-field contract that verify_account_env.py compares; CI-006 edits that same verifier. Same plane, same file — serialize, authority repair first.
- **CI-002(Phase 2c) -> CI-013** (mutation_surface) — Phase 2c touches ops/autonomy/local_execution_gate.py together with l4_local.py and the publish path. CI-013's stage-naming and guardrail narrowing edit the same gate. They cannot be parallel lanes.

## Full status

| Progress | Item | P | Wave | Seq | Lev | Deps | Title | Remaining |
|---|---|---|---|---|---|---|---|---|
| 🟡 partial | **CI-007** | 0 | 1 | 1 | 1 | — | Replace standing breakglass environment strings with scoped expiring receipts | IMP-04 / ENV-2: remove the standing variable from the account environment, or replace its value with one that describes an actual standing policy. |
| 🟡 partial | **CI-006** | 0 | 1 | 2 | 8 | CI-007 | Resolve authority-sensitive environment drift at the actual source | I-EL-02: name the file that produced the live value when a variable drifts. |
| 🟡 partial | **CI-004** | 0 | 1 | 3 | 2 | — | Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components | IMP-03 / I-BF-01: treat a governance_revision mismatch as expiry, distinct from TTL expiry. |
| 🟡 partial | **CI-009** | 0 | 1 | 4 | 3 | — | Establish one project interpreter/toolchain authority and verify importability before READY | I-EL-05: end the deps pass with an import smoke on the resolved interpreter; record interpreter path and version in the log. |
| ⬜ not started | **CI-028** | 2 | 1 | 4 | 4 | — | Improve dependency provisioning evidence and determinism | I-EL-03(P8): write the deps step's exit code into the stamp or the log's final line, and timestamp the log. |
| 🟡 partial | **CI-003** | 1 | 1 | 5 | 5 | — | Make the Stop hook ownership-aware instead of residue-blind | Add `.mcp.json` to the Claude-specific exclude block in install.sh. One glob; the design decision it belongs to is already made and documented. |
| ⬜ not started | **CI-005** | 1 | 2 | 6 | 7 | CI-004 | Make memory health transport-specific and continuity task-bearing | I-BS-05: split the receipt's `memory` component into memory.cli and memory.mcp, probed independently, with the CLI verdict based on graphiti_memory… |
| 🟡 partial | **CI-010** | 0 | 2 | 7 | 9 | CI-004 | Make broker authentication and reachability diagnosable | I-EL-02: report proxy-denied and upstream-error as distinct probe states, so an allowlist remediation decision has something to decide on. |
| 🟡 partial | **CI-036** | 2 | 2 | 8 | 11 | — | Keep unpushed-commit counts honest across merged-and-deleted branches | Consolidate repo_hygiene.py's prune with the session-start prune so a count read mid-session is not served by the session-end pass. |
| ⬜ not started | **CI-030** | 3 | 2 | 9 | 19 | CI-004 | Improve receipt CLI ergonomics without multiplying state owners | LOADER-1: make bare invocation read and print, keep --read accepted, and name the exact command in CLAUDE.md's receipt paragraph. |
| 🟡 partial | **CI-012** | 1 | 3 | 10 | 6 | — | Gate rules and MCP config on actual surface capabilities | IMP-07: extend rule 22 with the server-absent case and name the required fallback, so the obligation stays closable. |
| 🟡 partial | **CI-102** | 4 | 3 | 11 | 10 | — | Valid GH_TOKEN or formal surface exemption from gh-dependent gates | Record the REST route as a sanctioned surface capability in ops/autonomy/surface_profile.yaml and rule 62, or provision the PAT. Until then the nex… |
| ⬜ not started | **CI-023** | 1 | 3 | 12 | 15 | — | Collapse variable-loading authorities into one reproducible loader contract | IMP-02(P4): amend rule 06 to `source …; resolve_governance_paths_or_exit`. |
| ⬜ not started | **CI-027** | 3 | 3 | 13 | 24 | — | Correct rule rationale that no longer matches container reality | IMP-17: keep the pinned-interpreter mandate, replace the justification with the true one (version pinning and dependency isolation), and regenerate… |
| 🟡 partial | **CI-015** | 1 | 3 | 14 | 17 | — | Name and enforce the authoritative governance checkout | I-BS-13: when a second checkout of the governance repository is present, print both paths with their revisions and state which one rules resolve fr… |
| 🟡 partial | **CI-008** | 0 | 4 | 15 | 12 | — | Reconcile make pr doctrine with consumer-repository command contracts | Enable the consumer-workspace path: cwd=$GOV_ROOT so repo-local `entry:` hooks resolve, absolute --files paths, and a governance-only-local-hook sk… |
| ⬜ not started | **CI-019** | 2 | 4 | 16 | 22 | — | Coordinate concurrent writers on shared PR branches | IMP-06(P7) retry half: bounded fetch/merge --no-edit/regen/re-verify/push loop, N<=2, never rewriting history. |
| ⬜ not started | **CI-025** | 2 | 4 | 17 | 14 | — | Provide sanctioned cleanup of generated/cache residue | IMP-05/IMP-08(P7): add `make clean-pyc` and have the adapters gate pre-clean or ignore cache debris rather than failing on it. |
| ⬜ not started | **CI-013** | 1 | 4 | 18 | 13 | — | Preserve fail-closed destructive/staging gates while making denials actionable | I-BS-10 (in-repo): name the refused stage of a compound command and state that later stages did not run. |
| 🟡 partial | **CI-016** | 1 | 4 | 19 | 16 | — | Make L4/release receipts resolve paths, branch, and head dynamically | IMP-14: resolve pr_template against the released repository across the standard template locations; emit null when none is found. |
| 🟡 partial | **CI-014** | 2 | 4 | 20 | 18 | — | Make target repository/cwd explicit for governance CLIs | Add --workspace to graphiti_memory_client.py, defaulting to current behaviour. |
| 🟡 partial | **CI-002** | 0 | 5 | 21 | 23 | CI-013 | Make bootstrap projection ownership-aware and non-destructive to tracked repo content | Phase 2c (relocate L9_AUTONOMY_STATE_DIR outside the worktree). The only unmitigated leg. Touches l4_local.py + local_execution_gate.py + make pr t… |
| ⬜ not started | **CI-018** | 1 | 5 | 22 | 21 | — | Make local CI parity and hooks first-class provisioning | IMP-01(P7): add a make target running the campaign and controller suites with HOME empty and both git config files at /dev/null, and reference it f… |
| ⬜ not started | **CI-021** | 2 | 5 | 23 | 20 | — | Make session-experience and skill-usage logging observable | I-BS-11: narrow the matcher to namespaces this surface exposes, and emit a session-start line naming the log path and its current entry count. |
| ⬜ not started | **CI-022** | 2 | 5 | 24 | 25 | — | Provision or explicitly declare service-backed integration-test dependencies | I-EL-07, in-repo half: state at session start that service-backed integration tests are unavailable, so the split between runnable and unrunnable c… |
| 🟡 partial | **CI-017** | 1 | 5 | 25 | 26 | — | Validate generated-artifact membership and report all drift in one pass | IMP-09 (l9-meta-injector): collect manifest staleness and dist divergence in one report, or add `npm run regen`. |
| ⬜ not started | **CI-032** | 3 | 5 | 26 | 27 | — | Give slow validation units explicit headroom without weakening total proof | IMP-10(P4): split the five-run incremental chain across two files, or reduce the incremental scale fixture while leaving corpus_scale.test.ts at te… |
| 🟡 partial | **CI-001** _external_blocked_ | 1 | — | — | — | — | Publish and enforce the real GitHub REST/GraphQL capability boundary | IMP-01 only: the remote-session prompt still denies gh access that demonstrably works. Harness-owned; no in-repo lever. |
| ⬜ not started | **CI-011** _external_blocked_ | 2 | — | — | — | — | Bound large MCP responses with field projection/pagination | — |
| ⬜ not started | **CI-020** _external_blocked_ | 3 | — | — | — | — | Expose notification age when queued state is delivered | — |
| ❓ unknown | **CI-024** _needs_attachment_ | 2 | — | — | — | — | Repair or remove foreign/stale bootstrap and deploy entrypoints | — |
| ⛔ blocked | **CI-026** _external_blocked_ | 3 | — | — | — | — | Support safe on-disk aliases for dot-prefixed repositories | IMP-16: durable alias support in add_repo, or an explicit record that attachment is per-session operator configuration and not a delivered capabili… |
| ❓ unknown | **CI-029** _needs_attachment_ | 3 | — | — | — | — | Persist repeatable cross-repo E2E fixtures | — |
| ❓ unknown | **CI-031** _needs_attachment_ | 3 | — | — | — | — | Keep repo documentation and tracked-path hygiene synchronized | — |
| ✅ done | **CI-033** _closed_ | 99 | — | — | — | — | Use pipefail in push/retry helpers | — |
| ✅ done | **CI-037** _closed_ | 1 | — | — | — | — | Make abandoned work fail closed instead of relying on doctrine | — |
| ⬜ not started | **CI-100** _external_blocked_ | 4 | — | — | — | — | Investigate why PR #70's workflow runs were gated in action_required | — |
| ⬜ not started | **CI-101** _external_blocked_ | 4 | — | — | — | — | Align the branch directive with the repository actually worked in | — |

## Not scheduled, and why

**External-blocked (6)** — no lever on any surface this org owns. Broken out of `not_started` so that count is a workload rather than a mixture:
- **CI-001** — Publish and enforce the real GitHub REST/GraphQL capability boundary
- **CI-011** — Bound large MCP responses with field projection/pagination
- **CI-020** — Expose notification age when queued state is delivered
- **CI-026** — Support safe on-disk aliases for dot-prefixed repositories
- **CI-100** — Investigate why PR #70's workflow runs were gated in action_required
- **CI-101** — Align the branch directive with the repository actually worked in

**Unverifiable at this binding (3)** — the named targets live in repositories no session here carries. Recorded as `unknown` rather than re-asserted from the predecessor's evidence:
- **CI-024** — Repair or remove foreign/stale bootstrap and deploy entrypoints
- **CI-029** — Persist repeatable cross-repo E2E fixtures
- **CI-031** — Keep repo documentation and tracked-path hygiene synchronized

**Closed (2)** — CI-033 (pre-existing at pack generation) and CI-037 (verified live at this binding). Retained for provenance, not scheduled.

## Still proposed, not adopted

**CI-034** — bind the overlay to a governance SHA and invalidate on drift. **Fourth occurrence.** The predecessor recorded `assessed_against_sha: 30c6ecd4` — which is CI-034's *recording* half — and then main advanced 59 commits with nothing flagging it. Recording the SHA without the check only makes staleness legible to a reader who thinks to compare, which is what the predecessor said itself.

**CI-035** — cross-check the receipt stores. Reproducing at this binding (see CI-004 above). Still the cheaper and more reliable detector than CI-004's world-comparison, and still unbuilt. Fold into CI-004's Wave 1 lane if you prefer one record per defect class.

Neither is adopted here. Adopting them is a scope decision for the pack owner, and this revision reconciles rather than expands. The `blocked_on: external` schema addition **is** adopted, because without it the active-queue count is not honest — see `progress.yaml: schema_additions`.
