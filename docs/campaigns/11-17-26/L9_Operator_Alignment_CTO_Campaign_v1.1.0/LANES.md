# Four execution lanes | ownership, exact worktrees and dependency joins

**Dispatch source:** `lanes/A.md`, `lanes/B.md`, `lanes/C.md`, `lanes/D.md` are the machine-checked briefs. This file is the aggregate roadmap. Child Task scope begins with the corresponding lane brief and the current host-rendered child system prompt; do not copy this aggregate text as the launch system prompt.

## Lane A | .github operator scoped admission | pool slot 1

**Read-only proof under current Cursor CTO child rules:** Inspect candidate PR #255, approved source hashes and actual merge readiness. The current `governance/cto-mode/MODE.yaml#operating_protocol.child_system_prompt` explicitly prohibits coding children from branching/pushing `.github` on Cursor. **Lane A cannot remediate #255 or author the separate `strategy/**` adoption PR.** CTO must separately prove a real allowed `.github` writer/host publication path or return `BLOCKED_GITHUB_WRITER`. That writer, once authorized, may copy only the seven exact approved files from `repo-overlay/strategy/`; no global semantic registry changes.

**Deliver:** current-head #255 and approval evidence, real need for PR remediation/adoption, the verified identity of an authorized `.github` writer or exact `BLOCKED_GITHUB_WRITER`. CTO independently records admission on main only after an actual permitted writer published and its PR merged; unimplemented source adoption is never claimed from A's report.

## Lane B | semantic compiler operator-source producer | pool slot 2

**Single writer:** `Quantum-L9/l9-semantic-compiler-engine`, and only the smallest justified `src/l9_semantic_compiler/` owner + focused `tests/test_projection*.py`, `tests/test_composition_provenance.py`, `tests/test_payload_validation_protocol.py` changes (if a change is actually needed). `.github` and Cursor-Governance are read-only dependencies. The existing `src/l9_semantic_compiler/engine/registry.py#CanonicalAuthority` ensures normal canonical projection from the registered `.github` global registry, so naive pointing at `strategy/` is not supported. First determine if an already supported, admitted scoped source mechanism suffices. Never bypass `CanonicalAuthority._verify_owner`, spoof global source IDs, or emit improvised receipts.

**Deliver:** exact evidence for one of (1) existing producer path used as-is, (2) bounded, admitted-compatible producer extension with independently verifiable provenance/negative controls, (3) blocked owner decision needed. Only write a PR for a genuine case (2). The interface/output contract to Lane D is agreed by CTO before dependent edits. A new global semantic contract or compiler-produced admission decision is outside this lane.

## Lane C | Cursor skill and Planner prerequisite PR train | pool slot 3

**Single writer:** `Quantum-L9/Cursor-Governance`, the **currently changed-file set** of #1011 and #1030 only. #1011 owns strategic-plan skill + registries, and #1030 owns `commands/planner.md`, `governance/planner-mode/MODE.yaml`, `ops/autonomy/planner_mode.py`, `tools/authority/produce_projection_bundle.py`, generated strategic-planning projection bundles, CI workflows and its current diff files. Both currently report `mergeable=true` but `mergeable_state=unstable` (snapshot), NOT ready. Repair checks and reviews in the original PR branches. Never modify Lane D-owned `governance/cto-mode/MODE.yaml`, `governance/architect-mode/MODE.yaml`, `governance/operator-alignment/**` or `ops/autonomy/projection_mode.py`.

**Deliver:** each PR actually merged on main with receipt; exact current-head CI and review closure; stack-safe #1011-before-#1030 merge, and confirmed `/planner` mode. Skill availability is not proof Planner mode is active.

## Lane D | Cursor consumer alignment | pool slot 4

**Single writer:** only `governance/operator-alignment/**`, `ops/autonomy/*operator_alignment*`, `tests/ops/autonomy/*operator_alignment*`, `generated/governance/operator_alignment/**` (producer bytes only); and if justified `ops/autonomy/projection_mode.py`, `governance/cto-mode/MODE.yaml`, `governance/architect-mode/MODE.yaml`, `governance/coding-agent-mode/MODE.yaml`, `commands/lcto.md`, `commands/architect.md`. **Never touch** the changed-file set of #1011/#1030 before those have merged, including `tools/authority/produce_projection_bundle.py`, `.github/workflows/l9-projection-bundle-*`, `commands/planner.md`, `governance/planner-mode/MODE.yaml`, or generated strategic-planning bundles. After PRs merge, CTO may assign a separately reviewed follow-on for Planner mode integration. The current `ops/autonomy/projection_mode.py` is the host's shared mode owner and may be extended only in a backward compatible way.

**Deliver:** evidence of a producer-backed operator view, independent verifier, CTO/Architect staged opt-in and behavioral proof, Planner after C, Meta Planner advisory-only, Coding Agent delegated-only with explicit `BLOCKED` confidentiality state until real read isolation is demonstrated. Code cannot widen actor identity, credentials, merge/deploy rights or Plan mutation.

## Collisions and sequencing

- A and B are different repositories. A/B/D share interface dependencies, not write ownership.
- C and D both target Cursor-Governance, but have **disjoint active write sets**. The CTO freezes the live PR file census at dispatch and stops any newly observed collision before a write.
- C is the only writer for existing #1011/#1030 branches. D uses its own branch/worktree; the CTO owns post-merge integration. No agent edits another lane's branch or merges.
- If producer B requires a new .github global profile/semantic file, **do not** add a fifth concurrent .github writer. Stop that dependent outcome and request an explicit new subject/authority decision.
- Each pool slot is reusable after ready-to-merge; no fresh uncontrolled agents. Use the existing Cursor Task continuation process.

## Live collision gate (required before dispatch and before publishing)

The CTO obtains `changed_files` for *both* Cursor PR #1011 and #1030 on their current heads and freezes a complete path set per branch; `mergeable` is not a file census. Compare that set with every path lane D intends to write. If any collision or newly changed generated path appears, **stop just that conflicting path** and serialize after C lands. The CTO never fixes C's branch or D's branch; the owning coding agent does. Do not override collisions with different worktrees, since publication conflicts remain.

After source/producer admission, Lane D may need a second work item for Planner-specific binding files now owned by Lane C. Allocate that to an **idle reused slot only after both Planner PRs merge**, with a fresh base and exact scoped brief; never introduce a fifth concurrent worker.

**Source read boundary:** A works in `.github`; B/C/D see `.github` as read-only dependency for governed projections. The coding-agent host's whole-repo read privilege still exposes `strategy/` to any child that has that credential, so no child may issue a source-secrecy PASS. A textual allowlist is not a sandbox.

**Source writer is an authorization-dependent dependency, not a fifth hidden swarm agent.** If current CTO governance forbids `.github` writes to child slots, none of the four pool workers may claim that role. A separate existing authorized publication capability must be independently identified or CTO requests the narrow owner decision. Do not auto-modify the operating protocol to clear this check.
