# L9 Pipeline Orchestrator — spec → contracts → one-session-per-contract, hands-off

Goal: paste messy input once; get a full chain of PRs built, each in its own fresh Claude Code
session, in dependency order, without you copy-pasting between sessions.

## The three stages

```
STAGE 0 — SPEC (any LLM)
  You: paste messy input to  claude-code-spec-compiler
  Out: campaign-spec.yaml   (+ spec_report.yaml)

STAGE 1 — CONTRACTS (one Claude Code session, code compiler installed)
  Run: compile_contract.py --spec campaign-spec.yaml --out out --validate --emit-artifacts
  Out: out/PR-*/  each with {PR-*.contract.json, CLAUDE.md, settings.json, preflight.sh}
  Then: build orchestration state.yaml from the emitted set (one row per contract, in order).

STAGE 2 — BUILD (self-advancing fresh session per contract)
  A Routine fires a FRESH session for the next ready contract.
  That session: preflight -> build in scope -> npm run validate -> commit -> mark green -> launch next.
  Repeats until the chain is DONE.
```

## Why each contract gets its OWN session (not one big session)
The contracts are compiled to be **context-window-bounded**: one PR = one focused cold session that
`resume_from`s the prior contract `merged_and_green`. `preflight.sh` is the cold-start guard;
`CLAUDE.md` is the scope header; `settings.json` denies push/merge. This is the exact shape a
fresh-session-per-contract loop needs — the automation just drives what the contracts already assume.

## The merge gate — no HITL, deterministic auto-merge (v2.5.0)
Every contract **denies `git push` / `git merge` / PR-merge** by design. Build + validate + commit is
fully automated per contract. Promotion `green -> merged` (which unblocks the next contract) is a
**separate authorized step** — never the build session (DPK role isolation: an agent must not merge
its own work). The human tap is **removed** and replaced by a deterministic gate.

### Auto-merge gate (`automerge_gate.py`)
A PR is ELIGIBLE to auto-merge ONLY when ALL three hold:
1. **ci_green** — every check run / status is success|neutral|skipped; none pending or failed.
2. **review_flags_resolved** — no standing `CHANGES_REQUESTED`; required approvals met.
3. **review_comments_resolved** — all review threads resolved (or outdated) AND `remediation_ran: true`
   (the PR-remediation / autofix loop actually executed against the review-agent comments).

`advance.py state.yaml gate <id> pr_state.json` runs the gate; on ELIGIBLE (and `merge_policy: auto`)
it promotes `green -> merged` and unblocks the next contract. On BLOCKED it leaves the contract green
and prints the exact failing condition. `merge_policy: manual` returns the verdict but leaves promotion
to the operator.

### Per-contract flow (auto-merge)
```
build session (role: builder)   preflight -> build in scope -> npm run validate -> commit -> set green
merge  session (role: merger)   push branch -> open PR -> [PR remediation loop] -> fetch PR state
                                -> advance.py gate <id> pr_state.json
                                   ELIGIBLE -> merge_pull_request + set merged + fire next contract
                                   BLOCKED  -> keep remediating / report
```
The **PR remediation loop** is the environment's PR-steward (`subscribe_pr_activity`): it watches the
PR, autofixes CI failures, and resolves review-agent comments, setting `remediation_ran: true` once it
has run. Only then can condition 3 pass.

### Belt-and-suspenders: GitHub branch protection (so the merge CALL can't fire early) — BUILT
Two independent gates now guard the merge: the deterministic `automerge_gate.py` (in-orchestrator)
AND GitHub branch protection (server-side, objective). Even if the orchestrator were wrong, GitHub
refuses the merge until protection is satisfied.

**Repo-agnostic.** Nothing here is hardcoded to a repo, and **missing repo/branch is never a blocker.**
`owner/repo/branch`, the required status checks, and the review-agent CODEOWNER are all AUTO-DISCOVERED
(git remote, `.github/workflows/*`, `.github/CODEOWNERS`). Anything not discoverable degrades to a
warning and a resolvable placeholder — the dry-run always succeeds and emits a usable payload.

Files:
- `branch_protection.example.yaml` — desired state; every field is an OPTIONAL override. Defaults:
  `contexts: []` (auto-discover), `review_agent_owner: null` (auto/optional), `owner/repo/branch: null`
  (auto-detect). Strict up-to-date, `required_conversation_resolution: true`, `required_approving_review_count: 1`,
  `require_code_owner_reviews` (honored only if a CODEOWNERS owner exists), repo `allow_auto_merge: true`.
- `CODEOWNERS.example` — optional: assign the review agent as owner so ITS approval is the required one
  (**0 human approvals**). If absent, protection still enforces checks + 1 approval + conversation resolution.
- `apply_branch_protection.py [--config c] [--owner O --repo R --branch B] [--checks a,b] [--apply]` —
  runs with **zero args** inside any repo; auto-discovers everything, prints the REST payload + `gh api`
  commands (branch protection has no GitHub MCP tool). DRY-RUN by default; `--apply` enacts live only
  when a token is set AND a concrete owner/repo/branch was resolved. Also flips repo `allow_auto_merge`.
- `verify_branch_protection.py <config> <live_protection.json>` — fail-closed check that the LIVE branch
  matches the config before the orchestrator trusts native auto-merge.

Setup (in any repo — no repo/branch required up front):
```
1. (optional) commit .github/CODEOWNERS naming your review agent (from CODEOWNERS.example).
2. python apply_branch_protection.py                # auto-discovers repo/branch/checks/owner; dry-run
3. python apply_branch_protection.py --apply        # same, enacts live (GITHUB_TOKEN in env)
4. python verify_branch_protection.py branch_protection.example.yaml <(gh api repos/OWNER/REPO/branches/BRANCH/protection)
```

### Native auto-merge (the merge just fires when GitHub says all gates pass)
Per PR, the orchestrator merge-step calls the GitHub MCP tool
`mcp__github__enable_pr_auto_merge(owner, repo, pullNumber, mergeMethod)`. GitHub then merges the
PR **the instant** branch protection is satisfied (checks green + conversations resolved + agent
approved). `automerge_gate.py` becomes the confirming/record-keeping gate:
`advance.py gate <id> pr_state.json` verifies eligibility and flips `green -> merged` in state once
GitHub reports the PR merged. No human, no early merge.

### Migration record (control relaxation — logged, not silent)
```yaml
control_relaxation: remove_human_in_the_loop_before_merge
replaced_by: automerge_gate (ci_green AND review_flags_resolved AND review_comments_resolved+remediation_ran)
still_enforced:
  - build session cannot push/merge (denied_tools unchanged; role isolation preserved)
  - merge performed by a separate authorized step, gated deterministically
  - GitHub branch protection required as the outer objective enforcement
authorized_by: operator request (2026-07-13)
```

`advance.py` implements the chain via `chain_on` (`green` | `merged`) and the merge via `merge_policy`
(`auto` | `manual`) in `state.yaml`. For no-HITL per-PR gating, use `chain_on: merged` + `merge_policy: auto`.

## Wiring Stage 2 to this environment (Routines)
The environment spawns a fresh session per firing via a **Routine** (`create_trigger`) with
`create_new_session_on_fire: true`. Two ways to chain:

1. **Self-advancing (recommended):** each per-contract session ends by calling `fire_trigger` on the
   orchestrator Routine (or `send_later`), passing the next contract id via the trigger `text`. No
   polling; strictly sequential; each contract in a clean session. The Routine's prompt is
   `advance.py state.yaml seed <next-id>` output (the fresh-session seed below).
2. **Cron sweep:** a Routine fires every N minutes; each firing runs `advance.py state.yaml next`,
   and if a contract is ready, executes it. Simpler, but polls.

### The Routine prompt (fresh-session seed)
Set the Routine's `prompt` to instruct the session to: read `state.yaml`, run
`python advance.py state.yaml next`; if it prints a contract id, run
`python advance.py state.yaml seed <id>` and follow that seed exactly (preflight -> build -> validate
-> commit -> `set <id> green`); then, per `chain_on`, either fire the next session or stop and await
merge. If it prints `__AWAIT_MERGE__` stop and notify; if `__DONE__` report completion and disable the Routine.

## Files
- `advance.py` — deterministic driver: `next` | `seed <id>` | `set <id> <status>`. No side effects
  beyond `state.yaml`. Determinism stays in the script; the session decides WHAT to build.
- `state.example.yaml` — the ordered chain + statuses + `chain_on` policy.
- `make_state.py` — build `state.yaml` from an emitted `out/PR-*/` set (Stage 1 → Stage 2 bridge).

## What is fully automated vs your input
- Fully automated: spec→contracts (Stage 1), and per-contract preflight/build/validate/commit + chain
  advance (Stage 2).
- Your input: (a) paste messy input once (Stage 0); (b) the merge policy (`chain_on`), and if
  `merged`, the merge tap or CI auto-merge authorization. That's it.
