# Laws and Invariants

These are reconciled invariants derived from repeated source evidence. They are not claimed as pre-existing named laws unless the cited source says so.

## INV-001 — Repository ownership outranks bootstrap convenience

Bootstrap must not overwrite, symlink over, or blanket-ignore tracked consumer-repository content.

**Evidence:** P3 FAIL-02; P6 FA-4; P9 F-01; C-001

## INV-002 — Machine/session artifacts must not create false authored-work signals

Bootstrap/state artifacts should live outside repo-owned surfaces or be explicitly owned and excluded from author-work checks.

**Evidence:** P1 FRICTION-01/02; P3 FRIC-02; P6 FA-4; P9 F-01/F-02

## INV-003 — Destructive ambiguity remains fail-closed

Unresolved or empty destructive targets remain blocked; remediation improves literal scope, authorization reachability, and diagnostics instead of weakening the safety check.

**Evidence:** P1 FRICTION-12; P4 F-05; P9 FR-07; C-007

## INV-004 — Capability health is multidimensional

REST, GraphQL, token validity, broker reachability, MCP parse/approval, and memory transports are independently observable states.

**Evidence:** CF-001; CF-006; CF-014; C-004; C-006

## INV-005 — Freshness-bound receipts cannot silently outlive their authority inputs

Receipts that depend on governance revision, container lifecycle, branch, or head must become stale/invalid when those inputs change.

**Evidence:** P3 FRIC-07; P4 FR-03; P6 FA-2; P8 R-05; P9 F-06/F-13

## INV-006 — Exceptional authority must be scoped and expiring

A one-time breakglass grant cannot become standing silent configuration.

**Evidence:** P1 FRICTION-08; P6 FR-4; P9 F-17

## INV-007 — Mandated command paths must exist or have one explicit supported fallback

Policy may not simultaneously declare a single mandatory command and govern repositories that lack it without a canonical fallback.

**Evidence:** P1 FRICTION-04; P3 FAIL-09; P6 FR-2; P9 F-10

## INV-008 — Authority-sensitive drift needs provenance and an executable resolution path

The effective value, source, expected value, and repairability must be visible; unresolved policy choice stays OPEN.

**Evidence:** CF-003; CI-006

## INV-009 — Session continuity must carry task state or explicitly state that none exists

Hydration/writeback may not treat generic resume tautologies as task-bearing continuity.

**Evidence:** P1 FRICTION-06; P6 FA-5/6; P7 FR-05; P9 F-04/FR-02

## INV-010 — Toolchain READY means the repository can actually run under the resolved project environment

Installed binaries alone are insufficient; interpreter/version/importability must be verified.

**Evidence:** P3 FAIL-04/05; P5 FR-003; P8 R-02; P9 F-15

## INV-011 — Rules that depend on optional surface capabilities must declare the precondition

When the mechanism is unavailable, the rule intent remains but the missing execution mechanism is surfaced before work begins.

**Evidence:** P4 FR-05; P9 FR-01/08; CI-012
