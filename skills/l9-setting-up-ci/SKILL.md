---
name: l9-setting-up-ci
description: activate governed L9 CI from the org seeder or l9-ci-core stamp. never invent ci.yml or biome.json. use when bootstrapping CI, activating l9-ci-core, adding Biome, or adding lint/test/type-check stages.
paths: ".github/workflows/**, biome.json, .biomeignore, .editorconfig, .vscode/extensions.json"
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, ci, github-actions, biome, l9-ci-core, seeder]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-08-15
---

# Setup CI (L9 seeder + stamp)

## Purpose

Activate the org-owned CI surface. Agents **distribute** locked callers and the
locked Biome contract. They do **not** invent `.github/workflows/ci.yml`,
`biome.json`, ESLint, or Prettier.

| Stack | What to install |
|-------|-----------------|
| JS / TS (`package.json`) | `l9-ci-pack` Node path: Biome + tsc + tests |
| Python (`pyproject.toml` / `requirements.txt`) | `l9-ci-pack` Python path: ruff + mypy + pytest |
| Both | Both pack workflows; Biome still owns JS/TS/JSON |

## Core Contract

| Step | Output |
|------|--------|
| Detect | Stack from manifests. Do not ask for formatter choice. |
| Prefer seeder | Org `Quantum-L9/.github` already fans out `l9-ci-pack` (missing-only). |
| Else stamp | Clone `l9-ci-core` and run `presets/typescript/stamp.sh`. |
| Never invent | No hand-authored `ci.yml` or `biome.json`. |
| Editor | After `biome.json` exists, `install_ide_profile.sh` owns `.vscode/settings.json`. |

## Authority Order

1. Explicit operator instruction (stack, required checks, `enforce-biome`).
2. Existing `.github/workflows/` — extend; do not add a second lint owner.
3. Org seeder / `l9-ci-pack` (distribution SSOT for Quantum-L9 consumers).
4. `l9-ci-core` `presets/typescript/` + `presets/python/` (execution contract).
5. This skill.
6. `Unknown` — ask before deploy jobs or secret names.

## Forbidden

- Do not create `.github/workflows/ci.yml`.
- Do not invent, draft, or rewrite `biome.json`. Extra path excludes may only be
  **appended** to `files.includes` after a stamp.
- Do not copy `biome.json` from another product repo and treat it as the contract.
- Do not add ESLint or Prettier as a second JS/TS/JSON owner.
- Do not flip `enforce-biome: true` on a dirty tree.
- Do not mass-run `biome check --write .` unless the operator asked.
- Do not hand-author `.vscode/settings.json` (Cursor-Governance IDE profile owns it).
- Do not put secrets in workflow YAML.

## Steps

### 1. Detect the stack

- **Node / TypeScript:** `package.json` present.
  - `NODE_VERSION` from `.nvmrc`, `.node-version`, or `engines.node`; else `"20"`.
  - `PACKAGE_MANAGER` from lockfile: `pnpm-lock.yaml` → `pnpm`, `yarn.lock` → `yarn`, else `npm`.
  - `HAS_TYPESCRIPT` is `"true"` if `tsconfig.json` exists at repo root.
- **Python:** `pyproject.toml` or `requirements.txt` present.
- If both exist, install both pack halves.

### 2. Prefer the org seeder (Quantum-L9 consumers)

If the repo is in `Quantum-L9` and lacks the pack files, **do not hand-copy**.
Ask the operator to run (or run, if you have org workflow dispatch):

```bash
gh workflow run seed-governance.yml --repo Quantum-L9/.github \
  -f mode=seed -f repo_filter="<repo-name>" -f categories=l9-ci-pack
```

The seeder is **missing-only**. It will add absent files and leave existing
ones untouched. After a seed PR merges, expected JS/TS files:

- `biome.json`, `.biomeignore`, `.editorconfig`, `.vscode/extensions.json`
- `.github/workflows/l9-analysis.yml`
- `.github/workflows/l9-lint-test-node.yml` (SDK Biome job, `enforce-biome: false`)
- `.github/governance/*.yaml`

If those files are already present, stop inventing more CI. Tune only the
`env:` block in the Node lint workflow (`NODE_VERSION`, `PACKAGE_MANAGER`,
`HAS_TYPESCRIPT`).

### 3. Fallback: stamp from l9-ci-core

Use this when the seeder cannot run (outside the org, no dispatch, or you
need the files in this checkout now):

```bash
git clone --depth=1 https://github.com/Quantum-L9/l9-ci-core.git /tmp/l9-ci-core
mkdir -p .github
cp -R /tmp/l9-ci-core/presets/typescript/.github/. .github/
bash /tmp/l9-ci-core/presets/typescript/stamp.sh "$(pwd)"
```

`stamp.sh` copies the locked Biome 2.5.8 contract, `.biomeignore`,
`.editorconfig`, and the `biomejs.biome` extension recommendation. Existing
`biome.json` / `.editorconfig` are kept.

For Python hygiene, copy `presets/python/.github/workflows/l9-lint-test.yml`
(or the pack equivalent) instead of inventing ruff steps.

### 4. Wire package scripts (JS/TS only, only if replacing ESLint)

No `lint` script is required. The SDK Biome job does not read `package.json`.
If `package.json` already has `lint` and the operator asked to point it at Biome:

```json
"lint": "biome check .",
"lint:fix": "biome check --write ."
```

Add `@biomejs/biome` at **2.5.8** (the locked contract version) if you add
those scripts. Do not add ESLint or Prettier.

If `typecheck` is missing and `tsconfig.json` exists, `"typecheck": "tsc --noEmit"`
is allowed. Do not fabricate a `test` script.

### 5. Editor profile

After `biome.json` exists:

1. If this repo is listed in Cursor-Governance
   `environment/ide/exceptions.yaml` → `eslint_owned_repos`, remove it in a
   Governance PR (basename match beats the `biome.json` heuristic).
2. Run `install_ide_profile.sh` from the Governance clone. Do not hand-write
   `.vscode/settings.json`.

### 6. Deploy (optional, only if asked)

Add a deploy job only when the operator requested it. Gate on the lint/test
workflow succeeding and the target branch. Secrets stay in GitHub / Infisical
settings, never in YAML.

## Notes

- `l9-ci-core` executes CI. `Quantum-L9/.github` only distributes callers and
  the locked formatter contract. `l9-ci-sdk` owns the Biome scanner.
- The org seeder replaces a **stock** ESLint `l9-lint-test-node.yml` with the
  Biome caller. Customized Node lint workflows are kept. Do not invent a
  second lint workflow.
- Keep installs deterministic (`npm ci` / frozen lockfiles) in any job you
  touch. Third-party actions stay SHA-pinned.
- Load `l9-ci-ops` for triage after setup, not for inventing a new pipeline.

## Resource Map

| Surface | Path |
|---------|------|
| Org seeder | `Quantum-L9/.github` `ops/build-seed-payload.js`, `ops/sync-org-files.sh` |
| Pack | `Quantum-L9/.github/l9-ci-pack/` |
| TS stamp | `Quantum-L9/l9-ci-core/presets/typescript/stamp.sh` |
| TS workflow | `presets/typescript/.github/workflows/l9-lint-test.yml` |
| IDE class | Cursor-Governance `install_ide_profile.sh` (`biome_default`) |

## Validation

- JS/TS repos have the stamped `biome.json` (or a pre-existing one), not a
  hand-authored substitute.
- Node lint workflow calls `Quantum-L9/l9-ci-sdk/.github/workflows/l9-biome-scan.yml`
  at a full SHA with `enforce-biome: false` unless the operator flipped it.
- No second JS/TS/JSON formatter owner.
- No secrets in committed YAML.
- Deterministic installs in jobs that install dependencies.

## Failure Handling

- Unknown stack → inspect manifests; ask if still ambiguous.
- Seeder skipped a dest because the file exists → keep it, unless it is the
  stock ESLint `l9-lint-test-node.yml` (the seeder replaces that one file).
- Workspace still classified `eslint_owned` after `biome.json` exists →
  confirm it is not listed in `eslint_owned_repos`, then re-run
  `install_ide_profile.sh`.
- SHA-pin policy required → follow the consumer repo rule.
