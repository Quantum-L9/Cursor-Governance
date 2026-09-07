# Claude Code capability + sanctioned finish path — repaired source contract

This WIP artifact records the intent behind PR #514. It is supporting evidence,
not an independent authority. Current memory and repository-scope law come from
the revised #509/#517 memory stack and the executable Claude adapter settings.

## Target outcome

Converge Claude Code Web/Mobile so the normal L9 path is frictionless without
creating a second authority plane:

1. safe Edit/Write/NotebookEdit and bounded inspection are pre-approved while
   L9 PreToolUse policy remains authoritative;
2. durable agent memory is the canonical `l9-graphite-memory` stdio MCP ending
   at `MemoryService`;
3. ordinary autonomous durable writes use
   `memory.phase_lock` → `memory.write_governed` and do not require a vendor
   permission dialog;
4. `memory.phase_lock` is a memory-write consistency precondition only, never
   repository-write authority;
5. the selected `CLAUDE_PROJECT_DIR` checkout is the primary repository scope,
   so SessionStart does not request Add Repo for it;
6. only a genuinely different repository discovered later may require one
   narrowly scoped repository-access request;
7. hosted GitHub transport is REST-first and known GraphQL-backed commands are
   rejected before network;
8. publication has one agent-visible route: `make pr`;
9. Claude native auto-memory and scheduled-task polling remain disabled because
   L9 memory and l9-pr-remediation already own those planes.

## Explicitly retired assumptions

The following are not current architecture and must not be restored:

- direct `graphiti-memory` provider MCP access;
- `graphiti_memory_client.py` as the live memory front door;
- `search_memory_facts` / raw `add_memory` as model-facing memory operations;
- provider URL or bearer possession by the model surface;
- a read-only model memory plane;
- generic `memory.ingest` as an autonomous-write bypass;
- proactive Add Repo with `access=push` for the already-selected primary checkout;
- GitHub scope for `Cursor-Governance` merely because `$HOME/.cursor-governance`
  supplies local governance scripts;
- raw `git push`, `gh pr create`, arbitrary REST POST, or GitHub MCP publication
  as alternate publication paths.

## Canonical ownership

| Concern | Owner |
|---|---|
| Governance files | `$HOME/.cursor-governance` |
| Durable agent memory | `l9-graphiti-memory` `MemoryService` |
| Interactive memory write | `memory.phase_lock` → `memory.write_governed` |
| Repository mutation policy | L9 Git/worktree/PreToolUse governance |
| Primary repo scope | selected `CLAUDE_PROJECT_DIR` checkout |
| Later cross-repo expansion | hosted repository-scope capability, exact new repo only |
| Hosted GitHub reads | repository-scoped REST / approved GitHub read tools |
| Publication | `make pr` |
| PR convergence | `l9-pr-remediation` |

## Evidence requirement

Static settings tests are necessary but not sufficient. The candidate must also
be exercised on hosted Claude Code and prove: no Register Repo Root prompt, no
primary Add Repo prompt, no normal Edit/Write prompt, no memory-write prompt,
no Send Later prompt, no known-bad GraphQL attempt, and a successful canonical
memory receipt for a governed write.
