---
name: l9-pipeline-orchestrator
description: drive a compiled contract chain as one fresh Claude Code session per contract, in dependency order. use when running an emitted multi-PR chain that needs an advance driver, auto-merge gate, and branch protection.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pipeline, orchestrator, contract-chain, automerge]
  owner: igor_beylin
  status: active
  version: "1.0.0"
  updated: "2026-08-28"
  sibling: l9-claude-coding-contract-compiler
  extracted_from: l9-claude-coding-contract-compiler v2.4.0-v2.6.1 orchestrate module
---


# L9 Pipeline Orchestrator

## Purpose
Execute a **compiled contract chain** end-to-end: one fresh Claude Code session per contract, in
dependency order, with no manual copy-paste between sessions. This pack is the **execution half** of
the pipeline; it consumes the `out/PR-*/` set emitted by `l9-claude-coding-contract-compiler`
(`compile_contract.py --emit-artifacts`) and drives it to completion.

Separation of concerns: the code compiler **emits + validates** contracts; this pack **runs** them.
They version independently.

## The three stages
```
STAGE 0  any LLM         claude-code-spec-compiler       →  campaign-spec.yaml
STAGE 1  Claude Code     compile_contract.py --emit-artifacts  →  out/PR-*/
                         make_state.py out state.yaml          →  ordered chain (chain_on: green default)
STAGE 2  Claude Code     Routine fires a FRESH session per contract, self-advancing:
                         preflight → build in scope → npm run validate → commit → advance set green → gate → next
```

## Components (all repo-agnostic; nothing hardcodes a repo)
- `advance.py` — deterministic chain driver: `next` | `seed <id>` | `set <id> <status>` |
  `gate <id> pr_state.json`. No side effects beyond `state.yaml`. Determinism lives here; the
  session decides WHAT to build.
- `make_state.py` — build `state.yaml` from an emitted `out/PR-*/` set (default `chain_on: green`).
- `automerge_gate.py` — no-HITL merge predicate: **ci_green AND review_flags_resolved AND
  review_comments_resolved** (`remediation_ran: true`). ELIGIBLE / fail-closed with reasons.
- `apply_branch_protection.py` — belt-and-suspenders: auto-discovers repo/branch/checks/CODEOWNER
  (git + `.github/workflows` + `.github/CODEOWNERS`); prints the REST payload + `gh api` commands;
  `--apply` enacts live with a token. **Missing repo/branch is never a blocker** (dry-run always exits 0).
- `verify_branch_protection.py` — fail-closed check that live protection matches the config.
- `branch_protection.example.yaml`, `CODEOWNERS.example` — optional overrides / templates.
- `README.md` — full flow, the Routine wiring (`create_trigger` + `create_new_session_on_fire`),
  the auto-merge policy, the branch-protection setup, and the control-relaxation migration record.

## Merge policy (choose in state.yaml)
- `chain_on: green` (default) — next contract starts when the prior is green; one stack review/merge at end.
- `chain_on: merged` + `merge_policy: auto` — per-PR gating with **no human tap**: `advance.py gate`
  promotes `green → merged` only when `automerge_gate.py` is ELIGIBLE. Pair with GitHub branch protection
  so the merge call itself can't fire early.

## Safety invariants (unchanged from the contracts)
- The **build session never pushes/merges its own work** (denied_tools in each contract). Merge runs in
  a separate authorized step (DPK role isolation).
- Removing the human tap is a **logged control relaxation** (migration record in `README.md`).
- Two independent merge gates: in-orchestrator `automerge_gate.py` + server-side GitHub branch protection.

## Requires
- The emitted contract set from `l9-claude-coding-contract-compiler` (`out/PR-*/`).
- Python `pyyaml` (advance/make_state); `jsonschema` not required here.
- For live GitHub actions: a token in env (`GITHUB_TOKEN`) and/or the GitHub MCP tools
  (`enable_pr_auto_merge`, `merge_pull_request`).

## Validation
Not complete unless: `make_state.py` builds an ordered state from an emitted set; `advance.py`
reaches `__DONE__` in both gate modes; `automerge_gate.py` is ELIGIBLE only when all three conditions
hold; `apply_branch_protection.py` runs repo-agnostically (zero args) and never blocks on missing
repo/branch; `verify_branch_protection.py` fails closed on weak protection.
