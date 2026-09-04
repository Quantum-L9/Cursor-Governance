# Routing regression examples

## Table of contents

1. SplitWisely
2. Website-only idea
3. Bounded existing repository
4. PR Cognitive Convergence
5. Mixed product plus website
6. Negative cases

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

- one existing repository needs a bounded code/documentation/configuration change;
- no cross-repository convergence.

Expected:

```text
EXISTING_REPO_CHANGE -> l9-plan-simple path if planning is still needed
```

If a valid executable plan already exists and the current downstream executor accepts it, reuse it rather than re-plan.

## 4. PR Cognitive Convergence

Requirements affect:

- `Quantum-L9/PR_Repair`;
- `Quantum-L9/LLM-Router`;
- `Quantum-L9/l9-cognitive-runtime`.

The source pack already includes dependency-ordered contracts, acceptance tests, rollback/replay, and a Program Execution handoff.

Expected topology:

```text
EXISTING_SYSTEM_CAMPAIGN -> Program Execution adapter
```

Do not call Foundry, Website-Bot, or Plan Simple as the primary route.

On the 2026-09-02 PE baseline, current admission is single-target, so compatibility result must be:

```text
EXECUTOR_CAPABILITY_GAP
```

Do not lie by naming only PR_Repair as the target or launching three independent campaigns.

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

## 6. Negative cases

### Raw idea with no IdeaOS decision

Expected: `IDEAOS_DECISION_REQUIRED`.

### Unknown specialized capability

Expected: `CAPABILITY_OWNER_UNKNOWN`, not nearest-sounding skill selection.

### Website plus generic repository duplicate

If the generic repository requirement refers only to Website-Bot's internal site repository, reject the duplicate requirement as an ownership modeling error.

### Multi-repo campaign on single-target PE

Expected: `EXECUTOR_CAPABILITY_GAP`, never silent decomposition.
