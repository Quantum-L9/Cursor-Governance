# Routing regression examples

## Table of contents

1. SplitWisely
2. Website-only idea
3. Bounded existing repository
4. PR Cognitive Convergence
5. Mixed product plus website
6. IgorBot lineage regression
7. Negative cases

## 1. SplitWisely

Requirements:

- new standalone software product repository;
- no specialized factory owns the product artifact.

Expected:

```text
NEW_PRODUCT_REPOSITORY -> l9-idea-foundry
```

Website-Bot is not called unless a separate website requirement exists.

## 2. Website-only idea

Requirement:

- new marketing/corporate/service website.

Expected:

```text
SPECIALIZED_FACTORY -> Quantum-L9/Website-Bot
```

Foundry is not called merely because Website-Bot may provision a site repository.

## 3. Bounded existing repository

Requirement:

- one existing repository needs a bounded change;
- no cross-repository convergence.

Expected:

```text
EXISTING_REPO_CHANGE -> l9-plan-simple when planning is still needed
```

If a valid executable plan already exists and the current downstream executor accepts it, reuse it rather than re-plan.

## 4. PR Cognitive Convergence

Requirements affect multiple existing repositories and form one causal program.

Expected topology:

```text
EXISTING_SYSTEM_CAMPAIGN -> Program Execution adapter
```

If a validated current Program Execution snapshot explicitly denies multi-target admission, compatibility is:

```text
EXECUTOR_CAPABILITY_GAP
```

If multi-target support is unresolved, the result is `ADAPTER_CAPABILITY_UNKNOWN`, never a guessed gap and never silent decomposition.

## 5. Mixed product plus website

Requirements:

- new standalone product repository;
- new marketing website.

Expected graph:

```text
unit-product -> Foundry
unit-website -> Website-Bot
```

If website authoring needs product identity produced by Foundry, add an explicit dependency. Otherwise run independently.

## 6. IgorBot lineage regression

This fixture captures the real failure that motivated v1.1.

Source outcome:

- a mature voice/follow-up idea pack initially looks birth-shaped;
- repository reality proves `Quantum-L9/igorbot` already owns the product/runtime;
- no new repository is born;
- the route becomes one `EXISTING_REPO_CHANGE` owned by `l9-plan-simple`;
- a supplied Execution Graph is structurally valid but its `source_envelope_digest` belongs to an older Envelope;
- a supplied Plan Simple capability snapshot has the wrong shape and falsely appears to show incapability.

Required behavior:

```text
validated Envelope
  -> supplied stale Graph rejected as DERIVED_ARTIFACT_STALE
  -> regenerate Graph from Envelope
  -> malformed adapter evidence rejected as ADAPTER_SNAPSHOT_INVALID
  -> inspect current Plan Simple contract
  -> compile revision-bound adapter-capabilities/v2 snapshot
  -> COMPATIBLE when single-target support is proven
  -> hand off bounded existing-repo unit
```

Never interpret the stale graph as current because it passes structural validation. Never interpret malformed adapter evidence as `EXECUTOR_CAPABILITY_GAP`.

## 7. Negative cases

### Raw idea with no IdeaOS decision

Expected: `IDEAOS_DECISION_REQUIRED`.

### Unknown capability

Expected: `CAPABILITY_OWNER_UNKNOWN`, not nearest-sounding skill selection.

### Website plus generic repository duplicate

If the generic repository requirement refers only to Website-Bot's internal site repository, reject the duplicate requirement as an ownership-modeling error.

### Stale graph

If graph `source_envelope_digest` does not equal the semantic digest of the current Envelope:

```text
DERIVED_ARTIFACT_STALE
```

Regenerate from the Envelope and invalidate dependent receipts.

### Invalid adapter snapshot

Missing source revision bindings or topology declarations:

```text
ADAPTER_SNAPSHOT_INVALID
```

Do not emit `EXECUTOR_CAPABILITY_GAP`.

### Unknown adapter support

A valid snapshot with `multi_target: null` or `single_target: null` yields:

```text
ADAPTER_CAPABILITY_UNKNOWN
```

### Stale receipt

A Receipt whose Envelope or Graph digest no longer matches current parents is `DERIVED_ARTIFACT_STALE` and must be regenerated without reopening unrelated upstream decisions.
