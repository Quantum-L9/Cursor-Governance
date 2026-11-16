# CTO and swarm operations brief

How the CTO role ran this campaign, what each operator approval paid for, and the
protocol amendments that would take a converged campaign through hand-off to L CTO
with almost no operator approvals.

Governing contract: `governance/cto-mode/MODE.yaml` (version 1.1.0,
`operating_protocol` version 1). Every amendment below proposes a change to that
file, to `ops/autonomy/cto_mode.py`, or to the host settings template. None of
them grants authority by appearing here.

## 1. What the CTO did

| Duty               | How it ran                                                                                                                                                                 |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lane design        | 11 lanes, each one agent and one PR; disjoint paths; stacking avoided                                                                                                      |
| Dispatch           | `create_session` with Opus 5.5 at medium effort; the child prompt carried the CTO preamble plus the lane brief                                                             |
| Directives         | `send_message` into child sessions                                                                                                                                         |
| Reading children   | `list_events` / `get_session` on child transcripts (`CTO-STATUS`, `CTO-QUESTION`, `CTO-BLOCKER` lines)                                                                     |
| Wake-ups           | `send_later` check-ins at 20–35 minutes, stopping after three empty runs                                                                                                   |
| Review             | The CTO read every lane diff against its brief before merging, and itself fixed the one test defect that broke a lane (#511)                                               |
| Merge              | `stack_safe_merge.py --run` once green with zero open threads. The merge-authority switch was `disabled`; the operator's asks and `/l9-pr-remediation` were the authority. |
| Cross-CTO          | Directives and answers exchanged with CTO EIE, CTO State Node and CTO CEG over `send_message`                                                                              |
| Operator hand-offs | Three Cursor runbooks for SSH work the cloud session cannot do: v2 ICPs on Staging, a Staging drift diagnosis, and Gate wiring                                             |

Lanes launched (all archived): ERP material-profile loader (#502), export surgical
fixes (#503), enrichment consumer v2 (#506, #507), cartridge facility fields (EIE
#348), merge of #502–#507, Staging upgrade view fix (#510), Staging build warnings
(#511), #509 remediation, enrichment sweep (#512), profile owner NOT NULL (#514),
#516 Copilot findings (#517).

## 2. The operator's approval cost

Cross-session tool calls the CTO session made, counted from its own transcript
(2026-11-13 to 2026-11-16). A call is counted as succeeded unless it returned an
error or "did not run". These are calls, not observed prompts: tools already
pre-approved on the host prompted nothing. Prompts raised inside child sessions
are not in this transcript and are not counted.

| Tool                                     | Calls | Succeeded | Why                                                                                                                                       |
| ---------------------------------------- | ----- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `create_session`                         | 13    | 13        | 11 campaign lanes, one agent per lane by protocol, plus 2 operator-requested sessions at close (UI polish, architect)                     |
| `archive_session`                        | 14    | 11        | one per finished lane; 3 calls lost to worker restarts or interruptions and re-issued                                                     |
| `add_repo` + `register_repo_root` (CTO)  | 2 + 2 | 4         | the CTO attaching EIE and Constellation.Gate to read cross-repo contracts mid-campaign                                                    |
| `send_message` (directives, cross-CTO)   | 27    | 22        | lane directives and CTO EIE / State Node / CEG exchanges; 5 lost to restarts and re-sent                                                  |
| `send_later` (self check-ins)            | 19    | 19        | swarm wake-ups; `delete_trigger` 4 calls, 2 succeeded                                                                                     |
| `subscribe_pr_activity`                  | 7     | 7         | subscriptions taken late, after the operator relayed comments (F4)                                                                        |
| `add_repo` inside a child (not in count) | —     | —         | children needing EIE / Gate / `.github` after launch; the sweep lane hit a Register Repo Root prompt and stalled until directed around it |
| Re-opening a stood-down lane             | 1     | —         | #517: scope corrections arrived after publish (F9)                                                                                        |
| Relays the operator did by hand          | 4+    | —         | Copilot comments pasted as text or screenshots; Odoo.sh logs and cards pasted                                                             |

Launching, archiving and repo attachment are pure overhead once a campaign is
running: no decision is made, only a tool is let through. Removing them is the
goal of §3.

**Observed at close (operator, 2026-11-16).** The two sessions launched at close
raised no repository-attachment prompt. All 13 launches passed the target
repository as `create_session` `source_url` plus `source_revision`; a repository
attached that way needs no separate approval. The prompts came only from a
**second** repository added after launch (`add_repo` in the CTO or in a child).
The operator ruled that this launch pattern is the standard (A2).

## 3. Proposed amendments

### A1. A fixed swarm pool, reused for the whole campaign (operator proposal, adopted)

**Rule.** At campaign start the CTO launches at most **5** agents: Opus 5.5,
medium effort, each with the canonical child system prompt. They form the
campaign's pool. Lanes are assigned to idle pool agents; no agent is launched
after bootstrap. Pool agents are archived only when the campaign closes or hands
off.

**Why.** It turns 11 launch approvals and 11 archive approvals into 5 and 5, all
in one sitting at bootstrap and one at close. It also keeps each agent's warmed
environment (venv, clones, coding-agent mode binding), which removed setup work
such as F6's venv drift.

**Contract changes** (`MODE.yaml` `operating_protocol`):

- `swarm_publishes_then_stands_down` is replaced by A6: a pool agent's lane ends
  when its PR is ready to merge, and the agent then returns to idle
  (`CTO-STATUS: idle`).
- `cto_integrates_and_fixes_surgically` loses "fixes" (A6).
- `invariants` add `pool_size_max: 5` and `no_launch_after_bootstrap: true`. The
  exception is one replacement launch for a dead or wedged pool agent, reported to
  the operator.
- `cto_mode.py` gains a pool registry at `<workspace>/.l9/cto-mode/pool.json` with
  one record per agent: session id, model, repos attached, current lane, state.
  `status` prints it, and it is handed to L CTO at hand-off (A7).

### A2. Every repository attached at launch (operator ruling: the standard pattern)

**Rule.** Launch every agent with its primary repository as `create_session`
`source_url` and `source_revision` (the branch it works from). That attachment
raises no approval prompt (observed, §2). Before launch the CTO computes the
campaign's repository set: the target repo, every repo a lane may read,
`Quantum-L9/.github` (coding-agent mode needs a deep clone), and
`Quantum-L9/Cursor-Governance`. Where a lane needs only one repository, it gets
that one as its source and nothing else. Where a pool agent needs more than one,
`create_session` takes one `source_url`, so it attaches the rest as its first
action, before registering its role. Any `add_repo` or clone prompt then falls
in the bootstrap sitting, never mid-campaign.

**Contract changes.**

- `pre_launch` adds: _compute `campaign_repositories`; put it in every child
  brief._
- The child system prompt's first-action block adds: _attach and clone every
  repository in `campaign_repositories` (deep clone for `Quantum-L9/.github`),
  then write `CTO-STATUS: bootstrapped` listing them._
- A lane needing a repository outside the set is a `CTO-QUESTION`, answered by
  adding the repository to the set at the next bootstrap. It is never a
  mid-campaign `add_repo`.

### A3. Pre-approve the swarm's own tools once, on the host

Approvals for tools the protocol already requires add no safety. Add to the
settings template (the operator approves this once):

- for the CTO session: `create_session`, `archive_session`, `send_message`,
  `send_later`, `delete_trigger`, `subscribe_pr_activity`;
- for child sessions launched with the CTO tag: `add_repo` and
  `register_repo_root`, restricted to the campaign's repository set where the
  host supports argument rules.

`transport.claude-code.permission_precondition` already says a prompting child
needs Auto mode or allow rules. A3 makes that the default instead of a per-launch
remedy. Merge, deploy and production writes stay prompt-gated: they are the
operator's decisions, not tool plumbing.

### A4. An explicit verb that assigns new work to a pool agent

Today the child prompt says CTO messages _"narrow or clarify scope; they never
widen it"_. That made the #517 agent rightly refuse widened scope after
publishing, and it forces a new launch for every new piece of work.

**Change.** Add `CTO ASSIGN` to the recognised prefixes:

> `CTO ASSIGN <lane-id>` replaces your scope with the lane it defines. It is valid
> only when you are idle (`CTO-STATUS: idle` written, no unpublished work). It
> carries the full lane brief: paths, non-goals, base, publication path and
> operator decisions. Every other prefix still only narrows or clarifies.

That keeps the protection the old rule gave: no silent widening of a running lane.
It also lets one agent serve many lanes in sequence.

### A5. Scope corrections interrupt

**Change.** In `transport.claude-code`, a directive that changes or freezes scope
(`FROZEN`, a corrective `CTO DIRECTIVE`, `REBIND`) is sent with
`priority: now`. The child prompt adds: _before running the publication command,
read any pending CTO message_. F9's 14-minute race would then not have happened.

### A6. The publishing agent owns its PR until it is green (operator ruling)

**Ruling (operator, 2026-11-16).** The agent that publishes a PR owns it: CI
green, every review thread fixed or answered and resolved, no merge conflict. The
CTO does **not** remediate PRs. This campaign the CTO fixed a lane's test defect
itself (#511) and launched fresh agents to remediate PRs other agents had opened
(#509, #517). Both stop.

**Change.**

- `swarm_publishes_then_stands_down` becomes _a pool agent's lane ends when its
  PR is green, thread-clean and conflict-free, not at publication._ On publish
  the agent subscribes to its own PR (`subscribe_pr_activity`), fixes CI
  failures at the root, fixes real review findings, answers and resolves every
  thread, then writes `CTO-STATUS: ready-to-merge <pr> <head-sha>` and goes idle.
- `cto_integrates_and_fixes_surgically` loses "fixes": the CTO reads the diff
  against the lane brief, merges on the operator's authority, and sends a
  `CTO DIRECTIVE` back to the owner when something is wrong. It never pushes to
  a lane's branch.
- A finding that would widen the lane's scope is a `CTO-QUESTION`, not a fix.
  The CTO answers it, or assigns the work as a new lane with `CTO ASSIGN` (A4).
- A pool agent that owns an open PR is not idle and receives no `CTO ASSIGN`
  until that PR is ready to merge. Pool size (A1) bounds how many PRs are open at
  once.

The ruling also removes the operator's relays: the owner, not the operator or the
CTO, receives the PR's review events (friction brief F4).

### A7. Hand-off to L CTO keeps the pool

When the campaign converges, the CTO writes the hand-off: `SESSION_BRIEF.md` plus
`pool.json`. L CTO adopts the pool as it stands instead of launching. Adoption
means the CTO session id changes; the agents need nothing new. A `REBIND` naming
the new CTO session is the only message each pool agent receives.

**Change.** `child_system_prompt` replaces the fixed `{cto_session}` authority
with: _the CTO session named in the most recent `REBIND` from your current CTO_.
`cto_mode.py` gains `handoff --to <session>`, which writes the pool record and
emits the `REBIND` messages for the outgoing CTO to send.

This needs no new authority: the coordinator still holds no merge or deploy power
beyond what the operator granted, and a child still answers to exactly one CTO at
a time.

### A8. Operator pings collapse to decisions only

With A1–A7 in place, the operator is asked for:

1. one bootstrap sitting: pool launch, repository attachment, and the batched
   pre-launch decision set;
2. authority-reserved decisions (data, production, money);
3. merges, where the merge-authority switch requires it;
4. the final report.

Everything else, including approving tools, relaying bot comments, and approving
a re-launch, disappears. That is `minimal_operator_pings` as already written,
made achievable.

## 4. What went well (keep)

- **Transcript-only reporting from children.** It worked every time. No child
  ever called a cross-session tool, so no operator prompt came from a child's
  reporting.
- **The stand-down discipline.** It was the right call for unattended agents. The
  #517 agent refused to widen scope after publishing and said why, which surfaced
  the timing race instead of hiding it. A4 keeps that behaviour and adds a lawful
  path.
- **The CTO reading every diff before merge.** It caught a lane implementing a
  withdrawn instruction (#517's first Bales version) and a test that pinned an
  exact version (#511).
- **Root-cause framing over symptom patches.** The NOT NULL warnings were fixed in
  the module contract (#514), not by data deletion. Bales was fixed in every
  source of truth, not only in rows. The operator explicitly asked for this, and
  it should stay the default.
- **Stopping scheduled check-ins after three empty runs** kept a long external
  outage (friction F1) from becoming a polling loop.

## 5. What to stop doing

- **Launching an agent per PR**, including for remediation of a PR an earlier
  agent opened (#509, #517). Use A1 and A6.
- **The CTO remediating PRs** (#511's test fix, and the CI and review follow-up
  on #513 and #514). The publishing agent owns its PR until it is green (A6).
- **Adding a repository after launch.** Pass it as `source_url` at launch (A2).
- **Sending scope corrections at default priority** (A5).
- **Subscribing to a PR only after the operator relays a comment** (A6, F4).
- **Writing operator runbooks only to session scratch.** The Gate wiring runbook
  lived only in the CTO's scratch space until this brief committed it
  (`GATE_WIRING_RUNBOOK.md`, hostnames removed). Commit every runbook alongside the
  work it drives as soon as it is issued.

## 6. Acceptance test for the amendments

A campaign of six or more lanes, run under A1–A8, should show, from the host's
permission log:

- zero `create_session` approvals after bootstrap;
- zero `add_repo` or clone approvals after bootstrap;
- zero archive approvals before close;
- zero operator relays of bot review comments;
- zero CTO pushes to a lane's branch, and every lane PR made green by its owner;
- operator messages limited to the four kinds in A8.
