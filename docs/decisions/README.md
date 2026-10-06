# Architecture Decision Records

This directory is the repository's record of durable architecture decisions.
Each ADR file is the record. This index is generated from those files by
`ops/scripts/validate_adr_identity.py`. One number is one decision. A
`docs/decisions/` pointer and an `environment/contracts/execution/adr/` body
may share a number only when the filename slug is the same decision.

<!-- BEGIN L9 ADR INDEX (generated — do not edit) -->

| Number | Status | Title | Record |
|---|---|---|---|
| ADR-0001 | Accepted | Claude Code bounded concurrent autonomy — PR convergence, human-approved merge | `docs/decisions/ADR-0001-claude-code-bounded-concurrent-autonomy.md` |
| ADR-0002 | Accepted | Memory is an enforced contract, not advisory context | `docs/decisions/ADR-0002-memory-enforcement-contract.md` |
| ADR-0003 | Accepted for **hook vs interactive roles**. Transport/store duality via `L9_MEMORY_HTTP_URL` / `memory_client.py` is **superseded by ADR-0006** (single Graphiti front door). | Memory architecture — two entry points, one contract | `docs/decisions/ADR-0003-memory-two-entry-points-one-contract.md` |
| ADR-0004 | Accepted | The hook memory client is a contract-pinned stdlib mirror of `memory.*` | `docs/decisions/ADR-0004-hook-memory-client-contract-pin.md` |
| ADR-0005 | Accepted | One agent episodic memory; product/domain memory is out of band | `docs/decisions/ADR-0005-one-agent-memory-domain-out-of-band.md` |
| ADR-0006 | Accepted (supersedes ADR-0003's dual HTTP hook/MCP plane for Claude lifecycle) | Single memory front door — Cursor Graphiti only | `docs/decisions/ADR-0006-single-memory-front-door-graphiti.md` |
| ADR-0007 | Accepted | Goal-level intent is the Program Execution front door | `docs/decisions/ADR-0007-goal-level-intent-front-door.md` |
| ADR-0008 | Accepted | Intent resolution is an explicit provenance-bearing boundary | `docs/decisions/ADR-0008-intent-resolution-provenance-boundary.md` |
| ADR-0009 | Accepted | Named autonomy profiles own default execution authority | `docs/decisions/ADR-0009-named-autonomy-policy-profiles.md` |
| ADR-0010 | Accepted | Program synthesis emits design-time authority; the Controller remains runtime authority | `docs/decisions/ADR-0010-blueprint-synthesis-controller-boundary.md` |
| ADR-0011 | Accepted | Autonomous replanning is bounded by the immutable Program Lock | `docs/decisions/ADR-0011-bounded-replanning-within-program-lock.md` |
| ADR-0012 | Accepted | Replan revisions are evidence-triggered and independently validated | `docs/decisions/ADR-0012-evidence-gated-replan-revisions.md` |
| ADR-0013 | Accepted | Shared agent semantics have one canonical source; peer-local semantic forks are forbidden | `docs/decisions/ADR-0013-canonical-peer-semantics-no-local-forks.md` |
| ADR-0014 | Accepted | Shared semantic revisions apply atomically to all registered peers | `docs/decisions/ADR-0014-atomic-all-peer-semantic-revisions.md` |
| ADR-0015 | Accepted | Golden semantic vectors and a peer-parity gate prove cross-peer equivalence | `docs/decisions/ADR-0015-golden-semantic-vectors-peer-parity.md` |
| ADR-0016 | Accepted | Long autonomous chains run from durable typed state, not accumulated conversation | `docs/decisions/ADR-0016-typed-runtime-state-context-projections.md` |
| ADR-0017 | Accepted | Peer Execution Core Is Upstream of All Adapters | `docs/decisions/ADR-0017-peer-execution-core-upstream-of-adapters.md`<br>`environment/contracts/execution/adr/ADR-0017-peer-execution-core-upstream-of-adapters.md` |
| ADR-0018 | Accepted | Separate Peer Identity, Execution Profile, Transport, and Provider | `docs/decisions/ADR-0018-separate-peer-identity-profile-transport-provider.md`<br>`environment/contracts/execution/adr/ADR-0018-separate-peer-identity-profile-transport-provider.md` |
| ADR-0019 | Accepted | Canonical Execution Request/Result and Shared Transport Boundary | `docs/decisions/ADR-0019-canonical-execution-request-result-and-shared-transports.md`<br>`environment/contracts/execution/adr/ADR-0019-canonical-execution-request-result-and-shared-transports.md` |
| ADR-0020 | Accepted | Provider-Neutral Inference Routing; DeepSeek Deferred | `docs/decisions/ADR-0020-provider-neutral-inference-routing-deepseek-deferred.md`<br>`environment/contracts/execution/adr/ADR-0020-provider-neutral-inference-routing-deepseek-deferred.md` |
| ADR-0021 | Accepted | Decompose Claude Code from Thick Gold Standard to Thin Provider | `docs/decisions/ADR-0021-decompose-claude-code-thick-adapter.md`<br>`environment/contracts/execution/adr/ADR-0021-decompose-claude-code-thick-adapter.md` |
| ADR-0022 | Accepted | Thin-Adapter Conformance Is Merge-Blocking | `docs/decisions/ADR-0022-thin-adapter-conformance-is-merge-blocking.md`<br>`environment/contracts/execution/adr/ADR-0022-thin-adapter-conformance-is-merge-blocking.md` |
| ADR-0023 | Accepted | Task Readiness, Ordering, and Blocking Semantics | `docs/decisions/ADR-0023-task-readiness-ordering-and-blocking-semantics.md`<br>`environment/contracts/execution/adr/ADR-0023-task-readiness-ordering-and-blocking-semantics.md` |
| ADR-0024 | Unknown | Mission Is Durable Parent Intent; the Program Controller Remains Runtime Authority | `docs/decisions/ADR-0024-mission-parent-intent-and-controller-boundary.md`<br>`environment/contracts/execution/adr/ADR-0024-mission-parent-intent-and-controller-boundary.md` |
| ADR-0025 | Unknown | Mission Revision Is Immutable; Mission Lifecycle Is a Separate State Domain | `docs/decisions/ADR-0025-mission-revision-immutability-and-lifecycle-separation.md`<br>`environment/contracts/execution/adr/ADR-0025-mission-revision-immutability-and-lifecycle-separation.md` |
| ADR-0026 | Unknown | Mission Program Binding Is Exact-State and Must Not Create Circular Blueprint Identity | `docs/decisions/ADR-0026-exact-mission-program-binding-and-non-circular-blueprint-identity.md`<br>`environment/contracts/execution/adr/ADR-0026-exact-mission-program-binding-and-non-circular-blueprint-identity.md` |
| ADR-0027 | Unknown | Mission Acceptance Is Separate from Program Acceptance | `docs/decisions/ADR-0027-mission-acceptance-separate-from-program-acceptance.md`<br>`environment/contracts/execution/adr/ADR-0027-mission-acceptance-separate-from-program-acceptance.md` |
| ADR-0028 | Accepted | Session hydrate/close visibility and write-primary repair | `docs/decisions/ADR-0028-session-hydrate-close-visibility.md` |
| ADR-0029 | Accepted | Surface-hook divergence (shared brain upstream) | `docs/decisions/ADR-0029-surface-hook-divergence.md` |
| ADR-0030 | Accepted | The memory control plane is the single front door | `docs/decisions/ADR-0030-memory-control-plane-single-front-door.md` |
| ADR-0031 | Accepted | Signed-agent MCP door + dual write classes | `docs/decisions/ADR-0031-signed-agent-mcp-write-classes.md` |
| ADR-0032 | Accepted | A close-gap is a lifecycle condition, and an unbound runtime is an environment fault — neither is memory degradation | `docs/decisions/ADR-0032-close-gap-is-lifecycle-not-memory-degradation.md` |
| ADR-0033 | Accepted | Two lanes into one `MemoryService` — agents write directly, hooks write bounded, nothing writes around it | `docs/decisions/ADR-0033-two-lanes-one-memoryservice.md` |
| ADR-0034 | Accepted | SessionStart reads what sessionEnd writes, plus last-24h agent-lane facts | `docs/decisions/ADR-0034-hydrate-close-agent-lane-alignment.md` |
| ADR-0035 | Accepted | `recorded_after` is a search selector that skips the relevance drop | `docs/decisions/ADR-0035-recorded-after-search-selector.md` |
| ADR-0036 | Accepted | Core Owns the Makefile Compiler Runtime | `docs/decisions/ADR-0036-core-owns-makefile-compiler-runtime.md` |
| ADR-0037 | Accepted | Direct agent memory records represent independently governable knowledge | `docs/decisions/ADR-0037-direct-agent-memory-record-granularity.md` |
| ADR-0039 | Accepted | Cloud Graphiti HTTPS reachability | `docs/decisions/ADR-0039-cloud-graphiti-https-reachability.md` |
| ADR-0040 | Accepted | Contracts own rule semantics; Cursor rules are activation and projection surfaces | `docs/decisions/ADR-0040-contracts-own-rule-semantics.md` |
| ADR-0041 | Accepted | Rule Activation Binding is the canonical intermediate representation between contracts and platform rules | `docs/decisions/ADR-0041-rule-activation-binding-intermediate-representation.md` |
| ADR-0042 | Accepted | Normative and advisory content are separate channels in rule projections | `docs/decisions/ADR-0042-normative-advisory-rule-channels.md` |
| ADR-0043 | Accepted | Rule activation is explicit, faithfully representable, and context-budgeted | `docs/decisions/ADR-0043-rule-activation-and-context-budget.md` |
| ADR-0044 | Accepted | Cursor .mdc files are deterministic generated projections with clause-level provenance | `docs/decisions/ADR-0044-deterministic-generated-cursor-rule-projections.md` |
| ADR-0045 | Accepted | RULES-MANIFEST.yaml is the generated rule projection registry | `docs/decisions/ADR-0045-rules-manifest-generated-projection-registry.md` |
| ADR-0046 | Accepted | Rule compilation fails closed on unresolved authority, conflict, scope widening, unsupported activation, context overflow, and projection drift | `docs/decisions/ADR-0046-rule-compiler-fail-closed-conflicts-scope-and-drift.md` |
| ADR-0047 | Accepted | Existing Cursor rules migrate through a strangler lifecycle with a monotonic hidden-doctrine ratchet | `docs/decisions/ADR-0047-rules-strangler-migration-and-doctrine-ratchet.md` |
| ADR-0048 | Accepted | Multi-agent main-bound execution — Git isolates writers, memory does not | `docs/decisions/ADR-0048-multi-agent-main-bound-execution.md` |
| ADR-0049 | Accepted | Universal campaign ingress and typed architecture admission | `docs/decisions/ADR-0049-universal-campaign-ingress-and-architecture-admission.md`<br>`environment/contracts/execution/adr/ADR-0049-universal-campaign-ingress-and-architecture-admission.md` |
| ADR-0050 | Accepted | Compiler-owned structure, target resolution, and program owner | `docs/decisions/ADR-0050-compiler-owned-structure-target-resolution-and-program-owner.md`<br>`environment/contracts/execution/adr/ADR-0050-compiler-owned-structure-target-resolution-and-program-owner.md` |

<!-- END L9 ADR INDEX -->

The next number is one greater than the highest number in this index.
Unassigned integers below that highest number stay unused.
Superseding a decision adds a later ADR that links to the record it replaces.
Prior records stay on disk.
