# System dogfood and validation snapshot

Bound repository: `Quantum-L9/Cursor-Governance`

Bound baseline: `main@119d0df04347f1e45367cccfb68f494a753f4dca`

## Capability census

| Capability | Canonical owner | Kind | Reuse in PR digest | Boundary |
|---|---|---|---|---|
| Skill compilation/validation | `l9-skill-compiler` | deterministic + authored guidance | build and validate this pack | does not own PR judgement |
| Repository wiring | `l9-wire-into-repo` | governed integration | place the guard in the existing lifecycle | does not create a second pipeline |
| Code structure analysis | `l9-code-analysis` | read-only judgement | supporting structural map | not a PR gate by itself |
| Structured judgement | `l9-structured-reasoning` | judgement | unresolved architecture/proportionality only | never parses basic diff/CI |
| Gap/readiness analysis | `l9-gap-analysis` | judgement | conditional target-vs-current delta | not default on every PR |
| Code graph | `l9-code-graph-rag-mcp` | deterministic graph query | conditional importer/blast-radius evidence | only when an index is already healthy |
| PR remediation | `l9-pr-remediation` | mutating convergence | downstream consumer | must not own immutable pre-remediation judgement |
| CI/gates | repository CI + `make pr` | deterministic execution | evidence input | syntax/tests/policy, not semantic proportionality |

## Optimal suite

Core lifecycle: `l9-pr-digest -> l9-pr-remediation`

Build/wire owners: `l9-skill-compiler -> l9-wire-into-repo`

Supporting composition: `l9-code-analysis`, judgement-only `l9-structured-reasoning`, conditional healthy-index `l9-code-graph-rag-mcp`, and conditional explicit-delta `l9-gap-analysis`.

Not globally enabled for this path: `l9-global-architect`, security/performance auditors, CI setup, GMP, and unrelated domain skills. Their responsibilities are distinct and their default context cost or blast radius is unjustified here.

## PR lifecycle gap

Current publish flow opens the PR, writes `.l9/pr/pr-remediation-handoff.json`, and launches the bounded-autonomy `poll_worker`, which historically entered `l9-pr-remediation` directly. CI and the PR board establish mechanical state, but they do not prove task-intent alignment, proportionality, duplicate architecture ownership, or speculative expansion.

Insertion seam: `skills/l9-bounded-autonomy/references/prompt-templates.md#poll_worker`, immediately before the worker is allowed to enter `l9-pr-remediation`.

Only `READY_FOR_REMEDIATION` and `READY_WITH_NON_BLOCKING_NOTES` may pass the bounded remediation packet downstream.

## Real-PR dogfood

- **#474:** generated repo-index cleanup, about 21k deleted lines, observed CI green. `READY_FOR_REMEDIATION`, LLM count 0. Proves size alone does not block.
- **#469:** Semgrep-driven campaign subprocess isolation, observed CI green. `READY_WITH_NON_BLOCKING_NOTES`, LLM count 0, because production changed without a test file in the diff.
- **#476:** 25-file first-class Cursor adapter, observed CI green. Deterministic `title_body_intent_mismatch` plus adapter/governance questions. The adapter location is compatible with canonical law, but the PR body assigns every changed path to an unrelated ruff-format task. Final `INTENT_UNKNOWN_REVIEW_REQUIRED`, one targeted judgement pass. Green CI does not waive intent authority.
- **#479:** repo-doc topology/schema hardening. Observed `L9 Lint and Test` failure. `CI_OR_EXECUTION_FAILURE`, LLM count 0 because deterministic failure already blocks.
- **#460:** 30-file WIP CI audit archive with wheel/tar evidence, observed CI green. Binary/dependency signals require one targeted judgement; PR body explicitly maps them to audit evidence. Final `READY_WITH_NON_BLOCKING_NOTES`. Large/binary evidence is not rejected merely for being unusual.

## False-positive / false-negative review

False positives caught and repaired during dogfood:

- new files under existing top-level directories are no longer treated as new top-level owners without base-directory evidence
- `test_catalog.txt` is no longer mistaken for an executable deleted test
- adapter-directory growth is grouped instead of emitting one semantic question per file

Known residual risk: semantic duplicate ownership can remain `UNKNOWN` when repository search or a healthy code graph cannot establish equivalence. Connector-normalized evidence without patches is weaker than a local git checkout, so the engine preserves questions/unknowns instead of fabricating proof.

No known false negative was demonstrated by this bounded corpus. That is not a claim of exhaustive detection.

## Validation receipt

Executed locally against the authored pack overlay:

- `python3 scripts/self_test.py` -> PASS
- `python3 -m py_compile scripts/pr_digest.py scripts/self_test.py` -> PASS
- repo-exact `l9-skill-compiler/scripts/validate_skill_pack.py` logic -> PASS
- `pr_digest.py --validate-only` on emitted machine JSON -> PASS
- pre-remediation wiring test -> 2 passed
- normalized real-PR fixtures for #474, #469, #476, #479, #460 -> executed

Full repository `make pr-check` was `NOT_EXECUTED` locally because this runtime cannot clone GitHub. Remote branch CI is the authoritative full-repository regression after publication.
