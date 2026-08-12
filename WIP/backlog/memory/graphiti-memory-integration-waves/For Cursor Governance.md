Choose **1: switch to Cursor-Governance and add the three producer modules first**.

That is the only path that preserves the agreed repository boundary and allows Wave 1, Wave 2, and the cross-repository compatibility checks to remain truthful.

Do **not** skip the cross-repo guard. Option 2 would install assets against an incomplete producer contract and create avoidable drift. Option 3 is safe as a read-only exercise, but it does not unblock execution and risks the binding assumptions becoming stale once the missing producer modules land.

Use this order:

```text
Cursor-Governance
1. Add:
   subagent-generated-data/retrieval/context_query.py
   subagent-generated-data/retrieval/reuse_recorder.py
   subagent-generated-data/invalidation/repository_event_bridge.py

2. Validate them against:
   subagent-generated-data/adapters/graphiti_memory.py
   existing schemas, routes, orchestration, and state-store contracts

3. Merge the Cursor-Governance PR.

l9-graphiti-memory
4. Re-run Wave 1 with the cross-repo guard enabled.
5. Run Wave 2.
6. Run the binding preflight.
7. Perform the surgical MemoryService / store / CLI / MCP integration.
```

The `l9-graphiti-memory` agent should stop now and preserve its checkout unchanged except for any read-only inspection notes already produced. The next active build belongs in `/Users/ib-mac/Cursor-Governance` at the current producer boundary.
