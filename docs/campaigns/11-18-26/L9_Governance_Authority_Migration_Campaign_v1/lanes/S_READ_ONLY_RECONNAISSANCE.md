```yaml
repository_access:
  writable: []
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/l9-ci-core
    - https://github.com/Quantum-L9/L9-Ops-MCP
    - https://github.com/Quantum-L9/l9-ci-sdk
    - https://github.com/Quantum-L9/l9-repo-template
  unlisted_repositories: no_access
```

# S: parallel read-only source and authority census

**Executor:** pool Tasks, at most four, inside the campaign pool cap of five. **No mutation rights.** Do not add lane files to narrow access. Narrow the repository list in the task prompt. The header above is the maximum. All outputs are inspection evidence, not cached permission. The 2026-11-18 SHA, open-PR, and ruleset recheck in `09_EXECUTION_BINDING.md` is the starting ledger. Re-read anything a lane will mutate immediately before that lane writes.

## Assignment

1. Resolve current main SHA for `.github`, Cursor-Governance, Core and L9-Ops-MCP, record candidate PR diffs/overlaps and classify changes since `02_VERIFIED_SOURCE_BASELINE.md`. If a material authority/input changed, rebind the affected lane before it mutates; do not halt unrelated work.
2. At `.github`, trace the *actual* global semantic/admission authority, policy owner directory, validators, ADR/release route and ruleset apply/census capability. Search for a pre-existing org-invariant policy owner to avoid duplicate files. Confirm exactly which signed release mechanism is supported and what key/identity proof is necessary, or report `UNKNOWN` without a fabricated command.
3. At Cursor-Governance, inventory all active `ORG_INVARIANTS.yaml`/L9-ORG references, declared authority, actor hooks, program execution and publication guard entrypoints. Find all active tests and generated consumers on fetched `origin/main` `59c0b3e0fae7418c67b7e3be76c4e3f412ad49dd`. #1036 is open and changes only three `.github` files; it is not the inventory base. Check the current single `make pr` invocation path/flags.
4. At Core, trace `Analyze (central Core)` job and existing authorization, checkout and read-only action scopes; identify the precise step implementing required policy checks with no self-skipping green. Read SDK only to classify technical-gate ownership; do not mutate it.
5. At L9-Ops-MCP, trace readers of its legacy `ORG_INVARIANTS.yaml` and existing negative path and determine whether a source-bound reduced compatibility view is feasible.
6. Verify live current organization ruleset 21895545 and Cursor main protection 20855699 separately from committed JSON; record bypass actors, strictness, required check names and actual scope. If API access is unavailable, report exact missing permission.

## Output

One shared read-only evidence ledger with `repo, SHA, source_path, blob_sha, fact, inference_or_unknown, overlap_with_lane, exact_required_owner_action`. Route questions to named owning lanes A/B/C/M/E/F. Scout results are **not** admission or enforcement proof. Do not create PRs, comments, branches, commits, settings or workflows.
