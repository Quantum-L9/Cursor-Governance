# [CI Pipeline] {{ title }}

<!-- l9-ci-pipeline-signal:{{ repo }}#{{ pr }}:{{ fingerprint }} -->

## Handoff

- Classification: `CI_PIPELINE_SIGNAL`
- Downstream owner: `ci_remediation_agent`
- Source repository: `{{ repo }}`
- Source PR: `#{{ pr }}`
- Observed head: `{{ head_sha }}`
- Owning surface: `{{ owning_surface }}`
- Blocks PR: `{{ blocks_pr }}`

## Root Cause

{{ root_cause }}

## Affected Checks

{{ affected_checks }}

## Evidence

{{ evidence }}

## Reproduction or Observation

{{ reproduction }}

## Why PR Remediation Did Not Repair This

The failure is owned by CI orchestration, infrastructure, policy, or a shared CI surface. The PR remediation Skill is restricted to codebase defects and therefore made no CI-pipeline mutation.

- Repair attempted: `false`
- Repository files modified for this cause: `[]`

## Acceptance Criteria

{{ acceptance_criteria }}

## Non-Actions

- Do not change application or library code merely to bypass this pipeline defect.
- Do not weaken, skip, or rename required checks as a shortcut.
- Do not close this signal until the owning CI surface is repaired and the affected checks pass on the same PR head or an equivalent reproduction.
