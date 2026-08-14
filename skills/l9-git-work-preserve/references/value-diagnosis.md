# Value diagnosis

For each candidate ref:

1. `git log --oneline origin/main..<ref>`
2. `git diff --stat origin/main...<ref>`
3. Unique path set; optional `git cherry -v origin/main <ref>`
4. Emit diagnosis receipt (see `output-receipt.schema.yaml`)

## Confidence

| Level | Rule |
|-------|------|
| high | Zero commits ahead of `origin/main` and empty unique path set |
| medium | Only merge commits / empty trees |
| low / unknown | Any unique commit or unreadable history → **keep** |

Never classify `prune_candidate` when confidence is unknown.
