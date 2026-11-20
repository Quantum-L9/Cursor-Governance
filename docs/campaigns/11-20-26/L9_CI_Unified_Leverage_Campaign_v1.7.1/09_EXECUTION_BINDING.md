# Resolved execution binding (2026-11-20)

This file is the launch binding for `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`. It resolves
contradictions inside the v1.7.0 pack and between that pack and the live repositories and host. It
outranks any sentence elsewhere in this pack that it names. It does not admit an ADR or an invariant,
merge a pull request, complete G0, or launch the swarm.

Checked from CTO mode `ACTIVE`, Claude Code cloud session `session_017xwbxvn4RrcFtW27s3aYG4`.
Authority checkout `$HOME/.l9/authority/.github` is non-shallow and its `HEAD` equals `origin/main` at
`c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`. Cited compositions: technical-coordination
`sha256:9c159475edeb9a71b50242f51169675a8badd8a897ea9bf83fdda3eb236c6df4`, architecture
`sha256:ac3b440f654543fc8c3d547b1910041835e86277da636ac9b0d8d36739d4df28`, governance
`sha256:c5d80dbdb7d99eccebdaac663c5f1db8a24252db89b8135205e841d5468d1794`, evidence-provenance
`sha256:3eec77f93453af484e53504a7119938aa34d854f61822e77ed6f09730c2ca1d0`, contracts-conformance
`sha256:e499a076e3f406506a6bbe38208805aa9fea9f92dc22995331f34cc0a49a9ab1`, capabilities-dependencies
`sha256:a42f2987ac439d21b151db242b4bd782c3e591c2786f3a83a35f287e06b7f830`, identity-attribution
`sha256:665c6d8e38d4246842d52042286fc9e53ab3773023a174b88b63f80e567e18f5`, strategic-value
`sha256:cc362f794d51799fa223b3924f50be8aa116ffd8281beae2d697615cd231277b`.

`technical_coordination_role` coordinates bounded work inside existing authorization and grants no
execution, admission, publication or merge. `integration_responsibility` requires evidence of the exact
combined revision. `L9-ADMISSION-001` binds a decision to the exact subject revision, so a pull-request
state or head recorded on 2026-11-19 is not a current fact. `L9-ASSURANCE-001` and `L9-UNKNOWN-001`
keep every unproven item below as Unknown.

## What this chat authorizes

The operator asked for the pack to be inspected and corrected so that it executes without friction once
launched. That authorizes this binding, the lane briefs, and publication of the corrected pack. It does
not authorize the swarm launch, any merge, any vendor or billing change, or a G0 screen answer.

## Unchanged

The eleven invariant statements (`INVARIANTS.yaml`), the three ADR texts and the Core ADR index
(`candidates/adr/`), and the three patches (`candidates/*.patch`) are byte-identical to v1.7.0. So are
`ADRS.md`, `INVARIANTS.md`, `G0_OTHER_VENDOR_CHECK.md`, `audit/ALIGNMENT.yaml` and
`audit/RECURSIVE_ALIGNMENT_KERNEL.md`. The v1.7.0 checksum list is kept as
`audit/SHA256SUMS.v1.7.0`; `SHA256SUMS` covers this revision.

## Live recheck

| Repository | v1.7.0 baseline | Live default-branch head, 2026-11-20 | State |
| --- | --- | --- | --- |
| `Quantum-L9/.github` `main` | `c788b991` | `c788b991f2ed5f670a2d5660a7faa4e1d52f64e3` | unchanged |
| `Quantum-L9/l9-ci-core` `main` | `3579bdc1` | `3579bdc19a7f36973e4f0fe516ea5aa6c5ab9437` | unchanged |
| `Quantum-L9/l9-ci-sdk` `main` | `ab8a2554` | `ab8a25543bf99de4c932f1930841a1e5f2ef2f27` | unchanged |
| `Quantum-L9/Cursor-Governance` `main` | `263216c1` | `a95562c9c4cb22c5c489c989d554415b4e55ef1e` | moved: #1062 merged |
| `Quantum-L9/Enrichment.Inference.Engine` `main` | `29d4eb54` | `e1a61f781d99e18da3f4130fa8017485acdbfa7b` | moved: #364, #363, #362 merged |
| `Quantum-L9/Cognitive.Engine.Graphs` `main` | `90a98637` | `b2150980874180d386221b8b2ffd6cca91880a06` | moved: #508 merged |
| `cryptoxdog/IB-Odoo_19` `Staging` | `0626d949` | `341e45f450209417b9a9cc1d18328c1b77cfbe17` | moved: #552, #553, #555, #556 merged |

Pull requests the pack names:

| Pull request | v1.7.0 says | Live |
| --- | --- | --- |
| [Cursor-Governance #1067](https://github.com/Quantum-L9/Cursor-Governance/pull/1067) | merged | merged (`263216c1`) |
| [Cursor-Governance #1062](https://github.com/Quantum-L9/Cursor-Governance/pull/1062) | OPEN | **merged** 2026-11-20T16:23Z as `a95562c9` |
| [l9-ci-core #281](https://github.com/Quantum-L9/l9-ci-core/pull/281) | OPEN | open, head `faeeda69`, base `5acaf415` (one commit behind `main`) |
| [IB-Odoo_19 #552](https://github.com/cryptoxdog/IB-Odoo_19/pull/552) | OPEN | **merged** 2026-11-20T15:52Z |
| [IB-Odoo_19 #553](https://github.com/cryptoxdog/IB-Odoo_19/pull/553) | OPEN | **merged** (`d5b7378`) |
| [IB-Odoo_19 #556](https://github.com/cryptoxdog/IB-Odoo_19/pull/556) | OPEN | **merged** (`341e45f4`) |
| [Cognitive.Engine.Graphs #508](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/508) | sampled open PR | **merged** (`b2150980`) |
| [Enrichment.Inference.Engine #364](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/364) | sampled open PR | **merged** (`e1a61f78`) |

Open pull requests the pack does not know, all from the sibling campaign
`l9-ci-core-pr-fast-nightly-deep-cto-swarm-v1.1.0` (`docs/campaigns/11-17-26/`) or from governance work:

| Pull request | Head branch | Files that matter here |
| --- | --- | --- |
| [Cognitive.Engine.Graphs #514](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/514) | `agent/fleet-d/ceg-pilot` | `.github/workflows/ci-quality.yml`, `ci.yml`, `Repo.mk` |
| [Enrichment.Inference.Engine #365](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/365) | `agent/fleet-e/eie-pilot` | `.github/workflows/sonarcloud.yml`, `ci.yml`, `pr-pipeline.yml`, `Repo.mk` |
| [l9-ci-core #281](https://github.com/Quantum-L9/l9-ci-core/pull/281) | `agent/fleet-b2/pr-expense-guard` | `.github/workflows/org-ci.yml`, `self-ci.yml`, `tools/pr_expense_guard.py` |
| [.github #274](https://github.com/Quantum-L9/.github/pull/274) | `campaign/l9-org-ci-pr-fast-consumer-verification` | `AGENTS.md`, `Repo.mk`, `ops/validate-starters.sh` |
| [Cursor-Governance #1073](https://github.com/Quantum-L9/Cursor-Governance/pull/1073) | `claude-mobile/bold-shannon-u7r6p4` | `governance/cto-mode/MODE.yaml`, `environment/agents/adapters/claude-code/web/setup.bootstrap.sh` |

`l9-ci-sdk` has seven open pull requests: six Dependabot and #117 `ci(governance): restore drifted
governance files`. None adds an ADR.

## Corrections

Each row states what was found, the evidence, and the sentence it outranks.

| ID | Finding | Evidence | Binding |
| --- | --- | --- | --- |
| B01 | Four pull requests the pack treats as open are merged. | Live recheck above. | Every "OPEN", "reconcile before coding", "do not independently redo" and "pending" sentence about Cursor-Governance #1062 and IB-Odoo_19 #552, #553, #556 is outranked. The obligation is now to verify the merged change's live effect, per T15 and lanes N1 and H1. |
| B02 | #1062 is live, so Cursor-Governance Sonar is dispatch-only now. The old pull-request trigger is already gone. | Commit `a95562c9` message: "Sonar runs only from an admitted apply dispatch". | "Do not turn off the old trigger on static PR evidence" is moot. No hosted Core `mode=apply` run and native Sonar gate on `a95562c9` or later is recorded here, so Cursor-Governance Sonar is `NOT_EXECUTED` until one is observed. New finding T15. |
| B03 | Finding T03 has changed under the pack. | Core #280 (`3579bdc1`) checks out a consumer's declared external repository. CEG `b2150980` carries `.l9/external-checkout.json` pinning `cryptoxdog/IB-Odoo_19@3d721235` and commit `0f601c2` "run the sibling-mapper buyer proof where the consumer is checked out". | T03 is not a work item. Lane F1 records a fresh `Analyze (central Core)` result on CEG `main` and closes it `ALREADY_SATISFIED` or reopens it with that run. |
| B04 | The Odoo rule inventory moved. | `.semgrep/odoo-patterns.yml` at `341e45f4` has 39 `- id:` entries, blob `e92848dc`; fixtures are in `.semgrep/tests/`. | "36 rules", blob `48de124e` and "open #553 changes" are outranked. Lane H1 classifies 39. |
| B05 | Core, SDK, CEG, EIE and `.github` have no `pr` Make target. | Their root `Makefile` is Core's generated `make-v1` facade: `help`, `setup`, `validate`, `check`, `test` only. Core and CEG AGENTS.md say never edit it. | "Each target's verified `make pr`" is outranked by the Publication section below. A lane never adds a `pr` target and never falls back to a raw push. |
| B06 | The pack is addressed to Cursor. The live host is Claude Code cloud. | `get_session`: `environment_kind: anthropic_cloud`. | Transport is `operating_protocol.transport.claude-code`. No interactive browser exists, so each G0 screen is a link plus one navigation step. |
| B07 | A pool agent cannot clone, branch or push `Quantum-L9/.github`. | `cto_mode.py child-prompt`, REPOSITORIES rule. | Every `.github` write (CodeRabbit renderer, Dependabot generator, ruleset evidence) is lane G1 in the CTO session. Lane 3 text that assigns `.github` writes to "native provider owners" is narrowed to that. |
| B08 | The pack's lanes share repositories. Lane 2 and F2 both write Core. F1, F2 and Lane 3 all write CEG. Lane 3, Lane 4, F2 and F3 all write EIE and Cursor-Governance. | `CAMPAIGN.md` §C, `OTHER_TOOLS_EXECUTION.md` Phase B. | The lane table below is the writer map: one pool agent per repository, five slots. Lanes 1 to 4 and F1 to F3 remain concern labels only. |
| B09 | The sibling campaign already owns pull-request test expense. | Open-PR table above. | T09 and T11 are `delegated` to CEG #514, EIE #365, Core #281 and Cursor-Governance #1062. No lane here edits a file those pull requests change for that purpose. A lane that must touch the same file follows the Stacking section. |
| B10 | The EIE half of T10 sits inside a foreign pull request. | `--cov=engine` is at `.github/workflows/sonarcloud.yml:85` on `e1a61f78`; `engine/` does not exist; EIE #365 changes that file and adds `tests/ci/test_sonar_analysis_truthfulness.py`. | Lane F2 does not edit `sonarcloud.yml`. It records whether #365 removes the stale target and, if not, sends that as a `CTO-QUESTION`. |
| B11 | The T01 mechanism is no longer unknown. | CEG `.github/workflows/ci-quality.yml:151-186` at `b2150980`: three branches print a `::warning::` and skip (key absent, token lacks `scan` scope, "container failed to start; skipping scan (infra)"), and the job succeeds. Codecov at `:237-244` has `fail_ci_if_error: false`. | "The ZIP does not preserve the exact catch implementation" is resolved to those lines. Lane F1 re-reads them at its base before editing. |
| B12 | The three candidate patches apply. | `git apply --check` exits 0 for `core-governance-contract.patch` on Core `3579bdc1`, and for `sdk-integration-contract.patch` and `sdk-adr-index.patch` on SDK `ab8a2554`. | The patches are used as written. |
| B13 | No strict schema reads either contract file. | Core: only `tests/governance/test_governance_boundary.py` reads `.l9/governance-contract.yaml`, as substring assertions. SDK: only `tests/architecture/test_version_alignment.py` reads `.l9/integration-contract.yaml`, for `metadata.version`. | "Admissibility under current target validators is unknown" is resolved for the top-level fields `ci_runtime_invariants` and `ci_provider_invariants`. No field remap is needed. The witness tests are still required; a YAML entry is not enforcement. |
| B14 | Core has no `docs/adr/`. Its decisions are dated, append-only `AGENTS.md` sections. | `ls docs/adr` fails on `3579bdc1`; `AGENTS.md` §13 to §24 open with "Decision record for ...". | The frozen paths `docs/adr/0001-*.md`, `0002-*.md` and `docs/adr/README.md` stand. Lane L2 also appends one dated `AGENTS.md` section that points at them and repeats none of their text, so Core keeps one decision trail. |
| B15 | Two different records are called "ADR 0020". | SDK `docs/adr/` ends at 0019, so SDK 0020 is free. `.github` already has `docs/adr/0020-coderabbit-central-config-seeded.md`. | Always write the owner: "SDK ADR 0020" or ".github ADR-0020". |
| B16 | A swarm child cannot start on current Cursor-Governance `main`. | #1073 Problem: the Setup script holds no GitHub credential, the private Cursor-Governance clone fails at Setup, "and the platform refused to start every child". | Launch precondition P1 below. #1073 also changes `MODE.yaml`, so the CTO re-runs `cto_mode.py on` after it merges and renders the child prompt again. |
| B17 | The CTO session runs in `default` permission mode. `launch-spec` gives children `auto`, and a child cannot be more permissive than its parent. | `get_session`: `permission_mode: default`. | Launch precondition P2 below. |
| B18 | Children cannot read an uploaded ZIP. | The pack reached this session as an upload. | The pack lives at `docs/campaigns/11-20-26/L9_CI_Unified_Leverage_Campaign_v1.7.1/` in Cursor-Governance, which every child attaches. Until its pull request merges, a child reads it from the head named in its task prompt. Lane briefs carry the scope by themselves. |
| B19 | `Quantum-L9/coderabbit` is not among the 61 `Quantum-L9` repositories this session's GitHub access lists. | `list_repos`, 2026-11-20. Absent and not-installed cannot be told apart from here. | CodeRabbit inheritance pull requests stay `blocked_external_account` until the operator confirms the central repository exists (`.github` ADR-0020 makes its creation an operator task). The read-only audit proceeds. |
| B20 | `l9-assurance` and `l9-repo-template` exist and are outside this session's scope. | `list_repos`; session sources. | Neither is written. A lane that must read one sends a `CTO-QUESTION`. |
| B21 | Stage 2A needs merges the campaign cannot make. | `CURSOR_CANARY.md` Gate 0; Core `AGENTS.md` §16 "Activation is a pin advance". | Wave 1 ends at ready-to-merge pull requests and `CURSOR_CANARY_BLOCKED` with reason `BLOCKED_ON_PROMOTION`. Wave 2 starts when the operator merges and Core advances its SDK pin. |
| B22 | `PROOF.md` sections are out of numeric order (P0 to P8, P12, P13, P10, P11, P9, P14). | File order. | Read them by number. Nothing is missing. Version markers such as "v1.4.0" inside files are revision history, not competing versions. |
| B23 | G0 asks for one screen at a time. The CTO protocol asks for one batched question set. | `OPERATOR_VERIFY_FIRST.md`; `operating_protocol.pre_launch`. | Both hold, per the G0 section below. |

## Findings register

T01 to T14 keep their owners and proof contracts, with these changes.

| ID | Change |
| --- | --- |
| T01, T02, T07, T14 | Confirmed present on CEG `b2150980` (B11). Lane F1. |
| T03 | Changed by merged work (B03). Verify, do not rebuild. |
| T04 | Confirmed: Core `.github/workflows/security.yml:111` still ends Bandit with `\|\| echo "::notice::Bandit warnings are non-blocking"`. Whether any consumer still calls it after Core `AGENTS.md` §15 is Unknown. Lane L2. |
| T05, T06 | Not rechecked. Lane F2 rebinds on `e1a61f78`. |
| T08 | Not rechecked. Lane F1. |
| T09, T11 | Delegated to the sibling campaign's pull requests (B09). |
| T10 | EIE half delegated to EIE #365 (B10). Odoo half merged as #552; lane H1 proves the live Sonar scope. |
| T12, T13 | Not rechecked. Read-only audit in lanes G1 and F2. |
| **T15** (new, P1) | Cursor-Governance Sonar successor unproven after #1062 (B02). Lane N1 looks for a hosted Core `mode=apply` dispatch with a native Sonar gate on `a95562c9` or later. If none exists, the scheduler gap belongs to the sibling campaign and is reported, not patched here. |
| **T16** (new, launch blocker) | Swarm children cannot start (B16). Owner: operator merge of Cursor-Governance #1073. |

## Writer map and pool

Five pool slots, launched once in the bootstrap sitting, each bound to one repository. No lane has two
writers and no repository has two pool agents.

| Lane | Executor | Writes | Reads | Absorbs from v1.7.0 |
| --- | --- | --- | --- | --- |
| S0 | CTO session | this pack only | all seven repositories | Stage 0, Stage 0H ledger, G0 |
| L1 | pool slot 1 | `Quantum-L9/l9-ci-sdk` | EIE, CEG, Cursor-Governance, IB-Odoo_19 | Lane 1 |
| L2 | pool slot 2 | `Quantum-L9/l9-ci-core` | `l9-ci-sdk` | Lane 2, T04 |
| F1 | pool slot 3 | `Quantum-L9/Cognitive.Engine.Graphs` | `l9-ci-core` | F1, T03, T08, CEG parts of Lane 3 and 4 |
| F2 | pool slot 4 | `Quantum-L9/Enrichment.Inference.Engine` | `l9-ci-core` | T05, T06, T10 (EIE), T13, EIE parts of Lane 3 and 4 |
| N1 | pool slot 5 | `Quantum-L9/Cursor-Governance` | `l9-ci-core` | CodeQL A.1, T15, canary Gate 1, Cursor parts of Lane 3 and 4 |
| H1 | first idle slot, by `CTO ASSIGN` | `cryptoxdog/IB-Odoo_19` | `l9-ci-sdk` | Odoo harvest, T10 (Odoo), Odoo CodeRabbit |
| G1 | CTO session, one `.github` worktree | `Quantum-L9/.github` | all | T12, CodeRabbit and Dependabot generators, ruleset evidence |
| I1 | CTO session, disposable worktrees | none | all | Stage 1 integration, Stage 2A canary, Stage 4 closeout |

Lane N1 and this pack both sit in Cursor-Governance. The paths are disjoint: the CTO owns
`docs/campaigns/11-20-26/**`, lane N1 owns the paths its brief names.

The harvest ledger has one writer. Each lane reports its rows in its own transcript and pull request.
The CTO writes `evidence/HARVEST_LEDGER.md` in this pack.

Dependencies, not merge gates:

- L1 and L2 open their ADR and invariant pull requests first, against `main`, with no dependency.
- L2's multi-language work pins L1's capability-inventory head as soon as that head exists.
- I1 Stage 1 runs when L1 and L2 each report `ready-to-merge`.
- I1 Stage 2A needs the promotion in B21.
- No consumer check is retired in Wave 1. `L9-CI-CORE-004` forbids it before `CURSOR_CANARY_PASS`.

## Publication

One ceremony per pull request. No rehearsal run, no raw `git push`, no `gh pr create`, no MCP
`create_pull_request` or `push_files`.

| Repository | Command, from the lane worktree | Base |
| --- | --- | --- |
| `l9-ci-core`, `l9-ci-sdk`, `Cognitive.Engine.Graphs`, `Enrichment.Inference.Engine`, `.github` | `PR_REMEDIATE=0 OPEN_PR=1 make -C "$HOME/.cursor-governance" pr WS="$PWD"` (same as `PR_REMEDIATE=0 l9 pr`) | `main` |
| `Cursor-Governance` | `PR_REMEDIATE=0 make pr` | `main` |
| `cryptoxdog/IB-Odoo_19` | `make pr`, its own ceremony (`ops/config/publish-authority.json`: native route) | `Staging`, never `Production` or `main` |

Before the ceremony, in the lane worktree: scoped commits by pathspec, then
`python3 "$HOME/.cursor-governance/ops/autonomy/l4_local.py" begin --contract-id <lane>`, then
`authorize-release`. The governance gate does not run a consumer's own tests, so the lane runs that
repository's `make setup validate check test` (SDK: `ruff check .`, `ruff format --check .`,
`mypy l9_ci`, `pytest -q`) before publishing. A repair after a failed gate changes the tree, so
`authorize-release` is run again.

A Claude Code cloud child works on the branch its session designates. It does not create a second
branch for the same lane.

## Stacking

An unmerged pull request is never a wait.

- A lane with no overlapping open pull request branches from fetched `origin/main` (`origin/Staging`
  for IB-Odoo_19).
- A lane that must change a file a foreign open pull request also changes publishes against `main`
  first. Same file with disjoint hunks passes the overlap gate. If the gate reports a textual conflict,
  the lane stacks on that head: `PR_BASE=origin/<head branch>` with
  `L9_TASK_BASE_AUTHORIZED="operator 2026-11-20: stack on the open PR that owns the file"`.
  Expected cases: F1 on `agent/fleet-d/ceg-pilot` for `ci-quality.yml`, L2 on
  `agent/fleet-b2/pr-expense-guard` for `org-ci.yml`.
- A lane's second pull request stacks on its own first one. Bottom-up merge order. No rebase, no
  force-push; when a parent moves, merge it into the child.
- Dependabot pull requests are never a parent.

## G0

`OPERATOR_VERIFY_FIRST.md` and `G0_OTHER_VENDOR_CHECK.md` stand as written: read-only, one screen at a
time, no scan or test dispatch, no setting changed, Unknown is a valid answer.

- G0 is a conversation between the CTO session and the operator only. A pool agent never asks the
  operator anything and never performs a screen.
- The CTO does the self-service source check first, then opens G0 in the bootstrap sitting. It is the
  one standing exception to the single batched question set, because the operator asked for that
  format.
- G0 gates four things: lane N1's CodeQL and Sonar workflow or config edits, any scan or test
  dispatch, any vendor setting, and lane F1's Codecov authentication change. Nothing else waits. L1,
  L2, the F1 GitGuardian and aggregate fixes, F2, H1 and every read-only step run while G0 is open.
- A pool agent whose next step is behind G0 writes `CTO-BLOCKER: G0` and takes the next ungated step.

## Launch preconditions

One batched set for the operator. Nothing below is decided by this binding.

| ID | Needed from the operator | Why | If declined |
| --- | --- | --- | --- |
| P1 | Merge [Cursor-Governance #1073](https://github.com/Quantum-L9/Cursor-Governance/pull/1073), and apply its Setup script change if the environment needs one. | B16: no child starts without it. | The pool cannot launch. The CTO session can run S0, G0 and G1, and nothing else moves. |
| P2 | Put this CTO session in Auto permission mode before the bootstrap sitting. | B17: children inherit `default` and stall on prompts. | Children launch and stop at their first `add_repo` prompt; the operator must clear each one by hand. |
| P3 | Say "launch". | This binding does not authorize it. | The pack stays published and idle. |
| P4 | Start G0 now, or defer it. | G0 section. | The four gated items stay blocked; everything else runs. |
| P5 | Confirm whether `Quantum-L9/coderabbit` exists. | B19. | CodeRabbit closes as `blocked_external_account`. |

Recorded operator decisions the briefs carry: merges are the operator's; no purchase, tier change or
vendor-admin change; no consumer check retired before `CURSOR_CANARY_PASS`; ADRs stay Proposed until
their owner admits them.

## Unknown

- Whether a Core `mode=apply` dispatch has run for Cursor-Governance since `a95562c9` (T15).
- Whether Core `security.yml` still has a consumer caller (T04).
- Every vendor plan, seat, quota, spend and dashboard setting (G0).
- Whether `cryptoxdog/IB-Odoo_19` is bound by any required-workflow ruleset (`L9-CI-CORE-006`).
- The org-level ruleset state: this session's token read of it is not yet attempted. The repository
  ruleset route is the fallback. Lane G1 reads it.
- The run-to-checkout bindings listed in `OTHER_TOOLS_EVIDENCE.md` "Confidence and precedence".
- `Quantum-L9/L9-Ops-MCP` kernels and playbooks were not read for this binding; the repository is not
  attached to this session.

## Swarm

Do not launch the pool from this binding. When the operator says launch and P1 and P2 hold, each child
is created from `cto_mode.py launch-spec --cto-session session_017xwbxvn4RrcFtW27s3aYG4 --lane-repo
<owner/name>`, its fields passed unchanged to `create_session`. The child system prompt is that output
and is never written by hand. The lane brief in `lanes/` is the task prompt. Children report in their
own transcript and never message the operator.
