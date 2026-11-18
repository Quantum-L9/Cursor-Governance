# Explicit existing PRs | converge and merge if still open

The operator's latest instruction authorizes these three existing PRs as campaign merge subjects, conditional on latest-head readiness. CTO is the only session that merges. Coding agents own remediation and publication through the existing repo ceremony, not merge.

| PR | Exact scope | Observed 2026-11-17 | Required ordering |
|---|---|---|---|
| `.github#255` | v1 docs/candidates/ operator addition | open; `mergeable_state=blocked`; `mergeable=true`; head `922427b28e...` | independently converge, then merge before or with adoption |
| `Cursor-Governance#1011` | strategic-plan skill and registries | open; `unstable`; head `92a347ff7c...` | parent, merge first stack-safe |
| `Cursor-Governance#1030` | `/planner` mode and producer-generated projection bundles | open; `unstable`; head `5f175329a0...`; base `skills/l9-strategic-plan` | child, merge after proper parent integration and revalidation |

`.github#254` is an unrelated repository-registry PR observed open and blocked. It is **explicitly not in the authorized merge set**; if it merges independently, re-resolve current `main` and impacted bundle digests.

## CTO per-PR decision rule

1. Re-query LIVE current PR `state`, `merged`, head commit, base branch and `mergeable_state`. If already merged, inspect actual merge commit and diff, confirm expected approved scope and mark `ALREADY_MERGED_VERIFIED`. If closed unmerged, do not invent a new PR or recreate without operator decision.
2. A PR that says `mergeable=true` but `blocked` or `unstable` is NOT green. Require all required checks green on the exact live head, reviewer constraints and threads closed, no conflict, and all prescribed target checks satisfied. The publishing lane agent owns fixes and resolves review threads **only when that agent is actually authorized to write the repository**. Under current CTO child rules `.github` Lane A cannot write; find a separate existing governed `.github` writer or record `BLOCKED_GITHUB_WRITER` for #255 remediation/adoption.
3. Resolve `ops/config/merge-authority.json` at the *current Cursor-Governance HEAD*. On the 2026-11-17 inspected main its enforcement is `disabled`, but this is NOT a permanent assumption; if it is now `strict`, follow `skills/l9-pr-remediation/SKILL.md` and active host-grant mechanisms and do not self-authorize.
4. Use only the current approved `ops/autonomy/stack_safe_merge.py` to merge, with `--repo`, `--pr`, and live `--head-sha`, in its documented `--run` mode. The command is recorded in the current source skill; verify it at the working host before execution. No `--admin`, force push, bypass, or manual GitHub merge pretending branch protection passed.
5. For #1011/#1030, preserve stacked commits; `stack_safe_merge.py` chooses the ancestry-safe merge method. After parent lands, retarget child to main only with a verified diff/ancestry check, and rerun all required head-specific CI/reviews before child merge. A retarget that drops generated receipts or a plugin manifest is a blocker.
6. After each merge, verify `main` includes the exact intended subjects, sha, and no forbidden changes. If PR head changed since approval and the change is material in Doctrine/Intent, the original exact approval is not enough.
7. The explicit instruction covers merges of **only** the three named existing PRs. New adoption, compiler or Cursor alignment PR publication is within the campaign, but its merge is **MERGE_PENDING until the live governance switch and applicable actual operator merge authorization allow the exact PR/head**. The CTO cannot treat the phrase “run the campaign” as a blanket future-head merge grant. If the switch is disabled, still use the ordinary operator instruction/CTO mandate interpreted by current law; never claim authorization from this ZIP alone.

## Publication command boundary

`make pr` belongs to `Quantum-L9/Cursor-Governance` SSOT (`ops/make/publish.mk` -> `ops/scripts/pr_preflight.sh` / `run_pr_gate.sh` / `open_pr_after_gate.sh`, or verified declared native routing). Lane agent checks live source and runs the **one** authorized ceremony with its own writable workspace and correct base. A root consumer `Makefile` does NOT need a `pr` target. No raw `git push`, no direct `gh pr create`, no duplicate `OPEN_PR=0 make pr` rehearsal. Use current hooks and `PR_REMEDIATE=0` under the sworn child contract.

## Merge train checkpoints

- **Train A:** `.github #255` current-head checks → stack-safe merge by CTO → verify candidate docs on `main` → separate exact `strategy/` operator adoption PR. Distinguish accepted candidate from adopted `strategy/` source at every stage.
- **Train C:** Cursor `#1011` current-head checks → merge **parent** with `stack_safe_merge.py` and observed ancestry → inspect `#1030` after parent merge; verify retarget/merge-base, projected receipts and full *child-only* diff → run current-head checks → merge child. Never silently squash an active stack parent or drop a child receipt.
- **Follow-on:** B and D PRs, when genuinely needed, are independent targets. They never auto-merge because the three named PRs were approved. Verify branch protections, required reviews and exact effective merge authority at merge time.

**Special `.github` write boundary:** `governance/cto-mode/MODE.yaml#child_system_prompt` at pinned Cursor main explicitly forbids children from branching or pushing `.github`. This is not cured by an operator campaign request, disjoint worktree, or writable label in a Task brief. If #255 is ready, the CTO may merge it via current merge policy without coding-child writes; if it needs remediation, the CTO must locate a pre-existing permitted `.github` writer. Its successor operator `strategy/` adoption PR likewise requires a real authorized writer. Until proven, the admission join is blocked; continue independent B/C/D work.
