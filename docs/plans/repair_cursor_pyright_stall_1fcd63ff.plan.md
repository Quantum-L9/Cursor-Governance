---
name: Repair Cursor Pyright stall on ssot_checkout
overview: "Stop the files-to-analyze spinner by not creating .cursor-commands on ssot_checkout and pinning cursorpyright include. Not Biome. Build on this checkout."
todos:
  - id: todo-01-stop-ssot-checkout-link
    content: "setup_workspace_symlinks.sh: source workspace_kind.sh; if classify_workspace_kind is ssot or ssot_checkout, remove .cursor-commands and do not create it. Consumers still get the link."
    status: pending
    phase: execute
    depends_on: []
  - id: todo-02-prove-kind-gate
    content: "Add ssot_checkout fixture to kind/symlink tests so creating .cursor-commands on an identity-tree checkout fails the test."
    status: pending
    phase: execute
    depends_on: [todo-01-stop-ssot-checkout-link]
  - id: todo-03-pin-pyright-include
    content: "settings.python.json: include matches [tool.pyright]; autoSearchPaths false; shouldImportPylanceSettings never. Do not edit biome.json."
    status: pending
    phase: execute
    depends_on: []
  - id: todo-04-merge-ide-profile
    content: "Run install_ide_profile.sh so .vscode/settings.json gets the new keys. biome.json unchanged vs HEAD."
    status: pending
    phase: execute
    depends_on: [todo-03-pin-pyright-include]
  - id: todo-05-prove-clear
    content: "Kind tests + make pr-check. Restart Pyright. Output must not enumerate .cursor-commands. Spinner gone with markdown-only tabs."
    status: pending
    phase: validate
    depends_on: [todo-02-prove-kind-gate, todo-04-merge-ide-profile]
isProject: false
kind: simple
execute_via: cursor-build
kernel_pass:
  bound_path: repair_cursor_pyright_stall_1fcd63ff.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T21:40:00Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Named the exact owner: source workspace_kind.sh and call classify_workspace_kind; do not duplicate identity-file checks in setup_workspace_symlinks.sh."
      - "Named the existing test anchors to extend (ssot_checkout optional-link in test_workspace_kind.sh; T9 self-alias in test_workspace_rules_overlay.sh)."
      - "Locked write_deny on session_start_bootstrap.sh so the repair stays in the symlink script."
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-08-29T21:40:30Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "AGENTS.md §11 already says ssot_checkout must not require consumer .cursor-commands; this plan implements that sentence rather than inventing a new wiring rule."
      - "Plugin root ~/.cursor/plugins/local/l9-governance stays the discovery path; removing .cursor-commands on a gov checkout does not create a second commands tree."
      - "pyproject.toml [tool.pyright] remains the analysis include SSOT; settings.python.json copies that list and does not rewrite the additive_only root file."
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T21:41:00Z
    body_sha256: "aa25857885d5c83401ae235105eee873a1ca1a2469f87e0c92729e8b360ad6c7"
    deltas:
      - "C1 remains exclusive: consumer fixture must still receive .cursor-commands before settings.python.json is edited."
      - "U1 stays accept_bounded; missing PEC tab is not a plugin repair."
      - "No live make campaign; execute_via is cursor-build on this checkout."
---

# PLAN: Repair Cursor Pyright stall on ssot_checkout

**kind:** `simple` · **execute_via:** `cursor-build` · **skill:** `l9-plan-simple`
**plan_id:** `plan.ide.repair-cursor-pyright-stall.v1` · **schema_version:** `1.0.0` · **status:** `executable`

Machine SSOT: [`docs/plans/PLAN_DOCUMENT.repair-cursor-pyright-stall.v1.json`](PLAN_DOCUMENT.repair-cursor-pyright-stall.v1.json) (`validate_plan_document.py` PASS).

## Execute via Cursor Build

Press **Build**. Work in the **current checkout**.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.
- Pathspecs only. This checkout is dirty with untracked `WIP/`. Do not `git add -A`.

## Architect framing

| Field | Value |
|---|---|
| planning_ssot | Diagnose First audit 2026-08-29: emitter is `anysphere.cursorpyright` 1.0.12, not `biomejs.biome` |
| plan_class | `bounded_execution_contract` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | The 11:27 spinner matches the minute `.cursor-commands` was created on this second clone, pointing at `$HOME/.cursor-governance`. `[tool.pyright]` already documents that hang. Align the setup script with AGENTS.md §11 (`ssot_checkout` does not need consumer links). Leave Biome alone. |

## Immutable baseline

| Field | Value |
|---|---|
| captured_at | 2026-08-29T21:36:00Z |
| repository | Quantum-L9/Cursor-Governance |
| workspace | `/Users/ib-mac/Cursor-Governance` (current checkout) |
| workspace_kind | `ssot_checkout` (realpath ≠ `$HOME/.cursor-governance`; identity files present) |
| branch | `main` |
| commit_sha | `f9c3a60e8230105083096d844cdd0557440c094c` |
| dirty | `true` (untracked `WIP/8-16-26-random/`, `WIP/8-26-26-Claude Environment/`, `WIP/8-29-26/OIDC/`, `WIP/8-29-26/PE-Template.md` — out of envelope) |
| trigger_artifact | gitignored `.cursor-commands` → `$HOME/.cursor-governance` created 2026-08-29 11:27:37 |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` if `may_modify` paths changed under another agent |

## Objective

The status-bar and notification text `{count} files to analyze` is Cursor Pyright (`filesToAnalyzeCount` in `anysphere.cursorpyright-1.0.12`). Biome 3.7.1 has no such string and no LSP process. This checkout is a second clone. At 11:27 sessionStart created `.cursor-commands` → `$HOME/.cursor-governance`. Pyright activates on `pyproject.toml` and can enumerate that second full tree. `setup_workspace_symlinks.sh` already refuses the link on live SSOT; it still creates it on `ssot_checkout`. Workspace settings exclude `.cursor-commands` but do not set `include`; `autoSearchPaths` defaults true.

**It is:** stop the `ssot_checkout` link; pin `cursorpyright.analysis.include` to the existing `[tool.pyright]` roots; merge the IDE profile; prove Pyright no longer walks the symlink.

**It is not:** a Biome repair, a user-settings edit, a `pyproject.toml` rewrite, restoring `WIP/8-29-26/PEC/PEC-repair-pipeline.md`, or a quota/Cline/GitLens fix.

### Success properties

| id | property | evidence_type | proof | blocking |
|---|---|---|---|---|
| SP-01 | ssot_checkout does not get `.cursor-commands` | `runtime_behavior` | new kind/symlink fixture PASS; this checkout's `.cursor-commands` absent after setup rerun | true |
| SP-02 | consumer still gets `.cursor-commands` | `runtime_behavior` | existing consumer fixture in `test_workspace_rules_overlay.sh` still PASSes | true |
| SP-03 | IDE profile include matches `[tool.pyright]` | `structural` | `settings.python.json` include is `conftest.py`, `ops`, `environment`, `skills`, `tools`, `workflows`; `autoSearchPaths` false; `shouldImportPylanceSettings` never | true |
| SP-04 | Biome untouched | `repository_state` | `git diff --exit-code HEAD -- biome.json` | true |
| SP-05 | Pyright no longer walks the second tree | `runtime_behavior` | after Restart Server, Output `Cursor - Pyright` has no `.cursor-commands` or `$HOME/.cursor-governance` workspace-source paths; spinner gone with markdown-only tabs | true |
| SP-06 | PR gate | `quality_gate` | `make pr-check` PASS; catalog is `.pre-commit-config.yaml` | true |

## Capability preflight

| id | capability | command_or_action | pass_criteria | blocking |
|---|---|---|---|---|
| P0 | workspace identity | `realpath` workspace vs `$HOME/.cursor-governance`; `classify_workspace_kind` | `ssot_checkout`; symlink target is SSOT | true |
| P1 | emitter | `rg -F 'files to analyze'` on cursorpyright vs biome `main.js` | hit only in cursorpyright | true |
| P2 | plan depth | `route_plan.py --risk medium --evidence sufficient --json` | `depth=standard` `omit_gates=[]` | true |
| P3 | PLAN_DOCUMENT | `validate_plan_document.py docs/plans/PLAN_DOCUMENT.repair-cursor-pyright-stall.v1.json` | PASS | true |

## Execution envelope

**write_allow:** `ops/scripts/setup_workspace_symlinks.sh`, `ops/scripts/tests/test_workspace_kind.sh`, `ops/scripts/tests/test_workspace_rules_overlay.sh`, `environment/ide/settings.python.json`, `.vscode/settings.json`.

**write_deny:** `biome.json`, `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile`, `pyproject.toml`, `ops/hooks/session_start_bootstrap.sh`, `WIP/**`, user `settings.json`, other plans.

**commands allow:** kind/symlink test scripts, `install_ide_profile.sh`, `make pr-check`, scoped `git add` / `git commit` of this envelope, Cursor command `Cursor Pyright: Restart Server`.

**commands deny:** `make campaign`, `git add -A`, force-push, merge, uninstalling `biomejs.biome` or `anysphere.cursorpyright`.

**network:** `none`. **secrets:** `none`. **autonomous_merge:** `false`.

## Side effects and idempotency

| todo_id | side_effects | idempotency | irreversible |
|---|---|---|---|
| todo-01-stop-ssot-checkout-link | filesystem_mutation; next sessionStart will not recreate `.cursor-commands` on this kind | safe_with_dedupe | false |
| todo-02-prove-kind-gate | filesystem_mutation (test only) | safe_with_dedupe | false |
| todo-03-pin-pyright-include | filesystem_mutation | safe_with_dedupe | false |
| todo-04-merge-ide-profile | filesystem_mutation of untracked/managed `.vscode/settings.json` | safe_with_dedupe | false |
| todo-05-prove-clear | filesystem_read; Pyright restart | safe_to_repeat | false |

## Architecture impact

Wiring + IDE profile only. Owner: `ops/scripts/setup_workspace_symlinks.sh` for the link; `environment/ide/settings.python.json` for Pyright keys (merged by `ops/scripts/adapters/cursor.sh`). Plugin discovery stays `~/.cursor/plugins/local/l9-governance`. Formatter exclusivity unchanged: Biome JS/TS/JSON, Ruff Python, cursorpyright remains the Python language server.

Prohibited: a second analysis SSOT, disabling Biome, rewriting `[tool.pyright]` (additive_only root file; exclude already lists `.cursor-commands`).

## Rollback

Revert the `may_modify` pathspec set. Re-run `install_ide_profile.sh` if `.vscode/settings.json` was merged. Recreate `.cursor-commands` on this checkout only if a consumer workflow needs it (gitignored).

## Complexity and uncertainty

Standard depth. One bounded unknown (U1): full path on the second `Unable to open` toast. Accept: almost certainly the already-missing `WIP/8-29-26/PEC/PEC-repair-pipeline.md` editor restore. Tab restore is out of envelope.

## Execution DAG

```text
todo-01-stop-ssot-checkout-link ─► todo-02-prove-kind-gate ─┐
todo-03-pin-pyright-include ─► todo-04-merge-ide-profile ──┴─► todo-05-prove-clear
```

Checkpoint C1 after todo-01: if a consumer fixture loses `.cursor-commands`, **stop** — revert the setup script. Do not edit `settings.python.json` until the kind branch is proven.

Checkpoint C2 after todo-05: if Pyright Output still lists `.cursor-commands` paths, **stop and replan**. Do not disable Biome or cursorpyright to hide the spinner.

## Locked contracts (Build)

1. **Pyright, not Biome.** `biome.json` stays byte-identical to HEAD. Do not uninstall or reconfigure `biomejs.biome`.
2. **Kind split.** Source `ops/scripts/lib/workspace_kind.sh` and call `classify_workspace_kind`. `ssot` and `ssot_checkout`: no `.cursor-commands`. `consumer`: still linked to `$GLOBAL_COMMANDS`. Do not change plugin or `.cursor/plans` wiring in the same edit. Do not edit `session_start_bootstrap.sh`.
3. **Include list is a copy, not a new contract.** Roots are exactly `[tool.pyright] include` already on disk: `conftest.py`, `ops`, `environment`, `skills`, `tools`, `workflows`. Keep the existing exclude list.
4. **No user-settings edit.** Machine `User/settings.json` is out of envelope (and must not be opened in chat).
5. **Pathspecs only.** Do not stage untracked `WIP/`.

## Property evidence matrix

| After | Evidence |
|---|---|
| todo-01 | `classify_workspace_kind` on a fixture identity tree; `.cursor-commands` absent |
| todo-02 | `bash ops/scripts/tests/test_workspace_kind.sh` and `test_workspace_rules_overlay.sh` PASS |
| todo-03 | `rg -n autoSearchPaths environment/ide/settings.python.json` matches `false` |
| todo-04 | `.vscode/settings.json` has `cursorpyright.analysis.include`; `git diff --exit-code HEAD -- biome.json` |
| todo-05 | `make pr-check` PASS; Pyright Output has no `.cursor-commands` paths |

## Stress and disconfirm

- If the spinner remains with markdown-only tabs after the link is gone, the emitter hypothesis is wrong — re-`rg` extensions before touching Biome.
- If `classify_workspace_kind` labels a consumer as `ssot_checkout`, slash discovery via `.cursor-commands` breaks — C1 consumer fixture is the gate.
- If vscode `include` is ignored because `[tool.pyright]` wins, the settings change is still belt-and-suspenders; the setup-script change is the primary fix.
- Blast radius: sessionStart on governance worktrees and second clones only.
- Rollback: revert the envelope pathspecs; re-run the IDE profile installer.

## Out of scope

`biome.json` / Biome extension. User `settings.json`. `pyproject.toml` rewrite. Restoring or deleting the missing PEC markdown tab. Cursor Models 97% use / `Stats: 45798/32533`. Cline. GitLens. `make campaign` / Program Lock / PE overlay. Disabling `anysphere.cursorpyright` or Ruff.

## Convergence

| Field | Value |
|---|---|
| status | `partial` (plan ready; Build not run) |
| remaining_unknown_ids | `U1` |
| next_skill | Build on this checkout |
| execute_via | Cursor Build on the current checkout |
| stop_reason | Do not implement until Build. C1 before settings.python.json if the kind branch is unproven. |

```yaml
evidence_quality: high
decision_risk: reversible
action: proceed_with_validation
calibration_status: none
stated_probability: null
```

## Validation (Build)

```bash
bash ops/scripts/tests/test_workspace_kind.sh
bash ops/scripts/tests/test_workspace_rules_overlay.sh
git diff --exit-code HEAD -- biome.json
PR_BASE=origin/main make pr-check
```

Falsifiable read-backs:

- `test ! -e .cursor-commands` on this checkout after setup rerun
- `rg -n 'classify_workspace_kind' ops/scripts/setup_workspace_symlinks.sh` → match
- `rg -n '"cursorpyright.analysis.autoSearchPaths": false' environment/ide/settings.python.json` → match
- `rg -n '"cursorpyright.analysis.include"' environment/ide/settings.python.json .vscode/settings.json` → match
- `git diff --name-only HEAD -- biome.json` → empty
