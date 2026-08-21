---
name: Retire memory-bank
overview: Version-bound execution contract to retire memory-bank/ via Graphiti CLI, extinguish regenerators, relocate .l9/pr handoffs — with immutable baseline lock, capability probes, side-effect/idempotency semantics, property evidence, typed rollback, and a tight execution envelope. Broader l9-plan schema evolution is a follow-on milestone, not this change set.
todos:
  - id: baseline-lock
    content: "P0: Record/verify immutable baseline (commit, dirty, law/AGENTS/manifest/lock hashes); STOP on drift before mutate"
    status: completed
  - id: capability-preflight
    content: "P0: Runtime census — Graphiti health/resolve/search, venv+yaml, wiring script, .l9 writable; property-not-command pass"
    status: completed
  - id: classify-receipt
    content: Write classify receipt path→delete|migrate|skip + sha256; refuse migrate-class deletes until Gate B
    status: completed
  - id: delete-noise
    content: Delete sonar-pr98-*.json + empty stubs only (idempotent filesystem_mutation)
    status: completed
  - id: mine-cli-write
    content: "Gate B: ≤5 CLI writes + search proof; redacted atoms; episode receipt with digests"
    status: completed
  - id: relocate-handoff
    content: "R1: open_pr_after_gate → .l9/pr/; AGENTS+rules/98; envelope-limited paths"
    status: completed
  - id: stop-scaffold
    content: "R2–R5/R12: remove scaffold, flip wiring, no-op inject reader, drop Claude excerpt, RETIRE template consumers"
    status: completed
  - id: docs-alignment
    content: "R6–R11: MEMORY_BANK_POLICY RETIRED; AGENTS append-only; pipeline/DEPLOY/brief/bounded-autonomy/end-session; sync llm-rules"
    status: completed
  - id: delete-trees
    content: "Gate C: rm both memory-bank trees only after A+B; prove setup does not recreate"
    status: completed
  - id: validate-converge
    content: Property evidence matrix + make pr-check + rg writers; typed rollback if fail; YNP next=
    status: completed
isProject: false
---

# Retire `memory-bank/` — version-bound execution contract

## Architect framing (applied, not redesign)

`l9-plan` stays the planning SSOT. This plan is evolved from a structured retirement checklist into a **version-bound execution contract** for one mission (memory-bank retirement). Broader schema work (ratcheting mypy, org-wide asset registry, full envelope enforcement runtime) is **follow-on** — see §Follow-on milestone.

```text
PLAN_EXECUTABLE =
  schema_intent_clear
  AND baseline_matches
  AND capability_probes_pass
  AND invariants_match
  AND execution_envelope_respected
```

Not merely “markdown looks complete.”

## Immutable baseline (P0 — lock before mutate)

Captured at plan revision (re-verify at execution start; **STOP / re-plan on drift**):

```yaml
baseline:
  repository: Quantum-L9/Cursor-Governance
  workspace: /Users/ib-mac/Cursor-Governance
  ssot_clone: /Users/ib-mac/.cursor-governance
  branch: fix/issue-26-basename-cli   # re-verify at T0; may differ
  commit_sha: b7335757af1db8d18bb16e148b06148572e72309
  dirty: true   # untracked WIP/reports present — do not assume clean tree
  canonical_law_sha256: ac6008b4912124256d2c9c45a7f5034fc8088e5b111b0b588dc73d28c27856b6
  agents_md_sha256: dac06e0b26124323739384705659c9ebf6496b8b14cfc2f0e682ab596d1fbad5
  rules_manifest_sha256: 7e280b512fc1c30a4e15da21ee5f4b5337877e8fdc2b0d5e6ef52b21fd69cca6
  dependency_lock_sha256: 585ebd1af1e7a17a4de178711838b80c4f85c4a02847b42535440ac8294fcd9a
```

Execution step 0:

```text
plan.baseline ──compare──► current repo
                 /    \
              same    drift
               │        │
            continue   STOP → re-plan (do not mutate)
```

Untracked local dirt is allowed only if it does not overlap `may_modify` paths; overlapping dirt → STOP.

## Objective

Remove deprecated local T0 resume storage, migrate durables **only** via Graphiti CLI, extinguish regenerators, relocate `make pr` handoffs to `.l9/pr/`, prove deletion is sticky.

**Success properties (evidence-based, not “command exited 0” alone):**

| ID | Property | Evidence type | Proof |
|----|----------|---------------|-------|
| P-ABSENT | No `memory-bank/` on WS or SSOT | filesystem | `test ! -d …` both roots |
| P-STICKY | Symlink setup does not recreate it | runtime_behavior | run setup; re-check absent |
| P-MIGRATE | Durables searchable in Graphiti | runtime_behavior | CLI write + `search` hit per atom |
| P-HANDOFF | PR handoff path is `.l9/pr/` | structural | `open_pr_after_gate.sh` + AGENTS text |
| P-NOWRITE | No ops script mkdirs/writes memory-bank | structural | `rg` zero writer hits under `ops/scripts`+`ops/hooks` |
| P-GATE | Changed-file local gate green | quality_gate | `make pr-check` on envelope paths |

## Capability preflight (P0 — runtime census)

Before any mutate TODO:

| Probe | Property | Pass |
|-------|----------|------|
| Graphiti health | Memory plane reachable | healthy / tools list |
| `resolve` | Write group correct | `cursor-governance` (not `igor-workspace`) |
| `search` smoke | Read path works | exit 0 (empty OK) |
| Interpreter | CLI can import PyYAML | `$GOV/.venv/bin/python` + client |
| `.l9/` writable | Receipt/handoff home exists or creatable | mkdir OK |
| Wiring script | Governance wiring runnable | script exits; WARN on residual memory-bank OK |

If any probe Failed → status **Blocked** (keep durables on disk).

Do **not** treat advisory mypy corpus (historical debt) as a blocker for this mission; do treat **new** gate failures on touched files as blockers (ratchet: no new debt on envelope paths).

## Execution envelope (P1 — capability boundary)

```yaml
execution_envelope:
  filesystem:
    write:
      - ops/scripts/open_pr_after_gate.sh
      - ops/scripts/setup_workspace_symlinks.sh
      - ops/scripts/check_governance_wiring.sh
      - ops/graphiti/graphiti_memory_client.py
      - ops/graphiti/MEMORY_BANK_POLICY.md
      - ops/graphiti/DEPLOY.md
      - ops/graphiti/docs/CURSOR-GRAPHITI-INSTANTIATION-BRIEF.md
      - ops/graphiti/memory-bank-template/**   # RETIRED.md only
      - environment/claude-code/hooks/session_start_claude_governance.sh
      - .claude/hooks/session_start_claude_governance.sh
      - skills/l9-bounded-autonomy/SKILL.md
      - skills/l9-bounded-autonomy/references/campaign-handoff.md
      - commands/start-session.md
      - rules/98-make-pr-remediation.mdc
      - docs/MEMORY_PIPELINE_MAP.md
      - end-session.yaml                      # append-only root discipline
      - AGENTS.md                             # append-only
      - .l9/tmp/**
      - .l9/pr/**
      - memory-bank/**                        # delete only
      - $HOME/.cursor-governance/memory-bank/**  # delete only
    deny:
      - CANONICAL_LAW.md
      - ops/hooks/session_start_bootstrap.sh  # already correct; no drive-by
      - "**/.env"
      - "**/secrets/**"
  commands:
    allow:
      - governance venv python + graphiti_memory_client
      - rg / find / test / mkdir / rm -rf (scoped paths)
      - bash ops/scripts/setup_workspace_symlinks.sh
      - bash ops/scripts/check_governance_wiring.sh
      - make pr-check
      - python3 ops/scripts/sync_generated_artifacts.py
      - shasum / git rev-parse / git status
    deny:
      - git push --force
      - gh pr merge
      - terraform / infisical vault mutations
  network:
    mode: graphiti_only   # MCP Graphiti + existing tunnel; no new external writers
  secrets:
    access: none_required_for_migrate   # episode bodies redacted; no secret values
  autonomous_merge: false
```

## Side effects / idempotency (P0 — per TODO)

| TODO | side_effects | idempotency | retry | compensation | irreversible |
|------|--------------|-------------|-------|--------------|--------------|
| baseline-lock | none (read) | safe_to_repeat | n/a | n/a | false |
| capability-preflight | network_read | safe_to_repeat | retry_once | n/a | false |
| classify-receipt | filesystem_mutation | safe_to_repeat (overwrite receipt) | retry_once | rm receipt | false |
| delete-noise | filesystem_mutation, destructive | safe_to_repeat | retry_once | none (noise) | true for those files |
| mine-cli-write | network_write | **unsafe_blind_repeat** — search-dedupe before write | retry_once after search | cannot unwrite; supersede via new lesson | false* |
| relocate-handoff | filesystem_mutation | safe_to_repeat | retry_once | git restore file | false |
| stop-scaffold | filesystem_mutation | safe_to_repeat | retry_once | git restore | false |
| docs-alignment | filesystem_mutation | safe_to_repeat | retry_once | git restore / revert append | false |
| delete-trees | filesystem_mutation, destructive | safe_to_repeat | none after Gate B | restore only from Graphiti + template emergency | true for local trees |
| validate-converge | network_read, filesystem_mutation (none expected) | safe_to_repeat | retry_once | n/a | false |

\*Graphiti episodes are append-only; compensation = corrective episode, not delete.

## Architecture impact (P1 — ownership)

| TODO | bounded_context | layer | owning_contract | prohibited |
|------|-----------------|-------|-----------------|------------|
| mine-cli-write | graphiti_memory | control_plane | ADR-0005, MEMORY_PIPELINE_MAP, rules/03 | Product Neo4j; MCP as primary write; dual-write memory-bank |
| relocate-handoff / stop-scaffold | governance_wiring | chassis/ops | CANONICAL_LAW §2.1 Cursor-primary | Implementing shared brain under `environment/claude-code/` |
| docs-alignment | agent_docs | docs | AGENTS append-only / root protection | Overwriting protected root content without marker |

## Typed rollback (P1)

```yaml
rollback:
  supported: true
  trigger_conditions:
    - Gate B migrate search miss after writes
    - make pr-check fail on envelope paths
    - accidental edit outside execution_envelope
  code:
    strategy: git_restore_envelope_paths   # tracked files only
  data:
    strategy: none   # Graphiti append-only; corrective lesson if wrong atom
  external_state:
    strategy: none
  local_trees:
    strategy: do_not_undelete_noise; durables only if Gate B never passed
  verification:
    - git status --envelope paths clean or intentional
    - make pr-check
    - test memory-bank absent OR durables still present if Blocked
  irreversible_operations:
    - delete of sonar dumps / empty stubs
    - rm -rf memory-bank after Gate B
```

## Complexity / uncertainty (P2 signal)

```yaml
complexity: medium
uncertainty: medium   # Graphiti auth/group + dirty worktree
blast_radius: medium  # hooks/docs/make-pr path; not product engines
architectural_boundaries_crossed: 2   # memory plane + governance wiring
external_systems_touched: 1           # Graphiti VPS
migration_required: true              # T0 → Graphiti
unknown_dependency_count: 1           # whether SSOT clone path differs mid-flight
```

## Inventory + classify (unchanged substance)

**Delete (noise):** `sonar-pr98-*.json`; empty `tasks.md`/`progress.md`/`tech-debt.md`.

**Migrate then delete:** workspace `activeContext.md` (rewrite stale next — WB#109/SEO#47/CG#99 **MERGED**); `infisical-once-plan.json` → redacted decision/outcome + T6 residual; spent PR handoffs → one closed lesson; SSOT Jul-20 lessons (rebase / SchemaStore / `- uses:`).

**Classify receipt:** `.l9/tmp/memory-bank-retire-classify.json` — required before mutation.

## Write pipeline (CLI only)

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
CLIENT="${GOV}/ops/graphiti/graphiti_memory_client.py"
# Gate A → classify → noise delete → ≤5 writes with search-dedupe → Gate B
```

Canonical episodes (≤5): pickup_context (accurate next=); Infisical decision (redacted); three lessons (checkout -b; SchemaStore categories; SHA-pin `- uses:`). Skip if search already hits equivalent.

## Regenerators R1–R12 (extinguish)

R1 `open_pr_after_gate.sh` → `.l9/pr/`; R2 remove symlink scaffold; R3 wiring WARN-if-present; R4 inject/`_read_memory_bank` no-op; R5 Claude excerpt removal; R6 policy RETIRED; R7 AGENTS append-only; R8 start-session + rules/98; R9 bounded-autonomy no T0 fallback; R10 `end-session.yaml` Graphiti-only (append-only); R11 DEPLOY + instantiation brief; R12 template `RETIRED.md` stop copy.

## Execution DAG

```text
baseline-lock → capability-preflight → classify-receipt → delete-noise
       → mine-cli-write → relocate-handoff → stop-scaffold → docs-alignment
       → delete-trees → validate-converge
```

Parallelism: after Gate B, `relocate-handoff` ∥ `stop-scaffold` allowed if no file overlap conflicts; `docs-alignment` after code regenerators; `delete-trees` after both.

## Property evidence matrix (final validation)

| Property | Setup | Command / check | expected_positive | expected_negative | covers |
|----------|-------|-----------------|-------------------|-------------------|--------|
| P-MIGRATE | Gate B writes done | `graphiti_memory_client search "memory-bank retired"` | hit on PICKUP | no secret material in body | CAP-MEM-MIGRATE |
| P-ABSENT | Gate C | `test ! -d memory-bank` ×2 | exit 0 | — | CAP-MEM-ABSENT |
| P-STICKY | after setup script | re-test absent | exit 0 | — | CAP-MEM-STICKY |
| P-HANDOFF | code changed | `rg handoff_dir open_pr_after_gate.sh` | `.l9/pr` | no `memory-bank` | CAP-PR-HANDOFF |
| P-NOWRITE | — | `rg 'mkdir -p.*memory-bank\|handoff_dir=.*memory-bank' ops/` | zero | — | CAP-NO-REGEN |
| P-GATE | dirty only envelope | `make pr-check` | PASS | — | CAP-LOCAL-GATE |

## Stress / disconfirm

- **Disconfirming:** Schema-valid plan executed on drifted SHA → forbidden (baseline gate).
- **Assumption false if:** Graphiti group resolve returns shared workspace group → Blocked.
- **Blast radius:** make-pr handoff consumers must read new path (document in AGENTS + rule 98).
- **Rollback:** typed object above; never force-push; never undelete via re-scaffold as success path.

## Out of scope (this contract)

- Implementing Phase B distill
- Website-Bot / SEO-Bot / Infisical vault mutations
- MCP as primary write path
- Committing secrets; force-push; merge
- Org-wide deletion of consumer `memory-bank/` trees
- Full `l9-plan` schema redesign / mypy ratchet engine / asset lifecycle registry productization

## Follow-on milestone (architect P0–P2 for control plane — separate plan)

Do **not** fold into this PR. Next architectural plan after retirement converges:

| Pri | Change | Why |
|-----|--------|-----|
| P0 | `PLAN_DOCUMENT.baseline` in schema + GMP Phase0 compare | Prevent exec against changed reality |
| P0 | Property/evidence validation fields in schema | Avoid green-command false confidence |
| P0 | side_effects / idempotency on todos | Resumable agent execution |
| P0 | Runtime capability census hook in pre_validation | Don’t build on broken subsystems |
| P1 | Typed `rollback` object in schema | Safe remediation |
| P1 | `architecture_impact` + envelope in GMP handoff | Boundary violations before code |
| P1 | Ratcheting quality (new errors = 0) | Debt without blocking all work |
| P1 | Machine-readable asset lifecycle registry | Kill superseded/dangling refs |
| P2 | uncertainty × blast_radius over wall-clock | Better autonomy signal |

Preserve: machine-readable PLAN_DOCUMENT SSOT, authority order (repo reality > framework), Cursor-primary / wrap-outward, stress-test first-class, graph-engine chassis boundary.

## Convergence

This plan is execution-ready when baseline is re-verified, envelope is respected, and Gates A–C + property matrix are the definition of done. Broader l9-plan control-plane evolution requires its own PLAN_DOCUMENT — not silent scope expansion here.
