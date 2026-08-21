---
name: Bounded Autonomy SOP
overview: "Build a Cursor-primary bounded-autonomy SOP that makes parallel non-dependent work and background PR-poll subagents first-class: main agent continues other work while delegated poll/remediate workers drive PRs to merge-eligible, harvesting PR #40 invariants without autonomous merge."
todos:
  - id: protocol-spec
    content: "Author detailed protocol refs first: parallel fan-out, PR-poll subagent (Task+background), main-continue contract, join/merge, locks/lanes"
    status: pending
  - id: skill-pack
    content: "Create skills/l9-bounded-autonomy SKILL.md that mandates poll delegation + parallel Tasks; wire all references"
    status: pending
  - id: prompt-templates
    content: "Ship copy-paste Task prompt templates for poll worker, mutation lane, read-only lane; include notify contract"
    status: pending
  - id: slash-command
    content: "Add /autonomy with Phase-0 action graph (depends_on, locks, poll_workers) and execute steps that spawn background Tasks"
    status: pending
  - id: rule
    content: "Add agent_requested rule that forbids main-agent CI blocking and requires background poll delegation"
    status: pending
  - id: wire-routing
    content: "Wire AUTONOMY_MANIFEST + claude_routing (explicit-only); rebuild skill-registry.json"
    status: pending
  - id: wire-crosslink
    content: "Cross-link Claude autonomy README, l9-pr-remediation, babysit, end-session, cli-optimization, AGENTS.md"
    status: pending
  - id: worked-examples
    content: "Add references/examples.md with 2 worked campaigns (multi-PR poll + parallel independent fixes)"
    status: pending
  - id: validate
    content: "Validate autonomy runtime untouched; skill-activation + rules-validate; make pr on changed files"
    status: pending
isProject: false
---

# Bounded Autonomy SOP — thickened (Cursor-primary)

See canonical detailed plan: this file mirrors `/Users/ib-mac/.cursor/plans/bounded_autonomy_sop_8bce0bc8.plan.md`.

## Acceptance criteria (from original ask)

1. More autonomy (bounded campaign execution)
2. Parallel non-dependent Tasks in one turn
3. **Especially:** background PR-poll subagents while main continues — main must not block on CI

Protocol B (PR-poll subagent) is the centerpiece: `Task` + `run_in_background: true`, notify-on-state-change, main continues immediately, no `AwaitShell` on poll.

Full protocol A/B/C/D, prompt templates, worked examples, deliverables, and validation are in the plan body above / the 8bce0bc8 file.
