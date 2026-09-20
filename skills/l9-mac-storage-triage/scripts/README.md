# Scripts

**Path:** `skills/l9-mac-storage-triage/scripts` | **Kind:** subsystem

## Purpose

Emit FINDINGS.txt (human) and findings.json (machine) from one catalog + diagnosis.

## Modules

### `emit-findings.py`

Emit FINDINGS.txt (human) and findings.json (machine) from one catalog + diagnosis.

- `def kib_to_gib(kib) -> float | None`
- `def load_env_file(path) -> dict[str, str]`
- `def load_focus_sizes(tsv) -> dict[str, float]`
- `def resolve_path(rel) -> tuple[str, str]`
- `def fmt_gib(value) -> str`
- `def safe_label(item) -> str`
- `def pad(text, width) -> str`
- `def wrap_words(text, width) -> list[str]`
- _+9 more public symbol(s)_

## Entrypoints

- `00-diagnose.sh`
- `01-summarize.sh`
- `02-initialize-env.sh`
- `03-validate-env.sh`
- `04-plan.sh`
- `05-apply.sh`
- `06-verify.sh`
- `07-inventory-noise.sh`
- `08-focus-layout.sh`
- `09-emit-findings.sh`
- `inspect-sparse-file.sh`
- `mode-run.sh`
- `scan-ncdu.sh`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
