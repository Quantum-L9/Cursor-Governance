# Executive Decision: Program Execution v3 Hardening

## Decision

Build v3 where no authority-bearing transition depends on a semantic fact lacking one immutable identity, one canonical meaning, one authorized principal, and one executable proof path. Deliver baseline characterization and counterexample registry.

## Problem being resolved

Current v2 PE allows semantic drift (compiler drops retry_policy), mutable identities (dirty candidate becomes HEAD), cross-claim evidence substitution, actor-string authority, and caller-supplied gate PASS. Baseline characterization (S0) freezes v2 at 0db3fed, creates executable counterexample registry, and proves exact current behavior before v3 rebuild.

## Target state

Stage S0 complete: baseline frozen at 0db3fed, orchestrator detached, counterexample registry with executable xfail tests for every v2 gap, baseline integrity report with digest manifest, all gates PASS, ready for S1 semantic conservation work.

## Authority assignment

Reference `AUTHORITY_REGISTRY.yaml`.

