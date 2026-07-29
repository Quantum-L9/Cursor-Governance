<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/VALIDATION.md
layer: evidence
owner: governance-control-plane
status: active
version: 1.0.1
updated: 2026-07-28
/L9_META -->

# VALIDATION — evidence log (live runs, 2026-07-28 EDT, sandbox Python 3.11)

## 1. Registry + adapter validator

```
$ python3 tools/validate_agents.py --root .
PASS — registry valid, 5 agent(s), adapters consistent, no committed secrets
```

## 2. Rendered principals (synthetic tokens, --include-planned)

```
$ python3 tools/render_principals.py --registry agent_registry.yaml \
    --tokens /tmp/l9test/agent_tokens.local.json \
    --out /tmp/l9test/auth_tokens.json --include-planned
wrote 5 principal(s) -> /tmp/l9test/auth_tokens.json (agents: claude-code, codex, cursor, gemini, manus)

cursor       user=cursor_agent       roles=['orchestrator', 'memory-client'] write=['*'] promote=['*']
claude-code  user=claude_code_agent  roles=['implementer', 'memory-client'] write=['cursor-governance', 'l9-graphiti-memory', 'l9-node-template'] promote=[]
manus        user=manus_agent        roles=['researcher-builder', 'memory-client'] write=['cognitive-engine-graphs', 'cursor-governance', 'igor-workspace', 'igorbot', 'l9-graphiti-memory'] promote=[]
codex        user=codex_agent        roles=['implementer', 'memory-client'] write=['l9-node-template'] promote=[]
gemini       user=gemini_agent       roles=['reviewer', 'memory-client'] write=['cursor-governance.reviews', 'l9-graphiti-memory.reviews'] promote=[]
```

Grants match the role catalog exactly: orchestrator full write + promote;
implementers scoped to assigned groups; researcher-builder gains the shared
workspace namespace (`igor-workspace`, read from the registry's
`workspace_group` — an earlier build hardcoded the literal `l9-workspace`
here, fixed during repo integration); reviewer confined to `<group>.reviews`;
nobody else promotes.

## 3. Self-test suite (2 positive, 5 negative)

```
$ python3 tools/test_validators.py
PASS  T1 real pack passes validator
PASS  T2 principals render with role-correct grants
PASS  T3 shared token rejected
PASS  T4 duplicate user_id rejected
PASS  T5 unknown role rejected
PASS  T6 naming-law violation rejected
PASS  T7 committed secret rejected

7/7 tests passed
```

All identity values derive from `agent_registry.yaml`. Tokens used in testing
were synthetic and discarded; real tokens are issued at deployment and never
enter this repository. Not yet exercised: a live end-to-end write against a
deployed l9-memory-server (requires the routable endpoint from
`docs/MEMORY_TOPOLOGY.md` — an operator deployment step).
