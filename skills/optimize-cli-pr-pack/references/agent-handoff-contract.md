# Agent Handoff Contract

## Goal

Transfer executable state, not a narrative diary.

## AGENT_HANDOFF.md required sections

- mission and locked objective;
- repository and worktree identity;
- base ref, branch, commit or patch digest;
- completed changes by subsystem;
- bottleneck ownership, baseline, candidate measurement, and improvement;
- public behavior and compatibility notes;
- validation executed with evidence locations;
- deployment readiness and exact remaining human steps;
- unresolved blockers, risks, and `UNKNOWN` values;
- files intentionally excluded;
- next executable action;
- external limits that must not be bypassed;
- stop conditions and prohibited scope expansion.

## NEXT_AGENT_TASK.json required fields

```json
{
  "objective": "string",
  "status": "PR_READY | READY_WITH_HUMAN_STEP | BLOCKED",
  "repository": "string",
  "base_ref": "string",
  "branch": "string",
  "pack_manifest": "MANIFEST.json",
  "next_action": "string",
  "validation_entrypoint": "string",
  "deploy_entrypoint": "string",
  "blockers": [],
  "unknowns": [],
  "do_not": []
}
```

The next action must be executable and singular. Do not use vague language such as "review everything" or "finish deployment."
