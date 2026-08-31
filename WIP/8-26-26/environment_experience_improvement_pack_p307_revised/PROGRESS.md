# Environment Experience Improvement Pack — Progress (revision r2)

> **THIS PACK IS PROVENANCE, NOT THE LIVE QUEUE.** As of 2026-08-29 the live
> remaining-work queue is `WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json`
> (see `WIP/8-26-26-Claude Environment/_archive/DEPRECATED.md`). Read that first.
> Nothing here should be executed or `make campaign`'d from.
>
> **Last assessment of this pack: `main@a2f78b5`, 2026-08-29 — see [Re-assessment 2026-08-29](#re-assessment-2026-08-29--targeted-against-maina2f78b5).**
> That pass is **targeted**: it re-judged CI-004, CI-028, CI-005, CI-015, CI-002, CI-102 and CI-007
> against the tree. Everything else on this page is the `59f03a5d` assessment and is 64 commits
> stale. Current counts: **7 done · 17 partial · 10 not started · 1 blocked · 3 unknown**.

Assessed against **main@59f03a5d** on 2026-08-28, full SHA `59f03a5d4460b939360bc2fd5dd85239d47416a5`.
Predecessor: `WIP/8-26-26/environment_experience_improvement_pack_p307`, assessed at `30c6ecd4`.

**As assessed at `59f03a5d`:** 2 done · 16 partial · 16 not started · 1 blocked · 3 unknown (of 38).
Active queue 27; 6 external-blocked, 3 unverifiable without a repository attachment, 2 closed.

**After execution wave 1 (PR#360, open):** **7 done · 15 partial · 12 not started · 1 blocked ·
3 unknown** (of 38). **Active queue: 20.** 8 external-blocked, 3 needing an attachment, 7 closed.

Both figures are stated because they answer different questions, and collapsing them is exactly
how the predecessor came to carry three different counts in three stores. Every count above is
derived from the records themselves — `progress.yaml`'s stated `counts` and the tally over its 38
records agree by construction.

> **This pass is full, not targeted.** The predecessor was explicit that it re-verified only
> the records touched by #324 and #325 and carried the rest forward. It named `30c6ecd4`;
> main is at `59f03a5d`, 59 commits and 514 files later. Carrying judgements forward across
> that gap is how three records came to be wrong, so every record here was re-judged against
> the tree and the live container.

## Re-assessment 2026-08-29 — targeted, against `main@a2f78b5`

`main` advanced **64 commits** from `59f03a5d` to `a2f78b5`, and Cursor-Governance **PR#373**
(squash `7df89e74`) landed the `WIP/8-29-26/l9-runtime-velocity` implementation, which delivers
directly against records in this queue. Counts after this pass:

**7 done · 17 partial · 10 not started · 1 blocked · 3 unknown** (of 38) — `partial` +2 and
`not_started` −2 against the `59f03a5d` figures below.

> **This pass is targeted, not full.** Seven records were re-judged against the tree and the live
> container: **CI-004, CI-028, CI-005, CI-015, CI-002, CI-102, CI-007**. The other **31 are carried
> forward from `59f03a5d` unexamined** and are 64 commits stale — treat them as provisional. This is
> the same shape as the defect the r2 header below calls out in its own predecessor, which named
> `30c6ecd4` while main had advanced 59 commits. It is stated here rather than left implicit,
> because leaving it implicit is what made three records wrong last time.

| Record | Was | Now | What changed |
|---|---|---|---|
| **CI-004** | 🟡 partial | 🟡 partial | **R1 and R2 cleared.** Velocity T5 binds receipt freshness to the governance revision; T6 re-runs the installer once per revision when the receipt is not `ready`. Verified live: recorded `a2f78b531b55` equals live, receipt age 168s, so the guard is active and the DEGRADED verdict is current rather than inherited. **R3 is now the record's whole content** — five components still report bare `DEGRADED` with one global remediation string and no per-component reason or log path. |
| **CI-028** | ⬜ not started | 🟡 **partial** | Velocity T3 and T4: `session_deps_cloud.sh` fingerprints, installs and stamps **per repository**, and `toolchain_proven()` gates the stamp so a failed install refuses it. Banner reads `4/4 repositories cached and proven`. **R1 not cleared** — the stamp is a bare `touch`, carrying neither the deps exit code nor a timestamp. |
| **CI-005** | ⬜ not started | 🟡 **partial** | Half of R4 only: the banner now enumerates every discovered repository as hydrated or skipped. The other half is open — `workspace_roots()` sorts alphabetically and truncates at 6, so a 7th repo is dropped by alphabet, not by declared scope. R1's premise is live this session: `memory` is DEGRADED because the graphiti-memory MCP returns **502, upstream dial failed** — precisely the transport-specific split R1 asks for. |
| **CI-015** | 🟡 partial | 🟡 partial | Velocity RC-6 closed the destructive leg — the cloud refresh now skips its hard reset on a clone with tracked modifications and records `reset-skipped-dirty`. R1 stays open **and its precondition is live**: `/root/.cursor-governance` (where the hooks run) and `/home/user/Cursor-Governance` (where the session works) both exist, and nothing prints both paths with their revisions. |
| **CI-002** | 🟡 partial | 🟡 partial | Velocity T2 brought per-repository `.claude` mirrors inside the reconcilers' target set via `projection_roots()`. R1 and R2 untouched. |
| **CI-102** | 🟡 partial | 🟡 partial | R1's premise **re-verified in this container**, not carried forward — see the truth-table below. R1 remains the deliverable, scheduled as velocity T7. |
| **CI-007** | 🟡 partial | 🟡 partial | Scheduled as velocity T9. Its blast radius widened: `L9_PUBLISH_PATH_OVERRIDE` has **three** code/config readers, so R2 is a cross-surface contract change, not a single-site edit. |

### GitHub transport, probed 2026-08-29 (CI-102 / CI-001)

| Probe | Result |
|---|---|
| `gh` | present, `/usr/bin/gh` v2.98.0 |
| `gh api user` | succeeds, resolves `cryptoxdog` |
| `gh auth status` | reports `The token in GH_TOKEN is invalid` **and exits 0** |
| `gitleaks`, `pre-commit`, `uv` | present |
| `semgrep` | absent |

`gh auth status` is a **misleading detector**: it reports failure and exits 0, so any script
branching on its exit code silently takes the success path. CR-105 and CR-124 remain
`OBSERVED_CONTEXT_SPECIFIC` and are **not** overturned — this is a dated counter-observation for
this container, not a correction of theirs.

Companion pack: `WIP/8-29-26/l9-runtime-velocity` (`PROGRESS.md`, `progress.yaml`).

---

## Execution wave 1 — what was built, on a branch, and published

Branch `claude/cursor-governance-pack-reconcile-9d4c9v`, forked from `0fc6ee6f`, head
`8d812336`, published as **PR#360 against `main` — open, mergeable, not merged**, carrying the
`<!-- L9_PROTECTED_ROOT_PR -->` marker the protected-root gate requires. Gate evidence:
`make pr-check` green, 628 tests, 0 failures, ruff clean, working tree clean at head.

Seven of the queue's 26 execution units shipped. Eight records were touched.

| Record | Was | Now | Delivered | Left |
|---|---|---|---|---|
| **CI-027** | ⬜ not started | ✅ **done** | Rule 03's interpreter rationale replaced with the true one — version pinning and dependency isolation. Measured first: system `python3` is 3.11.15 and imports PyYAML fine; the venv is 3.12.3. Mandate unchanged. | — |
| **CI-030** | ⬜ not started | ✅ **done** | Both receipt CLIs read by default; `--read` still accepted and pinned byte-identical; CLAUDE.md names the command, with a test holding that text true. | — |
| **CI-025** | ⬜ not started | ✅ **done** | `make clean-pyc` → `clean_pyc.sh`: exact names only, name re-asserted at the deleting line, `.git` pruned, empty/missing/`/` root refused. | — |
| **CI-018** | ⬜ not started | ✅ **done** | `make test-ci-parity` runs both suites under CI's identity conditions and pr-check's docs point at it. Both suites pass at parity. | — |
| **CI-014** | 🟡 partial | ✅ **done** | `--workspace` on all 11 `graphiti_memory_client.py` subcommands; six `Path.cwd()` identity reads routed through `target_repo()`; actionable refusal; 12 tests including a source-walking guard. | — |
| **CI-003** | 🟡 partial | 🟡 partial → **external-blocked** | `.mcp.json` added to install.sh's exclude block; scoping pinned in both directions. | Hook-side ownership classification — external. |
| **CI-036** | 🟡 partial | 🟡 partial → **external-blocked** | `sync_remote_refs()` carries prune *and* `origin/HEAD`, fail-soft in three stages, held by a cross-site test. | Harness stop-hook resolution — external. |
| **CI-016** | 🟡 partial | 🟡 **partial** | IMP-14: `resolve_pr_template()` against the released repo, `None` when absent. | **I-BS-09** — `status` still reports staleness only inside `release_allows_remote()`'s prose `reason`, with no explicit field. |

Three findings are worth stating rather than burying in the record rows.

**CI-036's residual named the wrong defect.** It said timing; #325 had already fixed the timing.
The real fault was a *split invariant*: `bootstrap_agent_environment.sh` ships prune and
`origin/HEAD` together because pruning alone converts an overcount into **silence**, and
`repo_hygiene.py` had only the first half — in the tool that *deletes branches* on that evidence.

**CI-025's IMP-05 leg is re-scoped, not implemented.** Its named target is already invoked as
`PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B` (Makefile:616), which *prevents* the debris the leg asked
to clean up, and `.gitignore` covers both directories. Recorded as no-longer-required with the
evidence, rather than re-implemented to satisfy the wording.

**CI-018 deliberately deviates from its residual's wording.** The residual asked for "both git
config files at `/dev/null`" — a form `verification_bypass_gate.py` denies, because those
variables suppress the config that can carry `core.hooksPath` and the gate cannot tell a parity
run from a bypass. Written that way first, it ran only because the gate evaluates tool
invocations, not commands inside a Make recipe. Shipping a target that normalises a denied form is
how an exemption gets invented. Isolation is `HOME` alone and the property is **asserted** — the
run aborts naming the leaking key — which is stronger than the env-var recipe, since that one only
ever assumed its mechanism worked.

### Three repairs outside the pack

Rule 42/3: a pre-existing error is in scope the moment it is identified. All three were red on
`main`.

- **`99608999`** — `run_pr_precommit.sh`: restored the staged-mode exemption #347 dropped. Without
  it, `install_commit_hook.sh`'s governed shim rejected **every** commit, so the one supported way
  to verify at commit time was broken.
- **`8eff1c60`** — justified #359's five added gate-timing swallows plus `9ecfc823`'s one, and
  un-redded the ratchet. Each was read first; none swallows the result of a check. `SWALLOW_BASELINE`
  *is* the justification mechanism — an earlier reading of the bump as rule-60 weakening was mine
  and was wrong.
- **`8d812336`** — `session_debt.py`: `OPEN_STATES` (live view) split from `BLOCKING_STATES` (ends
  a turn), rule 42 amended, deferrals always printed. This is not CI-037, which stays done; it is
  the satisfiability defect underneath it. A turn that had pushed everything and reasoned every
  finding still could not end — the unclearable gate rule 42's own Satisfiability section calls
  worse than no gate. `open` stays the only blocking state deliberately: a `record` that ended a
  turn would make *declaring* a finding the abandonment the rule exists to prevent.

### What is left

**20 records active.** The critical path is untouched and unchanged: **`CI-004` → `CI-005`**,
weight 6, still the two most expensive records in the queue. `CI-004` is the P0 — a
`governance_revision` mismatch is still not treated as receipt expiry, so the stale-receipt defect
reproduces at every binding and TTL will never catch it, and `CI-005` is gated behind it.

Remaining effort **35 of 42** units across **19 of 26** execution units. `CI-016`'s weight is not
decremented although a leg shipped: fractional consumption makes the remaining figure unauditable,
so the narrowed residual sits on the record instead.

The makespan **lower bound** at 4 lanes falls from 11 to **9** — `max(6, ⌈35/4⌉)`. The *achievable*
makespan is deliberately not restated. Removing seven units changes which pairs collide and which
lane assignment is optimal; that needs the scheduler re-run, not an arithmetic adjustment.

### Five findings deferred to a human

| Finding | State |
|---|---|
| `od-002-makefile-precedence` | The operator's correction — workspace Makefile first, SSOT clone second — contradicts `surface_profile.yaml`, CLAUDE.md, rules 48/88 and `test_publish_verb_governance_always.py`. Scoped "behaviour only, for now", so **no doctrine was changed**. `OPEN_DECISIONS.yaml` OD-002 moves `RESOLVED` → **`REOPENED`** and CI-008 is flagged as shaped by the old direction. |
| `verify-gate-denies-hookspath-read` | `verification_bypass_gate.py` denies `git config --get core.hooksPath` — a *read*. The matcher does not separate `--get`/`--get-all`/`--list` from a write, so diagnosing the hook model is blocked by the gate protecting it. Narrow fix: exempt read forms. |
| `debt-gate-deferred-still-blocks` | Superseded by `8d812336`; left open for a human to close. |
| `debt-gate-fix-cannot-self-apply` | `session_debt_wrap.py:15` pins the gate to the **SSOT clone's** copy, so a fix to the debt gate cannot take effect for the session that writes it. Clears when `8d812336` reaches `main`. |
| `gate-fail-receipt-unclearable-by-projection-fix` | The PR gate's FAIL receipt keys on tracked content, but the repair it names for a projection drift writes only into untracked `.claude/`. Doing exactly what the gate asks does not change the digest, so the next run refuses with STOP LOOPING. Found while recording this wave; deferred because it is the gate blocking the turn. |

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

The first pass scheduled this as six waves of up to four lanes. That model is replaced.
It cost **13 effort units at 4 lanes against an 11-unit lower bound**, for two reasons,
and both were mine rather than the pack's.

**Waves are global barriers.** Every lane in wave N+1 waited for every lane in wave N.
Nothing in the dependency structure required that.

**It grouped by file, and the repository does not.** Rule 53 runs `git merge-tree
--write-tree` precisely to tell same-file/disjoint-hunk apart from a real textual
conflict. Grouping at file granularity invented serialization the repo is built to avoid.

Recomputing collisions at region granularity dissolved four of the five groups:

| Group | Was | Now |
|---|---|---|
| `G-rules` | CI-012 -> CI-102 -> CI-023 -> CI-027 -> CI-015, one lane, five deep | Dissolved. The four rule records touch four different .mdc files and share only the GENERATED projection, which is merge-driver exempt. CI-015 was in the group by mistake — its targets are the session-start banner and resolve_governance_paths.sh, not a rule file at all. The chain of five becomes three independent units plus one genuine pair. |
| `G-gate` | CI-025 -> CI-013 -> CI-002(2c) | CI-025 does not edit the gate. Its targets are the Makefile (`clean-pyc`) and validate_execution_adapters.py. It is a singleton. And CI-002's gate edit is the state-dir path while CI-013's is denial staging — different regions, so the CI-002 -> CI-013 edge is dropped too. |
| `G-bootstrap` | CI-009+CI-028 -> CI-036, with CI-004 held out of the group | Four records touch bootstrap_agent_environment.sh — CI-004 (receipt writer), CI-009+CI-028 (deps stage), CI-036 (prune section). Three disjoint regions of one file. None of them collide, and CI-004 was never outside the group to begin with. |
| `G-l4` | CI-016 -> CI-002(2c) | l4_local.py#receipt-fields vs l4_local.py#statedir vs l4_local.py#refusal (CI-014): three disjoint regions, no collision, no semantic order. Edge dropped. |

Of 325 unordered pairs across the 26 execution units, **2 collide**:

- **CI-007 × CI-015** on `session_start#banner-authority` — CI-007 first. Both add a line to the banner's authority section — CI-007 reports a breakglass grant in force, CI-015 names which of two governance clones rules resolve from. The grant line lands first because it is the P0.
- **CI-015 × CI-023** on `resolve_governance_paths.sh#assert` — CI-023 first. CI-023 adds the source-without-call guard; CI-015 makes the resolver assert which clone is authoritative. Both add logic to the same entry-point region, and the guard is what the assert reports through.

Nine inherited dependency edges were dropped; 4 survive.

| Dropped edge | Why it does not hold |
|---|---|
| `CI-002 -> CI-013` | gate#statedir vs gate#stages — different regions, no semantic order |
| `CI-002 -> CI-016` | l4#statedir vs l4#receipt-fields — same |
| `CI-003 -> CI-002` | CI-003's lever is install.sh's exclude block; it consumes no ownership guard |
| `CI-012 -> CI-004` | rule text and rule frontmatter never read the bootstrap receipt |
| `CI-018 -> CI-009` | a ci-parity make target does not need the deps import smoke to exist |
| `CI-022 -> CI-009` | a session-start coverage declaration is unrelated to interpreter authority |
| `CI-023 -> CI-009` | CI-023's remaining scope does not change WHICH interpreter resolves |
| `CI-025 -> CI-013` | inverted in practice — clean-pyc removes the pressure that motivates narrowing the guardrail |
| `CI-028 -> CI-009` | not a dependency, the same edit — collapsed into one unit |

### Cost and the shape of the constraint

Total effort **42 units** across 26 execution units, weighted from the source records' own S/M/L estimates and scoped to the in-repo residual. Weighted critical path **6**: `CI-004 → CI-005` — two records, but the two most expensive in the queue, one gating the other.

| Lanes | Makespan | Lower bound | |
|---|---|---|---|
| 2 | **21** | 21 | optimal |
| 3 | **14** | 14 | optimal |
| 4 | **11** | 11 | optimal |
| 5 | **9** | 9 | optimal |
| 6 | **7** | 7 | optimal |
| 7 | **6** | 6 | optimal |
| 8 | **6** | 6 | optimal |

The schedule meets its lower bound at every width. It saturates at **7 lanes** — an eighth concurrent branch buys nothing and costs a review slot.

### The one lever, and why it was not pulled

split CI-005's receipt leg (I-BS-05, depends on CI-004) from its three hydration legs (independent), shortening the path from 6 to 4. **NOT TAKEN** — Measured rather than assumed. Total effort is unchanged at 42, so below 9 lanes the schedule is effort-bound and the shorter path buys exactly zero: makespan is identical at W=2..8. It first pays at W=9 (6 -> 5). Splitting a pack record to win nothing at every width anyone will run is scope churn, so CI-005 stays whole. The partial dependency is recorded on the record instead, so a team running wide can start its hydration legs without waiting.

### Recommended width: 4 lanes

Not the fastest — 6 lanes finishes in 7 units against 11. It is the width the publication doctrine supports. Rule 48 stacks concurrent PRs bottom-up with rebase and conflict resolution forbidden, which holds only while scopes stay disjoint; every additional lane is another branch that must stay mergeable against a moving base. Four lanes keeps the stack reviewable and still beats the wave model. Go to 6 if review throughput allows; there is no reason to exceed 7.

**Makespan 11** (6 lanes would finish in 7). Intervals are effort units, not days.

| Lane | Sequence |
|---|---|
| **L0** | `[0-3] CI-004` → `[3-6] CI-005` → `[6-8] CI-019` → `[8-9] CI-025` → `[9-10] CI-021` → `[10-11] CI-017` |
| **L1** | `[0-3] CI-012` → `[3-4] CI-010` → `[4-5] CI-030` → `[5-7] CI-023` → `[7-9] CI-015` → `[9-10] CI-018` → `[10-11] CI-032` |
| **L2** | `[0-2] CI-007` → `[2-4] CI-006` → `[4-6] CI-008` → `[6-8] CI-002` → `[8-9] CI-016` → `[9-10] CI-027` |
| **L3** | `[0-2] CI-009+CI-028` → `[2-4] CI-102` → `[4-6] CI-013` → `[6-7] CI-003` → `[7-8] CI-036` → `[8-9] CI-014` → `[9-10] CI-022` |

The four openers are leverage 1, 2, 3 and 6 — the highest the DAG permits at t=0. CI-007, the live standing breakglass grant, opens L2. L0 carries the critical chain, CI-004 then CI-005, and has no slack: any slip there slips the program. CI-003 is leverage 5 but only one effort unit, so it slots at [6-7] rather than consuming a lane opener — spending a t=0 slot on the queue's cheapest item would displace a 3-unit head and cost a full unit of makespan.

At 6 lanes, for comparison — makespan 7:

| Lane | Sequence |
|---|---|
| **L0** | `[0-3] CI-004` → `[3-6] CI-005` → `[6-7] CI-021` |
| **L1** | `[0-3] CI-012` → `[3-4] CI-010` → `[4-6] CI-015` → `[6-7] CI-018` |
| **L2** | `[0-2] CI-007` → `[2-4] CI-006` → `[4-5] CI-030` → `[5-6] CI-025` → `[6-7] CI-027` |
| **L3** | `[0-2] CI-009+CI-028` → `[2-4] CI-013` → `[4-6] CI-002` → `[6-7] CI-022` |
| **L4** | `[0-2] CI-102` → `[2-4] CI-023` → `[4-5] CI-003` → `[5-6] CI-016` → `[6-7] CI-017` |
| **L5** | `[0-2] CI-008` → `[2-4] CI-019` → `[4-5] CI-036` → `[5-6] CI-014` → `[6-7] CI-032` |

### Ordering law

Priority class never overrides a prerequisite, and leverage never overrides a collision. Within what the DAG permits, the scheduler starts the ready unit with the greatest remaining downstream depth — which is why a P2 (CI-028) opens at t=0 and a P0 (CI-002) is mid-queue.

## Full status

| Progress | Item | P | Lane | Slot | Eff | Seq | Lev | Deps | Title | Remaining |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟡 partial | **CI-004** | 0 | L0 | [0-3] | 3 | 1 | 2 | — | Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components | IMP-03 / I-BF-01: treat a governance_revision mismatch as expiry, distinct from TTL expiry. |
| 🟡 partial | **CI-012** | 1 | L1 | [0-3] | 3 | 2 | 6 | — | Gate rules and MCP config on actual surface capabilities | IMP-07: extend rule 22 with the server-absent case and name the required fallback, so the obligation stays closable. |
| 🟡 partial | **CI-007** | 0 | L2 | [0-2] | 2 | 3 | 1 | — | Replace standing breakglass environment strings with scoped expiring receipts | IMP-04 / ENV-2: remove the standing variable from the account environment, or replace its value with one that describes an actual standing policy. |
| 🟡 partial | **CI-009** | 0 | L3 | [0-2] | 2 | 4 | 3 | — | Establish one project interpreter/toolchain authority and verify importability before READY | I-EL-05: end the deps pass with an import smoke on the resolved interpreter; record interpreter path and version in the log. |
| ⬜ not started | **CI-028** | 2 | L3 | [0-2] | 2 | 5 | 4 | — | Improve dependency provisioning evidence and determinism | I-EL-03(P8): write the deps step's exit code into the stamp or the log's final line, and timestamp the log. |
| 🟡 partial | **CI-006** | 0 | L2 | [2-4] | 2 | 6 | 8 | CI-007 | Resolve authority-sensitive environment drift at the actual source | I-EL-02: name the file that produced the live value when a variable drifts. |
| 🟡 partial | **CI-102** | 4 | L3 | [2-4] | 2 | 7 | 10 | — | Valid GH_TOKEN or formal surface exemption from gh-dependent gates | Record the REST route as a sanctioned surface capability in ops/autonomy/surface_profile.yaml and rule 62, or provision the PAT. Until then the nex… |
| ⬜ not started | **CI-005** | 1 | L0 | [3-6] | 3 | 8 | 7 | CI-004 | Make memory health transport-specific and continuity task-bearing | I-BS-05: split the receipt's `memory` component into memory.cli and memory.mcp, probed independently, with the CLI verdict based on graphiti_memory… |
| 🟡 partial | **CI-010** | 0 | L1 | [3-4] | 1 | 9 | 9 | CI-004 | Make broker authentication and reachability diagnosable | I-EL-02: report proxy-denied and upstream-error as distinct probe states, so an allowlist remediation decision has something to decide on. |
| ⬜ not started | **CI-030** | 3 | L1 | [4-5] | 1 | 10 | 19 | CI-004 | Improve receipt CLI ergonomics without multiplying state owners | LOADER-1: make bare invocation read and print, keep --read accepted, and name the exact command in CLAUDE.md's receipt paragraph. |
| 🟡 partial | **CI-008** | 0 | L2 | [4-6] | 2 | 11 | 12 | — | Reconcile make pr doctrine with consumer-repository command contracts | Enable the consumer-workspace path: cwd=$GOV_ROOT so repo-local `entry:` hooks resolve, absolute --files paths, and a governance-only-local-hook sk… |
| ⬜ not started | **CI-013** | 1 | L3 | [4-6] | 2 | 12 | 13 | — | Preserve fail-closed destructive/staging gates while making denials actionable | I-BS-10 (in-repo): name the refused stage of a compound command and state that later stages did not run. |
| ⬜ not started | **CI-023** | 1 | L1 | [5-7] | 2 | 13 | 15 | — | Collapse variable-loading authorities into one reproducible loader contract | IMP-02(P4): amend rule 06 to `source …; resolve_governance_paths_or_exit`. |
| ⬜ not started | **CI-019** | 2 | L0 | [6-8] | 2 | 14 | 22 | — | Coordinate concurrent writers on shared PR branches | IMP-06(P7) retry half: bounded fetch/merge --no-edit/regen/re-verify/push loop, N<=2, never rewriting history. |
| 🟡 partial | **CI-002** | 0 | L2 | [6-8] | 2 | 15 | 23 | — | Make bootstrap projection ownership-aware and non-destructive to tracked repo content | Phase 2c (relocate L9_AUTONOMY_STATE_DIR outside the worktree). The only unmitigated leg. Touches l4_local.py + local_execution_gate.py + make pr t… |
| 🟡 partial | **CI-003** | 1 | L3 | [6-7] | 1 | 16 | 5 | — | Make the Stop hook ownership-aware instead of residue-blind | Add `.mcp.json` to the Claude-specific exclude block in install.sh. One glob; the design decision it belongs to is already made and documented. |
| 🟡 partial | **CI-015** | 1 | L1 | [7-9] | 2 | 17 | 17 | CI-007, CI-023 | Name and enforce the authoritative governance checkout | I-BS-13: when a second checkout of the governance repository is present, print both paths with their revisions and state which one rules resolve fr… |
| 🟡 partial | **CI-036** | 2 | L3 | [7-8] | 1 | 18 | 11 | — | Keep unpushed-commit counts honest across merged-and-deleted branches | Consolidate repo_hygiene.py's prune with the session-start prune so a count read mid-session is not served by the session-end pass. |
| ⬜ not started | **CI-025** | 2 | L0 | [8-9] | 1 | 19 | 14 | — | Provide sanctioned cleanup of generated/cache residue | IMP-05/IMP-08(P7): add `make clean-pyc` and have the adapters gate pre-clean or ignore cache debris rather than failing on it. |
| 🟡 partial | **CI-016** | 1 | L2 | [8-9] | 1 | 20 | 16 | — | Make L4/release receipts resolve paths, branch, and head dynamically | IMP-14: resolve pr_template against the released repository across the standard template locations; emit null when none is found. |
| 🟡 partial | **CI-014** | 2 | L3 | [8-9] | 1 | 21 | 18 | — | Make target repository/cwd explicit for governance CLIs | Add --workspace to graphiti_memory_client.py, defaulting to current behaviour. |
| ⬜ not started | **CI-021** | 2 | L0 | [9-10] | 1 | 22 | 20 | — | Make session-experience and skill-usage logging observable | I-BS-11: narrow the matcher to namespaces this surface exposes, and emit a session-start line naming the log path and its current entry count. |
| ⬜ not started | **CI-018** | 1 | L1 | [9-10] | 1 | 23 | 21 | — | Make local CI parity and hooks first-class provisioning | IMP-01(P7): add a make target running the campaign and controller suites with HOME empty and both git config files at /dev/null, and reference it f… |
| ⬜ not started | **CI-027** | 3 | L2 | [9-10] | 1 | 24 | 24 | — | Correct rule rationale that no longer matches container reality | IMP-17: keep the pinned-interpreter mandate, replace the justification with the true one (version pinning and dependency isolation), and regenerate… |
| ⬜ not started | **CI-022** | 2 | L3 | [9-10] | 1 | 25 | 25 | — | Provision or explicitly declare service-backed integration-test dependencies | I-EL-07, in-repo half: state at session start that service-backed integration tests are unavailable, so the split between runnable and unrunnable c… |
| 🟡 partial | **CI-017** | 1 | L0 | [10-11] | 1 | 26 | 26 | — | Validate generated-artifact membership and report all drift in one pass | IMP-09 (l9-meta-injector): collect manifest staleness and dist divergence in one report, or add `npm run regen`. |
| ⬜ not started | **CI-032** | 3 | L1 | [10-11] | 1 | 27 | 27 | — | Give slow validation units explicit headroom without weakening total proof | IMP-10(P4): split the five-run incremental chain across two files, or reduce the incremental scale fixture while leaving corpus_scale.test.ts at te… |
| 🟡 partial | **CI-001** _external_blocked_ | 1 | — | — | — | — | — | — | Publish and enforce the real GitHub REST/GraphQL capability boundary | IMP-01 only: the remote-session prompt still denies gh access that demonstrably works. Harness-owned; no in-repo lever. |
| ⬜ not started | **CI-011** _external_blocked_ | 2 | — | — | — | — | — | — | Bound large MCP responses with field projection/pagination | — |
| ⬜ not started | **CI-020** _external_blocked_ | 3 | — | — | — | — | — | — | Expose notification age when queued state is delivered | — |
| ❓ unknown | **CI-024** _needs_attachment_ | 2 | — | — | — | — | — | — | Repair or remove foreign/stale bootstrap and deploy entrypoints | — |
| ⛔ blocked | **CI-026** _external_blocked_ | 3 | — | — | — | — | — | — | Support safe on-disk aliases for dot-prefixed repositories | IMP-16: durable alias support in add_repo, or an explicit record that attachment is per-session operator configuration and not a delivered capabili… |
| ❓ unknown | **CI-029** _needs_attachment_ | 3 | — | — | — | — | — | — | Persist repeatable cross-repo E2E fixtures | — |
| ❓ unknown | **CI-031** _needs_attachment_ | 3 | — | — | — | — | — | — | Keep repo documentation and tracked-path hygiene synchronized | — |
| ✅ done | **CI-033** _closed_ | 99 | — | — | — | — | — | — | Use pipefail in push/retry helpers | — |
| ✅ done | **CI-037** _closed_ | 1 | — | — | — | — | — | — | Make abandoned work fail closed instead of relying on doctrine | — |
| ⬜ not started | **CI-100** _external_blocked_ | 4 | — | — | — | — | — | — | Investigate why PR #70's workflow runs were gated in action_required | — |
| ⬜ not started | **CI-101** _external_blocked_ | 4 | — | — | — | — | — | — | Align the branch directive with the repository actually worked in | — |

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

**CI-035** — cross-check the receipt stores. Reproducing at this binding (see CI-004 above). Still the cheaper and more reliable detector than CI-004's world-comparison, and still unbuilt. Fold into CI-004's slot on lane L0 if you prefer one record per defect class.

Neither is adopted here. Adopting them is a scope decision for the pack owner, and this revision reconciles rather than expands. The `blocked_on: external` schema addition **is** adopted, because without it the active-queue count is not honest — see `progress.yaml: schema_additions`.
