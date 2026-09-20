# Scripts

**Path:** `skills/l9-mac-storage-triage/scripts` | **Tier:** discovered

## Purpose

Emit FINDINGS.txt (human) and findings.json (machine) from one catalog + diagnosis.



## Components

### Shell entrypoints

- `skills/l9-mac-storage-triage/scripts/00-diagnose.sh`
- `skills/l9-mac-storage-triage/scripts/01-summarize.sh`
- `skills/l9-mac-storage-triage/scripts/02-initialize-env.sh`
- `skills/l9-mac-storage-triage/scripts/03-validate-env.sh`
- `skills/l9-mac-storage-triage/scripts/04-plan.sh`
- `skills/l9-mac-storage-triage/scripts/05-apply.sh`
- `skills/l9-mac-storage-triage/scripts/06-verify.sh`
- `skills/l9-mac-storage-triage/scripts/07-inventory-noise.sh`
- `skills/l9-mac-storage-triage/scripts/08-focus-layout.sh`
- `skills/l9-mac-storage-triage/scripts/09-emit-findings.sh`
- `skills/l9-mac-storage-triage/scripts/inspect-sparse-file.sh`
- `skills/l9-mac-storage-triage/scripts/mode-run.sh`
- `skills/l9-mac-storage-triage/scripts/scan-ncdu.sh`

## Functions

- `def kib_to_gib(kib) -> float | None`
- `def load_env_file(path) -> dict[str, str]`
- `def load_focus_sizes(tsv) -> dict[str, float]`
- `def resolve_path(rel) -> tuple[str, str]`
- `def fmt_gib(value) -> str`
- `def safe_label(item) -> str`
- `def pad(text, width) -> str`
- `def wrap_words(text, width) -> list[str]`
- `def du_gib(path, timeout) -> float | None`
- `def entry_when(entry) -> str`
- `def needs_inspect(raw) -> bool`
- `def inspect_path(abs_path, hint) -> dict | None`
- `def render_txt(doc) -> str`
- `def build_doc(report_dir) -> dict`
- `def write_outputs(doc, report_dir) -> None`
- `def latest_report() -> Path | None`
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `datetime`, `json`, `os`, `pathlib`, `shutil`, `subprocess`

<!-- l9-module-readme: generated-from-ast -->
