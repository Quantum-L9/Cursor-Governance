# CHANGE_SUMMARY — current v2.7.0

## v2.7.0 — target-aware validation + same-branch one-commit chain

Repairs two live compiler defects and formalizes the requested execution transport without changing
the contract scope/DPK architecture.

| Surface | Change |
|---|---|
| `schemas/campaign-spec.schema.json` | `campaign.validation` required; cold-resume + commit-gate commands explicit; `sizing.commits` fixed to 1 |
| `scripts/compile_contract.py` | removed npm defaults; executable branch equality; current-item proof gates commit; N+1 consumes only N's dedicated completion proof; internal `committed_and_validated` seams; exact one-commit command; terminal-only `make pr` |
| `schemas/coding-contract.schema.json` | `git_workflow`; `required_before_commit`; internal committed state; one-commit metadata |
| `scripts/generate_preflight.py` | exact command execution; no `#` stripping; multiline fail-closed; safe display quoting |
| `scripts/validate_contract.py` | validates git workflow, completion proof, direct remote denials, committed handoff shape |
| `scripts/validate_chain.py` | proves predecessor HEAD/proof, one commit per contract, same branch, one terminal `make pr` |
| `scripts/plan_decomposition.py` | max commits per focused contract = 1 |
| `scripts/generate_claude_settings.py` | generated CLAUDE.md states exact commit command, no intermediate push, terminal delivery |
| examples | Node explicit npm migrated; Python and Go neutrality fixtures added |
| `scripts/test_target_validation.py` | executable 11-case regression suite including real Git branch/predecessor preflight and no-replay proof |
| docs/provenance/intelligence | updated to remove stale merged/npm assumptions and encode current authority |
| `agents/openai.yaml` | ChatGPT Skill UI metadata added for packaged-skill compatibility |

Intentional breaking input change: old campaign specs must add `campaign.validation`. There is no
compatibility fallback because silently restoring npm would reintroduce the defect.

---

# CHANGE_SUMMARY — v1.0.0 -> v2.0.0 (DPK-1.0 integration)

Recursive improvement passes (L9 recursiveImprovementMode, min 5):
1. inventory_and_baseline: 24 files, no stubs. Gap: no repo-operability layer.
2. contract_tightening: DPK AGENTS.md authority order adopted; scope derived from manifest.
3. entropy_reduction: DPK layers bound 1:1 to contract sections (no overlap, AD-005/AD-006).
4. implementation_hardening: 5 DPK schemas + readiness scoring added to validate_contract.py.
5. validation_and_commit_readiness: validator executed on 4 fixtures; 10-pass alignment audit PASS.

| Change | Type |
|---|---|
| `references/dpk-integration.md` | NEW — six-layer control plane bindings |
| `schemas/dpk-manifest.schema.json` | NEW |
| `schemas/dpk-task-contract.schema.json` | NEW |
| `schemas/dpk-alert-runbook.schema.json` | NEW |
| `schemas/dpk-debt-register.schema.json` | NEW |
| `schemas/dpk-readiness-score.schema.json` | NEW |
| `schemas/coding-contract.schema.json` | UPDATED — dpk block + refs |
| `scripts/validate_contract.py` | UPDATED — DPK readiness + red-line gate |
| `SKILL.md` | UPDATED v2.0.0 — dpk-integration in resource map |
| `ALIGNMENT_REPORT.md` | NEW — 10-pass audit result |

## v2.1.1 — correctness fixes (validators + cause)

Fixes found by dogfooding the compiler on its own PR-B output (the chain shipped "converged"
while `validate_chain.py` rejected it, and the validator's v2.1.0 checks were dead code).

| Change | Type | Why |
|---|---|---|
| `scripts/validate_contract.py` | FIX | v2.1.0 checks (`read_only_authority`, `session_budget`, `halt_codes`) sat below `sys.exit(main())` and referenced an undefined `run_claude_fit_checks` — dead when run, `NameError` on import. Now defined above `main()` and actually invoked. Added `check_handoff_seam_shape` so a bad seam is caught per-contract too. |
| `scripts/validate_chain.py` | FIX | Repaired the mangled rule-3 `source_commits` expression; added the missing commit-gap check; version → v2.1.1. |
| `schemas/coding-contract.schema.json` | UPDATED | `session_budget.source_commits` added so the chain gap/dup check has real data. |
| `references/claude-fill-policy.md` | UPDATED | NEW **Seam Vocabulary Contract**: the handshake field must be `"<id> merged_and_green"`, byte-identical to the next contract's intake; capabilities move to `verify_before_starting`. This is the *cause* fix — the fill policy previously let the two seam fields use different vocabularies, which `validate_chain.py` (correctly) rejects. |
| `SKILL.md` | UPDATED | Resource Map now lists all 5 bundled scripts (was 1); workflow + Validation now REQUIRE `validate_chain.py` on any decomposed chain — "per-contract green alone is not convergence." |

## v2.2.0 — deterministic emitter + canonical input spec

Closes the last determinism gap: `author` mode filled the 30 sections by model judgment, which
violated the skill's own rule ("determinism-critical logic MUST live in bundled scripts"). The
emit step is now a script; the model only authors a canonical spec.

| Change | Type | Why |
|---|---|---|
| `scripts/compile_contract.py` | NEW | Spec-driven emitter. Reads `campaign-spec.yaml`, emits schema-valid instances, and **derives** `contract_id`, handoff seam tokens, contiguous `source_commits`, and `chain_digest` (imported from `validate_chain.py` — one digest source, no drift). Self-validates every instance + the chain and exits non-zero on any failure. Fails closed with `DECOMPOSE_REQUIRED` on oversized items; enforces `in_scope ⊆ boundaries.owns` and injects `does_not_own` into `hard_out_of_scope`. |
| `schemas/campaign-spec.schema.json` | NEW | Canonical input contract: campaign block + ordered items (`allowed_files`, `forbidden_paths`/`forbidden_capabilities`, `preserved`, `verify_proof`, `sizing`, required `readiness.categories`). |
| `references/canonical-spec.md` | NEW | The seven input-canonicalization rules. |
| `examples/campaign-spec.example.yaml` | NEW | Full 9-item PR-002..010 campaign spec with real per-item DPK assessments. |
| `SKILL.md`, `RUNBOOK.md`, `references/output-modes.md` | UPDATED | Workflow adds the `compile` step; author mode is now script-emitted; Resource Map lists the emitter + spec schema + example. |
| DPK readiness | HARDENED | `readiness.categories` is now a **required real assessment** per item — the emitter never fabricates a score. |

Verification: emitting the PR-002..010 example reproduces `chain_digest =
sha256:03141121760661ccbc13093e5e786d6578de102a91af7f088f52a1c599dfcb3c` (identical to the
hand-built pack — digest is over contract IDs, so chain identity is preserved), 9/9
`validate_contract` VALID, chain VALID, and all four fail-closed negative tests pass.

## v2.3.0 — exemplary intelligence layer (l9-skill-compiler v3.3.0)

Added `expertise_model.yaml`, `skill_intelligence_report.yaml`, `references/enforcement-gates.md`;
SKILL.md gained the Exemplary Intelligence Layer section. `validate_exemplary_skill.py` → PASS.
Doc/metadata only — no script, schema, or gate behavior changed.

## v2.3.1 — documentary hardening (recursive-improvement pass, additive doc-only)

Ran a recursive-improvement/alignment pass; the logic was green but evidence docs had gone stale.
Fixes (F1–F6), **zero code/schema/gate changes**:

| Change | Type | Why |
|---|---|---|
| `REGRESSION_GUARD.md` | REWRITTEN (F1) | v2.0.0 guard didn't cover the v2.2.0 emitter or v2.3.0 layer; now enumerates every version + the digest-invariance assertion. |
| `ALIGNMENT_REPORT.md` | REFRESHED (F2) | Re-scanned the new surface (15 schemas, emitter, intelligence YAMLs): transport N/A, 0 forbidden-term source hits, `safe_load` only, no unsafe calls. |
| `VALIDATION.md`, `MANIFEST.md` | HEADERS (F3) | Stale v1.0.0/table headers refreshed; addition tables declared authoritative. |
| `expertise_model.yaml`, `skill_intelligence_report.yaml` | METADATA (F4) | Added `# L9META` provenance headers (comments only; data unchanged). |
| `PROVENANCE_MAP.yaml` | NEW (F6) | source nuclear-contracts → campaign spec → emitter → instances → validators. |

**F5 — doctrine single-source-of-truth map** (compression without churn): each recurring rule has
one authoritative home; other files reference it. Do not restate authoritatively elsewhere.

| Doctrine | Authoritative source |
|---|---|
| Seam Vocabulary (handshake tokens) | `references/claude-fill-policy.md` |
| Input canonicalization (7 rules) | `references/canonical-spec.md` |
| Determinism-in-scripts (emit rule) | `SKILL.md` Non-Negotiables |
| Scope-lock three lists | `references/kernel-scope-lock.md` |
| Fail-closed blocking states | `references/kernel-fail-closed.md` |
| Per-stage enforcement gates | `references/enforcement-gates.md` |

Re-verified after edits: `validate_exemplary_skill.py` PASS; emitter digest still
`sha256:0314…cb3c`, 9/9 + chain VALID. Diff limited to `*.md` + 2 YAML comment headers + new PROVENANCE_MAP.

## v2.4.0 — orchestration module (hands-off chain execution)

Adds `orchestrate/` so a compiled chain runs **one fresh Claude Code session per contract**, in order,
without manual copy-paste between sessions. `make_state.py` builds an ordered `state.yaml` from the
emitted `out/PR-*/` set; `advance.py` is the deterministic driver (`next` / `seed <id>` / `set`);
`orchestrate/README.md` documents the 3-stage flow and the Routine wiring
(`create_trigger` + `create_new_session_on_fire`).

Default policy **`chain_on: green`** — fully hands-off (next contract builds as soon as the prior is
green; one stack review/merge at the end). `chain_on: merged` pauses per PR for a tap or CI auto-merge.
The merge step stays the one authorized action (contracts deny push/merge). Emitter, validators, and
schemas are byte-unchanged; digest + exemplary gate re-verified. Driver tested in both gate modes.

## v2.5.0 — no-HITL auto-merge gate

Removes the human tap before merge, replacing it with a deterministic gate `orchestrate/automerge_gate.py`.
A PR auto-merges ONLY when **ci_green AND review_flags_resolved AND review_comments_resolved**
(the last requires `remediation_ran: true` — the PR-remediation/autofix loop ran against the
review-agent comments). `advance.py gate <id> pr_state.json` promotes `green -> merged` on ELIGIBLE
(`merge_policy: auto`), else keeps it green and prints the blocking condition.

Gate tested on 6 fixtures: 1 ELIGIBLE + 5 fail-closed (CI failure, changes-requested, unresolved
thread, remediation-not-run, CI-pending). `advance.py gate` promotes only on ELIGIBLE; a CI-failing PR
stays green.

### Migration record (control relaxation — logged, not silent)
```yaml
control_relaxation: remove_human_in_the_loop_before_merge
authorized_by: operator request (2026-07-13)
replaced_by: automerge_gate (ci_green AND review_flags_resolved AND review_comments_resolved+remediation_ran)
still_enforced:
  - build session cannot push/merge (denied_tools unchanged; DPK role isolation)
  - merge runs in a separate authorized step, gated deterministically
  - GitHub branch protection (required checks + conversation resolution + agent approval) as outer enforcement
```
Emitter/validators/schemas byte-unchanged; digest `sha256:0314…cb3c` + exemplary gate re-verified.

## v2.6.0 — belt-and-suspenders (GitHub branch protection + native auto-merge)

Makes the merge CALL itself impossible to fire early — a second, server-side gate independent of the
orchestrator. `orchestrate/apply_branch_protection.py` turns `branch_protection.example.yaml` into the
GitHub REST payloads (branch protection has no MCP tool) and prints ready-to-run `gh api` commands
(DRY-RUN default; `--apply` live with a token). It requires: CI + review-agent status checks, strict
up-to-date, `required_conversation_resolution`, and `require_code_owner_reviews` + 1 approval with the
review agent as CODEOWNER — **0 human approvals**. `verify_branch_protection.py` fail-closed confirms
the live branch matches before the orchestrator trusts auto-merge. Native per-PR auto-merge is enabled
via the MCP tool `enable_pr_auto_merge`; GitHub merges the instant protection passes, and
`automerge_gate.py` records eligibility + flips state to merged.

Tested: apply dry-run emits correct payloads + commands; verify passes on a compliant fixture and
fail-closed lists all 5 gaps on a weak one. Emitter/validators/schemas byte-unchanged; digest +
exemplary gate re-verified. The skill makes no live GitHub call itself (apply is DRY-RUN without an
explicit `--apply` + token).

## v2.6.2 — clean compiler (orchestrator extracted to a sibling pack)

Separation of concerns: the orchestration surface (v2.4.0–v2.6.1: `orchestrate/advance.py`,
`make_state.py`, `automerge_gate.py`, `apply_branch_protection.py`, `verify_branch_protection.py`,
config/README) is **removed from this compiler** and moved to the standalone sibling pack
**`l9-pipeline-orchestrator`**. That pack consumes this compiler's emitted `out/PR-*/` contracts.

Rationale: the compiler's job is emit + validate; chain execution, merge policy, and GitHub branch
protection are a distinct lifecycle concern that should version independently. Emitter, validators,
schemas, and the exemplary intelligence layer are **byte-unchanged**; digest `sha256:0314…cb3c` and
`validate_exemplary_skill.py` re-verified after removal.

## v2.3.2 — convergence finalization (recursive kernel pass 2)

Re-ran the recursive-improvement kernel against the revised v2.3.1 pack. It found exactly one
residual item — **G1**: `MANIFEST.md` headline said "44 files" but the pack is 45 (an off-by-one
the v2.3.1 F3 header edit introduced before `PROVENANCE_MAP.yaml` was counted). Fixed `44 → 45`,
bumped version headers to v2.3.2, and stamped `convergence_status: fixed_point` in `SKILL.md`.

| Change | Type |
|---|---|
| `MANIFEST.md` | FIX (G1) — file count 44 → 45 |
| version headers (SKILL/MANIFEST/ALIGNMENT/VALIDATION/REGRESSION_GUARD) | v2.3.1 → v2.3.2 |
| `SKILL.md` | `convergence_status: fixed_point` added |

**Convergence:** two kernel passes; pass 1 closed six stale-doc findings, pass 2 closed the single
self-introduced count typo. An additional pass yields no material improvement → **converged (fixed
point)**. Zero code/schema/gate changes across the entire v2.3.x line; emitter digest invariant and
exemplary gate hold.
