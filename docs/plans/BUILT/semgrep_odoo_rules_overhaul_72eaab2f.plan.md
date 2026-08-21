---
name: Semgrep Odoo Rules Overhaul
overview: Apply the verified semgrep_overhaul_v1 pack verbatim — overwrite .semgrep/odoo-patterns.yml, add --error to the Makefile semgrep target, wire a pinned semgrep step into ci.yml static-checks, and file the GMP report (renumbered to 134).
todos:
  - id: copy-yml
    content: Overwrite .semgrep/odoo-patterns.yml with the pack's odoo-patterns.yml verbatim (full metadata + header)
    status: completed
  - id: makefile-error
    content: Insert --error into the Makefile semgrep target (line 141), preserving the existing no-@ line form
    status: completed
  - id: ci-wire
    content: Add run_check semgrep step to ci.yml static-checks after 'Pipeline v2 guard' (line 125), pinned semgrep version
    status: completed
  - id: verify-pin
    content: Confirm the pinned semgrep version exists/is current before committing the pin
    status: completed
  - id: gmp-report
    content: Copy the pack's GMP report into reports/ as GMP-Report-134-Semgrep-Rules-Overhaul.md (132 is taken)
    status: completed
  - id: validate
    content: "Validate: YAML parse, semgrep 0 ERROR findings, sql-injection sanity snippet, advisory-lock/CREATE VIEW non-fire, make pr-check"
    status: completed
isProject: false
---

# Semgrep Odoo Rules Overhaul — apply `semgrep_overhaul_v1` pack

Decision: apply **everything** (Tier 1 + 2 + 3) and **copy the pack's files verbatim** (full metadata/header) to minimize rewriting. The pack at [current work - ib/05-29-2026/semgrep_overhaul_v1](current work - ib/05-29-2026/semgrep_overhaul_v1) was independently verified against the live repo and its critique of the prior plan is correct on all points.

## Ground truth (verified this session)

- The on-disk [.semgrep/odoo-patterns.yml](.semgrep/odoo-patterns.yml) currently has `odoo-raw-sql` as a bare top-level `pattern-either:` with **zero exemptions** (would fire on ~50 advisory-lock sites), and already contains `odoo-commented-code` + `odoo-bare-except`. So the rule must be **restructured** (not just amended), `odoo-bare-except` must **not** be re-added, and `odoo-commented-code` must be **preserved**.
- Advisory-lock idiom is `"SELECT pg_try_advisory_lock(hashtext(%s))"` with the dynamic key as a **bound param** (e.g. `[f"...close_{rec.id}"]`) — see [transaction.py](plasticos_transaction/models/transaction.py) L953-966. The regex exemption `pg_(try_)?advisory_(unlock|lock)` matches the `hashtext` variant; the literal `pattern-not` variant would not.
- 3 `CREATE VIEW` sites live in `def init(self):` — covered by `pattern-not-inside def init`.
- [ci.yml](.github/workflows/ci.yml) uses a `run_check` wrapper and has `run_check "Pipeline v2 guard"` at **line 125**; it has **no** semgrep step → the pack's patch is a drop-in *add* (not a replace).
- [Makefile](Makefile) line 141 is `\tsemgrep --config .semgrep/odoo-patterns.yml --severity ERROR --quiet --include="plasticos_*"` (no leading `@`).
- Next free GMP report number is **134** (130-133 exist; the pack's file is mis-numbered 132).
- No `semgrep` pin exists in `requirements*.txt` today → the CI pin is net-new.

## Steps

### 1. Overwrite the rule file (Tier 1 + 2)
Copy [semgrep_overhaul_v1/odoo-patterns.yml](current work - ib/05-29-2026/semgrep_overhaul_v1/odoo-patterns.yml) verbatim over [.semgrep/odoo-patterns.yml](.semgrep/odoo-patterns.yml). This single overwrite delivers all rule-file changes at once:
- `odoo-raw-sql` restructured into `patterns:` AND block + `pattern-not-regex` advisory-lock exemption + `pattern-not-inside def init`.
- `odoo-env-ref-unguarded` fixed into a valid `patterns:` AND block.
- `odoo-commented-code` and `odoo-bare-except` preserved (with metadata).
- `odoo-sql-injection` added (interpolation vector; verified non-FP).
- Full metadata + header/exemption-contract documentation on all 5 rules.
- No `paths:` block (the pack correctly avoids in-rule `paths:` to prevent AND-conflict with CLI `--include`).

### 2. Makefile `--error` (Tier 3)
Edit [Makefile](Makefile) line 141 — insert `--error` after `--severity ERROR`. Keep the existing line form (no leading `@`):

```makefile
	semgrep --config .semgrep/odoo-patterns.yml --severity ERROR --error --quiet --include="plasticos_*"
```

(The pack's `Makefile.patch` shows a leading `@`; the real line has none — apply as a precise edit to the actual line.)

### 3. Wire semgrep into `ci.yml` (Tier 3 — CI policy change)
Per [ci.yml.patch](current work - ib/05-29-2026/semgrep_overhaul_v1/ci.yml.patch), add a blocking `run_check` immediately after `run_check "Pipeline v2 guard"` (line 125), before `run_check "Critical manifest check"` (line 127):

```yaml
          run_check "Semgrep Odoo rules" bash -c \
            "pip install semgrep==<PINNED> --quiet && \
             semgrep --config .semgrep/odoo-patterns.yml \
                     --severity ERROR --error --quiet \
                     --include='plasticos_*'"
```

This makes any new ERROR finding block merges. Safe today (post-overwrite finding count is 0).

### 4. Verify the semgrep pin
Before committing, confirm the pinned version (pack suggests `1.74.0`) is a real, current semgrep release; adjust the pin if a newer stable is preferred. Optionally also record the pin in `requirements-dev.txt` for local/CI parity (small, keeps versions from drifting) — include only if it doesn't widen scope.

### 5. File the GMP report
Copy [semgrep_overhaul_v1/GMP-Report-132-Semgrep-Rules-Overhaul.md](current work - ib/05-29-2026/semgrep_overhaul_v1/GMP-Report-132-Semgrep-Rules-Overhaul.md) into `reports/` as **`GMP-Report-134-Semgrep-Rules-Overhaul.md`** (132 is taken by Crm-Bridge). Fix the in-file report number header to 134.

## Validation (run after edits)
- `python3 -c "import yaml; yaml.safe_load(open('.semgrep/odoo-patterns.yml'))"` → valid YAML.
- `semgrep --config .semgrep/odoo-patterns.yml --severity ERROR --error --quiet --include="plasticos_*"` → **0** findings, exit 0.
- Sanity snippet `cr.execute(f"SELECT {x}")` → `odoo-sql-injection` fires.
- Confirm advisory-lock sites ([transaction.py](plasticos_transaction/models/transaction.py)) and `CREATE VIEW` sites do **not** fire.
- `make pr-check` passes end-to-end.

## Out of scope / do not touch
- No changes to advisory-lock semantics, `CREATE VIEW` DDL, or any business logic.
- Do not embed in-rule `paths:` (pack rationale: ANDs with CLI `--include`).
- Do not re-enable disabled workflows beyond the single `ci.yml` semgrep step.
