# Claude Code Mobile bootstrap readiness remediation

> Make the Claude Code cloud/mobile adapter self-healing and truthful: eliminate the wrong-workspace wiring class, stop READY being reported for artifacts that never load, reconcile the drifted MCP surface, and isolate the capability-broker gap as the one remaining infrastructure blocker.

**Repository** `Quantum-L9/Cursor-Governance` · **Branch** `claude/mobile-bootstrap-readiness-audit-aoi0mn` · **Commit** `941ab77` · **Governance SSOT** `941ab77` · **Depth** `deep` · **Estimate** 2 GMP runs: T1-T7 + T12 (adapter truth + cache rebuild), then T8-T10 (parity). T11 is operator infrastructure.

Planning artifact only — no code was changed to produce it. Execution runs through `@environment/program-execution` + `/autonomy`.

---

## The one sentence version

The Claude Code cloud adapter wired itself into `/home/user` — the parent of the checkout, which is not a git repository — and then reported `READY` for everything it had just installed somewhere Claude never reads. Twelve fixes make it self-healing and honest. Eleven are code. One is infrastructure you own.

## Why it happened

| | |
|---|---|
| The account Setup script ran once, at governance `d424f588` | At that revision `web/setup.sh:145` passed `--workspace "$(pwd)"` with no resolution, and `install.sh` had no git-repo guard |
| Anthropic snapshots the environment after the first successful Setup run | The fix that exists at HEAD `941ab77` has never executed |
| SessionStart refreshes the *governance clone* every session | It never re-runs the *installer* |

So the running environment is pinned to a six-commit-old installer, and nothing in the startup path notices. That single fact produces most of what follows.

## What to build

Ordered by leverage. Effort `S` ≈ under an hour, `M` ≈ half a day, `L` ≈ multi-day.

### 1. Self-heal installer drift at SessionStart   <sub>`T1`</sub>

Add a cloud-only installer-drift self-heal to SessionStart: when the receipt names a different workspace or an older governance revision than live, re-run install.sh bounded and fail-open, then re-read the receipt

`Insert` · effort **M** · risk **medium** · depends on none

**Where** `environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`  
**Anchor** after the CLAUDE_CODE_REMOTE governance refresh block, before emit_bootstrap_status

### 2. Allowlist `api.context7.io` (forces the cache rebuild)   <sub>`T12`</sub>

Add api.context7.io to the environment's Custom allowed-domains list; the same edit forces a setup-script cache rebuild, which is what lands the T1 installer fix

`Insert` · effort **S** · risk **low** · depends on none

**Where** `environment/agents/adapters/claude-code/web/network-policy.md`  
**Anchor** the allowlisted-hosts table

### 3. Count skills that actually load   <sub>`T2`</sub>

Replace the SSOT SKILL.md file count with a loadable-skill probe over the real discovery paths and report both numbers

`Replace` · effort **S** · risk **low** · depends on none

**Where** `environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`  
**Anchor** line 115, the 'skills available: N l9-* skills under $GOV/skills' line

### 4. Mark stale receipt statuses STALE   <sub>`T3`</sub>

Mark receipt-derived statuses STALE in the SessionStart projection when receipt.workspace differs from the session project dir, instead of printing READY verbatim

`Replace` · effort **S** · risk **low** · depends on none

**Where** `environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`  
**Anchor** lines 216-227 in the emit_bootstrap_status python block

### 5. Make `.mcp.json` a managed artifact   <sub>`T5`</sub>

Make .mcp.json a managed artifact: reconcile it from mcp.template.json when it carries the L9 managed marker, and update the committed workspace .mcp.json to the 6-server broker template

`Replace` · effort **M** · risk **high** · depends on none

**Where** `environment/agents/adapters/claude-code/install.sh`, `.mcp.json`  
**Anchor** install.sh lines 205-206 '.mcp.json already present — left as the repo committed it'

### 6. Run adapter self-validation from the installer   <sub>`T7`</sub>

Invoke validate_claude_env.py from install.sh and downgrade a receipt status on non-zero, so adapter self-validation failures surface instead of sitting unread

`Insert` · effort **S** · risk **medium** · depends on `T6`

**Where** `environment/agents/adapters/claude-code/install.sh`  
**Anchor** before the receipt write block at install.sh:250

### 7. Remove the prohibited git pre-commit hook   <sub>`T4`</sub>

Detect and remove a pre-commit-generated .git/hooks/pre-commit during cloud SessionStart, matching the prohibition the helper already documents

`Insert` · effort **S** · risk **medium** · depends on none

**Where** `environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh`  
**Anchor** in the pre-commit warm block, beside the 'Never pre-commit install' comment at lines 169-176

### 8. Fix the memory-enforcement schema   <sub>`T6`</sub>

Allow gate_shape and note on the precondition definition in the memory-enforcement schema so the contract the doctrine requires validates

`Insert` · effort **S** · risk **low** · depends on none

**Where** `environment/agents/adapters/claude-code/memory/memory-enforcement.schema.json`  
**Anchor** definitions.precondition properties, which is additionalProperties:false

### 9. Teach the MCP inventory about Claude Code   <sub>`T8`</sub>

Extend the MCP inventory scan set to the Claude Code surface (.mcp.json in workspace and $HOME/.claude.json) so it stops reporting an empty server list

`Insert` · effort **S** · risk **low** · depends on none

**Where** `ops/scripts/inventory_mcp_servers.py`  
**Anchor** lines 74-77, the scanned_configs list

### 10. Mirror slash commands into `.claude/commands`   <sub>`T9`</sub>

Add a slash-command reconciler that mirrors commands/ into <workspace>/.claude/commands, and call it from install.sh beside the skill reconciler

`Create` · effort **M** · risk **medium** · depends on none

**Where** `ops/scripts/reconcile_claude_commands.py`, `environment/agents/adapters/claude-code/install.sh`  
**Anchor** new script modelled on reconcile_claude_l9_skills.py scope_target

> **Blocked.** Gated on U1: mirroring is only correct if Claude Code tolerates the existing name/version/before_chain/auto_chain frontmatter. Probe two commands first; if discovery breaks, fall back to amending rule 02-slash-commands instead.

### 11. Regression tests for all of it   <sub>`T10`</sub>

Add regression tests: drift self-heal fires only on mismatch, loadable-skill probe counts load paths, STALE projection on workspace mismatch, stale git hook removed, .mcp.json reconcile is idempotent

`Create` · effort **M** · risk **low** · depends on `T1`, `T2`, `T3`, `T4`, `T5`

**Where** `ops/scripts/tests/test_bootstrap_diagnostic_contract.py`, `environment/agents/adapters/claude-code/tests/test_session_start_selfheal.py`  
**Anchor** extend the existing bootstrap diagnostic contract suite

### 12. Deploy the capability broker   <sub>`T11`</sub>

Deploy the capability broker and run sessions in the self-hosted ccpool_ environment it is built for, then set L9_CAPABILITY_BROKER_URL

`Replace` · effort **L** · risk **high** · depends on none

**Where** `ops/secrets/k8s/broker-deployment.yaml`, `ops/secrets/deploy/broker-kubernetes.yaml`  
**Anchor** broker-deployment.yaml:65 --audience ccpool_prod; broker_identity.py:143 ccpool_ audience guard

> **Blocked.** Infrastructure, not code. The broker is complete and coherent: broker-deployment.yaml:65,69 pins --audience ccpool_prod, capability_broker.py:47 serves --audience ccpool_<environment>, and broker_identity.py:143 refuses any audience not starting with ccpool_. It expects a self-hosted ccpool_ pool whose control plane issues the iss=ccr session assertion. This session is CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default, where no ccr issuer exists (claude.ai CCR JWKS probed 404). Nothing in the design is missing; it is undeployed and this environment is not its target. L9_BROKER_JWKS_URL is already the env knob for a self-hosted issuer.

---

## Sequencing

**Critical path** `T1` → `T2` → `T3` → `T5` → `T7` → `T10`

| Milestone | Outcome | Unlocks | Checkpoint evidence | If it fails |
|---|---|---|---|---|
| **M1** | SessionStart re-installs the adapter on receipt drift and reports load-path truth | the wrong-workspace class self-heals without an environment rebuild | a session started with a mismatched receipt ends with receipt.workspace == CLAUDE_PROJECT_DIR and SessionStart prints a loadable-skill count of 51 | revert T1 and keep the STALE projection from T3 as the honest fallback |
| **M2** | MCP surface reconciled and adapter self-validation wired into install | Context7/Semgrep/GitGuardian/Playwright register the moment a broker exists | validate_claude_env.py exits 0 from install.sh and .mcp.json lists 6 servers | stop; do not proceed to command reconciliation with a failing validator |
| **M3** | Stale-state cleanup and Claude-surface tooling parity landed with tests green | make pr-check and publication | pytest suites PASS and make pr-check PASS on a clean worktree | block release authorization; no push |
| **M4** | Capability broker deployed and broker URL set | all 8 non-memory brokered capabilities move DEGRADED to ONLINE | bootstrap_agent_env.sh --check exits 0 with all 8 non-memory capabilities ENABLED | keep the DEGRADED posture; never substitute a pasted credential |

## Proving it worked

| | Command | Passes when |
|---|---|---|
| `V1` | `python3 environment/agents/adapters/claude-code/validate_claude_env.py` | RESULT: PASS and exit 0 |
| `V2` | `python3 -m pytest tests/ops/scripts environment/agents/adapters/claude-code/tests -q` | all PASS |
| `V3` | `bash environment/agents/adapters/claude-code/install.sh --check --governance $HOME/.cursor-governance --workspace /home/user/Cursor-Governance` | settings/skills/rules/mcp READY; capabilities/memory DEGRADED with broker reason only |
| `V4` | `bash ops/secrets/bootstrap_agent_env.sh --check --surface claude-code` | exit 1 while L9_CAPABILITY_BROKER_URL is unset — proves T1-T10 made the environment truthful without fabricating capability health |
| `V5` | `make pr-check` | PASS on a clean worktree |

`V4` is the honesty check. It must still **fail** — the capability plane stays `DEGRADED` while the broker is unset, and no adapter fix may paper over that.

## Success criteria

- A session whose bootstrap receipt names a workspace other than CLAUDE_PROJECT_DIR re-runs install.sh and ends with receipt.workspace == CLAUDE_PROJECT_DIR
- SessionStart reports a loadable-skill count read from the actual load paths, and that count is 51 in this workspace
- When receipt.workspace != CLAUDE_PROJECT_DIR, SessionStart prints settings/skills/rules as STALE(<value>) instead of the bare value
- validate_claude_env.py exits 0 and is invoked by install.sh
- Workspace .mcp.json declares the same server set as mcp.template.json (6 servers)
- No .git/hooks/pre-commit generated by pre-commit survives a cloud SessionStart
- inventory_mcp_servers.py lists the workspace .mcp.json servers instead of reporting none
- pytest tests/ops/scripts and environment/agents/adapters/claude-code/tests PASS
- make pr-check PASS

## Scope

**In**

- `environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`
- `environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh`
- `environment/agents/adapters/claude-code/install.sh`
- `environment/agents/adapters/claude-code/memory/memory-enforcement.schema.json`
- `ops/scripts/inventory_mcp_servers.py`
- `ops/scripts/reconcile_claude_commands.py (new)`
- `workspace .mcp.json`
- `tests for the above`
- `ops/secrets/k8s/broker-deployment.yaml + deploy/broker-kubernetes.yaml`

**Out**

- Changing the broker's identity model — it is complete as designed for a ccpool_ self-hosted pool
- Introducing any second authentication path beside the existing ccr session assertion
- Editing mcp.template.json's Authorization header, which is the existing design's contract
- Pasting any Infisical, Sonar, Semgrep or Graphiti credential onto this surface
- Memory readiness, memory hydration and memory MCP behaviour
- Re-pasting the account Setup script as the remediation mechanism
- Installing the uploaded l9-plan v2.0.0 over SSOT v4.0.0
- Any git push, PR open or merge from plan mode

## Risks

| Risk | Mitigation |
|---|---|
| T1 re-runs install.sh concurrently with make pr and trips the repo-write lock, producing the 'files were modified by this hook' misattribution documented in learning/failures/precommit-hook-attribution.md | acquire ops/scripts/lib/repo_write_lock.sh via run_reconciler semantics, wait briefly, then skip fail-soft exactly as the other sessionStart reconcilers already do |
| T1 adds seconds to every drifted session start and the SessionStart hook has a 30s timeout in .claude/settings.json | run install.sh --quiet, bound it with a budget like session_deps_cloud.sh does, and self-detach past the budget rather than blocking the hook |
| T5 overwrites an intentionally customized consumer .mcp.json | reconcile only when the file carries an _l9_managed marker or is byte-identical to a known prior template; otherwise report drift and leave it |
| T9 mirrors 54 commands whose frontmatter Claude Code may reject or mis-parse | resolve U1 with a two-command spike before mirroring all 54; if frontmatter is incompatible, fall back to amending rule 02-slash-commands to name the governance path instead |
| T4 removes a hook a local developer installed deliberately | gate removal on CLAUDE_CODE_REMOTE=true and on the pre-commit generation marker in the file body |
| Landing T1-T10 makes the environment look healthy while every brokered capability is still DEGRADED | T3 and T7 make status strictly more honest, not less; C4 keeps the broker gap visible as its own checkpoint and T11 stays open |
| T12's allowlist edit forces an immediate cache rebuild, so an unrelated defect in the setup script would surface as sessions failing to start | land T16 before T12 so no setup-script path can exit non-zero |
| T12's allowed-hosts edit forces an immediate cache rebuild, so any setup-script path that exits non-zero would surface as sessions failing to start (the platform contract treats a non-zero setup script as a failed session start; setup.bootstrap.sh exits 1 on governance clone failure and on missing web/setup.sh) | verify the governance clone and web/setup.sh resolve before editing allowed hosts; this is a deliberate fail-closed choice in the existing design and is recorded here as a risk, not changed |

## Open questions

| | Question | What it decides | How to close |
|---|---|---|---|
| `U1` | Does Claude Code load commands/*.md with name/version/before_chain/auto_chain frontmatter, or does non-standard frontmatter break command discovery? | Decides whether T9 mirrors all 54 commands into .claude/commands or falls back to amending rule 02-slash-commands. Gates T9 only. | `probe` |
| `U3` | When will sessions run in the self-hosted ccpool_ environment the broker targets, rather than cloud_default? | Gates T11 and every brokered capability. Now a scheduling question for the operator, not a technical unknown: the design is complete, the environment is simply not the one it serves. | `ask` |
| `U4` | Does the full pre-commit catalog pass via the stale .git/hooks/pre-commit, or does sync-generated-artifacts fail git commit on this surface? | Sets T4 priority: live git-commit blocker versus hygiene only. | `probe` |

None of these block `T1`–`T10` or `T12`. U2 is resolved by the platform contract: the environment cache rebuilds on a setup-script or allowed-hosts change and at ~7 days, so T12 and the T1 rollout are one lever and B-01 self-heals passively within a week. U3 is no longer 'is there an issuer' but 'when do sessions run in the ccpool_ pool the broker already targets' — an operator scheduling question. T11 stays infrastructure-blocked with a precise cause. T1-T10 and T12 are unblocked and require no architectural change.

## Stress test

**Questions that would break this plan**

- If SessionStart re-runs install.sh on every drifted session, does it add unacceptable latency or race the repo-write lock held by a concurrent make pr?
- Could the self-heal loop permanently if install.sh writes a receipt that still disagrees with CLAUDE_PROJECT_DIR, for example when the session runs outside a git repo?
- Does overwriting .mcp.json from the template destroy a deliberate consumer-repo customization in a downstream repo that is not Cursor-Governance?
- Is a loadable-skill count of 51 actually sufficient, given Claude Code enumerates skills at session start so a mid-session install is invisible until the next session?
- Do the 54 command files with name/version/before_chain/auto_chain frontmatter actually load as Claude Code commands, or does the extra frontmatter break discovery?
- Does removing .git/hooks/pre-commit break a developer who deliberately installed it on a local checkout rather than a cloud sandbox?
- If the broker never ships, does any of T1-T10 create a false impression that capabilities are closer to ONLINE than they are?

**This plan is wrong if**

- Anthropic begins re-running the account Setup script per session, which would make T1 redundant but not harmful
- Claude Code adds mid-session skill hot-reload, which would remove the one-session lag noted in C1
- A downstream consumer repo pins its own .mcp.json intentionally, which would make the T5 managed marker mandatory rather than optional

**Blast radius** session_start_claude_governance.sh and session_deps_cloud.sh run on every cloud session across every consumer repository that commits the adapter, so a defect here degrades or blocks session startup fleet-wide rather than in one repo. install.sh additionally runs on CLI and Desktop. .mcp.json reconciliation touches the MCP surface every session start. The fail-open contract on both hooks is the containment boundary and must be preserved.

**Rollback** Every change is confined to four adapter files plus two ops scripts and a new reconciler; git revert of the feature branch restores d424f588-equivalent behaviour. The self-heal is gated on CLAUDE_CODE_REMOTE=true and on an explicit drift comparison, so setting L9_CLAUDE_SELFHEAL=0 disables it without a code change. .mcp.json changes are recoverable from mcp.template.json. No infrastructure, credential or remote state is mutated, so there is nothing to roll back outside the repository.

## Execution boundary

**May modify**

- `environment/agents/adapters/claude-code/hooks/`
- `environment/agents/adapters/claude-code/install.sh`
- `environment/agents/adapters/claude-code/memory/memory-enforcement.schema.json`
- `environment/agents/adapters/claude-code/web/network-policy.md`
- `ops/scripts/inventory_mcp_servers.py`
- `ops/scripts/reconcile_claude_commands.py`
- `tests/ops/scripts/`
- `environment/agents/adapters/claude-code/tests/`
- `.mcp.json`

**Must not modify**

- `ops/secrets/capabilities.yaml`
- `ops/secrets/infisical-cursor-governance.yaml`
- `ops/autonomy/local_execution_gate.py`
- `ops/autonomy/merge_gate.py`
- `CANONICAL_LAW.md`
- `environment/agents/adapters/claude-code/web/setup.bootstrap.sh`
- `ops/secrets/broker_identity.py`
- `ops/secrets/capability_broker.py`
- `environment/agents/adapters/claude-code/mcp.template.json`

**Contracts preserved throughout**

- SessionStart hooks are fail-open and always exit 0
- No raw secret is ever hydrated onto a model-controlled surface
- make pr remains the only route to GitHub
- install.sh classifies BLOCKED/DEGRADED/READY and never reports unconditional readiness
- memory is never a gate on repository mutation
- capability failure semantics stay degrade, never a silent pass

**Run before declaring done**

```bash
python3 environment/agents/adapters/claude-code/validate_claude_env.py
python3 -m pytest tests/ops/scripts environment/agents/adapters/claude-code/tests -q
make pr-check
```

---

<sub>Generated from `.cursor/plans/mobile_bootstrap_fixes.plan.json` (schema 1.0.0, validated PASS against l9-plan v4.0.0). Regenerate rather than edit by hand.</sub>
