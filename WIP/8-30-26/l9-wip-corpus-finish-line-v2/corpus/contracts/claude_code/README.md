# Claude Code Contract Execution Order

Run against `Quantum-L9/l9-cognitive-runtime` in order:

1. `PR-01-PHASE5-WORK-CONTEXT-COMPILER.contract.yaml`
2. `PR-02-PHASE6A-WORK-UNIT-COMPILER.contract.yaml`
3. `PR-03-PHASE6B-LEVERAGE-PLANNER.contract.yaml`
4. `PR-04-PHASE6C-BUILD-WAVES-PE-HANDOFF.contract.yaml`

Each contract halts before merge. After a PR lands, refresh `main`, revalidate the prerequisite and execute the next contract. If current repo architecture already contains an equivalent component, modify/extend it rather than creating a duplicate package.
