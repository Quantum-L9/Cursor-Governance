# Improvement Report

## Baseline defect

The repository already had substantial shared lifecycle machinery, but its
ownership boundary was inverted: the shared implementation lived under
`adapters/common`, Claude was documented as the thick gold-standard adapter,
peer identity was embedded in provider descriptors, and Claude had a special
bounded scheduler/provider path.

## Highest-leverage correction

Promote reusable execution into one Peer Execution Core and reduce each peer
provider to capability probe plus request/invocation/result translation.

## Accepted improvements

- one canonical execution substrate upstream of providers;
- identity/provider/profile separation;
- canonical provider request/result contracts;
- shared permission, timeout, context, telemetry, and receipt mechanics;
- fail-closed context/runtime persistence and complete worker remote-action denial;
- strict shared subprocess argv/environment/timeout handling with timeout-race safety;
- durable provider-exception state and fail-closed Claude output translation;
- provider-neutral bounded execution runtime;
- removal of the bounded-autonomy provider identity;
- full single-task Controller-to-provider-to-verification operator spine;
- fail-closed thin-provider architecture gate;
- truthful dormant-provider readiness;
- active doctrine aligned with implementation;
- Controller-owned abort/retry recovery for post-admission execution failures;
- durable Attempt Receipt write-before-success ordering and stale-receipt quarantine;
- isolated-worktree staging plus atomic verified patch application;
- thin-driver enforcement across routable worker, verifier, remote-action, and
  deployment adapter kinds.

## Explicit deferrals

- DeepSeek backend configuration;
- direct DeepSeek provider;
- Codex/Gemini/Manus invocation transports;
- retry policy above one attempt;
- unrelated adapter feature expansion beyond thin-driver ownership correction.

These deferrals do not block Claude-first pipeline execution or the thin-provider
architecture.
