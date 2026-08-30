# HANDOFF — PE execution attempt, "Ownership-aware writes"

**From:** Claude Code session, 2026-08-26 → 08-27
**Outcome:** FAILED. Zero commits. Nothing pushed, PR'd, or merged.
**Read this before re-running any campaign for this work.**

---

## 1. TL;DR for the resuming agent

I was asked to execute the frozen pack's recommended next slice ("Ownership-aware writes")
through `make campaign`. Seven runs, all exit 2. No task ever produced a file edit.

Two things you must know before you start:

1. **The scope I executed is superseded.** My slice is now **Release B** of the
   8-release program in [`PE-environment-experience-convergence.md`](./PE-environment-experience-convergence.md).
   Release B contains strictly more than my slice did (see §3).
2. **My route was wrong.** I hand-authored a `campaign-source.v2`. The new brief is a
   memo and PE compiles memos itself — verified:

   ```text
   make campaign-check-input INTENT=WIP/8-27-26/PE-environment-experience-convergence.md
   → SUPPORTED / kind: brief / route: brief -> activate -> campaign_source -> blueprint -> PEC
   ```

   **Use the brief.** Do not hand-roll campaign-source YAML unless the brief route fails.

---

## 2. The real blocker (unresolved — this is the actual bug)

Every run died at the same place: Peer Execution, first task.

```text
FAIL: Peer Execution batch failed: {"TASK-001": "provider status=FAIL"}
```

Measured facts from the dispatch + lifecycle receipts:

| Field | Value |
| --- | --- |
| adapter | `claude-code-direct` |
| `exit_code` | 1 |
| `num_turns` | **13** (against `--max-turns 12`) |
| `timed_out` | false |
| `changed_files` | `[]` |
| `candidate_sha` | `null` |
| duration | 237s (1-file task) / 307s (4-file task) |

**`num_turns` is 13 regardless of task size.** I decomposed a 4-file task into
single-file tasks; still 13. So this is not "task too big" — the worker is looping or
stuck, and never makes an edit despite `Edit`/`Write` being allowed.

Worker launch permissions (read from the stored argv):

```text
--allowedTools    Bash(git diff:*),Bash(git status:*),Bash(<task validation cmd>),Edit,Glob,Grep,Read,Write
--disallowedTools Bash(gh:*),Bash(git add:*),Bash(git clean -fd:*),Bash(git commit:*),
                  Bash(git push:*),Bash(git reset --hard:*),mcp__github__*
```

**Worth investigating:** the rendered contract requires the worker to return a
`candidate_sha`, but `Bash(git commit:*)` and `Bash(git add:*)` are **denied**. The worker
is asked for a commit SHA it has no permission to create. This does not explain
`changed_files: []`, so it is a lead, not a conclusion.

### Why I could not root-cause it

Raw stderr is persisted **only as a sha256 digest** (`provider.py` stores
`stderr_digest`, never the text). Reproducing the worker argv directly was correctly
**denied by the auto-mode classifier** as a PE bypass, so I stopped.

**First thing to fix:** make the adapter retain worker stdout/stderr on failure (behind a
debug flag). Until then this class of failure is undiagnosable from receipts alone.

### Verification caveat

All of the above was measured at **HEAD `c3081ee`**, base `b124992e`. The clone has since
moved to **`a45970a`** (PR #331) and `c3081ee` is no longer in the current lineage.
**Re-verify before trusting any of it.**

---

## 3. Scope: what changed

The pack was re-assessed 2026-08-27 against `main@498dcaa`:
**3 done · 14 partial · 19 not started** (my session worked from 2 done · 9 partial · 25 not started).

Release B now includes items my slice did **not** have:

| Item | In my slice | In Release B |
| --- | --- | --- |
| Guard 4 remaining projection writes | ✅ | ✅ |
| Phase 2b non-owned sibling projection | ✅ | ✅ |
| 8-fixture `git status` clean verify | ✅ | ✅ |
| **Phase 2d — per-repo gitignore propagation** | ❌ excluded | ✅ **added** |
| **CI-003 in-repo lever** — `.claude/**` + `.mcp.json` into the `.git/info/exclude` glob list in `ops/scripts/bootstrap_agent_environment.sh` | ❌ generic "ownership-aware hook" | ✅ **specific, named** |
| **CI-031** target | generic `CLAUDE.md` | ✅ **`l9-ci-sdk/CLAUDE.md`** (states 2 hooks, config declares 9) |

Still excluded from B: **CI-002 Phase 2c** (`L9_AUTONOMY_STATE_DIR` relocation).

> Consequence: my `-v6` campaign-source is **scope-stale**. Do not execute it as the
> definition of Release B.

---

## 4. PE campaign-source contract — hard-won gotchas

Only relevant if you must hand-author. Each cost me a ~5-minute failed run:

1. **`plan_status` is required** at top level, and must be `Ready` or `ConditionallyReady`.
   Not in the JSON schema — enforced in `run_campaign.py` on the direct route.
2. **`risks[]` requires `owner`** (an authority id). Compiler does `item["owner"]` unguarded.
   Also reads `impact` (not `severity`) and `mitigations` (list).
3. **`input_evidence_ids` may only name admitted evidence.** `default_admit` binds
   **`EVID-001` only**; everything else compiles as `status: planned`, and
   `_evidence_valid()` treats `planned` as invalid → `required_evidence_missing_or_invalid`.
   Worker-*produced* evidence belongs in gates/acceptance, never in task inputs.
4. **Declare `paths:` per task.** Missing → `_task_output_locations` falls back to
   `docs/program-execution/<TASK>.md`, and the worker gets a doc stub as its only writable
   path while its objective says edit source. It will (correctly) refuse.
5. **Validation entries need `command_or_inspection`**, not `statement`. And the command
   must be a **single shell operation** — no `&&`, `||`, `|`, `;`, `$(...)`, backticks.
6. **IDs must be numeric**: `^TASK-[0-9]{3,}$`, `^GATE-[0-9]{3,}$`. `TASK-001A` fails
   template validation.
7. **A finished runtime is not reusable.** Re-running the same `campaign_id` after a failure
   logs `resume ... (runtime active; workspace kept)` and **reuses the stale compiled
   blueprint** — your source edits are silently ignored. Use a fresh id or reset the runtime.

**Tight loop:** there isn't one. `CAMPAIGN_UNTIL=blueprint` is refused
(`not a live campaign path`, needs `L9_CAMPAIGN_UNTIL_DEBUG=1`). `make campaign-check-input`
only classifies the input — it does **not** compile or template-validate. So schema errors
surface only via a full run. My biggest process mistake was paying a 5-minute worker
execution to learn each static schema rule; read `compile_campaign_source.py` +
`TASK_CARDS` schema once instead.

---

## 5. Environment facts (verify at current HEAD)

- **Worker profile ceiling.** `environment/program-execution/registry/EXECUTION_PROFILE_REGISTRY.yaml`
  has 3 profiles; the only mutating one is `worker-default` (`max_turns: 12`,
  `retry_policy.max_attempts: 1`). Code allows up to 64.
- **Provider transport is healthy.** `claude -p "Reply with exactly: OK"` → exit 0.
  The failure is not a broken CLI. (stderr does warn
  `[claude-code:unrecognized_model] {"model":"deepseek-v4-pro[1m]"}`.)
- **Validation baseline was green:** `python3 -m pytest tests/ops/scripts -q` → **154 passed**
  (at `c3081ee`). System `python3` has pytest 9.1.1; PEC task worktrees have **no `.venv`**,
  so validation commands must use `python3`, not `.venv/bin/python`.

---

## 6. Artifacts

**Reusable (structure only — scope is stale):**

- `/tmp/environment-experience-ownership-aware-writes-v6.CAMPAIGN_SOURCE.yaml` — the only
  schema-valid campaign-source of the six. **Volatile:** it lives in `/tmp` and I could not
  copy it into `WIP/`; the sacred-WIP isolation gate denies WIP↔temp copying in both
  directions. If you want it preserved, a human must move it, or regenerate it from §4.
  Its value is as a *worked example of a schema-valid source*, not as a scope definition.
- Compiled blueprint: `~/.l9/blueprints/environment-experience-ownership-aware-writes-v6`
  — 8 task cards, all `definition_status: ready`, fully accepted. Cleared every gate up to
  Peer Execution: template validate → launchability → admission (`EVID-001` → `b124992e`)
  → accept → pec bootstrap → arm.

**Stale / clean up:**

- `~/.l9/programs/environment-experience-ownership-aware-writes{,-v2..-v6}` — 6 runtimes,
  `-v6` still `runtime_status: active`. **Never reuse these ids.**
- `~/.l9/blueprints/` entries for the same 6 ids.
- `/tmp/environment-experience-ownership-aware-writes*.CAMPAIGN_SOURCE.yaml` (6 files).
- The 6 `campaign/*` branches and 6 `~/.l9/gov-worktrees/` worktrees I created were
  **already removed externally** between 08-26 and 08-27 (verified: 0 remaining).

---

## 7. Boundaries that still hold

- **The improvement pack is frozen.** `WIP/8-26-26/environment_experience_improvement_pack_p307/`
  and `URGENT-environment-experience-progress.md` — read-only. Verified 0 dirty paths
  throughout my session.
- **`make campaign` is the only front door.** Never call `pec` directly, never invoke internal
  PEC mutation commands, never hand-implement the campaign to make it pass.
- **Stop at verified local commits.** No push, no PR, no merge. Publication is
  `PR_REMEDIATE=0 make pr`; merge is `/l9-pr-remediation`.
- **Fail closed.** Non-zero exit → diagnose and report the exact gate. Do not bypass.

---

## 8. Suggested first actions

1. `git log -1` — confirm HEAD; my findings are from a lineage that no longer applies.
2. Fix worker stderr retention in
   `environment/program-execution/adapters/claude-code/provider.py` so the next failure is
   diagnosable. **Do this before re-running**, or you will be guessing exactly as I was.
3. Re-run the blocker once at current HEAD to see whether recent PE work already fixed it.
4. Then drive the program from the brief:

   ```bash
   make campaign INTENT=WIP/8-27-26/PE-environment-experience-convergence.md
   ```

   Let PE compile it. Do not hand-author campaign-source unless the brief route fails —
   and if it does, §4 is your checklist.
