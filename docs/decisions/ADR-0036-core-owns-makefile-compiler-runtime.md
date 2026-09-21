# ADR-0036: Core Owns the Makefile Compiler Runtime

## Status

Accepted

## Date

2026-09-21

## Context

Compiler V2 introduces a generated `Repo.mk` adapter, a repository-owned `Repo.local.mk` extension layer, and a deterministic target-binding model. The implementation needs one owner for rendering, output drift detection, target-collision validation, and the reference migration contract.

The existing `l9-ci-core` repository already owns a portable Make façade and its reconciler. Its canonical template delegates repository capabilities to `Repo.mk` and governed operations to the `l9` dispatcher. Its runtime detects and repairs generated Makefile drift. Cursor-Governance owns the dispatcher, publication lifecycle, consumer-safe target classification, capability/secret boundaries, and peer topology. It does not currently contain a consumer-facade template or a Makefile compiler runtime.

GAR selected the Core location after evaluating three candidates: a new runtime repository, a Cursor-Governance implementation, and an extension of the Core renderer. The decision preserves the distinction between architectural judgment, local compilation, governance policy, and documentation obligations.

## Options Considered

### Option A: Create a new `runtime-make` repository

A separate repository would isolate the compiler, but it would add a new release lifecycle, compatibility surface, adoption model, and authority boundary before the existing Core renderer has been migrated. It would duplicate the only demonstrated template-and-reconciler seam.

### Option B: Implement the compiler in Cursor-Governance

Cursor-Governance already owns governed publication and dispatcher policy. Adding consumer adapter compilation here would couple repository-native build semantics to governance and risk creating a second target registry or a second publication-adjacent authority.

### Option C: Extend `Quantum-L9/l9-ci-core`

Core already owns the canonical generated façade, its deterministic reconciliation path, the repository execution contract, and the test/change-policy companions that protect that surface. It can host the compiler without taking over SDK detection or Governance publication.

## Decision

We place the Compiler V2 runtime in **`Quantum-L9/l9-ci-core`**. The initial implementation is a narrow module, conventionally named `tools/l9_make/`, or an explicitly renamed successor to the current `tools/l9_repo` façade renderer.

Core owns the canonical `Repo.mk` renderer, generated-output drift validation, closed target-descriptor validation, and the reference migration. The Core module compiles only standard local capability bindings. It must not infer repository capabilities, execute provider behavior, implement publication, manage secrets, or own product-specific targets.

The target graph is:

```text
l9-ci-core tools/l9_make/Repo.mk.template
                  │
                  ▼
consumer Repo.mk                 generated and committed
consumer Repo.local.mk           tracked repository-owned native leaves/extensions
consumer Makefile                stable bootstrap with required includes
```

`l9-ci-sdk` remains the owner of capability detection and semantic findings. Core may validate a separately approved SDK-produced plan envelope, but it must not duplicate SDK capability semantics. Cursor-Governance remains the owner of `l9` dispatch, publication, PR gates, consumer-safe target policy, capability registry, secret inventory, and peer topology.

GAR remains the architecture and integrity owner. `l9-update-agent-docs` remains the downstream documentation-obligation and receipt compiler; it does not acquire Makefile semantic ownership or rendering authority.

## Consequences

The first implementation change occurs in `l9-ci-core`, not Cursor-Governance. It atomically migrates the current generated relation from `Makefile.template -> Makefile` to `Repo.mk.template -> Repo.mk`, while turning the root `Makefile` into a stable bootstrap and moving repository-owned native leaves to `Repo.local.mk`.

The compiler must fail closed on a missing required layer, output drift, an unknown descriptor, duplicate or override target declarations, an unsafe command binding, and a reserved governance name. Generated and local layers must never implement `git push`, `gh pr`, direct PR creation, or a publication bypass. `make pr` remains a governance delegation.

A new `runtime-make` repository is not created. Cursor-Governance does not gain a generic consumer adapter compiler. The active `l9-update-agent-docs` PR stack is not used to implement this runtime; after that stack settles, Repo Docs runs independently against the Core change to compile documentation obligations and a receipt.

## References

[1]: https://github.com/Quantum-L9/l9-ci-core/blob/ed22910dbe7069181aafd10d0ba6c94763520bed/tools/l9_repo/Makefile.template "Current Core portable Make facade"
[2]: https://github.com/Quantum-L9/l9-ci-core/blob/ed22910dbe7069181aafd10d0ba6c94763520bed/tools/l9_repo/__main__.py "Current Core reconciliation implementation"
[3]: https://github.com/Quantum-L9/Cursor-Governance/blob/615d16c5229c18b416d6d28c12bbb97989350769/skills/l9-global-architect/integrations/L9_RUNTIME_BINDING.yaml "GAR integration ownership boundary"
[4]: https://github.com/Quantum-L9/Cursor-Governance/blob/615d16c5229c18b416d6d28c12bbb97989350769/skills/l9-update-agent-docs/SKILL.md "Repository Documentation Obligation Compiler boundary"
[5]: https://github.com/Quantum-L9/Cursor-Governance/pulls "Cursor-Governance open pull requests"
