---
name: l9-mobile-session-hydrator
description: Hydrate ChatGPT mobile L9 sessions from compact packets; preserve anchors, artifacts, constraints, two-way loops, mesh signals, and exhaust without loading full transcript or full kernel stack.
skill_schema: 1
layer: control_plane
role: mobile_session_hydration
status: canonical_draft
version: 1.0.0
---

# L9 Mobile Session Hydrator

## Purpose

Resume L9 sessions in ChatGPT mobile with minimal context and maximum continuity.

## Activation

Use when the user asks to resume, hydrate, continue, recover from drift, compress context, or boot a new mobile chat from prior L9 work.

## Reject

Do not use for trivial one-off answers, non-L9 tasks, or direct build requests with no handoff or hydration need.

## Workflow

1. Read the SessionHydrationRequest or current chat state.
2. Compile a SessionHydrationPacket.
3. Activate only the necessary context slice.
4. Confirm objective, artifacts, boundaries, unknowns, and next action.
5. Capture signals and exhaust during the session.
6. Trigger end-of-session harvester when context pressure rises.
