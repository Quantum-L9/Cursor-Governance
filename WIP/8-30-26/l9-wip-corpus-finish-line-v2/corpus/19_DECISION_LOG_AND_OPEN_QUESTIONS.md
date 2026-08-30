# Decision Log and Open Questions

## Locked decisions
- Dropbox remains source storage.
- Meta Injector observes; Topology compiles; Memory admits/persists; Graphiti projects/queries.
- WorkContextCompiler and LeveragePlanner sit after governed memory retrieval.
- Cursor-Governance Program Execution owns execution.
- Planning prioritizes WorkUnits, never raw files.
- Wave planning supports parallel work based on dependency independence.

## Questions to resolve during implementation, not before pilot
- exact home/API surface for WorkContextCompiler and WorkUnit/Leverage planner, with l9-cognitive-runtime the current natural candidate
- exact graph retrieval query API used by the compiler
- context budget policy by downstream agent/provider
- persistence location for immutable BuildWavePlan history
- outcome feedback contract from Program Execution back into corpus/memory

These are implementation choices unless a seam audit proves an authority conflict.
