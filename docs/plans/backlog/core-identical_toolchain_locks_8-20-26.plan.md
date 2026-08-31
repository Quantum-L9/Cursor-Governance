---
name: Core-identical toolchain locks
overview: Every repo must use the exact versions already declared in Quantum-L9/l9-ci-core. Do not invent newer pins. Align internal Core drift and downstream copies to those files, then percolate via install-consumer-ci@v2.
todos:
  - id: todo-01-preflight
    content: Re-read Core requirements-consumer-ci.txt and presets/typescript/biome.json at origin/main; record CORE_RUFF/MYPY/PYTEST/BIOME; clone Core and .github outside Website-Bot
    status: pending
  - id: todo-02-core-action-lock
    content: "R1: move existing Core pin strings into install-consumer-ci (do not bump); toolchain-lock.json derived from those files + biome schema; root file becomes -r include"
    status: pending
  - id: todo-03-core-kill-fallbacks
    content: "R1: pre-commit rev = v + CORE_RUFF (v0.16.1 today); delete 0.14.5/1.19.0/8.4.2 fallback; replace unpinned pip; delete Dependabot pip consumer-ci block"
    status: pending
  - id: todo-04-core-tests-docs
    content: "R1: pin-identity tests (pre-commit == pin file); keep test_phase_scope exact set; rewrite consumer-lint-test.md; add tools/publish_consumer_ci_tag.sh"
    status: pending
  - id: todo-05-core-validate-pr
    content: "R1: make agent-check; prove pin file bytes were not upgraded; open Core PR; do not tag yet"
    status: pending
  - id: todo-06-core-retag-v2
    content: "R1 after merge: point v2 at merge SHA; V-TAG curl of v2 pin file equals CORE_* strings"
    status: pending
  - id: todo-07-orgpack-callers
    content: "R2 after v2: pack l9-lint-test.yml uses install-consumer-ci@v2; zero version literals"
    status: pending
  - id: todo-08-orgpack-validate-pr
    content: "R2: V-PACK then open .github PR"
    status: pending
  - id: todo-09-websitebot-align
    content: "R3 from origin/main: @biomejs/biome must equal CORE_BIOME; Dependabot ignore it; no python pin file; no dirty WIP"
    status: pending
  - id: todo-10-gov-align-to-core
    content: "R4: set ruff/mypy/pytest in requirements.txt, pyproject.toml, pre-commit to CORE_* (0.16.2 → 0.16.1 today); Dependabot ignore; drop sdk-wins; skill calls action"
    status: pending
  - id: todo-11-identity-validate
    content: "W4: V-AUTH V-CORE V-TAG V-PACK V-WB V-GOV V-IDENT; fail if any repo lock string != Core authority files"
    status: pending
isProject: false
kernel_pass:
  bound_path: core-identical_toolchain_locks_8-20-26.plan.md
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
    body_sha256: "0e86544fb67fa6e8b27fd41f905d4dba95ed5901b51b7fb4f9dd3257fab05e2e"
    deltas:
      - "G_PLAN_ETC and G_PLAN_EITHER_OR stay clean after this stamp"
      - "Canonical body_sha256 is the post-stamp file hash with sha fields zeroed"
      - "Do not mark status executable while the checker still fails"
---

# Core-identical toolchain locks (no invented versions)

This replaces the prior plan’s lock set. That plan used `ruff==0.16.2` because Governance already had it. **Wrong.** Core is the only authority. Governance must move to Core, not the other way around.

## Authority law (fail-closed)

At execute, re-read these two Core files at `origin/main`. Those strings are the lock. If they differ from this plan’s snapshot, **use the files**, not this snapshot.

- Python SSOT: [`requirements-consumer-ci.txt`](https://github.com/Quantum-L9/l9-ci-core/blob/main/requirements-consumer-ci.txt)
- Biome SSOT: [`presets/typescript/biome.json`](https://github.com/Quantum-L9/l9-ci-core/blob/main/presets/typescript/biome.json) `$schema` (the `2.5.8` in `https://biomejs.dev/schemas/2.5.8/schema.json`)

**Snapshot at Core `0d28395428426853c44825c4645c23ee8ace23b1` (2026-08-17):**

- `ruff==0.16.1`
- `mypy==2.3.0`
- `pytest==9.1.1`
- Biome `2.5.8`

Forbidden:

- Bumping Core to `0.16.2` / `0.16.3` / latest PyPI because it is newer
- Leaving Governance on `ruff==0.16.2` (“already newer”)
- Writing a different ruff/mypy/pytest/biome string in Website-Bot, the org pack, or Governance
- Copying pin files into consumers as a second SSOT (callers only, except Governance local venv which must **equal** Core)

Identity rule: after the program, `ruff`/`mypy`/`pytest`/`biome` version strings that appear as locks in R1–R4 are **character-identical** to Core’s two authority files. V-IDENT fails on any mismatch.

## What is drift today (align TO Core, do not pick a third number)

- Core pin file: `ruff==0.16.1`
- Core pre-commit: `rev: v0.14.5` (internal Core drift — set to `v0.16.1`)
- Core `pr-pipeline.yml` fallback: `ruff==0.14.5` `mypy==1.19.0` `pytest==8.4.2` (delete; install the pin file)
- Core `ruff.toml` comment still says `ruff==0.14.5` (comment only; do not change rule set)
- Governance `requirements.txt` / `pyproject.toml`: `ruff==0.16.2` (change to `0.16.1`)
- Governance pre-commit: `rev: v0.16.0` plus “sdk wins over core” (change to `v0.16.1`; drop that comment)
- Website-Bot `@biomejs/biome`: `2.5.8` (already equals Core schema; keep; Dependabot-ignore so it cannot leave)
- `l9-ci-sdk` biome schema `2.5.5` (follow-on; do not “fix” from this program)

## Percolation (unchanged mechanism)

```mermaid
flowchart TD
  pins["Core requirements-consumer-ci.txt + biome.json schema"]
  action["install-consumer-ci action copies those exact strings"]
  tag["tag v2 after Core merge"]
  pack[".github pack calls @v2 no version literals"]
  wb["Website-Bot biome equals Core schema"]
  gov["Governance ruff/mypy/pytest equal Core pins"]
  pins --> action
  action --> tag
  tag --> pack
  tag --> wb
  tag --> gov
```

Installer lives at `l9-ci-core/.github/actions/install-consumer-ci/` because `$GITHUB_ACTION_PATH` only ships that directory. Pin **values** inside it must be the existing Core pin file, moved or included — not rewritten to a preferred version.

Do not add a new `.github/workflows/*.yml` unless `tests/workflows/test_phase_scope.py` expected set is updated. Retag `v2` via `tools/publish_consumer_ci_tag.sh`. `v2` does not exist yet.

## Repo isolation

Four clones, four branches from each `origin/main`, four PRs. Never mix.

- **R1 Core** — only place the lock is **authored**. Baseline re-resolve; last seen `0d28395428426853c44825c4645c23ee8ace23b1`. Move existing pins into the action; align pre-commit/fallback **to** the pin file. Do not bump the pin file.
- **R2 `Quantum-L9/.github`** — callers only. Zero `ruff==` / `mypy==` / `pytest==` / biome version literals in `l9-ci-pack`.
- **R3 Website-Bot** — new branch from `origin/main` (dirty tree is not the baseline). Biome lock must equal Core `2.5.8`. Dependabot ignore `@biomejs/biome`. No `requirements-consumer-ci.txt`. No WIP files.
- **R4 Governance** — `ruff`/`mypy`/`pytest` in `requirements.txt`, `pyproject.toml`, and `.pre-commit-config.yaml` must equal Core pins (`0.16.1` / `2.3.0` / `9.1.1`). Ignore those three in Dependabot. Skill tells agents to call the action.

## R1 Core work (no version invention)

Create action files by **moving** the current pin file contents:

- `requirements-consumer-ci.txt` inside the action = current root file (`ruff==0.16.1` …)
- `toolchain-lock.json` derived from that file plus biome schema `2.5.8`
- Root `requirements-consumer-ci.txt` becomes `-r .github/actions/install-consumer-ci/requirements-consumer-ci.txt`
- `install.sh` fail-closed; no unpinned `pip install ruff`
- `action.yml` runs `install.sh` from `github.action_path`

Align Core to its own pin file:

- `.pre-commit-config.yaml` `rev: v0.16.1` (from `v0.14.5`)
- Delete `pr-pipeline.yml` else-branch `0.14.5` / `1.19.0` / `8.4.2`
- Replace preset/template `command -v ruff || pip install ruff` with `uses: …/install-consumer-ci@v2`
- Delete Dependabot `pip` / `deps(consumer-ci)` block
- Rewrite `docs/consumer-lint-test.md`: versions are Core-owned; consumers call `@v2`
- Test: pre-commit `rev` == `v` + pin `ruff==`; lock JSON == pin file; `test_phase_scope` still exact-set
- `stamp.sh` **exists** on current main; do not invent a new stamp; do not change `biome.json` schema unless Core’s file already changed

## R2 / R3 / R4 (identical strings only)

- Pack Python workflow: `uses: Quantum-L9/l9-ci-core/.github/actions/install-consumer-ci@v2` after Core `v2` exists. Start R2 only after tag.
- Website-Bot: if `package.json` biome != Core schema, set it to Core’s version and refresh the lockfile **only for that package**. Today it already matches `2.5.8`. Dependabot ignore. No python pins.
- Governance: replace `0.16.2` with Core’s `0.16.1` in both manifests; pre-commit `v0.16.1`; delete “sdk wins over core”; Dependabot ignore `ruff` `mypy` `pytest`.

## Success properties

- **SP-AUTH** Execute log shows the two Core files were read and the four strings recorded before any edit.
- **SP-01** Action pin file at `v2` equals Core’s pre-change pin file (`ruff==0.16.1` unless Core’s file moved).
- **SP-02** `toolchain-lock.json` biome equals Core `biome.json` `$schema` minor (`2.5.8`).
- **SP-03** Core pre-commit `rev` == `v` + pin ruff (`v0.16.1`).
- **SP-04** No stale fallback pins and no bare `pip install ruff|mypy|pytest` in Core workflows/presets.
- **SP-05** Core Dependabot has no `pip` consumer-ci ecosystem.
- **SP-06** Pack has `@v2` caller and no version literals.
- **SP-07** Website-Bot `@biomejs/biome` == Core biome schema version; Dependabot ignores it; no python pin file.
- **SP-08** Governance `ruff`/`mypy`/`pytest` strings == Core pin file; pre-commit matches ruff; Dependabot ignores those three.
- **SP-09** Core `make agent-check`; Governance `make pr-check`.
- **SP-IDENT** V-IDENT: extracted lock strings from R1 action, R3 package.json, R4 requirements/pyproject/pre-commit are identical to the Core authority files. Any extra version is a fail.

## Validation

**V-AUTH (before edits):**

```bash
gh api repos/Quantum-L9/l9-ci-core/contents/requirements-consumer-ci.txt?ref=main --jq .content | base64 -d
gh api repos/Quantum-L9/l9-ci-core/contents/presets/typescript/biome.json?ref=main --jq .content | base64 -d | rg 'biomejs.dev/schemas/'
```

Record `CORE_RUFF`, `CORE_MYPY`, `CORE_PYTEST`, `CORE_BIOME`. All later writes use these variables.

**V-CORE / V-TAG / V-PACK** as before, but greps use `$CORE_RUFF` not `0.16.2`.

**V-IDENT (required):**

```bash
# fail if any written lock != Core authority
test "$(rg -N '^ruff==' "$CORE_ACTION_PINS")" = "ruff==${CORE_RUFF#ruff==}"
# Governance
rg -n "ruff==${CORE_RUFF#ruff==}" ~/.cursor-governance/requirements.txt
rg -n "ruff==${CORE_RUFF#ruff==}" ~/.cursor-governance/pyproject.toml
rg -n "rev: v${CORE_RUFF#ruff==}" ~/.cursor-governance/.pre-commit-config.yaml
# Website-Bot
rg -n "\"@biomejs/biome\": \"${CORE_BIOME}\"" package.json
# Pack has no literals
rg -n 'ruff==|mypy==|pytest==|@biomejs/biome' l9-ci-pack && echo FAIL || echo PASS
```

**V-GOV:** `make pr-check` after the **downgrade** to Core’s ruff. Do not keep `0.16.2` to make a local test green.

## Out of scope

- Choosing a “better” ruff than Core’s pin file
- Stamping `ruff.toml` into consumers
- Mass fan-out PRs
- Pack Node ESLint→Biome rewrite
- `l9-ci-sdk` 2.5.5 follow-on
- Auto-merge / `@main`
- Website-Bot dirty WIP

## Unknowns

- **U-01** Push/tag rights on Core and `.github` — probe at execute
- **U-02** Core pin file may change before execute — use the file, not this snapshot
- **U-03** SDK Biome 2.5.5 — accept_bounded follow-on

## Execute

`@environment/program-execution` then `/autonomy`. `autonomous_merge: false`. Core PR first, tag `v2`, then pack, then Website-Bot + Governance in parallel. Four PRs, never mixed.
