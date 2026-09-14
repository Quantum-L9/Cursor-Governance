# PATHS-PROPOSAL - per-skill `paths` scoping

`paths` is optional. When set, the skill surfaces only while the agent is
working with matching files. Unset means the skill is always eligible and the
agent routes on `description` alone.

**The asymmetry that matters:** a wrong glob is worse than no glob. An
unscoped skill costs ~5 lines of discovery metadata. A wrongly-scoped skill is
invisible exactly when you need it. Default to unscoped; scope only where the
trigger is genuinely a file type.

Of 45 live skills: **17 recommended for scoping**, **28 deliberately left unscoped**.

## Recommended for `paths`

| skill | proposed paths | rationale |
|---|---|---|
| `l9-api-smoke-testing` | `**/api/**, **/routes/**, **/*router*.py, **/*controller*.py` | Route-bound. |
| `l9-architecture-decision-records` | `docs/adr/**, docs/decisions/**` | ADR-bound. |
| `l9-aws-secrets` | `ops/secrets/**, **/*.env*, **/secrets/**` | Secret-registry-bound. Verify against .cursorignore so it never reads real values. |
| `l9-ci-ops` | `.github/workflows/**, Makefile, .pre-commit-config.yaml` | Triage is config-bound; broaden only if it must fire on log text. |
| `l9-code-graph-rag-mcp` | `graph/**, **/*graph*.py` | Graph-layer-bound; verify against 97-graph-* rule globs so the two agree. |
| `l9-dag-authoring` | `pipeline/**, workflows/**, **/*dag*.yaml, **/*dag*.py` | DAG artifact-bound. |
| `l9-e2e-blocker-resolution` | `**/e2e/**, **/*.spec.ts, playwright.config.*` | E2E suite-bound. |
| `l9-kubernetes-deploying` | `k8s/**, **/kustomization.yaml, **/*deployment*.yaml, **/*.helm.yaml, charts/**` | Manifest-bound. |
| `l9-prompt-engineering` | `prompts/**, **/*prompt*.md` | Prompt-artifact-bound. |
| `l9-python-tdd-with-uv` | `**/*.py, pyproject.toml, uv.lock` | Python TDD only matters with Python files in context. |
| `l9-repo-index` | `reports/repo-index/**` | Index-output-bound. |
| `l9-setting-up-ci` | `.github/workflows/**, .gitlab-ci.yml, Makefile` | CI config-bound. |
| `l9-setting-up-terraform` | `**/*.tf, **/*.tfvars, **/.terraform.lock.hcl` | Terraform-bound. |
| `l9-skill-compiler` | `skills/**` | Operates on skills. |
| `l9-update-agent-docs` | `AGENTS.md, docs/**, README.md` | Doc-bound. |
| `l9-update-command` | `commands/**` | Operates on commands. |
| `l9-wire-skill-into-repo` | `skills/**, .cursor-plugin/plugin.json` | Operates on skill wiring. |

## Deliberately unscoped

Do not add `paths` to these. Each is invoked by intent, conversation state, or
terminal output - none of which are file-path detectable.

| skill | why unscoped |
|---|---|
| `l9-auditing-performance` | Same - intent-driven audit. |
| `l9-auditing-security` | Should be able to fire on intent during any review. Do not scope. |
| `l9-bounded-autonomy` | Autonomy policy. |
| `l9-chat-extraction` | Conversation-driven, not file-driven. |
| `l9-cli-optimization` | Broad. |
| `l9-code-analysis` | General-purpose. |
| `l9-code-maintenance` | Repo-wide sweeps. |
| `l9-component-verification` | Intent-driven verification ladder. |
| `l9-context7-docs` | Docs lookup, triggered by unknown API not by path. |
| `l9-end-session` | Session lifecycle. |
| `l9-forge` | Velocity mode, invoked explicitly. |
| `l9-gap-analysis` | Target-state driven. |
| `l9-gmp-protocol` | Protocol-level. |
| `l9-governance-symlinks` | Leave unscoped. Runs when links are broken - file context is irrelevant, and it already sets disable-model-invocation. |
| `l9-governance-wiring` | Intent-driven via /wire. Scoping would hide it. |
| `l9-graphiti-memory` | Memory subsystem is intent-driven. |
| `l9-harvest-pipeline` | Pipeline-driven. |
| `l9-incident-response` | Must fire on intent during an incident. Never scope. |
| `l9-inspect` | Operates on code not yet in the repo - paths would defeat it. |
| `l9-issue-remediation` | Issue-driven. |
| `l9-monitoring-terminal-errors` | Fires on terminal output, not files. Never scope. |
| `l9-plan` | Planning precedes file context by definition. |
| `l9-pr-remediation` | PR-driven, fires after make pr. |
| `l9-recursive-optimization` | Meta. |
| `l9-repository-renovation` | Repo-wide. |
| `l9-structured-reasoning` | Reasoning mode. |
| `l9-ui-operator` | Fires when APIs are insufficient - not path-detectable. |
| `l9-ynp` | Meta/next-action. |

## Verification requirement

Three of the scoped proposals overlap existing rule globs. Confirm they agree,
because a skill and a rule disagreeing about the same path set is drift:

- `l9-code-graph-rag-mcp` vs `97-graph-engine-architecture` / `97-graph-layer-boundary`
- `l9-ci-ops` and `l9-setting-up-ci` vs `71-ci-cd-pipeline`
- `l9-python-tdd-with-uv` vs `20-lang-python` and `25-python-dora-header`

Also check `l9-aws-secrets` against `.cursorignore`. Scoping it to
`**/secrets/**` and `**/*.env*` means the skill activates near real secrets;
the ignore file must prevent the agent from reading their contents.
