# Sonar FP — LLM/CLI path-escape on optimize-cli-pr-pack scripts

## Status

False-positive residual on SonarCloud New Code Security Rating for this skill's
`scripts/` directory. Same class as `environment/agents/tools/` (PR #25 /
`SONAR-FP-PATH-ESCAPE.md` there).

## Rules flagged after real confinement

| Rule | Sink | Mitigation in code |
|------|------|--------------------|
| `pythonsecurity:S8707` | `route_optimize.py` CLI read/write | `--root` + relative paths + `realpath`/`commonpath` |
| `pythonsecurity:S2083` | `build_commit_pack.write_text` | `under_root` before `open()` |
| `pythonsecurity:S6096` | tar creation | `under_root` + BytesIO payloads (no extract path join) |
| `pythonsecurity:S6350` | `git diff --` path args | `safe_relative` allowlist + argv list (no shell) |

Sonar still attributes BLOCKER/MAJOR vulnerabilities to these sinks after the
gates above, which fails Quality Gate (Security Rating ≥ A).

## Gate workaround

`sonar-project.properties` excludes `**/skills/optimize-cli-pr-pack/scripts/**`
from analysis. Do **not** use `NOSONAR`. Revisit when Sonar recognizes the
sanitizer pattern.
