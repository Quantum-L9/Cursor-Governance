# Execution runbook | verified owners and bounded joins

## R0: CTO opt-in and read-only preflight (no mutations)

1. Open `commands/lcto.md` from the **current** Cursor-Governance checkout; explicitly activate `/lcto` using that mode's declared interpreter/entrypoint from the target workspace. Require mode JSON `ACTIVE`, inspect every `load[].composed_view` and cite digest. If `BLOCKED`, do not claim CTO projection competence or silently reconstruct it from docs.
2. Pin current `Quantum-L9/.github`, `Quantum-L9/l9-semantic-compiler-engine`, and `Quantum-L9/Cursor-Governance` main SHAs. Confirm exact checkout origins and read mode/merge/publish source at that revision. Snapshot current exact PR heads, bases, CI, reviews, threads, conflicts and checks for #255, #1011, #1030. The 2026-11-17 snapshot is evidence of **state then**, not state now.
3. Check .github PR #255 actually contains `docs/candidates/L9_Operator_Doctrine_Intent_Alignment_Admission_v1.0.0/repo-overlay/strategy/**`; compare all five source digests and overall `subject_digest` to `evidence/approved_v1_exact_subject_manifest.json`. If changed materially, do not infer the old approval covers it.
4. Inspect `governance/cto-mode/MODE.yaml#operating_protocol`, `ops/autonomy/cto_mode.py`, `ops/autonomy/session_role.py`, `/coding-agent` mode and `ops/autonomy/swarm_role_gate.py` in current Cursor. Resolve whether operator merge permission is recorded under its present merge-authority switch. Use only the actual operating plane, not a copied prompt.
5. Inspect and freeze the **current** changed-file census of #1011/#1030 before declaring C/D disjoint. Start up to **four** fixed Cursor Task slots under `governance/cto-mode/MODE.yaml`; use exactly the host-rendered `child-prompt` as the system prompt, with `lanes/<id>.md` as task scope. Each child registers and reports `/coding-agent` ACTIVE before changes. On Cursor, follow the mode's Task continuation contract; no cross-session messages from children, no separate integration agent.

## R0.2: Lane A is the `.github` writer

Render `child-prompt` from `$HOME/.cursor-governance` at `origin/main` and record that SHA. The binding prompt requires a non-shallow clone of `Quantum-L9/.github` before edits. That clone is the `/coding-agent` authority root. Lane A publishes `#255` remediation and the seven-file `strategy/` overlay with `make pr` and `WS` set to the `.github` checkout. Do not invent a fifth worker. Do not edit `operating_protocol`. Raw `git push` and `gh pr create` stay forbidden. A hook denial of that `make pr` is the blocker, reported with the hook's own message.

## R0.5: Exact cross-lane interface and ownership freeze

- CTO computes file ownership from the *live* #1011 and #1030 PR diffs, compares them with lane D's actual planned file paths, and rejects any duplicate writer before code edits. Lane C alone repairs its stacked PR branches; D alone owns its new separate worktree. Newly discovered overlap is a CTO reassignment/dependency decision, not a waiver.
- CTO resolves the *actual* operator-source projection contract before allowing B or D to introduce an API or record shape. The existing `.github` global admission skill does not authorize arbitrary `strategy/` sources. If a new global language rule is needed, pause just J2/J4 and route outside the frozen campaign.
- For each downstream role record `requested`, `available`, `admitted operator source`, `producer verified`, `consumer verified`, `actor authorized`, `host active`, and `read-isolation proof` separately. No collective success inference.

## R1: Four parallel lanes

**A `.github` admission:** Confirm #255 status, source bytes, and exact approval. Remediate `#255` inside its live changed-file set and publish the seven-file `strategy/` overlay. No global `semantics/` edits. Publish with `make pr`, then stand down. The CTO merges it in the post-integration train.

**B compiler producer:** Resolve the difference between a registered global source and an operator-scoped source. A strategy-owned YAML merely present in `.github` is not a `CanonicalAuthority` projectable source. Inspect current real CLI `projection-coordinates`, `project`, `compose`, `verify-projection`, `CanonicalAuthority`, selectors, receipts and payload validation. Prove whether existing verified producer can render **operator-owned** strategy source classes without misclassifying them as globally canonical. If no compliant path exists, first identify which contract/owner must authorize the new source-class interpretation; return a CTO-QUESTION with the exact missing semantic contract. Only implement a compiler-owned operator-scoped adapter when existing applicable authority or separately approved local contract explicitly permits it. Do not create a schema by guessing, forge global admission, or copy producer logic into Cursor. Otherwise keep J2 BLOCKED and continue unrelated work. The consumer never becomes a second projector. Publish only genuinely necessary compiler change; target existing projection-focused tests and negative controls.

**C Cursor prerequisite merge:** Converge #1011, then its stacked #1030. #1011 is skill and registry; #1030 is the Planner mode, generated bundles and relevant workflow/driver. The PR's `base=skills/l9-strategic-plan` is a **live stack**: do not squash a parent in a way that drops the child. CTO uses current `stack_safe_merge.py` and stack handling. After #1011 integration, re-evaluate #1030's target base, diff, producer-issued receipts and CI at the new head before its merge.

**D Cursor consuming views:** Prepare a bounded operator-alignment verifier and mode adapter **without editing C-owned paths**; do not claim a producer-backed view before Lane B has a verified contract and emission. The actual interface is specified by `PRODUCER_CONSUMER_HANDOFF.md` as a checklist, not a fabricated data format. Existing `ops/autonomy/projection_mode.py` already verifies admitted-and-current global bundles; extend or reuse it only as needed for an **independent operator-owned source view**, preserving existing mode APIs. Create explicit, source-specific fail-closed operator verifier; consume only producer-emitted verified bytes, not local re-selection. CTO/Architect can be prepared independently. Planner integration only after C; Meta Planner must remain advisory and cannot mutate Plan. Coding Agent view only six delegated obligations, verified no strategy source leakage, and never granted wider repo authorization by projection.

## R2: Hold every in-scope PR for one integration test

Children do not merge. The CTO does not merge a lane just because that lane published.

1. After each child stands down, repair red required checks on that branch inside the frozen write set.
2. Build a disposable worktree that combines the campaign heads. Run the CTO integration tests there. `#1011` stays the parent of `#1030` in that combination.
3. When those tests pass, merge every in-scope PR with `ops/autonomy/stack_safe_merge.py --run`. Order is `#1011`, then retarget and revalidate `#1030`, then `#1030`. `#255` merges before a strategy adoption PR that contains it. Verify each mainline SHA. Candidate docs alone are not admission. The adoption merge is operator-scoped. Do not call the global `semantics/` admission skill for it.
4. If B's result is `BLOCKED_INTERFACE`, record it and continue the merge train for PRs that do not depend on a producer receipt. Do not open a compiler PR that spoofs a global source.
5. Confirm `/planner` on main after `#1030` merges. Activation claims that require main wait until this train. The CTO runs the combined tests itself.

## R2.5: What the completion grant merges

The operator grant covers the three named PRs and every follow-on PR lanes A–D open whose diff stays inside that lane's write scope. The trigger is campaign completion plus passing CTO integration tests, plus green required checks on that head. `.github#254`, a global `semantics/` change, a diff outside the lane write scope, and a red required check stop at `MERGE_PENDING`. This runbook never instructs agents to manufacture a grant, disable enforcement, or merge by bypass. Children never merge.

## R3: Role-specific activation and acceptance

- CTO: opt-in `/lcto` remains ACTIVE and now loads an independently verified operator-alignment view *in addition* to the existing eight global domain projections. Conflicts/stale source => BLOCKED for the affected alignment input, not silent fallback or new authority.
- Architect: existing `/architect` requires valid global architectural projections plus exact operator view; no change in architecture admission authority.
- Planner: do not activate until the #1011/#1030 stack actually lands on main and Planner's Plan Keeper identity is verified; the Plan remains in its designated Memory owner, not a copied Git plan.
- Meta Planner: bind advisory-only view to its real consumer if observed. Do not invent an always-on Meta Planner mode to meet a checklist; report `BLOCKED_NO_CONSUMER` where absent.
- Coding Agent: verify delegated-only content, no full upstream material, and actual credential/repo access constraints. Because a full `.github` read credential can access the whole repository, **a prompt-level restricted view is not proof of confidentiality**. Do not enable or call that assurance PASS until this is structurally resolved. No plan graph access to ordinary coding agents.

## R3.5: Coding Agent access truth

As long as a real Coding Agent identity can read `Quantum-L9/.github` and the `strategy/` records within it, its restricted view may be mechanically accurate as **context minimization**, but **upstream confidentiality is NOT PROVEN**. G5 and J5 stay blocked, regardless of a correct JSON preview. Do not claim Coding Agent protected-source ACTIVE or substitute a prompt for ACL. CTO/Architect/Planner activation can proceed independently if their own gates pass.

## R4: Closure

For each PR: record repo, number, prior/head Sha, base, latest checks and review state, exact merge method/status and observed mainline SHA; **not just a green button**. For admission: record file-set sha256 and operator decision reference, separate from global semantic law. For each projected view: record source owners, revisions, source/raw digests, producer version, PASS receipts, replayer/verifier evidence, actor identity, ACL enforcement, consumer mode and decision test results. For blocked roles record earliest owner and one next action. CTO reports `ACTIVE`, `BLOCKED`, `REJECTED`, `STALE` or `NOT_IMPLEMENTED` by role and never a fabricated universal success.

**No unauthorized adjacent work.** Never merge `.github#254`; don't opportunistically solve CI architecture unrelated to this campaign; do not create alternate SSOTs or Memory writers.
