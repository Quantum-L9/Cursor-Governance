---
name: l9-setting-up-ci
description: set up a GitHub Actions CI/CD pipeline with linting, testing, type-checking, and deployment steps. use when bootstrapping CI for a repo or adding lint/test/type-check/deploy stages to GitHub Actions.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, ci, github-actions, pipeline, devops]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
---

# Setup CI (GitHub Actions)

## Purpose

Bootstrap or extend GitHub Actions CI/CD: detect project stack, create `.github/workflows/ci.yml`, add lint/test/typecheck/build stages, optional matrix and deploy jobs.

## Core Contract

| Step | Output |
|------|--------|
| Detect | Stack from manifest files |
| Scaffold | `ci.yml` with checkout + setup + cache |
| Quality | lint, typecheck, test, build jobs |
| Optional | matrix, deploy, status badge |
| Secrets | GitHub Settings only — never in YAML |

## Authority Order

1. Explicit user stack, branch names, and required gates.
2. Existing `.github/workflows/` — extend, do not duplicate conflicting workflows.
3. Repo package scripts (`npm run lint`, `make pr-check`, etc.).
4. This skill's steps below.
5. `Unknown` — ask before adding deploy jobs or secret names.

## Steps

1. **Detect the project structure** — check for `package.json` (Node.js), `requirements.txt` / `pyproject.toml` (Python), `go.mod` (Go), or monorepo tools like Turborepo.

2. **Create `.github/workflows/ci.yml`**

   For a Node.js project:

   ```yaml
   name: CI

   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: 20
             cache: npm
         - run: npm ci
         - run: npm run lint
         - run: npm run typecheck
         - run: npm test
         - run: npm run build
   ```

3. **Add type-checking** — if `typecheck` script doesn't exist in `package.json`, add `"typecheck": "tsc --noEmit"`.

4. **Add caching** — the `actions/setup-node` `cache` option handles `node_modules`. For monorepos with Turborepo, add remote caching or `actions/cache` for `.turbo`.

5. **Add matrix testing (optional)** — if the user needs to test across Node versions or OS:

   ```yaml
   strategy:
     matrix:
       node-version: [18, 20, 22]
   ```

6. **Add deployment step (optional)** — if requested, add a deploy job that runs only on `main` pushes, gated by the build job succeeding:

   ```yaml
   deploy:
     needs: build
     if: github.ref == 'refs/heads/main'
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       - run: npm ci && npm run build
       - run: npx vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }}
   ```

7. **Add status badge** — add the workflow status badge to the project README:

   ```markdown
   ![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
   ```

## Notes

- Keep CI fast — run lint and typecheck in parallel using separate jobs if the pipeline is slow.
- Use `npm ci` (not `npm install`) for deterministic installs.
- Store secrets (API keys, deploy tokens) in GitHub repository settings, never in the workflow file.

## Resource Map

No `references/` folder — workflow templates and notes live in this file. For PlasticOS repos, align with existing `ci.yml` rather than replacing — load `l9-ci-ops` for triage after setup.

## Validation

Workflow MUST use deterministic installs (`npm ci`, not `npm install`). Third-party actions SHOULD be version-pinned. Deploy jobs MUST gate on build success and target branch. No secrets in committed YAML.

## Failure Handling

- Unknown stack → inspect manifests; ask user if ambiguous.
- Missing test/lint scripts → add scripts to package manifest or document manual steps.
- Existing CI conflict → merge into single gate workflow; do not create duplicate PR checks.
- SHA-pin policy required → follow repo rule (e.g. PlasticOS `86-ci-github-actions`).
