---
name: Seed doc functional upgrades
overview: Catalog 3–5 functional (not cosmetic) upgrades for every ranked Quantum-L9/.github seed document, then execute the highest-leverage waves on a new branch from .github origin/main so default seed hardens L9, stops red PRs, and lets agents ship without asking.
todos:
  - id: w0-baseline
    content: "Lock .github origin/main SHA; stack on #58 if open; Program Lock bind; new branch from that tip"
    status: completed
  - id: w0-seeder-policy
    content: "Shrink ALL_CATEGORIES: drop LICENSE, FUNDING, on-org-update; dependabot Actions-only; collapse duplicate issue templates; stack-detect Python lint dest"
    status: completed
  - id: w0-contributing
    content: Rewrite CONTRIBUTING.md to live activation + make pr (delete v2 .cursor/rules|skills|commands symlink ritual)
    status: completed
  - id: w1-python-skip
    content: "Mirror #58 on l9-lint-test.yml: detect Python manifests, skip jobs, rename Test Suite, no unpinned pip"
    status: completed
  - id: w1-gov-caller
    content: governance.yml job-level permissions for both jobs; preflight v1 tag SHA
    status: completed
  - id: w2-gov-pack
    content: Fill sdk_policy; add agent/l4 profile; ship Semgrep identity maps; JSON-in-YAML seed preflight
    status: completed
  - id: w2-analysis
    content: Stack-select Semgrep configs; governance-pack-missing check; prefer Core analyze-semgrep reusable
    status: completed
  - id: w3-codeowners-pr
    content: Path-scoped CODEOWNERS; agent/chore PR template variant; labels default to org-sync not seed
    status: completed
  - id: w4-prove
    content: Extend test-build-seed-payload.js + validate-starters.sh; make validate / pr-check; update l9-setting-up-ci pointers
    status: completed
isProject: false
kernel_pass:
  bound_path: seed_doc_functional_upgrades_757455bf.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T17:20:00Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Stamp kernel_pass so the next editor is not the first to fail G_PLAN_KERNEL_PASS"
      - "Keep this plan's existing todos and body; do not reopen landed work from this stamp"
      - "Do not mix #374 end-of-file-fixer exclude into this corpus pass"
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-08-29T17:20:30Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Align with issue #377 and the #376 G_PRECOMMIT_CONFIG plus kernel_pass precedent"
      - "Leave docs/plans/_TEMPLATE.plan.md exempt via PLAN_SKIP_PREFIXES"
      - "Do not edit .pre-commit-config.yaml in this cluster"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T17:21:00Z
    body_sha256: "6190c8d9d881dd6d6109c477bd2ddc3fbab272da96ca236072056221e5eec89c"
    deltas:
      - "G_PLAN_ETC and G_PLAN_EITHER_OR stay clean after this stamp"
      - "Canonical body_sha256 is the post-stamp file hash with sha fields zeroed"
      - "Do not mark status executable while the checker still fails"
---

# Seed-document functional upgrades

Mission: turn the org seed corpus into a stack-aware L9 instantiation pack. Each ranked document gets 3–5 **behavioral** upgrades (gates, skip-safety, authority, autonomy). No wording-only edits.

**Baselines (immutable):**
- Cursor-Governance workspace HEAD `6440800201ede7991f3e63eeebfd9b4eed085bf7` (local; `origin/main` is `fda7f5fe…` — do not mix WIP).
- Quantum-L9/.github `origin/main` `17f2d5be583a78317711c8ba9c751a5eea634722`. Stack on open [#58](https://github.com/Quantum-L9/.github/pull/58) (`fix/seed-ci-safe-pack`) when still open (`PR_STACK=auto`); else branch from that SHA.
- New branch from `.github` `origin/main` (KERNEL/pack landing). Do not edit Cursor-Governance product files except the skill/doc pointers named below.

**Depth:** standard (`route_plan.py`). **code_in_scope:** true. **autonomous_merge:** false.

```text
this plan
  → @environment/program-execution (Blueprint → Program Lock → Controller)
  → @autonomy (subordinate lease)
  → PE adapter cursor-foreground
```

Live run after confirm: `make -C "$HOME/.cursor-governance" campaign INTENT=<this-plan>`. Program lease is authoritative. Do not free-form mutate from markdown.

---

## First-order leverage (do these once)

Shared causes, not 18 local patches:

1. **Seeder policy is the control plane.** [`ops/build-seed-payload.js`](https://github.com/Quantum-L9/.github/blob/main/ops/build-seed-payload.js) `ALL_CATEGORIES` ships drop-ranked files. Change default categories + add stack detect. Every later document upgrade inherits it.
2. **Skip-safe callers.** #58 fixed Node `cache:` / `Test Suite` collision. Python [`l9-lint-test.yml`](https://github.com/Quantum-L9/.github/blob/main/l9-ci-pack/workflows/l9-lint-test.yml) still always runs ruff/mypy/pytest and names a job `Test Suite`.
3. **CONTRIBUTING teaches forbidden wiring.** [`templates/community-health/CONTRIBUTING.md`](https://github.com/Quantum-L9/.github/blob/main/templates/community-health/CONTRIBUTING.md) still says clone Cursor-Governance and symlink `.cursor/rules|skills|commands` — that is CANONICAL_LAW v3 **forbidden**. Agents who follow it create a second governance tree.
4. **Empty governance knobs.** [`quality-thresholds.yaml`](https://github.com/Quantum-L9/.github/blob/main/l9-ci-pack/governance/quality-thresholds.yaml) `sdk_policy: ""` means no threshold gate. Pack looks complete; CI is not.
5. **`on-org-update.yml` force-pushes with `git add -A`.** Violates worktree isolation and `make pr` doctrine; writes tokens for a no-op when `sync_ci_from_pack.py` is absent.

---

## Per-document functional upgrades (3–5 each)

### 1. Governance YAML pack (`.github/governance/*`) — keep

- Bind `quality-thresholds.yaml` `sdk_policy` to the pinned SDK policy file (non-empty). Empty string is a dead gate.
- Add an `agent` / `l4_local` profile in [`execution-profiles.yaml`](https://github.com/Quantum-L9/.github/blob/main/l9-ci-pack/governance/execution-profiles.yaml) whose `allowed_events` cover `workflow_dispatch` + local `make pr-check`, so bounded autonomy uses the same resolver as CI.
- Ship Semgrep identity/policy maps (Cursor-Governance#276 added these locally; pack does not). One identity → one finding.
- Make `promotion-policy.yaml` `approval_required` encode *who* (CODEOWNERS team), not a boolean agents cannot satisfy.
- Seeder preflight: refuse to write the pack unless every YAML parses as JSON-in-YAML (`json.loads`). Today a comment in a "YAML" file kills resolve at consumer CI.

### 2. Biome contract (`biome.json`, `.biomeignore`, `.editorconfig`) — keep

- Seeder already missing-only on `biome.json`. Add a **replace-forbidden** test: different `$schema` → keep consumer file.
- Append generated-path excludes (`GENERATED_PATH_PREFIXES` / `.l9/**`) in the stock includes so seed does not fail Biome on receipts.
- Do not invent a second `biome.json`. Extra excludes only via append to `files.includes` (skill already says this; seeder must enforce).
- Editor: seed extensions only; never `settings.json` (IDE profile owns it).
- Optional: `biome ci` path-filter input so PRs scan changed files, not the whole tree.

### 3. `l9-analysis.yml` — keep

- Replace inline `pip install semgrep` with Core `analyze-semgrep.yml` reusable (already on Core `docs/templates/`). One hop, no floating major.
- Auto-select `--config` from stack (`p/python` vs `p/javascript`+`p/typescript`) instead of always all three.
- If `.github/governance/` is missing, publish one blocking check `governance-pack-missing` and skip Semgrep — agents get a remediable signal, not a mysterious resolve crash.
- Stable check-run name (`L9 Analysis`) so required-status mapping is one string.
- Keep `checks: write` only on publish (already). Do not widen.

### 4. `.vscode/extensions.json` — keep

- Seed Biome always (JSON).
- Add Ruff recommendation only when Python manifests exist (stack-aware).
- Add `unwantedRecommendations` for ESLint/Prettier when Biome owns JS/TS/JSON.
- Do not seed `.vscode/settings.json`.
- Prefer `install_ide_profile.sh` class merge over a raw overwrite of consumer extensions.

### 5. `SECURITY.md` — keep

- Advisory URL must be **this repo** (`$GITHUB_REPOSITORY/security/advisories/new`), not always `Quantum-L9/.github`. Wrong inbox is a functional miss.
- Machine-readable severity/SLA block (YAML frontmatter) for bots and `gov-violation` routing.
- Split: vulnerability → advisory; conduct → CODE_OF_CONDUCT; CI seed failure → `ci-failure.yml`.
- Preflight: fail seed if a consumer already has a competing SECURITY.md (doc already forbids a second one).
- Contact_links in `ISSUE_TEMPLATE/config.yml` must use the same advisory URL pattern (one SSOT).

### 6. `l9-lint-test-node.yml` — keep (post-#58)

- Detect package manager from lockfile (`pnpm-lock.yaml` / `yarn.lock` / `package-lock.json`), do not hardcode `npm`.
- Enable `setup-node` cache only when that lockfile exists (omit the key otherwise).
- Drive `enforce-biome` from a repo variable or governance file, not a committed `false` that never flips.
- Export expected required contexts (`Biome …`, `Type Check`, `Node Test Suite`) so a seeder/script can set branch protection.
- Do not re-seed over a customized Biome-only file (already in `isStockUnsafeNodeWorkflow`).

### 7. `l9-lint-test.yml` (Python) — stack

- Detect `pyproject.toml` / `requirements.txt`; skip lint/test jobs when absent (mirror #58).
- Rename job `Test Suite` → `Python Test Suite` (required-context collision).
- Stop `pip install -e .` / unpinned `pytest-*` fallbacks; toolchain only via `install-consumer-ci@v2`.
- Seeder: write this file only when Python manifests exist.
- Coverage threshold stays consumer `env:`; default 0 remains advisory.

### 8. `governance.yml` caller — keep

- Add **job-level permissions** for both `pr` and `issue` jobs (callee write scopes). Permission validation runs before `if:` skip — partial grant still startup_fails (existing WIP diagnosis).
- Pin `@v1` and add preflight `git ls-remote` SHA check against recorded v1.
- Never `secrets: inherit` blank; named secrets only if a callee needs one.
- Default caller `strict`/advisory must match pack `rule-modes.yaml` (no silent blocking on first seed).
- Do not seed a second `governance.yml` over a customized caller.

### 9. `CODEOWNERS` — keep

- Stop seeding `* @Quantum-L9/platform` on every path (review friction, false required-reviewer). Path-scope: `.github/`, `infra/`, `SECURITY.md`, `CODEOWNERS` only.
- Keep skip-if-root-CODEOWNERS (already in `buildSeedPayload`).
- Validate team slugs live at seed time; unresolvable owner makes the rule inert.
- Allow a consumer overlay the seeder never touches (e.g. `CODEOWNERS` exists → skip).
- Blast-radius extra reviewer (`cryptoxdog`) only on those paths, not `*`.

### 10. `pull_request_template.md` — optional

- Ship an **agent/chore variant** that `make pr` / auto-seed writes so Enforce-PR-Policies does not fail generated PRs.
- Machine-fill Evidence from `.l9/pr/gate-receipt.json` or the Actions run URL (Cursor-Governance already prefill-capable).
- Auto-check Risk=Low + `n/a — because` on Gates for docs-only / seed PRs.
- Generate Changes-by-intent from `git diff --name-only` in the publish path.
- Keep the human template for non-agent PRs; do not make humans fill agent fields.

### 11. `labels.yml` — optional

- Default: **do not seed** the file. Org `sync-labels-all.yml` already fans labels without a consumer PR.
- If kept: drop `.github`-only `area:*` labels from the consumer copy (ci-templates, org-profile, ci-self).
- Add `deps` (dependabot.yml references it; missing label is friction).
- Replace only when consumer file is byte-identical to previous stock (same pattern as Node caller).
- Pack CI: yamllint `commas` on this file (regression for #58).

### 12. `CODE_OF_CONDUCT.md` — optional

- Enforcement action = open `gov-violation.yml` (or Security Advisory for confidential), not "mention @platform".
- Reporter privacy path distinct from public issues.
- Contact = resolvable CODEOWNERS team, not a slack-style mention in markdown.
- Missing-only (already). Do not overwrite a consumer CoC.
- Keep Prettier-safe structure (#58); no further prose work.

### 13. `CONTRIBUTING.md` + `SUPPORT.md` — optional (CONTRIBUTING is currently harmful)

- **Delete the v2 symlink ritual.** Replace with live activation: sessionStart hook, `l9-governance` plugin, `.cursor-commands` consumer-only, **no** `.cursor/rules|skills|commands` directory symlinks.
- Add "How an agent ships": L4 local commits → kernels → `PR_REMEDIATE=0 make pr`. No raw `git push` / `gh pr create`.
- SUPPORT: route CI failures to `ci-failure.yml`; security to SECURITY.md; law questions to CANONICAL_LAW.
- Do not tell contributors to clone Cursor-Governance *into* the consumer workspace root.
- Drop SUPPORT from default seed if `config.yml` contact_links cover the same routes.

### 14. ISSUE_TEMPLATE set (9 files) — trim

- Delete duplicates: `bug_report.yml` vs `1-bug.yml`, `feature_request.yml` vs `2-feature.yml`. Keep the numbered chooser set + `ci-failure` + `gov-violation` + `config.yml`.
- Add a `seed-ci-failure` form (repo, SHA, failing check name) so a red auto-seed is a ticket, not a chat.
- Agent-fillable fields: `repository`, `sha`, `check_url`.
- `blank_issues_enabled: false` stays.
- `config.yml` contact_links stay the only extra; do not add a fourth security URL.

### 15. `dependabot.yml` — drop from default (or shrink)

- Default seed: **github-actions only** (SHA-pin freshness). No pip/npm unless a lockfile exists.
- `open-pull-requests-limit: 2`.
- Label `deps` only if that label exists (or stop labeling).
- Groups stay minor/patch; no major auto-PRs.
- Align with the standing "close Dependabot noise" policy.

### 16. `on-org-update.yml` — drop from default until real

- Do not seed until `sync_ci_from_pack.py` is in the pack and only updates **replaceable stock** dests.
- If kept: **forbid** `git add -A` and `git push -f`. Pathspecs + no force-push.
- Publish via consumer `make pr` / equivalent, not raw `gh pr create`.
- `contents: write` only after a proven diff; start `contents: read`.
- Dispatch payload lists dests; ignore customized files.

### 17. `FUNDING.yml` — drop

- Remove from `ALL_CATEGORIES` / community-health loop.
- Do not seed empty comment files.
- Sponsors belong on the org profile, not 40 consumer PRs.
- Preflight: refuse empty FUNDING dest.
- No consumer workflow should require this file.

### 18. `LICENSE` — drop

- Remove from default seed. License is a legal choice.
- Repo-template may ship one for *new* repos; seeder must not plant LICENSE on existing trees (even missing-only).
- Prefer GitHub repo `license` property / SPDX, not a copied file.
- Never overwrite.
- CODEOWNERS must not churn on LICENSE template edits.

---

## Execution envelope (when Build / campaign runs)

- **Writable:** Quantum-L9/.github `l9-ci-pack/**`, `templates/**`, `ops/build-seed-payload.js`, `ops/test-build-seed-payload.js`, `ops/sync-org-files.sh`, `workflow-templates/l9-v2-*.yml`.
- **Cursor-Governance (pointers only):** [`skills/l9-setting-up-ci/SKILL.md`](skills/l9-setting-up-ci/SKILL.md) default category list; no `CANONICAL_LAW.md` rewrite.
- **Forbidden:** force-push, `secrets: inherit` widen, invent `biome.json`, seed LICENSE/FUNDING, Core `docs/templates` overwrite unless a follow-on Core PR is cut so `sync-v2-starters.sh` cannot regress #58 + this pack.
- **Quality gate:** `node ops/test-build-seed-payload.js` && `bash ops/validate-starters.sh` on .github; `make pr-check` if that repo grows a Makefile gate. Cursor-Governance pointer PR: `make pr-check`.
- **Idempotency:** seeder missing-only + replaceable-stock predicates; re-run must not clobber custom Node/Biome/CODEOWNERS.

## Architecture impact

Seeder becomes stack-aware (detect `package.json` / `pyproject.toml` / `requirements.txt`). Default category set shrinks. Callers stay consumers; Core still executes. Follow-on: patch `l9-ci-core` `presets/typescript` + `docs/templates/l9-lint-test.yml` so the next `make sync-core` does not wipe skip-safety.

## Stress and disconfirm

- If most Quantum-L9 repos are Python-only, seeding skip-safe Node/Biome is still useful (JSON). If they have **no** JSON, Biome is idle — still not red.
- If `* @platform` CODEOWNERS is load-bearing for org rulesets, narrowing paths will drop required reviewers — verify rulesets before cutting `*`.
- If Core sync runs before Core is patched, pack regresses. Treat Core follow-on as a hard dependency of "done", or pin pack and refuse sync until SHAs match.
- Blast radius: next org seed / auto-seed-new-repo. Rollback: revert the .github PR; consumers keep missing-only files already written.

## Out of scope

- Re-opening the 42 closed seed PRs in this plan (re-seed after pack merge is a later campaign).
- Merging .github #58 (human / `/l9-pr-remediation`).
- Cosmetic markdown, emoji, reflow except CONTRIBUTING (functional rewrite).
- C1/VPS, Infisical values, new GitHub PAT.
- Changing Cursor-Governance `CANONICAL_LAW.md` or `AGENTS.md` body (append-only / protected).

## Doc / root surface

- Cursor-Governance: update `l9-setting-up-ci` "Prefer seeder" category list to the new default. Root files: N/A (no new root file; no AGENTS fold).
- .github: `l9-ci-pack/README.md` must state stack detect + dropped dests (functional contract, not prose).

## Convergence

`status: fill` until JSON validates and this projection is built. After campaign: green .github PR, tests prove dropped dests absent from default payload, Python caller skip-safe, CONTRIBUTING no longer mentions `.cursor/rules` symlinks.

## Execute via PE + autonomy

After plan confirm: emit `PLAN_DOCUMENT` JSON → `skills/l9-plan/scripts/validate_plan_document.py` PASS → `render_plan_pe_autonomy.py` into `docs/plans/` (machine store). Then `make campaign INTENT=<plan>` from a clean .github worktree on `origin/main` (or #58 tip). Autonomy packet must not widen Task Card ceilings. `autonomous_merge: false`.

**YNP (single next play):** confirm this plan, then merge or stack [#58](https://github.com/Quantum-L9/.github/pull/58) and run wave 0 (seeder default-category shrink + CONTRIBUTING rewrite). That removes the most red-PR mass per line changed.
