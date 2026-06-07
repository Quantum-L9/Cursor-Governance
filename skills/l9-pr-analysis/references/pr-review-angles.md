<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [pr, review, angles]
status: active
/L9_META -->

# PR review angles

Load when the user asks for a focused PR review without full `/pr` analysis.

## Output contract

- Cite **file path and line number** for each finding.
- Rank: **blocker** | **important** | **nit**.
- Be specific — "looks risky" is not a finding.
- If the diff lacks context, say so and ask for the full file.
- End with verdict on its own line: `Safe to merge | needs changes | reject`.

## Angle 1: Security

Priority order:

1. Auth/authz — missing checks, role assumptions, IDOR
2. Input validation — untrusted input into queries, shell, paths, deserialization
3. Injection — SQL, command, prompt, template
4. Secrets — hardcoded keys, secrets in logs or client bundles
5. Output encoding — XSS, unescaped templating
6. Crypto — `Math.random` for tokens, weak hashes, custom crypto
7. Data exposure — PII in logs, overshared API responses

## Angle 2: Performance

1. N+1 — loops with per-item DB/network calls
2. Hot-path allocations — objects/regex inside loops
3. Unbounded work — missing pagination, unconstrained result sets
4. Bad async — sequential `await` where `Promise.all` fits
5. Cache misuse — wrong cache keys or missing TTLs
6. Complexity — hidden O(n²) patterns

## Angle 3: Tests

1. New branches have at least one test
2. Edge cases — empty, null, boundaries, dependency errors
3. Assertion strength — not snapshot-only or happy-path-only
4. Mocking discipline — mocks fail when interface changes
5. Determinism — date/time/random/network stubbed
6. Test names describe behavior

## Angle 4: Architecture

1. Boundary drift — layers crossing seams
2. Premature abstraction — interfaces with one implementation
3. Coupling — utilities importing feature modules
4. Scalability — what breaks at 10× load
5. Reversibility — rollback difficulty for one-way doors
6. Naming — role-based names, not implementation names

End architecture angle with: `Architecturally sound | needs trim | re-think before merging`.
