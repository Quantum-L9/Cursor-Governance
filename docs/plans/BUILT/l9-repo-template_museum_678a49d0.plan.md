---
name: l9-repo-template museum
overview: CANONICAL consolidation (v0+Improve+Leverage+org .github max-pull) for Quantum-L9/l9-repo-template — replaces prior plan copies. Thin Python GitHub Template with verify/sync-ci/rename; maximize Quantum-L9/.github; deprecate golden-repo.
todos:
  - id: l1-bind-pin
    content: Clone museum; freeze Quantum-L9/.github SHA into .l9/ci-pin
    status: completed
  - id: l2-skeleton
    content: Materialize skeleton from inventory; LICENSE from org .github
    status: completed
  - id: l3-force-multipliers
    content: Ship make verify + org-aware sync-ci + bootstrap_rename (+tests)
    status: completed
  - id: l4-ci-once
    content: "Run sync-ci: l9-ci-pack + templates/dependabot.yml + CODEOWNERS.repo"
    status: completed
  - id: l5-green-template
    content: make verify + Actions green; enable is_template; AGENTS CI table
    status: completed
  - id: l6-smoke-deprecate
    content: CP3 throwaway smoke; golden-repo banner; archive after
    status: completed
isProject: false
---

## PLAN: Open l9-repo-template museum (deprecate golden-repo)

**This is the single canonical plan.** Treat prior copies (`…_01a29145` v0-only, `…_23b50202` leverage-only) as superseded once this file is the active plan in the UI.

### Consolidation ledger
| Run | Contributed |
|-----|-------------|
| v0 | Museum target, golden deprecation, Layer A, transplants, milestones |
| Improve | Pack CI, consumer-ci pins, SOURCE_DIR=., no LOAD_PACK, generic AGENTS, inventory, CP3 |
| Leverage | verify / sync-ci / rename, `.l9/ci-pin`, L1–L6 |
| Org pull | Maximize [Quantum-L9/.github](https://github.com/Quantum-L9/.github) — copy non-inheritable; inherit community health |

### Objective
Thin Python GitHub Template at [l9-repo-template](https://github.com/Quantum-L9/l9-repo-template) that pulls **max possible** from [Quantum-L9/.github](https://github.com/Quantum-L9/.github), then deprecate [golden-repo](https://github.com/cryptoxdog/golden-repo).

**Success:** (1) `make verify` / `sync-ci` / `rename` tested (2) CI+dependabot+CODEOWNERS from org `.github` (3) no re-authored inheritable community health (4) Actions green → `is_template` → CP3 smoke (5) golden banner → archive.

### Org `.github` max-pull matrix (locked)

Per [org README](https://github.com/Quantum-L9/.github/blob/main/README.md): community health/PR/issue templates **inherit**; **dependabot is not inheritable**.

| Org surface | Action | Destination |
|-------------|--------|-------------|
| `l9-ci-pack/governance/*` | Copy via sync-ci | `.github/governance/` |
| `l9-ci-pack/workflows/l9-analysis.yml` | Copy via sync-ci | `.github/workflows/` |
| `l9-ci-pack/workflows/l9-lint-test.yml` | Copy via sync-ci (Python) | `.github/workflows/` |
| `templates/dependabot.yml` | **Must copy** | `.github/dependabot.yml` |
| `templates/CODEOWNERS.repo` | **Must seed** (adapt) | `.github/CODEOWNERS` |
| `templates/governance-caller.yml` | Evaluate at L4; skip if redundant | optional |
| `LICENSE` | Copy SSOT | `LICENSE` |
| `CONTRIBUTING` / `SECURITY` / `SUPPORT` / `CODE_OF_CONDUCT` / `FUNDING` | **Inherit** — do not fork | README note |
| `ISSUE_TEMPLATE` / PR template | **Inherit** | README note |
| `workflow-templates/*` (v1) | **Forbidden** | never |
| `rulesets/` `ops/` org `scripts/` `profile/` org workflows | **Out** | org-only |

**sync-ci:** pin = org `.github` 40-char SHA → fetch pack + `templates/dependabot.yml` + `templates/CODEOWNERS.repo` → patch lint-test `env:` only → refuse `@main` / v1 starters / golden workflows. Core only for `requirements-consumer-ci.txt` if pack lacks it.

### Leverage / cuts
Invest once in sync-ci + verify + rename + inventory. Cut golden CI/engine, LOAD_PACK v1, protocol in AGENTS, duplicate org health files, hand-edited YAML.

### Scope
**In:** museum; org max-pull; Gate_SDK/topology only for packaging shapes org lacks; automations; Template flag; golden deprecation.
**Out:** migrating living repos; TypeScript workflow; copier; org rulesets/ops; Gate_SDK product edits.

### Locked defaults
setuptools+uv.lock, py3.12, `l9_example_pkg`; lint `SOURCE_DIR=.` `TEST_DIR=tests/` `COVERAGE_THRESHOLD=0`; deny `engine/` `chassis/` `domains/` etc.

### Pre-Validation
P0 bind museum · P1 inventory org surfaces · P2 freeze org SHA → `.l9/ci-pin` · P3 Gate_SDK pr-check Skipped · P4 museum push Required · P5 golden write Unknown

### Routing
org `.github` → l9-ci-pack + templates → `make sync-ci` → museum; inheritable health → derived repos via GitHub defaults; Gate_SDK/topology → skeleton only; museum → Use template → `make rename` + `make verify`; CI bumps → `make sync-ci`.

### Todos
- **L1** Clone; pin org `.github` SHA
- **L2** Skeleton + org LICENSE
- **L3** verify + org-aware sync-ci + rename (+tests)
- **L4** First sync-ci (pack + dependabot + CODEOWNERS)
- **L5** Green + Template flag + AGENTS CI table
- **L6** CP3 smoke → golden banner → archive

### Checkpoints
CP1 `make verify` · CP2 Actions green + dependabot present · CP3 throwaway rename+verify + `is_template` · CP4 golden banner

### Doc impact
README (3 commands + org source/inherit) · AGENTS generic · ARCHITECTURE org boundary · TEMPLATE_INVENTORY Source column · no CONTRIBUTING/SECURITY copies · golden README at L6

### Final Validation
verify · Actions · is_template · no PacketEnvelope/poetry/sonar · sync-ci idempotent · dependabot from org template · CP3 · honesty labels

### Recommend
Execute L1–L5 after approval; L6 after CP3. Prefer org `.github` over Gate_SDK/golden for every file the org owns.
