# Thin Command Binding Contract

A command exists to trigger or locate the DAG, not to restate its workflow.

A valid command trigger should contain only discovery metadata, brief usage, the canonical DAG id/path, and the minimal invocation needed by the current command system.

Reject or reduce command files that contain duplicated phase-by-phase workflow instructions, stale `.cursor-commands/workflows/dags/...` repo paths, or a second implementation of validation/registration behavior.

Do not create a command unless requested or already part of the workflow's owned public surface.
