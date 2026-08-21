---
name: Rich root agent docs
overview: "Refreshed 2026-08-14 against origin/main@72ff9d4. Same mission: harden l9-update-agent-docs to create/refresh agent quartet + Core-10 + consumer CANONICAL_LAW, then seed l9-repo-template. Do not fork CG law. Do not fight sync-ci community-health files. Do not clobber generated/PE root blocks."
todos:
  - id: audit-bind
    content: "W0: new CG branch from origin/main@72ff9d4 (or then-current tip); re-inventory skill + template checklist; stop_and_replan on SHA drift"
    status: pending
  - id: improve-skill
    content: "Improve.md on skills/l9-update-agent-docs: create-if-absent for quartet + Core-10 + consumer CANONICAL_LAW; preserve generated/PE managed blocks; sync-ci community files are out"
    status: pending
  - id: leverage-skill
    content: Recursive Leverage.md on the skill pack until no material extra-pass gain; single ingress; grounded stubs not empty placeholders
    status: pending
  - id: wire-skill
    content: l9-wire-skill-into-repo if version/triggers/discovery tables change
    status: pending
  - id: apply-template
    content: "Apply upgraded skill in l9-repo-template: seed full root library; enrich from ground truth; README index; leave sync-ci community files untouched"
    status: pending
  - id: harden-sync-ci-fetch
    content: "Harden scripts/sync_ci_from_pack.py fetch(): reject non-https and non-allowlisted hosts (CWE-939)"
    status: pending
  - id: inventory-gate
    content: Update TEMPLATE_INVENTORY.md + inventory_check.py to require agent quartet + Core-10 + consumer CANONICAL_LAW at repo root
    status: pending
  - id: validate-both
    content: "CG make pr-check PASS; template make verify PASS; CANONICAL_LAW is binding-not-fork; sync_ci allowlist closed; community-health files remain sync-ci owned"
    status: pending
isProject: false
---

# Rich Root Agent Docs (Template Bootstrap)

> **Revision (2026-08-14):** same mission, new baseline. Supersedes the 2026-08-12 envelope that locked `fcbd5ed` (#107). That tip is **163 commits** behind `origin/main@72ff9d4` (#148). Do not Build the old envelope.
>
> **Execute via:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter `cursor-foreground`.
>
> **Landing:** new branch from refreshed `origin/main` (KERNEL pack new-branch default). Do not land on dirty `fix/ci-required-contexts-wip-only`.

## Locked decisions (unchanged mission)

- **Library set (B):** agent quartet **plus** readme-dag Core (10) **at repo root**, **plus** consumer `CANONICAL_LAW.md`.
  - **Agent quartet:** `AGENTS.md`, `ARCHITECTURE.md`, `INVARIANTS.md`, `CLAUDE.md`
  - **Core (10)** ([`commands/readme-dag.md`](commands/readme-dag.md)): `ARCHITECTURE.md`, `API_REFERENCE.md`, `DATA_MODEL.md`, `WORKFLOW_GUIDE.md`, `TEST_STRATEGY.md`, `DEPLOYMENT.md`, `MIGRATION_GUIDE.md`, `SECURITY_MODEL.md`, `CHANGELOG.md`, `ROADMAP.md`
  - **Canonical law:** root `CANONICAL_LAW.md` as a **consumer binding** (authority order + pointer to Cursor-Governance SSOT + template-local musts). **Not** a copy/fork of governance [`CANONICAL_LAW.md`](CANONICAL_LAW.md).
  - **Also:** surgical `README.md` index linking the full library.
- **Community health (revised):** `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, issue/PR templates are **sync-ci owned** on `l9-repo-template` (`TEMPLATE_INVENTORY.md` + `make sync-ci`). Do **not** create, rewrite, or delete them. `SECURITY_MODEL.md` is product/security-architecture doc, not org `SECURITY.md`.
- **Managed-block rule (new):** on any existing root file, preserve generated / PE adapter regions:
  - `<!-- BEGIN L9 FORMATTER OWNERSHIP` … `<!-- END L9 FORMATTER OWNERSHIP -->`
  - `<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:* -->` (and matching `# PROGRAM_EXECUTION_ADAPTER_LAYER_V1` in non-md)
  - Do not dump these into the template consumer binding.
- **Stub quality:** every new file ships a grounded minimal contract (purpose, ownership, sections, validation hooks, labeled `Unknown` only where product fill-in awaits `make rename`). Empty / decorative placeholders fail Recursive Leverage `no_placeholders` / `no_scaffolds`.
- **Span (dual-repo):** mutate Cursor-Governance skill first on a clean worktree, then apply it in `Quantum-L9/l9-repo-template` and update inventory gates.
- **Kernel pipeline (kernels stay read-only unless a proven contract gap forces a skill-side fix):**
  1. [`kernels/Improve.md`](kernels/Improve.md)
  2. [`kernels/Recursive Leverage.md`](kernels/Recursive%20Leverage.md) — extra pass adds no material leverage.

## Mission

Make `l9-update-agent-docs` the single ingress for ensuring a rich **repo-root** agent/product doc library exists and stays aligned with ground truth, then apply that skill to `l9-repo-template` so GitHub Template–derived repos start with the full library (quartet + Core-10 + consumer CANONICAL_LAW).

## Immutable baseline (re-verify at W0)

| Field | Value |
|---|---|
| CG tip authority | `origin/main` |
| Locked SHA | `72ff9d4509d831faa43dd76018b704a06a48938b` — Merge #148 `fix/pe-crack-remediation-v1` (2026-08-14 20:38 EDT) |
| Retired lock | `fcbd5ed73f102b9f4f34e28858630b3a434f6085` (#107) — historical only |
| Working tree | **Must be a clean dedicated worktree/branch from that tip.** Current primary `fix/ci-required-contexts-wip-only` is out of envelope. |
| Skill path | `skills/l9-update-agent-docs/SKILL.md` v2.0.2 — quartet refresh **only when files exist**; no create path; no Core-10; no CANONICAL_LAW; no `references/` |
| Skill drift since old lock | #123 frontmatter normalize only — contract gap unchanged |
| CG root docs | `AGENTS.md`, `CANONICAL_LAW.md` (SSOT), `CHANGELOG.md`, `README.md`. Missing product Core-10 / `INVARIANTS.md` / `CLAUDE.md`. **CG is not the seed target.** |
| CG root protection | `AGENTS.md` + `CANONICAL_LAW.md` are `additive_only`. Skill work on CG is pack-only; do not edit those SSOT files. |
| Template (`l9-repo-template` `main`) | Has `README` / `AGENTS` / `ARCHITECTURE` / `CHANGELOG` plus **sync-ci community-health copies**. Missing `CLAUDE.md`, `INVARIANTS.md`, consumer `CANONICAL_LAW.md`, and most Core-10. |
| Template `fetch()` | `scripts/sync_ci_from_pack.py` still raw `urlopen` — no https/host allowlist |
| stop_and_replan | HEAD ≠ locked SHA; Program Lock drift; tip moves mid-flight without rebase policy; dirty overlap into `write_deny` |

## Architect framing

- **plan_class:** `integration_plan` (skill contract + consumer template seed)
- **redesign_allowed:** false
- **follow_on_schema_evolution_separate:** true (WIP plan-schema promotion stays out)

## Root library checklist (union, deduped)

Required at **template** repo root after apply:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `INVARIANTS.md`
4. `CANONICAL_LAW.md` (consumer binding)
5. `ARCHITECTURE.md`
6. `API_REFERENCE.md`
7. `DATA_MODEL.md`
8. `WORKFLOW_GUIDE.md`
9. `TEST_STRATEGY.md`
10. `DEPLOYMENT.md`
11. `MIGRATION_GUIDE.md`
12. `SECURITY_MODEL.md`
13. `CHANGELOG.md`
14. `ROADMAP.md`
15. `README.md` (index links to all of the above)

Present and **out of this library** (do not treat as missing or as a fail): sync-ci community health (`CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`) and org issue/PR templates.

## Success properties (blocking)

1. **SP-skill-create:** Skill creates missing library files from ground truth / labeled `Unknown`, never fabricates CI/hook counts.
2. **SP-skill-refresh:** Existing quartet files get surgical CI/pre-commit/lint/false-positive/skill-table updates; Core-10 + CANONICAL_LAW get create-or-structure-preserve. Generated formatter + PE adapter blocks are byte-stable.
3. **SP-kernel-convergence:** After Improve + Recursive Leverage, an extra full pass finds no material improvement (handoff note).
4. **SP-template-library:** Template root contains the full checklist; `README.md` links every entry.
5. **SP-canonical-law-binding:** Template `CANONICAL_LAW.md` states consumer authority order, points at Cursor-Governance SSOT (not a pasted fork), and lists template-local musts (inventory, sync-ci, rename, no deny-dirs).
6. **SP-inventory:** `TEMPLATE_INVENTORY.md` + `scripts/inventory_check.py` require the full checklist; `make inventory-check` / `make verify` PASS.
7. **SP-sync-ci-community:** Existing sync-ci community-health files remain; this plan does not add a second copy path and does not delete them. `SECURITY_MODEL.md` ≠ `SECURITY.md`.
8. **SP-gates:** CG `make pr-check` PASS for skill changes; template verify PASS after seed.
9. **SP-sync-ci-url-gate:** `scripts/sync_ci_from_pack.py` `fetch()` fail-closes unless URL scheme is `https` and host is in `{api.github.com, raw.githubusercontent.com}`.
10. **SP-stub-quality:** No empty Core-10/quartet/law files; each has purpose + sections + at least one grounded fact or explicit `Unknown` with fill trigger.

## Execution envelope

**Filesystem write_allow**

- CG (new branch/worktree from locked tip): `skills/l9-update-agent-docs/**`, skill wiring surfaces from `l9-wire-skill-into-repo` if version/description changes
- Template (separate clone/worktree): checklist files + `README.md`, `TEMPLATE_INVENTORY.md`, `scripts/inventory_check.py`, `scripts/sync_ci_from_pack.py`

**write_deny**

- CG governance SSOT: `CANONICAL_LAW.md`, `AGENTS.md`, `ORG_INVARIANTS.yaml` (do not edit; do not copy wholesale into template)
- Generated / PE managed blocks on any file
- `kernels/**`
- Creating, rewriting, or deleting template community-health / issue-PR template files
- WIP schema promotion into live `l9-plan` validators
- Config-tier readme-dag files (`ENVIRONMENT_SPEC.yaml`, `NEO4J_ONTOLOGY.yaml`) unless already present
- Landing on the dirty primary clone

**commands allow:** inspect/read, skill pack validators if present, `make pr-check` (CG), template `make inventory-check` / `make verify`, `gh` read + later scoped PR after L4 `authorize-release`

**network:** `named_services_only` (GitHub for template clone/PR)

**autonomous_merge:** true only inside L4 program/plan Build stack after green+mergeable; older open PRs bottom-up first

## Kernel pass order

```mermaid
flowchart LR
  audit[Audit_bind_new_branch] --> improve[Improve_kernel_on_skill]
  improve --> leverage[Recursive_Leverage_on_skill]
  leverage --> wire[Wire_skill_if_needed]
  wire --> apply[Apply_skill_to_template]
  apply --> harden[Harden_sync_ci_fetch]
  harden --> invent[Update_template_inventory]
  invent --> validate[Validate_both_repos]
```

1. **Audit / W0** — new branch from `origin/main`; lock full SHA; inventory missing checklist; map CI/hooks/lint for template.
2. **Improve** on [`skills/l9-update-agent-docs`](skills/l9-update-agent-docs/) — ensure quartet + Core-10 + consumer CANONICAL_LAW; create-if-absent with grounded stubs; surgical refresh; structure-preserve; managed-block + sync-ci rules.
3. **Recursive Leverage** — converge; single ingress; move long templates into `references/root-doc-library.md` if SKILL.md bloats.
4. **Wire** — `l9-wire-skill-into-repo` if version/triggers change.
5. **Apply** inside `l9-repo-template` — seed/enrich checklist; README index; leave community-health files alone.
6. **Harden sync-ci fetch** — https + host allowlist before `urlopen`.
7. **Inventory** — require full checklist in `TEMPLATE_INVENTORY.md` + `inventory_check.py`.
8. **Validate** — CG `make pr-check`; template `make verify`; binding-not-fork; allowlist closed; community files still sync-ci owned.

## Skill contract changes

Update [`skills/l9-update-agent-docs/SKILL.md`](skills/l9-update-agent-docs/SKILL.md) (+ `references/` if needed):

| Tier | Files | Create if absent | Refresh behavior |
|------|-------|------------------|------------------|
| Agent quartet | `AGENTS`, `ARCHITECTURE`, `INVARIANTS`, `CLAUDE` | Yes | Surgical from CI/hooks/lint/skills (existing Steps 2–6). Skip/preserve generated + PE blocks. |
| Core (10) | readme-dag list (overlap: `ARCHITECTURE`, `CHANGELOG`) | Yes at **repo root** | Required headings; fill from ground truth; product specifics as `Unknown` + fill trigger |
| Canonical law | `CANONICAL_LAW.md` | Yes (consumer binding only) | Preserve local musts; never overwrite with dumped CG SSOT; never copy PE/formatter blocks from CG |
| Index | `README.md` | Must already exist in template | Add/keep library index links; do not strip existing product sections |

**CANONICAL_LAW consumer binding must include:**

- Authority order: explicit user > org/governance SSOT at `~/.cursor-governance/CANONICAL_LAW.md` (when wired) > this file’s template-local musts > skills
- Symlink/wiring summary (`.cursor-commands` → governance)
- Template-local musts: inventory allowlist, `make sync-ci` owns workflows **and** community-health files, no deny-dirs, rename via `make rename`
- Explicit **non-goals:** not the governance SSOT; do not duplicate full CG law text

**Explicit skill out:** community health files; Config (2) / User (6) readme-dag extras beyond `README`/`CHANGELOG`/`LICENSE`; PlasticOS domain sections still owned by adapters.

**Do not edit** `kernels/Improve.md` / `kernels/Recursive Leverage.md` unless execution proves a kernel bug.

## Stress / disconfirm

- Empty Core-10 or quartet files → **fail**.
- Pasting full CG `CANONICAL_LAW.md` into the template → **fail**.
- Inventory requires files the skill did not create → **fail**.
- Deleting or rewriting sync-ci `CONTRIBUTING`/`SECURITY`/`SUPPORT`/`CODE_OF_CONDUCT` → **fail**.
- Clobbering formatter-ownership or PE adapter blocks → **fail**.
- `# nosec` on urllib without https+host allowlist → **fail**.
- Seeding Core-10 only under `docs/` → **fail** (repo root is locked).
- Building on dirty `fix/ci-required-contexts-wip-only` → **fail**.

## Sync-ci urllib finding (in scope)

| Field | Value |
|-------|--------|
| Path | `l9-repo-template` `scripts/sync_ci_from_pack.py` (`fetch` → `urllib.request.urlopen`) |
| Tool message | Dynamic URL + urllib `file://` → arbitrary file read (CWE-939) |
| Severity | WARNING |
| Current risk | Low: URLs from fixed hosts + hex pins |
| Chosen fix | Fail-closed scheme+host allowlist inside `fetch()`; no `requests` |

## Rollback

- CG: revert skill/wiring commits on the feature branch.
- Template: revert seed/inventory/sync-ci harden commits; restore community-health only via `make sync-ci` if accidentally touched.
- No force-push. No irreversible ops.

## Out of scope

- Promoting WIP canonical plan schema into live `l9-plan` validators
- Editing kernel bodies for style
- Re-deriving or deleting org community-health files on the template
- Dumping full CG `CANONICAL_LAW.md` / `ORG_INVARIANTS.yaml` into the template
- Seeding readme-dag Config (2) or full User (6) set beyond README index duties
- Changing CG root-file-protection to require Core-10 on Cursor-Governance itself (follow-on)
- PlasticOS adapter rewrite beyond noting adapter still wins for domain sections
- Mixing this landing onto unrelated WIP branches

## Follow-on (separate plan)

- Optional CG local Core-10 + root-file-protection registration for those paths
- Live validator binding for `canonical.schema.plan_document.v1`
- Optional `docs/` mirrors if a future product template wants dual location

## Doc / root surface impact

| Surface | Action |
|---------|--------|
| CG `skills/l9-update-agent-docs/**` | Update (primary) |
| CG root governance SSOT (`AGENTS.md`, `CANONICAL_LAW.md`) | N/A — do not edit |
| Template root library (15 paths) | Create/enrich |
| Template community-health / issue-PR templates | Preserve; sync-ci owned |
| Template `TEMPLATE_INVENTORY.md` + `inventory_check.py` | Require full checklist |
| Template `scripts/sync_ci_from_pack.py` | Harden `fetch()` |
| Template `INVARIANTS.md` / `SECURITY_MODEL.md` | Note sync-ci URL allowlist + security boundaries |

## Convergence

Ready for **Build** when W0 re-verifies `origin/main` (refresh lock if tip moved) on a clean worktree and the envelope above is respected.

Converged when all blocking SP-* have filesystem/quality_gate evidence and both repos’ declared gates PASS.

**Handoff after green+mergeable:** merge this L4 stack; older open PRs bottom-up first.
