# CI Signal Boundary

## Objective

Separate codebase remediation from CI-pipeline remediation before any edit. This Skill owns codebase repair. It does not own CI pipeline repair.

## Normative Ownership Classes

### CODEBASE_REPAIR

Use only when the failing evidence identifies a defect in source, tests, fixtures, package dependencies, generated artifacts owned by the repository, or other code required for normal runtime behavior.

Examples:

- source type error;
- implementation bug causing a test failure;
- stale test fixture;
- missing import or module declaration;
- formatting or lint violation in source;
- vulnerable dependency that can be safely updated without changing CI policy;
- build failure caused by repository code or package metadata used outside CI.

### CI_PIPELINE_SIGNAL

Use when repair requires changing CI orchestration, CI infrastructure, CI policy, or a shared enforcement surface rather than correcting repository code.

Signal-only surfaces include:

- `.github/workflows/**`;
- `.github/actions/**` and composite actions;
- reusable workflow inputs, outputs, permissions, secrets, and call contracts;
- action versions or SHA pins;
- hosted or self-hosted runner images, labels, capacity, networking, disk, or tools;
- GitHub permissions, OIDC, environments, protected branches, required-check names, merge queue, and check wiring;
- CI-only shell or orchestration scripts whose purpose is running the pipeline;
- centralized CI repositories, SDKs, templates, or global baseline configuration;
- caches, artifact services, package proxies, service containers, external scanners, and third-party outages;
- invalid or contradictory lint/type/test configuration when the needed change alters enforcement rather than compliant code;
- secret absence, credential scope, environment provisioning, or repository settings.

Read these surfaces to diagnose and cite evidence. Never edit them in this Skill.

### HUMAN_DECISION

Use when ownership or intended policy cannot be established without product, architecture, security-exception, legal, or business direction.

### FALSE_POSITIVE

Use when current evidence disproves the signal or the failure no longer exists on the current head.

## Decision Test

Ask in order:

1. Can the failure be corrected by changing normal source, tests, fixtures, or package dependencies without altering how CI is orchestrated or enforced?
2. Would the proposed fix touch a signal-only surface or change policy, permissions, environment, action wiring, check definitions, runner behavior, or shared CI contracts?
3. Does the same source command fail locally for the same code reason?
4. Is the failing behavior specific to CI environment, credentials, services, workflow expression, or reusable workflow contract?

Classify `CODEBASE_REPAIR` only when answer 1 is yes and answer 2 is no. Classify `CI_PIPELINE_SIGNAL` when answer 2 or 4 is yes. Unknown ownership is not permission to edit.

## Mixed Failures

A single failed job may contain multiple root causes. Split it:

- codebase defect -> repair normally;
- CI-pipeline defect -> issue file;
- human decision -> decision record.

Do not let one pipeline symptom contaminate the codebase batch. Do not modify CI merely to expose or bypass a code failure.

## Root-Cause Deduplication

Group symptoms only when they share the same causal mechanism and owning surface. Use a stable fingerprint over:

```text
repo + pr + normalized_owning_surface + normalized_root_cause + affected_check_names
```

One fingerprint equals one issue file. Different causes require different files even when they fail the same job. The same cause appearing in multiple jobs produces one issue file listing every affected check.

## Required CI Signal Record

```yaml
id: CI-001
fingerprint: 64-char sha256
classification: CI_PIPELINE_SIGNAL
title: concise root-cause title
root_cause: evidence-backed causal statement
owning_surface: workflow | reusable_workflow | action | runner | permissions | secrets | oidc | branch_protection | check_wiring | cache | external_service | shared_ci | ci_only_script | policy_config | unknown
affected_checks: []
evidence: []
source_repo: owner/repo
source_pr: 1
blocks_pr: true
repair_attempted: false
repository_files_modified: []
downstream_owner: ci_remediation_agent
issue_file_path: issues/ci-pipeline/<fingerprint-prefix>-<slug>.md
acceptance_criteria: []
```

`repair_attempted` must be false. `repository_files_modified` must be empty. Any violation is a protocol failure.

## Issue File Contract

Render one Markdown file per CI root cause from `assets/ci-pipeline-issue-template.md`. Each file must contain:

- source repository, PR, head, and affected checks;
- root cause and ownership classification;
- redacted evidence and reproduction notes;
- why the PR remediation agent did not repair it;
- suspected owning surface and downstream owner;
- acceptance criteria;
- explicit non-actions;
- stable deduplication marker.

Always include these files in the final tar.gz, whether or not the PR converges. Do not commit them to the PR branch.

## Live GitHub Issue Policy

CI signal files are handoff artifacts, not automatic issues in the consumer repository. Create a live CI issue only when the user explicitly authorizes it and the owning CI repository is independently resolved. Otherwise package the files for the downstream CI remediation agent.
