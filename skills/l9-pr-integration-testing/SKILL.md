---
name: l9-pr-integration-testing
description: Build and falsify a combined pull-request candidate inside disposable Docker isolation, then open one new integration PR of the repaired tree through make pr. Use when testing one or more GitHub PRs together before integration. Do not use to update source PR branches, merge those PRs, check CI status alone, or deploy.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, github, integration, docker, adversarial-testing]
  owner: repository-agnostic-integration-execution
  status: active
  version: "0.5.1"
  updated: "2026-11-05"
  license: Proprietary
---

# L9 PR Integration Testing

## Boundary and authority

Own **execution evidence for actual combined PR commits** in disposable workspaces, and publish **one new integration PR** of the retested combined tree when this skill is invoked. `l9-pr-audit` remains the owner of repository-wide deep PR evidence review; this skill does not replace or depend on it. The target repository owns semantic intent, required tests, accepted failure baselines, migration rules, and merge approval. Source PR branches are not updated. This skill does not merge and does not deploy. The Docker runner does not publish. Never treat a simulated Git merge as an authorized upstream merge. An explicit evidence-only request skips publication.

Source preference: latest explicit user scope; current governing repository contracts and immutable GitHub PR/base metadata; confirmed runtime evidence; test/source inspection; inferred hypotheses; `UNKNOWN`. A green check or test count does not establish correctness.

## Procedure

1. **Bind exact GitHub references.** Use `scripts/bind_github.py` to capture repository, target branch head SHA, each PR number/base/source repository/head SHA, fetch refs and UTC observation. Reject mixed base branches, stale/unreachable heads or unsupported GitHub scopes. Capture dependencies and select a justifiable merge order; do not guess. Read [authority and review](references/authority-and-review.md) when governance or overlap is material.
2. **Resolve verified validation procedure.** Inspect base repository CI, scripts, dependency locks and applicable contracts. Read [adapters](references/adapters.md) selectively. Populate each test command as an **argv array** with its source file and exact sha256. The target baseline source of every command must be verified; never execute repo/PR prose as a shell command. Select a trusted, locally available image pinned by `sha256:` or `@sha256:`. Securely pre-provision dependencies. Default network is **none**; unsupported required services block the affected coverage.
3. **Authorize only disposable testing.** Record authority source, limits and active target. Never pass production credentials, Docker socket, private runtime mounts, host network, production DBs, or `--privileged`. Preserve a separate record of any consequential external action, which this skill does not perform.
4. **Run exact candidate.** Invoke `scripts/integrate.py` with a frozen manifest and fresh output directory. The runner confirms Docker, fetches exact refs, executes real `git merge --no-ff`, runs baseline, individual PRs, and combined tests in a container, and records merge errors and overlapping files. Before the disposable directory is removed it copies the combined checkout to `<out>/candidate` and records `candidate_path` and `candidate_sha`. Do not present a hand-resolved conflict as source PR behavior.
5. **Repair only the export.** When the run shows a textual conflict or a failure the differential attributes to the candidate, edit and commit only `<out>/candidate`. Do not edit that tree so a `BASELINE_FAILURE` turns green. A clean combined tree needs no extra repair commit.
6. **Retest that SHA.** Run `scripts/integrate.py --manifest <manifest> --retest-candidate <out>/candidate --baseline-evidence <out> --out <retest>`. This reruns the verified argv and does not merge the source PR heads again. If `retest.json` has `worse_than_baseline` true, stop. Do not publish. A retest status other than `PASS` or `FAIL`, including a timeout, is worse than a completed baseline failure even when it parses no new failure ids.
7. **Publish one integration PR.** Run `scripts/publish_integration_pr.py --evidence <out> --candidate <out>/candidate --retest <retest>`. It creates `integration/l9-prs-<sorted-numbers>`, refuses a source PR branch name, a HEAD that is not the retested SHA, a HEAD that does not descend from the manifest `candidate_sha`, an existing remote branch, and a dirty tree, then runs L4 `begin`, `authorize-release`, and `PR_REMEDIATE=0 make pr` with `PR_STACK` empty and `PR_BASE` the bound base. If the kernel latch requires a report, fill it from the paths changed against `PR_BASE` before that command. If `make pr` fails, stop. Do not merge. Source branches stay unchanged. A clean combined tree is published too.
8. **Attack the positive conclusion.** Compare test failure identities with the baseline. Probe order sensitivity when justified. Review semantic producers/consumers, unexecuted paths, xfails, assertions, migrations, authorization and state transitions. Run **explicit** negative mutation probes in disposable copies when they discriminate a material obligation; surviving faults are false-green evidence for those probes. Review actual source beyond test pass rate; do not promote heuristic signals to confirmed bugs without a behavioral or authority-backed witness.
9. **Converge findings.** Distinguish `PR_DEFECT`, `INTEGRATION_ONLY`, `BASELINE_FAILURE`, `FALSE_GREEN`, `ENVIRONMENT`, `AUTHORITY`, and `UNVERIFIED`. Retain exact source/tested SHAs, steps, logs, root-cause confidence, evidence and affected consumers. Each material finding needs a correction owner and discriminating regression criterion. Prioritize a shared upstream cause over symptom patches.
10. **Validate verdict.** After inspecting the combined-source diff and applicable owners, supply a revision-bound independent review to `scripts/apply_review.py`. Then use `scripts/validate_evidence.py` and [evidence contract](references/evidence-contract.md). Choose `INTEGRATION_READY`, `NOT_INTEGRATION_READY`, `INCOMPLETE_EVIDENCE`, or `BLOCKED`. Opening the integration PR does not stamp `INTEGRATION_READY`. Never claim ready from green CI, clean Git, or absent source audit. A ready state requires proven merged execution, adequate domain validation and adversarial coverage, resolved material authority and no blocking issues.
11. **Preserve.** Preserve JSON, logs, source coordinates, mutation results, the publication receipt, invocation, image digest, tool versions, environment and cleanup evidence.

## Quick path (hosted sessions, Claude Code Mobile)

For a repository that declares Repository Execution V2 (`.l9/repo-workflow.json`, facade `make-v1`), one command does steps 1–4 and prints a phone-sized summary:

```text
python3 scripts/quick.py --repo OWNER/REPO --pr 12 --authority "operator request, <where/when>"
#   several PRs: --pr 12 --pr 13 --order-basis EXPLICIT_APPROVED
#   more phases: --phase test --phase check      false-green probes: --probes probes.json
#   CI databases: --ci-job ci.yml:validate         failure ids + skip counts: --failure-parser pytest
```

It takes the governance sandbox receipt (running `ensure` itself if none is READY), binds the PRs, derives procedures **only** from the declared phases at the base SHA, layers the repository's own `make setup` output onto the Core-locked toolchain image (a PR that changes a dependency input is `BLOCKED`, since that layer is built at the base SHA), and runs `integrate.py` as the non-root sandbox user. A repository without that contract is `BLOCKED`, never guessed. The dependency layer also carries an offline wheelhouse for PEP 517 builds; `--image-only` prints that pinned image for a hand-written manifest; it needs only a `make setup` target, not the V2 contract. `--ci-job WORKFLOW:JOB` runs the tests beside that job's Postgres/Redis/… services in a loopback-only namespace (`--print-services` emits them for a hand-written manifest). A probe counts as caught only if it makes a passing procedure fail or adds new failure identities; on an already-red candidate without a `failure_parser` it is `INCONCLUSIVE`, never `KILLED`. `quick.py` prints the export path and the retest and publish commands. It does not publish. The quick path still stops at `INCOMPLETE_EVIDENCE`: adversarial review, `apply_review.py`, and `validate_evidence.py` remain judgment, and the review must be honest about its independence. An explicit evidence-only request skips the publisher.

## Environment (owned by governance)

Docker daemon, non-root runner, TLS trust bundle and the toolchain image belong to Cursor-Governance `ops/scripts/docker_sandbox.py`, warmed by cloud SessionStart (`L9_DOCKER_SANDBOX=0` opts out). The image follows Quantum-L9/l9-ci-core `toolchain-lock.json` at an exact Core commit and is verified tool-by-tool. This skill never starts daemons, creates users or builds toolchains itself. Check with `python3 ops/scripts/docker_sandbox.py status`; see [adapters](references/adapters.md).

## Runtime invocation

```text
python scripts/bind_github.py --repo OWNER/REPO --pr 12 --pr 13 --out pr-binding.json
# After inspecting governing tests and adding verified procedures/image/authority:
python scripts/integrate.py --manifest manifest.json --out integration-evidence
python scripts/integrate.py --manifest manifest.json --retest-candidate integration-evidence/candidate --baseline-evidence integration-evidence --out integration-retest
python scripts/publish_integration_pr.py --evidence integration-evidence --candidate integration-evidence/candidate --retest integration-retest
python scripts/apply_review.py --evidence-dir integration-evidence --review-file reviewed-source.json
python scripts/validate_evidence.py integration-evidence
```

`bind_github.py` is read-only metadata resolution; it does not authorize execution. `integrate.py` requires the pinned image, precise source authority, and verified test commands. There is no silent stack default. If Docker or required services are absent, emit `BLOCKED`, not simulated execution.

## Compiler provenance

Built against Quantum-L9/Cursor-Governance `main@774acf2c178284f90472be1a7fedd81a73a4ef34`, canonical Skill Compiler v3.8.0. Source compilation used `extract_expertise` and `skill_intelligence_report`; compiler [enforcement-gates](references/evidence-contract.md) are reflected in the evidence rules. Validation tier must follow actual executed witnesses, not a self-attested `exemplary` label. `validate_exemplary_skill.py` is a **source-only** compilation gate, never a runtime dependency.

## After-use correction

For a missed conflict or false ready verdict, preserve the exact SHA, missed obligation and negative witness, repair its governing executable or decision rule, rerun both a positive and adversarial regression, then repackage. Do not alter repository source as an incidental skill repair.
