# /agent-git

Canonical command contract for all agent git operations. This is the only
sanctioned way agents interact with git when multiple agents may be
working concurrently.

## Lifecycle
1. **doctor** `python tools/agent_git.py --cwd <worktree> doctor`
2. **claim** `python tools/agent_git.py --cwd . claim --branch feat/<node-id>-<slug> --path ../wt-<node-id> --base main --agent-id <agent-id>`
3. **commit** `python tools/agent_git.py --cwd <worktree> commit --message "<summary>" --agent-id <agent-id> --node-id <node-id>`
4. **conflicts** `python tools/agent_git.py --cwd <worktree> conflicts --against <peer-branch>`
5. **push** `python tools/agent_git.py --cwd <worktree> push --base main --agent-id <agent-id> --max-retries 3`
6. **release** `python tools/agent_git.py --cwd <worktree> release --branch feat/<node-id>-<slug>`

## Provenance requirement
Every commit carries `L9-Agent`, `L9-Worktree`, `L9-Node` trailers, enforced
by `.github/workflows/agent-git-guard.yml`.
