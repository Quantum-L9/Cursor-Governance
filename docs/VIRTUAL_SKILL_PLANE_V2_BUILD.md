# Virtual Skill Plane v2 — build brief

Schema: `L9_VIRTUAL_SKILL_PLANE_V2` · Repository: `Quantum-L9/Cursor-Governance`
· Branch: `claude/virtual-skill-plane-v2-6ybcqf` · Built: 2026-09-06

## Executive verdict

Cursor native skill discovery cardinality is now decoupled from canonical L9
skill cardinality, statically proven and CI-enforced. Cursor discovers exactly
one native skill (`l9-skill-gateway`); the canonical corpus (56 skills) stays
under `skills/` and is reached through registry v2, the unchanged deterministic
router, exact materialized `SKILL.md` resources, and conversation-scoped atomic
route receipts. The plugin manifest cutover was performed only after the
replacement control plane passed its full suite in legacy-manifest mode.

**Final status:** `VIRTUAL_SKILL_PLANE_V2_BUILT_STATICALLY_VALIDATED_RUNTIME_CURSOR_GATE_PENDING`
— no Cursor runtime exists in this cloud session, so the runtime acceptance
gate is `NOT_EXECUTED`. The branch is published as PR #513 with every CI check
green (see "Publication state"). Nothing in the build itself is pending.

## Revision binding

| Item | Value |
|---|---|
| Exact start SHA (`origin/main`) | `051c63c904a35210e549ff4eb125325dedfcba99` |
| Code candidate SHA (local, phases 0–7) | `d809a72` |
| Code candidate SHA (local, phases 8–12, cutover) | `da618d33b267ca7ebaaee9accd363b8133f379ce` |
| PR #513 first head (after #512-aligned frontmatter + worktree test isolation) | `c88ffa3e806d7c5202ed0d19449635400814d956` |
| Branch tip | the commit carrying this brief revision (see PR head) |

## Architecture before

```
CURSOR NATIVE PLANE ──(.cursor-plugin/plugin.json "skills": "skills")──▶ skills/ (56 canonical SKILL.md exposed natively)
beforeSubmitPrompt ──▶ route_prompt() ──▶ ~/.cursor/l9/skill-route.json (global, non-atomic, written only on a hit)
                                     └──▶ additional_context (unsupported on beforeSubmitPrompt)
rules/23 ──▶ static "Common triggers" table + l9-plan-simple planning mapping (second routing authority)
AUTONOMY_MANIFEST.cursor_discovery ──▶ "~/.cursor/skills symlinked" (stale model)
manifest route `plan` ──▶ l9-plan  (rule said l9-plan-simple: split-brain)
```

## Architecture after

```
CURSOR NATIVE PLANE
   │  exactly 1 discoverable skill  (.cursor-plugin/plugin.json "skills": "./environment/agents/adapters/cursor/skills")
   ▼
l9-skill-gateway / SKILL.md            adapter only — no routing, no scoring, no inventory
   │  fallback: ops/skill_routing/resolve.py --prompt
   ▼
L9 CONTROL PLANE
   skills/AUTONOMY_MANIFEST.yaml  (cursor_discovery: mode virtual_gateway)
   ops/generated/skill-registry.json  (registry v2: skill_md, skill_sha256, generation_id)
   ops/skill_routing/registry.py  → route_prompt.py (unchanged brain, explicit ties)
   → materialize.py (exact SKILL.md, path security) → receipt.py (scoped, atomic)
   ~/.cursor/l9/routes/<conversation-key>/current.json   routed | no_route | disabled | degraded
   sessionStart: ### Route locator (+ env L9_ROUTE_CONVERSATION_ID / L9_ROUTE_RECEIPT_PATH)
   ▼
CANONICAL CAPABILITY PLANE   skills/l9-*/SKILL.md  (N = 56 today; N never changes native count)
```

## Authority consolidation (current vs target)

| Concern | Before | After |
|---|---|---|
| Semantic routing inventory | manifest + registry **and** rule 23 table **and** native roster | `AUTONOMY_MANIFEST.yaml` → registry v2 only |
| Selection | `route_prompt.py` (implicit manifest-order ties) | `route_prompt.py` (score DESC, priority DESC, route_id ASC) |
| Name → resource | none (model rediscovered skills) | `materialize.py` |
| Route state | global `skill-route.json` | per-conversation `routes/<key>/current.json` |
| Cursor discovery | `skills/` (N skills) | `environment/agents/adapters/cursor/skills` (1 skill) |
| Runtime enforcement | rule 23 v1 (mapping + hook path) | rule 23 v2 (consumption contract only) |
| Projection proof | none | `validate_skill_projection.py` (pre-commit + CI + Makefile) |

Findings reconfirmed before edit: VSP-P0-001…P0-004, P1-001…P1-006,
P2-001…P2-004 all reproduced on `051c63c9` (see characterization results).
P3-001 (Claude-specific names such as `claude_routing`,
`build_claude_skill_registry.py`) is **deferred** unchanged.

## Planning split-brain resolution

Confirmed against the skill contracts: `l9-plan/SKILL.md` ("do not use for
ordinary cursor plan mode or build-button plans (use l9-plan-simple)") and
`l9-plan-simple/SKILL.md` ("do not use for /l9-plan, make campaign, or a PE
lock"). Encoded in the manifest:

| Prompt class | Primary | Route |
|---|---|---|
| ordinary implementation plan / Build-ready spec / Cursor Plan mode | `l9-plan-simple` (stays `explicit_only`; reached by `hint_allowed` — see "Claude Code preservation") | `plan` (`required_any` planning phrases; negative signals: campaign, program lock, program-execution, pe+autonomy, /l9-plan) |
| Program Execution campaign plan / PE+autonomy / Program Lock / `/l9-plan` | `l9-plan` | `campaign_plan` (priority 1) |
| `make campaign INTENT=…` (live activation) | `l9-pe-campaign-activate` (`explicit_hint`) | `pe_campaign_activate` (unchanged) |

Rule 23 v2 carries no planning mapping; the characterization test
`test_rule_and_router_agree_on_ordinary_planning` fails if a trigger table
returns.

## Registry v2

`ops/scripts/build_claude_skill_registry.py` emits `schema_version: 2`,
`generation_id = sha256("<manifest_sha>:<corpus_sha>")`, and per record
`skill_md` + `skill_sha256`; route ids must be unique and `priority` an int.
`ops/skill_routing/registry.py` validates schema, top-level identity fields,
record shape (`^l9-…`, `path == skills/<name>`, `skill_md == skills/<name>/SKILL.md`,
hex digest, invocation enum), duplicate names, and route references; it builds
the name index and exposes generation identity. Corpus hashing happens only at
generation (`check_files=True` is opt-in for CI). Regeneration is byte-identical
(`test_generation_is_byte_deterministic`).

## Scoped receipt design

Schema `l9.cursor-skill-route.v2`; statuses `routed | no_route | disabled |
degraded`; required fields `schema, status, conversation_id, generation_id,
workspace_roots, workspace_key, issued_at, expires_at, registry` (+
`conversation_key`, optional `prompt_sha256`, never the raw prompt). Layout
`~/.cursor/l9/routes/<sha256(conversation_id)[:32]>/current.json`
(`L9_ROUTE_STATE_ROOT` injects the root for tests). Writes: same-directory
temp → flush → fsync → `os.replace`. Reads validate schema, status,
conversation identity + key, workspace scope, TTL (default 1800 s,
`L9_ROUTE_TTL_SECONDS`), registry generation, and materialized skill presence.

## Materialization design

`materialize_route(decision, registry)` resolves primary + ≤2 supports to
`{name, skill_md (absolute), invocation, sha256}`; rejects unknown names,
overlap, >2 supports, absolute or traversal paths, non-`SKILL.md`, wrong
folder, missing files, symlink escapes out of `skills/`, and digest mismatch
against the registry (fail closed).

## Gateway contract

`environment/agents/adapters/cursor/skills/l9-skill-gateway/SKILL.md`
(343 discovery bytes, budget 1024): native roster ≠ canonical inventory;
inventory = registry; consume the scoped receipt; fallback = shared resolver;
one primary / two supports; routing is never mutation authority; never
enumerate, mirror, score. The validator rejects any canonical skill name in
the gateway body.

## Plugin cutover and rollback

`.cursor-plugin/plugin.json`: `skills: "skills"` → `"./environment/agents/adapters/cursor/skills"`;
`l9.canonical_skills_directory: "skills"` plus registry/projection/gateway
metadata. Performed after the pre-cutover suite (validator in
`--allow-legacy-manifest` mode, routing/registry/materialize/receipt/locator/hook
suites) was green. **Rollback proof:** reverting that one field restores the
prior discovery; registry v2, receipts, materialization, router tests, and the
planning fix remain valid because canonical skills never moved
(`test_legacy_plugin_manifest_fails_strict` shows the validator's legacy mode
accepts the rollback state).

## Cardinality

| Measure | Value |
|---|---|
| Cursor native skill count | 1 |
| Canonical skill count | 56 |
| Registry skill count | 56 (= canonical, asserted) |
| Synthetic canonical skills added in test | +1 and +1000 → registry grows, native stays 1 |
| Synthetic registry sizes routed end-to-end | 100, 500, 1000, 5000, 10000 |

## Synthetic scale results (this container, `.venv` Python 3.12, median/p95)

| N | registry parse | retrieve | explicit route | description fallback | materialize | receipt write | whole hook |
|---|---|---|---|---|---|---|---|
| 100 | 0.6/1.0 ms | 0.02/0.03 ms | 11.6/11.7 ms | 94/95 ms | 0.11/0.31 ms | 0.85/1.92 ms | 79/105 ms |
| 500 | 2.6/3.1 ms | 0.09/0.11 ms | 58/60 ms | 468/468 ms | 0.13/0.32 ms | 0.77/1.63 ms | 132/161 ms |
| 1000 | 5.3/6.0 ms | 0.20/0.23 ms | 118/123 ms | 940/954 ms | 0.15/0.35 ms | 1.0/2.1 ms | 194/196 ms |
| 5000 | 29/33 ms | 1.2/1.4 ms | 598/628 ms | 4513/4530 ms (full run) | 0.17/0.38 ms | 0.9/2.0 ms | 702/896 ms |
| 10000 | 66/69 ms | 2.5/2.7 ms | 1180/1183 ms | 9012/9053 ms (full run) | 0.12/0.33 ms | 0.7/1.5 ms | 1326/1447 ms |

Engineering targets (not architectural truth): route@5000 < 100 ms — **not
met** (598 ms; the scorer is O(routes × signals) and was deliberately not
rewritten); materialize+receipt < 50 ms — met (< 3 ms); whole hook < 500 ms —
met through 1000 skills, not at 5000+. At today's 56 skills the whole hook is
~80 ms. The description fallback is the O(N) hotspot (~0.9 ms/skill); the
retrieval boundary (`retrieve_candidates` / `rank_candidates`) is where a
bounded index goes when the corpus grows past ~1000. Fallback timing above
1000 runs only with `L9_VSP_SCALE_FULL=1`. No network, LLM, or MCP in the path
(`test_no_network_or_model_dependencies_in_prompt_path`).

## Route security results

Materialization: canonical pass, normalized internal symlink pass when the
registry digest matches, parent-escape fail, foreign-absolute fail, external
symlink fail, missing `SKILL.md` fail, digest-mismatch fail, unknown
primary/support fail (`test_materialize.py`, 14 cases). Validator: mirrored
skill fail, symlink escape fail, gateway-in-registry fail, legacy manifest
fail (strict), non-virtual manifest fail (`test_skill_projection.py`).

## No-route stale-state result

`test_no_route_overwrites_previous_route`, `test_empty_prompt_writes_no_route`,
`test_disabled_overwrites_routed`, `test_degraded_on_corrupt_registry`: a
routed receipt is replaced by `no_route`/`disabled`/`degraded` on the very
next event. A payload without `conversation_id` writes nothing and logs a
WARN (no scope to write into) — the documented limit.

## Concurrency isolation result

`test_two_conversations_have_separate_receipts`,
`test_conversation_a_cannot_consume_b`,
`test_same_workspace_different_conversations_are_separate`,
`test_different_workspace_same_conversation_rejected`,
`test_concurrent_writers_never_tear` (4 writers × 20 + reader, zero torn reads).

## Hook contract result

Inputs `conversation_id, generation_id, workspace_roots, prompt`; stdout
exactly `{"continue": true}` on every path (routed, no-route, disabled,
degraded, missing conversation, malformed payload, installed-symlink name);
source contains no `additional_context`, `skill-route.json`, `write_text(`,
or network imports (`test_before_submit_router.py`, 11 cases).

## Session locator

`session_locator.py` keys receipts on `conversation_id` (present on both
`sessionStart` and `beforeSubmitPrompt` per cursor.com/docs/agent/hooks;
`session_id` is never used). `session_start_bootstrap.sh` reads stdin once
(`read -r -t 3 -d ''`), delegates to the Python owner, appends `### Route
locator` to `additional_context`, and exports `L9_ROUTE_CONVERSATION_ID` /
`L9_ROUTE_RECEIPT_PATH` via the hook `env` output. Identifier relationship is
tested (`test_session_start_and_before_submit_share_identity`); a differing
runtime id is a one-function change (`extract_conversation_id`).

## CI projection invariants

Pre-commit hook `cursor-skill-projection`; `governance-self-check.yml` steps
"Cursor skill projection gate" and "Skill plane suites"; `make
cursor-projection-check`, `make skill-plane-test`; registry drift already
covered by `sync_generated_artifacts.py --check`.

## Cursor runtime acceptance

`NOT_EXECUTED` — this session has no Cursor runtime (cloud container, Claude
Code surface). Static repository validation is not runtime proof. Runtime
checklist to execute on a Cursor machine after `make cursor-install`: reload
the local plugin → native roster shows only `l9-skill-gateway` → prompt "Audit
this unfamiliar repository architecture and map the flows." → receipt `routed`
with `l9-code-analysis` + `l9-structured-reasoning` and the exact canonical
paths → "Fix this typo." → receipt `no_route` → two conversations → two
receipt directories → ordinary planning prompt → `l9-plan-simple` → explicit
hint → `source: explicit_hint`, no mutation → add a canonical skill +
regenerate → registry +1, native 1.

## Deferred naming cleanup

`claude_routing` → `routing`, `build_claude_skill_registry.py` →
`build_skill_registry.py`: not combined with this cutover (contract: only if
correctness requires it; it did not). Migration pattern when done: prefer new
key, accept legacy, fail closed when both present and differ.

## Unresolved UNKNOWNs

- Whether Cursor treats `"./environment/agents/adapters/cursor/skills"` in
  `plugin.json` identically to `"skills"` for a local plugin (same relative
  form as the existing `"./commands"`; runtime gate pending).
- Whether Cursor keeps `sessionStart` stdin open beyond the 3 s bounded read
  (payload is documented as a single JSON object; bounded read retains partial
  data).

## Validation evidence

| Check | Command | Exit | Result | Status |
|---|---|---|---|---|
| characterization + registry + materialize + receipt + locator + scale | `.venv/bin/python -m pytest ops/skill_routing/tests -q` | 0 | 104 passed (33 subtests) | PASS |
| hook contract + projection invariants | `.venv/bin/python -m pytest environment/agents/adapters/cursor/tests -q` | 0 | all passed (incl. 1000-synthetic-skill cardinality) | PASS |
| Claude-side router smoke | `.venv/bin/python -m pytest environment/agents/adapters/claude-code/tests/test_cursor_skill_router.py -q` | 0 | 2 passed | PASS |
| combined plane suite | same three paths, `-q` | 0 | 116 passed, 33 subtests, 36 s | PASS |
| Cursor projection validator (strict, post-cutover) | `.venv/bin/python environment/agents/adapters/cursor/validate_skill_projection.py` | 0 | native=1 canonical=56 registry=56 gateway_bytes=343 | PASS |
| pre-cutover validator (legacy manifest) | `… validate_skill_projection.py --allow-legacy-manifest` | 0 | PASS before the plugin edit | PASS |
| registry generation drift | `.venv/bin/python ops/scripts/build_claude_skill_registry.py --root . --check` | 0 | CURRENT | PASS |
| generated artifacts | `.venv/bin/python ops/scripts/sync_generated_artifacts.py --root . --force --check` | 0 | no updates needed | PASS |
| canonical skill standard | `.venv/bin/python ops/scripts/check_skills_standard.py` | 0 | 56 live, footprint 7199 B / 16384 | PASS |
| rules standard | `.venv/bin/python ops/scripts/check_rules_standard.py` | 0 | PASS (pre-existing 96-rule size warn) | PASS |
| Claude activation validator | `.venv/bin/python environment/agents/adapters/claude-code/validate_skill_activation.py` | 0 | RESULT: PASS (33 fixtures) | PASS |
| neighbouring suites (claude projection, sync, plan-simple, commands) | `.venv/bin/python -m pytest … -q` | 0 | 240 passed | PASS |
| ruff | `.venv/bin/ruff check` / `format --check` on changed Python | 0 | All checks passed | PASS |
| workflow action pins | `.venv/bin/python ops/scripts/validate_workflow_action_pins.py` | 0 | 43 references compliant | PASS |
| repo hygiene | `.venv/bin/python tools/check_repo_hygiene.py` | 0 | PASS | PASS |
| governance symlinks | `bash ops/scripts/validate_governance_symlinks.sh` | 0 | PASS | PASS |
| `make pr` full gate (kernel hook, pre-commit, ruff, generated heal, pytest catalog, skill self-tests, root-file protection, wiring, security) | `PR_OVERLAP=ignore PR_REMEDIATE=0 make pr` in `~/.l9/gov-worktrees/vsp-v2` | 0 | RESULT: PASS — local PR gate clean; PR open + subscribed | PASS |
| GitHub CI on PR #513 head `c88ffa3e` | 19 check runs (governance-self-check, Test Suite, Lint and Type Check, CodeQL, Semgrep, root-file append-only gate, SBOM, peer conformance, …) | — | 19/19 success | PASS |
| Cursor runtime acceptance | — | — | no Cursor runtime in this session | NOT_EXECUTED |

Two test-isolation defects surfaced only when the gate ran from a dedicated
worktree on a machine that also holds `~/.cursor-governance`: the resolver test
had to pin `HOME` so the home clone could not satisfy the ancestor-walk case,
and the synthetic scale roots had to carry the `ops/skill_routing` package under
test so the hook never loaded an older home-clone copy. Both are test-only
fixes (commit `c88ffa3e`); no product code changed.

## Publication state

Published as **PR #513** (`claude/virtual-skill-plane-v2-6ybcqf` → `main`)
through the sanctioned path only: L4 `begin` + `authorize-release`, tree-kernel
receipt, then `PR_REMEDIATE=0 make pr` from the dedicated wired worktree
`~/.l9/gov-worktrees/vsp-v2` (the SSOT clone stays on `main`, which the
governance wiring check requires). `PR_OVERLAP=ignore` was used with a stated
justification recorded in the PR body: the early-overlap probe found
end-of-file append collisions on the append-only `AGENTS.md` / `Makefile` with
PRs #508 and #509, and an identical `disable-model-invocation` removal in
`skills/l9-plan-simple/SKILL.md` with PR #512 (this branch now carries the same
hunk, so that file merges cleanly whichever lands first). Three sibling
chains made `PR_STACK=auto` ambiguous; merge bottom-up per rule 53.

Session notes that matter for the next publisher: publication was first
blocked because the repository was not attached to the cloud session (git proxy
and `gh api` 403); a `gate-failure.json` latched on that telemetry failure had
to be cleared once access was restored, and `make -C $GOV pr WS=<worktree>` is
gated on the SSOT clone's L4 receipt, so `make pr` must run inside the worktree.

## Changed-file inventory (40 paths, `051c63c9..da618d3`)

Control plane: `ops/skill_routing/{__init__,registry,route_prompt,materialize,receipt,session_locator,resolve}.py`,
`ops/scripts/build_claude_skill_registry.py`, `ops/generated/skill-registry.json`
(+ Claude mirror), `ops/hooks/before_submit_skill_router.py`,
`ops/hooks/session_start_bootstrap.sh`.
Cursor adapter: `environment/agents/adapters/cursor/skills/l9-skill-gateway/SKILL.md`,
`environment/agents/adapters/cursor/validate_skill_projection.py`,
`.cursor-plugin/plugin.json`, `environment/skill-adapters/SKILL_ADAPTER_ROOTS.yaml`.
Doctrine: `skills/AUTONOMY_MANIFEST.yaml`, `skills/l9-plan-simple/SKILL.md`,
`rules/23-l9-skill-routing.mdc` (+ generated RULES-MANIFEST.*, llm-rules
projection), `AGENTS.md` (append-only amendment),
`environment/agents/adapters/claude-code/settings.template.json` + `.claude/settings.json`
(**severed** — both are byte-identical to the merge base; see below).
Gates: `.pre-commit-config.yaml`, `.github/workflows/governance-self-check.yml`, `Makefile` (append-only).
Tests: `ops/skill_routing/tests/{test_characterization,test_registry,test_materialize,test_receipt,test_session_locator,test_scale}.py`,
`skill_routing_cases.json`, `environment/agents/adapters/cursor/tests/{test_before_submit_router,test_skill_projection}.py`,
`environment/agents/adapters/claude-code/tests/test_cursor_skill_router.py`.

## Claude Code preservation (boundary of this plane)

**Claude Code is intentionally outside this plane's boundary.** Everything above
— the gateway, registry v2, materialization, scoped receipts — is Cursor-side,
and none of it may change how Claude Code behaves.

This build initially crossed that line. Cursor and Claude Code share `skills/`
and `AUTONOMY_MANIFEST.yaml`, so moving `l9-plan-simple` to `auto_invoke` — done
purely so the Cursor `plan` route could reach it — propagated through the
generators and dropped the skill's `"user-invocable-only"` override from
`.claude/settings.json` and `settings.template.json`. A skill the corpus marks
user-invocable-only became model-invocable on Claude Code, inside a PR about
Cursor virtualization. That is a Claude Code behavior change riding in another
surface's change set.

**Severed.** The tier move was never required: `explicit_only` primaries are
already routable through `hint_allowed: true`, the pattern eleven other routes
use (`repo_sync_ff`, `pr_analysis`, `issue_remediation`, …). The `plan` route now
carries `hint_allowed` plus a `required_any` gate of discriminating planning
phrases, so `retrieve_candidates` admits it and `_hint_gate` passes it through
on a solid hit. Routing still resolves to `l9-plan-simple` with the same
supporting skill; only `source` changes from `route` to `explicit_hint` — the
correct authority level for a skill whose own doctrine is that Build is the
user's press.

Restored to the merge-base state: `skills/l9-plan-simple/SKILL.md`
(`disable-model-invocation: true`) and the `AUTONOMY_MANIFEST.yaml`
`explicit_only` tier entry, with `l9-plan-simple` removed from
`claude_routing.primary_skills` — no `explicit_only` skill appears there, so
`composition_role` returns to `general`. Both Claude settings files and both
registry mirrors were regenerated, never hand-edited.

| check | command | result |
|---|---|---|
| Claude settings diff vs merge base | `git diff 051c63c..HEAD -- .claude/settings.json environment/agents/adapters/claude-code/settings.template.json` | **empty** |
| Claude skill set + tier map vs merge base | 56 skills both sides, per-skill `invocation` / `disable_model_invocation` / `skillOverrides` compared | **identical, 0 differing entries** |
| routing | `pytest ops/skill_routing/tests` | 83 passed, 33 subtests |
| projection | `validate_skill_projection.py` | `native=1 canonical=56 registry=56` PASS |
| activation | `validate_skill_activation.py` | PASS |

Three routing fixtures move `expected_source` `route` → `explicit_hint`;
`expected_primary` and `expected_supporting` are unchanged.

**The contract and its mechanical gate are not in this PR.** The Claude Code
Preservation Contract (CC-001..010, V-CC-001..005) and its validator are owned
by **PR #518**, opened separately for that purpose; this PR carries only the
sever. The tier promotion itself, if wanted, is owned by **PR #512** ("Promote
five read-only/guidance skills to `auto_invoke`"), where it is a deliberate,
separately reviewed decision rather than a side effect. #513 previously carried
#512's `SKILL.md` frontmatter hunk for merge-cleanliness; it no longer does.
