# Campaign Activation Files

Two things live here.

| Path | What it is |
|---|---|
| `TEMPLATE/` | Copy-and-fill kit. The only files you need for a new campaign. |
| this folder (root + `examples/` + `level3-make-pr-single-path/`) | Worked example: `level3-make-pr-single-path`. Not a template. |

## New campaign

1. Copy `TEMPLATE/INTENT.yaml`.
2. Fill `campaign_id`, `title`, `objective`, `target`, `tasks`.
3. Follow `TEMPLATE/HOWTO.md`.

Do not start from `CAMPAIGN_SOURCE.yaml` in this folder. That seed is the
level-3 example. The activator compiler emits a valid seed from INTENT.

## This folder (level-3 example)

| File | Role |
|---|---|
| `INTENT.yaml` | Front-door for `level3-make-pr-single-path`. Compiler-admissible. Forbidden inside `campaigns/<id>/`. |
| `CAMPAIGN_SOURCE.yaml` | Compiled v2 seed for that example. Lands at `campaigns/<id>/`. |
| `source-integrity-receipt.json` | sha256 bind of that seed. Lands next to it. |
| `HOST_REGISTRATIONS.yaml` | The four host appends. Compiler patches these; do not invent new host files. |
| `host-patches/` | Append-only snippets. Never overwrite live host files with these. |
| `level3-make-pr-single-path/` | Same seed + receipt as the campaign-dir pair. |

## Allowed campaign-dir pair

```
environment/program-execution/campaigns/<id>/
  CAMPAIGN_SOURCE.yaml
  source-integrity-receipt.json
```

Nothing else.
