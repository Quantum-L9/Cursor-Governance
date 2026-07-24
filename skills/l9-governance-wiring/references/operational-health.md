<!-- L9_META
l9_schema: 1
parent: l9-governance-wiring
origin: migrated-from profiles/operational-health.md
sources: [profiles/operational-health.md]
tags: [health, oversight, verification, governance]
status: active
/L9_META -->

# Operational Health

How to check whether the governance installation is actually working, rather than assuming it is.

## The two live checks

| Check | What it verifies |
|---|---|
| `ops/scripts/verify-setup-alignment.sh` | Presence and wiring of governance scripts, hooks, symlinks, LaunchAgents |
| `ops/scripts/operational-oversight.py` | Higher-level oversight; invokes the alignment script as its verification path |

Run the alignment script directly when diagnosing a wiring problem; run oversight when you want the
aggregate view.

## Reading the result

The alignment script reports `N / M` tests passed. **The baseline is not currently a full pass** —
some tests fail on missing optional scripts and LaunchAgent services. That means:

- A raw failure count is not itself a finding. Compare against the known baseline.
- The signal is a **change** in the count, or a specific test flipping from pass to fail.
- Record the baseline count before making governance changes, so regressions are attributable.

## Anti-pattern

Do not make a failing test pass by weakening the test. If a check fails because the artifact it looks
for genuinely no longer exists, either restore the artifact or remove the check with that reasoning
stated — never lower a threshold to get green.

## Not implemented

The original profile described automatic recovery-script triggering on critical failure, aggregated
health scoring, and a `workspace_health_report.json` artifact. None of that exists. Health checks are
**manually invoked and read by a human or agent** — treat any claim of autonomous recovery as false.
