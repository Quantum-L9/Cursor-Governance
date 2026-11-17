# Cursor-Governance Cleanup Tracker

Status: ADVISORY / planning only
Source repository: Quantum-L9/Cursor-Governance
Observed main revision: 3384e7546a9aee002d9e99df868ffcd70e74f786
Tracker created: 2026-10-07

## Purpose

Maintain one cumulative source of truth for the Cursor-Governance cleanup campaign so future discussion only needs to state new decisions, refinements, reversals, blockers, or evidence.

## Conversation rule

Do not restate the full cleanup inventory every turn.

Future updates should report only:
- NEW decision
- REFINED decision
- REVERSED decision
- NEW evidence
- NEW blocker
- CLOSED item

The cumulative state remains in `eviction-register.yaml` and `battle-plan.md`.

## Disposition vocabulary

- KEEP: remains owned by Cursor-Governance.
- REFRESH: remains, but current implementation needs alignment/replacement in place.
- CONSOLIDATE: multiple overlapping surfaces become one owner/surface.
- EVICT: ownership moves to another repository.
- ARCHIVE_DISABLE: preserve historical material, remove all active reachability.
- REVIEW: not enough evidence yet to move or retain.
- VERIFY: expected relationship exists, but exact current implementation/location must be confirmed before execution.

## Current headline

Cursor-Governance should become a lean coding/agent governance control plane. Idea lifecycle moves to IdeaOS. Program/campaign execution moves to a new l9-campaign-execution repository. Legacy DAG workflow attempts are archived and fully unwired. GAR is upgraded to the newest lazy-hydrated version and becomes always available to Cursor routing without being force-run on every prompt. All active skills touched by the cleanup are normalized for OpenAI compatibility with an `agents/openai.yaml` sidecar while preserving still-used platform-specific metadata.
