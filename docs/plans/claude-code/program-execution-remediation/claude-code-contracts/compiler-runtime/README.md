# claude-coding-contract-compiler

Compiles scoped, fail-closed Claude Code contract chains from one canonical campaign spec.

## v2.7.0 execution model

The compiler is now **target-validation-aware** and ecosystem-neutral:

- `campaign.validation.cold_resume.commands` is mandatory.
- `campaign.validation.commit_gate.commands` is mandatory.
- The compiler never guesses npm, pytest, Go, Cargo, Maven, Gradle, Make, or another ecosystem.
- Bootstrap/install commands are never silently treated as validation.
- Every contract runs on the same campaign branch.
- Every contract creates exactly **one local commit** with exact subject = contract ID.
- Contract 2+ preflight proves the immediately previous contract exists as HEAD and reruns the
  entire validation gate that authorized that predecessor commit.
- Internal seams are `<id> committed_and_validated`, not `merged_and_green`.
- No push occurs between contracts.
- Direct `git push` and direct PR creation remain denied.
- The terminal contract alone is authorized to run **exactly `make pr` once** after its local commit.

## Compile

```bash
python scripts/compile_contract.py \
  --spec campaign-spec.yaml \
  --out DIR \
  --validate \
  --emit-artifacts
```

Canonical input schema: `schemas/campaign-spec.schema.json`.
Authoring rules: `references/canonical-spec.md`.

## Validate

Per contract:

```bash
python scripts/validate_contract.py DIR/PR-001.contract.json
```

Whole chain:

```bash
python scripts/validate_chain.py DIR/PR-*.contract.json
```

Target-awareness regression suite:

```bash
python scripts/test_target_validation.py
```

The regression suite includes explicit Node/npm, Python, Go, negative schema, real Git branch and
predecessor-preflight execution, deterministic recompilation, one-commit policy, and single terminal
`make pr` authority.

## Generated per-contract artifacts

With `--emit-artifacts`:

- `.claude/settings.json`
- `CLAUDE.md`
- `preflight.sh`

`preflight.sh` executes canonical command strings exactly. It does not strip inline `#` content and
fails closed on multiline commands, branch mismatch, predecessor commit mismatch, or failed proof.

## DPK

DPK ownership/readiness/rollback integration is preserved. DPK does not choose repository validation
commands. That authority is `campaign.validation`.
