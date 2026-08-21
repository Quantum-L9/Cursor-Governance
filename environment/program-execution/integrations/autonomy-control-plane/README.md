# Root Autonomy Control Plane Bridge

This bridge maps one Program task into one root-autonomy campaign and action.
Program leases remain authoritative; the root-autonomy lease is subordinate and
must not outlive the Program lease.

`make campaign` execute binds through `grant.py` before any worker write:

1. Probe `autonomy/` (fail closed if the control plane is missing).
2. Map the rendered Program contract to a schema-valid campaign packet.
3. Compile and bootstrap the graph in the PEC workspace SQLite store.
4. Complete synthesis (the already-rendered contract) so the executor is READY.
5. Issue, acknowledge, and authorize `repository.write_scoped` + `git.commit_local`.
6. Write `runtime/autonomy-packet.json` and `runtime/autonomy-grant.json`.

Push, pull request, and merge stay forbidden on this autonomous path.
`owns_program_state` remains false.
